"""
PixelLab Face Pool for Viperball

Pre-generates a reusable pool of pixel-art portraits via the PixelLab API.
Faces are saved as face_000.png … face_N.png and persist across dynasty
resets.  Any player in any save maps to a face deterministically:

    face_index = hash(player_id) % pool_size

Usage:
    # Generate the pool (one-time, or to grow it):
    python -m engine.face_generator --count 200

    # In code — look up which face a player gets:
    from engine.face_generator import get_face_index, get_pool_size
    idx = get_face_index(player_id)         # e.g. 42
    # template uses: /stats/static/faces/face_042.png

Requires PIXELLAB_API_KEY environment variable for generation.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import os
import re
from pathlib import Path
from typing import List, Optional

import requests as _requests

PIXELLAB_API_URL = "https://api.pixellab.ai/v1/generate-image-bitforge"
FACE_SIZE = 24  # 24x24 — chunky NES / Retro Bowl style

_DEFAULT_FACES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "stats_site", "static", "faces"
)


# ── Appearance trait pools (simple traits for chunky retro faces) ──

SKIN_TONES = [
    "light skin", "medium skin", "olive skin",
    "tan skin", "brown skin", "dark brown skin",
]

HAIR_COLORS = [
    "black", "brown", "red", "blonde", "dark brown",
]

HELMET_COLORS = [
    "white helmet", "red helmet", "blue helmet", "green helmet",
    "gold helmet", "orange helmet", "purple helmet", "gray helmet",
]


def _pick(options: list, h: int, shift: int) -> str:
    return options[(h >> shift) % len(options)]


def build_pool_prompt(index: int) -> str:
    """Build a unique PixelLab prompt for face slot `index`."""
    h = int(hashlib.sha256(f"viperball-face-{index}".encode()).hexdigest(), 16)

    skin = _pick(SKIN_TONES, h, 0)
    hair_color = _pick(HAIR_COLORS, h, 8)
    helmet = _pick(HELMET_COLORS, h, 16)

    return (
        f"female football player, {skin}, {hair_color} hair, "
        f"{helmet}, sports jersey, running pose"
    )


def pool_face_path(index: int, faces_dir: str = _DEFAULT_FACES_DIR) -> Path:
    """Path for a specific pool face: face_042.png"""
    return Path(faces_dir) / f"face_{index:03d}.png"


# ── Pool inspection ──

def get_pool_size(faces_dir: str = _DEFAULT_FACES_DIR) -> int:
    """Count how many pool faces currently exist."""
    d = Path(faces_dir)
    if not d.is_dir():
        return 0
    return sum(1 for f in d.iterdir() if re.match(r"face_\d{3}\.png$", f.name))


def get_face_index(player_id: str, pool_size: int = 0,
                   faces_dir: str = _DEFAULT_FACES_DIR) -> Optional[int]:
    """
    Map a player_id to a face index.  Returns None if pool is empty.
    """
    n = pool_size or get_pool_size(faces_dir)
    if n == 0:
        return None
    h = int(hashlib.sha256(player_id.encode()).hexdigest(), 16)
    return h % n


def get_face_url(player_id: str, pool_size: int = 0,
                 faces_dir: str = _DEFAULT_FACES_DIR) -> Optional[str]:
    """Return the static URL path for a player's face, or None if no pool."""
    idx = get_face_index(player_id, pool_size, faces_dir)
    if idx is None:
        return None
    return f"/stats/static/faces/face_{idx:03d}.png"


# ── PixelLab API ──

def _call_pixellab(prompt: str, seed: int, api_key: str) -> bytes:
    """Call PixelLab BitForge API and return raw PNG bytes."""
    payload = {
        "description": prompt,
        "negative_description": "fantasy, realistic, 3d, smooth, gradient, portrait, headshot, face only",
        "image_size": {"width": FACE_SIZE, "height": FACE_SIZE},
        "text_guidance_scale": 8.0,
        "outline": "single color black outline",
        "shading": "flat shading",
        "detail": "low detail",
        "no_background": True,
        "view": "side",
        "direction": "east",
        "seed": seed,
    }

    resp = _requests.post(
        PIXELLAB_API_URL,
        json=payload,
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=30,
    )

    if resp.status_code != 200:
        raise RuntimeError(
            f"PixelLab API error {resp.status_code}: {resp.text[:200]}"
        )

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
    faces_dir: str = _DEFAULT_FACES_DIR,
    api_key: Optional[str] = None,
    force: bool = False,
) -> Path:
    """Generate a single pool face (synchronous). Skips if it already exists."""
    api_key = api_key or os.environ.get("PIXELLAB_API_KEY", "")
    if not api_key:
        raise ValueError("PIXELLAB_API_KEY not set")

    out_path = pool_face_path(index, faces_dir)
    if not force and out_path.is_file():
        return out_path

    out_path.parent.mkdir(parents=True, exist_ok=True)

    prompt = build_pool_prompt(index)
    seed_hash = int(hashlib.sha256(f"viperball-face-{index}".encode()).hexdigest(), 16)
    seed = seed_hash % (2**31)

    png_bytes = _call_pixellab(prompt, seed, api_key)
    out_path.write_bytes(png_bytes)
    return out_path


async def generate_pool(
    count: int = 200,
    faces_dir: str = _DEFAULT_FACES_DIR,
    api_key: Optional[str] = None,
    force: bool = False,
    concurrency: int = 4,
) -> dict:
    """
    Generate the full face pool asynchronously.

    Returns {"generated": [indices], "skipped": [indices], "failed": [...]}.
    """
    api_key = api_key or os.environ.get("PIXELLAB_API_KEY", "")
    sem = asyncio.Semaphore(concurrency)
    results: dict = {"generated": [], "skipped": [], "failed": []}

    async def _gen(idx: int):
        out_path = pool_face_path(idx, faces_dir)
        if not force and out_path.is_file():
            results["skipped"].append(idx)
            return
        async with sem:
            try:
                await asyncio.to_thread(
                    generate_pool_face, idx, faces_dir, api_key, force
                )
                results["generated"].append(idx)
            except Exception as e:
                results["failed"].append({"index": idx, "error": str(e)})

    await asyncio.gather(*[_gen(i) for i in range(count)])
    return results


# ── CLI entry point ──

if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Generate the viperball pixel-art face pool via PixelLab API"
    )
    parser.add_argument(
        "--count", type=int, default=200,
        help="Number of faces to generate (default: 200)",
    )
    parser.add_argument(
        "--dir", default=_DEFAULT_FACES_DIR,
        help="Output directory for face PNGs",
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
    print(f"Face pool: {existing} existing faces in {args.dir}")
    print(f"Generating up to {args.count} faces (concurrency={args.concurrency})...")

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
            print(f"  FAIL face_{f['index']:03d}: {f['error']}")
