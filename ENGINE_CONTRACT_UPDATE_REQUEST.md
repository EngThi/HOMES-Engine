# Engine Contract Update Request

The current Engine contract is behind the VideoLM product surface.

VideoLM now exposes more than the original demo assembly and NotebookLM video path. The Engine should treat the manifest as a living contract, inspect the current API/UI behavior, ask clarifying questions when a capability is ambiguous, and update its integration so it can use the newer Studio features instead of hardcoding only the older video flow.

## Current Stable Base

```text
https://54-162-84-165.sslip.io
```

Primary discovery endpoint:

```text
GET /api/engine/manifest
```

The Engine should fetch this on startup and should not rely on old tunnel URLs, stale docs, or a fixed list of artifact types.

## Known Contract Gaps

The Engine manifest currently advertises the older public bridge and NotebookLM video flow, but VideoLM now supports more NotebookLM Studio outputs:

- Audio overview
- Video overview
- Infographic PNG
- Report
- Quiz
- Flashcards
- Mind map
- Slides / slide deck PDF
- Data table

The Factory flow also has a newer visual source:

- Fast image API storyboard images
- NotebookLM infographic images as Factory scene assets
- Image aspect options: landscape, portrait, square

These newer capabilities should be represented in the Engine contract so an external Engine can discover and use them without reading frontend code.

## What The Engine Should Do

1. Fetch `GET /api/engine/manifest`.
2. Compare advertised capabilities with the current VideoLM UI and API routes.
3. Ask questions when behavior is not explicit, especially around:
   - Which Studio artifacts should be public vs authenticated.
   - Which artifacts require NotebookLM profile/cookies.
   - Which fields are required per artifact type.
   - Expected output format per artifact.
   - Polling behavior and timeout expectations.
   - Whether Factory infographic assets should be exposed through the Engine manifest.
4. Update the manifest/contract so it includes all supported artifact types and their request fields.
5. Keep the Engine integration generic: accept an artifact type and options instead of special-casing only `video`.

## Questions For VideoLM

Please answer these before the Engine locks the new generic contract:

1. Which artifact types are officially supported today?
2. Which artifact types are public/demo-safe without login?
3. Which artifact types require NotebookLM cookies/profile?
4. Which artifact types require an existing `notebookId`?
5. Which artifact types can be created from only `urls`?
6. Which artifact types can be created from uploaded `assets`?
7. For each artifact type, what is the exact final output field?
   - `videoUrl`
   - `audioUrl`
   - `imageUrl`
   - `pdfUrl`
   - `jsonUrl`
   - `htmlUrl`
   - `downloadUrl`
   - `artifactUrl`
8. Does `GET /api/research/:projectId/download` return a single artifact or can it return multiple artifacts?
9. Does the polling response include `status`, `progress`, `stage`, `type`, and `artifactType` for every artifact?
10. What are the expected timeouts per artifact type?
11. Should the Engine always use `format=brief` for reviewer-safe NotebookLM jobs?
12. What image aspect values are accepted by the Factory infographic asset flow?
13. Are generated infographic images public files under `/images`, `/assets`, `/videos`, or another route?
14. Should Factory infographic assets be usable as normal `images[]` for `/api/video/demo/assemble`?
15. Which generated URLs are stable enough for reviewer playback/download?

## Required Manifest Shape

The manifest should not only say a feature exists. It should describe how an external Engine calls it.

Suggested top-level shape:

```json
{
  "name": "VideoLM Factory",
  "version": "2026-05-xx",
  "baseUrl": "https://54-162-84-165.sslip.io",
  "capabilities": {
    "publicDemoAssembly": true,
    "notebookLMStudioArtifacts": true,
    "factoryInfographicAssets": true
  },
  "artifactTypes": {
    "video": {
      "public": true,
      "requiresProfile": false,
      "pollEndpoint": "/api/research/{projectId}/download",
      "outputFields": ["videoUrl", "videoPath"],
      "contentTypes": ["video/mp4"],
      "expectedTimeoutSeconds": 900
    }
  }
}
```

Each artifact type should declare:

