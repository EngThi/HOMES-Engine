# VideoLM Manifest Update For HOMES-Engine

This is the file to send to VideoLM when asking them to update `/api/engine/manifest`.

The goal is simple: HOMES-Engine must discover VideoLM as a full artifact factory, not only as the old video renderer. The manifest should become the source of truth for every public/authenticated artifact the Engine can request, poll, validate, and report back to the HOMES Hub.

## Stable Base

```text
https://54-162-84-165.sslip.io
```

Required discovery endpoint:

```text
GET https://54-162-84-165.sslip.io/api/engine/manifest
```

The Engine should fetch this manifest on startup and should not rely on stale docs, temporary tunnel URLs, or frontend source code.

## Why This Update Is Needed

The current public manifest mostly describes:

- public demo video assembly;
- authenticated video assembly;
- NotebookLM video submission/polling;
- health and music endpoints.

But the VideoLM product surface now appears to include more Studio outputs and Factory visual workflows:

- audio overview;
- video overview;
- infographic PNG;
- report;
- quiz;
- flashcards;
- mind map;
- slides / slide deck PDF;
- data table;
- fast image API storyboard images;
- NotebookLM infographic images as Factory scene assets;
- image aspect options: `landscape`, `portrait`, `square`.

The Engine needs those features in the manifest so it can integrate generically instead of hardcoding only `video`.

## Do Not Break Existing Contract

These existing routes must keep working:

```text
GET  /api/engine/health
GET  /api/engine/manifest
POST /api/video/demo/assemble
GET  /api/video/:projectId/status
POST /api/engine/notebooklm/video
GET  /api/research/:projectId/download
```

Existing rules the Engine depends on:

- `videoUrl` may be relative, for example `/videos/file.mp4`.
- Relative URLs must resolve against manifest `baseUrl`.
- Public MP4s are served from `/videos/*.mp4`.
- UI/Engine must validate public MP4s with `HEAD 200/206` and `content-type: video/mp4`.
- API routes must return JSON, not frontend HTML.
- Completed video jobs reported to HOMES Hub need public `video_url` / `videoUrl`, not only a local `video_path`.

## Required Manifest Additions

Add a top-level artifact contract. Example shape:

```json
{
  "name": "VideoLM Factory",
  "version": "2026-05-03",
  "baseUrl": "https://54-162-84-165.sslip.io",
  "capabilities": {
    "publicDemoAssembly": true,
    "authenticatedAssembly": true,
    "notebookLMResearch": true,
    "notebookLMStudioArtifacts": true,
    "factoryInfographicAssets": true
  },
  "artifactTypes": {
    "video": {
      "label": "Video overview",
      "public": true,
      "requiresAuth": false,
      "requiresNotebookLMProfile": false,
      "requiresNotebookId": false,
      "acceptedInputs": ["urls", "assets", "script", "audio", "images"],
      "requiredFields": [],
      "optionalFields": ["projectId", "title", "theme", "style", "format", "profileId", "notebookId"],
      "triggerEndpoint": "/api/engine/notebooklm/video",
      "pollEndpoint": "/api/research/{projectId}/download",
      "outputFields": ["videoUrl", "videoPath", "artifactUrl"],
      "contentTypes": ["video/mp4"],
      "expectedTimeoutSeconds": 900,
      "stablePublicUrl": true
    },
    "infographic": {
      "label": "Infographic PNG",
      "public": true,
      "requiresAuth": false,
      "requiresNotebookLMProfile": true,
      "requiresNotebookId": false,
      "acceptedInputs": ["urls", "assets", "theme"],
      "requiredFields": ["projectId"],
      "optionalFields": ["style", "stylePrompt", "aspect", "profileId", "notebookId"],
      "triggerEndpoint": "/api/research/{projectId}/trigger",
      "pollEndpoint": "/api/research/{projectId}/download",
      "outputFields": ["imageUrl", "artifactUrl", "downloadUrl"],
      "contentTypes": ["image/png"],
      "expectedTimeoutSeconds": 900,
      "stablePublicUrl": true
    }
  }
}
```

