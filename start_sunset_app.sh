#!/bin/bash

echo "🌅 Starting AI Stem Separator with Beautiful Sunset UI"
echo "======================================================"
echo ""

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3."
    exit 1
fi

# Check if dependencies are installed
echo "🔍 Checking dependencies..."
python3 -c "import demucs, fastapi, uvicorn" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "📦 Installing dependencies..."
    pip3 install -r requirements.txt
fi

echo ""
echo "🚀 Starting servers..."
echo "📡 API Server: http://localhost:8000"
echo "🌅 Sunset UI: http://localhost:8080"
echo "🛑 Press Ctrl+C to stop both servers"
echo ""

# Function to cleanup background processes
cleanup() {
    echo ""
    echo "🛑 Shutting down servers..."
    kill $API_PID $FRONTEND_PID 2>/dev/null
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Start API server in background
echo "🔧 Starting API server..."
python3 -m uvicorn stem_separator_api:app --host 0.0.0.0 --port 8000 &
API_PID=$!

# Wait a moment for API server to start
sleep 2

# Start frontend server in background
echo "🎨 Starting Sunset UI server..."
python3 serve_frontend.py &
FRONTEND_PID=$!

# Wait a moment and open browser
sleep 3
echo ""
echo "🌐 Opening browser..."
if command -v open &> /dev/null; then
    open http://localhost:8080
elif command -v xdg-open &> /dev/null; then
    xdg-open http://localhost:8080
else
    echo "📱 Please open http://localhost:8080 in your browser"
fi

echo ""
echo "✅ Both servers are running!"
echo "🎵 Your beautiful sunset AI stem separator is ready!"
echo ""
echo "📱 Frontend: http://localhost:8080"
echo "📡 API: http://localhost:8000"
echo "📚 API Docs: http://localhost:8000/docs"
echo ""

# Wait for user to stop
wait
