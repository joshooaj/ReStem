# 🚀 Quick Start Guide

## Step 1: Build & Start the Service

```powershell
# From the demucs directory
docker-compose up -d
```

Wait ~2 minutes for the build to complete the first time.

## Step 2: Verify It's Running

```powershell
# Check the service is healthy
curl http://localhost:8000/

# Or open in browser
start http://localhost:8000/docs
```

You should see the interactive API documentation.

## Step 3: Test with Your Audio File

### Option A: Use the Web UI (Easiest)

1. Open `frontend/index.html` in your browser
2. Drag & drop an MP3 file
3. Click "Upload & Process"
4. Wait 2-5 minutes
5. Download the ZIP with separated tracks!

### Option B: Use the Python Test Client

```powershell
# Install requests if needed
pip install requests

# Run the test
python backend/test_client.py path/to/your/song.mp3
```

### Option C: Use cURL

```powershell
# 1. Upload
$response = curl.exe -X POST -F "file=@song.mp3" http://localhost:8000/upload | ConvertFrom-Json
$jobId = $response.job_id
Write-Host "Job ID: $jobId"

# 2. Check status (repeat until completed)
curl.exe http://localhost:8000/status/$jobId

# 3. Download when ready
curl.exe -o separated.zip http://localhost:8000/download/$jobId
```

## Step 4: Extract & Listen

Unzip the downloaded file to get:
- **vocals.mp3** - singing/speech only
- **drums.mp3** - percussion only
- **bass.mp3** - bass instruments only
- **other.mp3** - everything else

## Troubleshooting

**Port already in use?**
```powershell
# Edit docker-compose.yml and change port:
# ports:
#   - "8080:80"  # Use 8080 instead
```

**Container won't start?**
```powershell
# Check logs
docker-compose logs -f backend

# Rebuild
docker-compose down
docker-compose up --build -d
```

**Out of memory?**
- Increase Docker Desktop memory limit (Settings → Resources)
- Minimum recommended: 6GB RAM

## What's Next?

- Customize the frontend styling
- Add authentication to the API
- Deploy to AWS/GCP/Azure
- Add a database for job persistence
- Implement webhook notifications

Enjoy! 🎵
