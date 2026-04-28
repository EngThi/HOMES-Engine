import os, sys, logging, random, json
from datetime import datetime
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import VIDEO_FPS, OUTPUT_DIR, ASSETS_DIR, SCRIPTS_DIR, TTS_ENGINE
from core.ffmpeg_engine import FFmpegEngine
from core.gemini_tts import GeminiTTS
from core.subtitle_utils import generate_ass_from_text
from core.branding_loader import BrandingLoader
from core.image_gen import ImageGenerator
from core.videolm_client import assemble_via_videolm

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BROLL_DIR  = os.path.join(ASSETS_DIR, "broll")
AUDIO_DIR  = os.path.join(ASSETS_DIR, "audio")
RENDER_DIR = os.path.join(OUTPUT_DIR,  "renders")
CACHE_DIR  = os.path.join(OUTPUT_DIR,  "cache")


class VideoProject:
    def __init__(self, script_path: str, brand_name: str = "default"):
        self.timestamp   = datetime.now().strftime("%H%M%S")
        self.script_name = Path(script_path).stem.replace(".pending", "")
        self.project_id  = f"{self.script_name}_{self.timestamp}"
        self.project_dir = os.path.join(CACHE_DIR, self.project_id)
        os.makedirs(self.project_dir, exist_ok=True)
        self.audio_file  = os.path.join(self.project_dir, "narration.wav")
        self.subs_file   = os.path.join(self.project_dir, "subtitles.ass")
        self.output_file = os.path.join(RENDER_DIR, f"HOMES_{self.project_id}.mp4")


