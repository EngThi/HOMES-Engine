from core.runtime import CapabilityContext, CapabilityRegistry, CapabilitySpec, PolicyEngine, StateStore, load_profile


def test_capability_registry_runs_declared_handler():
    registry = CapabilityRegistry()
    spec = CapabilitySpec(
        id="demo.echo",
        name="Echo",
        description="Return input payload",
        category="agent",
        permissions_required=["profile.read"],
    )

    @registry.register(spec)
    def echo(context, args):
        return {"profile": context.profile["id"], "args": args}

    result = registry.run("demo.echo", {"hello": "world"}, CapabilityContext(profile={"id": "test"}))

    assert result == {"profile": "test", "args": {"hello": "world"}}
    assert registry.list()[0]["id"] == "demo.echo"


def test_policy_engine_denies_hardware_by_default():
    spec = CapabilitySpec(
        id="physical.relay",
        name="Relay",
        description="Toggle relay",
        category="physical",
        hardware_access=True,
    )

    decision = PolicyEngine().decide(spec)

    assert decision.allowed is False
    assert "Hardware" in decision.reason


def test_profile_loader_merges_default_profile(tmp_path):
    profile_dir = tmp_path / "profiles"
    profile_dir.mkdir()
    (profile_dir / "alice.json").write_text(
        '{"id":"alice","preferences":{"language":"pt-BR"}}',
        encoding="utf-8",
    )

    profile = load_profile("alice", root=str(profile_dir))

    assert profile["id"] == "alice"
    assert profile["preferences"]["language"] == "pt-BR"
    assert profile["preferences"]["rss_feeds"]


def test_state_store_persists_values_and_events(tmp_path):
    store = StateStore(str(tmp_path / "state.sqlite"))

    store.set("jobs", "job1", {"status": "completed"})
    event_id = store.append_event("job.completed", {"id": "job1"})

    assert store.get("jobs", "job1") == {"status": "completed"}
    assert event_id == 1
    assert store.recent_events()[0]["event_type"] == "job.completed"
