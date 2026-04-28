import os
import json
import logging

logger = logging.getLogger(__name__)

class BrandingLoader:
    def __init__(self, brand_name="default"):
        self.brand_name = brand_name or "default"
        self.brand_path = os.path.join("branding", self.brand_name)
        
        # Fallback para demo se a pasta não existir
        if not os.path.exists(self.brand_path):
            logger.warning(f"[HOMES] Brand '{self.brand_name}' não encontrada, usando 'demo'.")
            self.brand_name = "demo"
            self.brand_path = os.path.join("branding", "demo")
            
        self.config = self._load_config()

    def _load_config(self):
        config_file = os.path.join(self.brand_path, "brand_colors.json")
        # Também tenta brand.json (conforme patch.py)
        if not os.path.exists(config_file):
            config_file = os.path.join(self.brand_path, "brand.json")
            
        if os.path.exists(config_file):
            with open(config_file, "r") as f:
                try:
                    return json.load(f)
                except:
                    return {}
        return {}

    def get_style_prompt(self):
        prompt_file = os.path.join(self.brand_path, "style_prompt.txt")
        if os.path.exists(prompt_file):
            with open(prompt_file, "r") as f:
                return f.read().strip()
        return ""

    def get_asset_path(self, asset_name):
        """Retorna o caminho de um asset (logo, intro, music) se existir."""
        path = os.path.join(self.brand_path, asset_name)
        return path if os.path.exists(path) else None

    def get_broll_folder(self):
        return os.path.join(self.brand_path, "broll_folder")
