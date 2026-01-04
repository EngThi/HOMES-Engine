import os
import subprocess
import sys
import logging
import random
import re
import math
from datetime import datetime

# Configuração de Logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configurações Globais
ASSETS_DIR = "assets"
BROLL_DIR = os.path.join(ASSETS_DIR, "broll")
OUTPUT_DIR = "output"
SCRIPTS_DIR = "scripts"
FONT_PATH = os.path.join(ASSETS_DIR, "fonts", "Montserrat-ExtraBold.ttf")

# Temas Visuais (v1.4)
THEMES = {
    "default": (
        "Alignment=2,BorderStyle=3,Outline=1,Shadow=0,"
        "MarginV=40,Fontname=Montserrat ExtraBold,FontSize=18,PrimaryColour=&H00FFFFFF"
    ),
    "yellow_punch": (
        "Alignment=2,BorderStyle=1,Outline=2,Shadow=0,"
        "MarginV=40,Fontname=Montserrat ExtraBold,FontSize=20,PrimaryColour=&H0000FFFF,OutlineColour=&H00000000"
    ),
    "minimal_box": (
        "Alignment=2,BorderStyle=3,Outline=0,Shadow=0,"
        "MarginV=50,Fontname=Montserrat ExtraBold,FontSize=16,PrimaryColour=&H00FFFFFF,BackColour=&H80000000"
    )
}

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

def get_dynamic_broll_sequence(target_duration, clip_duration=3.0):
    """
    Seleciona múltiplos clipes aleatórios para cobrir a duração total.
    Retorna lista de caminhos absolutos.
    """
    files = [os.path.join(BROLL_DIR, f) for f in os.listdir(BROLL_DIR) if f.lower().endswith('.mp4')]
    
    if not files:
        # Fallback para background estático se não houver clipes
        default_bg = os.path.join(ASSETS_DIR, "background.mp4")
        return [default_bg] if os.path.exists(default_bg) else []

    num_clips = math.ceil(target_duration / clip_duration)
    sequence = []
    
    # Preenche a sequência garantindo variedade
    for _ in range(num_clips):
        sequence.append(random.choice(files))
        
    return sequence

def generate_video(script_path):
    """
    v1.4: Dynamic B-Roll (Cortes Rápidos) + Music Ducking + Themes
    """
    create_dirs()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    script_name = os.path.basename(script_path).replace(".txt", "")
    
    output_filename = f"HOMES_v1.4_{timestamp}.mp4"
    output_file = os.path.join(OUTPUT_DIR, output_filename)
    audio_file = os.path.join(OUTPUT_DIR, f"{script_name}_audio.mp3")
    subs_file = os.path.join(OUTPUT_DIR, f"{script_name}_subs.vtt")
    
    # 1. Gerar Áudio e Legenda
    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        logger.info(f"🎤 Gerando narração...")
        voice = "pt-BR-AntonioNeural"
        subprocess.run([
            "edge-tts", "--text", content, "--write-media", audio_file, 
            "--write-subtitles", subs_file, "--voice", voice
        ], check=True)
        
        # Sincronização
        intro_delay = 1.0 # Reduzi um pouco para ficar mais dinâmico
        shift_vtt_timestamps(subs_file, intro_delay)
        
        audio_duration = get_audio_duration(audio_file)
        video_duration = audio_duration + intro_delay + 1.0
        
        # 2. Preparar B-Roll Dinâmico
        clip_duration = 4.0 # 4 segundos por clipe
        broll_clips = get_dynamic_broll_sequence(video_duration, clip_duration)
        
        if not broll_clips:
            logger.error("❌ Nenhum arquivo de vídeo encontrado em assets/broll/ ou assets/background.mp4")
            return

        logger.info(f"🎞️ Sequência de B-Roll: {len(broll_clips)} clipes para {video_duration:.1f}s")

        # 3. Construir Filtro Complexo do FFmpeg
        inputs = []
        filter_complex = ""
        
        # Adiciona clipes de vídeo aos inputs
        for i, clip in enumerate(broll_clips):
            inputs.extend(["-i", clip])
            # Escala e Corta para 720x1280 (9:16) e trima duração
            filter_complex += (
                f"[{i}:v]scale=720:1280:force_original_aspect_ratio=increase,"
                f"crop=720:1280,trim=duration={clip_duration},setpts=PTS-STARTPTS[v{i}];"
            )
        
        # Concatena os streams de vídeo processados
        concat_inputs = "".join([f"[v{i}]" for i in range(len(broll_clips))])
        filter_complex += f"{concat_inputs}concat=n={len(broll_clips)}:v=1:a=0[v_base];"
        
        # Loop se necessário (segurança) e Legendas
        ffmpeg_subs = subs_file.replace(":", "\\:")
        selected_theme = THEMES["yellow_punch"] # Padrão v1.4
        
        filter_complex += (
            f"[v_base]loop=-1:size=32767:start=0[v_looped];"
            f"[v_looped]subtitles={ffmpeg_subs}:force_style='{selected_theme}'[v_out]"
        )

        # 4. Áudio (Music Ducking)
        music_path = find_background_music()
        narration_input_index = len(broll_clips) # O aúdio da narração é o próximo input
        inputs.extend(["-i", audio_file])
        
        if music_path:
            music_input_index = len(broll_clips) + 1
            inputs.extend(["-stream_loop", "-1", "-i", music_path])
            
            filter_complex += (
                f";[{narration_input_index}:a]adelay={int(intro_delay*1000)}|{int(intro_delay*1000)},volume=1.5,asplit[narr1][narr2];"
                f"[{music_input_index}:a]volume=0.3[bgm];"
                f"[bgm][narr2]sidechaincompress=threshold=0.03:ratio=20:attack=5:release=800[bgm_ducked];"
                f"[narr1][bgm_ducked]amix=inputs=2:duration=first[a_out]"
            )
        else:
             filter_complex += (
                f";[{narration_input_index}:a]adelay={int(intro_delay*1000)}|{int(intro_delay*1000)},volume=1.5[a_out]"
            )

        # 5. Comando Final
        logger.info(f"🎬 Renderizando v1.4...")
        cmd = ["ffmpeg"] + inputs + [
            "-filter_complex", filter_complex,
            "-map", "[v_out]", "-map", "[a_out]",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28", # CRF maior para rapidez no teste
            "-c:a", "aac", "-b:a", "128k",
            "-t", str(video_duration),
            output_file, "-y"
        ]
        
        subprocess.run(cmd, check=True)
        
        # 6. Copiar para Download
        android_download_path = f"/sdcard/Download/{output_filename}"
        try:
            subprocess.run(["cp", output_file, android_download_path], check=True)
            print(f"\n🚀 ABSOLUTE CINEMA v1.4 (DYNAMIC) OPERACIONAL!")
            print(f"🎬 Vídeo: {output_filename}")
            print(f"📍 Pasta: Downloads do Celular")
        except:
            print("\n⚠️ Vídeo salvo em output/ mas não copiado para SDCard.")

    except Exception as e:
        logger.error(f"❌ Erro Crítico: {e}")
        # Debug: Mostrar comando se falhar?
        # print(cmd)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        generate_video(sys.argv[1])
    else:
        print("Uso: python video_maker.py <script>")
