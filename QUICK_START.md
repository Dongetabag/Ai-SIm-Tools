# 🚀 Quick Start Guide

## Your AI Stem Separator is Ready!

You now have a complete AI stem separator application that can separate audio into vocals, drums, bass, and other instruments using state-of-the-art AI models.

## 🎯 What You Have

✅ **Simple Python Script** - Command-line tool for quick separations  
✅ **FastAPI Web Server** - REST API with file upload and real-time status  
✅ **React Frontend** - Beautiful web interface for easy use  
✅ **Docker Support** - Easy deployment with containers  
✅ **Multiple AI Models** - Choose between speed and quality  

## 🚀 How to Run

### Option 1: Quick Start (Recommended)
```bash
cd "/Users/simeonreid/music app"
./start_server.sh
```
Then open http://localhost:8000 in your browser!

### Option 2: Manual Start
```bash
cd "/Users/simeonreid/music app"
python3 -m uvicorn stem_separator_api:app --reload --host 0.0.0.0 --port 8000
```

### Option 3: Command Line Only
```bash
cd "/Users/simeonreid/music app"
python3 stem_separator_simple.py your_audio_file.mp3
```

### Option 4: Docker
```bash
cd "/Users/simeonreid/music app"
docker-compose up --build
```

## 🎵 How to Use

### Web Interface
1. Open http://localhost:8000 in your browser
2. Drag and drop an audio file (MP3, WAV, FLAC)
3. Choose an AI model
4. Click "Start Separation"
5. Download the separated stems (vocals, drums, bass, other)

### Command Line
```bash
# Basic usage
python3 stem_separator_simple.py song.mp3

# With custom output directory
python3 stem_separator_simple.py song.mp3 output_folder

# With specific model
python3 stem_separator_simple.py song.mp3 output_folder mdx_extra
```

### API
```bash
# Upload and separate
curl -X POST http://localhost:8000/api/separate \
  -F "file=@song.mp3" \
  -F "model=htdemucs"

# Check status
curl http://localhost:8000/api/status/{job_id}

# Download stems
curl http://localhost:8000/api/download/{job_id}/vocals -o vocals.wav
```

## 🎨 Available Models

| Model | Quality | Speed | Best For |
|-------|---------|-------|----------|
| `htdemucs` | ⭐⭐⭐⭐⭐ | ⚡⚡⚡ | **Recommended** |
| `htdemucs_ft` | ⭐⭐⭐⭐⭐ | ⚡⚡⚡ | Fine-tuned version |
| `mdx_extra` | ⭐⭐⭐⭐⭐⭐ | ⚡⚡ | Best quality (slower) |
| `mdx_extra_q` | ⭐⭐⭐⭐ | ⚡⚡⚡⚡ | Fast processing |

## 📁 File Structure

```
music app/
├── stem_separator_simple.py    # Command-line tool
├── stem_separator_api.py       # FastAPI web server
├── StemSeparator.jsx           # React component
├── index.html                  # Web interface
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Docker configuration
├── docker-compose.yml         # Docker Compose setup
├── start_server.sh            # Quick start script
├── test_setup.py              # Setup verification
└── README.md                  # Complete documentation
```

## 🔧 Troubleshooting

### Server Won't Start
- Make sure Python 3 is installed: `python3 --version`
- Install dependencies: `pip3 install -r requirements.txt`
- Check if port 8000 is available

### Poor Quality Separation
- Try the `mdx_extra` model for best quality
- Ensure your input file is high quality
- Use shorter audio files for better results

### Slow Processing
- The application will use CPU by default (slower)
- For GPU acceleration, install CUDA-enabled PyTorch
- Use `mdx_extra_q` model for faster processing

## 🎉 Next Steps

1. **Test with your music**: Try separating a song you know well
2. **Experiment with models**: Compare different AI models
3. **Integrate into your app**: Use the React component or API
4. **Deploy to production**: Use Docker for easy deployment

## 📚 More Information

- See `README.md` for complete documentation
- Check the API documentation at http://localhost:8000/docs when running
- Visit [Demucs GitHub](https://github.com/facebookresearch/demucs) for more details

---

**🎵 Your AI stem separator is ready to use! Enjoy separating music! 🎵**
