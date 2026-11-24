"""Write the penalty table in RULES.md from engine PENALTY_CATALOG.

Run after changing the catalog:  python scripts/build_rules_penalty_table.py
tests/test_rules_doc.py fails if the table and the catalog disagree.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine.game_engine import PENALTY_CATALOG  # noqa: E402

PHASE_TITLES = {
    "pre_snap": "Before the snap",
    "during_play_run": "During a run",
    "during_play_lateral": "During a lateral play",
    "during_play_kick_pass": "During a kick pass",
    "during_play_kick": "During a punt, snap kick or field goal",
    "post_play": "After the play",
}
START = "<!-- PENALTY_TABLE -->"
END = "<!-- /PENALTY_TABLE -->"


def notes(p):
    out = []
    if p.get("auto_first"):
        out.append("Automatic first down")
    if p.get("loss_of_down"):
        out.append("Loss of down")
    if p.get("punt_only"):
        out.append("Punts only")
    return ", ".join(out)


def build_table():
    lines = [START, ""]
    for phase, entries in PENALTY_CATALOG.items():
        lines.append(f"### {PHASE_TITLES.get(phase, phase)}")
        lines.append("")
        lines.append("| Foul | Yards | On | Notes |")
        lines.append("|---|---|---|---|")
        for p in entries:
            lines.append(f"| {p['name']} | {p['yards']} | {p['on'].capitalize()} | {notes(p)} |")
        lines.append("")
    lines.append(END)
    return "\n".join(lines)


def main():
    path = os.path.join(ROOT, "RULES.md")
    text = open(path, encoding="utf-8").read()
    table = build_table()
    if END in text:
        text = re.sub(re.escape(START) + r".*?" + re.escape(END), table, text, flags=re.S)
    else:
        text = text.replace(START, table)
    open(path, "w", encoding="utf-8").write(text)


if __name__ == "__main__":
    main()
