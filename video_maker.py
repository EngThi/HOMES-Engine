import os
import subprocess
import sys
import logging
import random
import asyncio
import re
from datetime import datetime

# Configuração de Logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configurações
ASSETS_DIR = "assets"
BROLL_DIR = os.path.join(ASSETS_DIR, "broll")
OUTPUT_DIR = "output"
SCRIPTS_DIR = "scripts"
FONT_PATH = os.path.join(ASSETS_DIR, "fonts", "Montserrat-ExtraBold.ttf")

def get_audio_duration(audio_path):
    try:
        result = subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", audio_path]
        )
        return float(result.strip())
    except:
        return 10.0

def shift_vtt_timestamps(vtt_path, offset_seconds):
    """Adiciona um atraso aos tempos do arquivo VTT para sincronizar com o áudio atrasado."""
    def shift_match(match):
        h, m, s, ms = map(float, match.groups())
        total_seconds = h * 3600 + m * 60 + s + ms / 1000 + offset_seconds
        new_h = int(total_seconds // 3600)
        new_m = int((total_seconds % 3600) // 60)
        new_s = int(total_seconds % 60)
        new_ms = int((total_seconds * 1000) % 1000)
        return f"{new_h:02d}:{new_m:02d}:{new_s:02d}.{new_ms:03d}"

    pattern = re.compile(r"(\d{2}):(\d{2}):(\d{2})\.(\d{3})")
    
    with open(vtt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    new_content = pattern.sub(shift_match, content)
    
    with open(vtt_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

def create_dirs():
    os.makedirs(ASSETS_DIR, exist_ok=True)
    os.makedirs(BROLL_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(SCRIPTS_DIR, exist_ok=True)

def find_background_music():
    for ext in ['mp3', 'wav']:
        for file in os.listdir(ASSETS_DIR):
            if file.lower().endswith(f".{ext}"):
                return os.path.join(ASSETS_DIR, file)
    return None

def pick_random_broll():
    files = [f for f in os.listdir(BROLL_DIR) if f.lower().endswith('.mp4')]
    if not files:
        default_bg = os.path.join(ASSETS_DIR, "background.mp4")
        return default_bg if os.path.exists(default_bg) else None
    return os.path.join(BROLL_DIR, random.choice(files))

def generate_video(script_path):
    """
    v1.6: B-Roll Dinâmico + Legendas Sincronizadas (VTT Shifting) + Music Ducking.
    """
    create_dirs()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    script_name = os.path.basename(script_path).replace(".txt", "")
    
    output_filename = f"HOMES_v1.6_{timestamp}.mp4"
    output_file = os.path.join(OUTPUT_DIR, output_filename)
    audio_file = os.path.join(OUTPUT_DIR, f"{script_name}_audio.mp3")
    subs_file = os.path.join(OUTPUT_DIR, f"{script_name}_subs.vtt")
    
    broll_path = pick_random_broll()
    music_path = find_background_music()

    if not broll_path:
        logger.error("❌ Nenhum B-Roll encontrado.")
        return

    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        # 1. Gerar Áudio e Legenda
        logger.info(f"🎤 Gerando narração e legendas...")
        voice = "pt-BR-AntonioNeural"
        subprocess.run([
            "edge-tts", "--text", content, "--write-media", audio_file, 
            "--write-subtitles", subs_file, "--voice", voice
        ], check=True)
        
        # 2. Sincronização (Delay de 2s)
        intro_delay = 2.0
        shift_vtt_timestamps(subs_file, intro_delay)
        
        audio_duration = get_audio_duration(audio_file)
        video_duration = audio_duration + intro_delay + 0.5

        # 3. Filtros
        ffmpeg_subs = subs_file.replace(":", "\\:")
        
        # Estilo Profissional: Fonte grande, Caixa preta, Centralizado
        subs_style = (
            "force_style='Alignment=2,BorderStyle=3,Outline=1,Shadow=0,"
            "MarginV=140,Fontname=Montserrat ExtraBold,FontSize=22,PrimaryColour=&H00FFFFFF'"
        )

        vf_chain = (
            f"scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,"
            f"subtitles={ffmpeg_subs}:{subs_style}"
        )

        # 4. Mixagem
        if music_path:
            logger.info(f"🎶 Mixando áudio com B-Roll: {os.path.basename(broll_path)}")
            audio_filter = (
                f"[1:a]volume=1.5,adelay=2000|2000,asplit[v1][v2];"
                f"[2:a]volume=0.4[m];"
                f"[m][v2]sidechaincompress=threshold=0.03:ratio=20:attack=5:release=500[m_d];"
                f"[v1][m_d]amix=inputs=2:duration=first[a_out]"
            )
            inputs = ["-stream_loop", "-1", "-i", broll_path, "-i", audio_file, "-stream_loop", "-1", "-i", music_path]
            map_audio = "[a_out]"
        else:
            audio_filter = f"[1:a]volume=1.5,adelay=2000|2000[a_out]"
            inputs = ["-stream_loop", "-1", "-i", broll_path, "-i", audio_file]
            map_audio = "[a_out]"

        # 5. Renderizar
        logger.info(f"🎬 Renderizando v1.6 | Duração: {video_duration:.2f}s")
        cmd = ["ffmpeg"] + inputs + [
            "-filter_complex", audio_filter, "-vf", vf_chain,
            "-map", "0:v", "-map", map_audio,
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "26",
            "-c:a", "aac", "-b:a", "192k", "-t", str(video_duration),
            output_file, "-y"
        ]
        
        subprocess.run(cmd, check=True)
        logger.info(f"✅ Sucesso!")

        # 6. Download
        android_download_path = f"/sdcard/Download/{output_filename}"
        try:
            subprocess.run(["cp", output_file, android_download_path], check=True)
            print(f"\n🚀 ABSOLUTE CINEMA v1.6 OPERACIONAL!")
            print(f"🎬 Vídeo: {output_filename}")
            print(f"📍 Pasta: Downloads do Celular")
        except:
            print("\n⚠️ Erro ao copiar para Downloads.")

    except Exception as e:
        logger.error(f"❌ Erro: {e}")

if __name__ == "__main__":
    create_dirs()
    if len(sys.argv) > 1:
        generate_video(sys.argv[1])
    else:
        print("Uso: python video_maker.py <script>")