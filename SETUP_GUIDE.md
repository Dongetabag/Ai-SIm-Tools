# AISim Tools - Local Setup Guide

This guide will help you set up and run AISim Tools locally on non-conflicting ports.

## 🚀 Quick Start

Run the automated setup script:

```bash
./start_app.sh
```

This script will:
- Check prerequisites (Python, FFmpeg)
- Create and activate a virtual environment
- Install all Python dependencies
- Start both API and frontend servers
- Open the app in your browser

## 📋 Prerequisites

### Required
- **Python 3.10+** (Python 3.11.14 recommended)
- **Node.js** (for frontend dependencies)

### Recommended
- **FFmpeg** (required for audio/video processing)

#### Installing FFmpeg

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Windows:**
Download from [ffmpeg.org](https://ffmpeg.org/download.html)

### Optional
AI API Keys for enhanced features:
- OpenAI API Key
- Google AI API Key
- Anthropic API Key

## 🔧 Manual Setup

If you prefer to set up manually:

### 1. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

**Note:** This will install large packages including PyTorch. Installation may take 10-20 minutes depending on your internet connection.

### 3. Configure API Keys (Optional)

Create a `.env` file in the project root:

```bash
OPENAI_API_KEY=your-openai-key-here
GOOGLE_API_KEY=your-google-key-here
ANTHROPIC_API_KEY=your-anthropic-key-here
```

### 4. Start the Servers

**Option A: Using the startup script (recommended)**
```bash
./start_app.sh
```

**Option B: Manual start**

Terminal 1 - API Server:
```bash
source venv/bin/activate
python3 ai_enhanced_api.py
```

Terminal 2 - Frontend Server:
```bash
source venv/bin/activate
python3 serve_frontend.py
```

## 🌐 Access the Application

After starting the servers:

- **Frontend UI:** http://localhost:8081
- **API Server:** http://localhost:8001
- **API Documentation:** http://localhost:8001/docs

## 🛠️ Available Tools

### 1. AI Audio Stem Separation
Separate audio into vocals, drums, bass, and other instruments using Demucs AI.

**Supported Formats:** WAV, FLAC, MP3, AAC, AIFF

### 2. YouTube to Audio Converter
Download and convert YouTube videos to high-quality audio files.

### 3. PDF Tools
Merge multiple PDFs with AI-powered document analysis.

### 4. Image Enhancement
Upscale and enhance images using AI and computer vision.

**Supported Formats:** JPG, PNG, GIF, BMP, TIFF, WebP

### 5. Video Generation
Generate videos from text prompts with AI enhancement.

**Output Formats:** MP4, MOV, MKV

### 6. AI Content Analysis
Analyze content using OpenAI, Google AI, or Anthropic Claude.

### 7. AI Prompt Optimization
Enhance your prompts for better AI results.

## 🔍 Troubleshooting

### Port Already in Use

If ports 8001 or 8081 are already in use, the startup script will automatically kill existing processes on those ports.

Manual cleanup:
```bash
# Kill process on port 8001
lsof -ti:8001 | xargs kill -9

# Kill process on port 8081
lsof -ti:8081 | xargs kill -9
```

### FFmpeg Not Found

Some features (audio/video conversion) require FFmpeg. Install it using the instructions in the Prerequisites section.

### Python Dependencies Installation Fails

If you encounter dependency conflicts:

1. Make sure you're using Python 3.10+
2. Update pip: `pip install --upgrade pip`
3. Try installing problematic packages individually

### Virtual Environment Issues

Delete and recreate the virtual environment:
```bash
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 📝 Logs

The startup script creates log files for debugging:

- `api_server.log` - API server logs
- `frontend_server.log` - Frontend server logs

View logs in real-time:
```bash
tail -f api_server.log
tail -f frontend_server.log
```

## 🛑 Stopping the Application

If using the startup script:
- Press `Ctrl+C` in the terminal

If running manually:
- Press `Ctrl+C` in each terminal window

## 💡 Tips

1. **First Run:** The first time you run the app, dependency installation will take 10-20 minutes.

2. **AI Features:** To use AI-enhanced features, configure API keys in the `.env` file.

3. **Output Files:** All processed files are saved in the `output/` directory.

4. **Performance:** For better performance with large files, ensure you have at least 8GB of RAM available.

5. **GPU Support:** If you have a CUDA-compatible GPU, PyTorch will automatically use it for faster processing.

## 🔄 Updates

To update the application:

```bash
git pull
source venv/bin/activate
pip install -r requirements.txt --upgrade
```

## 📞 Support

If you encounter issues:

1. Check the log files (`api_server.log`, `frontend_server.log`)
2. Ensure all prerequisites are installed
3. Verify your Python version is 3.10+
4. Make sure FFmpeg is installed and accessible

## 🎯 Configuration Changes

This setup uses non-conflicting ports:
- **API:** Port 8001 (changed from 8000)
- **Frontend:** Port 8081 (changed from 8080)

If you need to use different ports, edit:
- `ai_enhanced_api.py` (line 1269) for API port
- `serve_frontend.py` (line 12) for frontend port
- `ai_enhanced_ui.html` (line 83) for API URL in frontend
