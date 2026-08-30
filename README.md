# CTFVigil 🎯🦉

**CTFVigil** is an asynchronous, self-hostable Discord bot & task execution system designed for cybersecurity CTF (Capture The Flag) teams. It monitors upcoming events from CTFtime, automates CTF team war-room operations, and integrates with CTFd platforms to streamline challenge tracking and event management.

---

## 🏗️ Architecture

CTFVigil is structured as a containerized, event-driven service:

```
                  +-----------------------+
                  |     Discord API       |
                  +-----------+-----------+
                              | (Gateway / Reactions)
                              v
                      +---------------+
                      |   bot.py      |
                      |  (Discord)    |
                      +-------+-------+
                              |
                     Dispatch | Async Task
                              v
                      +---------------+
                      | Redis Broker  |
                      +-------+-------+
                              |
              +---------------+---------------+
              |                               |
              v                               v
    +-------------------+           +-------------------+
    |   Celery Worker   |           |    Celery Beat    |
    |  (Task Executer)  |           | (Periodic Heart)  |
    +-------------------+           +-------------------+
              |                               |
              +---------------+---------------+
                              |
                              v
                  +-----------------------+
                  |  CTFtime & CTFd APIs  |
                  +-----------------------+
```

- **Discord Bot (`bot.py`)**: Asynchronous `discord.py` bot interface supporting CLI-style command flags and real-time raw reaction event dispatching.
- **CTFtime Client (`ctfvigil/client.py`)**: Asynchronous API client for querying upcoming CTF competitions with custom User-Agents and rate-limiting.
- **CTFd Client (`ctfvigil/clients/ctfd.py`)**: HTTP client for interacting with CTFd instances (fingerprinting, challenge scraping, team scoreboard monitoring).
- **Background Tasks (`tasks/`)**: Celery workers backed by Redis for offloading background API syncs, periodic digests, and platform health checks.

---

## ⚡ Quickstart

### Prerequisites
- [Docker](https://docs.docker.com/get-docker/) & [Docker Compose](https://docs.docker.com/compose/)
- Python 3.10+ (if running locally without Docker)

### Running with Docker Compose

1. Clone the repository:
   ```bash
   git clone https://github.com/ctfvigil/CTFVigil.git
   cd CTFVigil
   ```

2. Create a `.env` configuration file:
   ```env
   DISCORD_TOKEN=your_discord_bot_token_here
   REDIS_URL=redis://redis:6379/0
   ```

3. Launch the stack:
   ```bash
   docker compose up -d --build
   ```

---

## 💻 Local Development

1. **Docker Hot-Reloading (Docker Compose Watch)**:
   ```bash
   docker compose watch
   ```
   *Automatically syncs local code edits into running containers and restarts Python processes in real time.*

2. **Native Environment**:
   ```bash
   virtualenv .venv
   source .venv/bin/activate
   pip install -e ".[dev]"
   ```

3. **Run tests**:
   ```bash
   pytest tests/
   ```

---

## 📜 Documentation & Guides

- [Testing Guide](docs/testing.md): Unit testing practices, execution options, and test coverage overview.
- [CTFd Integration Architecture](docs/CTFd.md): CTFd platform API integration strategy, permission models, and automation workflows.
- [Product Roadmap & Ideas](docs/roadmap.md): Planned features including war-room channel provisioning, challenge claiming, and military-style sitrep personas.

---

## 📄 License

Licensed under the [Apache License 2.0](LICENSE).
