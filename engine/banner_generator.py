"""
PixelLab Team Banner Pool for Viperball

Pre-generates a pool of pixel-art wide banners via the PixelLab API.
Banners are used as team page headers — wider, more cinematic than the
square stadium backgrounds.

Banners are saved as banner_000.png … banner_N.png and mapped to teams
deterministically:

    banner_index = hash(team_id) % pool_size

Usage:
    python -m engine.banner_generator --count 100

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
from typing import Optional

import requests as _requests

log = logging.getLogger(__name__)

PIXELLAB_API_URL = "https://api.pixellab.ai/v1/generate-image-pixflux"
PIXELLAB_TIMEOUT = 120
PIXELLAB_MAX_RETRIES = 6
PIXELLAB_RETRY_BACKOFF = 4  # seconds, doubled each retry — generous for 429s
BANNER_WIDTH = 320   # wide panoramic banner
BANNER_HEIGHT = 128  # shorter height for header strip

_DEFAULT_BANNERS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "stats_site", "static", "banners"
)

# ── Banner trait pools ──

BANNER_SCENES = [
    "football stadium exterior at game time",
    "football field from the sideline",
    "football locker room with jerseys hanging",
    "football team tunnel entrance with light",
    "football scoreboard and stadium lights",
    "football trophy case with championship trophies",
    "football tailgate scene outside stadium",
    "football press box overlooking the field",
    "football end zone with painted letters",
    "football team bench area with helmets",
    "football stadium concourse with banners",
    "football practice field with training equipment",
]

BANNER_MOODS = [
    "triumphant golden light",
    "intense dramatic lighting",
    "warm nostalgic afternoon glow",
    "electric night game atmosphere",
    "crisp autumn day feel",
    "epic cinematic lighting",
    "vibrant energetic atmosphere",
    "classic vintage sports feel",
    "modern sleek professional look",
    "misty morning practice vibe",
]

BANNER_COLORS = [
    "red and white accents", "blue and gold accents", "green and white accents",
    "purple and yellow accents", "orange and black accents", "navy and silver accents",
    "crimson and cream accents", "teal and white accents", "maroon and gold accents",
    "black and gold accents", "royal blue and white accents", "scarlet and gray accents",
    "forest green and gold accents", "cardinal red and navy accents",
    "burnt orange and white accents", "kelly green and silver accents",
]

BANNER_DETAILS = [
    "with pennants and flags",
    "with confetti in the air",
    "with dramatic shadows",
    "with lens flare from lights",
    "with team banners on walls",
    "with scoreboard glowing",
    "with crowd silhouettes",
    "with smoke effects",
]


def _pick(options: list, h: int, shift: int) -> str:
    return options[(h >> shift) % len(options)]


def build_banner_prompt(index: int) -> str:
    """Build a unique PixelLab prompt for banner slot `index`."""
    h = int(hashlib.sha256(f"viperball-banner-{index}".encode()).hexdigest(), 16)

    scene = _pick(BANNER_SCENES, h, 0)
    mood = _pick(BANNER_MOODS, h, 8)
    colors = _pick(BANNER_COLORS, h, 16)
    detail = _pick(BANNER_DETAILS, h, 24)

    return (
        f"16-bit pixel art wide panoramic scene, {scene}, "
        f"{mood}, {colors}, {detail}, cinematic composition"
    )


def pool_banner_path(index: int, banners_dir: str = _DEFAULT_BANNERS_DIR) -> Path:
    return Path(banners_dir) / f"banner_{index:03d}.png"


def get_pool_size(banners_dir: str = _DEFAULT_BANNERS_DIR) -> int:
    d = Path(banners_dir)
    if not d.is_dir():
        return 0
    return sum(1 for f in d.iterdir() if re.match(r"banner_\d{3}\.png$", f.name))


def get_banner_index(team_id: str, pool_size: int = 0,
                     banners_dir: str = _DEFAULT_BANNERS_DIR) -> Optional[int]:
    n = pool_size or get_pool_size(banners_dir)
    if n == 0:
        return None
    h = int(hashlib.sha256(team_id.encode()).hexdigest(), 16)
    return h % n


def get_banner_url(team_id: str, pool_size: int = 0,
                   banners_dir: str = _DEFAULT_BANNERS_DIR) -> Optional[str]:
    idx = get_banner_index(team_id, pool_size, banners_dir)
    if idx is None:
        return None
    return f"/stats/static/banners/banner_{idx:03d}.png"


# ── PixelLab API ──

def _call_pixellab(prompt: str, seed: int, api_key: str) -> bytes:
    payload = {
        "description": prompt,
        "image_size": {"width": BANNER_WIDTH, "height": BANNER_HEIGHT},
        "outline": "selective outline",
        "detail": "highly detailed",
        "shading": "detailed shading",
        "no_background": False,
        "direction": "east",
        "seed": seed,
    }

    for attempt in range(PIXELLAB_MAX_RETRIES):
        try:
            resp = _requests.post(
                PIXELLAB_API_URL,
                json=payload,
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=PIXELLAB_TIMEOUT,
            )
        except (_requests.exceptions.Timeout, _requests.exceptions.ConnectionError) as exc:
            if attempt < PIXELLAB_MAX_RETRIES - 1:
                time.sleep(PIXELLAB_RETRY_BACKOFF * (2 ** attempt))
                continue
            raise RuntimeError(
                f"PixelLab request failed after {PIXELLAB_MAX_RETRIES} attempts: {exc}"
            ) from exc

        if (resp.status_code == 429 or resp.status_code >= 500) and attempt < PIXELLAB_MAX_RETRIES - 1:
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


def generate_pool_banner(
    index: int,
    banners_dir: str = _DEFAULT_BANNERS_DIR,
    api_key: Optional[str] = None,
    force: bool = False,
) -> Path:
    api_key = api_key or os.environ.get("PIXELLAB_API_KEY", "")
    if not api_key:
        raise ValueError("PIXELLAB_API_KEY not set")

    out_path = pool_banner_path(index, banners_dir)
    if not force and out_path.is_file():
        return out_path

    out_path.parent.mkdir(parents=True, exist_ok=True)

    prompt = build_banner_prompt(index)
    seed_hash = int(hashlib.sha256(f"viperball-banner-{index}".encode()).hexdigest(), 16)
    seed = seed_hash % (2**31)

    png_bytes = _call_pixellab(prompt, seed, api_key)
    out_path.write_bytes(png_bytes)
    return out_path


async def generate_pool(
    count: int = 100,
    banners_dir: str = _DEFAULT_BANNERS_DIR,
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
        out_path = pool_banner_path(idx, banners_dir)
        if not force and out_path.is_file():
            results["skipped"].append(idx)
            done_count += 1
            return
        async with sem:
            try:
                await asyncio.to_thread(
                    generate_pool_banner, idx, banners_dir, api_key, force
                )
                results["generated"].append(idx)
            except Exception as e:
                results["failed"].append({"index": idx, "error": str(e)})
            done_count += 1
            if done_count % 5 == 0 or done_count == count:
                log.info("Banner pool progress: %d/%d (generated=%d, failed=%d)",
                         done_count, count, len(results["generated"]),
                         len(results["failed"]))

    await asyncio.gather(*[_gen(i) for i in range(count)])
    return results


# ── CLI entry point ──

if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Generate viperball pixel-art team banners via PixelLab API"
    )
    parser.add_argument(
        "--count", type=int, default=100,
        help="Number of banners to generate (default: 100)",
    )
    parser.add_argument(
        "--dir", default=_DEFAULT_BANNERS_DIR,
        help="Output directory for banner PNGs",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Regenerate existing banners",
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
    print(f"Banner pool: {existing} existing banners in {args.dir}")
    print(f"Generating up to {args.count} banners (concurrency={args.concurrency})...")

    results = asyncio.run(generate_pool(
        count=args.count,
        banners_dir=args.dir,
        api_key=api_key,
        force=args.force,
        concurrency=args.concurrency,
    ))

    print(f"Done: {len(results['generated'])} generated, "
          f"{len(results['skipped'])} skipped, "
          f"{len(results['failed'])} failed")
    if results["failed"]:
        for f in results["failed"][:5]:
            print(f"  FAIL banner_{f['index']:03d}: {f['error']}")
