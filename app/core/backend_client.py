"""
Backend client service for communicating with the Demucs separation backend.
"""
import logging
from typing import Optional
import httpx
from django.conf import settings
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class JobStatus:
    """Job status response from backend."""
    job_id: str
    status: str
    progress: float = 0.0
    current_step: str = ""
    output_files: list[str] = None
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if self.output_files is None:
            self.output_files = []


class BackendClient:
    """
    Client for communicating with the MuxMinus backend service.
    
    This client handles all HTTP communication with the FastAPI backend
    that runs Demucs for audio separation.
    """
    
    def __init__(self, base_url: str = None, api_key: str = None, timeout: float = 30.0):
        self.base_url = base_url or getattr(settings, 'BACKEND_URL', 'http://localhost:8001')
        self.api_key = api_key or getattr(settings, 'BACKEND_API_KEY', None)
        self.timeout = timeout
        
        self._headers = {}
        if self.api_key:
            self._headers['X-API-Key'] = self.api_key
    
    def _get_client(self) -> httpx.Client:
        """Get an HTTP client with configured defaults."""
        return httpx.Client(
            base_url=self.base_url,
            headers=self._headers,
            timeout=self.timeout,
        )
    
    async def _get_async_client(self) -> httpx.AsyncClient:
        """Get an async HTTP client with configured defaults."""
        return httpx.AsyncClient(
            base_url=self.base_url,
            headers=self._headers,
            timeout=self.timeout,
        )
    
    # =========================================================================
    # Health & Status
    # =========================================================================
    
    def health_check(self) -> dict:
        """Check if the backend is healthy."""
        try:
            with self._get_client() as client:
                response = client.get("/health")
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Backend health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}
    
    def get_queue_status(self) -> dict:
        """Get the current queue status."""
        with self._get_client() as client:
            response = client.get("/queue/status")
            response.raise_for_status()
            return response.json()
    
    def can_accept_jobs(self) -> bool:
        """Check if the backend can accept new jobs."""
        try:
            status = self.get_queue_status()
            return status.get("can_accept_jobs", False)
        except Exception as e:
            logger.error(f"Failed to check queue status: {e}")
            return False
    
    # =========================================================================
    # Models
    # =========================================================================
    
    def list_models(self) -> list[dict]:
        """List available Demucs models."""
        with self._get_client() as client:
            response = client.get("/models")
            response.raise_for_status()
            return response.json()
    
    def get_model_info(self, model_name: str) -> dict:
        """Get information about a specific model."""
        with self._get_client() as client:
            response = client.get(f"/models/{model_name}")
            response.raise_for_status()
            return response.json()
    
    # =========================================================================
    # Job Management
    # =========================================================================
    
    def submit_job(
        self,
        job_id: str,
        input_path: str,
        model: str = "htdemucs",
        two_stem: Optional[str] = None,
        output_format: str = "mp3",
    ) -> JobStatus:
        """
        Submit a new separation job to the backend.
        
        Args:
            job_id: Unique job identifier
            input_path: Path to input file (relative to shared uploads dir)
            model: Demucs model to use
            two_stem: Optional stem for two-stem separation
            output_format: Output audio format (mp3 or wav)
            
        Returns:
            JobStatus with initial status
        """
        payload = {
            "job_id": job_id,
            "input_path": input_path,
            "model": model,
            "output_format": output_format,
        }
        if two_stem:
            payload["two_stem"] = two_stem
        
        with self._get_client() as client:
            response = client.post("/jobs", json=payload)
            response.raise_for_status()
            data = response.json()
            return JobStatus(
                job_id=data["job_id"],
                status=data["status"],
                progress=data.get("progress", 0.0),
                current_step=data.get("current_step", ""),
            )
    
    def get_job_status(self, job_id: str) -> JobStatus:
        """Get the current status of a job."""
        with self._get_client() as client:
            response = client.get(f"/jobs/{job_id}")
            response.raise_for_status()
            data = response.json()
            return JobStatus(
                job_id=data["job_id"],
                status=data["status"],
                progress=data.get("progress", 0.0),
                current_step=data.get("current_step", ""),
                output_files=data.get("output_files", []),
                error_message=data.get("error_message"),
            )
    
    def list_jobs(self) -> list[JobStatus]:
        """List all jobs in the backend."""
        with self._get_client() as client:
            response = client.get("/jobs")
            response.raise_for_status()
            return [
                JobStatus(
                    job_id=data["job_id"],
                    status=data["status"],
                    progress=data.get("progress", 0.0),
                    current_step=data.get("current_step", ""),
                    output_files=data.get("output_files", []),
                    error_message=data.get("error_message"),
                )
                for data in response.json()
            ]
    
    def delete_job(self, job_id: str) -> bool:
        """Delete a completed/failed job from the backend."""
        try:
            with self._get_client() as client:
                response = client.delete(f"/jobs/{job_id}")
                response.raise_for_status()
                return True
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return False
            raise


# Global client instance
backend_client = BackendClient()
