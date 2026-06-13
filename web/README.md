# Viperball Web (SPA rebuild)

React + Mantine single-page app that replaces the NiceGUI UI at `viperball.fly.dev/`.
It consumes the existing FastAPI backend. See `../UI_REBUILD_PLAN.md` for the full plan.

## Stack
- **Vite + React + TypeScript** (no meta-framework)
- **Mantine v7** UI kit, light theme authored natively (`src/theme.ts`)
- **mantine-react-table** for dense, sortable, filterable data grids
- **TanStack Query** for data fetching/caching
- **React Router v6** for real, deep-linkable URLs (served under `/app`)
- **@mantine/spotlight** command palette (`⌘K` / `Ctrl-K`)

## Run
```bash
cd web
npm install
npm run dev        # http://localhost:5173/app/  (proxies /api* to :8080)
```
The Saves Library works **standalone** — when `/api/saves` 404s, it falls back to an
in-browser mock store (`src/api/saves.ts`) so you can click around before the Phase 0
backend lands.

## Build (served by FastAPI)
```bash
npm run build      # → web/dist, mounted at /app by FastAPI during the strangler migration
```

## What's here (Phase 1)
- AppShell: sidebar nav + topbar + command palette
- **Saves Library** (home): list / open / fork / delete experiments, with mode/tags/seed columns
- Phase 2–4 screens are placeholders that name the exact endpoints that will back them

## Generate typed API client (once backend is up)
```bash
npm run gen:api    # openapi-typescript from http://localhost:8080/openapi.json → src/api/schema.ts
```
