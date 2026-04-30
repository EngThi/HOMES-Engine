import os
import time
import logging
import requests
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config - pode vir do .env ou ser sobrescrito em testes
# ---------------------------------------------------------------------------
VIDEOLM_BASE = os.getenv("VIDEOLM_URL", "https://54-162-84-165.sslip.io").rstrip("/")
VIDEOLM_TOKEN = os.getenv("VIDEOLM_TOKEN", "")   # JWT opcional
VIDEOLM_ASSEMBLE_PATH = os.getenv("VIDEOLM_ASSEMBLE_PATH", "")
POLL_INTERVAL = int(os.getenv("VIDEOLM_POLL_INTERVAL", "5"))   # segundos
POLL_TIMEOUT  = int(os.getenv("VIDEOLM_POLL_TIMEOUT",  "600"))  # 10 min max


def _base_url() -> str:
    return os.getenv("VIDEOLM_URL", VIDEOLM_BASE).rstrip("/")


def _token() -> str:
    return os.getenv("VIDEOLM_TOKEN", VIDEOLM_TOKEN)


def _poll_interval() -> int:
    return int(os.getenv("VIDEOLM_POLL_INTERVAL", str(POLL_INTERVAL)))


def _poll_timeout() -> int:
    return int(os.getenv("VIDEOLM_POLL_TIMEOUT", str(POLL_TIMEOUT)))


def _assemble_path() -> str:
    path = os.getenv("VIDEOLM_ASSEMBLE_PATH", VIDEOLM_ASSEMBLE_PATH).strip()
    if not path:
        path = "/api/video/assemble" if _token() else "/api/video/demo/assemble"
    return path if path.startswith("/") else f"/{path}"


def _headers() -> dict:
    """Monta headers com ou sem JWT, incluindo bypass para Localtunnel."""
    h = {
        "Accept": "application/json",
        "Bypass-Tunnel-Reminder": "true"  # Essencial para Localtunnel/Ngrok
    }
    token = _token()
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def _assemble_endpoint() -> str:
    """Endpoint do contrato atual Engine -> VideoLM."""
    return f"{_base_url()}{_assemble_path()}"


def _alternate_assemble_endpoint() -> str:
    path = _assemble_path()
    if path == "/api/video/assemble":
        return f"{_base_url()}/api/video/demo/assemble"
    if path == "/api/video/demo/assemble":
        return f"{_base_url()}/api/video/assemble"
    return ""


def _status_endpoint(project_id: str) -> str:
    return f"{_base_url()}/api/video/{project_id}/status"


def engine_demo_url() -> str:
    return f"{_base_url()}/engine-demo"


