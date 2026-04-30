from pathlib import Path
from unittest.mock import Mock

from core import videolm_client


class FakeResponse:
    def __init__(self, ok=True, status_code=200, payload=None, text="", chunks=None):
        self.ok = ok
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text
        self._chunks = chunks or [b"video-bytes"]

    def json(self):
        return self._payload

    def raise_for_status(self):
        if not self.ok:
            raise RuntimeError(f"HTTP {self.status_code}")

    def iter_content(self, chunk_size=8192):
        yield from self._chunks


def test_endpoint_uses_public_demo_contract_without_token(monkeypatch):
    monkeypatch.setenv("VIDEOLM_URL", "https://videolm-absolute-cinema.loca.lt")
    monkeypatch.delenv("VIDEOLM_ASSEMBLE_PATH", raising=False)
    monkeypatch.delenv("VIDEOLM_TOKEN", raising=False)

    assert (
        videolm_client._assemble_endpoint()
        == "https://videolm-absolute-cinema.loca.lt/api/video/demo/assemble"
    )


def test_endpoint_uses_authenticated_contract_with_token(monkeypatch):
    monkeypatch.setenv("VIDEOLM_URL", "https://videolm-absolute-cinema.loca.lt")
    monkeypatch.delenv("VIDEOLM_ASSEMBLE_PATH", raising=False)
    monkeypatch.setenv("VIDEOLM_TOKEN", "jwt")

    assert (
        videolm_client._assemble_endpoint()
        == "https://videolm-absolute-cinema.loca.lt/api/video/assemble"
    )


def test_endpoint_can_be_overridden_for_demo_contract(monkeypatch):
    monkeypatch.setenv("VIDEOLM_URL", "https://videolm-absolute-cinema.loca.lt")
    monkeypatch.setenv("VIDEOLM_ASSEMBLE_PATH", "/api/video/demo/assemble")

    assert (
        videolm_client._assemble_endpoint()
        == "https://videolm-absolute-cinema.loca.lt/api/video/demo/assemble"
    )


def test_headers_include_localtunnel_bypass_and_optional_token(monkeypatch):
    monkeypatch.setenv("VIDEOLM_TOKEN", "test-token")

    headers = videolm_client._headers()

    assert headers["Accept"] == "application/json"
    assert headers["Bypass-Tunnel-Reminder"] == "true"
    assert headers["Authorization"] == "Bearer test-token"


def test_engine_demo_url_uses_base(monkeypatch):
    monkeypatch.setenv("VIDEOLM_URL", "https://54-162-84-165.sslip.io")

    assert videolm_client.engine_demo_url() == "https://54-162-84-165.sslip.io/engine-demo"


def test_fetch_engine_health(monkeypatch):
    monkeypatch.setenv("VIDEOLM_URL", "https://54-162-84-165.sslip.io")
    get = Mock(return_value=FakeResponse(payload={"status": "ok", "service": "VideoLM Engine Bridge"}))
    monkeypatch.setattr(videolm_client.requests, "get", get)

    health = videolm_client.fetch_engine_health()

    assert health["status"] == "ok"
    assert get.call_args.args[0] == "https://54-162-84-165.sslip.io/api/engine/health"


def test_fetch_engine_manifest(monkeypatch):
    monkeypatch.setenv("VIDEOLM_URL", "https://54-162-84-165.sslip.io")
    get = Mock(return_value=FakeResponse(payload={"name": "VideoLM Factory"}))
    monkeypatch.setattr(videolm_client.requests, "get", get)

    manifest = videolm_client.fetch_engine_manifest()

    assert manifest["name"] == "VideoLM Factory"
    assert get.call_args.args[0] == "https://54-162-84-165.sslip.io/api/engine/manifest"


