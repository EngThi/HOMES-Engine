import requests
import logging
import os
import base64
import urllib.parse
import time
from pathlib import Path
from typing import Optional
from config import ASSETS_DIR

logger = logging.getLogger(__name__)

from core.key_utils import get_gemini_keys

class ImageGenerator:
    """
    Gerador de imagens Profissional (Absolute Cinema v3.1).
    Key Rotation para Gemini Image e Fallback VIP para FLUX.
    """
    
    POLLINATIONS_URL = "https://image.pollinations.ai/prompt/"
    # Imagen 3 via Gemini API (pode mudar dependendo da lib)
    GEMINI_MODEL = "gemini-1.5-flash" 

    def __init__(self):
        self.api_keys = get_gemini_keys()
        self.current_idx = 0

    def _enhance_prompt(self, base_prompt: str) -> str:
        """Adiciona camadas de qualidade cinematográfica ao prompt."""
        cinematic_tags = (
            "8k resolution, cinematic lighting, dramatic shadows, "
            "photorealistic, highly detailed, masterwork, vertical 9:16 aspect ratio, "
            "shot on 35mm lens, depth of field, vivid colors, no text, no blur"
        )
        return f"{base_prompt}, {cinematic_tags}"

    def generate(self, prompt: str, filename: str, width: int = 720, height: int = 1280) -> Optional[str]:
        """Orquestra a geração com resiliência máxima."""
        enhanced_prompt = self._enhance_prompt(prompt)
        
        # 1. Tenta Gemini Image com Rotação de Chaves
        for _ in range(len(self.api_keys)):
            key = self.api_keys[self.current_idx]
            result = self._try_gemini(enhanced_prompt, filename, key)
            if result:
                return result
            # Se falhou, rotaciona a chave e tenta novamente
            self.current_idx = (self.current_idx + 1) % len(self.api_keys)

        # 2. Fallback para Pollinations (Flux) - Garantia de entrega
        logger.warning("⚠️ Todas as chaves Gemini falharam na imagem. Usando FLUX (VIP)...")
        return self._try_pollinations(enhanced_prompt, filename, width, height)

    def _try_gemini(self, prompt: str, filename: str, key: str) -> Optional[str]:
        """Tenta gerar via Imagen/Gemini API."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.GEMINI_MODEL}:generateContent?key={key}"
        # Nota: Geração de imagem via Gemini 2.0 exige response_modalities=["IMAGE"]
        payload = {
            "contents": [{"parts": [{"text": f"Generate a high quality image of: {prompt}"}]}],
            "generationConfig": {"response_modalities": ["IMAGE"]}
        }
        
        try:
            response = requests.post(url, json=payload, timeout=40)
            if response.status_code == 200:
                data = response.json()
                # Verifica se retornou dados de imagem inline
                parts = data['candidates'][0]['content']['parts']
                for part in parts:
                    if 'inlineData' in part:
                        image_data = base64.b64decode(part['inlineData']['data'])
                        output_path = Path(ASSETS_DIR) / "generated" / filename
                        output_path.parent.mkdir(exist_ok=True)
                        with open(output_path, "wb") as f: f.write(image_data)
                        logger.info(f"✅ Imagem gerada via Gemini ({key[:6]}): {output_path}")
                        return str(output_path.absolute())
        except Exception: pass
        return None

    def _try_pollinations(self, prompt: str, filename: str, width: int, height: int) -> Optional[str]:
        """Gera via Pollinations (FLUX) - Inquebrável."""
        encoded = urllib.parse.quote(prompt)
        seed = os.urandom(4).hex()
        url = f"{self.POLLINATIONS_URL}{encoded}?model=flux&width={width}&height={height}&seed={seed}&nologo=true"
        
        try:
            output_path = Path(ASSETS_DIR) / "generated" / filename
            output_path.parent.mkdir(exist_ok=True)
            
            response = requests.get(url, timeout=60)
            if response.status_code == 200:
                with open(output_path, "wb") as f: f.write(response.content)
                logger.info(f"✅ Imagem gerada via FLUX: {output_path}")
                return str(output_path.absolute())
        except Exception as e:
            logger.error(f"❌ Falha crítica no FLUX: {e}")
        return None

# Função estática de compatibilidade
def generate_image(prompt: str, filename: str) -> Optional[str]:
    return ImageGenerator().generate(prompt, filename)

if __name__ == "__main__":
    # Teste rápido
    gen = ImageGenerator()
    gen.generate("A futuristic city on Mars, neon lights, sandstorms", "mars_test.jpg")
