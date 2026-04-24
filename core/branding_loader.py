import os
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class BrandingLoader:
    def __init__(self, brand_name: str = "default"):
        self.brand_name = brand_name or "default"
        self._config = self._load()

    def _load(self):
        path = Path("branding") / self.brand_name / "brand.json"
        if not path.exists():
            print(f"[HOMES] Brand '{self.brand_name}' não encontrada, usando 'demo'.")
            path = Path("branding/demo/brand.json")
        
        if not path.exists():
            # Caso extremo onde nem a demo existe
            return {"style_prompt": "cinematic style", "primary_color": "#FFD700"}
            
        with path.open(encoding="utf-8") as f:
            return json.load(f)

    def get_style_prompt(self):
        return self._config.get("style_prompt", "")

    def get_asset_path(self, key):
        return self._config.get(key)
    
    @property
    def config(self):
        return self._config

    def get_broll_folder(self):
        return os.path.join("branding", self.brand_name, "broll_folder")