def test_assemble_posts_assets_polls_and_downloads_video(tmp_path, monkeypatch):
    monkeypatch.setenv("VIDEOLM_URL", "https://videolm-absolute-cinema.loca.lt")
    monkeypatch.delenv("VIDEOLM_ASSEMBLE_PATH", raising=False)
    monkeypatch.setenv("VIDEOLM_POLL_INTERVAL", "0")
    monkeypatch.setenv("VIDEOLM_POLL_TIMEOUT", "1")
    monkeypatch.delenv("VIDEOLM_TOKEN", raising=False)
    monkeypatch.setattr(videolm_client.time, "sleep", lambda _: None)

    audio = tmp_path / "narration.wav"
    image = tmp_path / "scene.jpg"
    out_dir = tmp_path / "renders"
    audio.write_bytes(b"wav")
    image.write_bytes(b"jpg")

    post = Mock(
        return_value=FakeResponse(
            payload={"videoUrl": "/api/video/test-project/download"}
        )
    )
    get = Mock(
        side_effect=[
            FakeResponse(payload={"status": "processing", "progress": 25, "stage": "rendering"}),
            FakeResponse(payload={"status": "completed", "progress": 100, "stage": "completed", "videoPath": "/videos/test.mp4"}),
            FakeResponse(chunks=[b"mp4"]),
        ]
    )
    monkeypatch.setattr(videolm_client.requests, "post", post)
    monkeypatch.setattr(videolm_client.requests, "get", get)

    result = videolm_client.assemble_via_videolm(
        audio_path=str(audio),
        image_paths=[str(image)],
        script="hello",
        project_id="test-project",
        bg_music_id="signature_music.mp3",
        output_dir=str(out_dir),
    )

    assert result == str(out_dir / "HOMES_test-project.mp4")
    assert Path(result).read_bytes() == b"mp4"

    post_url = post.call_args.args[0]
    post_kwargs = post.call_args.kwargs
    assert post_url == "https://videolm-absolute-cinema.loca.lt/api/video/demo/assemble"
    assert post_kwargs["headers"]["Bypass-Tunnel-Reminder"] == "true"
    assert post_kwargs["data"] == {
        "script": "hello",
        "bgMusicId": "signature_music.mp3",
        "projectId": "test-project",
        "duration": "0",
    }

    status_url = get.call_args_list[0].args[0]
    download_url = get.call_args_list[2].args[0]
    assert status_url == "https://videolm-absolute-cinema.loca.lt/api/video/test-project/status"
    assert download_url == "https://videolm-absolute-cinema.loca.lt/videos/test.mp4"


def test_assemble_falls_back_to_demo_endpoint(tmp_path, monkeypatch):
    monkeypatch.setenv("VIDEOLM_URL", "https://videolm-absolute-cinema.loca.lt")
    monkeypatch.setenv("VIDEOLM_ASSEMBLE_PATH", "/api/video/assemble")
    monkeypatch.setenv("VIDEOLM_POLL_INTERVAL", "0")
    monkeypatch.setenv("VIDEOLM_POLL_TIMEOUT", "1")
    monkeypatch.setattr(videolm_client.time, "sleep", lambda _: None)

    audio = tmp_path / "narration.wav"
    image = tmp_path / "scene.jpg"
    out_dir = tmp_path / "renders"
    audio.write_bytes(b"wav")
    image.write_bytes(b"jpg")

    post = Mock(
        side_effect=[
            FakeResponse(ok=False, status_code=404, text="not found"),
            FakeResponse(payload={"videoUrl": "/videos/fallback.mp4"}),
        ]
    )
    get = Mock(
        side_effect=[
            FakeResponse(payload={"status": "completed", "videoUrl": "/videos/fallback.mp4"}),
            FakeResponse(chunks=[b"fallback-mp4"]),
        ]
    )
    monkeypatch.setattr(videolm_client.requests, "post", post)
    monkeypatch.setattr(videolm_client.requests, "get", get)

    result = videolm_client.assemble_via_videolm(
        audio_path=str(audio),
        image_paths=[str(image)],
        script="hello",
        project_id="fallback-project",
        output_dir=str(out_dir),
    )

    assert result == str(out_dir / "HOMES_fallback-project.mp4")
    assert post.call_args_list[0].args[0].endswith("/api/video/assemble")
    assert post.call_args_list[1].args[0].endswith("/api/video/demo/assemble")
