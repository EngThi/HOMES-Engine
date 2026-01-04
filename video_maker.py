import os
import subprocess
import sys
import logging

# Configuração de Logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configurações
ASSETS_DIR = "assets"
OUTPUT_DIR = "output"
SCRIPTS_DIR = "scripts"

def check_ffmpeg():
    """Verifica se o FFmpeg está instalado."""
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.error("❌ FFmpeg não encontrado! Instale com: pkg install ffmpeg")
        return False

def create_dirs():
    """Cria pastas necessárias se não existirem."""
    os.makedirs(ASSETS_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(SCRIPTS_DIR, exist_ok=True)

def generate_video(script_path, background_video="background.mp4"):
    """
    Gera um vídeo com legendas baseadas no script.
    Otimizado para Mobile (720p + Ultrafast preset).
    """
    if not check_ffmpeg():
        return

    script_name = os.path.basename(script_path).replace(".txt", "")
    output_file = os.path.join(OUTPUT_DIR, f"{script_name}_final.mp4")
    bg_path = os.path.join(ASSETS_DIR, background_video)

    if not os.path.exists(bg_path):
        logger.warning(f"⚠️ Vídeo de fundo não encontrado em: {bg_path}")
        logger.info(f"ℹ️ Adicione um vídeo 'background.mp4' na pasta '{ASSETS_DIR}' para testar.")
        return

    logger.info(f"🎬 Iniciando renderização OTIMIZADA para: {script_name}")
    
    try:
        # Lendo o conteúdo do script
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Sanitização básica para FFmpeg
        text_content = content.replace(":", "\:").replace("'", "").replace("\n", " | ")[:100] + "..."

        # Comando Otimizado para Termux/Android:
        # 1. scale=1280:720 (Evita 4K pesado)
        # 2. preset ultrafast (Menos CPU, render mais rápido)
        # 3. crf 28 (Qualidade aceitável, arquivo leve)
        cmd = [
            "ffmpeg",
            "-i", bg_path,
            "-vf", f"scale=1280:720,drawtext=text='{text_content}':fontcolor=white:fontsize=48:x=(w-text_w)/2:y=(h-text_h)/2:box=1:boxcolor=black@0.6:boxborderw=10",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "28",
            "-c:a", "copy",
            "-t", "10", # Limitando a 10s para teste rápido
            output_file,
            "-y"
        ]
        
        subprocess.run(cmd, check=True)
        logger.info(f"✅ Vídeo gerado com sucesso: {output_file}")
        print("\n🛑 PARE AGORA E REGISTRE A PROVA! 🛑 (Verifique a pasta output)")

    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Erro na renderização: {e}")

if __name__ == "__main__":
    create_dirs()
    
    if len(sys.argv) > 1:
        generate_video(sys.argv[1])
    else:
        logger.info("ℹ️ Uso: python video_maker.py <caminho_do_script>")
