"""Hashes that are the same in every Python process.

Python's built-in hash() of a string changes each time the interpreter
starts (PYTHONHASHSEED), so any seed or index built from it changes on
every restart: schedules, referee crews, faces, banners and benchmark
results drift between runs. Use stable_hash for anything that must repeat.
"""

import zlib


def stable_hash(value) -> int:
    """A non-negative 32-bit hash of str(value) that never changes."""
    return zlib.crc32(str(value).encode("utf-8"))