def generate_video(
    script_path: str,
    theme_name:  str = "yellow_punch",
    brand_name:  str = "default",
) -> Optional[str]:
    """
    Pipeline principal — Engine como orquestrador, VideoLM como renderizador.

    Estágios:
        1. Carrega roteiro
        2. Gemini TTS  → narration.wav
        3. Legenda ASS (local, para referência)
        4. Gera imagens de cena em paralelo (Gemini → Pollinations fallback)
        5. Delega montagem FFmpeg ao VideoLM via videolm_client
        6. Copia .mp4 final para output/renders e salva metadata.json
    """
    proj     = VideoProject(script_path, brand_name)
    branding = BrandingLoader(brand_name)
    brand_cfg   = branding.get_config() if hasattr(branding, "get_config") else {}
    brand_style = branding.get_style_prompt()

    try:
        # ---- 1. Roteiro ----
        with open(script_path, "r", encoding="utf-8") as f:
            content = f.read().strip()

        if not content:
            logger.error("❌ Script vazio")
            return None

        # ---- 2. TTS ----
        logger.info(f"🎙️  TTS → {proj.audio_file}")
        voice = brand_cfg.get("voice", "Kore")
        
        # Se o áudio já existir (user upload), pula a geração
        if os.path.exists(proj.audio_file) and os.path.getsize(proj.audio_file) > 1000:
            logger.info("♻️  Usando áudio pré-existente (upload detectado)")
        else:
            tts_success = GeminiTTS().generate(content, proj.audio_file, voice=voice)
            # Fallback para Edge-TTS se o Gemini falhar (ex: cota 429)
            if not tts_success or not os.path.exists(proj.audio_file):
                logger.warning("⚠️ Gemini TTS falhou ou cota excedida. Usando Edge-TTS como fallback...")
                voice_fallback = "pt-BR-AntonioNeural" if "pt" in content.lower() else "en-US-ChristopherNeural"
                import subprocess
                subprocess.run(["edge-tts", "--text", content, "--write-media", proj.audio_file, "--voice", voice_fallback], check=True)

        if not os.path.exists(proj.audio_file):
            logger.error("❌ Falha crítica no TTS — nenhum motor funcionou")
            return None

        duration = FFmpegEngine.get_duration(proj.audio_file)
        logger.info(f"⏱️  Duração detectada: {duration:.1f}s")

        # ---- 3. Legendas locais (para debug / fallback) ----
        generate_ass_from_text(
            content, 
            duration, 
            proj.subs_file, 
            brand_colors=brand_cfg.get("colors"), 
            start_offset=1.0
        )

        # ---- 4. Geração de imagens ----
        sentences = [s.strip() for s in content.split(".") if len(s.strip()) > 10]
        logger.info(f"🖼️  Gerando {len(sentences)} imagens de cena...")

        img_gen = ImageGenerator()

        def generate_scene_image(args):
            i, sentence = args
            img_name = f"scene_{i}.jpg"
            prompt   = (
                f"Cinematic vertical photography, {sentence[:120]}, "
                f"{brand_style}, photorealistic, 8k, 9:16 aspect ratio, "
                "dramatic lighting, no text, no watermarks"
            )
            result = img_gen.generate(prompt, img_name)
            if result:
                dest = os.path.join(proj.project_dir, img_name)
                os.replace(result, dest)
                return dest
            return None

        with ThreadPoolExecutor(max_workers=4) as executor:
            scene_assets = [
                r for r in executor.map(generate_scene_image, enumerate(sentences))
                if r is not None
            ]

        if not scene_assets:
            logger.error("❌ Nenhuma imagem gerada — pipeline abortado")
            return None

        logger.info(f"✅ {len(scene_assets)}/{len(sentences)} imagens prontas")

        # ---- 5. Renderização (VideoLM com Fallback Local) ----
        bg_music_id = (
            brand_cfg.get("music", {}).get("file", "")
            if isinstance(brand_cfg.get("music"), dict)
            else ""
        )

        os.makedirs(RENDER_DIR, exist_ok=True)
        output_path = None

        # Tenta VideoLM se configurado
        if os.getenv("VIDEOLM_URL"):
            logger.info("🚀 Tentando renderização via VideoLM...")
            try:
                output_path = assemble_via_videolm(
                    audio_path   = proj.audio_file,
                    image_paths  = scene_assets,
                    script       = content,
                    project_id   = proj.project_id,
                    bg_music_id  = bg_music_id,
                    output_dir   = RENDER_DIR,
                )
            except Exception as e:
                logger.warning(f"⚠️ VideoLM falhou: {e}. Mudando para FFmpeg Local...")

        # Fallback para Motor Local (FFmpeg)
        if not output_path:
            logger.info("🎬 Iniciando Renderização Local (FFmpeg Engine)...")
            
            output_filename = f"HOMES_{proj.project_id}.mp4"
            output_path = os.path.join(RENDER_DIR, output_filename)
            
            # Busca Assets de Branding
            logo_path = branding.get_asset_path("logo.png")
            bg_music = branding.get_asset_path("signature_music.mp3") or branding.get_asset_path("music.mp3")
            
            success = FFmpegEngine.assemble_video(
                audio_path=proj.audio_file,
                image_paths=scene_assets,
                subs_path=proj.subs_file,
                output_path=output_path,
                duration=duration,
                logo_path=logo_path,
                bg_music_path=bg_music
            )
            if not success:
                logger.error("❌ Falha na renderização local via FFmpeg")
                return None

        # ---- 6. Metadata ----
        metadata = {
            "project_id":  proj.project_id,
            "brand":       brand_name,
            "duration":    duration,
            "scenes":      len(scene_assets),
            "status":      "completed",
            "timestamp":   datetime.now().isoformat(),
            "output_file": output_path,
            "engine":      "VideoLM",
        }
        with open(os.path.join(proj.project_dir, "metadata.json"), "w") as f:
            json.dump(metadata, f, indent=4)

        logger.info(f"🎬 CONCLUÍDO → {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"🔥 Erro no pipeline: {e}", exc_info=True)
        return None


if __name__ == "__main__":
    if len(sys.argv) > 1:
        generate_video(sys.argv[1])
    else:
        print("Uso: python core/video_maker.py <caminho_do_script.txt>")
