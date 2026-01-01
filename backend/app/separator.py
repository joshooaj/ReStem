"""
Demucs separation service using the CLI interface.

Demucs 4.0.x doesn't have a Python API module, so we use demucs.separate.main()
which provides the same functionality as the command line interface.
"""
import logging
import shutil
import tempfile
import time
from pathlib import Path
from typing import Optional, Callable, Dict, Any

import torch
import demucs.separate

from .config import settings
from .models import ModelChoice, StemChoice, OutputFormat

logger = logging.getLogger(__name__)

# Model information
MODEL_INFO = {
    ModelChoice.HTDEMUCS: {
        "name": "htdemucs",
        "description": "Hybrid Transformer Demucs - Fast with great quality",
        "stems": ["vocals", "drums", "bass", "other"],
    },
    ModelChoice.HTDEMUCS_FT: {
        "name": "htdemucs_ft",
        "description": "Fine-tuned Hybrid Transformer - Best quality, 4x slower",
        "stems": ["vocals", "drums", "bass", "other"],
    },
    ModelChoice.HTDEMUCS_6S: {
        "name": "htdemucs_6s", 
        "description": "6-stem model - Includes guitar and piano",
        "stems": ["vocals", "drums", "bass", "guitar", "piano", "other"],
    },
}


class SeparationService:
    """
    Service for separating audio using Demucs CLI interface.
    
    Since demucs 4.0.x doesn't have a Python API, we use demucs.separate.main()
    which provides the same functionality as the command line.
    """
    
    def __init__(self):
        self._device = settings.device
        
        # Check CUDA availability
        if self._device == "cuda" and not torch.cuda.is_available():
            logger.warning("CUDA requested but not available, falling back to CPU")
            self._device = "cpu"
        
        logger.info(f"SeparationService initialized with device: {self._device}")
    
    def separate(
        self,
        input_path: Path,
        output_dir: Path,
        model: ModelChoice = ModelChoice.HTDEMUCS,
        two_stem: Optional[StemChoice] = None,
        output_format: OutputFormat = OutputFormat.MP3,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> Dict[str, Path]:
        """
        Separate an audio file into stems using demucs CLI.
        
        Args:
            input_path: Path to the input audio file
            output_dir: Directory to save output files
            model: Demucs model to use
            two_stem: If set, perform two-stem separation isolating this stem
            output_format: Output format (mp3 or wav)
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dictionary mapping stem names to output file paths
        """
        start_time = time.time()
        
        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Starting CLI separation: {input_path} with model {model.value}, format {output_format.value}")
        
        # Build CLI arguments
        args = [
            "-n", model.value,
            "-d", self._device,
        ]
        
        # Output format
        if output_format == OutputFormat.MP3:
            args.append("--mp3")
            args.extend(["--mp3-bitrate", str(settings.mp3_bitrate)])
        
        # Add segment if specified (default for htdemucs is fine)
        if settings.segment:
            args.extend(["--segment", str(settings.segment)])
        
        # Add overlap
        if settings.overlap:
            args.extend(["--overlap", str(settings.overlap)])
        
        # Add shifts for better quality (but slower)
        if settings.shifts and settings.shifts > 0:
            args.extend(["--shifts", str(settings.shifts)])
        
        # Two-stem mode
        if two_stem:
            args.extend(["--two-stems", two_stem.value])
        
        # Use a temp directory for demucs output, then move files
        with tempfile.TemporaryDirectory() as temp_dir:
            args.extend(["-o", temp_dir])
            args.append(str(input_path))
            
            logger.info(f"Demucs CLI args: {args}")
            
            # Signal processing start
            if progress_callback:
                progress_callback({"progress": 10, "state": "processing"})
            
            # Run separation
            try:
                demucs.separate.main(args)
            except SystemExit as e:
                # demucs.separate.main() calls sys.exit(0) on success
                if e.code != 0 and e.code is not None:
                    raise RuntimeError(f"Demucs separation failed with exit code {e.code}")
            except Exception as e:
                logger.error(f"Separation failed: {e}")
                raise
            
            if progress_callback:
                progress_callback({"progress": 80, "state": "processing"})
            
            # Find and move output files
            # Demucs outputs to: temp_dir/model_name/track_name/stem.{wav,mp3}
            model_output_dir = Path(temp_dir) / model.value
            output_files: Dict[str, Path] = {}
            
            # Determine file extension based on format
            file_ext = ".mp3" if output_format == OutputFormat.MP3 else ".wav"
            
            if model_output_dir.exists():
                # Find the track directory (named after input file without extension)
                track_dirs = list(model_output_dir.iterdir())
                if track_dirs:
                    track_dir = track_dirs[0]
                    
                    for audio_file in track_dir.glob(f"*{file_ext}"):
                        stem_name = audio_file.stem
                        dest_path = output_dir / audio_file.name
                        shutil.copy2(audio_file, dest_path)
                        output_files[stem_name] = dest_path
                        logger.info(f"Copied {stem_name} to {dest_path}")
            
            if not output_files:
                raise RuntimeError(f"No output files found in {model_output_dir}")
            
            if progress_callback:
                progress_callback({"progress": 100, "state": "completed"})
            
            elapsed = time.time() - start_time
            logger.info(f"Separation complete in {elapsed:.2f}s: {list(output_files.keys())}")
            
            return output_files
    
    def get_model_info(self, model: ModelChoice) -> dict:
        """Get information about a model."""
        return MODEL_INFO.get(model, {})
    
    def list_models(self) -> list[dict]:
        """List all available models with their info."""
        return [
            {
                "id": model.value,
                **info,
                "supports_two_stem": True,
            }
            for model, info in MODEL_INFO.items()
        ]
    
    @property
    def device(self) -> str:
        """Return the current device."""
        return self._device
    
    def _simulate_separation(
        self,
        input_path: Path,
        output_dir: Path,
        model: ModelChoice,
        two_stem: Optional[StemChoice],
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> Dict[str, Path]:
        """
        Simulate separation when demucs isn't installed (for testing).
        Creates empty placeholder files.
        """
        logger.warning("SIMULATING separation - demucs not installed")
        
        # Simulate processing time
        for i in range(5):
            time.sleep(0.5)
            if progress_callback:
                progress_callback({"progress": (i + 1) * 20, "state": "processing"})
        
        # Get stems based on model
        model_info = MODEL_INFO.get(model, MODEL_INFO[ModelChoice.HTDEMUCS])
        stems = model_info["stems"]
        
        output_files: Dict[str, Path] = {}
        
        if two_stem:
            # Two-stem mode
            stem_name = two_stem.value
            stems_to_create = [stem_name, f"no_{stem_name}"]
        else:
            stems_to_create = stems
        
        # Create placeholder files
        for stem in stems_to_create:
            stem_path = output_dir / f"{stem}.wav"
            stem_path.touch()
            output_files[stem] = stem_path
            logger.info(f"Created placeholder: {stem_path}")
        
        return output_files


# Global service instance
separation_service = SeparationService()
