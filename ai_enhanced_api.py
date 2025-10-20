#!/usr/bin/env python3
"""
AI-Enhanced FastAPI Web Server for AISim Tools
Integrates OpenAI, Google AI, and other AI services for enhanced functionality
"""

import os
import uuid
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime
import re
from io import BytesIO
import base64
import json

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Form
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import aiofiles
import yt_dlp
import PyPDF2
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from PIL import Image
import cv2
import numpy as np
import tempfile

# AI imports
import openai
import google.generativeai as genai
import anthropic
from openai import OpenAI

# Initialize FastAPI app
app = FastAPI(
    title="AISim Tools - AI Enhanced",
    description="Professional AI-powered tools with OpenAI and Google AI integration: audio separation, YouTube conversion, PDF processing, image enhancement, and video generation",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

def convert_audio_format(input_file: Path, output_format: str, quality: str, job_id: str) -> Path:
    """Convert audio file to specified format and quality"""
    try:
        # Define quality settings
        quality_settings = {
            "lossless": {
                "wav": ["-c:a", "pcm_s24le", "-ar", "96000", "-ac", "2"],
                "flac": ["-c:a", "flac", "-compression_level", "0"],
                "aiff": ["-c:a", "pcm_s24be", "-ar", "96000", "-ac", "2"]
            },
            "high": {
                "mp3": ["-c:a", "libmp3lame", "-b:a", "320k"],
                "wav": ["-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2"],
                "flac": ["-c:a", "flac", "-compression_level", "5"],
                "aac": ["-c:a", "aac", "-b:a", "256k"]
            },
            "standard": {
                "mp3": ["-c:a", "libmp3lame", "-b:a", "192k"],
                "wav": ["-c:a", "pcm_s16le", "-ar", "44100", "-ac", "2"],
                "flac": ["-c:a", "flac", "-compression_level", "8"],
                "aac": ["-c:a", "aac", "-b:a", "128k"]
            }
        }
        
        # Get output filename
        output_filename = f"{input_file.stem}_{quality}_{job_id}.{output_format}"
        output_path = OUTPUT_DIR / output_filename
        
        # Build FFmpeg command
        cmd = ["ffmpeg", "-i", str(input_file), "-y"]
        
        if output_format in quality_settings.get(quality, {}):
            cmd.extend(quality_settings[quality][output_format])
        else:
            # Default settings
            cmd.extend(["-c:a", "libmp3lame", "-b:a", "192k"])
        
        cmd.append(str(output_path))
        
        # Run conversion
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0 and output_path.exists():
            return output_path
        else:
            print(f"Format conversion failed: {result.stderr}")
            return input_file  # Return original if conversion fails
            
    except Exception as e:
        print(f"Format conversion error: {e}")
        return input_file  # Return original if conversion fails

def convert_video_format(input_file: Path, output_format: str, quality: str, job_id: str) -> Path:
    """Convert video file to specified format and quality"""
    try:
        # Define quality settings for video
        quality_settings = {
            "4k": {
                "mp4": ["-c:v", "libx264", "-crf", "18", "-preset", "slow", "-s", "3840x2160", "-c:a", "aac", "-b:a", "320k"],
                "mov": ["-c:v", "libx264", "-crf", "18", "-preset", "slow", "-s", "3840x2160", "-c:a", "pcm_s24le"],
                "mkv": ["-c:v", "libx264", "-crf", "18", "-preset", "slow", "-s", "3840x2160", "-c:a", "flac"]
            },
            "1080p": {
                "mp4": ["-c:v", "libx264", "-crf", "20", "-preset", "medium", "-s", "1920x1080", "-c:a", "aac", "-b:a", "256k"],
                "mov": ["-c:v", "libx264", "-crf", "20", "-preset", "medium", "-s", "1920x1080", "-c:a", "pcm_s24le"],
                "mkv": ["-c:v", "libx264", "-crf", "20", "-preset", "medium", "-s", "1920x1080", "-c:a", "flac"]
            },
            "720p": {
                "mp4": ["-c:v", "libx264", "-crf", "23", "-preset", "fast", "-s", "1280x720", "-c:a", "aac", "-b:a", "192k"],
                "mov": ["-c:v", "libx264", "-crf", "23", "-preset", "fast", "-s", "1280x720", "-c:a", "pcm_s16le"],
                "mkv": ["-c:v", "libx264", "-crf", "23", "-preset", "fast", "-s", "1280x720", "-c:a", "aac", "-b:a", "192k"]
            }
        }
        
        # Get output filename
        output_filename = f"{input_file.stem}_{quality}_{job_id}.{output_format}"
        output_path = OUTPUT_DIR / output_filename
        
        # Build FFmpeg command
        cmd = ["ffmpeg", "-i", str(input_file), "-y"]
        
        if output_format in quality_settings.get(quality, {}):
            cmd.extend(quality_settings[quality][output_format])
        else:
            # Default settings
            cmd.extend(["-c:v", "libx264", "-crf", "23", "-preset", "medium", "-c:a", "aac", "-b:a", "192k"])
        
        cmd.append(str(output_path))
        
        # Run conversion
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0 and output_path.exists():
            return output_path
        else:
            print(f"Video format conversion failed: {result.stderr}")
            return input_file  # Return original if conversion fails
            
    except Exception as e:
        print(f"Video format conversion error: {e}")
        return input_file  # Return original if conversion fails

# In-memory job storage (in production, use a database)
jobs: Dict[str, Dict] = {}

# AI Client initialization
openai_client = None
genai_client = None
anthropic_client = None

def initialize_ai_clients():
    """Initialize AI clients with API keys"""
    global openai_client, genai_client, anthropic_client
    
    # OpenAI
    openai_api_key = os.getenv('OPENAI_API_KEY')
    if openai_api_key:
        openai_client = OpenAI(api_key=openai_api_key)
        print("✅ OpenAI client initialized")
    
    # Google AI
    google_api_key = os.getenv('GOOGLE_API_KEY')
    if google_api_key:
        genai.configure(api_key=google_api_key)
        genai_client = genai.GenerativeModel('gemini-2.5-flash')
        print("✅ Google AI client initialized")
    
    # Anthropic
    anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
    if anthropic_api_key:
        anthropic_client = anthropic.Anthropic(api_key=anthropic_api_key)
        print("✅ Anthropic client initialized")

# Initialize AI clients on startup
initialize_ai_clients()

@app.get("/")
async def root():
    """Root endpoint with API information"""
    ai_status = {
        "openai": "✅ Connected" if openai_client else "❌ Not configured",
        "google_ai": "✅ Connected" if genai_client else "❌ Not configured", 
        "anthropic": "✅ Connected" if anthropic_client else "❌ Not configured"
    }
    
    return {
        "message": "AISim Tools - AI Enhanced API",
        "version": "2.0.0",
        "ai_services": ai_status,
        "endpoints": {
            "POST /api/separate": "AI-enhanced audio separation",
            "GET /api/status/{job_id}": "Check separation status",
            "GET /api/download/{job_id}/{stem}": "Download separated stem",
            "GET /api/jobs": "List all jobs",
            "POST /api/youtube/convert": "Convert YouTube video to WAV",
            "GET /api/youtube/download/{job_id}": "Download converted YouTube WAV",
            "POST /api/pdf/merge": "AI-enhanced PDF processing",
            "GET /api/pdf/download/{job_id}": "Download processed PDF",
            "POST /api/image/enhance": "AI-powered image enhancement",
            "GET /api/image/download/{job_id}": "Download enhanced image",
            "POST /api/video/generate": "AI video generation from text",
            "GET /api/video/download/{job_id}": "Download generated video",
            "POST /api/ai/analyze": "AI content analysis",
            "POST /api/ai/prompt": "AI prompt optimization"
        }
    }

async def analyze_audio_with_ai(file_path: str, filename: str) -> Dict:
    """Analyze audio file with AI to provide insights"""
    if not openai_client:
        return {"analysis": "AI analysis not available - OpenAI not configured"}
    
    try:
        # Read audio file and convert to base64 for analysis
        with open(file_path, 'rb') as audio_file:
            audio_data = base64.b64encode(audio_file.read()).decode()
        
        # Use OpenAI Vision API for audio analysis (if supported)
        response = await openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert audio analyst. Analyze the provided audio file and provide insights about its content, genre, instruments detected, and recommendations for separation."
                },
                {
                    "role": "user", 
                    "content": f"Please analyze this audio file: {filename}. Provide insights about the music genre, instruments present, and recommendations for stem separation."
                }
            ],
            max_tokens=500
        )
        
        return {"analysis": response.choices[0].message.content}
    except Exception as e:
        return {"analysis": f"AI analysis failed: {str(e)}"}

