import sys
import subprocess
import re
import traceback
import shutil
import os
from pathlib import Path
import json
import llm_handler # Assumes llm_handler.py is in the same directory

# --- Ensure bundled FFmpeg is on PATH ---
try:
    import imageio_ffmpeg
    _ffmpeg_exe = Path(imageio_ffmpeg.get_ffmpeg_exe())
    _ffmpeg_dir = str(_ffmpeg_exe.parent)
    # Also ensure cwd (where we copy ffmpeg.exe) is on PATH
    _cwd = str(Path(__file__).parent.resolve())

    for _d in [_cwd, _ffmpeg_dir]:
        if _d not in os.environ.get("PATH", ""):
            os.environ["PATH"] = _d + os.pathsep + os.environ.get("PATH", "")

    # Create ffmpeg.exe alias in project dir if it doesn't exist yet
    _local_ffmpeg = Path(__file__).parent / "ffmpeg.exe"
    if not _local_ffmpeg.exists():
        import shutil as _sh
        _sh.copy(str(_ffmpeg_exe), str(_local_ffmpeg))
        print(f"[FFmpeg] Created local alias: {_local_ffmpeg}")

    print(f"[FFmpeg] Bundled binary: {_ffmpeg_exe}")
except Exception as _e:
    print(f"[FFmpeg Warning] Could not locate imageio_ffmpeg binary: {_e}")

CACHE_FILE = Path("generation_cache.json")

def load_cache():
    """Loads the generation cache from a JSON file."""
    if CACHE_FILE.exists():
        with open(CACHE_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_to_cache(key, data, cache):
    """Saves a new entry to the cache and writes it to the file."""
    cache[key] = data
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=4)

def parse_srt(file_path):
    """Parses a .srt file and returns the clean transcript text."""
    if not file_path.exists():
        print(f"Warning: SRT file not found at {file_path}")
        return "Transcript not found."
    try:
        content = file_path.read_text(encoding='utf-8', errors='replace')
    except Exception:
        content = file_path.read_text(errors='replace')
    # Handle both Windows CRLF (\r\n) and Unix LF (\n)
    text_only = re.sub(r'\d+\r?\n\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}\r?\n', '', content)
    return text_only.replace('\r\n', ' ').replace('\n', ' ').strip()

def find_scene_class_name(script_content):
    """Finds any class name that inherits from VoiceoverScene in the script."""
    match = re.search(r"class\s+([a-zA-Z0-9_]+)\s*\(\s*VoiceoverScene\s*\):", script_content)
    if match:
        return match.group(1)
    raise ValueError("Could not find a 'class YourSceneName(VoiceoverScene):' in the Manim script.")

def run_manim_process(command):
    """
    Runs the Manim command, captures its output, and enforces a timeout to prevent freezes.
    Uses errors='replace' to avoid UnicodeDecodeError on Windows OEM/CP1252 output.
    """
    try:
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=300
        )
        
        if process.stdout:
            print(f"[Manim STDOUT]:\n{process.stdout.strip()}")
        if process.stderr:
            print(f"[Manim STDERR]:\n{process.stderr.strip()}")
        return process.returncode, process.stdout, process.stderr

    except subprocess.TimeoutExpired as e:
        print("[Manim ERROR]: Process timed out after 5 minutes.")
        return -1, e.stdout or "", e.stderr or "Manim process timed out and was terminated."

    except Exception as e:
        print(f"[Manim ERROR]: Unexpected error in Manim process: {e}")
        return -1, "", str(e)


