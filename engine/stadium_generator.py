"""
PixelLab Stadium Backgrounds for Viperball

Pre-generates a pool of pixel-art stadium/field backgrounds via the PixelLab API.
Stadiums are saved as stadium_000.png … stadium_N.png and can be mapped to teams
deterministically:

    stadium_index = hash(team_id) % pool_size

Usage:
    python -m engine.stadium_generator --count 50

Requires PIXELLAB_API_KEY environment variable for generation.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import logging
import os
import re
import time
from pathlib import Path
from typing import List, Optional

import requests as _requests

log = logging.getLogger(__name__)

PIXELLAB_API_URL = "https://api.pixellab.ai/v1/generate-image-pixflux"
PIXELLAB_TIMEOUT = 120
PIXELLAB_MAX_RETRIES = 4
PIXELLAB_RETRY_BACKOFF = 2
STADIUM_SIZE = 64  # 64x64 — bigger than faces to show field detail

_DEFAULT_STADIUMS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "stats_site", "static", "stadiums"
)

# ── Stadium trait pools ──

STADIUM_TYPES = [
    "open-air football stadium",
    "domed football stadium",
    "retro brick football stadium",
    "modern glass football stadium",
    "small-town football field",
    "college football stadium",
    "large professional football arena",
    "outdoor football field with bleachers",
]

WEATHER_CONDITIONS = [
    "sunny day", "cloudy sky", "overcast", "golden sunset",
    "night game with floodlights", "light rain", "snow flurries",
    "clear blue sky", "dramatic orange sky", "foggy evening",
]

FIELD_FEATURES = [
    "green grass field", "pristine turf field",
    "worn grass field", "artificial turf",
    "freshly painted yard lines", "muddy field",
]

CROWD_SIZES = [
    "packed crowd", "half-full stands",
    "sold-out crowd with banners", "sparse crowd",
    "roaring fans with confetti", "standing-room-only crowd",
]

ACCENT_COLORS = [
    "red and white", "blue and gold", "green and white",
    "purple and yellow", "orange and black", "navy and silver",
    "crimson and gray", "teal and white", "maroon and gold",
    "black and gold", "royal blue and white", "scarlet and cream",
]


def _pick(options: list, h: int, shift: int) -> str:
    return options[(h >> shift) % len(options)]


def build_stadium_prompt(index: int) -> str:
    """Build a unique PixelLab prompt for stadium slot `index`."""
    h = int(hashlib.sha256(f"viperball-stadium-{index}".encode()).hexdigest(), 16)

    stadium_type = _pick(STADIUM_TYPES, h, 0)
    weather = _pick(WEATHER_CONDITIONS, h, 8)
    field = _pick(FIELD_FEATURES, h, 16)
    crowd = _pick(CROWD_SIZES, h, 24)
    colors = _pick(ACCENT_COLORS, h, 32)

    return (
        f"pixel art {stadium_type}, {weather}, {field}, "
        f"{crowd}, {colors} team colors, top-down isometric view"
    )


def pool_stadium_path(index: int, stadiums_dir: str = _DEFAULT_STADIUMS_DIR) -> Path:
    return Path(stadiums_dir) / f"stadium_{index:03d}.png"


def get_pool_size(stadiums_dir: str = _DEFAULT_STADIUMS_DIR) -> int:
    d = Path(stadiums_dir)
    if not d.is_dir():
        return 0
    return sum(1 for f in d.iterdir() if re.match(r"stadium_\d{3}\.png$", f.name))


def get_stadium_index(team_id: str, pool_size: int = 0,
                      stadiums_dir: str = _DEFAULT_STADIUMS_DIR) -> Optional[int]:
    n = pool_size or get_pool_size(stadiums_dir)
    if n == 0:
        return None
    h = int(hashlib.sha256(team_id.encode()).hexdigest(), 16)
    return h % n


def get_stadium_url(team_id: str, pool_size: int = 0,
                    stadiums_dir: str = _DEFAULT_STADIUMS_DIR) -> Optional[str]:
    idx = get_stadium_index(team_id, pool_size, stadiums_dir)
    if idx is None:
        return None
    return f"/stats/static/stadiums/stadium_{idx:03d}.png"


# ── PixelLab API ──

def _call_pixellab(prompt: str, seed: int, api_key: str) -> bytes:
    payload = {
        "description": prompt,
        "image_size": {"width": STADIUM_SIZE, "height": STADIUM_SIZE},
        "outline": "single color black outline",
        "detail": "low detail",
        "no_background": False,
        "direction": "south",
        "seed": seed,
    }

    last_err: Exception | None = None
    for attempt in range(PIXELLAB_MAX_RETRIES):
        try:
            resp = _requests.post(
                PIXELLAB_API_URL,
                json=payload,
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=PIXELLAB_TIMEOUT,
            )
        except (_requests.exceptions.Timeout, _requests.exceptions.ConnectionError) as exc:
            last_err = exc
            if attempt < PIXELLAB_MAX_RETRIES - 1:
                time.sleep(PIXELLAB_RETRY_BACKOFF * (2 ** attempt))
                continue
            raise RuntimeError(
                f"PixelLab request failed after {PIXELLAB_MAX_RETRIES} attempts: {exc}"
            ) from exc

        if (resp.status_code == 429 or resp.status_code >= 500) and attempt < PIXELLAB_MAX_RETRIES - 1:
            last_err = RuntimeError(f"PixelLab API error {resp.status_code}")
            time.sleep(PIXELLAB_RETRY_BACKOFF * (2 ** attempt))
            continue

        if resp.status_code != 200:
            raise RuntimeError(
                f"PixelLab API error {resp.status_code}: {resp.text[:200]}"
            )
        break

    data = resp.json()
    image_b64 = data.get("image", {}).get("base64", "")
    if not image_b64:
        images = data.get("data", {}).get("images", [])
        if images:
            image_b64 = images[0].get("base64", "")
    if not image_b64:
        image_b64 = data.get("base64", "")

    if not image_b64:
        raise RuntimeError(
            f"No image data in PixelLab response: {list(data.keys())}"
        )

    return base64.b64decode(image_b64)


def generate_pool_stadium(
    index: int,
    stadiums_dir: str = _DEFAULT_STADIUMS_DIR,
    api_key: Optional[str] = None,
    force: bool = False,
) -> Path:
    api_key = api_key or os.environ.get("PIXELLAB_API_KEY", "")
    if not api_key:
        raise ValueError("PIXELLAB_API_KEY not set")

    out_path = pool_stadium_path(index, stadiums_dir)
    if not force and out_path.is_file():
        return out_path

    out_path.parent.mkdir(parents=True, exist_ok=True)

    prompt = build_stadium_prompt(index)
    seed_hash = int(hashlib.sha256(f"viperball-stadium-{index}".encode()).hexdigest(), 16)
    seed = seed_hash % (2**31)

    png_bytes = _call_pixellab(prompt, seed, api_key)
    out_path.write_bytes(png_bytes)
    return out_path


async def generate_pool(
    count: int = 50,
    stadiums_dir: str = _DEFAULT_STADIUMS_DIR,
    api_key: Optional[str] = None,
    force: bool = False,
    concurrency: int = 4,
) -> dict:
    api_key = api_key or os.environ.get("PIXELLAB_API_KEY", "")
    sem = asyncio.Semaphore(concurrency)
    results: dict = {"generated": [], "skipped": [], "failed": []}

    done_count = 0

    async def _gen(idx: int):
        nonlocal done_count
        out_path = pool_stadium_path(idx, stadiums_dir)
        if not force and out_path.is_file():
            results["skipped"].append(idx)
            done_count += 1
            return
        async with sem:
            try:
                await asyncio.to_thread(
                    generate_pool_stadium, idx, stadiums_dir, api_key, force
                )
                results["generated"].append(idx)
            except Exception as e:
                results["failed"].append({"index": idx, "error": str(e)})
            done_count += 1
            if done_count % 5 == 0 or done_count == count:
                log.info("Stadium pool progress: %d/%d (generated=%d, failed=%d)",
                         done_count, count, len(results["generated"]),
                         len(results["failed"]))

    await asyncio.gather(*[_gen(i) for i in range(count)])
    return results


# ── CLI entry point ──

if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Generate viperball pixel-art stadium backgrounds via PixelLab API"
    )
    parser.add_argument(
        "--count", type=int, default=50,
        help="Number of stadiums to generate (default: 50)",
    )
    parser.add_argument(
        "--dir", default=_DEFAULT_STADIUMS_DIR,
        help="Output directory for stadium PNGs",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Regenerate existing stadiums",
    )
    parser.add_argument(
        "--concurrency", type=int, default=4,
        help="Max concurrent API calls (default: 4)",
    )
    args = parser.parse_args()

    api_key = os.environ.get("PIXELLAB_API_KEY", "")
    if not api_key:
        print("ERROR: Set PIXELLAB_API_KEY environment variable first")
        sys.exit(1)

    existing = get_pool_size(args.dir)
    print(f"Stadium pool: {existing} existing stadiums in {args.dir}")
    print(f"Generating up to {args.count} stadiums (concurrency={args.concurrency})...")

    results = asyncio.run(generate_pool(
        count=args.count,
        stadiums_dir=args.dir,
        api_key=api_key,
        force=args.force,
        concurrency=args.concurrency,
    ))

    print(f"Done: {len(results['generated'])} generated, "
          f"{len(results['skipped'])} skipped, "
          f"{len(results['failed'])} failed")
    if results["failed"]:
        for f in results["failed"][:5]:
            print(f"  FAIL stadium_{f['index']:03d}: {f['error']}")
