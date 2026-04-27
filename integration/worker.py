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

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.hub_client import (
    fetch_pending_job,
    report_job_done,
    report_job_error,
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
    topic  = job.get("topic", "general")
    script = job.get("script", "")
    theme  = job.get("theme", "yellow_punch")

    logger.info(f"🎬 Processando job #{job_id}: {topic[:60]}")

    # Salva script em arquivo para video_maker
    os.makedirs(SCRIPTS_DIR, exist_ok=True)
    script_path = os.path.join(SCRIPTS_DIR, f"job_{job_id}.txt")

    # Se o Hub não mandou script pronto, usa o tópico direto
    content = script if script.strip() else topic
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(content)

    try:
        output_path = generate_video(script_path, theme_name=theme)
        if output_path:
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
