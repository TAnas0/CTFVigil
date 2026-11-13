# CTFVigil Product & Feature Roadmap

This document outlines the planned feature roadmap, product vision, and architectural ideas for **CTFVigil**.

---

## 🎯 Phase 1: Core Automation (Closing Out)

- [x] **CTFtime Feed Integration**: Asynchronous API client fetching upcoming events.
- [x] **CLI Flag Converter**: Flexible command parsing (`!ctfs --limit 5 --online`).
- [x] **Individual Reaction Tracking**: Sending events as individual embed messages to support reaction listeners (`🎯` target acquisition).
- [x] **Background Processing Stack**: Celery + Redis architecture for offloading async background tasks outside Discord's event loop.
- [x] **Packaging & Testing**: Modern `pyproject.toml` setuptools layout and comprehensive `pytest` coverage.

### 🔧 Phase 1 Close-Out: Quality & Infrastructure

- [x] **Wire up Celery tasks**: Implement real logic in `sync_ctftime_events_task` — call `CTFTimeClient`, cache results in Redis, and push a digest to a configurable Discord channel. Replace all `print()` stubs with structured output.
- [ ] **Async-ify `CTFdClient`**: Migrate from `requests` (sync) to `aiohttp` (async) to match `CTFTimeClient` and avoid blocking the Discord event loop when bot commands invoke CTFd probes.
- [x] **Celery Beat periodic schedule**: Configure a periodic task in `celery_app.py` (e.g. daily CTFtime digest) so the beat scheduler actually fires something meaningful.
- [x] **Persist Celery beat schedule**: Move the beat schedule file from `/tmp/celerybeat-schedule` (lost on restart) to a named Docker volume.
- [x] **Pin Docker base image**: Replace `FROM python:3.12-slim` floating tag with a pinned digest for reproducible, auditable builds.
- [x] **Container healthchecks**: Add `HEALTHCHECK` directives to the `bot` and `worker` Compose services (currently only `redis` has one).
- [x] **CI/CD pipeline**: Add a GitHub Actions workflow running `pytest`, a `ruff` lint check, and a Docker build validation on every pull request.
- [x] **Bot command test layer**: Add `pytest` tests for the Discord command layer (`!ctfs`, `!track`, `!scoreboard`) using mocked `discord.py` contexts.
- [x] **Help message**: Write a proper `!help` embed detailing commands, flags, reaction targets, and usage examples.

---

## ⚔️ Phase 2: CTF Campaign & War-Room Operations

- [ ] **Automated Category & Channel Provisioning**:
  - Automatically create a Discord Category when a CTF target (`🎯`) is acquired.
  - Create dedicated `#announcements`, `#general`, and challenge-specific channels/threads.
- [ ] **Challenge Claiming (`!claim`)**:
  - Track who is currently working on specific challenges to eliminate duplicated effort.
- [ ] **Note & Artifact Aggregation (`!note`)**:
  - Convert marked Discord messages into a single aggregated writeup/notes document per challenge.
- [ ] **Reminders & Countdown Alerts**:
  - Automated background task dispatching alerts at **T-24h** and **T-1h** before event kickoff.
- [ ] **Post-Event Archiving**:
  - Automated category archiving/cleanup upon competition conclusion.

---

## 🏛️ Phase 3: Deep CTFd Platform Integration

- [ ] **CTFd Live Scoreboard Scraper**:
  - Periodic polling of `/api/v1/scoreboard` to post real-time solve announcements.
- [ ] **Challenge Sync (`/api/v1/challenges`)**:
  - Automatically pull newly released challenges during live CTF events and generate Discord threads.
- [ ] **Automated Bot User Registration**:
  - Admin-token or self-registration workflows to allow the bot to query authenticated endpoints.

---

## 🦉 Persona & Branding Ideas

- **Kernel / Military Persona**: Option for military-style communication (`[SITREP: Operation HackTheBox commences in 1 hour]`, `"Flag intercepted and verified by Team Kernel"`).
- **Owl / Sentinel Theme**: Vigilant monitoring theme for CTF alerts and feed updates.

---

## 💡 Competitor & Reference Projects

- [NullCTF](https://github.com/NullPxl/NullCTF): Discord bot providing CTF tools for team collaboration.
- [OvisBot](https://github.com/cybermouflons/ovisbot): CTF team Discord management bot.
- [SecGen](https://github.com/cliffe/SecGen): Automated Security VM generator.
