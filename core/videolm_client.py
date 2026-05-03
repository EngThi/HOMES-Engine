import os
import time
import logging
import json
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


def submit_notebooklm_video(
    project_id: str = "",
    title: str = "",
    theme: str = "",
    urls: Optional[list] = None,
    asset_paths: Optional[list] = None,
    style: str = "classic",
    format: str = "brief",
    style_prompt: str = "",
    live_research: bool = False,
    notebook_id: str = "",
    profile_id: str = "default",
    timeout: int = 120,
) -> dict:
    """Submete um job NotebookLM video para o VideoLM hosted bridge."""
    endpoint = f"{_base_url()}/api/engine/notebooklm/video"
    data = [
        ("style", style),
        ("format", format or "brief"),
        ("liveResearch", str(live_research).lower()),
        ("profileId", profile_id or "default"),
    ]
    if project_id:
        data.append(("projectId", project_id))
    if title:
        data.append(("title", title))
    if theme:
        data.append(("theme", theme))
    if style_prompt:
        data.append(("stylePrompt", style_prompt))
    if notebook_id:
        data.append(("notebookId", notebook_id))
    for url in urls or []:
        if url:
            data.append(("urls", url))

    files = []
    handles = []
    try:
        for path in asset_paths or []:
            if not path:
                continue
            if not os.path.exists(path):
                raise FileNotFoundError(f"NotebookLM asset not found: {path}")
            fh = open(path, "rb")
            handles.append(fh)
            files.append(("assets", (Path(path).name, fh, "application/octet-stream")))

        resp = requests.post(
            endpoint,
            data=data,
            files=files or None,
            headers=_headers(),
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json()
    finally:
        for fh in handles:
            fh.close()


def poll_notebooklm_video(project_id: str, timeout: int = 30) -> dict:
    """Consulta o endpoint de download/cache de um job NotebookLM video."""
    if not project_id:
        raise ValueError("project_id is required")
    resp = requests.get(
        f"{_base_url()}/api/research/{project_id}/download",
        headers=_headers(),
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()


def submit_studio_artifact(
    project_id: str,
    artifact_type: str = "video",
    title: str = "",
    theme: str = "",
    urls: Optional[list] = None,
    asset_paths: Optional[list] = None,
    style: str = "paper_craft",
    format: str = "brief",
    aspect: str = "",
    focus_prompt: str = "",
    infographic_orientation: str = "",
    infographic_detail: str = "",
    style_prompt: str = "",
    live_research: bool = False,
    notebook_id: str = "",
    profile_id: str = "default",
    timeout: int = 120,
) -> dict:
    """Submit a generic NotebookLM Studio artifact job through the VideoLM contract."""
    if not project_id:
        raise ValueError("project_id is required")
    artifact_type = normalize_artifact_type(artifact_type or "video")
    endpoint = f"{_base_url()}/api/engine/notebooklm/artifact"
    body = {
        "projectId": project_id,
        "type": artifact_type,
        "artifactType": artifact_type,
        "title": title,
        "theme": theme,
        "urls": urls or [],
        "style": style,
        "format": format or "brief",
        "aspect": aspect,
        "orientation": infographic_orientation or aspect,
        "focusPrompt": focus_prompt,
        "infographicOrientation": infographic_orientation or aspect,
        "infographicDetail": infographic_detail,
        "stylePrompt": style_prompt,
        "liveResearch": live_research,
        "notebookId": notebook_id,
        "profileId": profile_id or "default",
    }
    body = {key: value for key, value in body.items() if value not in ("", None, [], {})}
    files, handles = _open_asset_files(asset_paths or [], field_name="assets")
    try:
        resp = requests.post(
            endpoint,
            data=body,
            files=files or None,
            headers=_headers(),
            timeout=timeout,
        )
        if resp.status_code in (404, 405):
            return _submit_studio_artifact_legacy(
                project_id=project_id,
                artifact_type=artifact_type,
                title=title,
                theme=theme,
                urls=urls or [],
                asset_paths=asset_paths or [],
                style=style,
                format=format,
                aspect=aspect,
                focus_prompt=focus_prompt,
                infographic_orientation=infographic_orientation,
                infographic_detail=infographic_detail,
                style_prompt=style_prompt,
                live_research=live_research,
                notebook_id=notebook_id,
                profile_id=profile_id,
                timeout=timeout,
            )
        resp.raise_for_status()
        return normalize_artifact_result(resp.json(), project_id=project_id, artifact_type=artifact_type)
    finally:
        for fh in handles:
            fh.close()


def poll_studio_artifact(project_id: str, artifact_type: str = "", timeout: int = 30) -> dict:
    if not project_id:
        raise ValueError("project_id is required")
    result = poll_notebooklm_video(project_id, timeout=timeout)
    return normalize_artifact_result(result, project_id=project_id, artifact_type=artifact_type or result.get("artifactType") or result.get("type", "artifact"))


def submit_factory_infographic_assets(
    project_id: str,
    theme: str = "",
    urls: Optional[list] = None,
    style: str = "paper_craft",
    aspect: str = "portrait",
    orientation: str = "",
    notebook_id: str = "",
    profile_id: str = "default",
    timeout: int = 120,
) -> dict:
    if not project_id:
        raise ValueError("project_id is required")
    body = {
        "theme": theme,
        "urls": urls or [],
        "style": style,
        "aspect": aspect,
        "orientation": orientation or aspect,
        "notebookId": notebook_id,
        "profileId": profile_id or "default",
    }
    body = {key: value for key, value in body.items() if value not in ("", None, [], {})}
    resp = requests.post(
        f"{_base_url()}/api/research/{project_id}/factory-infographic-assets",
        json=body,
        headers=_headers(),
        timeout=timeout,
    )
    resp.raise_for_status()
    return normalize_artifact_result(resp.json(), project_id=project_id, artifact_type="factory-infographic-assets")


def poll_factory_infographic_assets(job_id: str, timeout: int = 30) -> dict:
    if not job_id:
        raise ValueError("job_id is required")
    resp = requests.get(
        f"{_base_url()}/api/research/factory-infographic-assets/{job_id}",
        headers=_headers(),
        timeout=timeout,
    )
    resp.raise_for_status()
    return normalize_artifact_result(resp.json(), artifact_type="factory-infographic-assets")


def normalize_artifact_result(result: dict, project_id: str = "", artifact_type: str = "artifact") -> dict:
    normalized = dict(result or {})
    normalized.setdefault("project_id", project_id or normalized.get("projectId", ""))
    normalized.setdefault("artifact_type", normalize_artifact_type(artifact_type or normalized.get("artifactType") or normalized.get("type", "artifact")))
    artifact_url = _extract_artifact_url(normalized)
    if artifact_url:
        normalized["artifact_url"] = resolve_artifact_url(artifact_url)
        if normalized["artifact_type"] == "video":
            normalized["video_url"] = normalized["artifact_url"]
            normalized["videoUrl"] = normalized["artifact_url"]
    content_type = _guess_content_type(normalized["artifact_url"]) if artifact_url else ""
    if content_type:
        normalized.setdefault("content_type", content_type)
    return normalized


def resolve_artifact_url(path: str) -> str:
    if not path:
        return ""
    return path if path.startswith(("http://", "https://")) else f"{_base_url()}{path}"


def resolve_video_url(video_path: str) -> str:
    if not video_path:
        return ""
    return resolve_artifact_url(video_path)


def normalize_artifact_type(artifact_type: str) -> str:
    value = (artifact_type or "artifact").strip().lower().replace("_", "-")
    aliases = {
        "table": "data-table",
        "datatable": "data-table",
        "data-table": "data-table",
        "data-table-pdf": "data-table",
        "mind-map": "mindmap",
        "mind_map": "mindmap",
        "slide": "slides",
        "slide-deck": "slides",
        "deck": "slides",
        "audio-overview": "audio",
        "video-overview": "video",
        "image": "infographic",
        "png": "infographic",
    }
    return aliases.get(value, value)


def _submit_studio_artifact_legacy(
    project_id: str,
    artifact_type: str,
    title: str = "",
    theme: str = "",
    urls: Optional[list] = None,
    asset_paths: Optional[list] = None,
    style: str = "paper_craft",
    format: str = "brief",
    aspect: str = "",
    focus_prompt: str = "",
    infographic_orientation: str = "",
    infographic_detail: str = "",
    style_prompt: str = "",
    live_research: bool = False,
    notebook_id: str = "",
    profile_id: str = "default",
    timeout: int = 120,
) -> dict:
    if artifact_type == "video":
        result = submit_notebooklm_video(
            project_id=project_id,
            title=title,
            theme=theme,
            urls=urls or [],
            asset_paths=asset_paths or [],
            style=style,
            format=format,
            style_prompt=style_prompt,
            live_research=live_research,
            notebook_id=notebook_id,
            profile_id=profile_id,
            timeout=timeout,
        )
        return normalize_artifact_result(result, project_id=project_id, artifact_type=artifact_type)

    _add_research_sources(project_id, urls or [], timeout=timeout)
    _add_research_files(project_id, asset_paths or [], notebook_id=notebook_id, profile_id=profile_id, timeout=timeout)
    body = {
        "type": artifact_type,
        "artifactType": artifact_type,
        "style": style,
        "format": format or "brief",
        "aspect": aspect,
        "orientation": infographic_orientation or aspect,
        "focusPrompt": focus_prompt,
        "infographicOrientation": infographic_orientation or aspect,
        "infographicDetail": infographic_detail,
        "stylePrompt": style_prompt,
        "liveResearch": live_research,
        "notebookId": notebook_id,
        "profileId": profile_id or "default",
        "theme": theme,
        "title": title,
    }
    body = {key: value for key, value in body.items() if value not in ("", None, [], {})}
    resp = requests.post(
        f"{_base_url()}/api/research/{project_id}/trigger",
        json=body,
        headers=_headers(),
        timeout=timeout,
    )
    resp.raise_for_status()
    return normalize_artifact_result(resp.json(), project_id=project_id, artifact_type=artifact_type)


def _open_asset_files(asset_paths: list, field_name: str = "files") -> tuple[list, list]:
    files = []
    handles = []
    for path in asset_paths or []:
        if not path:
            continue
        if not os.path.exists(path):
            for fh in handles:
                fh.close()
            raise FileNotFoundError(f"Studio artifact asset not found: {path}")
        fh = open(path, "rb")
        handles.append(fh)
        files.append((field_name, (Path(path).name, fh, "application/octet-stream")))
    return files, handles


def _add_research_sources(project_id: str, urls: list, timeout: int = 120) -> None:
    clean_urls = [url for url in urls or [] if url]
    if not clean_urls:
        return
    resp = requests.post(
        f"{_base_url()}/api/research/{project_id}/sources",
        json={"urls": clean_urls},
        headers=_headers(),
        timeout=timeout,
    )
    resp.raise_for_status()


def _add_research_files(
    project_id: str,
    asset_paths: list,
    notebook_id: str = "",
    profile_id: str = "default",
    timeout: int = 120,
) -> None:
    if not asset_paths:
        return
    files = []
    handles = []
    try:
        files, handles = _open_asset_files(asset_paths, field_name="files")
        if not files:
            return
        data = {"profileId": profile_id or "default"}
        if notebook_id:
            data["notebookId"] = notebook_id
        resp = requests.post(
            f"{_base_url()}/api/research/{project_id}/source-files",
            data=data,
            files=files,
            headers=_headers(),
            timeout=timeout,
        )
        resp.raise_for_status()
    finally:
        for fh in handles:
            fh.close()


def _extract_artifact_url(result: dict) -> str:
    for key in (
        "artifact_url",
        "artifactUrl",
        "video_url",
        "videoUrl",
        "videoPath",
        "audioUrl",
        "imageUrl",
        "pdfUrl",
        "jsonUrl",
        "htmlUrl",
        "downloadUrl",
        "url",
    ):
        value = result.get(key)
        if isinstance(value, str) and value:
            return value
    artifacts = result.get("artifacts")
    if isinstance(artifacts, list):
        for artifact in artifacts:
            if isinstance(artifact, dict):
                value = _extract_artifact_url(artifact)
                if value:
                    return value
    return ""


def _guess_content_type(url: str) -> str:
    lower = url.lower().split("?", 1)[0]
    if lower.endswith(".mp4"):
        return "video/mp4"
    if lower.endswith(".mp3"):
        return "audio/mpeg"
    if lower.endswith(".wav"):
        return "audio/wav"
    if lower.endswith(".png"):
        return "image/png"
    if lower.endswith((".jpg", ".jpeg")):
        return "image/jpeg"
    if lower.endswith(".pdf"):
        return "application/pdf"
    if lower.endswith(".json"):
        return "application/json"
    if lower.endswith(".html"):
        return "text/html"
    return ""


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

                with open(f"{out_file}.source.json", "w", encoding="utf-8") as f:
                    json.dump(
                        {
                            "project_id": project_id,
                            "video_url": download_url,
                            "video_path": video_path,
                        },
                        f,
                        indent=2,
                    )

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
