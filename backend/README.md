# Demucs Audio Separation API

## Quick Start

### Build and Run with Docker

```bash
# Build the image
docker build -t demucs-api ./backend

# Run the container
docker run -d -p 8000:80 --name demucs-api demucs-api

# Or with docker-compose (recommended)
docker-compose up -d
```

## API Endpoints

### 1. Health Check
```bash
GET /
```

### 2. Upload Audio File
```bash
POST /upload
Content-Type: multipart/form-data

# Example with curl
curl -X POST -F "file=@song.mp3" http://localhost:8000/upload
```

Response:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "filename": "song.mp3",
  "created_at": "2025-12-27T10:30:00",
  "completed_at": null,
  "error": null,
  "download_url": null
}
```

### 3. Check Job Status
```bash
GET /status/{job_id}

# Example
curl http://localhost:8000/status/550e8400-e29b-41d4-a716-446655440000
```

Response (completed):
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "filename": "song.mp3",
  "created_at": "2025-12-27T10:30:00",
  "completed_at": "2025-12-27T10:33:45",
  "error": null,
  "download_url": "/download/550e8400-e29b-41d4-a716-446655440000"
}
```

### 4. Download Separated Tracks
```bash
GET /download/{job_id}

# Example
curl -O -J http://localhost:8000/download/550e8400-e29b-41d4-a716-446655440000
```

Downloads a ZIP file containing:
- `bass.mp3` - Bass track
- `drums.mp3` - Drums track
- `other.mp3` - Other instruments
- `vocals.mp3` - Vocals track

### 5. List All Jobs
```bash
GET /jobs
```

### 6. Delete Job
```bash
DELETE /job/{job_id}
```

## Supported Audio Formats

- MP3 (`.mp3`)
- WAV (`.wav`)
- FLAC (`.flac`)
- OGG (`.ogg`)
- M4A (`.m4a`)
- AAC (`.aac`)

## Development

### Run Locally (without Docker)

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Interactive API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Architecture

- **FastAPI**: Modern async web framework
- **Demucs**: State-of-the-art audio source separation
- **Background Tasks**: Long-running separations don't block API
- **File Storage**: Uploads, processing, and completed files in separate directories

## Processing Time

Audio separation typically takes 1-3 minutes per song depending on:
- Song length
- Server CPU/GPU resources
- Demucs model quality settings

## Production Considerations

For production deployment, consider:

1. **Persistent Storage**: Use Docker volumes or cloud storage for `/app/completed`
2. **Job Persistence**: Replace in-memory `jobs` dict with Redis or database
3. **Queue System**: Use Celery + Redis for distributed task processing
4. **Auto-cleanup**: Implement TTL for completed jobs
5. **Rate Limiting**: Add rate limiting to prevent abuse
6. **Authentication**: Add API key or OAuth authentication
7. **GPU Support**: Use NVIDIA Docker runtime for faster processing
8. **Monitoring**: Add Prometheus metrics and health checks

## Example Workflow

```python
import requests
import time

# 1. Upload file
with open('song.mp3', 'rb') as f:
    response = requests.post('http://localhost:8000/upload', files={'file': f})
    job = response.json()
    job_id = job['job_id']
    print(f"Job created: {job_id}")

# 2. Poll for completion
while True:
    response = requests.get(f'http://localhost:8000/status/{job_id}')
    status = response.json()
    print(f"Status: {status['status']}")
    
    if status['status'] == 'completed':
        break
    elif status['status'] == 'failed':
        print(f"Error: {status['error']}")
        exit(1)
    
    time.sleep(5)  # Check every 5 seconds

# 3. Download result
response = requests.get(f'http://localhost:8000/download/{job_id}')
with open('separated_tracks.zip', 'wb') as f:
    f.write(response.content)
    print("Download complete!")
```
