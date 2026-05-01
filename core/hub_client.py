"""
hub_client.py — HOMES-Engine → HOMES Hub API client

Responsabilidades:
  - Buscar jobs de vídeo pendentes
  - Reportar conclusão/erro de jobs
  - Enviar telemetria local (CPU, disco, status)
  - Receber e executar comandos remotos do Hub

Todos os endpoints e o secret batem com hub/main.py do HOMES.
"""
import os
import time
import hmac
import hashlib
import json
import logging
import platform
import shutil
import subprocess
import requests
from typing import Optional
from dotenv import load_dotenv

# Carregar variáveis de ambiente do .env
load_dotenv()

logger = logging.getLogger(__name__)

HUB_BASE   = os.getenv("HOMES_HUB_URL", "http://localhost:8080").rstrip("/")
HUB_SECRET = os.getenv("HUB_SECRET", "homes_secret_dev")
ENGINE_ID  = os.getenv("ENGINE_ID", f"engine_{platform.node()}")


def _sign(payload: dict) -> str:
    """HMAC-SHA256 para autenticar POSTs no Hub."""
    body = json.dumps(payload, separators=(',', ':')).encode()
    return hmac.new(HUB_SECRET.encode(), body, hashlib.sha256).hexdigest()


def _signed_body_and_headers(payload: dict) -> tuple[bytes, dict]:
    body = json.dumps(payload, separators=(',', ':')).encode()
    signature = hmac.new(HUB_SECRET.encode(), body, hashlib.sha256).hexdigest()
    headers = {
        "Content-Type": "application/json",
        "X-Homes-Signature": signature,
    }
    return body, headers


def _post_signed(path: str, payload: dict, timeout: int = 10) -> requests.Response:
    body, headers = _signed_body_and_headers(payload)
    return requests.post(f"{HUB_BASE}{path}", data=body, headers=headers, timeout=timeout)


def _public_video_url(video_path: str) -> str:
    """Best-effort public URL for Hub downloads."""
    if not video_path:
        return ""
    if video_path.startswith(("http://", "https://")):
        return video_path
    if video_path.startswith("/videos/"):
        base_url = os.getenv("VIDEOLM_URL", "").rstrip("/")
        return f"{base_url}{video_path}" if base_url else ""

    sidecar_path = f"{video_path}.source.json"
    if os.path.exists(sidecar_path):
        try:
            with open(sidecar_path, "r", encoding="utf-8") as f:
                source = json.load(f)
            source_url = source.get("video_url") or source.get("videoUrl")
            if source_url:
                return source_url
        except (OSError, json.JSONDecodeError) as e:
            logger.warning(f"Não foi possível ler URL pública do vídeo {video_path}: {e}")

    public_base = os.getenv("HOMES_ENGINE_PUBLIC_BASE_URL", "").rstrip("/")
    public_prefix = os.getenv("HOMES_ENGINE_PUBLIC_VIDEO_PATH", "/videos").strip("/")
    if public_base and os.path.exists(video_path):
        return f"{public_base}/{public_prefix}/{os.path.basename(video_path)}"

    return ""


def _video_metadata(video_path: str) -> dict:
    metadata = {}
    if not video_path or not os.path.exists(video_path):
        return metadata

    try:
        metadata["size_bytes"] = os.path.getsize(video_path)
    except OSError:
        pass

    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height,r_frame_rate,codec_name:format=duration",
                "-of",
                "json",
                video_path,
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as e:
        logger.warning(f"Não foi possível ler metadata do vídeo {video_path}: {e}")
        return metadata

    if result.returncode != 0:
        logger.warning(f"ffprobe falhou para {video_path}: {result.stderr[:200]}")
        return metadata

    try:
        data = json.loads(result.stdout or "{}")
    except json.JSONDecodeError as e:
        logger.warning(f"ffprobe retornou JSON inválido para {video_path}: {e}")
        return metadata

    duration = (data.get("format") or {}).get("duration")
    if duration:
        try:
            metadata["duration_seconds"] = round(float(duration), 3)
        except (TypeError, ValueError):
            pass

    streams = data.get("streams") or []
    stream = streams[0] if streams else {}
    if stream.get("width"):
        metadata["width"] = int(stream["width"])
    if stream.get("height"):
        metadata["height"] = int(stream["height"])
    if stream.get("codec_name"):
        metadata["codec"] = stream["codec_name"]

    fps = _parse_fps(stream.get("r_frame_rate", ""))
    if fps:
        metadata["fps"] = fps

    return metadata


def _parse_fps(value: str) -> float:
    if not value:
        return 0
    try:
        if "/" in value:
            numerator, denominator = value.split("/", 1)
            denominator_float = float(denominator)
            if denominator_float == 0:
                return 0
            return round(float(numerator) / denominator_float, 3)
        return round(float(value), 3)
    except (TypeError, ValueError):
        return 0


# ---------------------------------------------------------------------------
# JOBS DE VÍDEO
# ---------------------------------------------------------------------------

def fetch_pending_job() -> Optional[dict]:
    """Retorna o próximo projeto PENDING ou None."""
    try:
        r = requests.get(f"{HUB_BASE}/api/projects/pending", timeout=5)
        if r.status_code == 200:
            data = r.json()
            return data if data and data.get("id") else None
    except requests.RequestException as e:
        logger.warning(f"Hub offline ou inatingível: {e}")
    return None


def report_job_status(job_id: str, status: str, progress: int = 0, stage: str = "", message: str = "") -> bool:
    """Atualiza progresso/status de um job no Hub."""
    payload = {
        "id": job_id,
        "status": status,
        "progress": progress,
        "stage": stage,
        "message": message,
        "engine_id": ENGINE_ID,
        "timestamp": time.time(),
    }
    try:
        r = _post_signed(f"/api/projects/{job_id}/status", payload, timeout=10)
        if not r.ok:
            logger.warning(f"Hub rejeitou status {status} do job {job_id}: {r.status_code} {r.text[:200]}")
        return r.ok
    except requests.RequestException as e:
        logger.error(f"Falha ao reportar status do job {job_id}: {e}")
    return False


