#!/bin/bash

# Navigate to the application directory
cd "$(dirname "$0")"

echo "🚀 Starting AISim Tools - AI Enhanced..."

# Kill any existing servers
echo "Stopping existing servers..."
pkill -f "uvicorn" 2>/dev/null || true
pkill -f "serve_frontend" 2>/dev/null || true
pkill -f "python.*8000" 2>/dev/null || true
pkill -f "python.*8080" 2>/dev/null || true

# Wait a moment
sleep 2

# Check if API keys are configured
echo "🔑 Checking AI API keys..."
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  OPENAI_API_KEY not set. Some AI features may not work."
    echo "   Set it with: export OPENAI_API_KEY='your-key-here'"
fi

if [ -z "$GOOGLE_API_KEY" ]; then
    echo "⚠️  GOOGLE_API_KEY not set. Some AI features may not work."
    echo "   Set it with: export GOOGLE_API_KEY='your-key-here'"
fi

if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "⚠️  ANTHROPIC_API_KEY not set. Some AI features may not work."
    echo "   Set it with: export ANTHROPIC_API_KEY='your-key-here'"
fi

echo ""

# Start AI-enhanced FastAPI backend server
echo "Starting AI-enhanced FastAPI backend server on http://localhost:8000..."
python3 -m uvicorn ai_enhanced_api:app --reload --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
BACKEND_PID=$!
echo "FastAPI backend PID: $BACKEND_PID"

# Start Python static frontend server
echo "Starting Python frontend server on http://localhost:8080..."
python3 serve_frontend.py > frontend.log 2>&1 &
FRONTEND_PID=$!
echo "Frontend server PID: $FRONTEND_PID"

echo "Waiting for servers to start..."
sleep 5

echo "Testing servers..."
curl -s http://localhost:8000/ > /dev/null && echo "✅ Backend server is running" || echo "❌ Backend server failed"
curl -s http://localhost:8080/ > /dev/null && echo "✅ Frontend server is running" || echo "❌ Frontend server failed"

echo ""
echo "🎉 AISim Tools - AI Enhanced is now running!"
echo "📱 Frontend: http://localhost:8080/ai_enhanced_ui.html"
echo "🔗 API Server: http://localhost:8000"
echo ""
echo "🤖 AI Features Available:"
echo "   • OpenAI GPT-4 integration for content analysis"
echo "   • Google AI for image and video enhancement"
echo "   • Anthropic Claude for advanced AI processing"
echo "   • AI-powered prompt optimization"
echo "   • Enhanced audio analysis with AI insights"
echo "   • Intelligent PDF content analysis"
echo "   • AI-enhanced image upscaling"
echo "   • Smart video generation with AI prompts"
echo ""
echo "🔧 To configure AI services:"
echo "   export OPENAI_API_KEY='your-openai-key'"
echo "   export GOOGLE_API_KEY='your-google-key'"
echo "   export ANTHROPIC_API_KEY='your-anthropic-key'"
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
wait $BACKEND_PID
wait $FRONTEND_PID
