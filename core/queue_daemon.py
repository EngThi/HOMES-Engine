import time, os, json
from pathlib import Path
from datetime import datetime
from core.video_maker import generate_video

PENDING_GLOB = "scripts/*.pending.txt"

def log(msg: str):
    ts = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[{ts}] [QUEUE] {msg}", flush=True)

def process_job(path: Path):
    brand = "demo"
    parts = path.stem.split("_")
    if len(parts) >= 2 and parts[1]:
        brand = parts[1]

    # marca como RUNNING para evitar reprocessamento se crashar
    running_path = path.with_suffix(".running.txt")
    path.rename(running_path)

    log(f"START {running_path.name} brand='{brand}'")
    try:
        generate_video(str(running_path), brand_name=brand)
        done_path = running_path.with_suffix(".done.txt")
        running_path.rename(done_path)
        log(f"DONE  {done_path.name}")
    except Exception as e:
        # em caso de erro, volta para .pending.txt para retry manual
        if running_path.exists():
            running_path.rename(path)
        log(f"ERROR {path.name}: {e}")
        raise

def queue_daemon(poll_interval: int = 5):
    log("Daemon iniciado. Monitorando scripts/*.pending.txt ...")
    while True:
        jobs = sorted(Path("scripts").glob("*.pending.txt"))
        for job in jobs:
            try:
                process_job(job)
            except Exception as e:
                log(f"Job {job.name} falhou, será retentado no próximo ciclo.")
        time.sleep(poll_interval)
