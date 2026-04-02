import os, subprocess, sys, logging, random, re, math
from datetime import datetime
from typing import List, Optional
from config import VIDEO_FPS, OUTPUT_DIR, ASSETS_DIR, SCRIPTS_DIR, TTS_ENGINE
from core.ffmpeg_engine import FFmpegEngine
from core.gemini_tts import GeminiTTS
from core.subtitle_utils import generate_ass_from_text

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BROLL_DIR = os.path.join(ASSETS_DIR, "broll")
AUDIO_DIR = os.path.join(ASSETS_DIR, "audio")
RENDER_DIR = os.path.join(OUTPUT_DIR, "renders")
CACHE_DIR = os.path.join(OUTPUT_DIR, "cache")

def generate_video(script_path, theme_name="yellow_punch"):
    """v1.7: ABSOLUTE CINEMA - Cinematic Subtitles & Audio Mastering"""
    os.makedirs(RENDER_DIR, exist_ok=True)
    os.makedirs(CACHE_DIR, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    script_name = os.path.basename(script_path).replace(".txt", "")
    output_filename = f"HOMES_v1.7_{timestamp}.mp4"
    output_file = os.path.join(RENDER_DIR, output_filename)
    audio_file = os.path.join(CACHE_DIR, f"{script_name}_audio.wav")
    subs_file = os.path.join(CACHE_DIR, f"{script_name}_subs.ass")

    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            
        # 1. Áudio & Legendas
        if TTS_ENGINE == "gemini":
            GeminiTTS().generate(content, audio_file, voice="Kore")
        else:
            audio_file = audio_file.replace(".wav", ".mp3")
            subprocess.run(["edge-tts", "--text", content, "--write-media", audio_file, "--voice", "pt-BR-AntonioNeural"], check=True)
        
        duration = FFmpegEngine.get_duration(audio_file)
        generate_ass_from_text(content, duration, subs_file)
        v_dur = duration + 2.0
        
        # 2. B-Roll Sequencer
        clips = [os.path.join(BROLL_DIR, f) for f in os.listdir(BROLL_DIR) if f.endswith('.mp4')]
        if not clips:
            logger.error("Sem clips em assets/broll/")
            return None
            
        brolls = [random.choice(clips) for _ in range(math.ceil(v_dur/4))]
        
        # 3. FFmpeg Filter Chain (Ken Burns + Grading + ASS)
        inputs, filter_c = [], ""
        for i, b in enumerate(brolls):
            inputs.extend(["-i", b])
            filter_c += FFmpegEngine.build_zoompan_filter(i, 4.0, 30, random.choice(["zoom_in", "zoom_out"]))
        
        filter_c += "".join([f"[v{i}]" for i in range(len(brolls))]) + f"concat=n={len(brolls)}:v=1:a=0[v_base];"
        filter_c += f"[v_base]eq=contrast=1.1:saturation=1.2,vignette='PI/4'[v_gr];[v_gr]ass={subs_file.replace(':','\\\\:')}[v_out]"
        
        # 4. Audio Mastering
        m_path = next((os.path.join(AUDIO_DIR, f) for f in os.listdir(AUDIO_DIR) if f.endswith(('.mp3','.wav'))), None)
        inputs.extend(["-i", audio_file])
        master = FFmpegEngine.get_audio_master_filter()
        
        if m_path:
            inputs.extend(["-stream_loop", "-1", "-i", m_path])
            filter_c += f";[{len(brolls)}:a]adelay=1000|1000,volume=1.8,asplit[n1][n2];[{len(brolls)}+1:a]volume=0.3[bg];[bg][n2]sidechaincompress=threshold=0.01:ratio=20[bgd];[n1][bgd]amix=inputs=2:duration=first,{master}[a_out]"
        else:
            filter_c += f";[{len(brolls)}:a]adelay=1000|1000,volume=1.5,{master}[a_out]"

        # 5. Render
        logger.info(f"🎬 Renderizando v1.7: {output_filename}")
        subprocess.run(["ffmpeg"] + inputs + ["-filter_complex", filter_c, "-map", "[v_out]", "-map", "[a_out]", "-c:v", "libx264", "-preset", "superfast", "-t", str(v_dur), output_file, "-y"], check=True)
        
        # 6. Salvar em Downloads do Celular
        # Tentamos o caminho padrão do Android no Termux
        android_download = "/sdcard/Download/"
        try:
            subprocess.run(["cp", output_file, f"{android_download}{output_filename}"], check=True)
            print(f"\n🚀 SUCESSO! Vídeo salvo em Downloads.")
        except Exception as e:
            print(f"\n⚠️ Falha ao copiar para Downloads. Verifique permissões: {e}")

        return os.path.abspath(output_file)
    except Exception as e:
        logger.error(f"Erro Crítico: {e}")
        return None

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("script")
    args = parser.parse_args()
    generate_video(args.script)
