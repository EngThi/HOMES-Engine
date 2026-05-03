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
from typing import Any, Optional
from dotenv import load_dotenv

# Carregar variáveis de ambiente do .env
load_dotenv()

logger = logging.getLogger(__name__)

HUB_BASE   = os.getenv("HOMES_HUB_URL", "http://localhost:8080").rstrip("/")
HUB_SECRET = os.getenv("HUB_SECRET", "homes_secret_dev")
ENGINE_ID  = os.getenv("ENGINE_ID", f"engine_{platform.node()}")
COMMAND_RESULTS = []
MAX_COMMAND_RESULTS = 20


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


_VIDEOLM_ARTIFACT_TYPES_CACHE: Any = None


def _public_artifact_url(artifact_path: str) -> str:
    """Best-effort public URL for Hub artifact downloads."""
    if not artifact_path:
        return ""
    if artifact_path.startswith(("http://", "https://")):
        return artifact_path
    if artifact_path.startswith(("/videos/", "/artifacts/", "/images/", "/files/")):
        base_url = os.getenv("VIDEOLM_URL", "").rstrip("/")
        return f"{base_url}{artifact_path}" if base_url else ""

    sidecar_path = f"{artifact_path}.source.json"
    if os.path.exists(sidecar_path):
        try:
            with open(sidecar_path, "r", encoding="utf-8") as f:
                source = json.load(f)
            source_url = (
                source.get("artifact_url")
                or source.get("artifactUrl")
                or source.get("video_url")
                or source.get("videoUrl")
                or source.get("image_url")
                or source.get("imageUrl")
                or source.get("url")
            )
            if source_url:
                return source_url
        except (OSError, json.JSONDecodeError) as e:
            logger.warning(f"Não foi possível ler URL pública do artifact {artifact_path}: {e}")

    public_base = os.getenv("HOMES_ENGINE_PUBLIC_BASE_URL", "").rstrip("/")
    public_prefix = os.getenv("HOMES_ENGINE_PUBLIC_ARTIFACT_PATH", "").strip("/")
    if not public_prefix:
        public_prefix = os.getenv("HOMES_ENGINE_PUBLIC_VIDEO_PATH", "/videos").strip("/")
    if public_base and os.path.exists(artifact_path):
        return f"{public_base}/{public_prefix}/{os.path.basename(artifact_path)}"

    return ""


def _public_video_url(video_path: str) -> str:
    """Backward-compatible wrapper for old video-only callers."""
    return _public_artifact_url(video_path)


def _guess_content_type(path_or_url: str) -> str:
    value = (path_or_url or "").split("?", 1)[0].lower()
    if value.endswith(".mp4"):
        return "video/mp4"
    if value.endswith(".webm"):
        return "video/webm"
    if value.endswith(".mov"):
        return "video/quicktime"
    if value.endswith(".png"):
        return "image/png"
    if value.endswith((".jpg", ".jpeg")):
        return "image/jpeg"
    if value.endswith(".pdf"):
        return "application/pdf"
    if value.endswith(".json"):
        return "application/json"
    if value.endswith(".html"):
        return "text/html"
    if value.endswith(".mp3"):
        return "audio/mpeg"
    if value.endswith(".wav"):
        return "audio/wav"
    return ""


def _is_video_artifact(path_or_url: str, content_type: str = "") -> bool:
    content_type = (content_type or "").lower()
    return content_type.startswith("video/") or (path_or_url or "").split("?", 1)[0].lower().endswith(
        (".mp4", ".webm", ".mov")
    )


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
    return report_artifact_done(job_id, artifact_path=video_path, artifact_type="video")


