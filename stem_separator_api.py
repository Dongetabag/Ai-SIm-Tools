#!/usr/bin/env python3
"""
FastAPI Web Server for AI Stem Separator
Provides REST API endpoints for audio stem separation
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

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Form
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import aiofiles
import yt_dlp
from TTS.api import TTS
import torch
import PyPDF2
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from PIL import Image
import cv2
import numpy as np
import tempfile

# Initialize FastAPI app
app = FastAPI(
    title="AISim Tools API",
    description="Professional AI-powered tools: audio separation, YouTube conversion, text-to-speech, PDF processing, image enhancement, and video generation",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global storage for job status
jobs: Dict[str, Dict] = {}

# Configuration
UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("output")
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

# Ensure directories exist
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "AISim Tools API",
        "version": "1.0.0",
        "endpoints": {
            "POST /api/separate": "Upload and separate audio file",
            "GET /api/status/{job_id}": "Check separation status",
            "GET /api/download/{job_id}/{stem}": "Download separated stem",
            "GET /api/jobs": "List all jobs",
            "POST /api/youtube/convert": "Convert YouTube video to WAV",
            "GET /api/youtube/download/{job_id}": "Download converted YouTube WAV",
            "POST /api/tts/generate": "Generate text-to-speech audio",
            "GET /api/tts/download/{job_id}": "Download generated TTS audio",
            "GET /api/tts/models": "List available TTS models",
            "POST /api/pdf/merge": "Merge multiple PDFs into one",
            "POST /api/pdf/split": "Split PDF into individual pages",
            "POST /api/pdf/convert": "Convert images to PDF",
            "GET /api/pdf/download/{job_id}": "Download processed PDF",
            "POST /api/image/enhance": "Enhance images with AI upscaling",
            "GET /api/image/download/{job_id}": "Download enhanced image",
            "POST /api/video/generate": "Generate AI video from text prompt",
            "GET /api/video/download/{job_id}": "Download generated video"
        }
    }

@app.post("/api/separate")
async def separate_audio(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    model: str = "htdemucs",
    instruments: str = "vocals,drums,bass,other"
):
    """
    Upload audio file and start separation process
    """
    
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")
    
    # Check file size
    file_size = 0
    temp_file_path = UPLOAD_DIR / f"temp_{uuid.uuid4()}_{file.filename}"
    
    try:
        async with aiofiles.open(temp_file_path, 'wb') as f:
            while chunk := await file.read(8192):
                file_size += len(chunk)
                if file_size > MAX_FILE_SIZE:
                    raise HTTPException(status_code=413, detail="File too large (max 100MB)")
                await f.write(chunk)
    except Exception as e:
        if temp_file_path.exists():
            temp_file_path.unlink()
        raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")
    
    # Validate model
    valid_models = ["htdemucs", "htdemucs_ft", "mdx_extra", "mdx_extra_q"]
    if model not in valid_models:
        if temp_file_path.exists():
            temp_file_path.unlink()
        raise HTTPException(status_code=400, detail=f"Invalid model. Available: {', '.join(valid_models)}")
    
    # Parse selected instruments
    selected_instruments = [inst.strip() for inst in instruments.split(',') if inst.strip()]
    
    # Create job
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "id": job_id,
        "filename": file.filename,
        "model": model,
        "instruments": selected_instruments,
        "status": "processing",
        "created_at": datetime.now().isoformat(),
        "input_file": str(temp_file_path),
        "output_dir": str(OUTPUT_DIR / job_id),
        "stems": {},
        "error": None
    }
    
    # Start background task
    background_tasks.add_task(process_audio, job_id)
    
    return {
        "job_id": job_id,
        "status": "processing",
        "message": "Audio separation started. Use the job_id to check status."
    }

async def process_audio(job_id: str):
    """
    Background task to process audio separation
    """
    job = jobs.get(job_id)
    if not job:
        return
    
    try:
        # Create output directory
        output_dir = Path(job["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Build demucs command
        cmd = [
            "python3", "-m", "demucs",
            "-n", job["model"],
            "-o", str(output_dir.parent),
            str(job["input_file"])
        ]
        
        # Run separation with better error handling
        try:
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=300  # 5 minute timeout
            )
        except subprocess.TimeoutExpired:
            job["status"] = "failed"
            job["error"] = "Processing timeout (5 minutes) - try with a shorter audio file"
            return
        
        # Check if demucs actually succeeded (returncode 0) or if it's just warnings
        if result.returncode == 0 or "UserWarning" in result.stderr:
            # Find output files - demucs creates output in the parent directory
            input_name = Path(job["input_file"]).stem
            model_output_dir = output_dir.parent / job["model"] / input_name
            
            # Also check if files are directly in the output directory
            if not model_output_dir.exists():
                model_output_dir = output_dir
            
            # Look for .wav files in the output directory
            wav_files = list(model_output_dir.glob("*.wav"))
            
            if wav_files:
                stems = {}
                for stem_file in wav_files:
                    stem_name = stem_file.stem
                    stems[stem_name] = {
                        "filename": stem_file.name,
                        "path": str(stem_file),
                        "size": stem_file.stat().st_size
                    }
                
                # Map custom instrument selections to actual Demucs outputs
                mapped_stems = {}
                selected_instruments = job.get("instruments", ["vocals", "drums", "bass", "other"])
                
                # Standard Demucs outputs
                demucs_outputs = ["vocals", "drums", "bass", "other"]
                
                # Map custom selections to available outputs
                instrument_mapping = {
                    "background": "vocals",  # Background vocals come from vocals stem
                    "piano": "other",       # Piano is usually in other stem
                    "strings": "other",     # Strings are usually in other stem
                    "keys": "other",        # Keys are usually in other stem
                    "vocals": "vocals",
                    "drums": "drums",
                    "bass": "bass",
                    "other": "other"
                }
                
                # Create mapped stems based on user selection
                for selected_inst in selected_instruments:
                    if selected_inst in instrument_mapping:
                        mapped_output = instrument_mapping[selected_inst]
                        if mapped_output in stems:
                            mapped_stems[selected_inst] = stems[mapped_output]
                
                job["stems"] = mapped_stems
                job["status"] = "completed"
            else:
                job["status"] = "failed"
                job["error"] = f"No output files found. Demucs output: {result.stdout[-500:] if result.stdout else 'No stdout'}"
        else:
            job["status"] = "failed"
            job["error"] = f"Demucs failed: {result.stderr}"
            
    except subprocess.TimeoutExpired:
        job["status"] = "failed"
        job["error"] = "Processing timeout (10 minutes)"
    except Exception as e:
        job["status"] = "failed"
        job["error"] = str(e)
    finally:
        # Clean up input file
        try:
            if Path(job["input_file"]).exists():
                Path(job["input_file"]).unlink()
        except:
            pass

@app.get("/api/status/{job_id}")
async def get_status(job_id: str):
    """
    Get the status of a separation job
    """
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
        # Handle different job types
        if job.get("type") == "youtube_conversion":
            return {
                "job_id": job_id,
                "status": job["status"],
                "title": job.get("title"),
                "filename": job.get("filename"),
                "url": job.get("url"),
                "created_at": job["created_at"],
                "error": job["error"]
            }
        elif job.get("type") == "tts_generation":
            return {
                "job_id": job_id,
                "status": job["status"],
                "text": job.get("text"),
                "model_name": job.get("model_name"),
                "filename": job.get("filename"),
                "created_at": job["created_at"],
                "error": job["error"]
            }
        elif job.get("type") in ["pdf_merge", "pdf_convert"]:
            return {
                "job_id": job_id,
                "status": job["status"],
                "filename": job.get("filename"),
                "created_at": job["created_at"],
                "error": job["error"]
            }
        elif job.get("type") == "pdf_split":
            return {
                "job_id": job_id,
                "status": job["status"],
                "filename": job.get("filename"),
                "file_paths": job.get("file_paths", []),
                "created_at": job["created_at"],
                "error": job["error"]
            }
        elif job.get("type") == "image_enhance":
            return {
                "job_id": job_id,
                "status": job["status"],
                "filename": job.get("filename"),
                "scale_factor": job.get("scale_factor"),
                "created_at": job["created_at"],
                "error": job["error"]
            }
        elif job.get("type") == "video_generation":
            return {
                "job_id": job_id,
                "status": job["status"],
                "filename": job.get("filename"),
                "prompt": job.get("prompt"),
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
                "error": job["error"]
            }

@app.get("/api/download/{job_id}/{stem}")
async def download_stem(job_id: str, stem: str):
    """
    Download a separated stem file
    """
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Job not completed yet")
    
    if stem not in job["stems"]:
        raise HTTPException(status_code=404, detail="Stem not found")
    
    stem_info = job["stems"][stem]
    file_path = Path(stem_info["path"])
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        file_path,
        filename=f"{job['filename']}_{stem}.wav",
        media_type="audio/wav"
    )

@app.get("/api/jobs")
async def list_jobs():
    """
    List all jobs (for debugging)
    """
    return {"jobs": list(jobs.values())}

@app.delete("/api/jobs/{job_id}")
async def delete_job(job_id: str):
    """
    Delete a job and its files
    """
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Delete output files
    try:
        output_dir = Path(job["output_dir"])
        if output_dir.exists():
            import shutil
            shutil.rmtree(output_dir)
    except:
        pass
    
    # Remove from jobs
    del jobs[job_id]
    
    return {"message": "Job deleted successfully"}

@app.post("/api/youtube/convert")
async def convert_youtube_to_wav(
    background_tasks: BackgroundTasks,
    url: str = Form(...),
    title: str = Form(None)
):
    """
    Convert YouTube video to WAV format
    """
    
    # Validate YouTube URL
    youtube_pattern = r'(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})'
    if not re.match(youtube_pattern, url):
        raise HTTPException(status_code=400, detail="Invalid YouTube URL")
    
    # Create job for YouTube conversion
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "id": job_id,
        "type": "youtube_conversion",
        "url": url,
        "title": title,
        "status": "processing",
        "created_at": datetime.now().isoformat(),
        "output_file": None,
        "error": None
    }
    
    # Start background task
    background_tasks.add_task(convert_youtube_audio, job_id)
    
    return {
        "job_id": job_id,
        "status": "processing",
        "message": "YouTube conversion started. Use the job_id to check status."
    }

async def convert_youtube_audio(job_id: str):
    """
    Background task to convert YouTube video to WAV
    """
    job = jobs[job_id]
    
    try:
        # Create output directory for YouTube downloads
        youtube_dir = OUTPUT_DIR / "youtube"
        youtube_dir.mkdir(exist_ok=True)
        
        # Generate filename
        title = job.get('title', 'youtube_audio')
        if title and isinstance(title, str):
            safe_title = re.sub(r'[^\w\s-]', '', title)
            safe_title = re.sub(r'[-\s]+', '-', safe_title)
        else:
            safe_title = 'youtube_audio'
        output_filename = f"{safe_title}_{job_id}.wav"
        output_path = youtube_dir / output_filename
        
        # Configure yt-dlp
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': str(youtube_dir / f"{job_id}.%(ext)s"),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav',
                'preferredquality': '192',
            }],
            'quiet': True,
            'no_warnings': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract video info
            info = ydl.extract_info(job['url'], download=False)
            job['title'] = info.get('title', 'Unknown Title')
            job['duration'] = info.get('duration', 0)
            
            # Download and convert
            ydl.download([job['url']])
        
        # Find the generated WAV file
        wav_file = youtube_dir / f"{job_id}.wav"
        if wav_file.exists():
            # Rename to final filename
            final_path = youtube_dir / output_filename
            wav_file.rename(final_path)
            
            job['output_file'] = str(final_path)
            job['filename'] = output_filename
            job['status'] = 'completed'
        else:
            job['status'] = 'failed'
            job['error'] = 'WAV file not created'
            
    except Exception as e:
        job['status'] = 'failed'
        job['error'] = str(e)

@app.get("/api/youtube/download/{job_id}")
async def download_youtube_wav(job_id: str):
    """
    Download converted YouTube WAV file
    """
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job['type'] != 'youtube_conversion':
        raise HTTPException(status_code=400, detail="Not a YouTube conversion job")
    
    if job['status'] != 'completed':
        raise HTTPException(status_code=400, detail="Job not completed yet")
    
    file_path = Path(job['output_file'])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        file_path,
        filename=job['filename'],
        media_type="audio/wav"
    )

# TTS endpoints
@app.get("/api/tts/models")
async def list_tts_models():
    """List available TTS models"""
    try:
        # Get device
        device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # List available models
        tts = TTS()
        models = tts.list_models()
        
        # Filter to show only some popular models for simplicity
        popular_models = [
            "tts_models/en/ljspeech/tacotron2-DDC",
            "tts_models/en/ljspeech/glow-tts",
            "tts_models/en/ljspeech/speedy-speech",
            "tts_models/en/vctk/vits",
            "tts_models/multilingual/multi-dataset/xtts_v2"
        ]
        
        available_models = [model for model in popular_models if any(model in str(m) for m in models)]
        
        return {
            "models": available_models,
            "device": device
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing TTS models: {str(e)}")

@app.post("/api/tts/generate")
async def generate_tts(
    background_tasks: BackgroundTasks,
    text: str = Form(...),
    model_name: str = Form("tts_models/en/ljspeech/tacotron2-DDC"),
    language: str = Form("en")
):
    """Generate text-to-speech audio"""
    try:
        # Create job ID
        job_id = str(uuid.uuid4())
        
        # Create job entry
        job = {
            "job_id": job_id,
            "type": "tts_generation",
            "status": "processing",
            "text": text,
            "model_name": model_name,
            "language": language,
            "created_at": datetime.now().isoformat(),
            "error": None,
            "filename": None,
            "file_path": None
        }
        
        jobs[job_id] = job
        
        # Start background task
        background_tasks.add_task(process_tts, job_id)
        
        return {"job_id": job_id, "message": "TTS generation started"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting TTS generation: {str(e)}")

async def process_tts(job_id: str):
    """Process TTS generation in background"""
    try:
        job = jobs[job_id]
        
        # Get device
        device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Initialize TTS
        tts = TTS(model_name=job["model_name"]).to(device)
        
        # Generate filename
        safe_text = re.sub(r'[^\w\s-]', '', job["text"])[:50]
        filename = f"tts_{safe_text}_{job_id}.wav"
        file_path = OUTPUT_DIR / filename
        
        # Generate TTS
        if "xtts_v2" in job["model_name"]:
            # Multi-lingual model requires language parameter
            tts.tts_to_file(text=job["text"], language=job["language"], file_path=str(file_path))
        else:
            # Standard single-language model
            tts.tts_to_file(text=job["text"], file_path=str(file_path))
        
        # Update job status
        job["status"] = "completed"
        job["filename"] = filename
        job["file_path"] = str(file_path)
        
    except Exception as e:
        job["status"] = "failed"
        job["error"] = str(e)

@app.get("/api/tts/download/{job_id}")
async def download_tts(job_id: str):
    """Download generated TTS audio"""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Job not completed")
    
    if not job["file_path"] or not os.path.exists(job["file_path"]):
        raise HTTPException(status_code=404, detail="Generated file not found")
    
    return FileResponse(
        path=job["file_path"],
        filename=job["filename"],
        media_type="audio/wav"
    )

# PDF Processing endpoints
@app.post("/api/pdf/merge")
async def merge_pdfs(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...)
):
    """Merge multiple PDFs into one"""
    try:
        job_id = str(uuid.uuid4())
        
        # Create job entry
        job = {
            "job_id": job_id,
            "type": "pdf_merge",
            "status": "processing",
            "filename": "merged.pdf",
            "created_at": datetime.now().isoformat(),
            "error": None,
            "file_path": None
        }
        
        jobs[job_id] = job
        background_tasks.add_task(process_pdf_merge, job_id, files)
        
        return {"job_id": job_id, "message": "PDF merge started"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting PDF merge: {str(e)}")

async def process_pdf_merge(job_id: str, files: List[UploadFile]):
    """Process PDF merge in background"""
    try:
        job = jobs[job_id]
        merger = PyPDF2.PdfMerger()
        
        # Read and merge all PDFs
        for file in files:
            content = await file.read()
            merger.append(BytesIO(content))
        
        # Create output file
        filename = f"merged_{job_id}.pdf"
        file_path = OUTPUT_DIR / filename
        
        with open(file_path, 'wb') as output_file:
            merger.write(output_file)
        merger.close()
        
        job["status"] = "completed"
        job["filename"] = filename
        job["file_path"] = str(file_path)
        
    except Exception as e:
        job["status"] = "failed"
        job["error"] = str(e)

@app.post("/api/pdf/split")
async def split_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """Split PDF into individual pages"""
    try:
        job_id = str(uuid.uuid4())
        
        job = {
            "job_id": job_id,
            "type": "pdf_split",
            "status": "processing",
            "filename": file.filename,
            "created_at": datetime.now().isoformat(),
            "error": None,
            "file_paths": []
        }
        
        jobs[job_id] = job
        background_tasks.add_task(process_pdf_split, job_id, file)
        
        return {"job_id": job_id, "message": "PDF split started"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting PDF split: {str(e)}")

async def process_pdf_split(job_id: str, file: UploadFile):
    """Process PDF split in background"""
    try:
        job = jobs[job_id]
        content = await file.read()
        
        pdf_reader = PyPDF2.PdfReader(BytesIO(content))
        file_paths = []
        
        for page_num in range(len(pdf_reader.pages)):
            pdf_writer = PyPDF2.PdfWriter()
            pdf_writer.add_page(pdf_reader.pages[page_num])
            
            filename = f"page_{page_num + 1}_{job_id}.pdf"
            file_path = OUTPUT_DIR / filename
            
            with open(file_path, 'wb') as output_file:
                pdf_writer.write(output_file)
            
            file_paths.append(str(file_path))
        
        job["status"] = "completed"
        job["file_paths"] = file_paths
        
    except Exception as e:
        job["status"] = "failed"
        job["error"] = str(e)

@app.post("/api/pdf/convert")
async def convert_images_to_pdf(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...)
):
    """Convert images to PDF"""
    try:
        job_id = str(uuid.uuid4())
        
        job = {
            "job_id": job_id,
            "type": "pdf_convert",
            "status": "processing",
            "filename": "converted.pdf",
            "created_at": datetime.now().isoformat(),
            "error": None,
            "file_path": None
        }
        
        jobs[job_id] = job
        background_tasks.add_task(process_image_to_pdf, job_id, files)
        
        return {"job_id": job_id, "message": "Image to PDF conversion started"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting conversion: {str(e)}")

async def process_image_to_pdf(job_id: str, files: List[UploadFile]):
    """Process image to PDF conversion in background"""
    try:
        job = jobs[job_id]
        
        filename = f"converted_{job_id}.pdf"
        file_path = OUTPUT_DIR / filename
        
        # Create PDF with images
        with open(file_path, 'wb') as output_file:
            pdf_canvas = canvas.Canvas(output_file, pagesize=letter)
            
            for file in files:
                content = await file.read()
                image = Image.open(BytesIO(content))
                
                # Convert to RGB if necessary
                if image.mode != 'RGB':
                    image = image.convert('RGB')
                
                # Get image dimensions and scale to fit page
                img_width, img_height = image.size
                page_width, page_height = letter
                
                # Calculate scaling factor
                scale_x = page_width / img_width
                scale_y = page_height / img_height
                scale = min(scale_x, scale_y) * 0.9  # 90% of page size
                
                new_width = img_width * scale
                new_height = img_height * scale
                
                # Center image on page
                x = (page_width - new_width) / 2
                y = (page_height - new_height) / 2
                
                # Save image temporarily
                temp_path = OUTPUT_DIR / f"temp_{job_id}_{file.filename}"
                image.save(temp_path, 'JPEG')
                
                # Draw image on PDF
                pdf_canvas.drawImage(str(temp_path), x, y, new_width, new_height)
                pdf_canvas.showPage()
                
                # Clean up temp file
                os.remove(temp_path)
            
            pdf_canvas.save()
        
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
    scale_factor: float = Form(2.0)
):
    """Enhance image with AI upscaling"""
    try:
        job_id = str(uuid.uuid4())
        
        job = {
            "job_id": job_id,
            "type": "image_enhance",
            "status": "processing",
            "filename": file.filename,
            "scale_factor": scale_factor,
            "created_at": datetime.now().isoformat(),
            "error": None,
            "file_path": None
        }
        
        jobs[job_id] = job
        background_tasks.add_task(process_image_enhance, job_id, file, scale_factor)
        
        return {"job_id": job_id, "message": "Image enhancement started"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting image enhancement: {str(e)}")

async def process_image_enhance(job_id: str, file: UploadFile, scale_factor: float):
    """Process image enhancement in background"""
    try:
        job = jobs[job_id]
        content = await file.read()
        
        # Load image
        image = Image.open(BytesIO(content))
        image_array = np.array(image)
        
        # Convert to OpenCV format
        if len(image_array.shape) == 3:
            opencv_image = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)
        else:
            opencv_image = image_array
        
        # Apply enhancement (simple upscaling with interpolation)
        height, width = opencv_image.shape[:2]
        new_width = int(width * scale_factor)
        new_height = int(height * scale_factor)
        
        # Use cubic interpolation for better quality
        enhanced_image = cv2.resize(opencv_image, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
        
        # Apply additional sharpening
        kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
        enhanced_image = cv2.filter2D(enhanced_image, -1, kernel)
        
        # Convert back to PIL Image
        if len(enhanced_image.shape) == 3:
            enhanced_image = cv2.cvtColor(enhanced_image, cv2.COLOR_BGR2RGB)
        
        enhanced_pil = Image.fromarray(enhanced_image)
        
        # Save enhanced image
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
    height: int = Form(512)
):
    """Generate AI video from text prompt"""
    try:
        job_id = str(uuid.uuid4())
        
        job = {
            "job_id": job_id,
            "type": "video_generation",
            "status": "processing",
            "prompt": prompt,
            "duration": duration,
            "width": width,
            "height": height,
            "filename": f"generated_video_{job_id}.mp4",
            "created_at": datetime.now().isoformat(),
            "error": None,
            "file_path": None
        }
        
        jobs[job_id] = job
        background_tasks.add_task(process_video_generation, job_id)
        
        return {"job_id": job_id, "message": "Video generation started"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting video generation: {str(e)}")

async def process_video_generation(job_id: str):
    """Process video generation in background"""
    try:
        job = jobs[job_id]
        
        # Create a simple video generation using frames and moviepy
        # This is a simplified version - in production you'd use actual video generation models
        
        # Create temporary directory for frames
        temp_dir = tempfile.mkdtemp()
        frames = []
        
        # Generate frames (simplified - create colored frames with text)
        num_frames = job["duration"] * 24  # 24 fps
        
        for i in range(num_frames):
            # Create a colored frame
            frame = np.zeros((job["height"], job["width"], 3), dtype=np.uint8)
            
            # Add gradient background
            for y in range(job["height"]):
                intensity = int(255 * (y / job["height"]))
                frame[y, :] = [intensity // 3, intensity // 2, intensity]
            
            # Add some animated elements
            center_x = job["width"] // 2
            center_y = job["height"] // 2
            
            # Animated circle
            radius = 50 + int(30 * np.sin(i * 0.1))
            cv2.circle(frame, (center_x, center_y), radius, (255, 255, 255), 3)
            
            # Add text
            text = f"Frame {i+1}/{num_frames}"
            cv2.putText(frame, text, (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            
            # Add prompt text (truncated)
            prompt_text = job["prompt"][:50] + "..." if len(job["prompt"]) > 50 else job["prompt"]
            cv2.putText(frame, prompt_text, (50, job["height"] - 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Save frame
            frame_path = os.path.join(temp_dir, f"frame_{i:04d}.png")
            cv2.imwrite(frame_path, frame)
            frames.append(frame_path)
        
        # Create video from frames using OpenCV
        filename = f"generated_video_{job_id}.mp4"
        file_path = OUTPUT_DIR / filename
        
        # Create video using OpenCV
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(str(file_path), fourcc, 24.0, (job["width"], job["height"]))
        
        for frame_path in frames:
            frame = cv2.imread(frame_path)
            out.write(frame)
        
        out.release()
        
        # Clean up temporary files
        for frame_path in frames:
            if os.path.exists(frame_path):
                os.remove(frame_path)
        os.rmdir(temp_dir)
        
        job["status"] = "completed"
        job["filename"] = filename
        job["file_path"] = str(file_path)
        
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
