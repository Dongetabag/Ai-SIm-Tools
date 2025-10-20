#!/bin/bash

# Navigate to the application directory
cd "$(dirname "$0")"

echo "🔄 Restarting AISim Tools servers..."

# Kill any existing servers
echo "Stopping existing servers..."
pkill -f "uvicorn stem_separator_api" 2>/dev/null || true
pkill -f "python3 serve_frontend.py" 2>/dev/null || true

# Wait a moment
sleep 2

# Start FastAPI backend server
echo "Starting FastAPI backend server on http://localhost:8000..."
python3 -m uvicorn simplified_api:app --reload --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
BACKEND_PID=$!
echo "FastAPI backend PID: $BACKEND_PID"

# Start Python static frontend server
echo "Starting Python frontend server on http://localhost:8080..."
python3 serve_frontend.py > frontend.log 2>&1 &
FRONTEND_PID=$!
echo "Frontend server PID: $FRONTEND_PID"

echo "Waiting for servers to start..."
sleep 5

# Test if servers are running
echo "Testing servers..."
curl -s http://localhost:8000/ > /dev/null && echo "✅ Backend server is running" || echo "❌ Backend server failed"
curl -s http://localhost:8080/ > /dev/null && echo "✅ Frontend server is running" || echo "❌ Frontend server failed"

echo ""
echo "🎵 AISim Tools servers restarted!"
echo "📱 Frontend: http://localhost:8080/simplified_ui.html"
echo "🔗 API Server: http://localhost:8000"
echo ""

# Function to kill background processes on exit
cleanup() {
    echo "Stopping servers..."
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    echo "Servers stopped."
}

# Trap Ctrl+C and call cleanup function
trap cleanup SIGINT

# Keep the script running until Ctrl+C is pressed
echo "Press Ctrl+C to stop both servers"
wait $BACKEND_PID
wait $FRONTEND_PID
