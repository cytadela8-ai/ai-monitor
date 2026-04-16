# Dotenv Autoload, Docker Packaging, And GHCR Publishing Design

## Goal

Make AI Monitor automatically load a local `.env` file, add a server-only Docker image for the
main instance, and publish that image to GitHub Container Registry from GitHub Actions.

## Non-Goals

- No container image for `ai-monitor-sync`
- No docker-compose requirement
- No deployment-specific orchestration manifests
- No release automation beyond building and publishing the image

## User Requirements

- `ai-monitor-server` should automatically load variables from `.env`
- `ai-monitor-sync` should also support `.env` automatically for consistency
- The project should include a server-ready Dockerfile
- GitHub Actions should build and push to GHCR
- Publishing should happen for:
  - pushes to `main`
  - version tags like `v1.2.3`
- The workflow should use pinned action SHAs

## Runtime Configuration

Use `python-dotenv` to load `.env` before either config object reads environment variables.

Rules:

- if `.env` exists in the working directory, load it automatically
- explicit process environment variables still win over `.env`
- both `AppConfig.from_env()` and `ClientConfig.from_env()` get the same behavior

This keeps local development, cron-based sync, and Docker-based server runs consistent.

## Docker Image

Add a single server-oriented `Dockerfile`.

Properties:

- base image: Python 3.13 slim
- install project and runtime dependencies
- default command: `ai-monitor-server`
- expose port `8000`
- keep the image simple and avoid bundling client-specific runtime behavior

Expected runtime model:

- mount or inject `.env`
- optionally mount log directories if the server machine should ingest local Codex and Claude data
- optionally mount a persistent path for the SQLite database

## GitHub Actions Publishing

Add one workflow to build and publish the Docker image to GHCR.

Triggers:

- push to `main`
- push tags matching `v*`

Behavior:

- build the Docker image
- publish to `ghcr.io/<owner>/<repo>`
- tag images for:
  - `main`
  - commit SHA
  - semver tag on release tags
  - `latest` on `main`

Do not publish on pull requests.

## Version And Pinning Sources

Use current official versions:

- `python-dotenv` `1.2.2` from PyPI
- `actions/checkout` `v6.0.2`
- `docker/login-action` `v3.7.0`
- `docker/metadata-action` `v5.10.0`
- `docker/setup-buildx-action` `v4.0.0`
- `docker/build-push-action` `v6.19.0`

Workflow actions must be pinned to immutable SHAs with version comments.

## Files

### New files

- `Dockerfile`
- `.dockerignore`
- `.github/workflows/publish-image.yml`
- `docs/superpowers/specs/2026-04-16-dotenv-docker-ghcr-design.md`
- `docs/superpowers/plans/2026-04-16-dotenv-docker-ghcr.md`

### Modified files

- `pyproject.toml`
- `ai_monitor/config.py`
- `README.md`
- `DEV.md`
- `.env.example`
- `tests/conftest.py`
- new config-focused tests as needed

## Testing Strategy

### Config Tests

- `.env` values load automatically when the process env is empty
- explicit process env values override `.env`
- both server and client config constructors benefit from the same autoload behavior

### Packaging Checks

- Dockerfile exists and uses the server entry point
- workflow file exists and references pinned SHAs

### Verification

- `pytest`
- `ruff check`
- `ty check`

## Docs

Update docs to cover:

- automatic `.env` loading
- Docker build and run examples
- GHCR image naming and publishing behavior
