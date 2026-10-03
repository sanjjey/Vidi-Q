# VIDI-Q: AI-Powered Multilingual Educational Video Platform

VIDI-Q is a high-performance educational video generation platform that converts any complex concept into synchronized, mathematical animations using **Manim Community Edition** and **manim-voiceover**. 

It features an asynchronous **FastAPI** backend with HTTP 206 byte-range streaming, multi-tier LLM failover (**Gemini 2.5 Flash → Groq GPT-OSS 120B → Local Ollama**), multi-language narration with colloquial **hybrid code-mixing** (e.g. Tanglish, Hinglish), and dynamic **pedagogical depth selection** (surface, detailed, in-depth).

---

## ⚡ Core Features

- **Multi-Provider LLM Failover**: Automatically cascades across providers to prevent downtime:
  1. Google Gemini (`gemini-2.5-flash`)
  2. Groq Cloud (`openai/gpt-oss-120b`, 131k context)
  3. Local Ollama (`llama3` / `qwen2.5:7b` via `http://localhost:11434/v1`)
- **Multilingual & Hybrid Code-Mixing**:
  - Supports 9+ languages (English, Tamil, Hindi, Spanish, French, German, Japanese, Italian, Portuguese).
  - **Conversational Hybrid Mode**: Uses natural colloquial sentence structure (Tanglish/Hinglish) while keeping technical scientific terms (*"Black Hole"*, *"Event Horizon"*, *"Gravity"*) in standard English.
  - Automatic unicode font injection (`Nirmala UI` for Indic scripts, `Yu Gothic` for Japanese) to prevent tofu boxes (`□□□`).
- **Adjustable Pedagogical Depth**:
  - ⚡ **Surface Level** (~30–60s): 3 sections, punchy visual metaphor.
  - 📖 **Detailed** (~2–3 min): 5–6 sections, step-by-step mechanism, practical examples, formulas.
  - 🔬 **In-Depth** (~4–6 min): 7–9 sections, first-principles derivation, animated simulation, edge cases.
- **FastAPI Asynchronous Engine**:
  - Non-blocking Manim rendering via threadpools.
  - Server-Sent Events (SSE) for live, real-time generation progress updates.
  - Native **HTTP 206 Partial Content** byte-range video streaming for instantaneous browser scrubbing.
- **Dual Database Architecture**:
  - Works with local PostgreSQL (`psycopg2`) or standalone fallback SQLite (`vidi_q_local.db`) with zero external setup needed.
  - Supabase client integration for cloud auth & storage.
- **Smart Cleanup & Caching**:
  - Automatic purge of Manim partial chunk files (`uncached_*.mp4`) saving 100–300MB disk per generation.
  - Multi-dimensional cache key based on `{topic}_{language}_{quality}_{depth}`.
- **Interactive Quiz Generator**:
  - Automatically synthesizes 4 multiple-choice questions from video transcripts in the selected language and depth.

---

## 🛠️ Prerequisites

- **Python 3.10+** (Tested on Python 3.11)
- **FFmpeg** installed and added to system `PATH`
- At least one LLM API key (**Google Gemini** or **Groq**) or a running **Ollama** instance

---

## ⚙️ Environment Variables

Create a `.env` file in the root directory:

```env
# Server
PORT=5000
DEFAULT_LLM_PROVIDER=gemini

# Google Gemini
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash

# Groq Cloud
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=openai/gpt-oss-120b

# Local Ollama (Optional)
LOCAL_LLM_URL=http://localhost:11434/v1
LOCAL_LLM_MODEL=llama3

# Database (PostgreSQL or SQLite fallback)
DB_MODE=postgres
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/vidi_q

# External Integrations (Optional)
ZAPIER_WEBHOOK_URL=your_zapier_webhook_url_here
SUPABASE_URL=your_supabase_url_here
SUPABASE_ANON_KEY=your_supabase_anon_key_here
```

---

## 🚀 Installation & Setup

