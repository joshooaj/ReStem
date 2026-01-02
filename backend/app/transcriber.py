"""
Whisper transcription service for speech-to-text processing.

This service provides transcription capabilities using OpenAI's Whisper model.
"""
import logging
import json
import time
from pathlib import Path
from typing import Optional, Callable, Dict, Any
from datetime import timedelta

import whisper
import torch

from .config import settings
from .models import TranscriptionType, TranscriptionFormat

logger = logging.getLogger(__name__)

# Transcription types that require word-level timestamps
TIMESTAMP_REQUIRED_TYPES = {
    TranscriptionType.TIMESTAMPED,
    TranscriptionType.SUBTITLES,
    TranscriptionType.LYRICS,
}


def format_timestamp(seconds: float) -> str:
    """
    Format seconds into HH:MM:SS,mmm format for SRT.
    
    Args:
        seconds: Time in seconds
        
    Returns:
        Formatted timestamp string
    """
    td = timedelta(seconds=seconds)
    hours = int(td.total_seconds() // 3600)
    minutes = int((td.total_seconds() % 3600) // 60)
    secs = int(td.total_seconds() % 60)
    millis = int((td.total_seconds() % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def format_timestamp_lrc(seconds: float) -> str:
    """
    Format seconds into [MM:SS.xx] format for LRC files.
    
    Args:
        seconds: Time in seconds
        
    Returns:
        Formatted timestamp string
    """
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"[{minutes:02d}:{secs:05.2f}]"


class TranscriptionService:
    """
    Service for transcribing audio/video using Whisper.
    
    Supports multiple output formats including plain text, timestamped JSON,
    SRT/VTT subtitles, and LRC lyrics files.
    """
    
    def __init__(self, model_name: str = "base"):
        """
        Initialize the transcription service.
        
        Args:
            model_name: Whisper model size (tiny, base, small, medium, large)
        """
        self._device = settings.device
        self._model_name = model_name
        self._model = None
        
        # Check CUDA availability
        if self._device == "cuda" and not torch.cuda.is_available():
            logger.warning("CUDA requested but not available, falling back to CPU")
            self._device = "cpu"
        
        logger.info(f"TranscriptionService initialized with device: {self._device}, model: {model_name}")
    
    def _load_model(self):
        """Load the Whisper model if not already loaded."""
        if self._model is None:
            logger.info(f"Loading Whisper model: {self._model_name}")
            self._model = whisper.load_model(self._model_name, device=self._device)
            logger.info("Whisper model loaded successfully")
    
    def transcribe(
        self,
        input_path: Path,
        output_dir: Path,
        transcription_type: TranscriptionType = TranscriptionType.BASIC,
        transcription_format: TranscriptionFormat = TranscriptionFormat.TEXT,
        language: Optional[str] = None,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> Dict[str, Path]:
        """
        Transcribe an audio/video file using Whisper.
        
        Args:
            input_path: Path to the input audio/video file
            output_dir: Directory to save output files
            transcription_type: Type of transcription to perform
            transcription_format: Output format
            language: Language code (e.g., 'en', 'es'). None for auto-detect
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dictionary mapping output type to file path
        """
        start_time = time.time()
        
        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Starting transcription: {input_path} with type {transcription_type.value}")
        
        # Load model
        if progress_callback:
            progress_callback({"progress": 10, "state": "loading_model"})
        
        self._load_model()
        
        if progress_callback:
            progress_callback({"progress": 20, "state": "transcribing"})
        
        # Transcribe the audio
        try:
            transcribe_options = {
                "verbose": False,
            }
            
            # Set language if specified
            if language:
                transcribe_options["language"] = language
            
            # Enable word-level timestamps for timestamped types
            if transcription_type in TIMESTAMP_REQUIRED_TYPES:
                transcribe_options["word_timestamps"] = True
            
            result = self._model.transcribe(str(input_path), **transcribe_options)
            
            if progress_callback:
                progress_callback({"progress": 70, "state": "formatting"})
            
            # Format and save output based on type
            output_files = self._format_output(
                result=result,
                output_dir=output_dir,
                transcription_type=transcription_type,
                transcription_format=transcription_format,
            )
            
            if progress_callback:
                progress_callback({"progress": 100, "state": "completed"})
            
            elapsed = time.time() - start_time
            logger.info(f"Transcription complete in {elapsed:.2f}s")
            
            return output_files
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise
    
    def _format_output(
        self,
        result: dict,
        output_dir: Path,
        transcription_type: TranscriptionType,
        transcription_format: TranscriptionFormat,
    ) -> Dict[str, Path]:
        """
        Format transcription result and save to file(s).
        
        Args:
            result: Whisper transcription result
            output_dir: Directory to save output files
            transcription_type: Type of transcription
            transcription_format: Output format
            
        Returns:
            Dictionary mapping output type to file path
        """
        output_files = {}
        
        if transcription_type == TranscriptionType.BASIC:
            # Plain text transcription
            output_path = output_dir / f"transcription.{transcription_format.value}"
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(result["text"].strip())
            output_files["transcription"] = output_path
            
        elif transcription_type == TranscriptionType.TIMESTAMPED:
            # JSON with timestamps
            output_path = output_dir / "transcription.json"
            
            # Extract segments with timestamps
            segments = []
            for segment in result.get("segments", []):
                segments.append({
                    "start": segment["start"],
                    "end": segment["end"],
                    "text": segment["text"].strip(),
                })
            
            data = {
                "text": result["text"].strip(),
                "language": result.get("language", "unknown"),
                "segments": segments,
            }
            
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            output_files["transcription"] = output_path
            
        elif transcription_type == TranscriptionType.SUBTITLES:
            # SRT or VTT subtitle files
            if transcription_format == TranscriptionFormat.SRT:
                output_path = output_dir / "subtitles.srt"
                self._write_srt(result, output_path)
            else:  # VTT
                output_path = output_dir / "subtitles.vtt"
                self._write_vtt(result, output_path)
            
            output_files["subtitles"] = output_path
            
        elif transcription_type == TranscriptionType.LYRICS:
            # LRC lyrics file
            output_path = output_dir / "lyrics.lrc"
            self._write_lrc(result, output_path)
            output_files["lyrics"] = output_path
        
        logger.info(f"Created output files: {list(output_files.keys())}")
        return output_files
    
    def _write_srt(self, result: dict, output_path: Path):
        """Write transcription as SRT subtitle file."""
        with open(output_path, "w", encoding="utf-8") as f:
            for i, segment in enumerate(result.get("segments", []), start=1):
                start = format_timestamp(segment["start"])
                end = format_timestamp(segment["end"])
                text = segment["text"].strip()
                
                f.write(f"{i}\n")
                f.write(f"{start} --> {end}\n")
                f.write(f"{text}\n\n")
    
    def _write_vtt(self, result: dict, output_path: Path):
        """Write transcription as WebVTT subtitle file."""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("WEBVTT\n\n")
            
            for segment in result.get("segments", []):
                start = format_timestamp(segment["start"]).replace(',', '.')
                end = format_timestamp(segment["end"]).replace(',', '.')
                text = segment["text"].strip()
                
                f.write(f"{start} --> {end}\n")
                f.write(f"{text}\n\n")
    
    def _write_lrc(self, result: dict, output_path: Path):
        """Write transcription as LRC lyrics file."""
        with open(output_path, "w", encoding="utf-8") as f:
            # Write metadata
            f.write("[ti:Transcribed Lyrics]\n")
            f.write("[ar:Unknown Artist]\n")
            f.write("[by:Mux Minus]\n")
            f.write("\n")
            
            # Write timestamped lyrics
            for segment in result.get("segments", []):
                timestamp = format_timestamp_lrc(segment["start"])
                text = segment["text"].strip()
                f.write(f"{timestamp} {text}\n")
    
    @property
    def device(self) -> str:
        """Return the current device."""
        return self._device


# Global service instance
transcription_service = TranscriptionService(model_name=settings.whisper_model)
