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
        Cria o efeito Ken Burns (ZoomPan) Cinematográfico com correção de proporção.
        """
        d = int(duration * fps)
        s = "720x1280"
        
        # Ken Burns 2.0
        if mode == "zoom_in":
            z = "min(zoom+0.0015,1.5)"
            x = "iw/2-(iw/zoom/2)"; y = "ih/2-(ih/zoom/2)"
        elif mode == "zoom_out":
            z = "if(eq(on,0),1.5,max(zoom-0.0015,1))"
            x = "iw/2-(iw/zoom/2)"; y = "ih/2-(ih/zoom/2)"
        else: # pan_left/right
            z = "1.3"; y = "ih/2-(ih/zoom/2)"
            x = f"(on/{d})*(iw-iw/zoom)" if mode == "pan_right" else f"(1-on/{d})*(iw-iw/zoom)"

        color_grade = "eq=contrast=1.15:saturation=1.3:brightness=0.02"
        
        # A MÁGICA: scale + crop para evitar achatamento
        return (
            f"[{index}:v]scale=1280:2275:force_original_aspect_ratio=increase,crop=1280:2275,scale=720:1280,"
            f"zoompan=z='{z}':x='{x}':y='{y}':d={d}:s={s}:fps={fps},"
            f"{color_grade},setsar=1,format=yuv420p,trim=duration={duration},setpts=PTS-STARTPTS[v{index}];"
        )
