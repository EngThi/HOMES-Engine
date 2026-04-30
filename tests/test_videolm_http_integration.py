import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from core import videolm_client


class VideoLMMockHandler(BaseHTTPRequestHandler):
    project_id = None

    def do_POST(self):
        if self.path != "/api/video/assemble":
            self.send_error(404)
            return

        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        if b'name="projectId"' not in body or b"http-integration" not in body:
            self.send_error(400, "missing projectId")
            return
        if self.headers.get("Bypass-Tunnel-Reminder") != "true":
            self.send_error(400, "missing bypass header")
            return

        type(self).project_id = "http-integration"
        payload = {"videoUrl": "/videos/http-integration.mp4"}
        self._json(200, payload)

    def do_GET(self):
        if self.path == "/api/video/http-integration/status":
            self._json(200, {"status": "completed", "videoPath": "/videos/http-integration.mp4"})
            return
        if self.path == "/videos/http-integration.mp4":
            self.send_response(200)
            self.send_header("Content-Type", "video/mp4")
            self.end_headers()
            self.wfile.write(b"mock-mp4")
            return
        self.send_error(404)

    def _json(self, status, payload):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):
        return


def test_videolm_client_against_real_http_mock(tmp_path, monkeypatch):
    server = ThreadingHTTPServer(("127.0.0.1", 0), VideoLMMockHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    audio = tmp_path / "narration.wav"
    image = tmp_path / "scene.jpg"
    out_dir = tmp_path / "renders"
    audio.write_bytes(b"wav")
    image.write_bytes(b"jpg")

    monkeypatch.setenv("VIDEOLM_URL", f"http://127.0.0.1:{server.server_port}")
    monkeypatch.setenv("VIDEOLM_POLL_INTERVAL", "0")
    monkeypatch.setenv("VIDEOLM_POLL_TIMEOUT", "1")
    monkeypatch.setattr(videolm_client.time, "sleep", lambda _: None)

    try:
        result = videolm_client.assemble_via_videolm(
            audio_path=str(audio),
            image_paths=[str(image)],
            script="script",
            project_id="http-integration",
            output_dir=str(out_dir),
        )
    finally:
        server.shutdown()
        server.server_close()

    assert result == str(out_dir / "HOMES_http-integration.mp4")
    assert (out_dir / "HOMES_http-integration.mp4").read_bytes() == b"mock-mp4"