def report_artifact_done(
    job_id: str,
    artifact_path: str = "",
    artifact_url: str = "",
    artifact_type: str = "artifact",
    content_type: str = "",
    metadata: Optional[dict] = None,
) -> bool:
    """Notifica o Hub que um job de artifact generico foi concluído."""
    public_url = artifact_url or _public_artifact_url(artifact_path)
    resolved_content_type = content_type or _guess_content_type(public_url or artifact_path)
    payload = {
        "id": job_id,
        "status": "completed",
        "engine_id": ENGINE_ID,
        "timestamp": time.time(),
    }
    if artifact_path:
        payload["artifact_path"] = artifact_path
    if artifact_type:
        payload["artifact_type"] = artifact_type
        payload["artifactType"] = artifact_type
    if public_url:
        payload["artifact_url"] = public_url
        payload["artifactUrl"] = public_url
    if resolved_content_type:
        payload["content_type"] = resolved_content_type
        payload["contentType"] = resolved_content_type
    if _is_video_artifact(public_url or artifact_path, resolved_content_type):
        if artifact_path:
            payload["video_path"] = artifact_path
        if public_url:
            payload["video_url"] = public_url
            payload["videoUrl"] = public_url
        payload.update(_video_metadata(artifact_path))
    if metadata:
        payload.update(metadata)
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
        from core.runtime import build_runtime_manifest, list_recipes, load_profile
        from core.runtime.default_capabilities import build_default_registry

        registry = build_default_registry()
        profile = load_profile("default")
        runtime_manifest = build_runtime_manifest(registry, profile, include_experimental=False)
        capabilities = runtime_manifest["capabilities"]
        telemetry["capabilities_count"] = len(capabilities)
        telemetry["capabilities"] = [
            {
                "id": capability["id"],
                "category": capability["category"],
                "experimental": capability["experimental"],
            }
            for capability in capabilities
        ]
        telemetry["runtime_manifest"] = runtime_manifest
        telemetry["recipes"] = list_recipes()
    except Exception as e:
        logger.warning(f"Falha ao anexar capabilities na telemetria: {e}")
    artifact_types = _videolm_artifact_types_for_telemetry()
    if artifact_types:
        telemetry["artifactTypes"] = artifact_types
        telemetry["artifact_types"] = artifact_types
    try:
        from core.runtime import StateStore

        telemetry["recent_runtime_events"] = StateStore().recent_events(limit=10)
    except Exception as e:
        logger.warning(f"Falha ao anexar eventos runtime na telemetria: {e}")
    if COMMAND_RESULTS:
        telemetry["recent_command_results"] = COMMAND_RESULTS[-MAX_COMMAND_RESULTS:]
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


def _videolm_artifact_types_for_telemetry() -> Any:
    """Attach VideoLM artifactTypes when the VM has a VideoLM URL configured."""
    global _VIDEOLM_ARTIFACT_TYPES_CACHE
    if _VIDEOLM_ARTIFACT_TYPES_CACHE is not None:
        return _VIDEOLM_ARTIFACT_TYPES_CACHE
    if os.getenv("HOMES_ENGINE_FETCH_VIDEOLM_MANIFEST", "1") == "0":
        _VIDEOLM_ARTIFACT_TYPES_CACHE = {}
        return _VIDEOLM_ARTIFACT_TYPES_CACHE
    if not os.getenv("VIDEOLM_URL"):
        _VIDEOLM_ARTIFACT_TYPES_CACHE = {}
        return _VIDEOLM_ARTIFACT_TYPES_CACHE

    try:
        from core.videolm_client import fetch_engine_manifest

        manifest = fetch_engine_manifest(timeout=2)
        artifact_types = manifest.get("artifactTypes") or manifest.get("artifact_types") or {}
        _VIDEOLM_ARTIFACT_TYPES_CACHE = artifact_types
        return artifact_types
    except Exception as e:
        logger.warning(f"Falha ao anexar artifactTypes do VideoLM na telemetria: {e}")
        _VIDEOLM_ARTIFACT_TYPES_CACHE = {}
        return _VIDEOLM_ARTIFACT_TYPES_CACHE


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
        script_path = submit_video_job(topic)
        return _remember_command_result(cmd, {"status": "queued", "script_path": script_path})

    elif cmd == "run_module":
        module_name = args[0] if args else None
        if module_name:
            from core.modules import run_module
            result = run_module(module_name, args[1:])
            return _remember_command_result(cmd, {"status": "completed", "module": module_name, "output": result})
        return _remember_command_result(cmd, {"status": "error", "error": "module name is required"})

    elif cmd == "run_capability":
        return execute_capability_command(cmd_obj)

    elif cmd == "run_recipe":
        return execute_recipe_command(cmd_obj)

    elif cmd == "speak":
        msg = " ".join(args)
        logger.info(f"[SPEAK] {msg}")
        try:
            import subprocess
            subprocess.run(["espeak", msg], capture_output=True, timeout=5)
        except Exception:
            pass
        return _remember_command_result(cmd, {"status": "completed", "message": msg})

    elif cmd == "status":
        push_telemetry()
        return _remember_command_result(cmd, {"status": "completed"})

    else:
        logger.warning(f"[HUB CMD] Comando desconhecido: {cmd}")
        return _remember_command_result(cmd, {"status": "error", "error": f"unknown command: {cmd}"})


