"""The NiceGUI app (nicegui_app/ and ui/) is deprecated and frozen. Interface
work goes in stats_site/. This test fails if any file in the frozen app
changes. Do not update the hash to make it pass; see AGENTS.md."""
import hashlib
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
FROZEN_HASH = "aa7f4f5b13b3ee7709c486e705bc54c08eadf8f82218f78d52c07a4d1b30617b"


def _hash() -> str:
    h = hashlib.sha256()
    files = list((ROOT / "nicegui_app").rglob("*")) + list((ROOT / "ui").rglob("*"))
    for p in sorted(files):
        if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc":
            h.update(str(p.relative_to(ROOT)).encode())
            h.update(p.read_bytes())
    return h.hexdigest()


def test_nicegui_app_is_frozen():
    assert _hash() == FROZEN_HASH, (
        "nicegui_app/ or ui/ changed. The NiceGUI app is deprecated and frozen: "
        "put interface work in stats_site/ instead (see AGENTS.md).")
