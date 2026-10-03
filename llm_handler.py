import os
import re
import json
from dotenv import load_dotenv
from config import LLM_CONFIG

load_dotenv()

SUPPORTED_LANGUAGES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "hi": "Hindi",
    "ta": "Tamil",
    "ja": "Japanese",
    "it": "Italian",
    "pt": "Portuguese"
}

SUPPORTED_VOICE_TLDS = {
    "com": "US / International",
    "co.uk": "British",
    "co.in": "Indian",
    "com.au": "Australian",
    "ca": "Canadian"
}

LANGUAGE_FONT_MAP = {
    "ta": "Nirmala UI",
    "hi": "Nirmala UI",
    "ja": "Yu Gothic",
    "zh": "Microsoft YaHei",
    "en": "Segoe UI",
    "es": "Segoe UI",
    "fr": "Segoe UI",
    "de": "Segoe UI",
    "it": "Segoe UI",
    "pt": "Segoe UI"
}

FAILOVER_ORDER = ["gemini", "groq", "local"]

DEPTH_CONFIGS = {
    "surface": {
        "label": "Surface Level (~30-60s)",
        "sections": "3 short sections (Hook, Core Concept, Quick Summary)",
        "narration_words": "80-120 words total",
        "description": "Fast high-level overview. Simple visual analogy. No derivation."
    },
    "detailed": {
        "label": "Detailed (~2-3 min)",
        "sections": "5-6 comprehensive sections (Hook, Intuitive Metaphor, Step-by-Step Mechanism/Math, Real-World Application, Pitfalls/Nuance, Summary)",
        "narration_words": "250-350 words total across all sections",
        "description": "Thorough breakdown with visual step-by-step mechanisms, practical examples, and formulas."
    },
    "indepth": {
        "label": "In-Depth (~4-6 min)",
        "sections": "7-9 deep sections (Hook & Context, First Principles Foundation, Core Mathematical/Physical Mechanics, Animated Step-by-Step Simulation, Multi-Stage Case Study, Edge Cases & Counter-Intuitions, Synthesis & Quiz Teaser)",
        "narration_words": "500-750 words total across all sections",
        "description": "Masterclass level first-principles deep dive. Detailed mathematical intuition, multiple animated sub-diagrams, comprehensive explanations."
    }
}

