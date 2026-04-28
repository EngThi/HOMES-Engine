import os
import time
import logging
import requests
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config — pode vir do .env ou ser sobrescrito em testes
# ---------------------------------------------------------------------------
VIDEOLM_BASE = os.getenv("VIDEOLM_URL", "http://localhost:3000").rstrip("/")
VIDEOLM_TOKEN = os.getenv("VIDEOLM_TOKEN", "")   # JWT — vazio = demo mode
POLL_INTERVAL = int(os.getenv("VIDEOLM_POLL_INTERVAL", "5"))   # segundos
POLL_TIMEOUT  = int(os.getenv("VIDEOLM_POLL_TIMEOUT",  "600"))  # 10 min max


def _headers() -> dict:
    """Monta headers com ou sem JWT."""
    h = {"Accept": "application/json"}
    if VIDEOLM_TOKEN:
        h["Authorization"] = f"Bearer {VIDEOLM_TOKEN}"
    return h


def _assemble_endpoint() -> str:
    """Escolhe endpoint autenticado ou demo automaticamente."""
    if VIDEOLM_TOKEN:
        return f"{VIDEOLM_BASE}/api/video/assemble"
    return f"{VIDEOLM_BASE}/api/video/demo/assemble"


def _status_endpoint(project_id: str) -> str:
    return f"{VIDEOLM_BASE}/api/video/{project_id}/status"


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
        1. POST multipart/form-data → /api/video/demo/assemble (ou /assemble com JWT)
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

        resp = requests.post(
            endpoint,
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

    while elapsed < POLL_TIMEOUT:
        time.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL

        try:
            s_resp = requests.get(status_url, headers=headers, timeout=15)
            if not s_resp.ok:
                logger.warning(f"⚠️  Status endpoint retornou {s_resp.status_code}")
                continue

            s       = s_resp.json()
            status  = s.get("status", "UNKNOWN")
            
            if status != last_status:
                logger.info(f"[{elapsed}s] VideoLM status: {status}")
                last_status = status

            if status in ("completed", "done"):
                # Resolve URL de download
                video_path  = s.get("videoPath") or video_url
                download_url = (
                    video_path if video_path.startswith("http")
                    else f"{VIDEOLM_BASE}{video_path}"
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

    logger.error(f"⏰ Timeout ({POLL_TIMEOUT}s) aguardando VideoLM para {project_id}")
    return None


# ---------------------------------------------------------------------------
# Teste rápido de conectividade — rode: python -m core.videolm_client
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import json
    print(f"[HOMES-Engine] VideoLM Client — conectando em {VIDEOLM_BASE}")
    try:
        r = requests.get(f"{VIDEOLM_BASE}/api/video/music", timeout=5)
        print(f"✅ VideoLM respondeu! Músicas disponíveis: {json.dumps(r.json(), indent=2)}")
    except Exception as e:
        print(f"❌ Não foi possível conectar: {e}")
        print("   Certifique-se que o VideoLM está rodando (docker-compose up)")
