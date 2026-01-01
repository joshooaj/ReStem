"""
Job queue manager for handling concurrent separation jobs.
"""
import asyncio
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
import traceback

from .config import settings
from .models import JobStatus, ModelChoice, StemChoice, OutputFormat
from .separator import separation_service

logger = logging.getLogger(__name__)


@dataclass
class Job:
    """Represents a separation job."""
    job_id: str
    input_path: Path
    output_dir: Path
    model: ModelChoice
    two_stem: Optional[StemChoice]
    output_format: OutputFormat = OutputFormat.MP3
    status: JobStatus = JobStatus.QUEUED
    progress: float = 0.0
    current_step: str = ""
    output_files: list[str] = field(default_factory=list)
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    processing_time: Optional[float] = None


class JobQueue:
    """
    Manages a queue of separation jobs with concurrency control.
    
    This ensures we don't overwhelm the system with too many concurrent
    GPU/CPU intensive separation tasks.
    """
    
    def __init__(self, max_concurrent: int = None, max_queue_size: int = None):
        self.max_concurrent = max_concurrent or settings.max_concurrent_jobs
        self.max_queue_size = max_queue_size or settings.max_queue_size
        
        self._jobs: Dict[str, Job] = {}
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=self.max_queue_size)
        self._active_count = 0
        self._lock = asyncio.Lock()
        self._workers: list[asyncio.Task] = []
        self._running = False
        
        logger.info(f"JobQueue initialized: max_concurrent={self.max_concurrent}, max_queue_size={self.max_queue_size}")
    
    async def start(self):
        """Start the worker tasks."""
        if self._running:
            return
            
        self._running = True
        
        # Create worker tasks
        for i in range(self.max_concurrent):
            worker = asyncio.create_task(self._worker(i))
            self._workers.append(worker)
        
        logger.info(f"Started {self.max_concurrent} worker tasks")
    
    async def stop(self):
        """Stop all worker tasks."""
        self._running = False
        
        # Cancel all workers
        for worker in self._workers:
            worker.cancel()
        
        # Wait for workers to finish
        if self._workers:
            await asyncio.gather(*self._workers, return_exceptions=True)
        
        self._workers.clear()
        logger.info("Job queue stopped")
    
    async def _worker(self, worker_id: int):
        """Worker task that processes jobs from the queue."""
        logger.info(f"Worker {worker_id} started")
        
        while self._running:
            try:
                # Wait for a job from the queue
                job_id = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            
            try:
                async with self._lock:
                    self._active_count += 1
                
                await self._process_job(job_id, worker_id)
                
            finally:
                async with self._lock:
                    self._active_count -= 1
                self._queue.task_done()
        
        logger.info(f"Worker {worker_id} stopped")
    
    async def _process_job(self, job_id: str, worker_id: int):
        """Process a single job."""
        job = self._jobs.get(job_id)
        if not job:
            logger.warning(f"Job {job_id} not found in jobs dict")
            return
        
        logger.info(f"Worker {worker_id} processing job {job_id}")
        
        job.status = JobStatus.PROCESSING
        job.started_at = datetime.utcnow()
        job.current_step = "Loading audio file"
        
        start_time = time.time()
        
        try:
            # Progress callback to update job progress
            def progress_callback(info: dict):
                job.progress = info.get("progress", 0)
                job.current_step = f"Separating ({info.get('state', 'processing')})"
            
            # Run separation in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            output_files = await loop.run_in_executor(
                None,
                lambda: separation_service.separate(
                    input_path=job.input_path,
                    output_dir=job.output_dir,
                    model=job.model,
                    two_stem=job.two_stem,
                    output_format=job.output_format,
                    progress_callback=progress_callback,
                )
            )
            
            # Update job with results
            job.status = JobStatus.COMPLETED
            job.progress = 100.0
            job.current_step = "Complete"
            job.output_files = [str(p.relative_to(settings.outputs_dir)) for p in output_files.values()]
            job.completed_at = datetime.utcnow()
            job.processing_time = time.time() - start_time
            
            logger.info(f"Job {job_id} completed in {job.processing_time:.2f}s")
            
        except Exception as e:
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            job.processing_time = time.time() - start_time
            
            logger.error(f"Job {job_id} failed: {e}")
            logger.debug(traceback.format_exc())
    
    async def submit(
        self,
        job_id: str,
        input_path: Path,
        model: ModelChoice = ModelChoice.HTDEMUCS,
        two_stem: Optional[StemChoice] = None,
        output_format: OutputFormat = OutputFormat.MP3,
    ) -> Job:
        """
        Submit a new job to the queue.
        
        Args:
            job_id: Unique job identifier
            input_path: Path to input audio file
            model: Demucs model to use
            two_stem: Optional stem for two-stem separation
            output_format: Output audio format
            
        Returns:
            The created Job object
            
        Raises:
            ValueError: If job_id already exists or queue is full
        """
        if job_id in self._jobs:
            raise ValueError(f"Job {job_id} already exists")
        
        if self._queue.full():
            raise ValueError("Job queue is full")
        
        # Create output directory for this job
        output_dir = settings.outputs_dir / job_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create job object
        job = Job(
            job_id=job_id,
            input_path=input_path,
            output_dir=output_dir,
            model=model,
            two_stem=two_stem,
            output_format=output_format,
        )
        
        # Store and queue the job
        self._jobs[job_id] = job
        await self._queue.put(job_id)
        
        logger.info(f"Job {job_id} submitted to queue")
        return job
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """Get a job by ID."""
        return self._jobs.get(job_id)
    
    def get_all_jobs(self) -> list[Job]:
        """Get all jobs."""
        return list(self._jobs.values())
    
    def remove_job(self, job_id: str) -> bool:
        """Remove a completed/failed job from tracking."""
        job = self._jobs.get(job_id)
        if job and job.status in (JobStatus.COMPLETED, JobStatus.FAILED):
            del self._jobs[job_id]
            return True
        return False
    
    @property
    def queue_size(self) -> int:
        """Number of jobs waiting in queue."""
        return self._queue.qsize()
    
    @property
    def active_jobs(self) -> int:
        """Number of jobs currently processing."""
        return self._active_count
    
    @property
    def can_accept_jobs(self) -> bool:
        """Check if the queue can accept more jobs."""
        return not self._queue.full()


# Global job queue instance
job_queue = JobQueue()
