"""
Viperball Sandbox - Main Entry Point
NiceGUI frontend + FastAPI backend in a single process.
"""

import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

from api.main import app as fastapi_app  # noqa: E402
from nicegui import ui  # noqa: E402
import nicegui_app.app  # noqa: E402, F401 — registers @ui.page routes


def main():
    ui.run_with(
        fastapi_app,
        title="Viperball Sandbox",
        storage_secret="viperball-sandbox-secret",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
    )


if __name__ == "__main__":
    main()
