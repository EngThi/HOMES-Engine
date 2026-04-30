import os
import struct
import logging
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)
from core.key_utils import get_gemini_keys

class GeminiTTS:
    def __init__(self):
        # Pool de chaves verificadas para resiliência total via .env
        self.api_keys = get_gemini_keys()
        self.current_idx = 0
        self.model_id = "gemini-2.5-flash-preview-tts"


    def _convert_to_wav(self, audio_data: bytes, mime_type: str) -> bytes:
        """Adiciona cabeçalho WAV aos dados brutos L16 retornados pelo Gemini."""
        bits_per_sample = 16
        sample_rate = 24000
        if "rate=" in mime_type:
            try: sample_rate = int(mime_type.split("rate=")[1].split(";")[0])
            except: pass
        num_channels = 1
        data_size = len(audio_data)
        bytes_per_sample = bits_per_sample // 8
        block_align = num_channels * bytes_per_sample
        byte_rate = sample_rate * block_align
        chunk_size = 36 + data_size
        header = struct.pack("<4sI4s4sIHHIIHH4sI", b"RIFF", chunk_size, b"WAVE", b"fmt ", 16, 1, num_channels, sample_rate, byte_rate, block_align, bits_per_sample, b"data", data_size)
        return header + audio_data

    def _write_stream_to_wav(self, client, text, config, output_path):
        full_audio_data = b""
        mime_type = "audio/L16;rate=24000"

        for chunk in client.models.generate_content_stream(model=self.model_id, contents=text, config=config):
            if chunk.parts:
                for part in chunk.parts:
                    if part.inline_data:
                        full_audio_data += part.inline_data.data
                        if part.inline_data.mime_type:
                            mime_type = part.inline_data.mime_type

        if not full_audio_data:
            raise Exception("Empty audio response")

        wav_data = self._convert_to_wav(full_audio_data, mime_type)
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(wav_data)
        return True

    def generate(self, text, output_path, voice="Zephyr"):
        """Gera áudio com Key Rotation e modelo v2.5 Flash TTS."""
        if not self.api_keys:
            logger.error("Nenhuma GEMINI_API_KEY disponível!")
            return False

        for _ in range(len(self.api_keys)):
            key = self.api_keys[self.current_idx]
            logger.info(f"🗣️  Gemini TTS (v2.5) | Key: {key[:6]}...")
            
            try:
                client = genai.Client(api_key=key)
                config = types.GenerateContentConfig(
                    temperature=1.0,
                    response_modalities=["audio"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
                        )
                    ),
                )

                self._write_stream_to_wav(client, text, config, output_path)
                logger.info(f"✅ Áudio salvo com Key: {key[:6]}...")
                return True

            except Exception as e:
                logger.warning(f"⚠️ Erro no GeminiTTS com chave {self.current_idx}: {e}")
                self.current_idx = (self.current_idx + 1) % len(self.api_keys)
        
        return False

    def generate_multi_speaker(self, dialogue, output_path, speakers_config=None):
        """Gera diálogo TTS com múltiplas vozes usando speaker labels."""
        if not self.api_keys:
            logger.error("Nenhuma GEMINI_API_KEY disponível!")
            return False

        speakers_config = speakers_config or {}
        speaker_voice_configs = [
            types.SpeakerVoiceConfig(
                speaker=speaker,
                voiceConfig=types.VoiceConfig(
                    prebuiltVoiceConfig=types.PrebuiltVoiceConfig(voice_name=voice)
                ),
            )
            for speaker, voice in speakers_config.items()
        ]

        for _ in range(len(self.api_keys)):
            key = self.api_keys[self.current_idx]
            logger.info(f"🗣️  Gemini TTS Multi-Speaker | Key: {key[:6]}...")

            try:
                client = genai.Client(api_key=key)
                config = types.GenerateContentConfig(
                    temperature=1.0,
                    response_modalities=["audio"],
                    speech_config=types.SpeechConfig(
                        multiSpeakerVoiceConfig=types.MultiSpeakerVoiceConfig(
                            speakerVoiceConfigs=speaker_voice_configs
                        )
                    ),
                )

                self._write_stream_to_wav(client, dialogue, config, output_path)
                logger.info(f"✅ Áudio multi-speaker salvo com Key: {key[:6]}...")
                return True

            except Exception as e:
                logger.warning(f"⚠️ Erro no GeminiTTS multi-speaker com chave {self.current_idx}: {e}")
                self.current_idx = (self.current_idx + 1) % len(self.api_keys)

        return False