def fetch_engine_health(timeout: int = 10) -> dict:
    resp = requests.get(f"{_base_url()}/api/engine/health", headers=_headers(), timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def fetch_engine_manifest(timeout: int = 15) -> dict:
    resp = requests.get(f"{_base_url()}/api/engine/manifest", headers=_headers(), timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def assemble_via_videolm(
    audio_path: str,
    image_paths: list,
    script: str,
    project_id: str,
    bg_music_id: str = "",
    output_dir: str = "output/renders",
) -> Optional[str]:
    """
    Envia os assets gerados pelo Engine para o backend do VideoLM renderizar.

    Fluxo:
        1. POST multipart/form-data -> /api/video/assemble
        2. Polling em GET /api/video/:projectId/status até status=completed
        3. Baixa o .mp4 final e salva em output_dir
        4. Retorna o caminho local do arquivo, ou None em caso de falha

    Parâmetros:
        audio_path   : caminho para narration.wav gerado pelo GeminiTTS
        image_paths  : lista de caminhos das imagens de cena (JPG/PNG)
        script       : texto completo da narração (usado para legendas no VideoLM)
        project_id   : ID único do projeto (ex: "topic_142305")
        bg_music_id  : nome do arquivo de música em data/music/ (opcional)
        output_dir   : pasta local onde o .mp4 final será salvo
    """
    endpoint = _assemble_endpoint()
    headers  = _headers()

    if not os.path.exists(audio_path):
        logger.error(f"❌ Áudio não encontrado: {audio_path}")
        return None

    if not image_paths:
        logger.error("❌ Nenhuma imagem fornecida para montagem")
        return None

    # --- Monta o multipart ---
    files = []
    audio_handle = None
    image_handles = []
    try:
        audio_handle = open(audio_path, "rb")
        files.append(("audio", (Path(audio_path).name, audio_handle, "audio/wav")))

        for img in image_paths:
            if not os.path.exists(img):
                logger.warning(f"⚠️  Imagem ausente, pulando: {img}")
                continue
            fh = open(img, "rb")
            image_handles.append(fh)
            files.append(("images", (Path(img).name, fh, "image/jpeg")))

        if not image_handles:
            logger.error("❌ Nenhuma imagem válida encontrada")
            return None

        data = {
            "script":     script or "",
            "bgMusicId":  bg_music_id,
            "projectId":  project_id,
            "duration":   "0",  # VideoLM calcula pelo áudio
        }

        logger.info(
            f"📤 Enviando para VideoLM [{endpoint}]\n"
            f"   projeto={project_id} | imagens={len(image_handles)} | áudio={Path(audio_path).name}"
        )

        resp = requests.post(endpoint, files=files, data=data, headers=headers, timeout=120)
        fallback_endpoint = _alternate_assemble_endpoint()
        if fallback_endpoint and resp.status_code in (401, 404, 405):
            logger.warning(
                f"⚠️  VideoLM retornou HTTP {resp.status_code} em {endpoint}. "
                f"Tentando fallback {fallback_endpoint}"
            )
            for _, file_tuple in files:
                file_tuple[1].seek(0)
            resp = requests.post(
                fallback_endpoint,
                files=files,
                data=data,
                headers=headers,
                timeout=120,
            )

    finally:
        if audio_handle:
            audio_handle.close()
        for fh in image_handles:
            fh.close()

    if not resp.ok:
        logger.error(
            f"❌ VideoLM rejeitou o job: HTTP {resp.status_code}\n"
            f"   Body: {resp.text[:400]}"
        )
        return None

    result    = resp.json()
    video_url = result.get("videoUrl", "")
    logger.info(f"✅ Job aceito. URL futura: {video_url}")

    # --- Polling ---
    status_url    = _status_endpoint(project_id)
    elapsed       = 0
    last_status   = ""
    last_progress = None
    last_stage    = ""

    poll_interval = _poll_interval()
    poll_timeout = _poll_timeout()

    while elapsed < poll_timeout:
        time.sleep(poll_interval)
        elapsed += poll_interval

        try:
            s_resp = requests.get(status_url, headers=headers, timeout=15)
            if not s_resp.ok:
                logger.warning(f"⚠️  Status endpoint retornou {s_resp.status_code}")
                continue

            s       = s_resp.json()
            status = s.get("status", "UNKNOWN")
            progress = s.get("progress")
            stage = s.get("stage") or (s.get("render") or {}).get("stage") or ""
            
            if status != last_status or progress != last_progress or stage != last_stage:
                progress_label = f" | progress={progress}%" if progress is not None else ""
                stage_label = f" | stage={stage}" if stage else ""
                logger.info(f"[{elapsed}s] VideoLM status: {status}{progress_label}{stage_label}")
                last_status = status
                last_progress = progress
                last_stage = stage

            if status in ("completed", "done"):
                # Resolve URL de download
                video_path = (
                    s.get("videoPath")
                    or s.get("videoUrl")
                    or s.get("url")
                    or video_url
                )
                if not video_path:
                    logger.error(f"❌ Status completo sem URL de vídeo: {s}")
                    return None
                download_url = (
                    video_path if video_path.startswith("http")
                    else f"{_base_url()}{video_path}"
                )

                os.makedirs(output_dir, exist_ok=True)
                out_file = os.path.join(output_dir, f"HOMES_{project_id}.mp4")

                logger.info(f"⬇️  Baixando vídeo: {download_url}")
                dl = requests.get(download_url, headers=headers, stream=True, timeout=180)
                dl.raise_for_status()

                with open(out_file, "wb") as f:
                    for chunk in dl.iter_content(chunk_size=8192):
                        f.write(chunk)

                size_mb = os.path.getsize(out_file) / 1_048_576
                logger.info(f"🎬 Vídeo salvo: {out_file} ({size_mb:.1f} MB)")
                return out_file

            elif status in ("error", "failed", "FAILED"):
                logger.error(
                    f"❌ VideoLM reportou falha no job {project_id}\n"
                    f"   Detalhe: {s.get('error', 'sem detalhe')}"
                )
                return None

        except requests.RequestException as e:
            logger.warning(f"⚠️  Erro de conexão no polling [{elapsed}s]: {e}")

    logger.error(f"⏰ Timeout ({poll_timeout}s) aguardando VideoLM para {project_id}")
    return None


# ---------------------------------------------------------------------------
# Teste rápido de conectividade — rode: python -m core.videolm_client
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import json
    print(f"[HOMES-Engine] VideoLM Client — conectando em {_base_url()}")
    try:
        r = requests.get(f"{_base_url()}/api/video/music", headers=_headers(), timeout=5)
        r.raise_for_status()
        print(f"✅ VideoLM respondeu! Músicas disponíveis: {json.dumps(r.json(), indent=2)}")
    except Exception as e:
        print(f"❌ Não foi possível conectar: {e}")
        print("   Certifique-se que o VideoLM está rodando (docker-compose up)")
