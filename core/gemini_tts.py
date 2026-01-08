import requests
import json
import base64
import wave
import re
import time
import os
import logging
from config import GEMINI_API_KEY

# Configuração de Logs do Sistema
logger = logging.getLogger(__name__)

class GeminiTTS:
    def __init__(self, api_key=None):
        # Usa a chave do config se não for passada explicitamente
        self.api_key = api_key or GEMINI_API_KEY
        if not self.api_key:
            logger.error("❌ GEMINI_API_KEY não encontrada!")
            raise ValueError("API Key é obrigatória para GeminiTTS.")
            
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent?key={self.api_key}"
        
        # Lista completa de vozes disponíveis no Gemini 2.5
        self.VOICES = [
            "Zephyr", "Puck", "Charon", "Kore", "Fenrir", "Leda", "Orus", 
            "Aoede", "Callirrhoe", "Autonoe", "Enceladus", "Iapetus", "Umbriel", 
            "Algieba", "Despina", "Erinome", "Algenib", "Rasalgethi", "Laomedeia", 
            "Achernar", "Alnilam", "Schedar", "Gacrux", "Pulcherrima", "Achird", 
            "Zubenelgenubi", "Vindemiatrix", "Sadachbia", "Sadaltager", "Sulafat"
        ]

    def generate(self, text, output_path="output.wav", voice="Kore"):
        """
        Gera áudio para um único narrador.
        """
        logger.info(f"🗣️ Gerando TTS (Voice: {voice}): {text[:50]}...")
        payload = {
            "contents": [{
                "parts": [{"text": text}]
            }],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "voiceConfig": {
                        "prebuiltVoiceConfig": {
                            "voiceName": voice
                        }
                    }
                }
            }
        }
        return self._execute_request(payload, output_path)

    def generate_multi_speaker(self, dialogue, output_path="dialogue.wav", speakers_config=None):
        """
        Gera áudio com múltiplos personagens.
        dialogue: String no formato "Nome: fala"
        speakers_config: Dicionário { "Nome": "Voz" }
        """
        if not speakers_config:
            # Default fallback
            speakers_config = {"Narrador": "Kore", "Personagem": "Leda"}

        logger.info(f"🗣️👥 Gerando Multi-Speaker TTS: {list(speakers_config.keys())}")

        speaker_configs = []
        for name, voice in speakers_config.items():
            speaker_configs.append({
                "speaker": name,
                "voiceConfig": {
                    "prebuiltVoiceConfig": {"voiceName": voice}
                }
            })

        payload = {
            "contents": [{
                "parts": [{"text": dialogue}]
            }],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "multiSpeakerVoiceConfig": {
                        "speakerVoiceConfigs": speaker_configs
                    }
                }
            }
        }
        return self._execute_request(payload, output_path)

    def _execute_request(self, payload, output_path):
        retries = 3
        for i in range(retries):
            try:
                response = requests.post(self.url, json=payload, timeout=60)
                if response.status_code == 200:
                    data = response.json()
                    
                    if 'candidates' not in data or not data['candidates']:
                        logger.error("❌ API retornou sucesso mas sem candidatos.")
                        return None

                    part = data['candidates'][0]['content']['parts'][0]['inlineData']
                    
                    # Extração do Sample Rate via Regex do MimeType (ex: audio/L16;rate=24000)
                    sample_rate_match = re.search(r'rate=(\d+)', part['mimeType'])
                    sample_rate = int(sample_rate_match.group(1)) if sample_rate_match else 24000
                    
                    audio_content = base64.b64decode(part['data'])
                    self._save_wav(audio_content, output_path, sample_rate)
                    
                    logger.info(f"✅ Áudio salvo: {output_path} ({sample_rate}Hz)")
                    return output_path
                
                elif response.status_code == 429:
                    wait_time = 2**i
                    logger.warning(f"⚠️ Rate Limit (429). Aguardando {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"❌ Erro API {response.status_code}: {response.text}")
                    break
            except Exception as e:
                logger.error(f"❌ Falha na conexão: {e}")
                time.sleep(2**i)
        return None

    def _save_wav(self, pcm_data, filename, sample_rate):
        # Garante que o diretório existe
        os.makedirs(os.path.dirname(filename) or '.', exist_ok=True)
        
        with wave.open(filename, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2) # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(pcm_data)
