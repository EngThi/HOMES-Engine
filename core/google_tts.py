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
    
    # Modelo GA para TTS (Dez 2025)
    MODEL_NAME = "gemini-2.5-flash-tts"
    DEFAULT_VOICE = "Kore"

    @staticmethod
    def generate_audio(text: str, output_path: str, voice_name: str = DEFAULT_VOICE) -> bool:
        """
        Gera áudio usando a API REST do Gemini.
        """
        if not GEMINI_API_KEY:
            logger.error("❌ GEMINI_API_KEY não configurada.")
            return False

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{GoogleGeminiTTS.MODEL_NAME}:generateContent?key={GEMINI_API_KEY}"
        
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
            logger.info(f"🎙️ Gerando áudio via Gemini REST API ({voice_name})...")
            response = requests.post(
                url, 
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                # O áudio vem em base64 dentro de inlineData ou blob
                audio_base64 = None
                try:
                    # Estrutura padrão para multimodal output
                    audio_base64 = data['candidates'][0]['content']['parts'][0]['inlineData']['data']
                except (KeyError, IndexError):
                    logger.error(f"❌ Resposta da API não contém áudio: {json.dumps(data)[:200]}...")
                    return False

                if audio_base64:
                    with open(output_path, "wb") as f:
                        f.write(base64.b64decode(audio_base64))
                    logger.info(f"✅ Áudio Gemini salvo em: {output_path}")
                    return True
            else:
                logger.error(f"❌ Erro na API Gemini TTS: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"❌ Falha na conexão Gemini TTS: {e}")
            return False

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Teste rápido
    test_path = "output/cache/test_gemini_rest_tts.wav"
    os.makedirs("output/cache", exist_ok=True)
    if GoogleGeminiTTS.generate_audio("Teste de áudio via API REST do Gemini.", test_path):
        print(f"Sucesso: {test_path}")
    else:
        print("Falha no teste.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Teste rápido se houver chave
    test_path = "output/cache/test_gemini_tts.wav"
    os.makedirs("output/cache", exist_ok=True)
    if GoogleGeminiTTS.generate_audio("Este é o motor de voz Absolute Cinema do Google Gemini.", test_path):
        print(f"Sucesso: {test_path}")
    else:
        print("Falha no teste (Verifique se a GEMINI_API_KEY é válida para Gemini 2.5).")
