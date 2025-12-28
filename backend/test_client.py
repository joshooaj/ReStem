#!/usr/bin/env python3
"""
Test client for the Demucs API

Requirements:
    pip install requests

Usage:
    python test_client.py audio_file.mp3
    python test_client.py audio_file.mp3 --api-url http://localhost:8000
"""

import argparse
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    print("❌ Error: 'requests' module not found")
    print("   Install it with: pip install requests")
    print("   Or: pip install -r requirements-dev.txt")
    sys.exit(1)


def upload_file(api_url: str, file_path: Path) -> str:
    """Upload audio file and return job_id"""
    print(f"📤 Uploading {file_path.name}...")
    
    with open(file_path, 'rb') as f:
        response = requests.post(
            f"{api_url}/upload",
            files={'file': ('audio.mp3', f, 'audio/mpeg')}
        )
    
    if response.status_code != 200:
        print(f"❌ Upload failed: {response.text}")
        sys.exit(1)
    
    job = response.json()
    job_id = job['job_id']
    print(f"✅ Upload successful! Job ID: {job_id}")
    return job_id


def wait_for_completion(api_url: str, job_id: str, poll_interval: int = 5):
    """Poll job status until completion"""
    print(f"⏳ Waiting for processing to complete...")
    
    while True:
        response = requests.get(f"{api_url}/status/{job_id}")
        
        if response.status_code != 200:
            print(f"❌ Status check failed: {response.text}")
            sys.exit(1)
        
        status = response.json()
        current_status = status['status']
        
        if current_status == 'completed':
            print(f"✅ Processing completed!")
            return status
        elif current_status == 'failed':
            error = status.get('error', 'Unknown error')
            print(f"❌ Processing failed: {error}")
            sys.exit(1)
        else:
            print(f"   Status: {current_status}...")
            time.sleep(poll_interval)


def download_result(api_url: str, job_id: str, output_path: Path):
    """Download the separated tracks ZIP file"""
    print(f"📥 Downloading separated tracks...")
    
    response = requests.get(f"{api_url}/download/{job_id}", stream=True)
    
    if response.status_code != 200:
        print(f"❌ Download failed: {response.text}")
        sys.exit(1)
    
    with open(output_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    
    print(f"✅ Download complete: {output_path}")
    print(f"   File size: {output_path.stat().st_size / 1024 / 1024:.2f} MB")


def main():
    parser = argparse.ArgumentParser(
        description="Test client for Demucs Audio Separation API"
    )
    parser.add_argument(
        "audio_file",
        type=Path,
        help="Path to audio file (MP3, WAV, FLAC, etc.)"
    )
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="API base URL (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output ZIP file path (default: <filename>_separated.zip)"
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=5,
        help="Status polling interval in seconds (default: 5)"
    )
    
    args = parser.parse_args()
    
    # Validate input file
    if not args.audio_file.exists():
        print(f"❌ File not found: {args.audio_file}")
        sys.exit(1)
    
    # Set default output path
    if args.output is None:
        args.output = Path(f"{args.audio_file.stem}_separated.zip")
    
    print("🎵 Demucs Audio Separation API Test")
    print("=" * 50)
    
    # Step 1: Upload
    job_id = upload_file(args.api_url, args.audio_file)
    
    # Step 2: Wait for completion
    job_status = wait_for_completion(args.api_url, job_id, args.poll_interval)
    
    # Step 3: Download
    download_result(args.api_url, job_id, args.output)
    
    print("\n" + "=" * 50)
    print("🎉 All done! Your separated tracks are ready.")
    print(f"   Extract the ZIP file to access:")
    print(f"   - bass.mp3")
    print(f"   - drums.mp3")
    print(f"   - other.mp3")
    print(f"   - vocals.mp3")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
