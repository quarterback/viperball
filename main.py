"""
Viperball Sandbox - Main Entry Point
NiceGUI frontend + FastAPI backend in a single process.

ui.run_with() mounts NiceGUI onto the FastAPI app at module level.
uvicorn serves the app and controls host/port.
"""

import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("viperball")

os.chdir(os.path.dirname(os.path.abspath(__file__)))

logger.info("Importing API...")
from api.main import app as fastapi_app  # noqa: E402
logger.info("Importing NiceGUI...")
from nicegui import ui  # noqa: E402

logger.info("Registering UI routes...")
import nicegui_app.app  # noqa: E402, F401 — registers @ui.page routes

# Mount NiceGUI onto the FastAPI app (no host/port — uvicorn handles that)
logger.info("Mounting NiceGUI onto FastAPI...")
ui.run_with(
    fastapi_app,
    title="Viperball Sandbox",
    storage_secret="viperball-sandbox-secret",
    reconnect_timeout=43200.0,
)
logger.info("Viperball ready.")


@fastapi_app.on_event("startup")
async def _prewarm_shared_data():
    """Pre-warm the shared data cache in a background thread.

    Loads team data and style dicts so the first page render is instant
    instead of blocking on 188 JSON file reads.
    """
    import asyncio
    from nicegui_app.app import _load_shared_data
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _load_shared_data)
    logger.info("Shared data cache pre-warmed.")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        fastapi_app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
    )
