#!/usr/bin/env python3
"""Add wicket counts to innings summary score lines in index.html (M2, M4, M5)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"

import sys

sys.path.insert(0, str(ROOT / "scripts"))
from innings_score import STATIC_MATCH_INNINGS, patch_summary_block  # noqa: E402


def main() -> None:
    html = INDEX.read_text(encoding="utf-8")
    for match_id, innings in STATIC_MATCH_INNINGS.items():
        html = patch_summary_block(html, match_id, innings)
    INDEX.write_text(html, encoding="utf-8")
    print(f"Updated innings score lines for {', '.join(STATIC_MATCH_INNINGS)} in {INDEX}")


if __name__ == "__main__":
    main()
