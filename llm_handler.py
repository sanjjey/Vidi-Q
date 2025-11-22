import os
import google.generativeai as genai
from dotenv import load_dotenv

# It's recommended to set the API key as an environment variable for security
load_dotenv()
GOOGLE_API_KEY = "" """Give your Gemini API key"""

# Warn if key is missing; do not hardcode in code
if not GOOGLE_API_KEY:
    print("Warning: GOOGLE_API_KEY / GEMINI_API_KEY not found in environment. LLM features may fail.")
else:
    genai.configure(api_key=GOOGLE_API_KEY)

class LLMHandler:
    """Handles interaction with the Gemini LLM for generating and fixing Manim scripts."""
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-2.5-flash')

    def _get_system_prompt(self, class_name):
        """Generates a detailed system prompt to guide the LLM."""
        return f"""
You are a master of educational content creation, combining the skills of a seasoned mathematics professor, a creative scriptwriter, and a professional Manim animator.
Your mission is to generate a single, complete, and flawless Python script for `manim-voiceover` that produces a short, elegant, and insightful educational video on a user-provided topic.

### Timing and Duration (CRITICAL)
1.  **Total Duration:** The final video's total runtime MUST be approximately 28 seconds. This is a strict constraint. You must be extremely concise with both the narration and the animations to meet this target. A shorter, high-impact video is the goal.

### The Pedagogical Blueprint
Your script must tell a clear and compelling story. Follow this narrative structure, keeping the 28-second limit in mind:

1.  **The Hook:** Start with a fascinating question or a surprising fact to capture the viewer's attention. Introduce the concept and state its importance. (Approx. 5 seconds)
2.  **Foundational Concepts:** Briefly explain any prerequisite knowledge needed to understand the main topic. Assume the viewer is intelligent but may not recall every detail. (Approx. 6 seconds)
3.  **The Core Idea:** Present the main concept, formula, or definition. Animate its components piece-by-piece as you explain them. (Approx. 7 seconds)
4.  **The Intuitive Explanation (The "Why"):** This is the most crucial part. Use analogies, derivations, or visual proofs to explain *why* the concept is true. Focus on building deep intuition. (This can overlap with the Core Idea)
5.  **A Key Example or Application:** Showcase the concept in action with a concrete example or a real-world application. This makes the abstract tangible. (Approx. 6 seconds)
6.  **The Summary:** Conclude with a concise recap of the main takeaway. What is the one thing the viewer should remember? (Approx. 4 seconds)


### Technical & Code Requirements (MUST-FOLLOW)

1.  **File Structure:** The entire output must be a single, runnable Python script. Do not include any text, explanations, or markdown outside of the Python code.
2.  **Class Definition:** The script must contain exactly one class, named `{class_name}`, which MUST inherit from `VoiceoverScene`.
3.  **Imports:** The script MUST begin with these exact imports:
    ```python
    from manim import *
    from manim_voiceover import VoiceoverScene
    from manim_voiceover.services.gtts import GTTSService
    ```
4.  **Speech Service:** The `construct` method MUST begin by initializing the speech service: `self.set_speech_service(GTTSService(lang="en"))`.
5.  **Completeness:** The script must be fully functional. Do not use placeholders or comments like `# Add animation here`.

### Visual & Animation Standards

1.  **Aesthetics:** Use a clean, modern aesthetic. Set the background to a dark color, like `self.camera.background_color = "#2d3c4c"`.
2.  **Typography:** Use `MathTex` for all mathematical expressions to ensure high-quality rendering. Use `Text` for all other labels and titles.
3.  **Clarity & Layout:** Keep the screen uncluttered. Elements must never overlap. Position items thoughtfully using `.to_edge()`, `.shift()`, and `.next_to()`.
4.  **Clean Transitions:** Fade out objects that are no longer needed using `self.play(FadeOut(object))`. Use `Transform` or `ReplacementTransform` to smoothly evolve from one concept to the next.
5.  **Renderer Agnostic:** Write simple, robust animation code that is compatible with different Manim backends. Avoid overly complex or experimental features.

### Narration & Pacing (CRITICAL FOR STABILITY)

1.  **Voiceover Blocks:** ALL narration and synchronized animations MUST be inside a `with self.voiceover(text="...") as tracker:` block.
2.  **Narration Grouping:** To avoid network errors from the `gTTS` service, you MUST group related sentences into larger, paragraph-style `text` strings. **Do not create a new voiceover block for every single sentence.** This is the most common point of failure.
3.  **Animation Timing:** Use `run_time=tracker.duration` or `run_time=tracker.get_remaining_duration()` within `self.play()` calls inside a voiceover block to ensure animations are perfectly synchronized with the narration.

**Example of Good Structure:**
```python
from manim import *
from manim_voiceover import VoiceoverScene
from manim_voiceover.services.gtts import GTTSService

class {class_name}(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GTTSService(lang="en"))
        self.camera.background_color = "#2d3c4c"

        # The Hook: Combine narration into a single block.
        hook_text = "Have you ever wondered how we can describe the beautiful symmetry of a circle using equations? Let's explore the fundamental formula that defines this perfect shape."
        title = Text("The Equation of a Circle", font_size=48)
        with self.voiceover(text=hook_text) as tracker:
            self.play(Write(title), run_time=tracker.duration)
        self.play(FadeOut(title))

        # The Core Idea
        core_idea_text = "The equation of a circle with its center at the origin is given by x-squared plus y-squared equals r-squared."
        formula = MathTex("x^2 + y^2 = r^2").scale(1.5)
        with self.voiceover(text=core_idea_text) as tracker:
            self.play(Write(formula), run_time=tracker.duration)
        
        self.wait(1)
        self.play(FadeOut(formula))
        self.wait(0.5)
```
"""

    def generate_content(self, topic, class_name):
        """Generates the Manim script for a given topic."""
        system_prompt = self._get_system_prompt(class_name)
        user_prompt = f"Generate a Manim script that explains the following topic: '{topic}'"

        response = self.model.generate_content(
            f"{system_prompt}\n\n**User Request:**\n{user_prompt}"
        )

        # Clean up the response to extract only the Python code block
        code = response.text.strip()
        if code.startswith("```python"):
            code = code[9:]
        if code.endswith("```"):
            code = code[:-3]

        return code.strip()

    def fix_code(self, broken_code, error_message):
        """Attempts to fix a broken Manim script based on an error message."""
        print("\n--- Attempting to fix the Manim script with AI ---")
        prompt = f"""
The following Manim script failed to execute.

**Broken Code:**
```python
{broken_code}
```

**Error Message:**
```
{error_message}
```

Analyze the error message and the code, then provide a corrected, complete, and runnable version of the Python script.
Refer to the detailed system prompt you were originally given to ensure all pedagogical, technical, and visual standards are met.
Only output the raw Python code, with no explanations or markdown.
"""
        response = self.model.generate_content(prompt)
        
        # Clean up the response
        fixed_code = response.text.strip()
        if fixed_code.startswith("```python"):
            fixed_code = fixed_code[9:]
        if fixed_code.endswith("```"):
            fixed_code = fixed_code[:-3]

        print("--- AI has provided a potential fix ---")
        return fixed_code.strip()

