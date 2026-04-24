import time
import os
from pathlib import Path
from core.video_maker import generate_video
from core.branding_loader import BrandingLoader

PENDING_GLOB = "scripts/*.pending.txt"

def process_job(path: Path):
    brand = "demo"
    # nome do arquivo pode codificar a brand: ia_<brand>_<timestamp>.pending.txt
    parts = path.stem.split("_")
    if len(parts) >= 2 and parts[1]:
        brand = parts[1]
    
    print(f"[QUEUE] Renderizando {path.name} com brand '{brand}'")
    generate_video(str(path), brand_name=brand)
    
    # renomeia para .done
    done = path.with_suffix(".done.txt")
    path.rename(done)

def queue_daemon(poll_interval: int = 5):
    print("[QUEUE] Daemon iniciado. Monitorando scripts *.pending.txt...")
    while True:
        jobs = [Path(p) for p in sorted(Path("scripts").glob("*.pending.txt"))]
        if not jobs:
            time.sleep(poll_interval)
            continue
        for job in jobs:
            try:
                process_job(job)
            except Exception as e:
                print(f"[QUEUE] Erro processando {job.name}: {e}")
        time.sleep(1)
