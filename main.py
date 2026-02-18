"""
Viperball Sandbox - Main Entry Point
Runs FastAPI backend + Streamlit UI
"""

import subprocess
import sys
import os
import time
import signal


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    api_proc = subprocess.Popen([
        sys.executable, "-m", "uvicorn", "api.main:app",
        "--host=0.0.0.0", "--port=8000",
        "--log-level=warning",
    ])

    time.sleep(1)

    streamlit_proc = subprocess.Popen([
        sys.executable, "-m", "streamlit", "run", "ui/app.py",
        "--server.port=5000",
        "--server.address=0.0.0.0",
        "--server.headless=true",
        "--browser.gatherUsageStats=false",
        "--server.enableCORS=false",
        "--server.enableXsrfProtection=false",
    ])

    def shutdown(signum, frame):
        api_proc.terminate()
        streamlit_proc.terminate()
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    try:
        streamlit_proc.wait()
    except KeyboardInterrupt:
        pass
    finally:
        api_proc.terminate()
        streamlit_proc.terminate()


if __name__ == "__main__":
    main()
