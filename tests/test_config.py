import unittest
import os
from config import validate_config, THEMES, ASSETS_DIR

class TestConfig(unittest.TestCase):
    def test_directories_exist(self):
        # validate_config should return True or False based on API key, 
        # but directories should be created upon import
        self.assertTrue(os.path.exists(ASSETS_DIR))
        
    def test_themes_loaded(self):
        self.assertIn("yellow_punch", THEMES)
        self.assertEqual(THEMES["yellow_punch"]["name"], "Yellow Punch")

if __name__ == "__main__":
    unittest.main()
