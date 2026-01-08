import time
import requests
import json
import os
import logging
from config import SCRIPTS_DIR, GEMINI_API_KEY
from core.video_maker import generate_video

# Configuração de Logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [POLLER] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Configurações do Backend
BACKEND_URL = "http://localhost:3000"
POLL_INTERVAL = 5  # Segundos

def get_pending_job():
    """Consulta a API por novos trabalhos."""
    try:
        response = requests.get(f"{BACKEND_URL}/api/project/pending", timeout=5)
        if response.status_code == 200:
            return response.json()
    except requests.exceptions.ConnectionError:
        logger.warning("Backend offline. Tentando reconectar...")
    except Exception as e:
        logger.error(f"Erro ao buscar job: {e}")
    return None

def report_completion(job_id, video_path):
    """Notifica o backend que o trabalho terminou."""
    payload = {
        "id": job_id,
        "video_path": str(video_path),
        "status": "completed",
        "timestamp": time.time()
    }
    try:
        requests.post(f"{BACKEND_URL}/api/project/{job_id}/complete", json=payload)
        logger.info(f"✅ Job #{job_id} sincronizado com sucesso!")
    except Exception as e:
        logger.error(f"❌ Falha ao reportar conclusão: {e}")

def process_job(job):
    """Orquestra a execução do job."""
    job_id = job.get('id')
    logger.info(f"🚀 Iniciando Job #{job_id}: {job.get('topic')}")
    
    # 1. Salvar Script Temporário
    script_content = job.get('script')
    if not script_content:
        logger.error("Job sem script!")
        return

    filename = f"job_{job_id}.txt"
    script_path = os.path.join(SCRIPTS_DIR, filename)
    
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script_content)
    
    # 2. Renderizar Vídeo (Chama o Engine)
    try:
        theme = job.get('theme', 'yellow_punch')
        # Nota: generate_video atualmente não retorna o path, vamos assumir baseado no log
        # Em produção, o video_maker deveria retornar o path.
        # Vamos rodar e capturar erros.
        generate_video(script_path, theme_name=theme)
        
        # Heurística para achar o vídeo (já que o video_maker joga no output)
        # Em um refactor futuro, generate_video deve retornar o path exato.
        logger.info("Renderização finalizada (supostamente).")
        
        return "caminho_simulado_para_video.mp4" # Placeholder para o mock
    except Exception as e:
        logger.error(f"Falha na renderização: {e}")
        return None

def start_worker():
    print(f"👷 HOMES-Engine Worker Iniciado")
    print(f"🔌 Conectado a: {BACKEND_URL}")
    print("--------------------------------")
    
    while True:
        job = get_pending_job()
        
        if job:
            video_path = process_job(job)
            if video_path:
                report_completion(job['id'], video_path)
        else:
            # Heartbeat discreto
            # print(".", end="", flush=True) 
            pass
            
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    start_worker()
