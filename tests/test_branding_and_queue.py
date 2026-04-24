import os
import unittest
from pathlib import Path
import sys
import shutil

# Adicionar raiz ao path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.branding_loader import BrandingLoader
from core.queue_daemon import process_job

class TestBrandingAndQueue(unittest.TestCase):
    def setUp(self):
        os.makedirs("branding/demo", exist_ok=True)
        with open("branding/demo/brand.json", "w", encoding="utf-8") as f:
            f.write('{"name":"demo","style_prompt":"test_cyberpunk"}')
        os.makedirs("scripts", exist_ok=True)
        
        # Mock do generate_video para não rodar FFmpeg nos testes
        import core.video_maker as vm
        self._orig_generate = vm.generate_video
        vm.generate_video = lambda script_path, brand_name=None: print(f"Mock Render: {script_path}")

    def tearDown(self):
        # Limpar lixo de teste se necessário (opcional)
        import core.video_maker as vm
        vm.generate_video = self._orig_generate

    def test_branding_fallback_demo(self):
        # Testa se ao pedir marca inexistente, ele cai na demo
        loader = BrandingLoader("marca_fantasma")
        style = loader.get_style_prompt()
        self.assertEqual(style, "test_cyberpunk")

    def test_process_job_renames_file(self):
        # Testa se o daemon renomeia de .pending para .done
        job = Path("scripts/ia_demo_999.pending.txt")
        job.write_text("conteudo de teste", encoding="utf-8")
        process_job(job)
        self.assertFalse(job.exists())
        self.assertTrue(any(f.name.endswith('.done.txt') for f in Path('scripts').glob('ia_demo_999*')))
        # Limpeza local
        if os.path.exists("scripts/ia_demo_999.done.txt"):
            os.remove("scripts/ia_demo_999.done.txt")

if __name__ == "__main__":
    unittest.main()