1. **Clone repository**:
   ```bash
   git clone <repository-url>
   cd VIDI-Q
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Verify FFmpeg**:
   ```bash
   ffmpeg -version
   ```

4. **Start the FastAPI server**:
   ```bash
   python server.py
   ```
   The backend will start at `http://127.0.0.1:5000` (or `http://localhost:5000`).

5. **Launch the Web Interface**:
   Open `index.html` directly in your browser or serve it with any local static server.

---

## 📡 API Reference

### 1. Video Generation
- **`POST /api/generate-video`**
  - **Request Body**:
    ```json
    {
      "prompt": "How does Gravity work?",
      "provider": "gemini",
      "quality": "draft",
      "language": "ta",
      "voice_tld": "co.in",
      "depth": "detailed",
      "job_id": "optional-uuid"
    }
    ```
  - **Options**:
    - `provider`: `"gemini"`, `"groq"`, `"local"`
    - `quality`: `"draft"` (480p), `"medium"` (720p), `"high"` (1080p)
    - `language`: `"en"`, `"ta"`, `"hi"`, `"es"`, `"fr"`, `"de"`, `"ja"`, `"it"`, `"pt"`
    - `voice_tld`: `"com"` (US), `"co.in"` (Indian), `"co.uk"` (British), `"com.au"` (Aussie), `"ca"` (Canadian)
    - `depth`: `"surface"` (~30-60s), `"detailed"` (~2-3m), `"indepth"` (~4-6m)
  - **Response**:
    ```json
    {
      "video_url": "/videos/how_does_gravity_work/720p30/HowDoesGravityWorkScene.mp4",
      "caption_content": "[SRT / VTT subtitles]",
      "title": "How does Gravity work?",
      "provider": "gemini",
      "language": "ta",
      "quality": "medium",
      "depth": "detailed"
    }
    ```

### 2. Live Progress Stream (SSE)
- **`GET /api/stream-progress/{job_id}`**
  - Streams real-time pipeline status events (`"Generating animation script..."`, `"Rendering Manim animation..."`).

### 3. Video Streaming
- **`GET /videos/{script_name}/{resolution}/{filename}`**
  - Streams video with native **HTTP 206 Partial Content** byte-range support for smooth timeline scrubbing.

### 4. Quiz Generation
- **`POST /api/generate-quiz`**
  - **Request Body**:
    ```json
    {
      "caption_content": "Transcript text...",
      "video_id": "video_id",
      "language": "ta"
    }
    ```

### 5. Authentication (Local & Cloud)
- **`POST /api/auth/login`** - Authenticate email/password
- **`POST /api/auth/register`** (or `/api/auth/signup`) - Register new account
- **`GET /api/auth/session`** - Validate session

---

## 📂 Project Architecture

```
VIDI-Q/
├── server.py               # FastAPI backend with SSE and HTTP 206 streaming
├── main.py                 # Core Manim execution, retry loop, and cache pipeline
├── llm_handler.py          # LLM orchestrator (Gemini/Groq/Ollama, hybrid prompts, font guard)
├── db.py                   # Unified DB layer (PostgreSQL with SQLite fallback)
├── config.py               # Environment configuration and path management
├── index.html              # Modern dark-mode React/Tailwind frontend interface
├── generation_cache.json   # Video cache index
├── requirements.txt        # Python package dependencies
└── media/                  # Output directory for rendered videos and subtitles
```

---

## 🛡️ Robustness & Anti-Crash Design

1. **Zero LaTeX Crashes**: LaTeX is omitted in favor of Unicode rendering (`Text("E = mc²")`) to ensure 100% crash-free execution on standard Windows/Linux/macOS machines.
2. **API Hallucination Guards**: Automatic regex cleanup catches and fixes hallucinated method calls (e.g. `add_voiceover_service` → `set_speech_service`).
3. **Indic Script Rendering**: Dynamically sets Windows system fonts (`Nirmala UI`) preventing missing glyph tofu boxes (`□□□`).
4. **Subprocess Sanitization**: Encodes stdout/stderr with UTF-8 `replace` error-handling to prevent Windows OEM/CP1252 character decode crashes.
