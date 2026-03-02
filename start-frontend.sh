#!/bin/bash
# Start frontend dev server
cd "$(dirname "$0")/frontend" || exit 1

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "[ERROR] Node.js not found. Please install Node.js 18+"
    exit 1
fi

# Install dependencies
if [ ! -d node_modules ]; then
    echo "[INFO] Installing frontend dependencies..."
    npm install
fi

# Start dev server
echo "[INFO] Starting frontend on http://localhost:3000"
npm run dev
