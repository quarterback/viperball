"""Progressive web app endpoints for the server-rendered stats site."""
from functools import lru_cache
from pathlib import Path
import struct
import zlib

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse, Response

router = APIRouter()
ASSETS = Path(__file__).resolve().parent / "static" / "pwa"
NO_CACHE = {"Cache-Control": "no-cache"}


@router.get("/manifest.webmanifest", include_in_schema=False)
def manifest():
    return JSONResponse({
        "id": "/stats/",
        "name": "Viperball",
        "short_name": "Viperball",
        "description": "Simulate games, manage dynasties and explore Viperball statistics.",
        "lang": "en-US",
        "start_url": "/stats/",
        "scope": "/stats/",
        "display": "standalone",
        "background_color": "#15171c",
        "theme_color": "#15171c",
        "icons": [
            {"src": "/stats/pwa/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
            {"src": "/stats/pwa/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
        ],
        "shortcuts": [
            {"name": "College", "url": "/stats/college/"},
            {"name": "Dynasty", "url": "/stats/dynasty/"},
            {"name": "Game Simulator", "url": "/stats/game-sim"},
            {"name": "Saves", "url": "/stats/saves"},
        ],
    }, media_type="application/manifest+json", headers=NO_CACHE)


@router.get("/sw.js", include_in_schema=False)
def service_worker():
    return FileResponse(ASSETS / "sw.js", media_type="application/javascript",
                        headers={**NO_CACHE, "Service-Worker-Allowed": "/stats/"})


# A small bitmap alphabet for the social card, avoiding a native graphics
# dependency or reliance on an installed font in the deployment container.
GLYPHS = {
    "A": (14,17,17,31,17,17,17), "B": (30,17,17,30,17,17,30),
    "C": (14,17,16,16,16,17,14), "D": (30,17,17,17,17,17,30),
    "E": (31,16,16,30,16,16,31), "G": (14,17,16,23,17,17,14),
    "I": (31,4,4,4,4,4,31), "L": (16,16,16,16,16,16,31),
    "M": (17,27,21,21,17,17,17), "N": (17,25,21,19,17,17,17),
    "O": (14,17,17,17,17,17,14), "P": (30,17,17,30,16,16,16),
    "R": (30,17,17,30,20,18,17), "S": (15,16,16,14,1,1,30),
    "T": (31,4,4,4,4,4,4), "U": (17,17,17,17,17,17,14),
    "V": (17,17,17,17,17,10,4), "Y": (17,17,10,4,4,4,4),
    " ": (0,0,0,0,0,0,0), "/": (1,1,2,4,8,16,16),
}
DARK = (21, 23, 28)
ORANGE = (255, 106, 0)
LIGHT = (233, 234, 238)


@lru_cache(maxsize=5)
def render_png(width, height, social=False):
    rows = [bytearray(bytes(DARK) * width) for _ in range(height)]

    def rect(x, y, w, h, color):
        for row in rows[max(0, y):min(height, y + h)]:
            left, right = max(0, x), min(width, x + w)
            if right > left:
                row[left * 3:right * 3] = bytes(color) * (right - left)

    def lettering(label, x, y, scale, color):
        for ch in label:
            for j, bits in enumerate(GLYPHS[ch]):
                for i in range(5):
                    if bits & (1 << (4 - i)):
                        rect(x + i * scale, y + j * scale, scale, scale, color)
            x += 6 * scale

    if social:
        rect(0, 0, width, 12, ORANGE)
        rect(80, 120, 150, 10, ORANGE)
        lettering("VIPERBALL", 80, 180, 18, ORANGE)
        lettering("LEAGUES / DYNASTIES / STATS", 80, 370, 6, LIGHT)
        rect(80, 480, width - 160, 2, (66, 70, 78))
        lettering("GAME SIMULATION", 80, 510, 5, LIGHT)
    else:
        # Center the mark inside the maskable icon safe zone.
        lettering("V", (width - 5 * (width // 11)) // 2,
                  (height - 7 * (width // 11)) // 2, width // 11, ORANGE)

    def chunk(kind, data):
        return (struct.pack(">I", len(data)) + kind + data +
                struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff))
    raw = b"".join(b"\x00" + row for row in rows)
    return (b"\x89PNG\r\n\x1a\n" +
            chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)) +
            chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


@router.get("/pwa/icon-{size}.png", include_in_schema=False)
def icon(size: int):
    if size not in (32, 180, 192, 512):
        raise HTTPException(404)
    return Response(render_png(size, size), media_type="image/png",
                    headers={"Cache-Control": "public, max-age=86400"})


@router.get("/pwa/social.png", include_in_schema=False)
def social_card():
    return Response(render_png(1200, 630, True), media_type="image/png",
                    headers={"Cache-Control": "public, max-age=86400"})


@router.get("/pwa/favicon.ico", include_in_schema=False)
def favicon():
    png = render_png(32, 32)
    header = struct.pack("<HHH", 0, 1, 1)
    entry = struct.pack("<BBBBHHII", 32, 32, 0, 0, 1, 32, len(png), 22)
    return Response(header + entry + png, media_type="image/x-icon",
                    headers={"Cache-Control": "public, max-age=86400"})
