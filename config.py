import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent
PROMPTS_DIR = BASE_DIR / "prompts"
TEMP_DIR = BASE_DIR / "temp"
OUTPUT_DIR = BASE_DIR / "output"

# Subdirectories
MANIM_SCRIPTS_DIR = TEMP_DIR / "manim_scripts"
AUDIO_FILES_DIR = TEMP_DIR / "audio_files"
VIDEO_FILES_DIR = TEMP_DIR / "video_files"

# Create directories if they don't exist
for directory in [PROMPTS_DIR, MANIM_SCRIPTS_DIR, AUDIO_FILES_DIR, VIDEO_FILES_DIR, OUTPUT_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# --- Database Configuration ---
DB_CONFIG = {
    # 'postgres' (local PostgreSQL) or 'supabase'
    "mode": os.getenv("DB_MODE", "postgres").lower(),
    "database_url": os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/vidi_q"),
    "supabase_url": os.getenv("SUPABASE_URL", ""),
    "supabase_anon_key": os.getenv("SUPABASE_ANON_KEY", "")
}

# --- Multi-Provider LLM Configuration ---
LLM_CONFIG = {
    "default_provider": os.getenv("DEFAULT_LLM_PROVIDER", "gemini").lower(),
    
    "gemini": {
        "api_key": os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or os.getenv("API_KEY", ""),
        "model": os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    },
    
    "groq": {
        "api_key": os.getenv("GROQ_API_KEY", ""),
        "model": os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    },
    
    "local": {
        "base_url": os.getenv("LOCAL_LLM_URL", "http://localhost:11434/v1"),
        "model": os.getenv("LOCAL_LLM_MODEL", "llama3"),
        "api_key": os.getenv("LOCAL_LLM_KEY", "ollama")
    }
}

# Legacy API_CONFIG alias for backward compatibility
API_CONFIG = {
    "api_key": LLM_CONFIG["gemini"]["api_key"],
    "model": LLM_CONFIG["gemini"]["model"]
}

# TTS Configuration (using pyttsx3 / gTTS)
TTS_CONFIG = {
    "rate": 150,    # Words per minute
    "volume": 0.9,  # Volume level (0.0 to 1.0)
}

# Manim Configuration
MANIM_CONFIG = {
    "quality": "high_quality",  # "low_quality", "medium_quality", "high_quality"
    "format": "mp4"
}


