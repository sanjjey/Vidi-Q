import os
import glob
import re
import requests
from pathlib import Path
import traceback
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import main as video_generator # Imports the logic from your main.py
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
# Enable Cross-Origin Resource Sharing to allow your frontend to call the backend
CORS(app, origins="*")

# The base directory where Manim saves its output files ('media/videos/')
VIDEO_DIR = Path(__file__).parent / "media" / "videos"

# --- Helper Functions for Formatting ---

def snake_to_pascal(snake_case_string):
    """Converts a snake_case string to PascalCase."""
    return "".join(word.capitalize() for word in snake_case_string.split('_'))

def snake_to_title(snake_case_string):
    """Converts a snake_case string to Title Case."""
    return " ".join(word.capitalize() for word in snake_case_string.split('_'))

# --- NEW: API Endpoint to List Existing Videos ---
@app.route('/send-to-zapier', methods=['POST'])
def send_to_zapier():
    data = request.json
    
    # Log the received data for debugging
    print("Received data:", data)

    # Send the received data to Zapier's Webhook
    zapier_webhook_url = os.getenv("ZAPIER_WEBHOOK_URL")
    if not zapier_webhook_url:
        return jsonify({"message": "Zapier webhook URL not configured"}), 500
    zapier_response = requests.post(zapier_webhook_url, json=data)
    
    # Check if the Zapier request was successful
    if zapier_response.status_code == 200:
        # Return a successful message to the frontend
        return jsonify({"message": "Data sent to Zapier successfully!"}), 200
    else:
        # Return an error message if Zapier failed to process the data
        return jsonify({"message": "Failed to send data to Zapier", "error": zapier_response.text}), 500

@app.route('/api/list-videos', methods=['GET'])
def list_videos():
    """
    Scans the VIDEO_DIR for existing video folders and returns a list of their metadata.
    """
    videos = []
    # Use the VIDEO_DIR path defined above, converting it to a string for glob
    search_path = os.path.join(str(VIDEO_DIR), "generated_*")
    
    for folder_path in glob.glob(search_path):
        if os.path.isdir(folder_path):
            try:
                folder_name = os.path.basename(folder_path)
                # The video_id is the part after 'generated_', e.g., 'alphabets'
                video_id = folder_name.replace("generated_", "")

                video_file_name = f"{snake_to_pascal(video_id)}.mp4"
                video_file_path = os.path.join(folder_path, "480p15", video_file_name)

                if os.path.exists(video_file_path):
                    creation_time = os.path.getctime(video_file_path)
                    videos.append({
                        "id": video_id,
                        "title": snake_to_title(video_id),
                        "created_at": creation_time * 1000 # JS uses milliseconds
                    })
            except Exception as e:
                print(f"Could not process folder {folder_path}: {e}")

    videos.sort(key=lambda v: v['created_at'], reverse=True)
    return jsonify(videos)

# --- NEW: API Endpoint to Get Details for a Single Video ---

@app.route('/api/video-details/<video_id>', methods=['GET'])
def get_video_details(video_id):
    """
    Returns detailed information for a single existing video, including its caption content.
    """
    folder_name = f"generated_{video_id}"
    pascal_case_id = snake_to_pascal(video_id)
    video_file = f"{pascal_case_id}.mp4"
    caption_file = f"{pascal_case_id}.srt"
    
    # Construct paths using the robust VIDEO_DIR Path object
    video_folder_path = VIDEO_DIR / folder_name / "480p15"
    video_file_path = video_folder_path / video_file
    caption_file_path = video_folder_path / caption_file

    if not video_file_path.exists():
        return jsonify({"error": "Video not found"}), 404

    caption_content = "Caption file not found."
    try:
        with open(caption_file_path, 'r', encoding='utf-8') as f:
            caption_content = f.read()
    except FileNotFoundError:
        print(f"Warning: Caption file not found at {caption_file_path}")
    except Exception as e:
        print(f"Error reading caption file {caption_file_path}: {e}")
        caption_content = "Error reading caption file."

    video_details = {
        "id": video_id,
        "title": snake_to_title(video_id),
        # This URL path MUST match your existing `serve_video` endpoint structure
        "video_file_url": f"/videos/{folder_name}/480p15/{video_file}",
        "caption_content": caption_content
    }
    return jsonify(video_details)

# --- Public config for frontend (safe values only) ---
@app.route('/api/public-config', methods=['GET'])
def public_config():
    import os
    return jsonify({
        "SUPABASE_URL": os.getenv("SUPABASE_URL"),
        "SUPABASE_ANON_KEY": os.getenv("SUPABASE_ANON_KEY"),
    })

