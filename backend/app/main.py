"""
MuxMinus Backend API - FastAPI Application

This service handles audio separation using Demucs models.
It's designed to run internally and receive jobs from the Django frontend.
"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Header
from fastapi.middleware.cors import CORSMiddleware

from .config import settings, ensure_directories
from .models import (
    JobRequest,
    JobStatusResponse,
    JobResult,
    ModelInfo,
    HealthResponse,
    QueueStatusResponse,
    JobStatus,
    ModelChoice,
    TranscriptionRequest,
    LyricsPipelineRequest,
    JobType,
)
from .queue import job_queue
from .separator import separation_service

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# Application version
VERSION = "1.0.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting MuxMinus Backend Service")
    ensure_directories()
    await job_queue.start()
    logger.info("Backend service ready")
    
    yield
    
    # Shutdown
    logger.info("Shutting down MuxMinus Backend Service")
    await job_queue.stop()


# Create FastAPI app
app = FastAPI(
    title="MuxMinus Backend API",
    description="Internal API for audio separation using Demucs",
    version=VERSION,
    lifespan=lifespan,
)

# Add CORS middleware (for internal use, you may want to restrict this)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Optional API key authentication
async def verify_api_key(x_api_key: Optional[str] = Header(None)):
    """Verify API key if configured."""
    if settings.api_key:
        if x_api_key != settings.api_key:
            raise HTTPException(status_code=401, detail="Invalid API key")
    return True


# =============================================================================
# Health & Status Endpoints
# =============================================================================

@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version=VERSION,
        device=separation_service.device,
        queue_size=job_queue.queue_size,
        active_jobs=job_queue.active_jobs,
    )


@app.get("/queue/status", response_model=QueueStatusResponse, tags=["Queue"])
async def queue_status():
    """Get the current queue status."""
    return QueueStatusResponse(
        queue_size=job_queue.queue_size,
        active_jobs=job_queue.active_jobs,
        max_concurrent=job_queue.max_concurrent,
        can_accept_jobs=job_queue.can_accept_jobs,
    )


# =============================================================================
# Model Information Endpoints
# =============================================================================

@app.get("/models", response_model=list[ModelInfo], tags=["Models"])
async def list_models():
    """List available Demucs models."""
    models = separation_service.list_models()
    return [
        ModelInfo(
            name=m["id"],
            description=m["description"],
            stems=m["stems"],
            supports_two_stem=m["supports_two_stem"],
        )
        for m in models
    ]


@app.get("/models/{model_name}", response_model=ModelInfo, tags=["Models"])
async def get_model_info(model_name: str):
    """Get information about a specific model."""
    try:
        model = ModelChoice(model_name)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found")
    
    info = separation_service.get_model_info(model)
    if not info:
        raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found")
    
    return ModelInfo(
        name=info["name"],
        description=info["description"],
        stems=info["stems"],
        supports_two_stem=True,
    )


# =============================================================================
# Job Management Endpoints
# =============================================================================

@app.post("/jobs", response_model=JobStatusResponse, tags=["Jobs"])
async def create_job(
    request: JobRequest,
    _: bool = Depends(verify_api_key),
):
    """
    Submit a new separation job.
    
    The job will be queued and processed asynchronously. Use the
    GET /jobs/{job_id} endpoint to check the status and retrieve results.
    """
    # Check if queue can accept jobs
    if not job_queue.can_accept_jobs:
        raise HTTPException(
            status_code=503,
            detail="Job queue is full. Please try again later.",
        )
    
    # Construct input path
    input_path = settings.uploads_dir / request.input_path
    
    # Verify input file exists
    if not input_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Input file not found: {request.input_path}",
        )
    
    # Check if job already exists
    existing_job = job_queue.get_job(request.job_id)
    if existing_job:
        raise HTTPException(
            status_code=409,
            detail=f"Job {request.job_id} already exists",
        )
    
    try:
        # Submit job to queue
        job = await job_queue.submit(
            job_id=request.job_id,
            input_path=input_path,
            job_type=JobType.SEPARATION,
            model=request.model,
            two_stem=request.two_stem,
            output_format=request.output_format,
        )
        
        return JobStatusResponse(
            job_id=job.job_id,
            status=job.status,
            progress=job.progress,
            current_step=job.current_step,
            created_at=job.created_at,
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/jobs/{job_id}", response_model=JobStatusResponse, tags=["Jobs"])
async def get_job_status(job_id: str):
    """Get the status of a job."""
    job = job_queue.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    return JobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        progress=job.progress,
        current_step=job.current_step,
        output_files=job.output_files,
        error_message=job.error_message,
        created_at=job.created_at,
        completed_at=job.completed_at,
    )


@app.get("/jobs", response_model=list[JobStatusResponse], tags=["Jobs"])
async def list_jobs():
    """List all jobs."""
    jobs = job_queue.get_all_jobs()
    return [
        JobStatusResponse(
            job_id=job.job_id,
            status=job.status,
            progress=job.progress,
            current_step=job.current_step,
            output_files=job.output_files,
            error_message=job.error_message,
            created_at=job.created_at,
            completed_at=job.completed_at,
        )
        for job in jobs
    ]


@app.delete("/jobs/{job_id}", tags=["Jobs"])
async def delete_job(job_id: str, _: bool = Depends(verify_api_key)):
    """
    Remove a completed or failed job from tracking.
    
    Note: This only removes the job from the queue's memory.
    Output files are NOT deleted by this endpoint.
    """
    job = job_queue.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    if job.status not in (JobStatus.COMPLETED, JobStatus.FAILED):
        raise HTTPException(
            status_code=400,
            detail="Can only delete completed or failed jobs",
        )
    
    job_queue.remove_job(job_id)
    return {"message": f"Job {job_id} removed"}


# =============================================================================
# Transcription Endpoints
# =============================================================================

@app.post("/transcribe", response_model=JobStatusResponse, tags=["Transcription"])
async def create_transcription_job(
    request: TranscriptionRequest,
    _: bool = Depends(verify_api_key),
):
    """
    Submit a new transcription job.
    
    The job will be queued and processed asynchronously. Use the
    GET /jobs/{job_id} endpoint to check the status and retrieve results.
    """
    # Check if queue can accept jobs
    if not job_queue.can_accept_jobs:
        raise HTTPException(
            status_code=503,
            detail="Job queue is full. Please try again later.",
        )
    
    # Construct input path
    input_path = settings.uploads_dir / request.input_path
    
    # Verify input file exists
    if not input_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Input file not found: {request.input_path}",
        )
    
    # Check file size (max 5GB for transcription)
    if input_path.stat().st_size > settings.max_upload_size_transcription:
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds 5GB limit for transcription jobs",
        )
    
    # Check if job already exists
    existing_job = job_queue.get_job(request.job_id)
    if existing_job:
        raise HTTPException(
            status_code=409,
            detail=f"Job {request.job_id} already exists",
        )
    
    try:
        # Submit job to queue
        job = await job_queue.submit(
            job_id=request.job_id,
            input_path=input_path,
            job_type=JobType.TRANSCRIPTION,
            transcription_type=request.transcription_type,
            transcription_format=request.transcription_format,
            language=request.language,
        )
        
        return JobStatusResponse(
            job_id=job.job_id,
            status=job.status,
            progress=job.progress,
            current_step=job.current_step,
            created_at=job.created_at,
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/lyrics", response_model=JobStatusResponse, tags=["Transcription"])
async def create_lyrics_pipeline_job(
    request: LyricsPipelineRequest,
    _: bool = Depends(verify_api_key),
):
    """
    Submit a new lyrics pipeline job (Demucs vocal isolation + Whisper transcription).
    
    This job type costs 2 credits as it performs both vocal separation and transcription.
    The job will be queued and processed asynchronously. Use the
    GET /jobs/{job_id} endpoint to check the status and retrieve results.
    """
    # Check if queue can accept jobs
    if not job_queue.can_accept_jobs:
        raise HTTPException(
            status_code=503,
            detail="Job queue is full. Please try again later.",
        )
    
    # Construct input path
    input_path = settings.uploads_dir / request.input_path
    
    # Verify input file exists
    if not input_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Input file not found: {request.input_path}",
        )
    
    # Check file size (max 5GB for lyrics pipeline)
    if input_path.stat().st_size > settings.max_upload_size_transcription:
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds 5GB limit for lyrics pipeline jobs",
        )
    
    # Check if job already exists
    existing_job = job_queue.get_job(request.job_id)
    if existing_job:
        raise HTTPException(
            status_code=409,
            detail=f"Job {request.job_id} already exists",
        )
    
    try:
        # Submit job to queue
        job = await job_queue.submit(
            job_id=request.job_id,
            input_path=input_path,
            job_type=JobType.LYRICS_PIPELINE,
            language=request.language,
        )
        
        return JobStatusResponse(
            job_id=job.job_id,
            status=job.status,
            progress=job.progress,
            current_step=job.current_step,
            created_at=job.created_at,
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# Entry point for running directly
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
