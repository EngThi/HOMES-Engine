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
import requests
from typing import Optional

logger = logging.getLogger(__name__)

HUB_BASE   = os.getenv("HOMES_HUB_URL", "http://localhost:8080").rstrip("/")
HUB_SECRET = os.getenv("HUB_SECRET", "homes_secret_dev")
ENGINE_ID  = os.getenv("ENGINE_ID", f"engine_{platform.node()}")


def _sign(payload: dict) -> str:
    """HMAC-SHA256 para autenticar POSTs no Hub."""
    body = json.dumps(payload, separators=(',', ':')).encode()
    return hmac.new(HUB_SECRET.encode(), body, hashlib.sha256).hexdigest()


def _signed_headers(payload: dict) -> dict:
    return {
        "Content-Type": "application/json",
        "X-Homes-Signature": _sign(payload),
    }


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


def report_job_done(job_id: str, video_path: str) -> bool:
    """Notifica o Hub que o job foi concluído."""
    payload = {
        "id": job_id,
        "video_path": video_path,
        "status": "completed",
        "engine_id": ENGINE_ID,
        "timestamp": time.time(),
    }
    try:
        r = requests.post(
            f"{HUB_BASE}/api/project/{job_id}/complete",
            json=payload,
            headers=_signed_headers(payload),
            timeout=10,
        )
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
        r = requests.post(
            f"{HUB_BASE}/api/project/{job_id}/complete",
            json=payload,
            headers=_signed_headers(payload),
            timeout=10,
        )
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
        r = requests.post(
            f"{HUB_BASE}/api/sensors",
            json=data,
            timeout=5,
        )
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