def execute_capability_command(cmd_obj: dict) -> dict:
    """Run a runtime capability from a Hub command object."""
    payload = _capability_payload(cmd_obj)
    capability_id = payload.get("capability_id") or payload.get("capabilityId") or payload.get("id")
    if not capability_id:
        result = {"status": "error", "error": "capability_id is required"}
        logger.warning(f"[HUB CAPABILITY] {result['error']}")
        return _remember_command_result("run_capability", result)

    capability_args = payload.get("args") or payload.get("capability_args") or {}
    profile_name = payload.get("profile") or payload.get("profile_id") or "default"

    try:
        from core.runtime import CapabilityContext, StateStore, load_profile
        from core.runtime.default_capabilities import run_capability

        context = CapabilityContext(
            profile=load_profile(profile_name),
            state=StateStore(),
            event={"source": "hub_command", "command": cmd_obj},
            engine_id=ENGINE_ID,
        )
        output = run_capability(capability_id, args=capability_args, context=context)
        result = {"status": "completed", "capability_id": capability_id, "output": output}
        logger.info(f"[HUB CAPABILITY] {capability_id} completed")
        return _remember_command_result("run_capability", result)
    except Exception as e:
        result = {"status": "error", "capability_id": capability_id, "error": str(e)}
        logger.error(f"[HUB CAPABILITY] {capability_id} failed: {e}")
        return _remember_command_result("run_capability", result)


def execute_recipe_command(cmd_obj: dict) -> dict:
    """Run a declarative runtime recipe from a Hub command object."""
    payload = _recipe_payload(cmd_obj)
    recipe_id = payload.get("recipe_id") or payload.get("recipeId") or payload.get("id")
    if not recipe_id:
        result = {"status": "error", "error": "recipe_id is required"}
        logger.warning(f"[HUB RECIPE] {result['error']}")
        return _remember_command_result("run_recipe", result)

    inputs = payload.get("inputs") or {}
    profile_name = payload.get("profile") or payload.get("profile_id") or "default"

    try:
        from core.runtime import CapabilityContext, StateStore, load_profile, run_recipe

        context = CapabilityContext(
            profile=load_profile(profile_name),
            state=StateStore(),
            event={"source": "hub_command", "command": cmd_obj},
            engine_id=ENGINE_ID,
        )
        output = run_recipe(recipe_id, inputs=inputs, context=context)
        result = {"status": "completed", "recipe_id": recipe_id, "output": output}
        logger.info(f"[HUB RECIPE] {recipe_id} completed")
        return _remember_command_result("run_recipe", result)
    except Exception as e:
        result = {"status": "error", "recipe_id": recipe_id, "error": str(e)}
        logger.error(f"[HUB RECIPE] {recipe_id} failed: {e}")
        return _remember_command_result("run_recipe", result)


def _capability_payload(cmd_obj: dict) -> dict:
    args = cmd_obj.get("args") or []
    if isinstance(args, dict):
        return args
    if not args:
        return {}
    if len(args) == 1 and isinstance(args[0], dict):
        return args[0]
    payload = {"capability_id": args[0]}
    if len(args) > 1 and isinstance(args[1], dict):
        payload["args"] = args[1]
    elif len(args) > 1:
        payload["args"] = {"value": args[1:]}
    return payload


def _recipe_payload(cmd_obj: dict) -> dict:
    args = cmd_obj.get("args") or []
    if isinstance(args, dict):
        return args
    if not args:
        return {}
    if len(args) == 1 and isinstance(args[0], dict):
        return args[0]
    payload = {"recipe_id": args[0]}
    if len(args) > 1 and isinstance(args[1], dict):
        payload["inputs"] = args[1]
    elif len(args) > 1:
        payload["inputs"] = {"value": args[1:]}
    return payload


def _remember_command_result(command: str, result: dict) -> dict:
    record = {
        "command": command,
        "result": result,
        "timestamp": time.time(),
        "engine_id": ENGINE_ID,
    }
    COMMAND_RESULTS.append(record)
    del COMMAND_RESULTS[:-MAX_COMMAND_RESULTS]
    return result


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

def hub_is_alive() -> bool:
    try:
        r = requests.get(f"{HUB_BASE}/health", timeout=3)
        return r.ok
    except Exception:
        return False
