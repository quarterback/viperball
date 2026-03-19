"""
PixelLab Face Generator for Viperball

Generates deterministic pixel-art player portraits using the PixelLab API.
Appearance traits (hair, skin, expression, etc.) are derived from a hash of
the player_id so the same player always gets the same face.

Usage:
    from engine.face_generator import generate_face, generate_faces_batch

    # Single player (sync)
    generate_face_sync(player_card, output_dir="stats_site/static/faces")

    # Batch (async, for the API endpoint)
    await generate_faces_batch(player_cards, output_dir="stats_site/static/faces")

Requires PIXELLAB_API_KEY environment variable.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import os
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

import requests as _requests

if TYPE_CHECKING:
    from engine.player_card import PlayerCard

PIXELLAB_API_URL = "https://api.pixellab.ai/v2/create-image-bitforge"
FACE_SIZE = 48  # 48x48 pixel art portraits


def _hash_player(player_id: str) -> int:
    """Deterministic 64-bit hash from player_id."""
    return int(hashlib.sha256(player_id.encode()).hexdigest(), 16)


def _pick(options: list, h: int, shift: int) -> str:
    """Deterministically pick from a list using bit-shifted hash."""
    return options[(h >> shift) % len(options)]


# ── Appearance trait pools ──

SKIN_TONES = [
    "light skin", "fair skin", "medium skin", "olive skin",
    "tan skin", "brown skin", "dark brown skin", "deep brown skin",
]

HAIR_COLORS = [
    "black hair", "dark brown hair", "brown hair", "auburn hair",
    "red hair", "blonde hair", "dark blonde hair", "light brown hair",
]

HAIR_STYLES = [
    "short hair", "buzzcut", "medium length hair", "long ponytail",
    "braids", "cornrows", "afro", "bun", "pixie cut",
    "shoulder length hair", "high ponytail", "dreadlocks",
]

EXPRESSIONS = [
    "determined expression", "confident smile", "intense stare",
    "focused expression", "serious look", "slight grin",
]

FACE_SHAPES = [
    "round face", "oval face", "angular face", "heart-shaped face",
]

ACCESSORIES = [
    "", "", "",  # most players have no accessory (weighted)
    "headband", "eye black", "face paint stripes",
]


def build_face_prompt(player: "PlayerCard") -> str:
    """Build a PixelLab prompt from deterministic player appearance traits."""
    h = _hash_player(player.player_id)

    skin = _pick(SKIN_TONES, h, 0)
    hair_color = _pick(HAIR_COLORS, h, 8)
    hair_style = _pick(HAIR_STYLES, h, 16)
    expression = _pick(EXPRESSIONS, h, 24)
    face_shape = _pick(FACE_SHAPES, h, 32)
    accessory = _pick(ACCESSORIES, h, 40)

    parts = [
        "pixel art portrait of a female athlete",
        "front-facing headshot",
        skin,
        f"{hair_color} {hair_style}",
        face_shape,
        expression,
    ]
    if accessory:
        parts.append(accessory)

    parts.append("sports jersey, clean background")
    parts.append("16-bit retro game style")

    return ", ".join(parts)


def face_path(player_id: str, output_dir: str) -> Path:
    """Return the expected file path for a player's face image."""
    return Path(output_dir) / f"{player_id}.png"


def has_face(player_id: str, output_dir: str) -> bool:
    """Check if a face image already exists (cached)."""
    return face_path(player_id, output_dir).is_file()


def _call_pixellab(prompt: str, seed: int, api_key: str) -> bytes:
    """Call PixelLab BitForge API and return raw PNG bytes."""
    payload = {
        "description": prompt,
        "image_size": {"width": FACE_SIZE, "height": FACE_SIZE},
        "text_guidance_scale": 8.0,
        "no_background": True,
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
    # Try multiple response shapes (API may vary)
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


def generate_face_sync(
    player: "PlayerCard",
    output_dir: str = "stats_site/static/faces",
    api_key: Optional[str] = None,
    force: bool = False,
) -> Optional[Path]:
    """
    Generate a pixel-art face for a single player (synchronous).

    Returns the path to the saved PNG, or None on failure.
    Skips generation if the face already exists (unless force=True).
    """
    api_key = api_key or os.environ.get("PIXELLAB_API_KEY", "")
    if not api_key:
        raise ValueError(
            "PIXELLAB_API_KEY not set. "
            "Set the environment variable or pass api_key directly."
        )

    out_path = face_path(player.player_id, output_dir)
    if not force and out_path.is_file():
        return out_path

    out_path.parent.mkdir(parents=True, exist_ok=True)

    prompt = build_face_prompt(player)
    seed = _hash_player(player.player_id) % (2**31)

    png_bytes = _call_pixellab(prompt, seed, api_key)
    out_path.write_bytes(png_bytes)
    return out_path


async def generate_face(
    player: "PlayerCard",
    output_dir: str = "stats_site/static/faces",
    api_key: Optional[str] = None,
    force: bool = False,
) -> Optional[Path]:
    """Async wrapper around generate_face_sync."""
    return await asyncio.to_thread(
        generate_face_sync, player, output_dir, api_key, force
    )


async def generate_faces_batch(
    players: List["PlayerCard"],
    output_dir: str = "stats_site/static/faces",
    api_key: Optional[str] = None,
    force: bool = False,
    concurrency: int = 4,
) -> dict:
    """
    Generate faces for a list of players with concurrency control.

    Returns {"generated": [...], "skipped": [...], "failed": [...]}.
    """
    api_key = api_key or os.environ.get("PIXELLAB_API_KEY", "")
    sem = asyncio.Semaphore(concurrency)
    results = {"generated": [], "skipped": [], "failed": []}

    async def _gen(p: "PlayerCard"):
        if not force and has_face(p.player_id, output_dir):
            results["skipped"].append(p.player_id)
            return
        async with sem:
            try:
                await generate_face(p, output_dir, api_key, force=force)
                results["generated"].append(p.player_id)
            except Exception as e:
                results["failed"].append(
                    {"player_id": p.player_id, "error": str(e)}
                )

    await asyncio.gather(*[_gen(p) for p in players])
    return results
