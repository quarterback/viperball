# After Action Report: NiceGUI 3.x Compatibility & SaaS UI Layout

**Date:** February 23, 2026

---

## Problem Statement
The Viperball Sandbox app was rendering a blank white page with no visible errors. The browser showed repeated "implicit handshake failed" messages and the websocket connection would open then immediately close in a loop.

## Root Cause Analysis
The app was built for NiceGUI 2.24.2 (as pinned in `requirements.txt`) but NiceGUI 3.7.1 was actually installed in the environment. Version 3.x changed how async page rendering and client connections work:

1. **`app.storage.tab`** requires `await client.connected()` before it can be accessed
2. **`await client.connected()`** in NiceGUI 3.x caused a deadlock when combined with `await run.io_bound()` API calls during page build — because NiceGUI and FastAPI share the same uvicorn event loop
3. This created a catch-22: the storage API needed the async wait, but the async wait broke the websocket lifecycle

## Debugging Process
1. Checked server logs — no Python errors or tracebacks (failures were silent)
2. Verified HTTP 200 responses (page HTML was served correctly)
3. Identified websocket connect/disconnect loop pattern
4. Stripped the page down to a minimal "Hello World" to confirm NiceGUI itself worked
5. Gradually added components back to isolate the failure point
6. Confirmed `await client.connected()` was the breaking call
7. Got the explicit error message: *"app.storage.tab can only be used with a client connection"*
8. Researched NiceGUI 3.x storage alternatives

## Solution
Three files changed:

| File | Change | Why |
|------|--------|-----|
| `nicegui_app/state.py` | `app.storage.tab` → `app.storage.user` | Cookie-based storage works without async client connection |
| `nicegui_app/app.py` | `async def index(client)` → `def index()`, removed `await client.connected()` | Synchronous page render eliminates the deadlock |
| `nicegui_app/pages/play.py` | Added `render_play_section_sync()` | Provides a sync entry point for initial page build; defers async API calls via timer for active sessions |

## Trade-offs
- `app.storage.user` persists across all tabs (not per-tab like before). For a single-user sandbox tool, this is acceptable — you're unlikely to run competing sessions in different tabs.
- The initial page render is fully synchronous. Active session data (dynasty/season status) loads asynchronously after render via a short timer, so there's a brief "Loading..." flash for returning sessions.

## UI Outcome
- SaaS-style horizontal navigation bar in the header: Play, League, My Team, Export, Debug, Inspector
- No hidden menus, no sidebar drawer — everything one click away
- Session status and End button visible in the header when a session is active
- Mobile-friendly flat button layout

## Lessons Learned
1. When NiceGUI reports no errors but the page is blank, it's almost always a websocket lifecycle issue — check the browser console for "implicit handshake failed"
2. In a shared event loop (NiceGUI + FastAPI on one process), `await` during page build is dangerous. Prefer synchronous rendering with deferred async loading.
3. Always verify the *installed* package version vs. what's *pinned* in requirements — they can silently diverge.
4. The NiceGUI storage types have very different connection requirements. `app.storage.user` is the safest default when you don't need per-tab isolation.

## NiceGUI Storage Reference

| Storage Type | Scope | Requires `await client.connected()` | Persists on Reload | Persists Across Tabs |
|---|---|---|---|---|
| `app.storage.client` | Per-connection | No | No | No |
| `app.storage.tab` | Per-tab session | Yes | Yes | No |
| `app.storage.user` | Per-user (cookie) | No | Yes | Yes |
| `app.storage.browser` | Per-browser | No | Yes | Yes |
| `app.storage.general` | Global | No | Yes (server-side) | Yes |
