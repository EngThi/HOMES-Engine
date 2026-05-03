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
    assert payload["artifact_url"] == "https://54-162-84-165.sslip.io/videos/job1.mp4"
    assert payload["artifactUrl"] == "https://54-162-84-165.sslip.io/videos/job1.mp4"
    assert payload["content_type"] == "video/mp4"
    assert payload["contentType"] == "video/mp4"
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


def test_report_artifact_done_includes_generic_fields(monkeypatch):
    calls = {}

    def fake_post(url, data, headers, timeout):
        calls.update({"url": url, "data": data, "headers": headers, "timeout": timeout})
        return FakeResponse()

    monkeypatch.setattr(hub_client, "HUB_BASE", "https://homes.chefthi.hackclub.app")
    monkeypatch.setattr(hub_client.requests, "post", fake_post)

    assert hub_client.report_artifact_done(
        "job1",
        artifact_url="https://54-162-84-165.sslip.io/artifacts/info.png",
        artifact_type="infographic",
        content_type="image/png",
        metadata={"size_bytes": 123456},
    )
    payload = json.loads(calls["data"].decode())
    assert payload["artifact_type"] == "infographic"
    assert payload["artifactType"] == "infographic"
    assert payload["artifact_url"] == "https://54-162-84-165.sslip.io/artifacts/info.png"
    assert payload["artifactUrl"] == "https://54-162-84-165.sslip.io/artifacts/info.png"
    assert payload["content_type"] == "image/png"
    assert payload["contentType"] == "image/png"
    assert payload["size_bytes"] == 123456
    assert "video_url" not in payload


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


def test_push_telemetry_includes_capability_catalog(monkeypatch):
    calls = {}

    def fake_post(url, data, headers, timeout):
        calls.update({"url": url, "data": data, "headers": headers, "timeout": timeout})
        return FakeResponse()

    monkeypatch.setattr(hub_client, "HUB_BASE", "https://homes.chefthi.hackclub.app")
    monkeypatch.setattr(hub_client.requests, "post", fake_post)

    assert hub_client.push_telemetry()
    payload = json.loads(calls["data"].decode())
    assert payload["capabilities_count"] == 19
    assert any(item["id"] == "production.video_render" for item in payload["capabilities"])
    assert any(item["id"] == "production.studio_artifact_submit" for item in payload["capabilities"])
    assert any(item["id"] == "production.studio_artifact_poll" for item in payload["capabilities"])
    assert any(item["id"] == "production.factory_infographic_assets_submit" for item in payload["capabilities"])
    assert any(item["id"] == "production.factory_infographic_assets_poll" for item in payload["capabilities"])
    assert any(item["id"] == "engine_smoke" for item in payload["recipes"])
    assert payload["runtime_manifest"]["capabilities_count"] == 19
    assert any(
        item["id"] == "production.factory_infographic_assets_poll"
        for item in payload["runtime_manifest"]["capabilities"]
    )


def test_push_telemetry_includes_videolm_artifact_types(monkeypatch):
    calls = {}

    def fake_post(url, data, headers, timeout):
        calls.update({"url": url, "data": data, "headers": headers, "timeout": timeout})
        return FakeResponse()

    def fake_manifest(timeout):
        return {
            "artifactTypes": {
                "video": {"contentTypes": ["video/mp4"]},
                "infographic": {"contentTypes": ["image/png"]},
            }
        }

    monkeypatch.setattr(hub_client, "HUB_BASE", "https://homes.chefthi.hackclub.app")
    monkeypatch.setattr(hub_client.requests, "post", fake_post)
    monkeypatch.setenv("VIDEOLM_URL", "https://54-162-84-165.sslip.io")
    monkeypatch.setattr("core.videolm_client.fetch_engine_manifest", fake_manifest)
    monkeypatch.setattr(hub_client, "_VIDEOLM_ARTIFACT_TYPES_CACHE", None)

    assert hub_client.push_telemetry()
    payload = json.loads(calls["data"].decode())
    assert payload["artifactTypes"]["video"]["contentTypes"] == ["video/mp4"]
    assert payload["artifact_types"]["infographic"]["contentTypes"] == ["image/png"]


def test_push_telemetry_includes_recent_runtime_events(monkeypatch, tmp_path):
    calls = {}

    def fake_post(url, data, headers, timeout):
        calls.update({"url": url, "data": data, "headers": headers, "timeout": timeout})
        return FakeResponse()

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(hub_client, "HUB_BASE", "https://homes.chefthi.hackclub.app")
    monkeypatch.setattr(hub_client.requests, "post", fake_post)

    from core.runtime import StateStore

    StateStore().append_event("capability.completed", {"id": "demo"})
    assert hub_client.push_telemetry()
    payload = json.loads(calls["data"].decode())
    assert payload["recent_runtime_events"][0]["event_type"] == "capability.completed"


