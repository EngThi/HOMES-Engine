import subprocess
import logging
import os
from typing import List, Optional

logger = logging.getLogger(__name__)

class FFmpegEngine:
    """
    Motor especializado em comandos FFmpeg para o pipeline Absolute Cinema.
    """
    
    @staticmethod
    def get_duration(file_path: str) -> float:
        try:
            result = subprocess.check_output(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", file_path]
            )
            return float(result.strip())
        except Exception as e:
            logger.error(f"Erro ao obter duração de {file_path}: {e}")
            return 0.0

    @staticmethod
    def run_command(cmd: List[str]) -> bool:
        try:
            logger.info(f"Executando FFmpeg: {' '.join(cmd[:10])}...")
            subprocess.run(cmd, check=True)
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg falhou: {e}")
            return False
        except Exception as e:
            logger.error(f"Erro inesperado: {e}")
            return False

    @staticmethod
    def get_audio_master_filter() -> str:
        """
        Aplica o filtro de normalização de volume (Loudness Normalization)
        Padrão: EBU R128 (-14 LUFS) para YouTube/Spotify.
        """
        return "loudnorm=I=-14:LRA=11:tp=-1.5"

    @staticmethod
    def build_zoompan_filter(index: int, duration: float, fps: int, mode: str = "zoom_in") -> str:
        """
        Cria o efeito Ken Burns (ZoomPan) Cinematográfico.
        Modos: zoom_in, zoom_out, pan_left, pan_right
        """
        d = int(duration * fps)
        s = "720x1280" # Resolução vertical para shorts/reels
        
        # Lógica de Movimento de Câmera (Ken Burns 2.0)
        if mode == "zoom_in":
            z = "min(zoom+0.0015,1.5)"
            x = "iw/2-(iw/zoom/2)"
            y = "ih/2-(ih/zoom/2)"
        elif mode == "zoom_out":
            z = "if(eq(on,0),1.5,max(zoom-0.0015,1))"
            x = "iw/2-(iw/zoom/2)"
            y = "ih/2-(ih/zoom/2)"
        elif mode == "pan_left":
            z = "1.3"
            x = f"(1-on/{d})*(iw-iw/zoom)"
            y = "ih/2-(ih/zoom/2)"
        else: # pan_right
            z = "1.3"
            x = f"(on/{d})*(iw-iw/zoom)"
            y = "ih/2-(ih/zoom/2)"

        # Color Grading: Aumenta contraste e saturação para o look "Absolute Cinema"
        color_grade = "eq=contrast=1.15:saturation=1.3:brightness=0.02"
        
        return (
            f"[{index}:v]scale=2000:-1,zoompan=z='{z}':x='{x}':y='{y}':d={d}:s={s}:fps={fps},"
            f"{color_grade},setsar=1,format=yuv420p,trim=duration={duration},setpts=PTS-STARTPTS[v{index}];"
        )

    @staticmethod
    def assemble_video(audio_path: str, image_paths: list, subs_path: str, output_path: str, duration: float, logo_path: str = None, bg_music_path: str = None) -> bool:
        """
        Versão de Alta Performance (v3.1):
        Suporta centenas de assets e vídeos longos (5min+).
        """
        fps = 24 # Reduzindo para 24fps em vídeos longos para salvar processamento no Termux
        num_images = len(image_paths)
        if num_images == 0: return False
        
        clip_duration = duration / num_images
        
        # 1. Preparação de Inputs (Otimizado)
        inputs = []
        for img in image_paths: inputs.extend(["-i", img])
        inputs.extend(["-i", audio_path])
        
        has_logo = logo_path and os.path.exists(logo_path)
        if has_logo: inputs.extend(["-i", logo_path])

        has_music = bg_music_path and os.path.exists(bg_music_path)
        if has_music: inputs.extend(["-stream_loop", "-1", "-i", bg_music_path])

        # 2. Filtros de Vídeo (Ken Burns 3.1)
        filter_complex = ""
        modes = ["zoom_in", "zoom_out", "pan_left", "pan_right"]
        for i in range(num_images):
            mode = modes[i % len(modes)]
            filter_complex += FFmpegEngine.build_zoompan_filter(i, clip_duration, fps, mode)
        
        concat_v = "".join([f"[v{i}]" for i in range(num_images)])
        filter_complex += f"{concat_v}concat=n={num_images}:v=1:a=0[v_base];"
        
        # 3. Logo & Legendas (Layered)
        v_node = "[v_base]"
        if has_logo:
            logo_idx = num_images + 1
            filter_complex += f"{v_node}[{logo_idx}:v]overlay=W-w-40:40[v_logo];"
            v_node = "[v_logo]"
        
        safe_subs = subs_path.replace(":", "\\\\:")
        fonts_dir = os.path.join(os.getcwd(), "assets", "fonts")
        filter_complex += f"{v_node}ass='{safe_subs}':fontsdir='{fonts_dir}'[v_out];"
        
        # 4. Mixagem de Áudio
        voice_idx = num_images
        if has_music:
            music_idx = num_images + (2 if has_logo else 1)
            # Volume Boost na voz e Sidechain na música
            filter_complex += f"[{voice_idx}:a]volume=1.8[v_a];[{music_idx}:a]volume=0.15[m_a];[v_a][m_a]amix=inputs=2:duration=first[a_out]"
        else:
            filter_complex += f"[{voice_idx}:a]volume=1.8[a_out]"

        # 5. Renderização (Preset Ultrafast para Celular/Termux)
        cmd = [
            "ffmpeg", "-y", "-threads", "0",
            "-hide_banner", "-loglevel", "error"
        ]
        cmd.extend(inputs)
        cmd.extend([
            "-filter_complex", filter_complex,
            "-map", "[v_out]", "-map", "[a_out]",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "22",
            "-c:a", "aac", "-b:a", "128k", "-shortest",
            output_path
        ])
        
        return FFmpegEngine.run_command(cmd)
