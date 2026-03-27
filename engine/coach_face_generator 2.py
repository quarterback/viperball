"""
PixelLab Coach Face Pool for Viperball

Pre-generates two pools of pixel-art coach portraits: one male-presenting,
one female-presenting.  Coaches don't wear helmets — they wear headsets,
caps, visors, or go bare-headed.

Files are saved as:
    coach_m_000.png … coach_m_N.png   (male pool)
    coach_f_000.png … coach_f_N.png   (female pool)

Assignment is deterministic:
    pool  = "m" if gender == "male" else "f"
    index = hash(coach_id) % pool_size[pool]

Usage:
    python -m engine.coach_face_generator --count 150

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

_DEFAULT_COACH_FACES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "stats_site", "static", "coach_faces"
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

MALE_HAIR_STYLES = [
    "short hair", "buzzcut", "crew cut", "slicked back hair",
    "comb over", "receding hairline", "bald head", "flat top",
    "side part", "wavy hair", "curly hair", "afro",
    "gray temples", "salt and pepper hair",
]

FEMALE_HAIR_STYLES = [
    "ponytail", "high ponytail", "bun", "pixie cut",
    "shoulder length hair", "long hair", "braids", "bob cut",
    "french braid", "curly hair", "wavy hair", "slicked back hair",
    "cornrows", "box braids",
]

HEADWEAR = [
    "wearing headset", "wearing baseball cap", "wearing visor",
    "no hat", "no hat", "no hat",  # weighted toward bare-headed
    "wearing headset", "wearing headset",  # weighted toward headsets
]

POLO_COLORS = [
    "white polo shirt", "red polo shirt", "blue polo shirt", "navy polo shirt",
    "green polo shirt", "dark green polo shirt", "black polo shirt",
    "gray polo shirt", "maroon polo shirt", "orange polo shirt",
    "purple polo shirt", "teal polo shirt", "khaki polo shirt",
    "crimson polo shirt", "gold polo shirt", "silver polo shirt",
]


def _pick(options: list, h: int, shift: int) -> str:
    return options[(h >> shift) % len(options)]


def build_coach_prompt(index: int, gender: str) -> str:
    """Build a unique PixelLab prompt for a coach face slot."""
    seed_str = f"viperball-coach-{gender}-{index}"
    h = int(hashlib.sha256(seed_str.encode()).hexdigest(), 16)

    skin = _pick(SKIN_TONES, h, 0)
    hair_color = _pick(HAIR_COLORS, h, 8)
    hair_styles = MALE_HAIR_STYLES if gender == "m" else FEMALE_HAIR_STYLES
    hair_style = _pick(hair_styles, h, 16)
    headwear = _pick(HEADWEAR, h, 24)
    polo = _pick(POLO_COLORS, h, 32)

    gender_word = "male" if gender == "m" else "female"
    return (
        f"{gender_word} football coach, {skin}, {hair_color} {hair_style}, "
        f"{headwear}, {polo}, portrait, standing pose"
    )


def pool_face_path(index: int, gender: str,
                   faces_dir: str = _DEFAULT_COACH_FACES_DIR) -> Path:
    return Path(faces_dir) / f"coach_{gender}_{index:03d}.png"


# ── Pool inspection ──

def get_pool_size(faces_dir: str = _DEFAULT_COACH_FACES_DIR,
                  gender: str | None = None) -> int | dict:
    """Count coach faces.  If gender is None, return {"m": N, "f": N}."""
    d = Path(faces_dir)
    if not d.is_dir():
        return {"m": 0, "f": 0} if gender is None else 0
    if gender is not None:
        pat = re.compile(rf"coach_{gender}_\d{{3}}\.png$")
        return sum(1 for f in d.iterdir() if pat.match(f.name))
    m = sum(1 for f in d.iterdir() if re.match(r"coach_m_\d{3}\.png$", f.name))
    f_count = sum(1 for f in d.iterdir() if re.match(r"coach_f_\d{3}\.png$", f.name))
    return {"m": m, "f": f_count}


def get_coach_face_index(coach_id: str, pool_size: int) -> int | None:
    if pool_size == 0:
        return None
    h = int(hashlib.sha256(coach_id.encode()).hexdigest(), 16)
    return h % pool_size


def get_coach_face_url(coach_id: str, gender: str, pool_sizes: dict,
                       faces_dir: str = _DEFAULT_COACH_FACES_DIR) -> str | None:
    """Return the static URL for a coach's face, or None if no pool."""
    # Map gender to pool key: male -> m, female -> f, neutral -> f (default)
    g = "m" if gender == "male" else "f"
    n = pool_sizes.get(g, 0)
    idx = get_coach_face_index(coach_id, n)
    if idx is None:
        return None
    return f"/stats/static/coach_faces/coach_{g}_{idx:03d}.png"


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


