# HOMES-Engine: Modular Personal Runtime

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FFmpeg](https://img.shields.io/badge/FFmpeg-rendering-007808?logo=ffmpeg&logoColor=white)](https://ffmpeg.org/)
[![Terminal First](https://img.shields.io/badge/interface-terminal--first-111827)](#try-it)
[![Hosted Demo](https://img.shields.io/badge/demo-online-16A34A)](https://54-162-84-165.sslip.io/engine-demo)
[![VideoLM](https://img.shields.io/badge/renderer-VideoLM-7C3AED)](https://54-162-84-165.sslip.io/api/engine/manifest)

HOMES-Engine is evolving into a modular personal runtime for autonomous workflows, local tools, media pipelines, and physical-world integration. Video generation is the first production-grade capability: the Engine receives jobs from the [HOMES Hub/MCP](https://github.com/EngThi/HOMES) layer, builds or accepts a script, generates narration and visual scenes, delegates final assembly to the hosted VideoLM renderer, and reports a public MP4 artifact back to the Hub.

The project started as a Termux/mobile-first experiment, but the reviewer path is now a hosted worker flow:

```text
HOMES Hub MCP -> HOMES-Engine worker -> VideoLM renderer -> public MP4 -> Hub dashboard
```

The long-term architecture is capability-based rather than app-based:

```text
Perception -> audio, vision, sensors, system status
Action     -> shell, browser, notifications, TTS, hardware
Cognition  -> planning, memory, profiles, policies
Production -> video, briefs, research, reports
Integration-> Hub API, MCP tools, queues, webhooks, HMAC, MQTT
```

## Try It

Hosted reviewer demo:

```text
https://54-162-84-165.sslip.io/engine-demo
```

Terminal-first workflow:

```bash
python3 main.py --demo-url
python3 main.py --health
python3 main.py --manifest
python3 main.py
```

The hosted demo is backed by the VideoLM VM renderer and includes pre-rendered outputs plus deterministic demo generation. The CLI remains the canonical local interface.

> [!TIP]
> A completed Hack Club NotebookLM render is available as a public MP4:<br>
> [Watch the Hack Club community render](https://54-162-84-165.sslip.io/videos/research_community_1777566704645.mp4)

## Production Capabilities

- **Terminal CLI:** interactive `python3 main.py` plus non-interactive flags for health, manifest, demo URL, direct render, Hub mode, local queue mode, and NotebookLM submit/poll.
- **Hosted VideoLM assembly:** sends audio, images, script, `projectId`, and optional background music to VideoLM; polls status; downloads the completed MP4.
- **NotebookLM video bridge:** submits URLs/assets/notebook IDs to the hosted NotebookLM video endpoint with selectable styles.
- **HOMES Hub worker:** polls pending jobs, reports progress, signs status/complete/telemetry with HMAC, and returns public video artifacts.
- **Public artifact reporting:** reports `video_path`, `video_url`, `videoUrl`, file size, duration, width, height, fps, codec, and `engine_id` on completed jobs.
- **Branding kits:** reads brand profiles for style prompts, colors, logos, and music assets.
- **Fallback rendering path:** uses local FFmpeg if the hosted renderer is unavailable.
- **Local queue daemon:** processes `scripts/*.pending.txt` jobs for terminal/offline workflows.
- **Runtime primitives:** capability registry, profile loader, policy gate, and SQLite state/event store are now scaffolded for broader automation modules.

## Technical Stack

- **Core:** Python 3.10+
- **Rendering:** hosted VideoLM plus local FFmpeg fallback
- **Audio:** Gemini TTS with Edge-TTS fallback
- **Images:** Gemini/Pollinations/local fallback generation
- **Subtitles:** local ASS subtitle generation
- **Hub auth:** compact JSON HMAC-SHA256 via `X-Homes-Signature`
- **Artifacts:** public VideoLM `/videos/*.mp4` URLs plus local `output/renders/` copies
- **Runtime state:** local SQLite key-value/event store for long-running capabilities

## Runtime Architecture

The Engine is being separated into layers so modules do not hardcode one user's routine or devices:

```text
core/runtime/  capability contracts, policy, profile loading, state store
core/modules/  plug-in capabilities
integration/   Hub worker, command polling, external control plane bridges
branding/      media-facing brand kits
profiles/      user preferences, sources, goals, devices, policies
output/        local renders, state, logs, generated assets
```

Capability contract:

```python
CapabilitySpec(
    id="creator.video_render",
    name="Video Render",
    description="Render a public MP4 from a script/topic",
    category="production",
    inputs_schema={...},
    outputs_schema={...},
    permissions_required=["video.render", "hub.report"],
    required_capabilities=[],
    triggers_supported=["hub_job", "cli"],
    async_mode=True,
    writes_state=True,
    network_access=True,
    hardware_access=False,
    edge_compatible=True,
    hub_compatible=True,
)
```

Profiles are JSON files under `profiles/` and hold preferences, sources, goals, devices, and policy defaults. Modules should read profile context from the runtime instead of embedding personal assumptions.

## CLI Commands

```bash
python3 main.py --demo-url
python3 main.py --health
python3 main.py --manifest
python3 main.py --demo
python3 main.py --render scripts/e2e_engine_test.txt
python3 main.py --hub
python3 main.py --daemon
```

NotebookLM:

```bash
python3 main.py --notebooklm-submit \
  --project-id engine_hackclub_demo \
  --theme "Hack Club community" \
  --url https://hackclub.com/ \
  --style paper_craft

python3 main.py --notebooklm-poll engine_hackclub_demo
```

Supported NotebookLM styles:

```text
classic
whiteboard
watercolor
anime
kawaii
retro_print
heritage
paper_craft
custom
```

`--style custom` requires `--style-prompt`.

## HOMES Hub Contract

The worker consumes jobs created by the HOMES Hub/MCP layer.

Accepted job shape:

```json
{
  "topic": "HOMES demo",
  "theme": "absolute_cinema",
  "script": "optional script",
  "params": {
    "target_duration_seconds": 30,
    "language": "pt-BR",
    "style": "cinematic dashboard demo",
    "angle": "public review walkthrough",
    "audience": "ship reviewers",
    "urls": ["https://homes.chefthi.hackclub.app"]
  }
}
```

Worker endpoints:

```text
GET  /api/projects/pending
POST /api/projects/:id/status
POST /api/projects/:id/complete
POST /api/sensors
```

The `POST` body is compact JSON signed with HMAC SHA256 using `HUB_SECRET`:

```text
X-Homes-Signature: <hmac_sha256_hex>
```

Completion payload includes public playback metadata:

```json
{
  "status": "completed",
  "video_path": "/local/path/output.mp4",
  "video_url": "https://54-162-84-165.sslip.io/videos/file.mp4",
  "videoUrl": "https://54-162-84-165.sslip.io/videos/file.mp4",
  "size_bytes": 1603736,
  "duration_seconds": 20,
  "width": 1080,
  "height": 1920,
  "fps": 30,
  "codec": "h264",
  "engine_id": "videolm-engine-1"
}
```

## MCP Surface

MCP lives in the HOMES Hub. HOMES-Engine is the worker/render side. The Hub MCP tools expected by the Engine workflow are:

```text
create_engine_job
get_engine_job
list_engine_jobs
retry_engine_job
get_engine_health
list_engine_outputs
get_engine_video_url
test_notify
```

Compatibility tools maintained by the Hub:

```text
create_engine_video_job
get_engine_status
publish_engine_artifact
get_mobile_status
send_mobile_command
get_hardware_capabilities
```

## Experimental Modules

The repository also includes exploratory modules that are not the reviewer-critical path:

- `core/modules/trend_intelligence.py`: RSS trend scan -> generated script queue. Requires `profile.json` and Gemini.
- `core/modules/skill_tree.py`: local XP/quest tracker in `output/skills_state.json`.
- `core/modules/rev_ops.py`: mock channel metrics plus Gemini strategy insight.
- `core/queue_handler.py`: JSON/n8n queue scaffold; local processing path is a placeholder.

These are kept as internal experiments. The shipped product surface is the terminal video worker, Hub integration, VideoLM render path, and NotebookLM bridge.

## Roadmap

1. **Runtime solidification:** register video/Hub/NotebookLM as first-class capabilities, expose capability lists to the Hub, and route module execution through policy checks.
2. **Agent layer:** event bus, task graph, browser operator, shell guardrails, and memory briefs.
3. **Ambient and physical layer:** Termux/edge adapters, voice command router, MQTT/HMAC bridge, ESP32/sensor capabilities, and safe-mode policies.
4. **Ecosystem:** external module SDK, reusable recipes, capability catalog, and third-party profile packs.

## Project Structure

- `core/`: The heart of the engine. Contains the video maker, TTS handlers, and branding loaders.
- `branding/`: Directory for creator profiles (colors, logos, and style guidelines).
- `assets/`: Local storage for b-rolls, fonts, and generated imagery.
- `scripts/`: Utility tools for benchmarking system performance and verifying environment secrets.
- `queue/`: JSON-based system for asynchronous task management.
- `integration/`: Hub worker and legacy Hub poller.
- `docs/`: integration notes and dashboard guidance.

## Installation & Setup

While optimized for Termux, HOMES Engine can run on any Linux-based system with FFmpeg installed.

1. **Environment Setup:**
   ```bash
   bash setup.sh
   ```
2. **Configuration:**
   Rename `.env.example` to `.env`. The default renderer is the hosted VideoLM VM. Add a `GEMINI_API_KEY` only if you want AI script/TTS generation locally.
3. **Execution:**
   ```bash
   python3 main.py
   ```

Worker deployment example:

```bash
git pull origin main
python3 -m integration.worker
```

Required worker environment:

```env
HOMES_HUB_URL=https://homes.chefthi.hackclub.app
HUB_SECRET=replace_with_shared_hub_secret
ENGINE_ID=videolm-engine-1

VIDEOLM_URL=https://54-162-84-165.sslip.io
VIDEOLM_POLL_INTERVAL=5
VIDEOLM_POLL_TIMEOUT=900
```

## Development Environment

This project began in a mobile development setup:

- **Editor:** Acode
- **Terminal:** Termux
- **Hardware target:** ARM64 mobile devices and small Linux VMs

The current reship target is a reliable hosted reviewer path backed by the VideoLM VM and HOMES Hub MCP.
