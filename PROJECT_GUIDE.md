# Demucs Audio Separation Service - Complete Setup

## 🎵 What This Does

A containerized REST API service that separates audio files into individual tracks:
- **Vocals** - singing/speech
- **Drums** - percussion
- **Bass** - bass instruments
- **Other** - all other instruments

Built with FastAPI, Demucs AI model, and Docker for easy deployment.

---

## 📁 Project Structure

```
demucs/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── test_client.py       # Python test client
│   ├── requirements.txt     # Python dependencies
│   ├── dockerfile           # Container definition
│   ├── .dockerignore        # Build exclusions
│   └── README.md            # API documentation
├── docker-compose.yml       # Multi-service orchestration
└── frontend/                # (your frontend code)
```

---

## 🚀 Quick Start

### Option 1: Docker Compose (Recommended)

```bash
# Start the service
docker-compose up -d

# Check logs
docker-compose logs -f backend

# Stop the service
docker-compose down
```

### Option 2: Docker (Manual)

```bash
# Build
cd backend
docker build -t demucs-api .

# Run
docker run -d -p 8000:80 --name demucs-api demucs-api

# Check logs
docker logs -f demucs-api

# Stop
docker stop demucs-api
docker rm demucs-api
```

The API will be available at `http://localhost:8000`

---

## 🧪 Testing

### Using the Python Test Client

```bash
# Install requests library
pip install requests

# Run the test
python backend/test_client.py path/to/song.mp3

# Custom options
python backend/test_client.py song.mp3 --api-url http://localhost:8000 --output my_tracks.zip
```

### Using cURL

```bash
# 1. Upload a file
curl -X POST -F "file=@song.mp3" http://localhost:8000/upload

# Response includes job_id:
# {"job_id":"abc-123-def","status":"pending",...}

# 2. Check status (replace abc-123-def with your job_id)
curl http://localhost:8000/status/abc-123-def

# 3. Download when complete
curl -O -J http://localhost:8000/download/abc-123-def
```

### Using the Interactive Docs

Visit `http://localhost:8000/docs` for Swagger UI with built-in testing.

---

## 🔌 API Reference

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check |
| POST | `/upload` | Upload audio file |
| GET | `/status/{job_id}` | Get job status |
| GET | `/download/{job_id}` | Download result ZIP |
| GET | `/jobs` | List all jobs |
| DELETE | `/job/{job_id}` | Delete job & files |

### Upload Request

```bash
POST /upload
Content-Type: multipart/form-data
```

**Supported formats:** MP3, WAV, FLAC, OGG, M4A, AAC

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "filename": "song.mp3",
  "created_at": "2025-12-27T10:30:00"
}
```

### Status Check

```bash
GET /status/{job_id}
```

**Statuses:**
- `pending` - Queued for processing
- `processing` - Currently separating audio
- `completed` - Ready to download
- `failed` - Error occurred

### Download

```bash
GET /download/{job_id}
```

Returns a ZIP file containing 4 MP3 files (320kbps):
- `bass.mp3`
- `drums.mp3`
- `other.mp3`
- `vocals.mp3`

---

## ⚙️ Configuration

### Environment Variables

Set in `docker-compose.yml`:

```yaml
environment:
  - PYTHONUNBUFFERED=1  # Real-time logs
  # Add more as needed:
  # - MAX_FILE_SIZE=100MB
  # - DEMUCS_MODEL=htdemucs
```

### Volumes

Persistent storage for uploads and results:

```yaml
volumes:
  - demucs-completed:/app/completed  # Processed files
  - demucs-uploads:/app/uploads      # Temporary uploads
```

### Resource Limits

Add to `docker-compose.yml` for production:

```yaml
deploy:
  resources:
    limits:
      cpus: '4'
      memory: 8G
    reservations:
      cpus: '2'
      memory: 4G
