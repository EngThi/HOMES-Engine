import os
import time
import sys
import logging

# Injetar a raiz do projeto no path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.video_maker import generate_video

logging.basicConfig(level=logging.INFO, format='%(asctime)s - DAEMON - %(message)s')
logger = logging.getLogger(__name__)

def run_daemon(brand="default"):
    logger.info(f"🚀 Queue Daemon iniciado (Brand: {brand})")
    logger.info("Aguardando arquivos .pending.txt em scripts/...")
    
    try:
        while True:
            pending_files = [f for f in os.listdir("scripts") if f.endswith(".pending.txt")]
            
            if pending_files:
                for filename in pending_files:
                    path = os.path.join("scripts", filename)
                    logger.info(f"🔥 Processando tarefa: {filename}")
                    
                    try:
                        # Executa o render
                        generate_video(path, brand_name=brand)
                        # Marca como concluído
                        os.rename(path, path.replace(".pending.txt", ".done.txt"))
                        logger.info(f"✅ Sucesso: {filename}")
                    except Exception as e:
                        logger.error(f"❌ Erro ao processar {filename}: {e}")
                    
                    time.sleep(2)
            
            time.sleep(10)
    except KeyboardInterrupt:
        logger.info("🛑 Daemon encerrado pelo usuário.")

if __name__ == "__main__":
    brand = sys.argv[1] if len(sys.argv) > 1 else "default"
    run_daemon(brand)