Every artifact type should declare:

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

## Artifact Types To Cover

Please confirm and document every supported type:

```text
audio
video
infographic
report
quiz
flashcards
mindmap
slides
data-table
```

If the exact API uses different names, publish both:

```json
{
  "id": "data-table",
  "aliases": ["data_table", "table"]
}
```

## Studio Endpoints To Document

Current NotebookLM Studio flow:

```text
POST /api/research/:projectId/sources
POST /api/research/:projectId/source-files
POST /api/research/:projectId/trigger
GET  /api/research/:projectId/download
```

The manifest should say:

- exact body for `/trigger`;
- valid `type` / `artifactType` values;
- valid `style` values;
- valid `format` values;
- which fields are required per artifact;
- whether result is one artifact or multiple artifacts;
- which output field contains the final URL;
- expected content type;
- polling response shape.

## Factory Infographic Asset Endpoints To Document

Factory infographic asset flow:

```text
POST /api/research/:projectId/factory-infographic-assets
GET  /api/research/factory-infographic-assets/:jobId
```

The manifest should say:

- required request fields;
- valid `aspect` values;
- whether output URLs are public;
- output route prefix;
- whether generated images can be used directly as `images[]` in `/api/video/demo/assemble`;
- polling response shape;
- expected timeout.

Expected aspect values if supported:

```text
landscape
portrait
square
```

## Generic Engine Integration Target

After this manifest exists, HOMES-Engine should add generic capabilities like:

```text
production.studio_artifact_submit
production.studio_artifact_poll
production.factory_infographic_assets_submit
production.factory_infographic_assets_poll
```

Generic submit input:

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

Normalized Engine output:

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

For video artifacts, the Engine must additionally keep Hub compatibility:

```json
{
  "video_url": "https://54-162-84-165.sslip.io/videos/file.mp4",
  "videoUrl": "https://54-162-84-165.sslip.io/videos/file.mp4"
}
```

## Questions VideoLM Needs To Answer

Please answer these explicitly:

1. Which artifact types are officially supported today?
2. Which artifact types are public/demo-safe without login?
3. Which artifact types require NotebookLM profile/cookies?
4. Which artifact types require an existing `notebookId`?
5. Which artifact types can be created from only `urls`?
6. Which artifact types can be created from uploaded `assets`?
7. Which artifact types can be created from text/theme only?
8. Does `/api/research/:projectId/download` return one artifact or multiple artifacts?
9. What is the final output URL field for each artifact type?
10. Does every polling response include `status`, `progress`, `stage`, `type`, and `artifactType`?
11. What are the expected timeouts per artifact type?
12. Should reviewer-safe NotebookLM jobs default to `format=brief`?
13. What `style` values are accepted for non-video artifacts?
14. What `aspect` values are accepted by Factory infographic assets?
15. Where are generated infographic images served from?
16. Can Factory infographic assets be reused as scene images for video assembly?
17. Which generated URLs are stable enough for reviewer playback/download?

## Acceptance Test

This manifest update is ready when:

1. `GET /api/engine/manifest` lists all Studio artifact types.
2. Each artifact type declares required fields, optional fields, endpoint, output fields, timeout, and content type.
3. The old public video demo path still works.
4. The old NotebookLM video path still works.
5. A generic artifact request can be submitted without hardcoding only `video`.
6. A generic artifact request can be polled.
7. The final result can normalize into `artifact_url`.
8. Video artifacts still normalize into `video_url` / `videoUrl`.
9. Public artifacts pass `HEAD 200/206` and correct content-type validation.
10. The HOMES Hub dashboard can display artifact type, status, progress, final URL, and download availability without special-casing only MP4 video.

## Current Verified Video Baseline

This known public render was verified:

```text
https://54-162-84-165.sslip.io/videos/terminal_dash_retest_1777720992_1777722387267.mp4
```

Validation:

```text
HEAD 200
content-type: video/mp4
content-length: 783379
```

Do not remove the existing `/videos/*.mp4` behavior while expanding the manifest.
