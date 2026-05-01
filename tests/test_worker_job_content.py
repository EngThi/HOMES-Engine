from integration.worker import _job_params, _job_text, _script_from_job


def test_job_params_accepts_json_string():
    params = _job_params({"params": '{"topic":"solar homes","theme":"retro_print"}'})

    assert params["topic"] == "solar homes"
    assert params["theme"] == "retro_print"


def test_job_text_reads_job_before_params():
    job = {"topic": "direct topic", "params": {"topic": "param topic"}}

    assert _job_text(job, job["params"], "topic") == "direct topic"


def test_script_from_job_uses_requested_topic_not_mock_dashboard_copy():
    script = _script_from_job(
        "urban gardening",
        {
            "target_duration_seconds": 20,
            "audience": "new homeowners",
            "angle": "small balconies can produce real food",
        },
        "paper_craft",
    )

    assert "urban gardening" in script
    assert "small balconies can produce real food" in script
    assert "paper_craft" in script
    assert "dashboard workflow" not in script
    assert "generic system demo" in script
