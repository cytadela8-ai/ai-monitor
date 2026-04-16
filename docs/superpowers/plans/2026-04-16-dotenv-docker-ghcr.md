# Dotenv Autoload, Docker Packaging, And GHCR Publishing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add automatic `.env` loading to AI Monitor, package the server as a Docker image, and
publish the image to GitHub Container Registry from GitHub Actions.

**Architecture:** Keep runtime entry points unchanged while loading `.env` before config objects
read environment variables. Add one server-only Docker image and one GitHub Actions workflow that
publishes `main`, SHA, semver, and `latest` tags to GHCR.

**Tech Stack:** Python 3.13, python-dotenv, uv, pytest, ruff, ty, Docker, GitHub Actions

---

## File Structure

### New files

- `Dockerfile`
- `.dockerignore`
- `.github/workflows/publish-image.yml`
- `tests/test_config_env.py`

### Files to modify

- `pyproject.toml`
- `ai_monitor/config.py`
- `README.md`
- `DEV.md`
- `.env.example`

## Task 1: Add Dotenv Autoload

**Files:**
- Modify: `pyproject.toml`
- Modify: `ai_monitor/config.py`
- Create: `tests/test_config_env.py`

- [ ] **Step 1: Write failing tests for `.env` autoload and environment override behavior**
- [ ] **Step 2: Run `uv run pytest tests/test_config_env.py -q` and verify the tests fail**
- [ ] **Step 3: Add `python-dotenv==1.2.2` and load `.env` before config parsing**
- [ ] **Step 4: Re-run `uv run pytest tests/test_config_env.py -q` and verify the tests pass**

## Task 2: Add Docker Packaging

**Files:**
- Create: `Dockerfile`
- Create: `.dockerignore`

- [ ] **Step 1: Add the server-only Dockerfile with `ai-monitor-server` as the default command**
- [ ] **Step 2: Add `.dockerignore` to keep the build context clean**
- [ ] **Step 3: Review the Dockerfile for unnecessary complexity**

## Task 3: Add GHCR Publishing Workflow

**Files:**
- Create: `.github/workflows/publish-image.yml`

- [ ] **Step 1: Add a workflow that triggers on `main` and `v*` tags**
- [ ] **Step 2: Use pinned action SHAs with version comments**
- [ ] **Step 3: Publish `main`, commit SHA, semver, and `latest` tags to GHCR**

## Task 4: Update Docs And Examples

**Files:**
- Modify: `README.md`
- Modify: `DEV.md`
- Modify: `.env.example`

- [ ] **Step 1: Document automatic `.env` loading**
- [ ] **Step 2: Add Docker build and run examples**
- [ ] **Step 3: Document GHCR publishing behavior**

## Task 5: Verify The Whole Slice

**Files:**
- No new code files

- [ ] **Step 1: Run `uv run pytest -q`**
- [ ] **Step 2: Run `uv run ruff check .`**
- [ ] **Step 3: Run `uv run ty check`**
