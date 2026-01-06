import requests
import logging
from pathlib import Path
from typing import Optional
import urllib.parse
from config import ASSETS_DIR

logger = logging.getLogger(__name__)

class ImageGenerator:
    """
    Gerador de imagens usando a API do Pollinations.ai (Modelo FLUX).
    Baseado nas recomendações de Olhe.md.
    """
    
    BASE_URL = "https://image.pollinations.ai/prompt/"
    DEFAULT_MODEL = "flux"
    
    @staticmethod
    def generate_image(prompt: str, filename: str, model: str = DEFAULT_MODEL, width: int = 1024, height: int = 1024) -> Optional[str]:
        """
        Gera uma imagem via Pollinations.ai e salva no diretório de assets.
        
        Args:
            prompt (str): Descrição da imagem.
            filename (str): Nome do arquivo de saída (ex: 'background_1.jpg').
            model (str): Modelo a ser usado (padrão: flux).
            width (int): Largura da imagem.
            height (int): Altura da imagem.
            
        Returns:
            Optional[str]: Caminho absoluto da imagem salva ou None em caso de erro.
        """
        try:
            encoded_prompt = urllib.parse.quote(prompt)
            url = f"{ImageGenerator.BASE_URL}{encoded_prompt}?model={model}&width={width}&height={height}&seed={urllib.parse.quote(str(os.urandom(4)))}"
            
            # Garantir que a pasta de assets existe
            output_dir = Path(ASSETS_DIR) / "generated"
            output_dir.mkdir(exist_ok=True)
            
            file_path = output_dir / filename
            
            logger.info(f"🎨 Gerando imagem: '{prompt}' via {model}...")
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                with open(file_path, "wb") as f:
                    f.write(response.content)
                logger.info(f"✅ Imagem salva em: {file_path}")
                return str(file_path.absolute())
            else:
                logger.error(f"❌ Erro na API Pollinations: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Falha na geração de imagem: {e}")
            return None

if __name__ == "__main__":
    import os
    logging.basicConfig(level=logging.INFO)
    # Teste rápido
    path = ImageGenerator.generate_image("A futuristic cyberpunk city in the clouds, cinematic lighting, 8k", "test_flux.jpg")
    if path:
        print(f"Sucesso: {path}")
    else:
        print("Falha no teste.")
