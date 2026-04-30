# VideoLM Engine Dashboard Guide

This guide describes the React dashboard that VideoLM should expose for HOMES Engine and reviewers.

The dashboard should be the safe hosted surface for testing the HOMES pipeline without requiring a local install, API quota, Termux, FFmpeg, or direct shell access.

## Primary URL

```text
https://54-162-84-165.sslip.io/engine-demo
```

## Product Shape

The page is not a marketing landing page. It is an operational dashboard.

The first screen should show:

- service health;
- renderer availability;
- public demo gallery;
- one deterministic render action;
- NotebookLM video action;
- current jobs/status;
- final MP4 player when a job completes.

The terminal remains the identity of HOMES Engine. The React dashboard exists so reviewers can test the hosted system safely.

## Recommended Layout

Use a dense, utilitarian layout:

```text
┌─────────────────────────────────────────────────────────────┐
│ HOMES Engine Demo                         Health: Online     │
│ VideoLM: https://54-162-84-165.sslip.io                     │
├─────────────────────┬───────────────────────────────────────┤
│ Actions             │ Current Job                           │
│ - Generate Demo     │ status / progress / stage              │
│ - NotebookLM Video  │ video player or logs                   │
│ - Test Notify       │                                       │
├─────────────────────┴───────────────────────────────────────┤
│ Gallery: pre-rendered MP4s                                  │
└─────────────────────────────────────────────────────────────┘
```

Avoid a hero page. The dashboard should immediately expose controls and video outputs.

## Core Cards

### 1. Health Card

Call:

```http
GET /api/engine/health
GET /api/video/demo/health
GET /api/engine/manifest
```

Show:

- `status`;
- service name;
- base URL;
- timestamp;
- max upload size;
- max images per render;
- queue concurrency.

### 2. Deterministic Demo Render

This is the main reviewer button.

Button label:

```text
Generate demo video
```

It should call:

```http
POST /api/video/demo/assemble
```

Use deterministic hosted assets, not Gemini/Pollinations at review time.

Required multipart fields:

```text
audio       file
images      file[]
script      string
projectId   string
bgMusicId   optional string
bgMusic     optional file
duration    optional number|string
```

Expected response:

```json
{
  "projectId": "engine_demo_123",
  "videoUrl": "/videos/engine_demo_123.mp4",
  "statusUrl": "https://54-162-84-165.sslip.io/api/video/engine_demo_123/status"
}
```

Then poll:

```http
GET /api/video/{projectId}/status
```

Status shape:

```json
{
  "status": "processing",
  "progress": 34,
  "stage": "rendering_clips",
  "currentFrame": null,
  "currentClip": 2,
  "totalClips": 8,
  "videoUrl": "/videos/engine_demo_123.mp4",
  "error": null
}
```

Completed shape:

```json
{
  "status": "completed",
  "progress": 100,
  "stage": "completed",
  "videoUrl": "/videos/engine_demo_123.mp4",
  "videoPath": "/videos/engine_demo_123.mp4",
  "error": null
}
```

When completed, resolve relative URLs with the VideoLM base URL:

```ts
const absoluteVideoUrl = videoUrl.startsWith("http")
  ? videoUrl
  : `${baseUrl}${videoUrl}`;
```

### 3. NotebookLM Video

This is the research/video generation action.

Call:

```http
POST /api/engine/notebooklm/video
```

Multipart fields:

```text
projectId      optional
title          optional
theme          optional
urls           optional, repeatable HTTPS URL(s)
assets         optional, file[]
style          classic | whiteboard | watercolor | anime | kawaii | retro_print | heritage | paper_craft | custom
stylePrompt    required if style=custom
liveResearch   optional
notebookId     optional existing NotebookLM notebook id
profileId      default
```

Example:

```bash
curl -X POST https://54-162-84-165.sslip.io/api/engine/notebooklm/video \
  -F "projectId=engine_hackclub_demo" \
  -F "theme=Hack Club community" \
  -F "urls=https://hackclub.com/" \
  -F "style=paper_craft"
```

Expected submit response:

```json
{
  "projectId": "engine_hackclub_demo",
  "status": "submitted",
  "notebookLM": "video",
  "pollUrl": "https://54-162-84-165.sslip.io/api/research/engine_hackclub_demo/download"
}
```

Poll:

```http
GET /api/research/{projectId}/download
```

Processing:

```json
{
  "status": "processing",
  "message": "Result is still being generated in Google Studio."
}
```

Completed:

```json
{
  "status": "completed",
  "videoUrl": "/videos/research_engine_hackclub_demo.mp4",
  "type": "video",
  "cached": true
}
```

Important behavior:

- If a research MP4 is already generated, return the cached result immediately.
- Do not re-trigger NotebookLM work during polling.
- Polling should never hang without a JSON response.

### 4. Public Gallery

Show at least three pre-rendered videos.

Required known public render:

```text
/videos/research_community_1777566704645.mp4
```

Also include:

```text
/videos/research_codex_notebooklm_hackclub.mp4
```

Render links should use the base URL from `/api/engine/manifest`, not hardcoded strings in React components.

## React Component Structure

Suggested files:

```text
src/pages/EngineDemo.tsx
src/components/engine/HealthPanel.tsx
src/components/engine/DemoRenderPanel.tsx
src/components/engine/NotebookLMPanel.tsx
src/components/engine/JobProgress.tsx
src/components/engine/VideoGallery.tsx
src/lib/engineApi.ts
```

## `engineApi.ts`

Use one API helper so endpoint paths do not spread through the app.

```ts
const FALLBACK_BASE_URL = "https://54-162-84-165.sslip.io";

export type EngineManifest = {
  baseUrl: string;
  publicEndpoints: Record<string, any>;
  capabilities: Record<string, any>;
};

export async function getManifest(): Promise<EngineManifest> {
  const res = await fetch("/api/engine/manifest");
  if (!res.ok) throw new Error(`Manifest failed: ${res.status}`);
  return res.json();
}

export async function getDemoHealth() {
  const res = await fetch("/api/video/demo/health");
  if (!res.ok) throw new Error(`Demo health failed: ${res.status}`);
  return res.json();
}

export function resolveVideoUrl(baseUrl: string, videoUrl: string) {
  if (!videoUrl) return "";
  return videoUrl.startsWith("http") ? videoUrl : `${baseUrl}${videoUrl}`;
}

export async function pollVideoStatus(projectId: string) {
  const res = await fetch(`/api/video/${projectId}/status`);
  if (!res.ok) throw new Error(`Status failed: ${res.status}`);
  return res.json();
}

export async function pollNotebookLM(projectId: string) {
  const res = await fetch(`/api/research/${projectId}/download`);
  if (!res.ok) throw new Error(`NotebookLM poll failed: ${res.status}`);
  return res.json();
}
```

## UI Controls

### Demo Render Panel

Controls:

- Theme select:
  - Hack Club community
  - HOMES public dashboard
  - Terminal-first creator workflow
- Generate button.
- Progress bar.
- Stage label.
- MP4 player.

Rules:

- Disable button while a job is running.
- Show queue message if server returns queued/processing.
- Store last successful video URL in local state.

### NotebookLM Panel

Controls:

- `projectId` text input.
- `title` text input.
- `theme` text input.
- URLs textarea, one URL per line.
- asset upload.
- style select:
  - `classic`
  - `whiteboard`
  - `watercolor`
  - `anime`
  - `kawaii`
  - `retro_print`
  - `heritage`
  - `paper_craft`
  - `custom`
- `stylePrompt` textarea, shown only when style is `custom`.
- `liveResearch` checkbox.
- `notebookId` input.
- `profileId` input, default `default`.

Validation:

- `stylePrompt` is required when style is `custom`.
- URLs must start with `https://`.
- Do not require URLs if assets or notebookId is provided.

## Job Progress Display

Show:

```text
Status: processing
Progress: 34%
Stage: rendering_clips
Clip: 2 / 8
```

If `error` exists, show a clear error block with the raw message.

If a job is slow, keep polling but show:

```text
Still working. Long research/render jobs can take a few minutes.
```

## Error Handling

Use these user-facing states:

- `offline`: health/manifest failed;
- `queued`: job accepted but not started;
- `processing`: polling active;
- `completed`: video player visible;
- `failed`: server returned error;
- `timeout`: frontend polling timed out.

For failed jobs, show:

- status;
- stage;
- error;
- projectId;
- retry button.

## Production Guardrails

VideoLM VM limits:

- one heavy render at a time;
- avoid live long-form render as the main reviewer path;
- keep pre-rendered gallery as fallback;
- clean `/videos` and temp files regularly;
- surface queue state clearly.

## HOMES Hub Integration

The dashboard can also show Engine connectivity through the Hub.

Hub endpoints:

```text
GET  https://homes.chefthi.hackclub.app/api/projects/pending
POST https://homes.chefthi.hackclub.app/api/projects/:id/status
POST https://homes.chefthi.hackclub.app/api/projects/:id/complete
POST https://homes.chefthi.hackclub.app/api/sensors
```

The POSTs are done by HOMES Engine, not by the browser, because they require HMAC.

Show Hub state read-only in the React dashboard if an endpoint is public:

- pending count;
- current job id;
- latest engine status;
- last completed video.

## What The Reviewer Should Be Able To Do

1. Open `/engine-demo`.
2. See VideoLM and Engine health.
3. Play pre-rendered videos.
4. Click `Generate demo video`.
5. Watch progress/stage update.
6. Play the final MP4.
7. Submit a NotebookLM video job with a style.
8. Poll and play cached/completed NotebookLM videos.

If all eight work, the dashboard is good enough for ship.

