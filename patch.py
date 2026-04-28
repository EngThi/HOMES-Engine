Você já consegue transformar esse v2.1 em algo “shipável” só com toques pontuais. Abaixo vão os pseudo‑patches para o **HOMES‑Engine** (sem encostar no repo ainda).

***

## 1. Brand `demo/` pronta para usar

### 1.1. Novo diretório de brand

Crie `branding/demo/brand.json`:

```jsonc
{
  "name": "demo",
  "primary_color": "#22c55e",
  "secondary_color": "#0f172a",
  "font": "System",
  "logo_path": "assets/demo_logo.png",
  "music_path": "assets/demo_bg_music.mp3",
  "style_prompt": "english tech explainer, calm but energetic, youtube style, short punchy sentences"
}
```

- Opcional: adicionar `assets/demo_logo.png` e `assets/demo_bg_music.mp3` placeholders (qualquer arquivo serve pro primeiro ship).

### 1.2. Garantir que sempre há uma brand válida

Em `core/branding_loader.py` (ou equivalente):

```python
class BrandingLoader:
    def __init__(self, brand_name: str = "default"):
        self.brand_name = brand_name or "default"
        self._config = self._load()

    def _load(self):
        path = Path("branding") / self.brand_name / "brand.json"
        if not path.exists():
            # fallback automático para demo
            print(f"[HOMES] Brand '{self.brand_name}' não encontrada, usando 'demo'.")
            path = Path("branding/demo/brand.json")
        with path.open(encoding="utf-8") as f:
            return json.load(f)
```

Assim, mesmo que o usuário erre o nome, `demo` assume o controle.

***

## 2. Tolerar ambiente não‑Termux sem quebrar

Hoje o menu chama `termux-speech-to-text` direto na opção `[1]`.  
Troque o `run_command` + uso no `main()` para algo seguro.

### 2.1. `run_command` defensivo

Em `main.py`:

```python
def run_command(cmd):
    try:
        return subprocess.check_output(cmd, shell=True).decode("utf-8").strip()
    except FileNotFoundError:
        # binário não existe (provavelmente não está em Termux)
        print(f"{YELLOW}[WARN]{RESET} Comando não encontrado: {cmd}")
        return None
    except Exception:
        return None
```

### 2.2. Opção 1: fallback para input manual

Trocar o trecho da opção `choice == '1'`:

```python
if choice == '1':
    content = run_command("termux-speech-to-text")
    if not content:
        print(f"{YELLOW}Termux STT não disponível. Digite o texto abaixo:{RESET}")
        content = input("\n> ")
    if content:
        script_path = f"scripts/voice_{int(time.time())}.txt"
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(content)
```

Resultado: em VM ou desktop não quebra, só cai para texto.

***

## 3. Queue daemon + flag `--daemon`

### 3.1. Novo módulo `core/queue_daemon.py`

Crie `core/queue_daemon.py`:

```python
import time
from pathlib import Path
from core.video_maker import generate_video
from core.branding_loader import BrandingLoader

PENDING_GLOB = "scripts/*.pending.txt"

def process_job(path: Path):
    brand = "default"
    # nome do arquivo pode codificar a brand: ia_<brand>_<timestamp>.pending.txt
    parts = path.stem.split("_")
    if len(parts) >= 2 and parts[1]:
        brand = parts[1]
    branding = BrandingLoader(brand)
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
```

### 3.2. Integrar com `main.py` (flag `--daemon`)

No topo de `main.py`, após imports:

```python
import argparse
from core.queue_daemon import queue_daemon
```

Antes de `if __name__ == "__main__":`:

```python
def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--daemon", action="store_true", help="Run in queue daemon mode")
    return parser.parse_args()
```

E no bloco final:

```python
if __name__ == "__main__":
    args = parse_args()
    if args.daemon:
        # modo serviço: sem interface interativa
        queue_daemon()
    else:
        main()
```

Agora você pode rodar:

```bash
python main.py --daemon
```

E deixar scripts `*.pending.txt` caírem dentro de `scripts/` pelo HOMES.

***

## 4. Testes mínimos para o Engine

Crie `tests/test_branding_and_queue.py` (parecido com o style do Opportunity Aggregator):

```python
import os
import unittest
from pathlib import Path

# add root & core ao path
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.branding_loader import BrandingLoader
from core.queue_daemon import process_job

class TestBrandingAndQueue(unittest.TestCase):
    def setUp(self):
        os.makedirs("branding/demo", exist_ok=True)
        with open("branding/demo/brand.json", "w", encoding="utf-8") as f:
            f.write('{"name":"demo","style_prompt":"test"}')
        os.makedirs("scripts", exist_ok=True)
        # fake generate_video para não rodar ffmpeg nos testes
        import core.queue_daemon as qd
        import core.video_maker as vm
        self._orig_generate = vm.generate_video
        vm.generate_video = lambda script_path, brand_name=None: None

    def tearDown(self):
        # limpar
        import shutil
        shutil.rmtree("branding", ignore_errors=True)
        shutil.rmtree("scripts", ignore_errors=True)
        import core.video_maker as vm
        vm.generate_video = self._orig_generate

    def test_branding_fallback_demo(self):
        loader = BrandingLoader("nao_existe")
        style = loader.get_style_prompt()
        self.assertEqual(style, "test")

    def test_process_job_renames_file(self):
        job = Path("scripts/ia_demo_123.pending.txt")
        job.write_text("conteudo", encoding="utf-8")
        process_job(job)
        self.assertFalse(job.exists())
        self.assertTrue(Path("scripts/ia_demo_123.done.txt").exists())

if __name__ == "__main__":
    unittest.main()
```

Isso garante:

- Fallback para brand `demo`.
- Queue daemon renomeia `.pending` → `.done` e chama `generate_video` sem rodar FFmpeg nos testes.

***

## 5. Pequenas correções de DX

Se quiser alinhar com a ficha v2.1 que você colou:

- No `README.md`, adicionar:

```markdown
### Queue Daemon

To run the engine as a background worker, consuming pending scripts:

```bash
python main.py --daemon
# drop files as scripts/<brand>_<timestamp>.pending.txt
```
```

- E ajustar a seção de “Key Features” para refletir exatamente os nomes de arquivos reais (`ai_writer.py`, `video_maker.py`, etc.), mas isso é só doc.

***

Se quiser, no próximo passo eu faço o mesmo tipo de pseudo‑patch, mas focado no **HOMES (hub)** para fechar o loop HOMES ↔ HOMES‑Engine.