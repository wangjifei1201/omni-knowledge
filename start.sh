#!/bin/bash
# Start both backend and frontend
echo "========================================="
echo "  omni-knowledge - 智能知识库系统"
echo "========================================="
echo ""
echo "Starting services..."
echo ""

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Start backend in background
echo "[1/2] Starting backend..."
bash "$SCRIPT_DIR/start-backend.sh" &
BACKEND_PID=$!

# Wait for backend to be ready
sleep 3

# Start frontend in background
echo "[2/2] Starting frontend..."
bash "$SCRIPT_DIR/start-frontend.sh" &
FRONTEND_PID=$!

echo ""
echo "========================================="
echo "  Services started:"
echo "  Backend:  http://localhost:8000"
echo "  Frontend: http://localhost:3000"
echo "  API Docs: http://localhost:8000/docs"
echo "========================================="
echo ""
echo "Press Ctrl+C to stop all services."

# Handle shutdown
cleanup() {
    echo ""
    echo "Stopping services..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    wait
    echo "All services stopped."
}

trap cleanup EXIT INT TERM
wait
