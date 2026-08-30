# CTFd Integration Technical Roadmap

## Integration Access Tiers

* **Level 1: Anonymous Read-Only**

CTFd instance is configured to be private, register option is disabled.
  * **Mechanism:** Public HTTP requests with no authentication.
  * **Capabilities:** Passive polling of public challenges, teams, and scoreboards (subject to platform privacy settings).
  * **Constraints:** Limited data if the instance hides scoreboards or challenge lists behind login walls.

* **Level 2: Participant Bot (User-Level)**
Our bot is registered as a CTF user/player, meaning they can see challenges at the very least. They might, or might not, have access to users list, teams, scoreboard.
The bot user could be considered part of a team or a solo user.
  * **Mechanism:** Browser automation (Playwright/Selenium) or captured session cookies via `/register`.
  * **Capabilities:** Standard user interaction, puzzle submissions, and visibility inside external platforms where admin rights are unavailable.
  * **Constraints:** Fragile against anti-bot scripts, CAPTCHAs, or closed registrations.

* **Level 3: Admin-Granted Bot (Admin Token)**
Administrators of the CTF will grant the bot an administrative access token.
  * **Mechanism:** Configurable Admin Access Token passed via `Authorization: Token <token>`.
  * **Capabilities:** Full programmatic control over users, teams, challenges, and system configurations. The cleanest and most robust integration approach.
  * **Constraints:** Requires initial administrative provisioning on the target platform.

* **Level 4: Plugin-Powered Extension (Advanced)**
  * **Mechanism:** Custom Python modules placed directly in the CTFd `plugins/` directory.
  * **Capabilities:** Deep Flask execution hooks, custom challenge types, and direct backend extensions.
  * **Constraints:** Restricted strictly to self-hosted instances you manage; unusable on third-party CTFs you do not own.

## Phase-by-Phase Implementation Plan

* **Phase 1: Core API Wrapper Development**
  * Build a lightweight Python client targeting CTFd's standard `v1` REST architecture (`ctfvigil/clients/ctfd.py`).
  * Implement liveness checks (`is_ctfd_instance`) and endpoint diagnostic probing (`probe_endpoint`, `probe_all_endpoints`, `get_ctfd_scoreboard_details`).
  * Expose anonymous inspection commands via Discord (`!track <url>` for instance diagnostics, `!scoreboard <url>` for live leaderboard standings).
  * Standardize response parsing around CTFd's native JSON envelope (`"success": boolean`).

* **Phase 2: Telemetry and Event Tracking**
  * Deploy background routines to poll datasets across users, teams, challenges, and scoreboards.
  * Validate stability against standard testing sandboxes like `https://demo.ctfd.io/`.

* **Phase 3: Background Worker Orchestration (Celery)**
  * Offload user creation, token caching, and synchronization routines to asynchronous Celery tasks.
  * Implement automated retry logic and a manual intervention fallback state for deployment roadblocks.

* **Phase 4: Community and Chat Extensions**
  * Connect telemetry pipelines to downstream applications like Discord notification bots.
  * Track challenge solve rates, first blood announcements, and hint drops to assist community management.

## Core API Endpoints Reference
* Users Registry: `/api/v1/users`
* Teams Registry: `/api/v1/teams`
* Challenges Catalog: `/api/v1/challenges`
* Leaderboard Standings: `/api/v1/scoreboard`
