#!/bin/bash
# Start backend server
cd "$(dirname "$0")/backend" || exit 1

# Create .env from example if not exists
if [ ! -f .env ]; then
    cp .env.example .env
    echo "[INFO] Created .env from .env.example"
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] python3 not found. Please install Python 3.10+"
    exit 1
fi

# Install dependencies
echo "[INFO] Installing backend dependencies..."
pip install -r requirements.txt -i http://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com -q

# Start server
echo "[INFO] Starting backend on http://localhost:8000"
python3 -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