```

---

## 🏗️ Architecture

### Request Flow

```
User → Upload MP3
      ↓
   FastAPI receives file
      ↓
   Generate unique job_id
      ↓
   Save to /app/uploads
      ↓
   Queue background task → Return job_id immediately
                              ↓
                           User polls /status
                              ↓
                         Background: Run Demucs
                              ↓
                         Create ZIP file
                              ↓
                         Status = completed
                              ↓
                         User downloads ZIP
```

### Directory Structure Inside Container

```
/app/
├── main.py
├── test_client.py
├── requirements.txt
├── uploads/         # Temporary uploaded files
│   └── {job_id}.mp3
├── temp/            # Demucs processing workspace
│   └── {job_id}/
│       └── htdemucs/{filename}/
│           ├── bass.mp3
│           ├── drums.mp3
│           ├── other.mp3
│           └── vocals.mp3
└── completed/       # Final ZIP files
    └── {job_id}.zip
```

---

## 🎯 Performance

### Processing Time

Typical separation times (CPU):
- 3-minute song: ~2-3 minutes
- 5-minute song: ~3-5 minutes

**With GPU:** 3-5x faster

### Enable GPU Support

Update `docker-compose.yml`:

```yaml
services:
  backend:
    # ... existing config ...
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

Requires: NVIDIA Docker runtime

---

## 🔒 Production Readiness

### Current State (MVP)

✅ Working REST API  
✅ Background processing  
✅ File upload/download  
✅ Docker containerized  
✅ Health checks  

### Recommended Additions

For production deployment:

1. **Persistent Job Storage**
   - Replace in-memory `jobs` dict with Redis or PostgreSQL
   - Survive container restarts

2. **Task Queue**
   - Use Celery + Redis for distributed processing
   - Scale workers independently

3. **Auto-cleanup**
   - Delete old jobs after 24-48 hours
   - Implement file TTL

4. **Security**
   - Add API key authentication
   - Rate limiting (e.g., 10 uploads/hour)
   - File size limits
   - Virus scanning

5. **Monitoring**
   - Prometheus metrics
   - Grafana dashboards
   - Error tracking (Sentry)

6. **Cloud Storage**
   - S3/GCS for uploads/results
   - Don't rely on container storage

---

## 🐛 Troubleshooting

### Container won't start

```bash
# Check logs
docker logs demucs-api

# Common issues:
# - Port 8000 already in use → Change port in docker-compose.yml
# - Out of memory → Increase Docker memory limit
```

### "Job not found" error

- Jobs are stored in memory only
- Restarting the container clears all jobs
- Use Redis in production

### Slow processing

- CPU-bound by default
- Enable GPU support for 3-5x speedup
- Consider pre-trained model caching

### Out of disk space

```bash
# Check volume usage
docker system df -v

# Clean up old data
docker volume rm demucs_demucs-completed
docker volume rm demucs_demucs-uploads
```

---

## 🔧 Development

### Local Development (without Docker)

```bash
cd backend

# Create venv
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install deps
pip install -r requirements.txt

# Run with hot reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Run Tests

```bash
# Test upload
python test_client.py ../shutup.flac

# Test API directly
curl http://localhost:8000/
curl -X POST -F "file=@test.mp3" http://localhost:8000/upload
```

---

## 📚 Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Web Framework | FastAPI | Async REST API |
| Server | Uvicorn | ASGI server |
| AI Model | Demucs | Audio separation |
| Audio Processing | FFmpeg | Format conversion |
| Container | Docker | Deployment |
| Orchestration | Docker Compose | Multi-service |

---

## 📄 License & Credits

- **Demucs**: https://github.com/facebookresearch/demucs
- **FastAPI**: https://fastapi.tiangolo.com/
- Your code: Customize as needed!

---

## 🎉 Next Steps

1. ✅ Build and test the API locally
2. ✅ Upload a sample audio file
3. ✅ Verify separated tracks quality
4. 🔜 Build frontend for user-friendly interface
5. 🔜 Deploy to cloud (AWS, GCP, Azure)
6. 🔜 Add authentication & payment
7. 🔜 Optimize for scale

**Happy separating!** 🎸🥁🎤🎹
