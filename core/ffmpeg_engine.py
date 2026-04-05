import subprocess
import logging
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
