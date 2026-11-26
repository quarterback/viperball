"""PWA endpoints and metadata contract."""
import struct
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from stats_site.pwa import router, render_png

ROOT = Path(__file__).resolve().parents[1]


def client():
    app = FastAPI()
    app.include_router(router, prefix="/stats")
    return TestClient(app)


def test_manifest_and_icons():
    c = client()
    response = c.get("/stats/manifest.webmanifest")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/manifest+json")
    manifest = response.json()
    assert manifest["id"] == manifest["scope"] == manifest["start_url"] == "/stats/"
    assert manifest["display"] == "standalone"
    for icon in manifest["icons"]:
        response = c.get(icon["src"])
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"
        size = int(icon["sizes"].split("x")[0])
        assert response.content[:8] == b"\x89PNG\r\n\x1a\n"
        assert struct.unpack(">II", response.content[16:24]) == (size, size)
    assert c.get("/stats/pwa/icon-180.png").status_code == 200
    assert c.get("/stats/pwa/icon-1024.png").status_code == 404


def test_social_card_and_worker():
    c = client()
    response = c.get("/stats/pwa/social.png")
    assert response.headers["content-type"] == "image/png"
    assert struct.unpack(">II", response.content[16:24]) == (1200, 630)
    worker = c.get("/stats/sw.js")
    assert worker.status_code == 200
    assert worker.headers["service-worker-allowed"] == "/stats/"
    assert worker.headers["cache-control"] == "no-cache"
    assert "req.method !== 'GET'" in worker.text
    assert "req.mode === 'navigate'" in worker.text
    assert "cache.put(" not in worker.text
    assert (ROOT / "stats_site/static/pwa/offline.html").is_file()


def test_metadata_and_registration_present():
    base = (ROOT / "stats_site/templates/base.html").read_text()
    for tag in ('rel="manifest"', 'rel="icon"', 'rel="apple-touch-icon"',
                'name="description"', 'property="og:title"',
                'property="og:image"', 'property="og:description"',
                'name="twitter:card"', 'pwa-install', '/stats/static/pwa/install.js'):
        assert tag in base
    install = (ROOT / "stats_site/static/pwa/install.js").read_text()
    assert "beforeinstallprompt" in install
    assert "navigator.serviceWorker.register('/stats/sw.js'" in install
