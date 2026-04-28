import os
import sys
import logging
import random
from typing import Optional
from google import genai
from google.genai import types

# Injetar a raiz do projeto no path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)

from core.key_utils import get_gemini_keys

class AIWriter:
    def __init__(self):
        # Pool de chaves verificadas via .env
        self.api_keys = get_gemini_keys()
        self.current_idx = 0
        self.model_id = "gemini-3-flash-preview"

    def get_client(self):
        if not self.api_keys: return None
        return genai.Client(api_key=self.api_keys[self.current_idx])

    def generate_script(self, topic: str, style_prompt: str = "", duration_target: str = "medium") -> Optional[str]:
        """Gera roteiro profissional usando Gemini 3 com Thinking e Search."""
        
        duration_map = {
            "short":  ("60 to 90 seconds", "1 to 2 dense paragraphs"),
            "medium": ("3 to 4 minutes", "4 to 6 paragraphs, evidence-heavy"),
            "long":   ("6 to 8 minutes", "8 to 10 paragraphs, documentary style"),
        }
        target_dur, target_struct = duration_map.get(duration_target, duration_map["medium"])

        prompt = f"""
Write a professional YouTube script for: "{topic}"
Target Duration: {target_dur}
Structure: {target_struct}
Tone Style: {style_prompt if style_prompt else "Veritasium/Kurzgesagt documentary style."}

RULES:
- American English only.
- NO section titles, NO rubrics, ONLY spoken narration.
- Use Google Search to include current data/numbers.
- Hook must start with a shocking fact.
- CTA at the end should be conversational.
"""

        for _ in range(len(self.api_keys)):
            client = self.get_client()
            if not client: break
            
            logger.info(f"🧠 Gemini 3 Thinking... | Key: {self.api_keys[self.current_idx][:6]}...")
            
            try:
                config = types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(thinking_level="HIGH"),
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                )
                
                response = client.models.generate_content(
                    model=self.model_id,
                    contents=prompt,
                    config=config,
                )

                if response.text:
                    return response.text.replace("*", "").strip()
                
                raise Exception("Empty response")

            except Exception as e:
                logger.warning(f"⚠️ Erro no AIWriter com chave {self.current_idx}: {e}")
                self.current_idx = (self.current_idx + 1) % len(self.api_keys)

        return None

# Função de compatibilidade com o resto do código
def generate_script_from_topic(topic: str, style_prompt: str = "", duration_target: str = "medium") -> Optional[str]:
    return AIWriter().generate_script(topic, style_prompt, duration_target)

if __name__ == "__main__":
    script = generate_script_from_topic("The future of NVIDIA GPUs", "Dramatic and technical")
    if script: print(script)
