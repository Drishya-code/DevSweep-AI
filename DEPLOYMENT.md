# DevSweep AI deployment

The repository builds a same-origin React application and FastAPI service. The public image runs in hosted mode: its only filesystem mutation API operates on per-session synthetic fixtures. The real-workspace page uses the browser File System Access API; the server receives metadata for AI suggestions and never gets a local path or file contents.

## Required configuration

Set `NEBIUS_API_KEY` as a server-side secret in the hosting provider. Create a Token Factory API key in the Nebius console. It is an inference credential, not a coding-agent token. Never set it as a `VITE_*` variable. The service uses the OpenAI-compatible `/v1/chat/completions` endpoint at `https://api.tokenfactory.nebius.com/v1/` and the configured `NEBIUS_MODEL` (default `nvidia/nemotron-3-super-120b-a12b`). Confirm the model is present in the key's available model catalog. Account access and inference permissions cannot be checked until that secret is installed.

## Run with Docker

```sh
docker build -t devsweep-ai .
docker run --rm -p 8000:8000 \
  -e NEBIUS_API_KEY=your_server_side_key \
  -v devsweep-data:/data \
  devsweep-ai
```

Open the container's HTTPS URL in deployment, or `http://localhost:8000` locally. The sample workspace data and application DB live under `/data`; mount a durable volume there. `/health` returns only a safe health status. Hosted mode hides interactive API docs and denies general scan, restore, history, and filesystem routes.

## Deploy on Render

The root `render.yaml` defines a single-instance Docker web service, `/health` check, 1 GB persistent disk at `/data`, and a server-only `NEBIUS_API_KEY` prompt. Render's persistent disks require a paid web-service plan; the Blueprint sets `starter`.

1. Sign in to Render and create a **New Blueprint Instance**.
2. Connect the existing `Drishya-code/DevSweep-AI` repository and choose branch `codex/hosted-demo-real-workspace`.
3. Review the Blueprint resources and enter the Nebius Token Factory key when Render prompts for `NEBIUS_API_KEY`. Do not add it to the repo or as a `VITE_*` value.
4. Create the Blueprint and wait for the Docker build and `/health` check to pass. Render provisions the public `onrender.com` HTTPS address.
5. Open the public URL, confirm `/health` returns `{"status":"healthy"}`, run the Nebius metadata analysis, and verify isolated sessions, preview/confirmation, undo/reset, and folder selection in a supported browser.

The GitHub branch is pushed, but no Render account/token is connected in this environment; no public deployment has been created or tested. The hosting owner must complete the dashboard flow above. Render prompts for `sync: false` secrets only during initial Blueprint creation; add or rotate secrets through the service's Environment page afterward. See [Render Blueprint documentation](https://render.com/docs/blueprint-spec), [persistent disks](https://render.com/docs/disks), and [health checks](https://render.com/docs/health-checks).

The sample demo creates a random UUID per browser profile and stores each fixture in its own directory under `DEVSWEEP_DEMO_ROOT`. Treat the session ID as a bearer identifier. Requests are size limited and the public AI analysis endpoints have a process-local per-IP rate limit. For deployments with multiple replicas, configure equivalent rate limiting at the ingress/shared gateway and use storage with the required consistency semantics. Never share one writable local volume between untrusted containers.

## Environment variables

| Variable | Purpose |
| --- | --- |
| `NEBIUS_API_KEY` | Required server-side Token Factory inference key; no mock fallback is used |
| `NEBIUS_BASE_URL` | OpenAI-compatible Token Factory endpoint; default `https://api.tokenfactory.nebius.com/v1/` |
| `NEBIUS_MODEL` | Model id enabled for the key; default retained from existing integration |
| `DEVSWEEP_HOSTED_DEMO` | `true` in the public image; enforces the hosted route allowlist |
| `DEVSWEEP_DEMO_ROOT` | Persistent per-session synthetic workspace storage; `/data/demo-workspaces` in Docker |
| `DEVSWEEP_DB_PATH` | Persistent app database path; `/data/devsweep.db` in Docker |
| `BACKEND_HOST` | `0.0.0.0` only for hosted container deployment; local default stays loopback |
| `BACKEND_PORT` / `PORT` | Listen port; platform `PORT` takes precedence |
| `DEVSWEEP_CORS_ORIGINS` | Exact allowed origins only when frontend is hosted separately; leave empty for same-origin |
| `VITE_API_BASE_URL` | Optional public API origin at frontend build time; never a secret |

## Browser folder access

Real-workspace mode requires HTTPS (or localhost) and a browser that supports `showDirectoryPicker`, currently best supported in Chromium-based browsers. The browser asks the user to select a directory and grant read/write permission. Permission can be denied, revoked, or unavailable; the app then stops and asks the user to reselect. Only relative paths, sizes, and timestamps go to Nebius. AI output is filtered against the inventoried list and a deterministic generated-artifact allowlist. After explicit confirmation, the browser moves selected files to `.devsweep-trash/<restore-id>` inside that selected directory; Undo restores them. This local mode depends on the browser tab remaining authorized and has no cross-browser backup. Other browsers can use the synthetic judge demo; a future local companion agent would need authenticated, per-folder capabilities before supporting them.

## Credential and security notes

Token Factory is documented by Nebius as an inference API with OpenAI-compatible chat completions. This code calls that inference endpoint, not a coding agent. Missing credentials produce a clear service-unavailable response; application code never silently substitutes MockProvider. Unit tests may inject test providers. The AI proposes; deterministic frontend/backend checks constrain paths and approval, and no AI output is executed as a command.

Use `.env.example` for local configuration placeholders. Do not commit `.env`, embed keys in source maps, or put secrets in browser build variables. The image's hosted route allowlist does not expose an unrestricted local-filesystem API.
