import requests, json, base64, wave, re, time, os, logging, subprocess
from config import GEMINI_API_KEY, GEMINI_TTS_MODEL

logger = logging.getLogger(__name__)

class GeminiTTS:
    def __init__(self, api_key=None):
        self.api_key = api_key or GEMINI_API_KEY
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_TTS_MODEL}:generateContent?key={self.api_key}"

    def generate(self, text, output_path="output.wav", voice="Kore"):
        chunks = self._split_text(text, max_chars=300)
        logger.info(f"🛡️ Iniciando Pipeline Blindado: {len(chunks)} blocos.")
        temp_files = []
        
        for i, chunk in enumerate(chunks):
            temp_path = f"{output_path}.part{i}.wav"
            success = False
            
            # TENTATIVA 1: IA Cloud (Gemini)
            try:
                res = self._generate_chunk(chunk, temp_path, voice)
                if res: 
                    temp_files.append(temp_path)
                    success = True
            except: pass
            
            # TENTATIVA 2: Fallback Local (Termux TTS - Offline)
            if not success:
                logger.warning(f"⚠️ IA falhou no bloco {i+1}. Usando TTS Local do Android...")
                success = self._generate_local_fallback(chunk, temp_path)
                if success: temp_files.append(temp_path)
            
            # TENTATIVA 3: Silêncio (Garantia de não crash)
            if not success:
                logger.error(f"❌ Falha total no bloco {i+1}. Gerando silêncio de segurança.")
                self._generate_silence(temp_path)
                temp_files.append(temp_path)

            time.sleep(0.5)

        return self._merge_wavs(temp_files, output_path)

    def _generate_local_fallback(self, text, output_path):
        """Usa a Termux API para gerar áudio offline se a internet cair."""
        try:
            # Gera em WAV via termux-tts-speak
            subprocess.run(["termux-tts-speak", "-f", output_path, text], check=True, capture_output=True)
            return os.path.exists(output_path)
        except:
            return False

    def _generate_silence(self, output_path, duration=2.0):
        """Gera um arquivo de silêncio para manter o FFmpeg vivo."""
        try:
            subprocess.run(["ffmpeg", "-f", "lavfi", "-i", f"anullsrc=r=24000:cl=mono", "-t", str(duration), "-acodec", "pcm_s16le", output_path, "-y"], check=True, capture_output=True)
            return True
        except: return False

    def _split_text(self, text, max_chars=300):
        sentences = re.split(r'(?<=[.!?]) +', text)
        chunks, current = [], ""
        for s in sentences:
            if len(current) + len(s) < max_chars: current += " " + s
            else:
                if current: chunks.append(current.strip())
                current = s
        if current: chunks.append(current.strip())
        return [c for c in chunks if c]

    def _generate_chunk(self, text, output_path, voice):
        payload = {"contents": [{"parts": [{"text": text}]}], "generationConfig": {"responseModalities": ["AUDIO"], "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}}}}
        for i in range(2): # Menos retries aqui pois temos o fallback local
            try:
                response = requests.post(self.url, json=payload, timeout=20)
                if response.status_code == 200:
                    data = response.json()
                    if 'candidates' in data and data['candidates']:
                        part = data['candidates'][0]['content']['parts'][0]['inlineData']
                        self._save_wav(base64.b64decode(part['data']), output_path, 24000)
                        return output_path
                time.sleep(1)
            except: pass
        return None

    def _merge_wavs(self, files, output_path):
        if not files: return None
        data = []
        params = None
        for f in files:
            try:
                with wave.open(f, 'rb') as w:
                    if params is None: params = w.getparams()
                    data.append(w.readframes(w.getnframes()))
                os.remove(f)
            except: continue
        if not data: return None
        with wave.open(output_path, 'wb') as w:
            w.setparams(params)
            for d in data: w.writeframes(d)
        return output_path

    def _save_wav(self, pcm_data, filename, sample_rate):
        os.makedirs(os.path.dirname(filename) or '.', exist_ok=True)
        with wave.open(filename, 'wb') as wav_file:
            wav_file.setnchannels(1); wav_file.setsampwidth(2); wav_file.setframerate(sample_rate)
            wav_file.writeframes(pcm_data)
