"""
worker.py — HOMES-Engine main worker loop

Responsabilidades:
  1. Poll HOMES Hub por jobs de vídeo pendentes
  2. Processar com video_maker → VideoLM
  3. Reportar status de volta ao Hub
  4. Poll de comandos remotos (generate_video, run_module, speak…)
  5. Push de telemetria a cada ciclo

Uso:
  python -m integration.worker          # loop infinito
  python integration/worker.py          # idem
"""
import os
import sys
import time
import logging
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.hub_client import (
    fetch_pending_job,
    report_job_done,
    report_job_error,
    report_job_status,
    push_telemetry,
    poll_commands,
    execute_command,
    hub_is_alive,
)
from core.video_maker import generate_video

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [WORKER] %(levelname)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

POLL_INTERVAL   = int(os.getenv("WORKER_POLL_INTERVAL", "10"))  # segundos
SCRIPTS_DIR     = os.path.join(os.path.dirname(__file__), "..", "queue")


def submit_video_job(topic: str):
    """
    Cria um arquivo .txt na fila local e processa imediatamente.
    Chamado pelo hub_client quando recebe cmd 'generate_video'.
    """
    import time as _t
    script_path = os.path.join(SCRIPTS_DIR, f"cmd_{int(_t.time())}.txt")
    os.makedirs(SCRIPTS_DIR, exist_ok=True)
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(topic)
    logger.info(f"📥 Job remoto enfileirado: {script_path}")
    return script_path


def process_hub_job(job: dict) -> bool:
    """
    Processa um job vindo do HOMES Hub.
    job = { id, topic, script, theme, status }
    """
    job_id = job.get("id", "unknown")
    params = _job_params(job)
    topic  = _job_text(job, params, "topic", "title", "prompt", default="general")
    script = job.get("script", "")
    theme  = _job_text(job, params, "theme", "style", default="yellow_punch")
    brand  = job.get("brand") or theme or "demo"

    logger.info(f"🎬 Processando job #{job_id}: {topic[:60]}")

    report_job_status(job_id, "processing", progress=5, stage="received", message="Engine accepted job")

    # Salva script em arquivo para video_maker
    os.makedirs(SCRIPTS_DIR, exist_ok=True)
    script_path = os.path.join(SCRIPTS_DIR, f"job_{job_id}.txt")

    # Build enough narration for reviewer-facing jobs; avoid 15s smoke renders unless explicitly requested.
    target_seconds = int(params.get("target_duration_seconds") or 60)
    content = script.strip() if script.strip() else _script_from_job(topic, params, theme)
    if target_seconds >= 55 and len(content.split()) < 120:
        content = (content + "\n\n" + _script_from_job(topic, {**params, "target_duration_seconds": target_seconds}, theme)).strip()
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(content)

    try:
        report_job_status(job_id, "processing", progress=20, stage="rendering", message="Rendering video")
        output_path = generate_video(script_path, theme_name=theme, brand_name=brand)
        if output_path:
            report_job_status(job_id, "processing", progress=95, stage="reporting", message="Render complete")
            report_job_done(job_id, output_path)
            logger.info(f"✅ Job #{job_id} concluído → {output_path}")
            return True
        else:
            raise RuntimeError("generate_video retornou None")
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ Job #{job_id} falhou: {error_msg}")
        report_job_error(job_id, error_msg)
        return False


def _job_params(job: dict) -> dict:
    params = job.get("params") or {}
    if isinstance(params, str):
        try:
            params = json.loads(params)
        except json.JSONDecodeError:
            params = {"prompt": params}
    return params if isinstance(params, dict) else {}


def _job_text(job: dict, params: dict, *keys: str, default: str = "") -> str:
    for key in keys:
        value = job.get(key)
        if value:
            return str(value).strip()
        value = params.get(key)
        if value:
            return str(value).strip()
    return default


def _script_from_job(topic: str, params: dict, theme: str = "") -> str:
    target = int(params.get("target_duration_seconds") or 60)
    language = params.get("language") or "en-US"
    angle = params.get("angle") or params.get("description") or params.get("summary") or ""
    audience = params.get("audience") or "reviewers"
    style = params.get("visual_style") or params.get("style") or theme or "editorial"
    urls = params.get("urls") or params.get("url") or ""
    if isinstance(urls, list):
        urls = ", ".join(str(url) for url in urls[:3])

    subject_line = f"{topic}"
    if angle:
        subject_line += f": {angle}"
    source_line = f" Reference source: {urls}." if urls else ""

    base = (
        f"{subject_line}. "
        f"This video is a concise overview for {audience}, focused on the requested theme rather than a generic system demo. "
        f"The visual direction is {style}, with each scene reinforcing the topic, the key idea, and the practical takeaway. "
        f"First, introduce why {topic} matters now. Then show the core concept, one concrete example, and the final takeaway. "
        f"End by making the topic feel clear, useful, and ready to share.{source_line} "
    )
    if language.lower().startswith("pt"):
        base = (
            f"{subject_line}. "
            f"Este vídeo é um resumo direto para {audience}, focado no tema pedido e não em uma demonstração genérica do sistema. "
            f"A direção visual é {style}, com cada cena reforçando o assunto, a ideia principal e a conclusão prática. "
            f"Primeiro, explique por que {topic} importa agora. Depois mostre o conceito central, um exemplo concreto e a mensagem final. "
            f"Feche deixando o tema claro, útil e pronto para compartilhar.{source_line} "
        )
    repeats = max(1, target // 18)
    return (base * repeats).strip()


def run_worker():
    logger.info(f"🟢 HOMES-Engine Worker iniciado")
    logger.info(f"🔌 Hub: {os.getenv('HOMES_HUB_URL', 'http://localhost:8080')}")
    logger.info(f"⏱️  Poll interval: {POLL_INTERVAL}s")

    # Avisa se o Hub não responde (não para o worker)
    if not hub_is_alive():
        logger.warning("⚠️  Hub não responde — worker continua em modo offline (queue local)")

    cycle = 0
    while True:
        cycle += 1
        try:
            # 1. Telemetria a cada 6 ciclos (~1 min)
            if cycle % 6 == 0:
                push_telemetry()

            # 2. Comandos remotos
            for cmd in poll_commands():
                execute_command(cmd)

            # 3. Job de vídeo pendente no Hub
            job = fetch_pending_job()
            if job:
                process_hub_job(job)

            # 4. Fila local (arquivos .txt em queue/)
            local_scripts = sorted(
                f for f in os.listdir(SCRIPTS_DIR)
                if f.endswith(".txt") and not f.startswith("job_")
            ) if os.path.exists(SCRIPTS_DIR) else []

            for fname in local_scripts[:1]:  # 1 por ciclo
                fpath = os.path.join(SCRIPTS_DIR, fname)
                logger.info(f"📥 Fila local: {fname}")
                output = generate_video(fpath)
                if output:
                    # Marca como processado renomeando
                    done_path = fpath.replace(".txt", ".done")
                    os.rename(fpath, done_path)
                    logger.info(f"✅ {fname} → {output}")

        except KeyboardInterrupt:
            logger.info("🛑 Worker encerrado pelo usuário")
            break
        except Exception as e:
            logger.error(f"🔥 Erro no ciclo {cycle}: {e}", exc_info=True)

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    run_worker()
