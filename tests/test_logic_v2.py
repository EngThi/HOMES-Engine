import unittest
import os
from core.branding_loader import BrandingLoader

class TestBranding(unittest.TestCase):
    def test_load_default_brand(self):
        loader = BrandingLoader("default")
        self.assertIsNotNone(loader.config)
        self.assertTrue("primary" in loader.config)

    def test_load_demo_brand(self):
        loader = BrandingLoader("demo")
        self.assertEqual(loader.config.get("primary"), "#00FFCC")
        
    def test_style_prompt_exists(self):
        loader = BrandingLoader("demo")
        prompt = loader.get_style_prompt()
        self.assertIn("cyberpunk", prompt.lower())

if __name__ == "__main__":
    unittest.main()
