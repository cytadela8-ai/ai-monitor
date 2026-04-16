# Client Docker Sync Implementation Plan

- [ ] Add tests for admin setup payloads and dashboard client-image wiring
- [ ] Add server-side client setup generation and `AI_MONITOR_CLIENT_IMAGE` config
- [ ] Update admin UI to render Docker-only setup instructions
- [ ] Add `Dockerfile.client` and `scripts/run-client-sync.sh`
- [ ] Extend GHCR publishing workflow to publish both server and client images
- [ ] Update `.env`, `.env.example`, `README.md`, and `DEV.md`
- [ ] Verify with `pytest`, `ruff`, `ty`, Docker builds, and Playwright
