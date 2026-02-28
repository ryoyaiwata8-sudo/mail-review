
import os
import time
import json
import re
from typing import Dict, Optional, List, Tuple
import google.generativeai as genai
from openai import OpenAI
from pathlib import Path

class AudioProcessor:
    def __init__(self, provider: str = "gemini", api_key: Optional[str] = None):
        self.provider = provider
        self.api_key = api_key
        
        if provider == "gemini":
            if not api_key:
                raise ValueError("API Key required for Gemini")
            genai.configure(api_key=api_key)
            model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")
            self.model = genai.GenerativeModel(model_name)
        elif provider == "openai":
            if not api_key:
                raise ValueError("API Key required for OpenAI")
            self.client = OpenAI(api_key=api_key)
            
    def transcribe(self, file_path: str) -> str:
        """Returns plain text transcript (cached if available)."""
        cache_path = file_path + ".txt"
        if os.path.exists(cache_path):
            with open(cache_path, "r", encoding="utf-8") as f:
                return f.read()

        try:
            res = self.process_full(file_path)
            return res.get("text", "[No text extracted]")
        except Exception as e:
            return f"[Error in transcription: {str(e)}]"

    def process_full(self, file_path: str) -> Dict:
        """
        Processes audio and returns structured result:
        { "text": str, "hold_total_sec": int, "hold_segments": list }
        """
        # Caching for structured result
        json_cache = file_path + ".json"
        if os.path.exists(json_cache):
            with open(json_cache, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "total_duration_sec" in data and data["total_duration_sec"] > 0:
                    return data
                print(f"[DEBUG] Cache exists but missing total_duration_sec. Re-processing {file_path}")

        if self.provider == "gemini":
            res = self._process_gemini(file_path)
        else:
            # Fallback to simple text if not gemini
            text = self._transcribe_openai(file_path)
            res = {"text": text, "hold_total_sec": 0, "hold_segments": []}

        # Cache it
        with open(json_cache, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False)
        return res

    def _process_gemini(self, file_path: str) -> Dict:
        print(f"Uploading {file_path} to Gemini...")
        audio_file = genai.upload_file(path=file_path)
        
        while audio_file.state.name == "PROCESSING":
            time.sleep(1)
            audio_file = genai.get_file(audio_file.name)
            
        if audio_file.state.name == "FAILED":
            raise ValueError("Gemini file upload failed.")
            
        # Request timestamped transcription and duration
        prompt = """
        transcribe with timestamps and calculate hold time.
        1. Transcribe the audio precisely.
        2. Detect "Hold" segments (start, end, duration).
        3. Determine the total duration of the audio file in seconds.
        4. Output MUST be valid JSON:
        {
          "text": "Full transcript here...",
          "total_duration_sec": 300.5,
          "hold_total_sec": 120,
          "hold_segments": [
            {"start": 10.5, "end": 70.5, "duration": 60, "trigger": "少々お待ちください"}
          ]
        }
        """
        
        response = self.model.generate_content([audio_file, prompt])
        cleaned = response.text.replace("```json", "").replace("```", "").strip()
        
        try:
            data = json.loads(cleaned)
            return data
        except:
            # Fallback if AI fails JSON
            return {"text": response.text, "total_duration_sec": 0, "hold_total_sec": 0, "hold_segments": []}

    def _transcribe_openai(self, file_path: str) -> str:
        with open(file_path, "rb") as audio_file:
            transcript = self.client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file,
                response_format="text"
            )
        return transcript
