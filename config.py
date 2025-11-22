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

# API Configuration

# --- API Configuration ---
# This is the central spot for your API settings.
API_CONFIG = {
    # It's crucial that your API_KEY is set in the .env file.
    "api_key": os.getenv("API_KEY"),
    
    # We specify the model here for easy swapping in the future.
    "model": "gemini-2.5-flash-preview-05-20",
}

# TTS Configuration (using pyttsx3)
TTS_CONFIG = {
    "rate": 150,    # Words per minute
    "volume": 0.9,  # Volume level (0.0 to 1.0)
}

# Manim Configuration
MANIM_CONFIG = {
    "quality": "high_quality",  # "low_quality", "medium_quality", "high_quality"
    "format": "mp4"
}


