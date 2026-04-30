import time
import logging
import sys
import os

# Injetar a raiz do projeto no path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import hub_client
from core.video_maker import generate_video
from config import SCRIPTS_DIR

# Configuração de Logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [HUB-INTEGRATION] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

POLL_INTERVAL = 10  # Conforme guia (5-10s)

def process_job(job: dict):
    """Executa o Job vindo do Hub."""
    job_id = job.get('id')
    topic  = job.get('topic', 'Untitled')
    script = job.get('script')
    theme  = job.get('theme', 'default')

    logger.info(f"🚀 Job Recebido: #{job_id} | Tópico: {topic}")

    if not script:
        logger.error(f"❌ Job #{job_id} não possui script. Cancelando.")
        hub_client.report_job_error(job_id, "Missing script content")
        return

    # 1. Salvar Script para o Engine
    script_filename = f"hub_{job_id}.txt"
    script_path = os.path.join(SCRIPTS_DIR, script_filename)
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script)

    # 2. Renderizar (Absolute Cinema v3.0)
    try:
        hub_client.report_job_status(job_id, "processing", progress=10, stage="rendering", message="Engine started render")
        logger.info(f"🎬 Iniciando Renderização Local (Marca: {theme})...")
        video_path = generate_video(script_path, brand_name=theme)
        
        if video_path and os.path.exists(video_path):
            logger.info(f"✅ Render concluído: {video_path}")
            # 3. Reportar ao Hub com Assinatura HMAC (automático via hub_client)
            hub_client.report_job_status(job_id, "processing", progress=95, stage="reporting", message="Render complete")
            if hub_client.report_job_done(job_id, video_path):
                logger.info(f"📡 Hub sincronizado: Job #{job_id} marcado como COMPLETED.")
            else:
                logger.error(f"📡 Falha na sincronização: Hub não aceitou a conclusão do Job #{job_id}.")
        else:
            hub_client.report_job_error(job_id, "Render failed to produce output file")
            
    except Exception as e:
        logger.error(f"💥 Erro Crítico no Engine: {e}")
        hub_client.report_job_error(job_id, str(e))

def main_loop():
    logger.info("🎬 HOMES-Engine Poller Ativo (v3.0 Integration)")
    logger.info(f"🔗 Hub Base: {os.getenv('HOMES_HUB_URL')}")
    
    # Check inicial de saúde
    if not hub_client.hub_is_alive():
        logger.warning("⚠️  Hub parece offline. Verifique a URL do Cloudflare.")

    last_telemetry = 0
    
    while True:
        # A. Polling de Jobs (Passo 1 do Guia)
        job = hub_client.fetch_pending_job()
        if job:
            process_job(job)
        
        # B. Telemetria de Saúde (A cada 30 segundos ou quando ocioso)
        if time.time() - last_telemetry > 30:
            hub_client.push_telemetry()
            last_telemetry = time.time()

        # C. Comandos Remotos
        commands = hub_client.poll_commands()
        for cmd in commands:
            hub_client.execute_command(cmd)

        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    try:
        main_loop()
    except KeyboardInterrupt:
        logger.info("Stopping Engine Poller...")