# --- Proxy: Generate quiz using Gemini API (server-side key) ---
@app.route('/api/generate-quiz', methods=['POST'])
def generate_quiz():
    try:
        data = request.get_json(force=True)
        caption_content = data.get('caption_content', '')
        video_id = data.get('video_id', '')

        if not caption_content or not caption_content.strip():
            return jsonify({"error": "caption_content is required"}), 400
        if not video_id:
            return jsonify({"error": "video_id is required"}), 400

        import os
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return jsonify({"error": "GEMINI_API_KEY not configured"}), 500
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={api_key}"

        system_prompt = (
            "You are a quiz creator. Based on the transcript, create a JSON quiz with 4 multiple-"
            "choice questions. Each must have 'id', 'text', 'options' (array of 4 strings), and "
            "'answer'. Output only the JSON object."
        )
        user_query = f"Transcript:\n---\n{caption_content}\n---"

        payload = {
            "contents": [{"parts": [{"text": user_query}]}],
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": {
                    "type": "OBJECT",
                    "properties": {
                        "quiz_id": {"type": "STRING"},
                        "video_id": {"type": "STRING"},
                        "questions": {
                            "type": "ARRAY",
                            "items": {
                                "type": "OBJECT",
                                "properties": {
                                    "id": {"type": "NUMBER"},
                                    "text": {"type": "STRING"},
                                    "options": {"type": "ARRAY", "items": {"type": "STRING"}},
                                    "answer": {"type": "STRING"}
                                },
                                "required": ["id", "text", "options", "answer"]
                            }
                        }
                    },
                    "required": ["quiz_id", "video_id", "questions"]
                }
            }
        }

        resp = requests.post(api_url, json=payload, headers={"Content-Type": "application/json"}, timeout=60)
        if not resp.ok:
            print("Gemini API error:", resp.status_code, resp.text)
            return jsonify({"error": f"Gemini API error {resp.status_code}", "details": resp.text}), resp.status_code

        result = resp.json()
        json_text = (
            result.get('candidates', [{}])[0]
                  .get('content', {})
                  .get('parts', [{}])[0]
                  .get('text')
        )
        if not json_text:
            return jsonify({"error": "No quiz data returned from Gemini"}), 502

        try:
            quiz_data = requests.utils.json.loads(json_text)
        except Exception:
            # Fallback to std json if requests.utils not suitable
            import json as _json
            try:
                quiz_data = _json.loads(json_text)
            except Exception as e:
                return jsonify({"error": "Failed to parse quiz JSON", "details": str(e)}), 502

        if not isinstance(quiz_data.get('questions'), list) or not quiz_data['questions']:
            return jsonify({"error": "Invalid quiz format from Gemini"}), 502

        quiz_data['video_id'] = video_id
        if 'quiz_id' not in quiz_data or not quiz_data['quiz_id']:
            quiz_data['quiz_id'] = f"quiz_{video_id}"

        return jsonify(quiz_data)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

# --- EXISTING: Endpoint to Serve Video Files ---

@app.route('/videos/<script_name>/<resolution>/<filename>')
def serve_video(script_name, resolution, filename):
    """
    Serves the video file from the complex directory structure that Manim creates.
    e.g., /videos/generated_fouriertransform/480p15/FourierTransform.mp4
    """
    directory_to_serve = VIDEO_DIR / script_name / resolution
    print(f"Serving file: {filename} from {directory_to_serve}")
    return send_from_directory(directory_to_serve, filename)

# --- EXISTING: Endpoint to Generate New Videos ---

@app.route('/api/generate-video', methods=['POST'])
def generate_video_endpoint():
    """
    API endpoint that receives a prompt from the frontend and initiates
    the video generation process.
    """
    data = request.get_json()
    prompt = data.get('prompt')

    if not prompt:
        return jsonify({"error": "Prompt is required"}), 400

    try:
        # Sanitize the prompt to create a valid Python module name (e.g., "fourier_transform")
        sanitized_topic_module = re.sub(r'[^a-zA-Z0-9_]', '', prompt.replace(' ', '_')).lower()
        
        # This function handles the entire backend process
        path_parts, transcript = video_generator.generate_video_process(prompt, sanitized_topic_module)
        
        # Construct the URL that the frontend can use to fetch the video.
        # This now directly matches the '/videos/...' route.
        video_url = "/videos/" + "/".join(str(p) for p in path_parts)

        return jsonify({
            "video_url": video_url,
            "caption_content": transcript,
            "title": prompt
        })

    except Exception as e:
        # Print the full error to the console for easier debugging
        print("An error occurred during video generation:")
        traceback.print_exc()
        # Return a more informative error message to the frontend
        error_message = f"An internal error occurred: {str(e)}"
        # Check for a specific common error
        if "Manim failed after all retry attempts" in str(e):
            error_message = "The AI failed to generate a valid animation script after multiple attempts. Please try a different or more specific prompt."

        return jsonify({"error": error_message}), 500

if __name__ == '__main__':
    # Runs the server on http://localhost:5000
    print(f"Starting Flask server...")
    print(f"Video directory set to: {VIDEO_DIR.resolve()}")
    app.run(debug=True, port=5000, use_reloader=False)

