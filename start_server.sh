#!/bin/bash

echo "🎵 Starting AI Stem Separator Server"
echo "=================================="

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

echo "🚀 Starting API server..."
echo "📱 Open http://localhost:8000 in your browser"
echo "🛑 Press Ctrl+C to stop the server"
echo ""

python3 -m uvicorn stem_separator_api:app --reload --host 0.0.0.0 --port 8000
