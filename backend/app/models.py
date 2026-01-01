"""
Pydantic models for API request/response schemas.
"""
from pydantic import BaseModel, Field
from typing import Literal, Optional
from enum import Enum
from datetime import datetime


class ModelChoice(str, Enum):
    """Available Demucs models."""
    HTDEMUCS = "htdemucs"
    HTDEMUCS_FT = "htdemucs_ft"
    HTDEMUCS_6S = "htdemucs_6s"


class StemChoice(str, Enum):
    """Available stems for two-stem separation."""
    VOCALS = "vocals"
    DRUMS = "drums"
    BASS = "bass"


class OutputFormat(str, Enum):
    """Output audio format."""
    MP3 = "mp3"
    WAV = "wav"


class JobStatus(str, Enum):
    """Job processing status."""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobRequest(BaseModel):
    """Request to create a new separation job."""
    job_id: str = Field(..., description="Unique job identifier from frontend")
    input_path: str = Field(..., description="Path to input audio file (relative to uploads dir)")
    model: ModelChoice = Field(default=ModelChoice.HTDEMUCS, description="Demucs model to use")
    two_stem: Optional[StemChoice] = Field(default=None, description="Stem to isolate for two-stem mode")
    output_format: OutputFormat = Field(default=OutputFormat.MP3, description="Output audio format")
    
    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "input_path": "1/abc123.mp3",
                "model": "htdemucs",
                "two_stem": None,
                "output_format": "mp3"
            }
        }


class JobProgress(BaseModel):
    """Progress update for a running job."""
    job_id: str
    status: JobStatus
    progress: float = Field(default=0.0, ge=0.0, le=100.0, description="Progress percentage")
    current_step: str = Field(default="", description="Current processing step")
    

class JobResult(BaseModel):
    """Result of a completed separation job."""
    job_id: str
    status: JobStatus
    output_files: list[str] = Field(default_factory=list, description="List of output file paths")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")
    processing_time: Optional[float] = Field(default=None, description="Processing time in seconds")


class JobStatusResponse(BaseModel):
    """Response for job status query."""
    job_id: str
    status: JobStatus
    progress: float = 0.0
    current_step: str = ""
    output_files: list[str] = []
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class ModelInfo(BaseModel):
    """Information about an available model."""
    name: str
    description: str
    stems: list[str]
    supports_two_stem: bool = True


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    device: str
    queue_size: int
    active_jobs: int


class QueueStatusResponse(BaseModel):
    """Queue status response."""
    queue_size: int
    active_jobs: int
    max_concurrent: int
    can_accept_jobs: bool