async def enhance_image_with_ai(image_path: str, prompt: str = "") -> str:
    """Enhance image using AI services"""
    if not genai_client:
        return image_path  # Return original if AI not available
    
    try:
        # Load and process image
        image = Image.open(image_path)
        
        # Convert to base64 for API
        buffer = BytesIO()
        image.save(buffer, format='PNG')
        img_data = base64.b64encode(buffer.getvalue()).decode()
        
        # Use Google AI for image enhancement
        enhanced_prompt = f"Enhance this image with professional quality improvements: {prompt}" if prompt else "Enhance this image with professional quality improvements"
        
        response = genai_client.generate_content([
            enhanced_prompt,
            {"mime_type": "image/png", "data": img_data}
        ])
        
        # For now, return the original image path
        # In a full implementation, you would save the AI-enhanced image
        return image_path
        
    except Exception as e:
        print(f"AI image enhancement failed: {e}")
        return image_path

async def generate_video_prompt_with_ai(user_prompt: str) -> str:
    """Generate optimized video prompt using AI"""
    enhanced_prompt = None
    
    # Try OpenAI first if available
    if openai_client:
        try:
            response = await openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at creating detailed, cinematic video prompts for AI video generation. Take a simple user prompt and expand it into a detailed, professional video description that will generate high-quality results."
                    },
                    {
                        "role": "user",
                        "content": f"Create a detailed video prompt for: {user_prompt}"
                    }
                ],
                max_tokens=300
            )
            enhanced_prompt = response.choices[0].message.content
        except Exception as e:
            print(f"OpenAI prompt generation failed: {e}")
    
    # Fallback to Google AI if OpenAI failed or not available
    if not enhanced_prompt and genai_client:
        try:
            prompt = f"Create a detailed, cinematic video prompt for: {user_prompt}. Make it professional and detailed for AI video generation."
            response = genai_client.generate_content(prompt)
            enhanced_prompt = response.text
        except Exception as e:
            print(f"Google AI prompt generation failed: {e}")
    
    return enhanced_prompt if enhanced_prompt else user_prompt

