#!/bin/bash

# AISim Tools - Startup Script
# This script starts the AI-Enhanced API server and frontend on non-conflicting ports
# API: http://localhost:8001
# Frontend: http://localhost:8081

set -e

echo "🚀 Starting AISim Tools..."
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check for required commands
echo "📋 Checking prerequisites..."

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 is not installed${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} Python3: $(python3 --version)"

# Check FFmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo -e "${YELLOW}⚠️  FFmpeg is not installed (required for audio/video processing)${NC}"
    echo "   Install with: sudo apt-get install ffmpeg (Ubuntu/Debian)"
    echo "   or: brew install ffmpeg (macOS)"
    echo ""
    echo -e "${YELLOW}   Continuing without FFmpeg - some features may not work${NC}"
else
    echo -e "${GREEN}✓${NC} FFmpeg: $(ffmpeg -version | head -1 | cut -d' ' -f3)"
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo ""
    echo -e "${YELLOW}⚠️  Virtual environment not found. Creating one...${NC}"
    python3 -m venv venv
    echo -e "${GREEN}✓${NC} Virtual environment created"
fi

# Activate virtual environment
echo ""
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Check and install dependencies
echo ""
echo "📦 Checking Python dependencies..."
if ! python3 -c "import fastapi" &> /dev/null; then
    echo -e "${YELLOW}⚠️  Dependencies not installed. Installing...${NC}"
    pip install -q -r requirements.txt
    echo -e "${GREEN}✓${NC} Dependencies installed"
else
    echo -e "${GREEN}✓${NC} Dependencies already installed"
fi

# Create output directory
mkdir -p output
echo -e "${GREEN}✓${NC} Output directory ready"

# Check for API keys
echo ""
echo "🔑 Checking API keys..."
if [ -f .env ]; then
    source .env
    echo -e "${GREEN}✓${NC} .env file found"
else
    echo -e "${YELLOW}⚠️  .env file not found${NC}"
    echo "   Create a .env file with your API keys:"
    echo "   OPENAI_API_KEY=your-key-here"
    echo "   GOOGLE_API_KEY=your-key-here"
    echo "   ANTHROPIC_API_KEY=your-key-here"
fi

# Kill any existing servers on ports 8001 and 8081
echo ""
echo "🧹 Cleaning up existing servers..."
lsof -ti:8001 | xargs kill -9 2>/dev/null || true
lsof -ti:8081 | xargs kill -9 2>/dev/null || true
sleep 1

# Start the API server in background
echo ""
echo "🎵 Starting API server on port 8001..."
python3 ai_enhanced_api.py > api_server.log 2>&1 &
API_PID=$!
echo -e "${GREEN}✓${NC} API server started (PID: $API_PID)"

# Wait for API to be ready
echo "⏳ Waiting for API to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:8001/ > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} API server is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}❌ API server failed to start${NC}"
        echo "Check api_server.log for details"
        kill $API_PID 2>/dev/null || true
        exit 1
    fi
    sleep 1
done

# Start the frontend server in background
echo ""
echo "🌐 Starting frontend server on port 8081..."
python3 serve_frontend.py > frontend_server.log 2>&1 &
FRONTEND_PID=$!
echo -e "${GREEN}✓${NC} Frontend server started (PID: $FRONTEND_PID)"

# Wait for frontend to be ready
echo "⏳ Waiting for frontend to be ready..."
for i in {1..10}; do
    if curl -s http://localhost:8081/ > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Frontend server is ready!"
        break
    fi
    if [ $i -eq 10 ]; then
        echo -e "${RED}❌ Frontend server failed to start${NC}"
        echo "Check frontend_server.log for details"
        kill $API_PID $FRONTEND_PID 2>/dev/null || true
        exit 1
    fi
    sleep 1
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}🎉 AISim Tools is now running!${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "📱 Frontend:   ${GREEN}http://localhost:8081${NC}"
echo -e "🔗 API:        ${GREEN}http://localhost:8001${NC}"
echo -e "📚 API Docs:   ${GREEN}http://localhost:8001/docs${NC}"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Process IDs:"
echo "  API Server:      $API_PID"
echo "  Frontend Server: $FRONTEND_PID"
echo ""
echo "Logs:"
echo "  API:      tail -f api_server.log"
echo "  Frontend: tail -f frontend_server.log"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all servers${NC}"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Stopping servers..."
    kill $API_PID $FRONTEND_PID 2>/dev/null || true
    echo "👋 Servers stopped!"
    exit 0
}

# Trap Ctrl+C and call cleanup
trap cleanup INT TERM

# Wait for processes
wait