def test_execute_capability_command_runs_runtime_capability(monkeypatch):
    captured = {}

    def fake_run_capability(capability_id, args=None, context=None):
        captured["capability_id"] = capability_id
        captured["args"] = args
        captured["engine_id"] = context.engine_id
        return {"ok": True}

    monkeypatch.setattr("core.runtime.default_capabilities.run_capability", fake_run_capability)

    result = hub_client.execute_command(
        {
            "command": "run_capability",
            "args": [
                {
                    "capability_id": "integration.hosted_demo_url",
                    "args": {"hello": "world"},
                }
            ],
        }
    )

    assert result["status"] == "completed"
    assert captured["capability_id"] == "integration.hosted_demo_url"
    assert captured["args"] == {"hello": "world"}
    assert captured["engine_id"] == hub_client.ENGINE_ID
    assert hub_client.COMMAND_RESULTS[-1]["command"] == "run_capability"


def test_execute_capability_command_accepts_legacy_args_shape(monkeypatch):
    captured = {}

    def fake_run_capability(capability_id, args=None, context=None):
        captured["capability_id"] = capability_id
        captured["args"] = args
        return {"ok": True}

    monkeypatch.setattr("core.runtime.default_capabilities.run_capability", fake_run_capability)

    result = hub_client.execute_command(
        {
            "command": "run_capability",
            "args": ["integration.hosted_demo_url", {"hello": "world"}],
        }
    )

    assert result["status"] == "completed"
    assert captured == {
        "capability_id": "integration.hosted_demo_url",
        "args": {"hello": "world"},
    }


def test_execute_recipe_command_runs_runtime_recipe(monkeypatch):
    captured = {}

    def fake_run_recipe(recipe_id, inputs=None, context=None):
        captured["recipe_id"] = recipe_id
        captured["inputs"] = inputs
        captured["engine_id"] = context.engine_id
        return {"status": "completed"}

    monkeypatch.setattr("core.runtime.run_recipe", fake_run_recipe)

    result = hub_client.execute_command(
        {
            "command": "run_recipe",
            "args": [
                {
                    "recipe_id": "engine_smoke",
                    "inputs": {"topic": "HOMES"},
                }
            ],
        }
    )

    assert result["status"] == "completed"
    assert captured == {
        "recipe_id": "engine_smoke",
        "inputs": {"topic": "HOMES"},
        "engine_id": hub_client.ENGINE_ID,
    }
    assert hub_client.COMMAND_RESULTS[-1]["command"] == "run_recipe"


def test_execute_recipe_command_accepts_legacy_args_shape(monkeypatch):
    captured = {}

    def fake_run_recipe(recipe_id, inputs=None, context=None):
        captured["recipe_id"] = recipe_id
        captured["inputs"] = inputs
        return {"status": "completed"}

    monkeypatch.setattr("core.runtime.run_recipe", fake_run_recipe)

    result = hub_client.execute_command({"command": "run_recipe", "args": ["engine_smoke", {"topic": "HOMES"}]})

    assert result["status"] == "completed"
    assert captured == {"recipe_id": "engine_smoke", "inputs": {"topic": "HOMES"}}


def test_execute_capability_command_requires_capability_id():
    result = hub_client.execute_command({"command": "run_capability", "args": []})

    assert result["status"] == "error"
    assert "capability_id" in result["error"]


def test_execute_command_remembers_unknown_command():
    result = hub_client.execute_command({"command": "does_not_exist", "args": []})

    assert result["status"] == "error"
    assert hub_client.COMMAND_RESULTS[-1]["result"]["error"] == "unknown command: does_not_exist"


def test_execute_command_accepts_notify():
    result = hub_client.execute_command({"command": "notify", "args": ["HOMES dashboard test"]})

    assert result == {"status": "completed", "message": "HOMES dashboard test"}
    assert hub_client.COMMAND_RESULTS[-1]["command"] == "notify"


def test_push_telemetry_includes_recent_command_results(monkeypatch):
    calls = {}

    def fake_post(url, data, headers, timeout):
        calls.update({"url": url, "data": data, "headers": headers, "timeout": timeout})
        return FakeResponse()

    hub_client.COMMAND_RESULTS.clear()
    hub_client._remember_command_result("status", {"status": "completed"})
    monkeypatch.setattr(hub_client, "HUB_BASE", "https://homes.chefthi.hackclub.app")
    monkeypatch.setattr(hub_client.requests, "post", fake_post)

    assert hub_client.push_telemetry()
    payload = json.loads(calls["data"].decode())
    assert payload["recent_command_results"][0]["command"] == "status"
