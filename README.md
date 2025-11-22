# Educational Video Generator

An AI-powered educational video generation system that creates animated videos using Manim and integrates with Google Gemini for content generation. The system provides a Flask-based web API for generating, managing, and serving educational videos with voiceovers and quizzes.

## Features

- **AI-Powered Video Generation**: Uses Google Gemini to generate Manim scripts for educational content
- **Automatic Voiceover**: Integrates with Manim Voiceover for text-to-speech narration
- **Video Caching**: Intelligent caching system to avoid regenerating existing videos
- **Quiz Generation**: Automatic quiz creation based on video transcripts using Gemini API
- **Web API**: RESTful Flask API for video generation and management
- **Cross-Origin Support**: CORS-enabled for frontend integration
- **External Integrations**: Zapier webhook support for automation workflows
- **Supabase Integration**: Database support for user management and data storage

## Prerequisites

- Python 3.8+
- FFmpeg (required for Manim video processing)
- Google Gemini API key
- Node.js (for frontend development, if applicable)

## Environment Variables

Create a `.env` file in the root directory of the project and add the following environment variables:

```env
GEMINI_API_KEY=your_gemini_api_key_here
ZAPIER_WEBHOOK_URL=your_zapier_webhook_url_here
SUPABASE_URL=your_supabase_url_here
SUPABASE_ANON_KEY=your_supabase_anon_key_here
```

- `GEMINI_API_KEY`: Your Google Gemini API key for AI-powered content generation **(Give the same in index.html file at line 191 and llm_handler.py at line 7)**
- `ZAPIER_WEBHOOK_URL`: Your Zapier webhook URL for automation workflows
- `SUPABASE_URL`: Your Supabase project URL for database integration **(Give the same in index.html file at line 55)**
- `SUPABASE_ANON_KEY`: Your Supabase anonymous key for client-side access **(Give the same in index.html file at line 56)**

**Note**: Never commit the `.env` file to version control. It should be added to your `.gitignore` file.

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd educational-video-generator
   ```

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Install FFmpeg**:
   - Download from [ffmpeg.org](https://ffmpeg.org/download.html)
   - Add FFmpeg's `bin` directory to your system's PATH

4. **Set up environment variables**:
   Create a `.env` file in the root directory with the required API keys and URLs as shown above.

## Usage

### Starting the Server

Run the Flask development server:

```bash
python server.py
```

The server will start on `http://localhost:5000`

### Generating Videos

#### Via API

Send a POST request to generate a new video:

```bash
curl -X POST http://localhost:5000/api/generate-video \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Explain the concept of geometric circles"}'
```

#### Via Frontend

If you have a frontend application, use the provided API endpoints to integrate video generation functionality.

### API Endpoints

#### Video Generation
- `POST /api/generate-video`: Generate a new educational video
  - Body: `{"prompt": "your topic here"}`
  - Returns: Video URL, transcript, and title

#### Video Management
- `GET /api/list-videos`: List all generated videos
- `GET /api/video-details/<video_id>`: Get details for a specific video

#### Quiz Generation
- `POST /api/generate-quiz`: Generate a quiz based on video transcript
  - Body: `{"caption_content": "transcript text", "video_id": "video_id"}`

#### External Integration
- `POST /send-to-zapier`: Send data to Zapier webhook

#### Static Files
- `GET /videos/<script_name>/<resolution>/<filename>`: Serve video files

## Project Structure

```
educational-video-generator/
├── main.py                 # Core video generation logic
├── server.py               # Flask API server
├── llm_handler.py          # Google Gemini integration
├── config.py               # Configuration settings
├── requirements.txt        # Python dependencies
├── generation_cache.json   # Video generation cache
├── system_prompt.md        # System prompts for AI
├── .env                    # Environment variables (not in version control)
├── media/
│   ├── videos/            # Generated video files
│   ├── images/            # Generated images
│   ├── Tex/               # LaTeX rendered equations
│   ├── texts/             # Text overlays
│   └── voiceovers/        # Audio files
└── index.html             # Frontend interface
```

## How It Works

1. **Content Generation**: The system uses Google Gemini to generate Manim Python scripts based on user prompts
2. **Script Processing**: Generated scripts are validated and executed using Manim
3. **Video Rendering**: Manim renders the animation with voiceover narration
4. **Caching**: Successful generations are cached to prevent redundant processing
5. **API Serving**: Generated videos are served through the Flask API

## Caching Mechanism

The system implements intelligent caching to improve performance:

- Videos are cached based on the input prompt
- Cache entries include video file paths and transcripts
- Cache is stored in `generation_cache.json`
- Automatic cache invalidation when files are missing

## Error Handling

The system includes comprehensive error handling:

- Automatic retry mechanism for failed generations (up to 4 attempts)
- Timeout protection for long-running Manim processes (5-minute limit)
- Detailed error logging and user-friendly error messages
- Graceful degradation when external services are unavailable

## External Integrations

### Google Gemini
- Used for script generation and quiz creation
- Requires API key configuration
- Handles rate limiting and error responses

### Zapier
- Webhook integration for automation workflows
- Configurable webhook URL
- Error handling for webhook failures

### Supabase
- Database integration for user management
- Public configuration endpoint for frontend access

## Development

### Adding New Features

1. Extend the `LLMHandler` class in `llm_handler.py` for new AI integrations
2. Add new API endpoints in `server.py`
3. Update the caching logic in `main.py` for new data types

### Testing

Run the server in development mode:

```bash
python server.py
```

Test video generation with different prompts to ensure reliability.

## Troubleshooting

### Common Issues

1. **FFmpeg not found**: Ensure FFmpeg is installed and in PATH
2. **Manim timeout**: Complex animations may exceed the 5-minute timeout
3. **API key errors**: Verify Gemini API key is correctly set in `.env`
4. **Cache issues**: Delete `generation_cache.json` to clear cache

### Debug Mode

Enable debug logging by setting the Flask app to debug mode in `server.py`.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

[Add your license information here]

## Support

For support and questions:
- Create an issue in the repository
- Check the troubleshooting section
- Review the API documentation

---

**Note**: This project requires a valid Google Gemini API key for full functionality. Ensure you have appropriate API quotas and billing set up before deployment.
