# Changelog

All notable changes to **CTFVigil** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### 🚀 Added (`feat`)
- **CTFd Live Scoreboard Command (`!scoreboard`)**: Added `!scoreboard <url>` (`!standings`, `!lb`, `!leaderboard`) command in `bot.py` to query anonymous public scoreboard standings from CTFd platforms, featuring medal badges (`🥇`, `🥈`, `🥉`) and protected endpoint handling.
- **CTFd Probing Command (`!track`)**: Added `!track <url>` (`!inspect`, `!probe`) command in `bot.py` to anonymously fingerprint CTFd target platforms and report HTTP accessibility across `/users`, `/teams`, `/challenges`, and `/scoreboard` endpoints.
- **Docker Compose Watch**: Added `develop.watch` hot-reloading rules to `docker-compose.yml` (`sync+restart` for application code and `rebuild` for `pyproject.toml`).

---

## [0.2.0] - 2026-08-30

### 🚀 Added (`feat`)
- **Pytest Unit Test Suite**: Comprehensive testing for utility modules (`ctfvigil/utils.py`) and API clients (`ctfvigil/client.py`) covering date parsing edge cases, string formatting, dynamic Discord embed rendering, and async HTTP error handling (`tests/test_utils.py`, `tests/test_client.py`).
- **Packaging & Build System**: PEP 621 / PEP 517 build configuration via `pyproject.toml` with `setuptools`, single-source `__version__` tracking in `ctfvigil/__init__.py`, and optional `dev` dependency groups.
- **Container Infrastructure**: Production-ready multi-stage `Dockerfile` running under a dedicated non-root user (`appuser`, UID `10001`) and orchestrating stack composition with `docker-compose.yml` (`redis`, `bot`, `worker`, `beat`).
- **Target Acquisition Listener**: Discord raw reaction listener (`on_raw_reaction_add`) triggering task dispatches upon `🎯` emoji reactions.
- **Documentation Suite**: Standardized testing guide (`docs/testing.md`) and product roadmap (`docs/roadmap.md`).

### 🔄 Changed (`refactor` / `style`)
- **Directory Restructuring**:
  - Isolated CTFd API interaction logic into `ctfvigil/clients/ctfd.py`.
  - Moved Celery configuration and task definitions into a dedicated `tasks/` package (`tasks/celery_app.py`, `tasks/tasks.py`).
- **CLI Flag Parser**: Standardized flag converter to `CLIFlags` supporting `--limit` and `--online` parameters with command alias support.

---

## [0.1.0] - 2026-08-29

### 🚀 Added (`feat`)
- **CTFtime API Client**: Asynchronous client `CTFTimeClient` featuring custom User-Agent headers, configurable request timeouts, and standard error handling.
- **CLI-Style Command Flags**: Flag parser supporting `--limit N` (default 5) and `--online` location filtering.
- **Command Suite**: Command set featuring `!ctfs` (CLI flag-driven feed), `!upcoming` (unfiltered feed), and `!onlinectfs` (online-only shortcut).
- **Discord Dynamic Timestamps**: Formatted timestamp rendering using Discord markdown tags (`<t:TIMESTAMP:F>` / `<t:TIMESTAMP:R>`).

### 🔄 Changed (`refactor`)
- **Event Layout**: Refactored feed output to dispatch events as individual embed messages to support reaction tracking.
- **Description Truncation**: Truncated event descriptions to the first paragraph ending with `...` to minimize embed clutter.

---

## [0.0.1] - 2026-08-29

### 🚀 Added (`feat`)
- **Prototype Initializer**: Initial Discord bot prototype with basic `!hello` greeting and multi-embed `!upcomingctfs` command.
