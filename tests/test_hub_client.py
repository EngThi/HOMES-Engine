import json
from pathlib import Path

from core import hub_client


class FakeResponse:
    ok = True
    status_code = 200
    text = "{}"

    def json(self):
        return {}


def test_signed_body_matches_signature(monkeypatch):
    monkeypatch.setattr(hub_client, "HUB_SECRET", "secret")
    payload = {"id": "job1", "status": "processing"}

    body, headers = hub_client._signed_body_and_headers(payload)

    assert body == json.dumps(payload, separators=(",", ":")).encode()
    assert headers["Content-Type"] == "application/json"
    assert headers["X-Homes-Signature"] == hub_client._sign(payload)


def test_report_job_status_posts_signed(monkeypatch):
    calls = {}

    def fake_post(url, data, headers, timeout):
        calls.update({"url": url, "data": data, "headers": headers, "timeout": timeout})
        return FakeResponse()

    monkeypatch.setattr(hub_client, "HUB_BASE", "https://homes.chefthi.hackclub.app")
    monkeypatch.setattr(hub_client.requests, "post", fake_post)

    assert hub_client.report_job_status("job1", "processing", progress=20, stage="rendering")
    assert calls["url"] == "https://homes.chefthi.hackclub.app/api/projects/job1/status"
    assert calls["headers"]["X-Homes-Signature"]
    assert b'"progress":20' in calls["data"]


def test_report_job_done_posts_complete(monkeypatch):
    calls = {}

    def fake_post(url, data, headers, timeout):
        calls.update({"url": url, "data": data, "headers": headers, "timeout": timeout})
        return FakeResponse()

    monkeypatch.setattr(hub_client, "HUB_BASE", "https://homes.chefthi.hackclub.app")
    monkeypatch.setattr(hub_client.requests, "post", fake_post)

    assert hub_client.report_job_done("job1", "output.mp4")
    assert calls["url"] == "https://homes.chefthi.hackclub.app/api/projects/job1/complete"


def test_report_job_done_includes_public_video_url_from_sidecar(monkeypatch, tmp_path):
    calls = {}
    video_path = tmp_path / "HOMES_job1.mp4"
    video_path.write_bytes(b"mp4")
    Path(f"{video_path}.source.json").write_text(
        json.dumps({"video_url": "https://54-162-84-165.sslip.io/videos/job1.mp4"}),
        encoding="utf-8",
    )

    def fake_post(url, data, headers, timeout):
        calls.update({"url": url, "data": data, "headers": headers, "timeout": timeout})
        return FakeResponse()

    monkeypatch.setattr(hub_client, "HUB_BASE", "https://homes.chefthi.hackclub.app")
    monkeypatch.setattr(hub_client.requests, "post", fake_post)

    assert hub_client.report_job_done("job1", str(video_path))
    payload = json.loads(calls["data"].decode())
    assert payload["video_path"] == str(video_path)
    assert payload["video_url"] == "https://54-162-84-165.sslip.io/videos/job1.mp4"
    assert payload["videoUrl"] == "https://54-162-84-165.sslip.io/videos/job1.mp4"


def test_report_job_done_includes_video_metadata(monkeypatch, tmp_path):
    calls = {}
    video_path = tmp_path / "HOMES_job1.mp4"
    video_path.write_bytes(b"mp4-bytes")

    class FakeCompletedProcess:
        returncode = 0
        stderr = ""
        stdout = json.dumps(
            {
                "streams": [
                    {
                        "width": 1080,
                        "height": 1920,
                        "r_frame_rate": "30/1",
                        "codec_name": "h264",
                    }
                ],
                "format": {"duration": "20.123456"},
            }
        )

    def fake_post(url, data, headers, timeout):
        calls.update({"url": url, "data": data, "headers": headers, "timeout": timeout})
        return FakeResponse()

    monkeypatch.setattr(hub_client, "HUB_BASE", "https://homes.chefthi.hackclub.app")
    monkeypatch.setattr(hub_client.requests, "post", fake_post)
    monkeypatch.setattr(hub_client.subprocess, "run", lambda *args, **kwargs: FakeCompletedProcess())

    assert hub_client.report_job_done("job1", str(video_path))
    payload = json.loads(calls["data"].decode())
    assert payload["size_bytes"] == len(b"mp4-bytes")
    assert payload["duration_seconds"] == 20.123
    assert payload["width"] == 1080
    assert payload["height"] == 1920
    assert payload["fps"] == 30
    assert payload["codec"] == "h264"


def test_parse_fps_handles_fractional_rates():
    assert hub_client._parse_fps("30000/1001") == 29.97
    assert hub_client._parse_fps("30/1") == 30
    assert hub_client._parse_fps("0/0") == 0


def test_push_telemetry_posts_signed(monkeypatch):
    calls = {}

    def fake_post(url, data, headers, timeout):
        calls.update({"url": url, "data": data, "headers": headers, "timeout": timeout})
        return FakeResponse()

    monkeypatch.setattr(hub_client, "HUB_BASE", "https://homes.chefthi.hackclub.app")
    monkeypatch.setattr(hub_client.requests, "post", fake_post)

    assert hub_client.push_telemetry()
    assert calls["url"] == "https://homes.chefthi.hackclub.app/api/sensors"
    assert calls["headers"]["X-Homes-Signature"]
