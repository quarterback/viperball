# Viperball

*A collegiate dynasty simulator for a sport that never existed.*

A full sports-simulation engine, four web frontends, and a 280-team fictional
universe — built to explore one question from a Reddit thread until it became a
working world.

---

## The premise

Someone asked what football would look like if it had evolved from the
pre-forward-pass era — no passing, more kicking, two-way players. Viperball is
the answer, built out completely: a gridiron code with six downs, no forward
pass, a six-channel scoring system (the 9-point touchdown, the 5-point drop
kick, the half-point "bell" for recovering a loose ball), and a 187-team
women's collegiate league to play it in.

Then the rules got a simulator. Then the simulator got leagues, dynasties,
recruiting, coaching trees, and four different ways to look at it.

---

## What it actually is

A monorepo of roughly **120,000 lines of Python**, no database and no ML
dependency — just a deterministic, contest-based simulation core wrapped in
several presentation layers.

| Layer | What it does | Tech |
|---|---|---|
| **Simulation engine** | Plays the game, runs seasons, dynasties, recruiting | Pure Python (~44 modules) |
| **REST API** | Wraps the engine, runs concurrent batch sims | FastAPI · Pydantic · async |
| **Interactive web app** | Play-calling, dynasty mode, commissioner mode | NiceGUI (Vue under the hood) · Plotly |
| **Stats portal** | Bloomberg-terminal-style read-only browser | FastAPI sub-router · Jinja2 · zero JS |
| **Data universe** | ~280 teams, 36-player rosters, procedural name pools | JSON |

Single-process deploy: NiceGUI is mounted onto the FastAPI app and served by
one uvicorn worker, containerized and shipped to **Fly.io** on a 2GB machine
with a health-checked rolling deploy.

---

## The engine is the interesting part

The core resolution system doesn't use static lookup tables. Every yard, every
catch, every kick is a **contest** between specific offensive and defensive
players' attributes, resolved stochastically:

- **Skill proximity creates variance.** Two evenly-matched players produce wild
  play-to-play swings; a mismatch produces consistent, predictable outcomes —
  the elite back reliably grinds out 6–7 yards, the contested one breaks 12 or
  gets stuffed for a loss.
- **Hot streaks** narrow a player's variance toward the high end after
  consecutive wins — a mechanical basis for the announcer's "she's got it going
  tonight."
- A **fatigue cliff** makes a 95-rated star at 25% energy play worse than a
  fresh backup, forcing real depth-chart usage.
- **Needs-based late-down conversion**, a kicker-range model where the kicker's
  rating actually determines range, weather effects, coaching archetypes that
  reshape the contest math, and nine distinct offensive schemes.

All of it tuned not by eyeballing single games but by running **200+ game batch
simulations** and validating aggregate scoring, turnover rates, and conversion
cascades against design targets.

---

## Scope

- **~280 teams** across collegiate, women's pro (WVL), and international
  leagues, each a JSON file with a 36-player roster, ratings, identity, and
  recruiting pipeline.
- **Multi-season dynasties** with recruiting, transfer portal, signing day,
  coach hiring/firing, polls, awards, and bowl games.
- **Procedural generation** scripts for teams, rosters, coaches, referees, and
  region-aware name pools.
- A documentation trail of **30+ design specs and after-action reports** —
  every major system shipped with a written rationale.

---

## What it demonstrates

- **Systems design under self-imposed constraints** — inventing a rule set, then
  proving it produces good games statistically.
- **End-to-end ownership** — domain model, simulation core, API, multiple UIs,
  data pipeline, containerization, and cloud deploy.
- **Iterative, measured tuning** — treating game balance as an empirical problem
  with batch validation, not vibes.
- **Building the same idea four ways** — interactive app, stats terminal, REST
  API, and CLI — each fitted to how a different user wants to engage.

---

*Stack: Python 3.11 · FastAPI · NiceGUI · Pydantic · Plotly · Jinja2 · pandas /
numpy · Docker · Fly.io*
