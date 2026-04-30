import main


def test_list_scripts_includes_demo_script():
    assert "e2e_engine_test.txt" in main.list_scripts()


def test_print_health_success(monkeypatch, capsys):
    monkeypatch.setattr(
        main,
        "fetch_engine_health",
        lambda: {
            "service": "VideoLM Engine Bridge",
            "baseUrl": "https://54-162-84-165.sslip.io",
            "timestamp": "now",
        },
    )

    assert main.print_health() is True
    assert "VideoLM OK" in capsys.readouterr().out


def test_print_manifest_summary_success(monkeypatch, capsys):
    monkeypatch.setattr(
        main,
        "fetch_engine_manifest",
        lambda: {
            "name": "VideoLM Factory",
            "version": "2026-04-29",
            "baseUrl": "https://54-162-84-165.sslip.io",
            "publicEndpoints": {
                "videoDemoAssemble": {"url": "https://54-162-84-165.sslip.io/api/video/demo/assemble"},
                "videoStatus": {"urlTemplate": "https://54-162-84-165.sslip.io/api/video/{projectId}/status"},
            },
            "capabilities": {"maxImagesPerRender": 100, "maxUploadMbPerFile": 100},
        },
    )

    assert main.print_manifest_summary() is True
    assert "VideoLM Factory" in capsys.readouterr().out


def test_print_hosted_demo(monkeypatch, capsys):
    monkeypatch.setattr(main, "engine_demo_url", lambda: "https://54-162-84-165.sslip.io/engine-demo")

    main.print_hosted_demo()

    assert "engine-demo" in capsys.readouterr().out


def test_poll_notebooklm_from_cli(monkeypatch, capsys):
    monkeypatch.setattr(
        main,
        "poll_notebooklm_video",
        lambda project_id: {
            "status": "completed",
            "videoUrl": "/videos/research_demo.mp4",
            "type": "video",
            "cached": True,
        },
    )
    monkeypatch.setattr(
        main,
        "resolve_video_url",
        lambda path: f"https://54-162-84-165.sslip.io{path}",
    )

    result = main.poll_notebooklm_from_cli("demo")

    assert result["cached"] is True
    assert "research_demo.mp4" in capsys.readouterr().out


def test_submit_notebooklm_from_cli(monkeypatch, capsys):
    captured = {}

    def fake_submit(**kwargs):
        captured.update(kwargs)
        return {
            "projectId": kwargs["project_id"],
            "status": "submitted",
        }

    monkeypatch.setattr(
        main,
        "submit_notebooklm_video",
        fake_submit,
    )

    result = main.submit_notebooklm_from_cli(
        project_id="demo",
        title="Demo Title",
        theme="Hack Club",
        urls=["https://hackclub.com/,https://example.com"],
        asset_paths=["assets/broll/i1.jpg"],
        style="custom",
        style_prompt="paper collage with terminal UI",
        live_research=True,
        notebook_id="notebook-1",
        profile_id="default",
        interactive=False,
    )

    assert result["status"] == "submitted"
    assert captured["title"] == "Demo Title"
    assert captured["urls"] == ["https://hackclub.com/", "https://example.com"]
    assert captured["asset_paths"] == ["assets/broll/i1.jpg"]
    assert captured["style"] == "custom"
    assert captured["style_prompt"] == "paper collage with terminal UI"
    assert captured["live_research"] is True
    assert captured["notebook_id"] == "notebook-1"
    assert "submitted" in capsys.readouterr().out


def test_submit_notebooklm_from_cli_noninteractive_does_not_prompt(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        main,
        "submit_notebooklm_video",
        lambda **kwargs: captured.update(kwargs) or {"status": "submitted"},
    )

    result = main.submit_notebooklm_from_cli(
        project_id="demo",
        theme="Hack Club",
        urls=["https://hackclub.com/"],
        style="paper_craft",
        interactive=False,
    )

    assert result["status"] == "submitted"
    assert captured["title"] == ""
    assert captured["notebook_id"] == ""


def test_validate_notebooklm_style_requires_prompt_for_custom():
    assert main.validate_notebooklm_style("paper_craft") is True

    try:
        main.validate_notebooklm_style("custom", "")
    except ValueError as e:
        assert "stylePrompt" in str(e)
    else:
        raise AssertionError("Expected ValueError")


def test_parse_csv_values():
    assert main.parse_csv_values(["https://a.com, https://b.com", "https://c.com"]) == [
        "https://a.com",
        "https://b.com",
        "https://c.com",
    ]