def generate_video_process(topic, sanitized_topic_module, llm_provider=None, llm_model=None,
                           quality="draft", language="en", voice_tld="com", depth="surface", status_callback=None):
    """ 
    Orchestrates the entire video generation pipeline with retry, failover, and cleanup.
    Supports resolution quality (-pql, -pqm, -pqh), depth levels (surface, detailed, indepth), multi-language and voice accents.
    """
    # --- Quality mapping ---
    quality_map = {
        "draft": ("-pql", "480p15"),
        "medium": ("-pqm", "720p30"),
        "high": ("-pqh", "1080p60")
    }
    quality_flag, res_folder = quality_map.get(str(quality).lower(), ("-pql", "480p15"))

    # --- FFmpeg Check ---
    _ffmpeg_found = shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")
    if not _ffmpeg_found:
        try:
            import imageio_ffmpeg as _iio
            _ffmpeg_found = _iio.get_ffmpeg_exe()
        except Exception:
            pass
    if not _ffmpeg_found:
        raise RuntimeError("CRITICAL ERROR: FFmpeg not found on system PATH.")

    cache_key = f"{topic}_{language}_{quality}_{depth}"
    cache = load_cache()
    if cache_key in cache:
        cached_data = cache[cache_key]
        video_path = Path.cwd() / "media" / "videos" / "/".join(cached_data["video_path_parts"])
        if video_path.exists():
            print(f"--- Serving '{topic}' ({depth}) from cache. ---")
            if status_callback:
                status_callback("Serving from cache...")
            return cached_data["video_path_parts"], cached_data["transcript"]
        else:
            del cache[cache_key]

    llm = llm_handler.LLMHandler(provider=llm_provider, model=llm_model)
    print(f"Starting video generation for topic: {topic} (using {llm.provider}, lang: {language}, quality: {quality}, depth: {depth})")
    if status_callback:
        status_callback(f"Generating animation script with {llm.provider.upper()} ({depth} mode)...")

    sanitized_topic_class = re.sub(r'[^a-zA-Z0-9]', '', topic.title())
    if not sanitized_topic_class.endswith("Scene"):
        sanitized_topic_class = f"{sanitized_topic_class}Scene"
    script_name = f"generated_{sanitized_topic_module}"
    script_path = Path(f"{script_name}.py")
    
    manim_script_content = None
    last_error = ""
    
    # Retry loop (up to 4 attempts)
    for attempt in range(4):
        try:
            if attempt == 0:
                manim_script_content = llm.generate_content(
                    topic, sanitized_topic_class, language=language, voice_tld=voice_tld, depth=depth
                )
            else:
                print(f"\n--- RETRY ATTEMPT {attempt} ({llm.provider}) ---")
                if status_callback:
                    status_callback(f"Fixing script with AI (Attempt {attempt + 1})...")
                manim_script_content = llm.fix_code(manim_script_content, last_error)

            script_path.write_text(manim_script_content, encoding='utf-8')
            scene_class_name = find_scene_class_name(manim_script_content)

            manim_command = [
                sys.executable, "-m", "manim", quality_flag, str(script_path), scene_class_name, "--disable_caching"
            ]
            
            print(f"\n--- Running Manim (Attempt {attempt + 1}, {quality_flag}) ---")
            if status_callback:
                status_callback("Rendering Manim animation & synthesizing voiceover...")

            return_code, stdout, stderr = run_manim_process(manim_command)
            
            if return_code == 0:
                print("Manim rendering completed successfully.")
                if status_callback:
                    status_callback("Packaging video & transcript...")
                
                media_dir = Path.cwd() / "media" / "videos" / script_name / res_folder
                video_file = media_dir / f"{scene_class_name}.mp4"
                srt_file = media_dir / f"{scene_class_name}.srt"

                if not video_file.exists():
                    raise FileNotFoundError(f"Manim ran, but output video was not found at: {video_file}")

                # --- Optimization: Clean up intermediate partial chunks to prevent disk bloat ---
                partial_dir = media_dir / "partial_movie_files"
                if partial_dir.exists():
                    try:
                        shutil.rmtree(partial_dir, ignore_errors=True)
                        print(f"[Cleanup] Removed partial movie files in {partial_dir}")
                    except Exception as _ce:
                        print(f"[Cleanup Notice] Could not remove partial files: {_ce}")

                transcript = parse_srt(srt_file)
                video_path_parts = [script_name, res_folder, f"{scene_class_name}.mp4"]

                # Save to cache
                new_cache_entry = {
                    "video_path_parts": video_path_parts,
                    "transcript": transcript
                }
                save_to_cache(cache_key, new_cache_entry, cache)

                if script_path.exists():
                    script_path.unlink()
                
                return video_path_parts, transcript

            else:
                print(f"Manim failed with return code {return_code}.")
                # Strip harmless warnings (SoX, runpy) so AI sees true exception
                raw_err = stderr or stdout
                clean_err_lines = [
                    line for line in raw_err.splitlines()
                    if "sox" not in line.lower()
                    and "manim.__main__" not in line
                    and "proceed here:" not in line.lower()
                    and "http://sox" not in line.lower()
                    and "path variables" not in line.lower()
                ]
                last_error = "\n".join(clean_err_lines).strip() or raw_err 

        except Exception as e:
            print(f"An error occurred in the generation process: {e}")
            traceback.print_exc()
            last_error = traceback.format_exc()

    if script_path.exists():
        script_path.unlink()
    
    raise RuntimeError(f"Manim failed after all retry attempts. Last error: {last_error}")

