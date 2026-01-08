import requests
import logging
import os
import base64
import urllib.parse
from pathlib import Path
from typing import Optional
from config import ASSETS_DIR, GEMINI_API_KEY, POLLINATIONS_API_KEY

logger = logging.getLogger(__name__)

class ImageGenerator:
    """
    Gerador de imagens Híbrido:
    Tenta Gemini 2.5 Flash Image -> Fallback para Pollinations (FLUX Autenticado)
    """
    
    POLLINATIONS_URL = "https://image.pollinations.ai/prompt/"
    GEMINI_MODEL = "gemini-2.5-flash-image"
    
    @staticmethod
    def generate_image(prompt: str, filename: str, width: int = 1024, height: int = 1024) -> Optional[str]:
        """
        Orquestra a geração de imagem com fallback.
        """
        # 1. Tentativa com Gemini (Nativo)
        result = ImageGenerator._generate_via_gemini(prompt, filename)
        if result:
            return result
            
        # 2. Fallback para Pollinations (Garantido & Autenticado)
        logger.warning("⚠️ Gemini Image indisponível. Usando Pollinations/FLUX (VIP Mode)...")
        return ImageGenerator._generate_via_pollinations(prompt, filename, width, height)

    @staticmethod
    def _generate_via_gemini(prompt: str, filename: str) -> Optional[str]:
        """Geração via Google Gemini 2.5"""
        if not GEMINI_API_KEY:
            return None
            
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{ImageGenerator.GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseModalities": ["IMAGE"]}
        }
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            if response.status_code == 200:
                data = response.json()
                if 'candidates' in data and data['candidates']:
                    image_b64 = data['candidates'][0]['content']['parts'][0]['inlineData']['data']
                    
                    output_path = Path(ASSETS_DIR) / "generated" / filename
                    output_path.parent.mkdir(exist_ok=True)
                    
                    with open(output_path, "wb") as f:
                        f.write(base64.b64decode(image_b64))
                    
                    logger.info(f"✅ Imagem gerada via Gemini: {output_path}")
                    return str(output_path.absolute())
        except Exception:
            pass
        return None

    @staticmethod
    def _generate_via_pollinations(prompt: str, filename: str, width: int, height: int) -> Optional[str]:
        """Geração via Pollinations.ai (Flux) com Autenticação"""
        retries = 3
        headers = {}
        
        # Injeção de Autenticação (VIP Mode)
        if POLLINATIONS_API_KEY:
            headers["Authorization"] = f"Bearer {POLLINATIONS_API_KEY}"
            # logger.info("💎 Usando chave Pollinations VIP")

        for i in range(retries):
            try:
                encoded_prompt = urllib.parse.quote(prompt)
                seed = urllib.parse.quote(str(os.urandom(4)))
                # Adiciona nologo=true para limpar marca d'água se a chave permitir
                url = f"{ImageGenerator.POLLINATIONS_URL}{encoded_prompt}?model=flux&width={width}&height={height}&seed={seed}&nologo=true"
                
                output_path = Path(ASSETS_DIR) / "generated" / filename
                output_path.parent.mkdir(exist_ok=True)
                
                logger.info(f"🎨 Tentativa {i+1} via Pollinations (Flux)...")
                response = requests.get(url, headers=headers, timeout=60)
                
                if response.status_code == 200:
                    with open(output_path, "wb") as f:
                        f.write(response.content)
                    logger.info(f"✅ Imagem gerada via Pollinations: {output_path}")
                    return str(output_path.absolute())
                else:
                    logger.warning(f"⚠️ Erro API Pollinations: {response.status_code} - {response.text}")
                    
            except Exception as e:
                logger.warning(f"⚠️ Tentativa {i+1} falhou: {e}")
                time.sleep(2)
        
        logger.error("❌ Falha total na geração de imagem após retries.")
        return None

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Teste do sistema híbrido
    path = ImageGenerator.generate_image("A majestic phoenix rising from the ashes, vertical, 8k cinematic", "hybrid_test.jpg")
    print(f"Resultado: {path}")