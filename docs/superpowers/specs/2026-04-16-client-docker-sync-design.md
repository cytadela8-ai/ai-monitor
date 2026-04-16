# Client Docker Sync Design

## Goal

Add a dedicated Docker image for client-mode sync, publish it to GHCR, and surface a copyable
Docker launch script in the admin panel so remote machines can push one snapshot on demand
without cloning the repo or setting up cron.

## Design

- Keep `ai-monitor-sync` as the single client entry point.
- Add `Dockerfile.client` with `ai-monitor-sync` as the default command.
- Publish two images from GitHub Actions:
  - `ghcr.io/<owner>/<repo>` for the server
  - `ghcr.io/<owner>/<repo>-client` for the client
- Add `AI_MONITOR_CLIENT_IMAGE` to server config so the admin UI can render the correct client
  image reference at runtime.
- Generate client setup instructions on the server side:
  - one `docker run` command
  - one full bash launcher script
  - a hidden-key version for later viewing after creation
- Remove cron guidance from the admin panel for now.

## Verification

- admin API tests for setup payloads
- dashboard test for client image exposure
- Playwright check that the admin panel renders the Docker script
- full `pytest`, `ruff`, and `ty` verification
