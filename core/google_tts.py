import os
import requests
import json
import base64
import logging
from typing import Optional
from config import GEMINI_API_KEY, GEMINI_MODEL

logger = logging.getLogger(__name__)

class GoogleGeminiTTS:
    """
    Motor de voz usando a API REST do Google Gemini (Multimodal Audio Output).
    Independente da biblioteca google-generativeai para maior compatibilidade.
    """
    
    # Modelo GA para TTS
    MODEL_NAME = "gemini-1.5-flash"
    DEFAULT_VOICE = "Kore"

    @staticmethod
    def generate_audio(text: str, output_path: str, voice_name: str = DEFAULT_VOICE) -> bool:
        """
        Gera áudio usando a API REST do Gemini.
        """
        if not GEMINI_API_KEY:
            logger.error("❌ GEMINI_API_KEY não configurada.")
            return False

        # Tentar modelos em ordem de preferência
        models_to_try = [GEMINI_MODEL, "gemini-2.0-flash", "gemini-1.5-flash-latest", "gemini-1.5-flash"]
        
        for model in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
            
            payload = {
                "contents": [{
                    "parts": [{"text": text}]
                }],
                "generationConfig": {
                    "responseModalities": ["AUDIO"],
                    "speechConfig": {
                        "voiceConfig": {
                            "prebuiltVoiceConfig": {
                                "voiceName": voice_name
                            }
                        }
                    }
                }
            }

            try:
                logger.info(f"🎙️ Tentando gerar áudio via Gemini REST API ({model}, Voz: {voice_name})...")
                response = requests.post(
                    url, 
                    headers={"Content-Type": "application/json"},
                    json=payload,
                    timeout=60
                )
                
                if response.status_code == 200:
                    data = response.json()
                    audio_base64 = None
                    try:
                        audio_base64 = data['candidates'][0]['content']['parts'][0]['inlineData']['data']
                    except (KeyError, IndexError):
                        logger.warning(f"⚠️ Modelo {model} não retornou áudio. Tentando próximo...")
                        continue

                    if audio_base64:
                        with open(output_path, "wb") as f:
                            f.write(base64.b64decode(audio_base64))
                        logger.info(f"✅ Áudio Gemini salvo em: {output_path} (usando {model})")
                        return True
                else:
                    logger.warning(f"⚠️ Erro no modelo {model}: {response.status_code}. Tentando próximo...")
                    continue

            except Exception as e:
                logger.error(f"❌ Falha na conexão com {model}: {e}")
                continue
        
        logger.error("❌ Todos os modelos Gemini falharam para TTS.")
        return False

if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Gerador de Áudio TTS via Gemini")
    parser.add_argument("--input", type=str, required=True, help="Caminho do arquivo de texto de entrada")
    parser.add_argument("--out", type=str, required=True, help="Caminho do arquivo de áudio de saída")
    parser.add_argument("--voice", type=str, default=GoogleGeminiTTS.DEFAULT_VOICE, help="Nome da voz")
    
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    
    if not os.path.exists(args.input):
        print(f"❌ Erro: Arquivo de entrada não encontrado: {args.input}")
        sys.exit(1)
        
    with open(args.input, "r", encoding="utf-8") as f:
        text = f.read().strip()
    
    if not text:
        print("❌ Erro: O arquivo de entrada está vazio.")
        sys.exit(1)
        
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    
    if GoogleGeminiTTS.generate_audio(text, args.out, args.voice):
        print(f"✅ Áudio salvo em: {args.out}")
    else:
        print("❌ Falha ao gerar áudio.")
        sys.exit(1)
