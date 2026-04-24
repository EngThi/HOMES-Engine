import os, subprocess, sys, logging, random, re, math, time, json
from datetime import datetime
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor

# Injetar a raiz do projeto no path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import VIDEO_FPS, OUTPUT_DIR, ASSETS_DIR, SCRIPTS_DIR, TTS_ENGINE
from core.ffmpeg_engine import FFmpegEngine
from core.gemini_tts import GeminiTTS
from core.subtitle_utils import generate_ass_from_text
from core.branding_loader import BrandingLoader
from core.image_gen import ImageGenerator

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BROLL_DIR, AUDIO_DIR = os.path.join(ASSETS_DIR, "broll"), os.path.join(ASSETS_DIR, "audio")
RENDER_DIR, CACHE_DIR = os.path.join(OUTPUT_DIR, "renders"), os.path.join(OUTPUT_DIR, "cache")

class VideoProject:
    def __init__(self, script_path, brand_name="default"):
        self.timestamp = datetime.now().strftime("%H%M%S")
        self.script_name = os.path.basename(script_path).replace(".txt", "").replace(".pending", "")
        self.project_id = f"{self.script_name}_{self.timestamp}"
        self.project_dir = os.path.join(OUTPUT_DIR, "cache", self.project_id)
        os.makedirs(self.project_dir, exist_ok=True)
        self.audio_file = os.path.join(self.project_dir, "narration.wav")
        self.subs_file = os.path.join(self.project_dir, "subtitles.ass")
        self.output_file = os.path.join(RENDER_DIR, f"HOMES_{self.project_id}.mp4")

def generate_video(script_path, theme_name="yellow_punch", brand_name="default"):
    """v1.8: Creator Branding Kit - Contextual Visuals & Semantic Sync"""
    proj = VideoProject(script_path, brand_name)
    branding = BrandingLoader(brand_name)
    brand_style = branding.get_style_prompt()

    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            
        # 1. Gerar Áudio Completo e Legendas
        logger.info(f"🎙️ Gerando narração: {proj.project_id}")
        GeminiTTS().generate(content, proj.audio_file, voice="Kore")
        duration = FFmpegEngine.get_duration(proj.audio_file)
        generate_ass_from_text(content, duration, proj.subs_file, start_offset=1.0)
        
        # 2. Lógica de Cenas Contextuais (v1.8 Semantic)
        # Quebra o roteiro em frases para gerar imagens que batem com o texto
        sentences = [s.strip() for s in content.split('.') if len(s.strip()) > 5]
        logger.info(f"🎞️ Roteiro dividido em {len(sentences)} cenas contextuais.")
        
        scene_assets = []
        
        def generate_scene_image(args):
            i, sentence = args
            img_name = f"scene_{i}.jpg"
            # Prompt focado na frase atual + estilo da marca
            prompt = f"Cinematic photography, {sentence}, {brand_style}, highly detailed, 8k, vertical 9:16"
            res = ImageGenerator.generate_image(prompt, img_name)
            if res:
                dest = os.path.join(proj.project_dir, img_name)
                os.rename(res, dest)
                return dest
            return None

        # Geração paralela das cenas para não demorar uma eternidade
        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(generate_scene_image, enumerate(sentences)))
            scene_assets = [r for r in results if r]

        if not scene_assets:
            logger.error("❌ Falha ao gerar imagens contextuais.")
            return None

        # 3. FFmpeg Chain - Ajustando duração de cada imagem ao tempo da frase
        # Heurística: Cada imagem dura proporcionalmente ao tamanho da frase
        total_chars = sum(len(s) for s in sentences)
        inputs, filter_c = [], ""
        
        current_v_time = 0.0
        for i, img in enumerate(scene_assets):
            sentence_dur = (len(sentences[i]) / total_chars) * duration
            # Garante tempo mínimo para o Ken Burns não bugar
            sentence_dur = max(2.5, sentence_dur) 
            
            inputs.extend(["-i", img])
            filter_c += FFmpegEngine.build_zoompan_filter(i, sentence_dur, 30, random.choice(["zoom_in", "zoom_out"]))
        
        concat_v = "".join([f"[v{i}]" for i in range(len(scene_assets))])
        filter_c += f"{concat_v}concat=n={len(scene_assets)}:v=1:a=0[v_base];"
        
        # Logo e Finalização Visual
        logo_path = branding.get_asset_path("logo.png")
        if logo_path:
            logo_idx = len(scene_assets) + 2
            inputs.extend(["-i", logo_path])
            filter_c += f"[v_base][{logo_idx}:v]overlay=W-w-20:20[v_logo];"
            v_node = "[v_logo]"
        else: v_node = "[v_base]"

        filter_c += f"{v_node}eq=contrast=1.1:saturation=1.2,vignette='PI/4'[v_gr];[v_gr]ass={proj.subs_file.replace(':','\\\\:')}[v_out]"
        
        # 4. Áudio e Masterização
        m_path = branding.get_asset_path("signature_music.mp3") or next((os.path.join(AUDIO_DIR, f) for f in os.listdir(AUDIO_DIR) if f.endswith(('.mp3','.wav'))), None)
        inputs.extend(["-i", proj.audio_file]); master = FFmpegEngine.get_audio_master_filter()
        
        if m_path:
            inputs.extend(["-stream_loop", "-1", "-i", m_path])
            filter_c += f";[{len(scene_assets)}:a]adelay=1000|1000,volume=1.8,asplit[n1][n2];[{len(scene_assets)}+1:a]volume=0.3[bg];[bg][n2]sidechaincompress=threshold=0.01:ratio=20[bgd];[n1][bgd]amix=inputs=2:duration=first,{master}[a_out]"
        else:
            filter_c += f";[{len(scene_assets)}:a]adelay=1000|1000,volume=1.5,{master}[a_out]"

        # 5. Render Final
        logger.info(f"🎬 Renderizando v1.8 Branded: {proj.project_id}")
        subprocess.run(["ffmpeg"] + inputs + ["-filter_complex", filter_c, "-map", "[v_out]", "-map", "[a_out]", "-c:v", "libx264", "-preset", "ultrafast", "-t", str(duration + 1.5), proj.output_file, "-y"], check=True)
        
        # 6. Exportação
        target = f"/sdcard/Download/HOMES_BRANDED_{proj.project_id}.mp4"
        subprocess.run(["cp", proj.output_file, target], check=True)
        subprocess.run(["termux-media-scan", target], capture_output=True)
        print(f"🚀 SUCESSO: {target}")

        return proj.output_file
    except Exception as e:
        logger.error(f"Erro: {e}")
        return None

if __name__ == "__main__":
    if len(sys.argv) > 1: generate_video(sys.argv[1])