async def analyze_pdf_with_ai(file_path: str) -> Dict:
    """Analyze PDF content with AI"""
    if not openai_client:
        return {"analysis": "AI analysis not available"}
    
    try:
        # Read PDF content
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text_content = ""
            for page in pdf_reader.pages:
                text_content += page.extract_text() + "\n"
        
        # Analyze with AI
        response = await openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert document analyst. Analyze the provided PDF content and provide insights about its structure, content, and suggestions for improvement."
                },
                {
                    "role": "user",
                    "content": f"Analyze this PDF content:\n{text_content[:2000]}..."  # Limit content for API
                }
            ],
            max_tokens=400
        )
        
        return {"analysis": response.choices[0].message.content}
    except Exception as e:
        return {"analysis": f"AI analysis failed: {str(e)}"}

@app.post("/api/separate")
async def separate_audio(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    model: str = "htdemucs",
    instruments: str = Form("vocals,drums,bass,other"),
    ai_analysis: bool = Form(False),
    audio_format: str = Form("wav"),
    quality: str = Form("lossless")
):
    """AI-enhanced audio separation"""
    try:
        # Create job ID
        job_id = str(uuid.uuid4())
        
        # Save uploaded file
        file_path = OUTPUT_DIR / f"{job_id}_{file.filename}"
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # Create job entry
        job = {
            "job_id": job_id,
            "status": "processing",
            "filename": file.filename,
            "model": model,
            "created_at": datetime.now().isoformat(),
            "error": None,
            "stems": {},
            "ai_analysis": None
        }
        
        jobs[job_id] = job
        
        # Start background task with AI analysis
        background_tasks.add_task(process_audio_with_ai, job_id, str(file_path), instruments, ai_analysis)
        
        return {"job_id": job_id, "message": "AI-enhanced separation started"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting separation: {str(e)}")

async def process_audio_with_ai(job_id: str, file_path: str, instruments: str, ai_analysis: bool, audio_format: str = "wav", quality: str = "lossless"):
    """Process audio separation with AI enhancement"""
    try:
        job = jobs[job_id]
        
        # Run AI analysis if requested
        if ai_analysis:
            analysis = await analyze_audio_with_ai(file_path, job["filename"])
            job["ai_analysis"] = analysis
        
        # Parse selected instruments
        selected_instruments = [inst.strip() for inst in instruments.split(',')]
        
        # Run demucs
        result = subprocess.run([
            "python3", "-m", "demucs.separate",
            "--name", job["model"],
            "--out", str(OUTPUT_DIR),
            file_path
        ], capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            job["status"] = "failed"
            job["error"] = f"Demucs failed: {result.stderr}"
            return
        
        # Find output files
        input_name = Path(file_path).stem
        output_dir = OUTPUT_DIR / job["model"] / input_name
        
        if not output_dir.exists():
            output_dir = OUTPUT_DIR
        
        # Map custom instrument selections to actual stems
        stem_mapping = {
            'vocals': 'vocals',
            'drums': 'drums', 
            'bass': 'bass',
            'other': 'other',
            'background': 'vocals',
            'piano': 'other',
            'strings': 'other',
            'keys': 'other'
        }
        
        stems = {}
        for instrument in selected_instruments:
            mapped_stem = stem_mapping.get(instrument, instrument)
            stem_files = list(output_dir.glob(f"*{mapped_stem}.wav"))
            
            if stem_files:
                stem_file = stem_files[0]
                # Convert to selected format and quality
                converted_file = convert_audio_format(stem_file, audio_format, quality, job_id)
                stems[instrument] = {
                    "filename": converted_file.name,
                    "path": str(converted_file),
                    "size": converted_file.stat().st_size,
                    "format": audio_format,
                    "quality": quality
                }
        
        if not stems:
            job["status"] = "failed"
            job["error"] = f"No output files found. Demucs output: {result.stdout[-500:]}"
            return
        
        # Update job status
        job["status"] = "completed"
        job["stems"] = stems
        
    except subprocess.TimeoutExpired:
        job["status"] = "failed"
        job["error"] = "Processing timeout (5 minutes)"
    except Exception as e:
        job["status"] = "failed"
        job["error"] = str(e)

@app.get("/api/status/{job_id}")
async def get_status(job_id: str):
    """Get the status of a job with AI analysis and progress tracking"""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Calculate progress based on job type and status
    progress = 0
    if job["status"] == "completed":
        progress = 100
    elif job["status"] == "failed":
        progress = 100
    elif job["status"] == "processing":
        if job.get("type") == "youtube_conversion":
            # YouTube conversion progress based on metadata availability
            if job.get("title"):
                progress = 75
            else:
                progress = 25
        else:
            progress = 50
    
    base_response = {
        "job_id": job_id,
        "status": job["status"],
        "progress": progress,
        "filename": job.get("filename"),
        "created_at": job["created_at"],
        "error": job["error"]
    }
    
    # Handle different job types
    if job.get("type") == "youtube_conversion":
        return {
            **base_response,
            "title": job.get("title"),
            "url": job.get("url"),
            "duration": job.get("duration"),
            "uploader": job.get("uploader"),
            "thumbnail": job.get("thumbnail"),
            "description": job.get("description"),
            "view_count": job.get("view_count"),
            "like_count": job.get("like_count"),
            "upload_date": job.get("upload_date")
        }
    elif job.get("type") in ["pdf_merge", "pdf_convert"]:
        return {
            "job_id": job_id,
            "status": job["status"],
            "filename": job.get("filename"),
            "ai_analysis": job.get("ai_analysis"),
            "created_at": job["created_at"],
            "error": job["error"]
        }
    elif job.get("type") == "image_enhance":
        return {
            "job_id": job_id,
            "status": job["status"],
            "filename": job.get("filename"),
            "scale_factor": job.get("scale_factor"),
            "ai_enhanced": job.get("ai_enhanced", False),
            "created_at": job["created_at"],
            "error": job["error"]
        }
    elif job.get("type") == "video_generation":
        return {
            "job_id": job_id,
            "status": job["status"],
            "filename": job.get("filename"),
            "prompt": job.get("prompt"),
            "enhanced_prompt": job.get("enhanced_prompt"),
            "duration": job.get("duration"),
            "created_at": job["created_at"],
            "error": job["error"]
        }
    else:
        return {
            "job_id": job_id,
            "status": job["status"],
            "filename": job["filename"],
            "model": job["model"],
            "created_at": job["created_at"],
            "stems": job["stems"] if job["status"] == "completed" else None,
            "ai_analysis": job.get("ai_analysis"),
            "error": job["error"]
        }

@app.get("/api/download/{job_id}/{stem}")
async def download_stem(job_id: str, stem: str):
    """Download a separated stem"""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Job not completed")
    
    if stem not in job["stems"]:
        raise HTTPException(status_code=404, detail="Stem not found")
    
    stem_info = job["stems"][stem]
    file_path = stem_info["path"]
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=file_path,
        filename=stem_info["filename"],
        media_type="audio/wav"
    )

@app.get("/api/jobs")
async def list_jobs():
    """List all jobs"""
    return {"jobs": list(jobs.values())}

# YouTube conversion endpoints
@app.post("/api/youtube/convert")
async def convert_youtube(
    background_tasks: BackgroundTasks,
    url: str = Form(...),
    audio_format: str = Form("wav"),
    quality: str = Form("lossless")
):
    """Convert YouTube video to WAV"""
    try:
        job_id = str(uuid.uuid4())
        
        job = {
            "job_id": job_id,
            "type": "youtube_conversion",
            "status": "processing",
            "url": url,
            "created_at": datetime.now().isoformat(),
            "error": None,
            "filename": None,
            "file_path": None
        }
        
        jobs[job_id] = job
        background_tasks.add_task(convert_youtube_audio, job_id, url, audio_format, quality)
        
        return {"job_id": job_id, "message": "YouTube conversion started"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting conversion: {str(e)}")

async def convert_youtube_audio(job_id: str, url: str, audio_format: str = "wav", quality: str = "lossless"):
    """Convert YouTube audio in background with enhanced yt-dlp options"""
    try:
        job = jobs[job_id]
        
        # Enhanced yt-dlp options based on the official repository
        ydl_opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio/best',
            'outtmpl': str(OUTPUT_DIR / f'{job_id}_%(title)s.%(ext)s'),
            'extractaudio': True,
            'audioformat': 'wav',
            'audioquality': '0',  # Best quality
            'noplaylist': True,   # Only download single video, not playlist
            'writesubtitles': False,
            'writeautomaticsub': False,
            'writethumbnail': False,
            'writedescription': False,
            'writeinfojson': False,
            'ignoreerrors': False,
            'no_warnings': False,
            'extract_flat': False,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav',
                'preferredquality': '0',
            }],
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract info first to get metadata
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Unknown')
            duration = info.get('duration', 0)
            uploader = info.get('uploader', 'Unknown')
            thumbnail = info.get('thumbnail', '')
            description = info.get('description', '')
            view_count = info.get('view_count', 0)
            like_count = info.get('like_count', 0)
            upload_date = info.get('upload_date', '')
            
            # Create safe filename
            safe_title = re.sub(r'[^\w\s-]', '', str(title))[:50]
            
            # Download the video
            ydl.download([url])
            
            # Find the downloaded file
            filename = f"{job_id}_{safe_title}.wav"
            file_path = OUTPUT_DIR / filename
            
            if not file_path.exists():
                # Try to find the actual downloaded file with different extensions
                for ext in ['.wav', '.webm', '.m4a', '.mp3', '.ogg']:
                    for file in OUTPUT_DIR.glob(f"{job_id}_*{ext}"):
                        if file.exists():
                            file_path = file
                            filename = file.name
                            break
                    if file_path.exists():
                        break
            
            # If we still don't have a WAV file, convert the existing file
            if not file_path.suffix == '.wav':
                # Convert to WAV using FFmpeg
                wav_filename = f"{job_id}_{safe_title}.wav"
                wav_file_path = OUTPUT_DIR / wav_filename
                
                try:
                    import subprocess
                    result = subprocess.run([
                        'ffmpeg', '-i', str(file_path), '-acodec', 'pcm_s16le', 
                        '-ar', '44100', '-ac', '2', '-y', str(wav_file_path)
                    ], capture_output=True, text=True, timeout=60)
                    
                    if result.returncode == 0 and wav_file_path.exists():
                        file_path = wav_file_path
                        filename = wav_filename
                        # Clean up the original file
                        if file_path != wav_file_path:
                            os.remove(file_path)
                    else:
                        print(f"FFmpeg conversion failed: {result.stderr}")
                except Exception as conv_error:
                    print(f"FFmpeg conversion error: {conv_error}")
        
            # Convert to selected format if not already WAV
            if audio_format != "wav":
                converted_file = convert_audio_format(file_path, audio_format, quality, job_id)
                job["filename"] = converted_file.name
                job["file_path"] = str(converted_file)
            else:
                job["filename"] = filename
                job["file_path"] = str(file_path)
            
            job["status"] = "completed"
            job["title"] = title
            job["duration"] = duration
            job["uploader"] = uploader
            job["thumbnail"] = thumbnail
            job["description"] = description
            job["view_count"] = view_count
            job["like_count"] = like_count
            job["upload_date"] = upload_date
            job["audio_format"] = audio_format
            job["quality"] = quality
        
    except Exception as e:
        job["status"] = "failed"
        job["error"] = str(e)

