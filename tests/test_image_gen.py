from pathlib import Path

from core import image_gen
from core.image_gen import ImageGenerator


def test_image_generator_creates_local_fallback(tmp_path, monkeypatch):
    monkeypatch.setattr(image_gen, "ASSETS_DIR", str(tmp_path))

    gen = ImageGenerator()
    result = gen._create_local_fallback(
        "fallback scene for a complete video render",
        "fallback.jpg",
        360,
        640,
    )

    assert result is not None
    assert Path(result).exists()
    assert Path(result).stat().st_size > 0