def generate_pool_face(
    index: int,
    gender: str,
    faces_dir: str = _DEFAULT_COACH_FACES_DIR,
    api_key: str | None = None,
    force: bool = False,
) -> Path:
    api_key = api_key or os.environ.get("PIXELLAB_API_KEY", "")
    if not api_key:
        raise ValueError("PIXELLAB_API_KEY not set")

    out_path = pool_face_path(index, gender, faces_dir)
    if not force and out_path.is_file():
        return out_path

    out_path.parent.mkdir(parents=True, exist_ok=True)

    prompt = build_coach_prompt(index, gender)
    seed_hash = int(hashlib.sha256(f"viperball-coach-{gender}-{index}".encode()).hexdigest(), 16)
    seed = seed_hash % (2**31)

    png_bytes = _call_pixellab(prompt, seed, api_key)
    out_path.write_bytes(png_bytes)
    return out_path


async def generate_pool(
    count: int = 150,
    faces_dir: str = _DEFAULT_COACH_FACES_DIR,
    api_key: str | None = None,
    force: bool = False,
    concurrency: int = 4,
) -> dict:
    """Generate coach face pools for both genders.

    `count` faces are generated per gender (so 150 means 150 male + 150 female).
    Returns {"generated": N, "skipped": N, "failed": [...]}.
    """
    api_key = api_key or os.environ.get("PIXELLAB_API_KEY", "")
    sem = asyncio.Semaphore(concurrency)
    results: dict = {"generated": [], "skipped": [], "failed": []}

    total = count * 2
    done_count = 0

    async def _gen(idx: int, g: str):
        nonlocal done_count
        out_path = pool_face_path(idx, g, faces_dir)
        if not force and out_path.is_file():
            results["skipped"].append(f"{g}_{idx}")
            done_count += 1
            return
        async with sem:
            try:
                await asyncio.to_thread(
                    generate_pool_face, idx, g, faces_dir, api_key, force
                )
                results["generated"].append(f"{g}_{idx}")
            except Exception as e:
                results["failed"].append({"index": f"{g}_{idx}", "error": str(e)})
            done_count += 1
            if done_count % 10 == 0 or done_count == total:
                log.info("Coach face pool progress: %d/%d (generated=%d, failed=%d)",
                         done_count, total, len(results["generated"]),
                         len(results["failed"]))

    tasks = []
    for g in ("m", "f"):
        for i in range(count):
            tasks.append(_gen(i, g))
    await asyncio.gather(*tasks)
    return results


# ── CLI entry point ──

if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Generate viperball pixel-art coach face pool via PixelLab API"
    )
    parser.add_argument(
        "--count", type=int, default=150,
        help="Number of faces PER GENDER to generate (default: 150)",
    )
    parser.add_argument(
        "--dir", default=_DEFAULT_COACH_FACES_DIR,
        help="Output directory for coach face PNGs",
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

    sizes = get_pool_size(args.dir)
    print(f"Coach face pool: {sizes} existing faces in {args.dir}")
    print(f"Generating up to {args.count} faces per gender (concurrency={args.concurrency})...")

    results = asyncio.run(generate_pool(
        count=args.count,
        faces_dir=args.dir,
        api_key=api_key,
        force=args.force,
        concurrency=args.concurrency,
    ))

    print(f"Done: {len(results['generated'])} generated, "
          f"{len(results['skipped'])} skipped, "
          f"{len(results['failed'])} failed")
    if results["failed"]:
        for f in results["failed"][:5]:
            print(f"  FAIL coach_{f['index']}: {f['error']}")
