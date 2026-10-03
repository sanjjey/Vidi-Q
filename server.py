import os
import re
import glob
import json
import uuid
import asyncio
import traceback
from pathlib import Path
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, Request, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool
import httpx
import uvicorn

import config
from config import DB_CONFIG, LLM_CONFIG
import db
import main as video_generator
import llm_handler
from llm_handler import SUPPORTED_LANGUAGES, SUPPORTED_VOICE_TLDS

# --- App Initialization ---
app = FastAPI(title="VIDI-Q Engine", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

VIDEO_DIR = Path("media/videos")

# In-memory progress tracking for SSE (Job ID -> List of progress messages)
job_events: Dict[str, asyncio.Queue] = {}

def update_job_status(job_id: str, message: str):
    if job_id and job_id in job_events:
        try:
            job_events[job_id].put_nowait(message)
        except Exception:
            pass

def snake_to_title(snake_str: str) -> str:
    return ' '.join(word.capitalize() for word in snake_str.split('_'))

# --- Root & Static Video Serving with HTTP 206 Partial Content ---

@app.get("/")
async def serve_index():
    index_path = Path("index.html")
    if index_path.exists():
        return FileResponse(index_path, media_type="text/html")
    return {"message": "VIDI-Q API running"}

@app.get("/videos/{file_path:path}")
async def serve_video_stream(file_path: str):
    full_path = (VIDEO_DIR / file_path).resolve()
    if not full_path.exists() or not full_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    # FileResponse natively supports HTTP 206 Byte-Range requests in Starlette/FastAPI
    media_type = "video/mp4" if full_path.suffix == ".mp4" else "text/plain"
    return FileResponse(full_path, media_type=media_type)

# --- Configuration for Frontend ---

@app.get("/api/public-config")
async def public_config():
    return {
        "db_mode": DB_CONFIG["mode"],
        "active_db": db.ACTIVE_DB_TYPE,
        "SUPABASE_URL": DB_CONFIG["supabase_url"],
        "SUPABASE_ANON_KEY": DB_CONFIG["supabase_anon_key"],
        "default_llm_provider": LLM_CONFIG["default_provider"],
        "available_providers": [
            {"id": "gemini", "name": "⚡ Google Gemini (2.5 Flash)", "default_model": LLM_CONFIG["gemini"]["model"]},
            {"id": "groq", "name": "🚀 Groq (GPT-OSS 120B)", "default_model": LLM_CONFIG["groq"]["model"]},
            {"id": "local", "name": "💻 Local Model (Ollama / LocalAI)", "default_model": LLM_CONFIG["local"]["model"]}
        ],
        "supported_languages": [
            {"code": code, "name": name} for code, name in SUPPORTED_LANGUAGES.items()
        ],
        "supported_voices": [
            {"tld": tld, "name": name} for tld, name in SUPPORTED_VOICE_TLDS.items()
        ],
        "quality_options": [
            {"id": "draft", "name": "⚡ Draft (480p @ 15fps - Fastest)", "folder": "480p15"},
            {"id": "medium", "name": "🎬 Balanced (720p @ 30fps)", "folder": "720p30"},
            {"id": "high", "name": "🌟 HD (1080p @ 60fps)", "folder": "1080p60"}
        ]
    }

# --- SSE Progress Stream ---

@app.get("/api/stream-progress/{job_id}")
async def stream_progress(job_id: str):
    """Streams real-time generation phase progress events to frontend via SSE."""
    if job_id not in job_events:
        job_events[job_id] = asyncio.Queue()

    queue = job_events[job_id]

    async def event_generator():
        try:
            while True:
                # Wait for next status update with timeout
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=120.0)
                    yield f"data: {json.dumps({'message': msg})}\n\n"
                    if "Completed" in msg or "failed" in msg.lower():
                        break
                except asyncio.TimeoutError:
                    yield f"data: {json.dumps({'message': 'Processing...'})}\n\n"
        finally:
            if job_id in job_events:
                del job_events[job_id]

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# --- Authentication Endpoints ---

