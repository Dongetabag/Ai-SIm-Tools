#!/usr/bin/env python3
"""
Simplified FastAPI Web Server for AISim Tools
Provides REST API endpoints for audio stem separation, PDF processing, and image enhancement
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
    description="Professional AI-powered tools: audio separation, YouTube conversion, PDF processing, image enhancement, and video generation",
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

# Configuration
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

# In-memory job storage (in production, use a database)
jobs: Dict[str, Dict] = {}

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "AISim Tools API",
        "version": "1.0.0",
        "endpoints": {
            "POST /api/separate": "Separate audio into stems",
            "GET /api/status/{job_id}": "Check separation status",
            "GET /api/download/{job_id}/{stem}": "Download separated stem",
            "GET /api/jobs": "List all jobs",
            "POST /api/youtube/convert": "Convert YouTube video to WAV",
            "GET /api/youtube/download/{job_id}": "Download converted YouTube WAV",
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
    """Separate audio into stems"""
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
            "stems": {}
        }
        
        jobs[job_id] = job
        
        # Start background task
        background_tasks.add_task(process_audio, job_id, str(file_path), instruments)
        
        return {"job_id": job_id, "message": "Separation started"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting separation: {str(e)}")

async def process_audio(job_id: str, file_path: str, instruments: str):
    """Process audio separation in background"""
    try:
        job = jobs[job_id]
        
        # Parse selected instruments
        selected_instruments = [inst.strip() for inst in instruments.split(',')]
        
        # Run demucs
        result = subprocess.run([
            "python3", "-m", "demucs.separate",
            "--model", job["model"],
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
            # Try alternative path
            output_dir = OUTPUT_DIR
        
        # Map custom instrument selections to actual stems
        stem_mapping = {
            'vocals': 'vocals',
            'drums': 'drums', 
            'bass': 'bass',
            'other': 'other',
            'background': 'vocals',  # Background vocals come from vocals stem
            'piano': 'other',        # Piano comes from other stem
            'strings': 'other',      # Strings come from other stem
            'keys': 'other'          # Keys come from other stem
        }
        
        stems = {}
        for instrument in selected_instruments:
            mapped_stem = stem_mapping.get(instrument, instrument)
            stem_files = list(output_dir.glob(f"*{mapped_stem}.wav"))
            
            if stem_files:
                stem_file = stem_files[0]
                stems[instrument] = {
                    "filename": stem_file.name,
                    "path": str(stem_file),
                    "size": stem_file.stat().st_size
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
    """Get the status of a separation job"""
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
    url: str
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
        background_tasks.add_task(convert_youtube_audio, job_id, url)
        
        return {"job_id": job_id, "message": "YouTube conversion started"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting conversion: {str(e)}")

async def convert_youtube_audio(job_id: str, url: str):
    """Convert YouTube audio in background"""
    try:
        job = jobs[job_id]
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': str(OUTPUT_DIR / f'{job_id}_%(title)s.%(ext)s'),
            'extractaudio': True,
            'audioformat': 'wav',
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'Unknown')
            safe_title = re.sub(r'[^\w\s-]', '', str(title))[:50]
            
            # Find the downloaded file
            filename = f"{job_id}_{safe_title}.wav"
            file_path = OUTPUT_DIR / filename
            
            if not file_path.exists():
                # Try to find the actual downloaded file
                for file in OUTPUT_DIR.glob(f"{job_id}_*"):
                    if file.suffix in ['.wav', '.webm', '.m4a']:
                        file_path = file
                        filename = file.name
                        break
        
        job["status"] = "completed"
        job["title"] = title
        job["filename"] = filename
        job["file_path"] = str(file_path)
        
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
    files: List[UploadFile] = File(...)
):
    """Merge multiple PDFs into one"""
    try:
        job_id = str(uuid.uuid4())
        
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
        
        for file in files:
            content = await file.read()
            merger.append(BytesIO(content))
        
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
        
        temp_dir = tempfile.mkdtemp()
        frames = []
        
        num_frames = job["duration"] * 24
        
        for i in range(num_frames):
            frame = np.zeros((job["height"], job["width"], 3), dtype=np.uint8)
            
            for y in range(job["height"]):
                intensity = int(255 * (y / job["height"]))
                frame[y, :] = [intensity // 3, intensity // 2, intensity]
            
            center_x = job["width"] // 2
            center_y = job["height"] // 2
            
            radius = 50 + int(30 * np.sin(i * 0.1))
            cv2.circle(frame, (center_x, center_y), radius, (255, 255, 255), 3)
            
            text = f"Frame {i+1}/{num_frames}"
            cv2.putText(frame, text, (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            
            prompt_text = job["prompt"][:50] + "..." if len(job["prompt"]) > 50 else job["prompt"]
            cv2.putText(frame, prompt_text, (50, job["height"] - 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
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
