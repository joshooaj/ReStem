# 📦 Optimized Docker Setup

## How It Works

Instead of bundling all packages in the Docker image (12GB+), this setup:

1. **Base image**: ~500MB (Python + FFmpeg only)
2. **First startup**: Downloads & installs PyTorch and dependencies (~2-3 minutes)
3. **Cached to volume**: Subsequent starts are fast (<10 seconds)

## Quick Start

```powershell
# Build the small base image
docker compose build

# First run - will install packages (takes 2-3 minutes)
docker compose up -d

# Watch the installation progress
docker compose logs -f backend

# Subsequent runs are fast!
docker compose restart backend
```

## Image Sizes

- **Base image**: ~835MB (Python 3.11 + FFmpeg + code)
- **With CPU-only PyTorch**: ~1.5GB total (cached in volume)
- **With GPU PyTorch** (default): ~8GB total (includes CUDA libraries)

## Switching Between CPU and GPU

By default, **GPU support is enabled**. To use CPU-only mode (smaller, faster download):

**Option 1: Environment variable (recommended)**

Edit `docker-compose.yml` and uncomment:
```yaml
environment:
  - USE_CPU=1
```

**Option 2: Edit requirements.txt**

Change the PyTorch lines to:
```
--extra-index-url https://download.pytorch.org/whl/cpu
torch==2.5.1+cpu
torchaudio==2.5.1+cpu
```

Then rebuild:
```powershell
docker compose down -v  # Remove volumes to force reinstall
docker compose up -d
```

## Volumes

Three volumes persist data:

- `demucs-pip-cache`: Downloaded packages (2-7GB)
- `demucs-completed`: Processed audio files
- `demucs-uploads`: Temporary uploads

## Publishing to Docker Hub

The base image is now small enough to publish:

```powershell
# Build and tag
docker build -t yourusername/demucs-api:latest ./backend

# Size check
docker images yourusername/demucs-api

# Push to Docker Hub
docker push yourusername/demucs-api:latest
```

Users will download the ~500MB image and packages install on first run.

## Clean Up

Remove all volumes (forces fresh package install):
```powershell
docker compose down -v
```

## Benefits

✅ **Small image**: Easy to publish and pull  
✅ **Flexible**: Choose CPU or GPU at runtime  
✅ **Fast updates**: Rebuild image in seconds  
✅ **Cached**: First install is slow, then fast forever  
