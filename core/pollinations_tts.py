import requests
import logging
from pathlib import Path
from typing import Optional
import urllib.parse
from config import OUTPUT_DIR

logger = logging.getLogger(__name__)

class PollinationsTTS:
    """
    Motor de voz usando a API do Pollinations.ai (Modelo OpenAI-Audio).
    Baseado nas recomendações de Olhe.md.
    """
    
    BASE_URL = "https://text.pollinations.ai/"
    DEFAULT_MODEL = "openai-audio"
    DEFAULT_VOICE = "nova" # Vozes: alloy, echo, fable, onyx, nova, shimmer
    
    @staticmethod
    def generate_audio(text: str, filename: str, voice: str = DEFAULT_VOICE) -> Optional[str]:
        """
        Gera áudio via Pollinations.ai e salva no diretório de cache.
        
        Args:
            text (str): Texto para converter em fala.
            filename (str): Nome do arquivo de saída (ex: 'audio_1.mp3').
            voice (str): Voz a ser usada.
            
        Returns:
            Optional[str]: Caminho absoluto do áudio salvo ou None em caso de erro.
        """
        try:
            encoded_text = urllib.parse.quote(text)
            url = f"{PollinationsTTS.BASE_URL}{encoded_text}?model={PollinationsTTS.DEFAULT_MODEL}&voice={voice}"
            print(f"DEBUG URL: {url}")
            
            # Garantir que a pasta de cache existe
            output_dir = Path(OUTPUT_DIR) / "cache"
            output_dir.mkdir(exist_ok=True)
            
            file_path = output_dir / filename
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
            }
            
            logger.info(f"🎙️ Gerando voz ({voice}): '{text[:30]}...' via Pollinations...")
            response = requests.get(url, headers=headers, timeout=60)
            
            if response.status_code == 200:
                with open(file_path, "wb") as f:
                    f.write(response.content)
                logger.info(f"✅ Áudio salvo em: {file_path}")
                return str(file_path.absolute())
            else:
                logger.error(f"❌ Erro na API Pollinations Audio: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Falha na geração de áudio: {e}")
            return None

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Teste rápido
    path = PollinationsTTS.generate_audio("Olá, este é um teste do novo motor de voz Absolute Cinema via Pollinations.", "test_voice.mp3")
    if path:
        print(f"Sucesso: {path}")
    else:
        print("Falha no teste.")
