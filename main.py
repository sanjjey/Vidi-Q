import subprocess
import re
import traceback
import shutil
from pathlib import Path
import json
import llm_handler # Assumes llm_handler.py is in the same directory

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
    content = file_path.read_text(encoding='utf-8')
    # Use regex to strip timestamps and line numbers, then join lines
    text_only = re.sub(r'\d+\n\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}\n', '', content)
    return text_only.replace('\n', ' ').strip()

def find_scene_class_name(script_content):
    """Finds any class name that inherits from VoiceoverScene in the script."""
    match = re.search(r"class\s+([a-zA-Z0-9_]+)\s*\(\s*VoiceoverScene\s*\):", script_content)
    if match:
        return match.group(1)
    raise ValueError("Could not find a 'class YourSceneName(VoiceoverScene):' in the Manim script.")

def run_manim_process(command):
    """
    Runs the Manim command, captures its output, and enforces a timeout to prevent freezes.
    """
    try:
        # Using subprocess.run is a simpler way to handle timeouts and capture output
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding='utf-8',
            timeout=300  # 5-minute timeout
        )
        
        # Print captured output for debugging
        if process.stdout:
            print(f"[Manim STDOUT]:\n{process.stdout.strip()}")
        if process.stderr:
            print(f"[Manim STDERR]:\n{process.stderr.strip()}")
        return process.returncode, process.stdout, process.stderr

    except subprocess.TimeoutExpired as e:
        print("[Manim ERROR]: Process timed out after 5 minutes. It was likely stuck on a network request or complex animation.")
        return -1, e.stdout or "", e.stderr or "Manim process timed out and was terminated."

    except Exception as e:
        print(f"[Manim ERROR]: An unexpected error occurred while running the Manim process: {e}")
        return -1, "", str(e)


def generate_video_process(topic, sanitized_topic_module):
    """ 
    Orchestrates the entire video generation pipeline with a retry/fix and caching mechanism.
    """
    # --- FFmpeg Check ---
    if shutil.which("ffmpeg") is None:
        raise RuntimeError(
            "CRITICAL ERROR: FFmpeg not found.\n"
            "Manim and manim-voiceover require FFmpeg to combine video and audio segments.\n"
            "Please download it from ffmpeg.org, install it, and add its 'bin' directory "
            "to your system's PATH environment variable before running the application again."
        )

    # --- Caching Logic ---
    cache = load_cache()
    if topic in cache:
        cached_data = cache[topic]
        # Verify that the cached file still exists
        video_path = Path.cwd() / "media" / "videos" / "/".join(cached_data["video_path_parts"])
        if video_path.exists():
            print(f"--- Serving '{topic}' from cache. ---")
            return cached_data["video_path_parts"], cached_data["transcript"]
        else:
            print(f"--- Cached file for '{topic}' not found. Regenerating. ---")
            # Invalidate this cache entry
            del cache[topic]


    llm = llm_handler.LLMHandler()
    
    print(f"Starting video generation for topic: {topic}")
    
    sanitized_topic_class = re.sub(r'[^a-zA-Z0-9]', '', topic.title())
    script_name = f"generated_{sanitized_topic_module}"
    script_path = Path(f"{script_name}.py")
    
    manim_script_content = None
    last_error = ""
    
    # Retry loop (up to 2 attempts)
    for attempt in range(4):
        try:
            if attempt == 0:
                print("Generating initial Manim script with Gemini...")
                manim_script_content = llm.generate_content(topic, sanitized_topic_class)
            else: # This is a retry attempt
                print(f"\n--- RETRY ATTEMPT {attempt} ---")
                manim_script_content = llm.fix_code(manim_script_content, last_error)

            script_path.write_text(manim_script_content, encoding='utf-8')
            print(f"Manim script saved to {script_path}")

            scene_class_name = find_scene_class_name(manim_script_content)
            print(f"Found Manim scene class: {scene_class_name}")

            manim_command = [
                "manim", "-pql", str(script_path), scene_class_name, "--disable_caching"
            ]
            
            print(f"\n--- Running Manim (Attempt {attempt + 1}) ---")
            print(f"Command: {' '.join(manim_command)}\n")
            
            return_code, stdout, stderr = run_manim_process(manim_command)
            
            print("\n--- Manim Finished ---")
            
            if return_code == 0:
                print("Manim rendering completed successfully.")
                
                media_dir = Path.cwd() / "media" / "videos" / script_name / "480p15"
                video_file = media_dir / f"{scene_class_name}.mp4"
                srt_file = media_dir / f"{scene_class_name}.srt"

                if not video_file.exists():
                    raise FileNotFoundError(f"Manim ran, but output video was not found at: {video_file}")
                
                print(f"Found video file: {video_file}")
                print(f"Found SRT file: {srt_file}")

                transcript = parse_srt(srt_file)
                video_path_parts = [script_name, "480p15", f"{scene_class_name}.mp4"]

                # --- Save to Cache on Success ---
                new_cache_entry = {
                    "video_path_parts": video_path_parts,
                    "transcript": transcript
                }
                save_to_cache(topic, new_cache_entry, cache)
                print(f"--- Saved '{topic}' to cache. ---")

                if script_path.exists():
                    script_path.unlink()
                
                return video_path_parts, transcript

            else:
                print(f"Manim failed with return code {return_code}.")
                last_error = stderr or stdout 

        except Exception as e:
            print(f"An error occurred in the generation process: {e}")
            traceback.print_exc()
            last_error = traceback.format_exc()

    # If the loop finishes without success
    if script_path.exists():
        script_path.unlink()
    
    raise RuntimeError(f"Manim failed after all retry attempts. Last error: {last_error}")

