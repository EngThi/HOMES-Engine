import os, json, logging
from pathlib import Path

logger = logging.getLogger(__name__)

class BrandingLoader:
    def __init__(self, brand_name: str = "demo"):
        self.brand_name = brand_name or "demo"
        self._config = self._load()

    def _load(self):
        path = Path("branding") / self.brand_name / "brand.json"
        if not path.exists():
            print(f"[HOMES] Brand '{self.brand_name}' not found, using 'demo'.")
            path = Path("branding/demo/brand.json")
        
        with path.open(encoding="utf-8") as f:
            return json.load(f)

    def get_style_prompt(self): return self._config.get("style_prompt", "")
    def get_voice_config(self): return self._config.get("voice", "Kore"), self._config.get("voice_speed", 1.0)
    def get_color_grade(self): return self._config.get("color_grade", {})
    def get_captions_config(self): return self._config.get("captions", {})
    def get_music_config(self): return self._config.get("music", {})
    
    @property
    def config(self): return self._config

    def get_asset_path(self, asset_name):
        path = os.path.join("branding", self.brand_name, asset_name)
        return path if os.path.exists(path) else None

    def get_broll_folder(self):
        return os.path.join("branding", self.brand_name, "broll_folder")