class LLMHandler:
    """
    Handles multi-provider LLM interactions with automatic failover (Gemini -> Groq -> Local),
    token pruning, and multi-language / multi-voice generation.
    """
    def __init__(self, provider=None, model=None):
        self.provider = (provider or LLM_CONFIG["default_provider"]).lower()
        self.model = model
        self.clients = {}
        self._init_client(self.provider)

    def _init_client(self, provider):
        if provider in self.clients:
            return

        if provider == "gemini":
            try:
                import google.genai as genai
                api_key = LLM_CONFIG["gemini"]["api_key"]
                if not api_key:
                    print("[LLM Warning] GEMINI_API_KEY not configured.")
                self.clients["gemini"] = genai.Client(api_key=api_key or "missing_key")
            except Exception as e:
                print(f"[LLM Error] Failed to initialize Gemini: {e}")

        elif provider == "groq":
            try:
                import groq
                api_key = LLM_CONFIG["groq"]["api_key"]
                if not api_key:
                    print("[LLM Warning] GROQ_API_KEY not configured.")
                self.clients["groq"] = groq.Groq(api_key=api_key or "missing_key")
            except Exception as e:
                print(f"[LLM Error] Failed to initialize Groq: {e}")

        elif provider in ("local", "ollama"):
            try:
                import openai
                base_url = LLM_CONFIG["local"]["base_url"]
                api_key = LLM_CONFIG["local"]["api_key"]
                self.clients["local"] = openai.OpenAI(base_url=base_url, api_key=api_key)
            except Exception as e:
                print(f"[LLM Error] Failed to initialize Local LLM: {e}")

    def _execute_provider_query(self, provider, system_prompt, user_prompt, response_json=False):
        self._init_client(provider)
        client = self.clients.get(provider)
        if not client:
            raise RuntimeError(f"Client for provider '{provider}' is not available.")

        if provider == "gemini":
            from google.genai import types as genai_types
            prompt = f"{system_prompt}\n\n**User Request:**\n{user_prompt}" if system_prompt else user_prompt
            config_kwargs = {"max_output_tokens": 4096}
            if response_json:
                config_kwargs["response_mime_type"] = "application/json"
            active_model = self.model or LLM_CONFIG["gemini"]["model"]
            response = client.models.generate_content(
                model=active_model,
                contents=prompt,
                config=genai_types.GenerateContentConfig(**config_kwargs)
            )
            return response.text.strip()

        elif provider == "groq":
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": user_prompt})
            kwargs = {"max_tokens": 4096}
            if response_json:
                kwargs["response_format"] = {"type": "json_object"}
            active_model = self.model or LLM_CONFIG["groq"]["model"]
            resp = client.chat.completions.create(
                model=active_model,
                messages=messages,
                **kwargs
            )
            return resp.choices[0].message.content.strip()

        elif provider in ("local", "ollama"):
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": user_prompt})
            kwargs = {"max_tokens": 4096}
            if response_json:
                kwargs["response_format"] = {"type": "json_object"}
            active_model = self.model or LLM_CONFIG["local"]["model"]
            resp = client.chat.completions.create(
                model=active_model,
                messages=messages,
                **kwargs
            )
            return resp.choices[0].message.content.strip()

        raise ValueError(f"Unknown provider '{provider}'")

    def _query(self, system_prompt, user_prompt, response_json=False):
        """
        Dispatches query with automatic failover chain:
        Selected provider -> Gemini -> Groq -> Local
        """
        # Determine trial order starting from preferred provider
        candidates = [self.provider]
        for p in FAILOVER_ORDER:
            if p not in candidates:
                candidates.append(p)

        last_error = None
        for p in candidates:
            try:
                result = self._execute_provider_query(p, system_prompt, user_prompt, response_json=response_json)
                if p != self.provider:
                    print(f"[LLM Failover] Primary failed. Succeeded with failover provider: {p}")
                return result
            except Exception as e:
                print(f"[LLM Warning] Provider '{p}' failed: {e}. Trying next candidate...")
                last_error = e

        raise RuntimeError(f"All LLM providers failed. Last error: {last_error}")

    def _clean_code(self, raw_text):
        """Extracts python code from LLM response safely."""
        text = raw_text.strip()
        match = re.search(r"```(?:python)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
        if match:
            code = match.group(1).strip()
        else:
            if text.startswith("```python"):
                text = text[9:]
            elif text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            code = text.strip()
        # Fix known LLM hallucinations for manim-voiceover API
        code = re.sub(r'\bself\.add_voiceover_service\(', 'self.set_speech_service(', code)
        code = re.sub(r'\bself\.init_voiceover\(', 'self.set_speech_service(', code)
        return code

    def _apply_font_guard(self, code, language="en"):
        font_name = LANGUAGE_FONT_MAP.get(language, "Segoe UI")
        # Ensure Text(...) calls include font="{font_name}" if font is not already specified
        def _inject_font(match):
            inner = match.group(1)
            if "font=" not in inner:
                return f'Text({inner}, font="{font_name}")'
            return match.group(0)

        return re.sub(r'\bText\(([^()\n]+?)\)', _inject_font, code)

    def _get_system_prompt(self, class_name, language="en", voice_tld="com", depth="surface"):
        lang_name = SUPPORTED_LANGUAGES.get(language, "English")
        font_name = LANGUAGE_FONT_MAP.get(language, "Segoe UI")
        depth_cfg = DEPTH_CONFIGS.get(depth, DEPTH_CONFIGS["surface"])

        if language != "en":
            lang_instruction = f"""### HYBRID / COLLOQUIAL CODE-MIXED MODE FOR {lang_name.upper()} (CRITICAL):
- Speak naturally like modern engineering students and professors (e.g. Tanglish for Tamil, Hinglish for Hindi).
- DO NOT use archaic, literal textbook translations for technical or scientific concepts.
  * FORBIDDEN (Archaic): Translating "Black Hole" as "கருந்துளை" or "Event Horizon" as "நிகழ்வு எல்லை" or "Gravity" as "ஈர்ப்பு விசை".
  * REQUIRED (Hybrid): Keep all technical terms in standard English (e.g. "Black Hole", "Event Horizon", "Gravity", "Escape Velocity", "Spacetime", "Machine Learning", "Algorithm", "Database") embedded within natural {lang_name} sentence structure.
- ON-SCREEN VISUAL LABELS, TITLES, & DIAGRAMS:
  * ALWAYS write titles, headings, and box labels in ENGLISH (e.g. Text("Black Hole", font="Segoe UI"), Text("Event Horizon", font="Segoe UI")).
  * Students and engineers recognize English technical terms; avoid translating diagram labels into native script.
  * Only conversational subtitle explanations may use {lang_name} (with font="{font_name}")."""
        else:
            lang_instruction = "All voiceover narration and on-screen Text labels must be in English."

        return f"""You are an expert Python developer and educator specializing in Manim animations with `manim-voiceover`.
Generate a single, flawless, self-contained Python script using Manim Community Edition and `manim-voiceover`.

### DEPTH PROFILE: {depth.upper()} ({depth_cfg['label']}):
- Target duration/pedagogy: {depth_cfg['description']}
- Structure into EXACTLY: {depth_cfg['sections']}
- Script narration length: {depth_cfg['narration_words']}
- Each section MUST have substantial explanatory narration and corresponding visual animations.

### CRITICAL RULES (ZERO TOLERANCE - VIOLATIONS WILL CRASH THE PROGRAM):
1. **NO LATEX ALLOWED - ABSOLUTE REQUIREMENT:**
   - LaTeX is NOT installed on the host system.
   - NEVER use `MathTex`, `Tex`, or `BulletedList`. Using them causes an immediate fatal crash.
   - Use ONLY `Text(...)` for ALL titles, labels, equations, formulas, and numbers.
   - Write formulas in unicode: e.g. `Text("E = mc²", font="{font_name}", font_size=40)`, `Text("a² + b² = c²", font="{font_name}", font_size=36)`.

2. **MANDATORY UNICODE FONT FOR {lang_name.upper()} ({language}):**
   - Windows requires an explicit font to render non-Latin/Indic characters cleanly without blank square boxes (tofu □□□).
   - EVERY `Text(...)` call MUST explicitly specify `font="{font_name}"` or `font="Segoe UI"`.
   - Example: `Text("...", font="{font_name}", font_size=36)`

3. **LANGUAGE & HYBRID CODE-MIXING CONFIGURATION:**
   - {lang_instruction}
   - First lines in `construct(self)` MUST BE EXACTLY:
     ```python
     self.set_speech_service(GTTSService(lang="{language}", tld="{voice_tld}"))
     self.camera.background_color = "#1e293b"
     ```
   - Speech service setup MUST be `self.set_speech_service(...)` — NEVER call `add_voiceover_service`.

4. **CLASS DEFINITION & IMPORTS:**
   - The script MUST begin with EXACTLY these imports:
```python
from manim import *
from manim_voiceover import VoiceoverScene
from manim_voiceover.services.gtts import GTTSService
```
   - Exactly ONE scene class named `{class_name}` that inherits from `VoiceoverScene`:
     `class {class_name}(VoiceoverScene):`

5. **VOICEOVER & ANIMATION SYNCHRONIZATION:**
   - EVERY animation (`self.play(...)`) MUST be placed inside a `with self.voiceover(text=...) as tracker:` block.
   - Inside each block, split `tracker.duration` cleanly among animations (e.g. `run_time=tracker.duration * 0.5`).
   - Narration strings must be natural spoken words: NO symbols like backslashes, dollar signs, asterisks, brackets, emojis, or LaTeX syntax.
   - At the end of each section, clean up previous objects before the next section:
     `self.play(*[FadeOut(m) for m in self.mobjects], run_time=0.5)`

6. **TOKEN & SPEED OPTIMIZATION:**
   - Output zero comments, zero docstrings, and zero placeholder text.
   - Keep code concise, minimal, and direct.

7. **OUTPUT FORMAT:**
   - Return ONLY the executable Python script enclosed inside ```python ... ``` fences.
   - No introductory text, no conversational padding outside code fences.
"""

    def generate_content(self, topic, class_name, language="en", voice_tld="com", depth="surface"):
        """Generates the Manim script for a given topic, language, voice accent, and depth level."""
        lang_name = SUPPORTED_LANGUAGES.get(language, "English")
        font_name = LANGUAGE_FONT_MAP.get(language, "Segoe UI")
        depth_cfg = DEPTH_CONFIGS.get(depth, DEPTH_CONFIGS["surface"])
        print(f"[LLM] Generating script for topic '{topic}' (depth: {depth} - {depth_cfg['label']}, {lang_name}, font: {font_name}, voice: {voice_tld}) using provider: {self.provider}")
        system_prompt = self._get_system_prompt(class_name, language=language, voice_tld=voice_tld, depth=depth)
        user_prompt = (
            f"Generate a robust Manim animation script explaining: '{topic}'.\n"
            f"Scene class name MUST be: '{class_name}'.\n"
            f"Depth Level: {depth.upper()} ({depth_cfg['label']}).\n"
            f"Required Structure: {depth_cfg['sections']}.\n"
            f"Narration Length: {depth_cfg['narration_words']}.\n"
            f"Language: {lang_name} ({language}).\n"
            f"Font MUST be: font='{font_name}' in all Text(...) calls.\n"
            f"Remember: Use ONLY Text(...) — NEVER MathTex or Tex."
        )
        response_text = self._query(system_prompt, user_prompt)
        cleaned = self._clean_code(response_text)
        return self._apply_font_guard(cleaned, language=language)

    def fix_code(self, broken_code, error_message):
        """Attempts to fix a broken Manim script based on an error message."""
        print(f"\n--- Attempting to fix the Manim script with AI ({self.provider}) ---")
        system_prompt = (
            "You are a Manim expert. Fix the broken Manim script so it executes without any errors.\n"
            "STRICT RULES:\n"
            "1. NO LATEX: Replace any MathTex or Tex with standard Text(...).\n"
            "2. Keep the scene class inheriting from VoiceoverScene.\n"
            "3. Speech service MUST be `self.set_speech_service(GTTSService(...))` — NEVER `add_voiceover_service`.\n"
            "4. Ensure all self.play() calls are inside `with self.voiceover(text=...) as tracker:`.\n"
            "5. Zero comments, zero docstrings. Output ONLY valid, runnable Python code inside ```python ``` fences."
        )
        user_prompt = f"""The following Manim script failed with an error:

**Broken Script:**
```python
{broken_code}
```

**Error Output:**
```
{error_message}
```

Provide the complete, corrected, fully working Python script."""
        response_text = self._query(system_prompt, user_prompt)
        fixed = self._clean_code(response_text)
        print("--- AI has provided a potential fix ---")
        return fixed

    def generate_quiz(self, caption_content, video_id, language="en"):
        """Generates a 4-question quiz from video transcript in the specified language."""
        lang_name = SUPPORTED_LANGUAGES.get(language, "English")
        hybrid_instruction = ""
        if language != "en":
            hybrid_instruction = (
                f" Follow HYBRID/COLLOQUIAL style: formulate question stems and natural speech in {lang_name}, "
                "but keep all technical scientific keywords (e.g., 'Black Hole', 'Event Horizon', 'Gravity', 'Velocity') "
                "in standard English. Never invent obscure textbook translations."
            )
        system_prompt = (
            f"You are a quiz creator. Based on the transcript, create a JSON quiz with 4 multiple-choice questions in {lang_name}.{hybrid_instruction} "
            "Return valid JSON matching this schema: "
            '{"quiz_id": "string", "video_id": "string", "questions": [{"id": 1, "text": "...", "options": ["A", "B", "C", "D"], "answer": "A"}]}. '
            "Output ONLY the JSON object, no Markdown fences or other text."
        )
        user_prompt = f"Transcript:\n---\n{caption_content}\n---"
        raw_result = self._query(system_prompt, user_prompt, response_json=True)
        clean = re.sub(r"^```(?:json)?\s*", "", raw_result.strip(), flags=re.IGNORECASE)
        clean = re.sub(r"\s*```$", "", clean).strip()
        data = json.loads(clean)
        data["video_id"] = video_id
        if not data.get("quiz_id"):
            data["quiz_id"] = f"quiz_{video_id}"
        return data
