# Viperball workspace notes

This file directs workspace agents to the current documentation rather than duplicating outdated system specifications.

- Start: [README](README.md), [Quick start](QUICKSTART.md).
- Product and modes: [FEATURES](FEATURES.md).
- Engine and rules: [ENGINE_README](ENGINE_README.md), [RULES](RULES.md), [COLLEGE_RULES](COLLEGE_RULES.md).
- Current architecture: [ARCHITECTURE_STATS_SITE_AND_RECRUITING](ARCHITECTURE_STATS_SITE_AND_RECRUITING.md).
- Current development queue: [docs/DEVELOPMENT_PLAN.md](docs/DEVELOPMENT_PLAN.md).
- Analytics and coaching: [ANALYTICS](ANALYTICS.md), [COACHING_SPEC](COACHING_SPEC.md).

Run `python main.py` after installing requirements.txt. FastAPI, server-rendered stats-site pages and NiceGUI share one process. Do not assume the old React, desktop or fast-sim paths exist. All new work starts from current main, uses existing regression/benchmark workflows, and records an AAR with code revision, observed results and unresolved limitations. Historic preference/rate targets in older reports are not current mandates.
