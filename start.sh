#!/bin/bash
# ============================================================
# One-Click Launch Script for AI Customer Support Agent
# ============================================================

set -e

echo "============================================================"
echo "🚀 Starting AI Support Resolution Agent System"
echo "============================================================"

# Check if .env exists in backend
if [ ! -f "backend/.env" ]; then
    if [ -f "backend/.env.example" ]; then
        echo "⚠️  backend/.env not found. Creating from .env.example..."
        cp backend/.env.example backend/.env
        echo "❗ Please add your GEMINI_API_KEY in backend/.env before continuing."
        exit 1
    fi
fi

# Function to kill child processes on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down services..."
    kill $(jobs -p) 2>/dev/null || true
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# Start Backend
echo "📦 Starting Backend on port 8000..."
cd backend
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
else
    source venv/bin/activate
fi
uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!
cd ..

# Wait for backend to be ready
echo "⏳ Waiting for backend to initialize..."
sleep 3

# Start Frontend
echo "💻 Starting Frontend on port 5173..."
cd frontend
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "============================================================"
echo "🎉 SYSTEM RUNNING!"
echo "👉 Web App:  http://localhost:5173"
echo "👉 API Docs: http://localhost:8000/docs"
echo "============================================================"
echo "Press Ctrl+C to stop all services."
echo ""

# Keep running
wait