@app.post("/api/auth/signup")
@app.post("/api/auth/register")
async def register(request: Request):
    data = await request.json()
    email = data.get("email")
    password = data.get("password")
    name = data.get("name", "")
    phone = data.get("phone", "")

    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password are required")

    user, err = db.create_user(email, password, name, phone)
    if err:
        raise HTTPException(status_code=400, detail=err)

    session_data = {
        "user": user,
        "access_token": str(uuid.uuid4()),
        "token_type": "bearer"
    }
    return {
        "message": "Registration successful",
        "user": user,
        "session": session_data,
        "data": session_data
    }

@app.post("/api/auth/login")
async def login(request: Request):
    data = await request.json()
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password are required")

    user, err = db.authenticate_user(email, password)
    if err or not user:
        raise HTTPException(status_code=401, detail=err or "Invalid email or password")

    session_data = {
        "user": user,
        "access_token": str(uuid.uuid4()),
        "token_type": "bearer"
    }
    return {
        "message": "Login successful",
        "user": user,
        "session": session_data,
        "data": session_data
    }

# --- Video Generation Endpoint ---

@app.post("/api/generate-video")
async def generate_video_endpoint(request: Request):
    data = await request.json()
    prompt = data.get("prompt")
    provider = data.get("provider") or LLM_CONFIG["default_provider"]
    model = data.get("model")
    user_id = data.get("user_id")
    quality = data.get("quality", "draft")
    language = data.get("language", "en")
    voice_tld = data.get("voice_tld", "com")
    depth = data.get("depth", "surface")
    job_id = data.get("job_id") or str(uuid.uuid4())

    if not prompt or not prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt is required")

    sanitized_topic_module = re.sub(r'[^a-zA-Z0-9_]', '', prompt.replace(' ', '_')).lower()

    if job_id not in job_events:
        job_events[job_id] = asyncio.Queue()

    def progress_callback(msg: str):
        update_job_status(job_id, msg)

    try:
        progress_callback("Initializing generator...")
        # Run non-blocking in threadpool so concurrent requests aren't frozen
        path_parts, transcript = await run_in_threadpool(
            video_generator.generate_video_process,
            topic=prompt,
            sanitized_topic_module=sanitized_topic_module,
            llm_provider=provider,
            llm_model=model,
            quality=quality,
            language=language,
            voice_tld=voice_tld,
            depth=depth,
            status_callback=progress_callback
        )

        video_url = "/videos/" + "/".join(str(p) for p in path_parts)

        # Save to database
        db.save_video_record(
            video_id=sanitized_topic_module,
            title=prompt,
            prompt=prompt,
            video_url=video_url,
            caption_content=transcript,
            user_id=user_id
        )

        progress_callback("Completed! Loading video...")

        return {
            "video_url": video_url,
            "caption_content": transcript,
            "title": prompt,
            "provider": provider,
            "language": language,
            "quality": quality,
            "depth": depth
        }

    except Exception as e:
        print("An error occurred during video generation:")
        traceback.print_exc()
        progress_callback(f"Generation failed: {str(e)}")
        error_msg = f"Generation Failed: {str(e)}"
        if "Manim failed after all retry attempts" in str(e):
            error_msg = "The AI failed to generate a valid animation script after multiple attempts. Please try a different prompt."
        raise HTTPException(status_code=500, detail=error_msg)

# --- Video Listing & Details ---

@app.get("/api/list-videos")
async def list_videos():
    video_map = {}

    # 1. Fetch from DB
    try:
        db_videos = db.get_all_videos()
        for v in db_videos:
            video_map[v["id"]] = v
    except Exception as e:
        print(f"[DB Warning] Could not fetch videos from DB: {e}")

    # 2. Scan filesystem for rendered folders
    search_path = os.path.join(str(VIDEO_DIR), "generated_*")
    for folder_path in glob.glob(search_path):
        if os.path.isdir(folder_path):
            try:
                folder_name = os.path.basename(folder_path)
                video_id = folder_name.replace("generated_", "")
                
                # Check all resolution subfolders
                for res in ["480p15", "720p30", "1080p60"]:
                    res_path = os.path.join(folder_path, res)
                    mp4_files = glob.glob(os.path.join(res_path, "*.mp4"))
                    if mp4_files:
                        video_file_path = mp4_files[0]
                        video_file_name = os.path.basename(video_file_path)
                        creation_time = os.path.getctime(video_file_path) * 1000
                        if video_id not in video_map:
                            video_map[video_id] = {
                                "id": video_id,
                                "title": snake_to_title(video_id),
                                "created_at": creation_time,
                                "video_url": f"/videos/{folder_name}/{res}/{video_file_name}"
                            }
                        break
            except Exception as e:
                print(f"Could not process folder {folder_path}: {e}")

    videos = list(video_map.values())
    videos.sort(key=lambda v: v.get('created_at', 0), reverse=True)
    return videos