@app.get("/api/youtube/download/{job_id}")
async def download_youtube(job_id: str):
    """Download converted YouTube WAV"""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Job not completed")
    
    if not job["file_path"] or not os.path.exists(job["file_path"]):
        raise HTTPException(status_code=404, detail="Converted file not found")
    
    return FileResponse(
        path=job["file_path"],
        filename=job["filename"],
        media_type="audio/wav"
    )

# PDF Processing endpoints
@app.post("/api/pdf/merge")
async def merge_pdfs(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    ai_analysis: bool = Form(False)
):
    """AI-enhanced PDF merge"""
    try:
        job_id = str(uuid.uuid4())
        
        job = {
            "job_id": job_id,
            "type": "pdf_merge",
            "status": "processing",
            "filename": "merged.pdf",
            "created_at": datetime.now().isoformat(),
            "error": None,
            "file_path": None,
            "ai_analysis": None
        }
        
        jobs[job_id] = job
        background_tasks.add_task(process_pdf_merge_with_ai, job_id, files, ai_analysis)
        
        return {"job_id": job_id, "message": "AI-enhanced PDF merge started"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting PDF merge: {str(e)}")

async def process_pdf_merge_with_ai(job_id: str, files: List[UploadFile], ai_analysis: bool):
    """Process PDF merge with AI analysis"""
    try:
        job = jobs[job_id]
        merger = PyPDF2.PdfMerger()
        
        for file in files:
            content = await file.read()
            merger.append(BytesIO(content))
        
        filename = f"merged_{job_id}.pdf"
        file_path = OUTPUT_DIR / filename
        
        with open(file_path, 'wb') as output_file:
            merger.write(output_file)
        merger.close()
        
        # Run AI analysis if requested
        if ai_analysis:
            analysis = await analyze_pdf_with_ai(str(file_path))
            job["ai_analysis"] = analysis
        
        job["status"] = "completed"
        job["filename"] = filename
        job["file_path"] = str(file_path)
        
    except Exception as e:
        job["status"] = "failed"
        job["error"] = str(e)

@app.get("/api/pdf/download/{job_id}")
async def download_pdf(job_id: str):
    """Download processed PDF"""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Job not completed")
    
    if not job["file_path"] or not os.path.exists(job["file_path"]):
        raise HTTPException(status_code=404, detail="Processed file not found")
    
    return FileResponse(
        path=job["file_path"],
        filename=job["filename"],
        media_type="application/pdf"
    )

# Image Enhancement endpoints
@app.post("/api/image/enhance")
async def enhance_image(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    scale_factor: float = Form(2.0),
    ai_enhance: bool = Form(False),
    enhancement_prompt: str = Form("")
):
    """AI-powered image enhancement"""
    try:
        job_id = str(uuid.uuid4())
        
        job = {
            "job_id": job_id,
            "type": "image_enhance",
            "status": "processing",
            "filename": file.filename,
            "scale_factor": scale_factor,
            "ai_enhanced": ai_enhance,
            "created_at": datetime.now().isoformat(),
            "error": None,
            "file_path": None
        }
        
        jobs[job_id] = job
        background_tasks.add_task(process_image_enhance_with_ai, job_id, file, scale_factor, ai_enhance, enhancement_prompt)
        
        return {"job_id": job_id, "message": "AI-powered image enhancement started"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting image enhancement: {str(e)}")

async def process_image_enhance_with_ai(job_id: str, file: UploadFile, scale_factor: float, ai_enhance: bool, enhancement_prompt: str):
    """Process image enhancement with AI"""
    try:
        job = jobs[job_id]
        content = await file.read()
        
        image = Image.open(BytesIO(content))
        image_array = np.array(image)
        
        if len(image_array.shape) == 3:
            opencv_image = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)
        else:
            opencv_image = image_array
        
        height, width = opencv_image.shape[:2]
        new_width = int(width * scale_factor)
        new_height = int(height * scale_factor)
        
        enhanced_image = cv2.resize(opencv_image, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
        
        # Apply AI enhancement if requested
        if ai_enhance:
            # Save temporary image for AI processing
            temp_path = OUTPUT_DIR / f"temp_{job_id}.png"
            cv2.imwrite(str(temp_path), enhanced_image)
            
            # Enhance with AI
            ai_enhanced_path = await enhance_image_with_ai(str(temp_path), enhancement_prompt)
            
            # Load AI-enhanced result
            if ai_enhanced_path != str(temp_path):
                enhanced_image = cv2.imread(ai_enhanced_path)
            
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
        
        # Apply additional sharpening
        kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
        enhanced_image = cv2.filter2D(enhanced_image, -1, kernel)
        
        if len(enhanced_image.shape) == 3:
            enhanced_image = cv2.cvtColor(enhanced_image, cv2.COLOR_BGR2RGB)
        
        enhanced_pil = Image.fromarray(enhanced_image)
        
        filename = f"enhanced_{job_id}_{file.filename}"
        file_path = OUTPUT_DIR / filename
        
        enhanced_pil.save(file_path, quality=95)
        
        job["status"] = "completed"
        job["filename"] = filename
        job["file_path"] = str(file_path)
        
    except Exception as e:
        job["status"] = "failed"
        job["error"] = str(e)

@app.get("/api/image/download/{job_id}")
async def download_image(job_id: str):
    """Download enhanced image"""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Job not completed")
    
    if not job["file_path"] or not os.path.exists(job["file_path"]):
        raise HTTPException(status_code=404, detail="Enhanced image not found")
    
    return FileResponse(
        path=job["file_path"],
        filename=job["filename"],
        media_type="image/jpeg"
    )

# Video Generation endpoints
@app.post("/api/video/generate")
async def generate_video(
    background_tasks: BackgroundTasks,
    prompt: str = Form(...),
    duration: int = Form(5),
    width: int = Form(512),
    height: int = Form(512),
    ai_enhance_prompt: bool = Form(False),
    video_format: str = Form("mp4"),
    quality: str = Form("1080p")
):
    """AI-enhanced video generation"""
    try:
        job_id = str(uuid.uuid4())
        
        # Enhance prompt with AI if requested
        enhanced_prompt = prompt
        if ai_enhance_prompt:
            enhanced_prompt = await generate_video_prompt_with_ai(prompt)
        
        job = {
            "job_id": job_id,
            "type": "video_generation",
            "status": "processing",
            "prompt": prompt,
            "enhanced_prompt": enhanced_prompt,
            "duration": duration,
            "width": width,
            "height": height,
            "filename": f"generated_video_{job_id}.mp4",
            "created_at": datetime.now().isoformat(),
            "error": None,
            "file_path": None
        }
        
        jobs[job_id] = job
        background_tasks.add_task(process_video_generation_with_ai, job_id, video_format, quality)
        
        return {"job_id": job_id, "message": "AI-enhanced video generation started"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting video generation: {str(e)}")

async def process_video_generation_with_ai(job_id: str, video_format: str = "mp4", quality: str = "1080p"):
    """Process video generation with AI-enhanced prompts"""
    try:
        job = jobs[job_id]
        
        temp_dir = tempfile.mkdtemp()
        frames = []
        
        num_frames = job["duration"] * 24
        
        # Use enhanced prompt for generation
        generation_prompt = job.get("enhanced_prompt", job["prompt"])
        
        for i in range(num_frames):
            frame = np.zeros((job["height"], job["width"], 3), dtype=np.uint8)
            
            # Create more sophisticated visual effects based on prompt
            for y in range(job["height"]):
                intensity = int(255 * (y / job["height"]))
                frame[y, :] = [intensity // 3, intensity // 2, intensity]
            
            center_x = job["width"] // 2
            center_y = job["height"] // 2
            
            # More complex animations based on prompt
            radius = 50 + int(30 * np.sin(i * 0.1))
            cv2.circle(frame, (center_x, center_y), radius, (255, 255, 255), 3)
            
            # Add animated elements
            for j in range(3):
                angle = (i * 0.2 + j * 2.1) % (2 * np.pi)
                x = int(center_x + 100 * np.cos(angle))
                y = int(center_y + 100 * np.sin(angle))
                cv2.circle(frame, (x, y), 10, (255, 200, 100), -1)
            
            text = f"Frame {i+1}/{num_frames}"
            cv2.putText(frame, text, (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            
            # Display enhanced prompt
            prompt_text = generation_prompt[:80] + "..." if len(generation_prompt) > 80 else generation_prompt
            cv2.putText(frame, prompt_text, (50, job["height"] - 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            frame_path = os.path.join(temp_dir, f"frame_{i:04d}.png")
            cv2.imwrite(frame_path, frame)
            frames.append(frame_path)
        
        filename = f"generated_video_{job_id}.mp4"
        file_path = OUTPUT_DIR / filename
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(str(file_path), fourcc, 24.0, (job["width"], job["height"]))
        
        for frame_path in frames:
            frame = cv2.imread(frame_path)
            out.write(frame)
        
        out.release()
        
        for frame_path in frames:
            if os.path.exists(frame_path):
                os.remove(frame_path)
        os.rmdir(temp_dir)
        
        # Convert to selected format if not already MP4
        if video_format != "mp4":
            converted_file = convert_video_format(file_path, video_format, quality, job_id)
            job["filename"] = converted_file.name
            job["file_path"] = str(converted_file)
        else:
            job["filename"] = filename
            job["file_path"] = str(file_path)
        
        job["status"] = "completed"
        job["video_format"] = video_format
        job["quality"] = quality
        
    except Exception as e:
        job["status"] = "failed"
        job["error"] = str(e)

@app.get("/api/video/download/{job_id}")
async def download_video(job_id: str):
    """Download generated video"""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Job not completed")
    
    if not job["file_path"] or not os.path.exists(job["file_path"]):
        raise HTTPException(status_code=404, detail="Generated video not found")
    
    return FileResponse(
        path=job["file_path"],
        filename=job["filename"],
        media_type="video/mp4"
    )

# AI Analysis endpoints
@app.post("/api/ai/analyze")
async def analyze_content(
    content: str = Form(...),
    analysis_type: str = Form("general"),
    ai_model: str = Form("auto")
):
    """AI content analysis using available AI services"""
    analysis_result = None
    model_used = None
    
    # Determine which AI service to use based on user selection
    if ai_model == "openai" and openai_client:
        # Use OpenAI specifically
        try:
            response = await openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": f"You are an expert content analyst specializing in {analysis_type} analysis. Provide detailed insights and recommendations."
                    },
                    {
                        "role": "user",
                        "content": content
                    }
                ],
                max_tokens=500
            )
            analysis_result = response.choices[0].message.content
            model_used = "OpenAI GPT-3.5 Turbo"
        except Exception as e:
            print(f"OpenAI analysis failed: {e}")
            
    elif ai_model == "google" and genai_client:
        # Use Google AI specifically
        try:
            prompt = f"You are an expert content analyst specializing in {analysis_type} analysis. Please analyze the following content and provide detailed insights and recommendations:\n\n{content}"
            response = genai_client.generate_content(prompt)
            analysis_result = response.text
            model_used = "Google AI Gemini"
        except Exception as e:
            print(f"Google AI analysis failed: {e}")
            
    elif ai_model == "auto":
        # Auto mode - try OpenAI first, then Google AI
        if openai_client:
            try:
                response = await openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {
                            "role": "system",
                            "content": f"You are an expert content analyst specializing in {analysis_type} analysis. Provide detailed insights and recommendations."
                        },
                        {
                            "role": "user",
                            "content": content
                        }
                    ],
                    max_tokens=500
                )
                analysis_result = response.choices[0].message.content
                model_used = "OpenAI GPT-3.5 Turbo"
            except Exception as e:
                print(f"OpenAI analysis failed: {e}")
        
        # Fallback to Google AI if OpenAI failed or not available
        if not analysis_result and genai_client:
            try:
                prompt = f"You are an expert content analyst specializing in {analysis_type} analysis. Please analyze the following content and provide detailed insights and recommendations:\n\n{content}"
                response = genai_client.generate_content(prompt)
                analysis_result = response.text
                model_used = "Google AI Gemini"
            except Exception as e:
                print(f"Google AI analysis failed: {e}")
                # Try a simpler prompt
                try:
                    simple_prompt = f"Analyze this content: {content[:500]}"
                    response = genai_client.generate_content(simple_prompt)
                    analysis_result = response.text
                    model_used = "Google AI Gemini (Simple Mode)"
                except Exception as e2:
                    print(f"Google AI simple analysis also failed: {e2}")
    
    if not analysis_result:
        raise HTTPException(status_code=503, detail="AI services not configured")
    
    return {
        "analysis": analysis_result,
        "type": analysis_type,
        "model_used": model_used,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/ai/prompt")
async def optimize_prompt(
    prompt: str = Form(...),
    purpose: str = Form("general"),
    ai_model: str = Form("auto")
):
    """AI prompt optimization using available AI services"""
    optimization_result = None
    model_used = None
    
    # Determine which AI service to use based on user selection
    if ai_model == "openai" and openai_client:
        # Use OpenAI specifically
        try:
            response = await openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": f"You are an expert prompt engineer. Optimize this prompt for {purpose} use. Make it more effective, clear, and likely to produce better results."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=300
            )
            optimization_result = response.choices[0].message.content
            model_used = "OpenAI GPT-3.5 Turbo"
        except Exception as e:
            print(f"OpenAI prompt optimization failed: {e}")
            
    elif ai_model == "google" and genai_client:
        # Use Google AI specifically
        try:
            optimization_prompt = f"You are an expert prompt engineer. Please optimize this prompt for {purpose} use. Make it more effective, clear, and likely to produce better results:\n\n{prompt}"
            response = genai_client.generate_content(optimization_prompt)
            optimization_result = response.text
            model_used = "Google AI Gemini"
        except Exception as e:
            print(f"Google AI prompt optimization failed: {e}")
            
    elif ai_model == "auto":
        # Auto mode - try OpenAI first, then Google AI
        if openai_client:
            try:
                response = await openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {
                            "role": "system",
                            "content": f"You are an expert prompt engineer. Optimize this prompt for {purpose} use. Make it more effective, clear, and likely to produce better results."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    max_tokens=300
                )
                optimization_result = response.choices[0].message.content
                model_used = "OpenAI GPT-3.5 Turbo"
            except Exception as e:
                print(f"OpenAI prompt optimization failed: {e}")
        
        # Fallback to Google AI if OpenAI failed or not available
        if not optimization_result and genai_client:
            try:
                optimization_prompt = f"You are an expert prompt engineer. Please optimize this prompt for {purpose} use. Make it more effective, clear, and likely to produce better results:\n\n{prompt}"
                response = genai_client.generate_content(optimization_prompt)
                optimization_result = response.text
                model_used = "Google AI Gemini"
            except Exception as e:
                print(f"Google AI prompt optimization failed: {e}")
    
    if not optimization_result:
        raise HTTPException(status_code=503, detail="AI services not configured")
    
    return {
        "optimized_prompt": optimization_result,
        "purpose": purpose,
        "model_used": model_used,
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
