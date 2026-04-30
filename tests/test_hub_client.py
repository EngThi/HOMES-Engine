import json

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
