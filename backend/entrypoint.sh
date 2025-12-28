#!/bin/bash
set -e

# Color output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting Demucs API...${NC}"

# Check if packages are already installed
if [ ! -f "/app/.packages_installed" ]; then
    echo -e "${YELLOW}📦 First run detected - installing dependencies...${NC}"
    
    # Check if CPU-only mode is requested
    if [ "${USE_CPU}" = "1" ]; then
        echo -e "${YELLOW}   Installing CPU-only PyTorch (faster download, ~200MB)${NC}"
        echo -e "${YELLOW}   This will take 1-2 minutes but only happens once.${NC}"
        pip install --cache-dir=/app/pip-cache \
            --index-url https://download.pytorch.org/whl/cpu \
            torch==2.5.1+cpu torchaudio==2.5.1+cpu
        pip install --cache-dir=/app/pip-cache -r /app/requirements.txt
    else
        echo -e "${YELLOW}   Installing GPU-enabled PyTorch (larger download, ~2GB)${NC}"
        echo -e "${YELLOW}   This will take 2-3 minutes but only happens once.${NC}"
        pip install --cache-dir=/app/pip-cache -r /app/requirements.txt
    fi
    
    # Mark as installed
    touch /app/.packages_installed
    
    echo -e "${GREEN}✅ Dependencies installed successfully!${NC}"
else
    echo -e "${GREEN}✅ Using cached dependencies${NC}"
fi

# Start the application
echo -e "${GREEN}🎵 Starting API server on port 80...${NC}"
exec uvicorn main:app --host 0.0.0.0 --port 80
