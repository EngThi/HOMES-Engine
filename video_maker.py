import os
import subprocess
import sys
import logging
import textwrap
import asyncio
from datetime import datetime
from tts_engine import generate_audio

# Configuração de Logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configurações
ASSETS_DIR = "assets"
OUTPUT_DIR = "output"
SCRIPTS_DIR = "scripts"
FONT_PATH = os.path.join(ASSETS_DIR, "fonts", "Montserrat-ExtraBold.ttf")
TEMP_DIR = os.path.join(OUTPUT_DIR, "temp_lines")

def get_audio_duration(audio_path):
    try:
        result = subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", audio_path]
        )
        return float(result.strip())
    except:
        return 10.0

def create_dirs():
    os.makedirs(ASSETS_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(SCRIPTS_DIR, exist_ok=True)
    os.makedirs(TEMP_DIR, exist_ok=True)

def wrap_text(text, width=22):
    clean_text = " ".join(text.split())
    return textwrap.wrap(clean_text, width=width)

def generate_video(script_path, background_video="background.mp4"):
    """
    v1.3: Atomic Textfiles (Sem Quadradinhos + Sem Erros de Aspas/Escapes).
    """
    create_dirs()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    script_name = os.path.basename(script_path).replace(".txt", "")
    
    output_filename = f"HOMES_{timestamp}.mp4"
    output_file = os.path.join(OUTPUT_DIR, output_filename)
    audio_file = os.path.join(OUTPUT_DIR, f"{script_name}_audio.mp3")
    bg_path = os.path.join(ASSETS_DIR, background_video)

    if not os.path.exists(bg_path):
        logger.error(f"❌ Fundo não encontrado: {bg_path}")
        return

    current_font = FONT_PATH if os.path.exists(FONT_PATH) else "Arial"
    ffmpeg_font = current_font.replace(":", "\:")

    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 1. Gerar Áudio
        logger.info("🎤 Gerando narração neural...")
        asyncio.run(generate_audio(content, audio_file))
        audio_duration = get_audio_duration(audio_file)
        video_duration = audio_duration + 0.5

        # 2. Preparar Linhas (Atomic Textfiles)
        lines = wrap_text(content)
        font_size = 55
        line_spacing = 15
        total_lines = len(lines)
        block_height = total_lines * font_size + (total_lines - 1) * line_spacing
        
        # Filtro base (Redimensionamento)
        vf_chain = "scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280"
        
        # Limpar pasta temporária de linhas
        for f in os.listdir(TEMP_DIR):
            os.remove(os.path.join(TEMP_DIR, f))

        for i, line in enumerate(lines):
            # Salva cada linha num arquivo separado SEM QUEBRA DE LINHA
            line_file = os.path.join(TEMP_DIR, f"line_{i}.txt")
            with open(line_file, "w", encoding="utf-8") as f:
                f.write(line)
            
            ffmpeg_line_path = line_file.replace(":", "\:")
            y_pos = f"(h-{block_height})/2+{i}*({font_size}+{line_spacing})"
            
            # Adiciona o drawtext usando o arquivo (zero escape de conteúdo necessário!)
            vf_chain += (
                f",drawtext=fontfile='{ffmpeg_font}':textfile='{ffmpeg_line_path}':"
                f"fontcolor=white:fontsize={font_size}:x=(w-text_w)/2:y={y_pos}:"
                f"box=1:boxcolor=black@0.6:boxborderw=20"
            )

        # 3. Renderizar
        logger.info(f"🎬 Renderizando v1.3 (Duração: {video_duration:.2f}s)")
        cmd = [
            "ffmpeg",
            "-stream_loop", "-1", "-i", bg_path,
            "-i", audio_file,
            "-vf", vf_chain,
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "26",
            "-c:a", "aac", "-b:a", "192k",
            "-t", str(video_duration),
            output_file, "-y"
        ]
        
        subprocess.run(cmd, check=True)
        logger.info(f"✅ Vídeo gerado: {output_file}")

        # 4. Download Automático
        android_download_path = f"/sdcard/Download/{output_filename}"
        try:
            subprocess.run(["cp", output_file, android_download_path], check=True)
            print(f"\n🚀 SUCESSO ABSOLUTO!")
            print(f"📍 Vídeo completo em: Downloads/{output_filename}")
        except:
            print("\n⚠️ Erro ao copiar. Verifique as permissões de storage.")

    except Exception as e:
        logger.error(f"❌ Erro: {e}")

if __name__ == "__main__":
    create_dirs()
    if len(sys.argv) > 1:
        generate_video(sys.argv[1])
    else:
        print("Uso: python video_maker.py <script>")