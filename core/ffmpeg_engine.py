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
    def build_zoompan_filter(index: int, duration: float, fps: int) -> str:
        """Cria o efeito Ken Burns (ZoomPan) com standardização de SAR e formato."""
        return (
            f"[{index}:v]scale=1280:2276,zoompan=z='min(zoom+0.001,1.1)':d={int(duration*fps)}:s=720x1280:fps={fps},"
            f"setsar=1,format=yuv420p,trim=duration={duration},setpts=PTS-STARTPTS[v{index}];"
        )