def report_job_done(job_id: str, video_path: str) -> bool:
    """Notifica o Hub que o job foi concluído."""
    payload = {
        "id": job_id,
        "video_path": video_path,
        "status": "completed",
        "engine_id": ENGINE_ID,
        "timestamp": time.time(),
    }
    video_url = _public_video_url(video_path)
    if video_url:
        payload["video_url"] = video_url
        payload["videoUrl"] = video_url
    payload.update(_video_metadata(video_path))
    try:
        r = _post_signed(f"/api/projects/{job_id}/complete", payload, timeout=10)
        if not r.ok:
            logger.warning(f"Hub rejeitou conclusão do job {job_id}: {r.status_code} {r.text[:200]}")
        return r.ok
    except requests.RequestException as e:
        logger.error(f"Falha ao reportar job {job_id}: {e}")
    return False


def report_job_error(job_id: str, error_msg: str) -> bool:
    """Notifica o Hub que o job falhou."""
    payload = {
        "id": job_id,
        "status": "error",
        "error": error_msg,
        "engine_id": ENGINE_ID,
        "timestamp": time.time(),
    }
    try:
        r = _post_signed(f"/api/projects/{job_id}/status", payload, timeout=10)
        if not r.ok:
            logger.warning(f"Hub rejeitou erro do job {job_id}: {r.status_code} {r.text[:200]}")
        return r.ok
    except requests.RequestException as e:
        logger.error(f"Falha ao reportar erro do job {job_id}: {e}")
    return False


# ---------------------------------------------------------------------------
# TELEMETRIA
# ---------------------------------------------------------------------------

def _get_local_telemetry() -> dict:
    """Coleta métricas locais da máquina onde o Engine roda."""
    telemetry = {
        "engine_id": ENGINE_ID,
        "platform": platform.system(),
        "timestamp": time.strftime("%H:%M:%S"),
    }
    try:
        from core.runtime.default_capabilities import build_default_registry

        capabilities = build_default_registry().list(include_experimental=True)
        telemetry["capabilities_count"] = len(capabilities)
        telemetry["capabilities"] = [
            {
                "id": capability["id"],
                "category": capability["category"],
                "experimental": capability["experimental"],
            }
            for capability in capabilities
        ]
    except Exception as e:
        logger.warning(f"Falha ao anexar capabilities na telemetria: {e}")
    # Disco
    try:
        usage = shutil.disk_usage(os.path.expanduser("~"))
        telemetry["storage_free_gb"] = f"{usage.free / 1e9:.1f}"
        telemetry["storage_total_gb"] = f"{usage.total / 1e9:.1f}"
    except Exception:
        pass
    # RAM
    try:
        with open("/proc/meminfo") as f:
            lines = f.readlines()
        total = int(lines[0].split()[1]) // 1024
        free  = int(lines[2].split()[1]) // 1024  # MemAvailable
        telemetry["ram_usage"] = f"{total - free}/{total}MB"
        telemetry["ram_free_mb"] = free
    except Exception:
        pass
    # Output dir size
    try:
        renders = os.path.join("output", "renders")
        if os.path.exists(renders):
            total_bytes = sum(
                os.path.getsize(os.path.join(renders, f))
                for f in os.listdir(renders)
                if os.path.isfile(os.path.join(renders, f))
            )
            telemetry["renders_size_mb"] = f"{total_bytes / 1e6:.1f}"
            telemetry["renders_count"] = len(os.listdir(renders))
    except Exception:
        pass
    telemetry["engine_active"] = True
    return telemetry


def push_telemetry() -> bool:
    """Envia métricas locais para o Hub (POST /api/sensors)."""
    data = _get_local_telemetry()
    try:
        r = _post_signed("/api/sensors", data, timeout=5)
        return r.ok
    except requests.RequestException:
        return False


# ---------------------------------------------------------------------------
# COMANDOS REMOTOS
# ---------------------------------------------------------------------------

def poll_commands() -> list:
    """
    Busca comandos remotos pendentes do Hub.
    Retorna lista de {command, args} ou [].
    """
    try:
        r = requests.get(f"{HUB_BASE}/api/actuators/mobile/poll", timeout=5)
        if r.ok:
            return r.json().get("commands", [])
    except requests.RequestException:
        pass
    return []


def execute_command(cmd_obj: dict):
    """Executa um comando vindo do Hub no contexto do Engine (desktop/Termux)."""
    cmd  = cmd_obj.get("command", "").lower()
    args = cmd_obj.get("args", [])
    logger.info(f"[HUB CMD] {cmd} {args}")

    if cmd == "generate_video":
        topic = args[0] if args else "interesting tech fact"
        # Import local para evitar circular
        from integration.worker import submit_video_job
        submit_video_job(topic)

    elif cmd == "run_module":
        module_name = args[0] if args else None
        if module_name:
            from core.modules import run_module
            run_module(module_name, args[1:])

    elif cmd == "speak":
        msg = " ".join(args)
        logger.info(f"[SPEAK] {msg}")
        try:
            import subprocess
            subprocess.run(["espeak", msg], capture_output=True, timeout=5)
        except Exception:
            pass

    elif cmd == "status":
        push_telemetry()

    else:
        logger.warning(f"[HUB CMD] Comando desconhecido: {cmd}")


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

def hub_is_alive() -> bool:
    try:
        r = requests.get(f"{HUB_BASE}/health", timeout=3)
        return r.ok
    except Exception:
        return False
