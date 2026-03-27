"""
PixelLab Referee Face Pool for Viperball

Pre-generates a pool of pixel-art referee portraits.  Referees wear
black-and-white striped shirts and referee caps.

Files are saved as ref_000.png … ref_N.png and mapped deterministically:

    ref_index = hash(referee_id) % pool_size

Usage:
    python -m engine.referee_generator --count 300

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
FACE_SIZE = 32  # 32x32 retro style

_DEFAULT_REFS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "stats_site", "static", "referees"
)

# ── Appearance trait pools ──

SKIN_TONES = [
    "pale skin", "light skin", "fair skin", "peach skin",
    "medium skin", "olive skin", "golden skin", "tan skin",
    "caramel skin", "brown skin", "dark brown skin", "deep brown skin",
    "ebony skin", "warm beige skin",
]

HAIR_COLORS = [
    "black", "jet black", "dark brown", "brown", "chestnut",
    "auburn", "red", "ginger", "strawberry blonde",
    "dirty blonde", "blonde", "platinum blonde", "light brown",
    "sandy brown", "copper", "burgundy", "dark red",
    "silver", "gray", "white",
]

HAIR_STYLES = [
    "short hair", "buzzcut", "crew cut", "slicked back hair",
    "comb over", "receding hairline", "bald head", "flat top",
    "side part", "wavy hair", "curly hair", "afro",
    "ponytail", "bun", "pixie cut", "shoulder length hair",
    "cornrows", "braids",
]

GENDERS = [
    "male", "male", "male", "male", "male",  # weighted 50/50
    "female", "female", "female", "female", "female",
]

REF_HEADWEAR = [
    "wearing referee cap", "wearing black cap",
    "no hat", "no hat", "no hat",
    "wearing referee cap",
]


def _pick(options: list, h: int, shift: int) -> str:
    return options[(h >> shift) % len(options)]


def build_ref_prompt(index: int) -> str:
    """Build a unique PixelLab prompt for referee face slot `index`."""
    h = int(hashlib.sha256(f"viperball-ref-{index}".encode()).hexdigest(), 16)

    gender = _pick(GENDERS, h, 0)
    skin = _pick(SKIN_TONES, h, 4)
    hair_color = _pick(HAIR_COLORS, h, 12)
    hair_style = _pick(HAIR_STYLES, h, 20)
    headwear = _pick(REF_HEADWEAR, h, 28)

    return (
        f"{gender} football referee, {skin}, {hair_color} {hair_style}, "
        f"{headwear}, black and white striped shirt, portrait, standing pose"
    )


def pool_ref_path(index: int, refs_dir: str = _DEFAULT_REFS_DIR) -> Path:
    return Path(refs_dir) / f"ref_{index:03d}.png"


# ── Pool inspection ──

def get_pool_size(refs_dir: str = _DEFAULT_REFS_DIR) -> int:
    d = Path(refs_dir)
    if not d.is_dir():
        return 0
    return sum(1 for f in d.iterdir() if re.match(r"ref_\d{3}\.png$", f.name))


def get_ref_index(referee_id: str, pool_size: int = 0,
                  refs_dir: str = _DEFAULT_REFS_DIR) -> int | None:
    n = pool_size or get_pool_size(refs_dir)
    if n == 0:
        return None
    h = int(hashlib.sha256(referee_id.encode()).hexdigest(), 16)
    return h % n


def get_ref_url(referee_id: str, pool_size: int = 0,
                refs_dir: str = _DEFAULT_REFS_DIR) -> str | None:
    idx = get_ref_index(referee_id, pool_size, refs_dir)
    if idx is None:
        return None
    return f"/stats/static/referees/ref_{idx:03d}.png"


# ── PixelLab API ──

def _call_pixellab(prompt: str, seed: int, api_key: str) -> bytes:
    payload = {
        "description": prompt,
        "image_size": {"width": FACE_SIZE, "height": FACE_SIZE},
        "outline": "single color black outline",
        "detail": "low detail",
        "no_background": True,
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


def generate_pool_ref(
    index: int,
    refs_dir: str = _DEFAULT_REFS_DIR,
    api_key: str | None = None,
    force: bool = False,
) -> Path:
    api_key = api_key or os.environ.get("PIXELLAB_API_KEY", "")
    if not api_key:
        raise ValueError("PIXELLAB_API_KEY not set")

    out_path = pool_ref_path(index, refs_dir)
    if not force and out_path.is_file():
        return out_path

    out_path.parent.mkdir(parents=True, exist_ok=True)

    prompt = build_ref_prompt(index)
    seed_hash = int(hashlib.sha256(f"viperball-ref-{index}".encode()).hexdigest(), 16)
    seed = seed_hash % (2**31)

    png_bytes = _call_pixellab(prompt, seed, api_key)
    out_path.write_bytes(png_bytes)
    return out_path


async def generate_pool(
    count: int = 300,
    refs_dir: str = _DEFAULT_REFS_DIR,
    api_key: str | None = None,
    force: bool = False,
    concurrency: int = 4,
) -> dict:
    """Generate the referee face pool asynchronously."""
    api_key = api_key or os.environ.get("PIXELLAB_API_KEY", "")
    sem = asyncio.Semaphore(concurrency)
    results: dict = {"generated": [], "skipped": [], "failed": []}

    done_count = 0

    async def _gen(idx: int):
        nonlocal done_count
        out_path = pool_ref_path(idx, refs_dir)
        if not force and out_path.is_file():
            results["skipped"].append(idx)
            done_count += 1
            return
        async with sem:
            try:
                await asyncio.to_thread(
                    generate_pool_ref, idx, refs_dir, api_key, force
                )
                results["generated"].append(idx)
            except Exception as e:
                results["failed"].append({"index": idx, "error": str(e)})
            done_count += 1
            if done_count % 10 == 0 or done_count == count:
                log.info("Referee pool progress: %d/%d (generated=%d, failed=%d)",
                         done_count, count, len(results["generated"]),
                         len(results["failed"]))

    await asyncio.gather(*[_gen(i) for i in range(count)])
    return results


# ── CLI entry point ──

if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Generate viperball pixel-art referee face pool via PixelLab API"
    )
    parser.add_argument(
        "--count", type=int, default=300,
        help="Number of referee faces to generate (default: 300)",
    )
    parser.add_argument(
        "--dir", default=_DEFAULT_REFS_DIR,
        help="Output directory for referee face PNGs",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Regenerate existing faces",
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
    print(f"Referee pool: {existing} existing faces in {args.dir}")
    print(f"Generating up to {args.count} referee faces (concurrency={args.concurrency})...")

    results = asyncio.run(generate_pool(
        count=args.count,
        refs_dir=args.dir,
        api_key=api_key,
        force=args.force,
        concurrency=args.concurrency,
    ))

    print(f"Done: {len(results['generated'])} generated, "
          f"{len(results['skipped'])} skipped, "
          f"{len(results['failed'])} failed")
    if results["failed"]:
        for f in results["failed"][:5]:
            print(f"  FAIL ref_{f['index']:03d}: {f['error']}")