```text
id
label
public
requiresAuth
requiresNotebookLMProfile
requiresNotebookId
acceptedInputs
requiredFields
optionalFields
triggerEndpoint
pollEndpoint
outputFields
contentTypes
expectedTimeoutSeconds
stablePublicUrl
```

## Endpoints That Need Contract Coverage

Current NotebookLM Studio path:

```text
POST /api/research/:projectId/sources
POST /api/research/:projectId/source-files
POST /api/research/:projectId/trigger
GET  /api/research/:projectId/download
```

The `trigger` endpoint supports multiple artifact types and options. The contract should describe each one.

Factory infographic asset path:

```text
POST /api/research/:projectId/factory-infographic-assets
GET  /api/research/factory-infographic-assets/:jobId
```

This path is used by Factory to generate NotebookLM infographic PNGs as storyboard images before FFmpeg assembly.

## Suggested Manifest Additions

Add capabilities similar to:

```json
{
  "notebookLMStudioArtifacts": true,
  "notebookLMArtifactTypes": [
    "audio",
    "video",
    "infographic",
    "report",
    "quiz",
    "flashcards",
    "mindmap",
    "slides",
    "data-table"
  ],
  "factoryInfographicAssets": true,
  "factoryImageAspects": ["landscape", "portrait", "square"]
}
```

Add endpoint descriptions for:

- `triggerNotebookLMArtifact`
- `pollNotebookLMArtifact`
- `factoryInfographicAssetsStart`
- `factoryInfographicAssetsPoll`

## Backwards Compatibility Requirements

Do not break the existing reviewer-safe video contract:

```text
POST /api/video/demo/assemble
GET  /api/video/:projectId/status
GET  /api/engine/health
GET  /api/engine/manifest
POST /api/engine/notebooklm/video
GET  /api/research/:projectId/download
```

The Engine still depends on these rules:

- `videoUrl` may be relative, for example `/videos/file.mp4`.
- Relative artifact URLs must be resolved against `baseUrl`.
- Public MP4s are served from `/videos/*.mp4`.
- The UI/Engine must validate public MP4s with `HEAD 200/206` and `content-type: video/mp4`.
- Do not report completed video jobs to the Hub without a public `video_url` / `videoUrl`.
- Do not return frontend HTML from `/api/...` routes.

## Engine-Side Implementation Target

Once VideoLM publishes the richer manifest, the Engine should add generic capabilities like:

```text
production.studio_artifact_submit
production.studio_artifact_poll
production.factory_infographic_assets_submit
production.factory_infographic_assets_poll
```

The input should be generic:

```json
{
  "project_id": "demo",
  "artifact_type": "infographic",
  "urls": ["https://hackclub.com/"],
  "assets": [],
  "style": "paper_craft",
  "format": "brief",
  "aspect": "portrait",
  "profile_id": "default",
  "notebook_id": ""
}
```

The output should be normalized:

```json
{
  "status": "completed",
  "project_id": "demo",
  "artifact_type": "infographic",
  "artifact_url": "https://54-162-84-165.sslip.io/path/file.png",
  "content_type": "image/png",
  "metadata": {}
}
```

Video remains a premium artifact type, but not the only one.

## Important Integration Rule

The Engine should not assume VideoLM is only a video renderer now. It is a Studio artifact factory plus a video assembly pipeline. If the Engine needs a field or option that is not in the manifest, it should ask for it and update the contract rather than silently ignoring the feature.

## Acceptance Test

This contract update is ready when:

1. `GET /api/engine/manifest` lists all Studio artifact types.
2. Each artifact type has required fields, optional fields, output fields, poll endpoint, timeout, and content type.
3. The old demo video path still works.
4. The Engine can submit a generic artifact request without hardcoding only `video`.
5. The Engine can poll the generic artifact request.
6. The Engine can normalize the final URL into `artifact_url`.
7. Video artifacts still normalize into `video_url` / `videoUrl` for Hub compatibility.
8. Public artifacts pass `HEAD 200/206` and correct content-type validation before being shown as completed.
9. The manifest documents whether each artifact is public, authenticated, or NotebookLM-profile-only.
10. The Hub dashboard can display artifact type, status, progress, final URL, and download availability without special-casing only videos.