@app.get("/api/video-details/{video_id}")
async def get_video_details(video_id: str):
    db_rec = db.get_video_record(video_id)
    folder_name = f"generated_{video_id}"
    video_root = VIDEO_DIR / folder_name

    video_file_name = None
    res_subfolder = "480p15"
    caption_file_path = None

    if video_root.exists():
        for res in ["480p15", "720p30", "1080p60"]:
            res_dir = video_root / res
            if res_dir.exists():
                mp4_files = list(res_dir.glob("*.mp4"))
                if mp4_files:
                    video_file_name = mp4_files[0].name
                    res_subfolder = res
                    srt_files = list(res_dir.glob("*.srt"))
                    if srt_files:
                        caption_file_path = srt_files[0]
                    break

    if not video_file_name:
        if db_rec and db_rec.get("video_url"):
            return {
                "id": video_id,
                "title": db_rec.get("title") or snake_to_title(video_id),
                "video_file_url": db_rec["video_url"],
                "caption_content": db_rec.get("caption_content") or "Caption file not found."
            }
        raise HTTPException(status_code=404, detail="Video not found")

    caption_content = ""
    if caption_file_path and caption_file_path.exists():
        try:
            with open(caption_file_path, "r", encoding="utf-8", errors="replace") as f:
                caption_content = f.read()
        except Exception as e:
            print(f"Caption read notice: {e}")

    if not caption_content and db_rec:
        caption_content = db_rec.get("caption_content") or ""

    return {
        "id": video_id,
        "title": (db_rec.get("title") if db_rec else None) or snake_to_title(video_id),
        "video_file_url": f"/videos/{folder_name}/{res_subfolder}/{video_file_name}",
        "caption_content": caption_content or "Caption file not found."
    }

# --- Quiz Generation Endpoint ---

@app.post("/api/generate-quiz")
async def generate_quiz_endpoint(request: Request):
    try:
        data = await request.json()
        caption_content = data.get("caption_content", "")
        video_id = data.get("video_id", "")
        provider = data.get("provider") or LLM_CONFIG["default_provider"]
        model = data.get("model")
        language = data.get("language", "en")

        if not caption_content or not caption_content.strip():
            raise HTTPException(status_code=400, detail="caption_content is required")
        if not video_id:
            raise HTTPException(status_code=400, detail="video_id is required")

        # Check existing quiz in DB
        existing_quiz = db.get_quiz_record(video_id)
        if existing_quiz:
            return existing_quiz

        handler = llm_handler.LLMHandler(provider=provider, model=model)
        quiz_data = await run_in_threadpool(
            handler.generate_quiz,
            caption_content=caption_content,
            video_id=video_id,
            language=language
        )

        db.save_quiz_record(
            quiz_data.get("quiz_id", f"quiz_{video_id}"),
            video_id,
            quiz_data.get("questions", [])
        )

        return quiz_data
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Quiz generation failed: {str(e)}")

# --- Zapier Webhook Forwarder ---

@app.post("/send-to-zapier")
async def send_to_zapier(request: Request):
    zapier_webhook_url = "https://hooks.zapier.com/hooks/catch/23871271/2a9d86u/"
    data = await request.json()
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(zapier_webhook_url, json=data)
            if resp.status_code == 200:
                return {"message": "Data sent to Zapier successfully!"}
            return JSONResponse(status_code=500, content={"message": "Failed to send data to Zapier", "error": resp.text})
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": "Zapier request failed", "error": str(e)})

if __name__ == '__main__':
    print("Starting VIDI-Q FastAPI server on http://127.0.0.1:5000...")
    print(f"Database mode: {DB_CONFIG['mode']} (active: {db.ACTIVE_DB_TYPE})")
    print(f"Default LLM provider: {LLM_CONFIG['default_provider']}")
    uvicorn.run(app, host="127.0.0.1", port=5000)
