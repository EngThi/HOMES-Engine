import requests
import logging
import os
import base64
import urllib.parse
import time
from pathlib import Path
from typing import Optional
from config import ASSETS_DIR, GEMINI_API_KEY, POLLINATIONS_API_KEY

logger = logging.getLogger(__name__)

class ImageGenerator:
    """
    Híbrido: Gemini 3.1 Flash Image -> Fallback Pollinations (FLUX VIP)
    v1.9.6: Adicionado suporte a retries inteligentes para evitar erro 429.
    """
    
    POLLINATIONS_URL = "https://image.pollinations.ai/prompt/"
    GEMINI_MODEL = "gemini-3.1-flash-image-preview"
    
    @staticmethod
    def generate_image(prompt: str, filename: str, width: int = 1024, height: int = 1024) -> Optional[str]:
        # 1. Tentativa Gemini
        result = ImageGenerator._generate_via_gemini(prompt, filename)
        if result: return result
            
        # 2. Fallback Pollinations
        return ImageGenerator._generate_via_pollinations(prompt, filename, width, height)

    @staticmethod
    def _generate_via_gemini(prompt: str, filename: str) -> Optional[str]:
        if not GEMINI_API_KEY: return None
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{ImageGenerator.GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
        payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseModalities": ["IMAGE"]}}
        try:
            response = requests.post(url, json=payload, timeout=40)
            if response.status_code == 200:
                data = response.json()
                if 'candidates' in data and data['candidates']:
                    image_b64 = data['candidates'][0]['content']['parts'][0]['inlineData']['data']
                    out = Path(ASSETS_DIR) / "generated" / filename
                    out.parent.mkdir(exist_ok=True)
                    with open(out, "wb") as f: f.write(base64.b64decode(image_b64))
                    return str(out.absolute())
        except: pass
        return None

    @staticmethod
    def _generate_via_pollinations(prompt: str, filename: str, width: int, height: int) -> Optional[str]:
        retries = 5
        headers = {"Authorization": f"Bearer {POLLINATIONS_API_KEY}"} if POLLINATIONS_API_KEY else {}

        for i in range(retries):
            try:
                encoded = urllib.parse.quote(prompt)
                seed = random.randint(1, 999999) if 'random' in globals() else time.time()
                url = f"{ImageGenerator.POLLINATIONS_URL}{encoded}?model=flux&width={width}&height={height}&seed={seed}&nologo=true"
                
                out = Path(ASSETS_DIR) / "generated" / filename
                out.parent.mkdir(exist_ok=True)
                
                response = requests.get(url, headers=headers, timeout=60)
                
                if response.status_code == 200:
                    with open(out, "wb") as f: f.write(response.content)
                    logger.info(f"✅ Imagem gerada (Pollinations): {filename}")
                    return str(out.absolute())
                
                elif response.status_code == 429:
                    wait = (i + 1) * 7
                    logger.warning(f"⚠️ Fila cheia (429). Aguardando {wait}s...")
                    time.sleep(wait)
                else:
                    time.sleep(2)
            except Exception as e:
                logger.warning(f"⚠️ Erro na tentativa {i+1}: {e}")
                time.sleep(5)
        
        return None
