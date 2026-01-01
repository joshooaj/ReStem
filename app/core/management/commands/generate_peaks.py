"""
Django management command to generate waveform peak data for audio files.

This generates small JSON files containing pre-computed waveform peaks,
allowing the web player to render waveforms without downloading full audio files.
Audio is only downloaded when the user clicks play.

Usage:
    python manage.py generate_peaks
    python manage.py generate_peaks --input static/demo --output static/demo/peaks
    python manage.py generate_peaks --samples 800
"""

import json
import os
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

# Audio processing - try multiple backends
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    from pydub import AudioSegment
    HAS_PYDUB = True
except ImportError:
    HAS_PYDUB = False

try:
    import librosa
    HAS_LIBROSA = True
except ImportError:
    HAS_LIBROSA = False


class Command(BaseCommand):
    help = 'Generate waveform peak data for audio files'

    def add_arguments(self, parser):
        parser.add_argument(
            '--input',
            type=str,
            default='static/demo',
            help='Input directory containing audio files (relative to app dir)'
        )
        parser.add_argument(
            '--output',
            type=str,
            default=None,
            help='Output directory for peaks JSON files (defaults to input/peaks)'
        )
        parser.add_argument(
            '--samples',
            type=int,
            default=800,
            help='Number of peak samples to generate (default: 800)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Overwrite existing peak files'
        )

    def handle(self, *args, **options):
        if not HAS_NUMPY:
            self.stderr.write(self.style.ERROR(
                'numpy is required. Install with: pip install numpy'
            ))
            return

        if not HAS_PYDUB and not HAS_LIBROSA:
            self.stderr.write(self.style.ERROR(
                'Either pydub or librosa is required.\n'
                'Install with: pip install pydub\n'
                'Or: pip install librosa'
            ))
            return

        # Resolve paths
        base_dir = Path(settings.BASE_DIR)
        input_dir = base_dir / options['input']
        output_dir = Path(options['output']) if options['output'] else input_dir / 'peaks'
        num_samples = options['samples']
        force = options['force']

        if not input_dir.exists():
            self.stderr.write(self.style.ERROR(f'Input directory not found: {input_dir}'))
            return

        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        # Find audio files
        audio_extensions = {'.mp3', '.wav', '.ogg', '.flac', '.m4a', '.aac'}
        audio_files = [
            f for f in input_dir.iterdir()
            if f.is_file() and f.suffix.lower() in audio_extensions
        ]

        if not audio_files:
            self.stdout.write(self.style.WARNING(f'No audio files found in {input_dir}'))
            return

        self.stdout.write(f'Found {len(audio_files)} audio file(s)')
        self.stdout.write(f'Output directory: {output_dir}')
        self.stdout.write(f'Samples per file: {num_samples}')
        self.stdout.write('')

        for audio_file in audio_files:
            output_file = output_dir / f'{audio_file.stem}.json'

            if output_file.exists() and not force:
                self.stdout.write(f'  Skipping {audio_file.name} (peaks exist, use --force to overwrite)')
                continue

            self.stdout.write(f'  Processing {audio_file.name}...')

            try:
                peaks, duration = self.generate_peaks(audio_file, num_samples)
                
                # Save as JSON
                peaks_data = {
                    'peaks': peaks,
                    'duration': round(duration, 3),
                    'samples': num_samples,
                    'source': audio_file.name
                }
                
                with open(output_file, 'w') as f:
                    json.dump(peaks_data, f)
                
                # Report file sizes
                audio_size = audio_file.stat().st_size / 1024
                peaks_size = output_file.stat().st_size / 1024
                savings = (1 - peaks_size / audio_size) * 100
                
                self.stdout.write(self.style.SUCCESS(
                    f'    ✓ Created {output_file.name} '
                    f'({peaks_size:.1f}KB vs {audio_size:.0f}KB audio, {savings:.0f}% smaller)'
                ))

            except Exception as e:
                self.stderr.write(self.style.ERROR(f'    ✗ Error: {e}'))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Done!'))

    def generate_peaks(self, audio_path: Path, num_samples: int) -> tuple[list[float], float]:
        """Generate normalized peak data from an audio file."""
        
        if HAS_LIBROSA:
            return self._generate_peaks_librosa(audio_path, num_samples)
        else:
            return self._generate_peaks_pydub(audio_path, num_samples)

    def _generate_peaks_librosa(self, audio_path: Path, num_samples: int) -> tuple[list[float], float]:
        """Generate peaks using librosa (higher quality)."""
        # Load audio file
        y, sr = librosa.load(str(audio_path), sr=None, mono=True)
        duration = len(y) / sr
        
        # Calculate samples per peak
        samples_per_peak = len(y) // num_samples
        
        peaks = []
        for i in range(num_samples):
            start = i * samples_per_peak
            end = start + samples_per_peak
            chunk = y[start:end]
            
            if len(chunk) > 0:
                # Use RMS for smoother waveform
                peak = float(np.sqrt(np.mean(chunk ** 2)))
            else:
                peak = 0.0
            peaks.append(peak)
        
        # Normalize to 0-1 range
        max_peak = max(peaks) if peaks else 1
        if max_peak > 0:
            peaks = [p / max_peak for p in peaks]
        
        return peaks, duration

    def _generate_peaks_pydub(self, audio_path: Path, num_samples: int) -> tuple[list[float], float]:
        """Generate peaks using pydub (more compatible)."""
        # Load audio file
        audio = AudioSegment.from_file(str(audio_path))
        
        # Convert to mono
        if audio.channels > 1:
            audio = audio.set_channels(1)
        
        duration = len(audio) / 1000.0  # pydub uses milliseconds
        
        # Get raw samples
        samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
        
        # Normalize samples
        max_val = np.max(np.abs(samples))
        if max_val > 0:
            samples = samples / max_val
        
        # Calculate samples per peak
        samples_per_peak = len(samples) // num_samples
        
        peaks = []
        for i in range(num_samples):
            start = i * samples_per_peak
            end = start + samples_per_peak
            chunk = samples[start:end]
            
            if len(chunk) > 0:
                # Use RMS for smoother waveform
                peak = float(np.sqrt(np.mean(chunk ** 2)))
            else:
                peak = 0.0
            peaks.append(peak)
        
        # Normalize to 0-1 range
        max_peak = max(peaks) if peaks else 1
        if max_peak > 0:
            peaks = [p / max_peak for p in peaks]
        
        return peaks, duration
