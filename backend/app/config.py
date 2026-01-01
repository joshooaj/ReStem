"""
Configuration settings for the backend service.
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Literal


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    
    # File paths (relative to shared volume)
    uploads_dir: Path = Path("/data/uploads")
    outputs_dir: Path = Path("/data/outputs")
    temp_dir: Path = Path("/data/temp")
    
    # Job processing settings
    max_concurrent_jobs: int = 2
    max_queue_size: int = 50
    
    # Demucs settings
    default_model: str = "htdemucs"
    device: Literal["cuda", "cpu"] = "cpu"
    segment: int | None = None  # None = auto
    shifts: int = 1  # Number of random shifts for quality
    overlap: float = 0.25
    jobs: int = 0  # Parallel jobs per separation (0 = auto)
    
    # Output settings
    output_format: Literal["wav", "mp3"] = "mp3"
    mp3_bitrate: int = 320
    
    # API settings
    api_key: str | None = None  # Optional API key for internal auth
    
    class Config:
        env_prefix = "MUXMINUS_"
        env_file = ".env"


# Global settings instance
settings = Settings()


def ensure_directories():
    """Create required directories if they don't exist."""
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    settings.outputs_dir.mkdir(parents=True, exist_ok=True)
    settings.temp_dir.mkdir(parents=True, exist_ok=True)
