from pathlib import Path

from PIL import Image

from core import video_maker


def test_target_scene_count_scales_to_long_form():
    content = "This is a complete long-form script. " * 20

    count = video_maker._target_scene_count(305, content)

    assert count >= 50
    assert count <= video_maker.MAX_VIDEOLM_IMAGES


def test_copy_broll_image(tmp_path):
    source = tmp_path / "source.jpg"
    dest = tmp_path / "dest.jpg"
    Image.new("RGB", (720, 1280), "#101827").save(source)

    result = video_maker._copy_broll_image(str(source), str(dest))

    assert result == str(dest)
    assert dest.exists()
    assert dest.stat().st_size > 0
