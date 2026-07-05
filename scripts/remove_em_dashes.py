#!/usr/bin/env python3
"""Replace em-dashes and en-dash punctuation across edgeware-u9 source files."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SKIP_DIRS = {".git", "node_modules", ".playwright-browsers", "test-results"}
TEXT_SUFFIXES = {
    ".html",
    ".py",
    ".js",
    ".md",
    ".txt",
    ".csv",
    ".json",
}

EM = "\u2014"
EN = "\u2013"
MDASH = "&mdash;"


def transform_mdash_entities(text: str) -> tuple[str, int]:
    """Replace &mdash; in user-facing text (still renders as em-dash in browsers)."""
    count = 0
    specifics = [
        (" &mdash; Ov ", ", Ov "),
        (" &mdash; Batting", " · Batting"),
        (" &mdash; Bowling", " · Bowling"),
        (" &mdash; WIN", " · WIN"),
        ("Next Match &mdash; ", "Next Match · "),
        ("Softball &mdash; Sunday", "Softball · Sunday"),
        ("Term 2026 &mdash; U9", "Term 2026 · U9"),
        ('class="c">&mdash;</td>', 'class="c">-</td>'),
        ('class="c scr">&mdash;</td>', 'class="c scr">-</td>'),
    ]
    for old, new in specifics:
        n = text.count(old)
        if n:
            text = text.replace(old, new)
            count += n
    # Match selector / fixture labels: "Hayes &mdash; 31 May" -> "Hayes · 31 May"
    new_text, n = re.subn(
        r"(\w[\w ]*?) &mdash; (\d{1,2} \w{3})",
        r"\1 · \2",
        text,
    )
    if n:
        text = new_text
        count += n
    # Remaining separator uses of &mdash;
    new_text, n = re.subn(r" &mdash; ", " · ", text)
    if n:
        text = new_text
        count += n
    return text, count


def transform(text: str) -> tuple[str, int]:
    original = text
    count = 0

    def sub(pattern: str, repl: str, s: str, *, flags: int = 0) -> str:
        nonlocal count
        new, n = re.subn(pattern, repl, s, flags=flags)
        count += n
        return new

    # Specific em-dash patterns (longest / most specific first)
    specifics = [
        ("Walkover" + EM + " no scorecard", "Walkover: no scorecard"),
        ("Cricket Summer Term 2026" + EM + " U9 Softball Sunday Fixtures", "Cricket Summer Term 2026 · U9 Softball Sunday Fixtures"),
        ("U9 Softball" + EM + " Match Rules & Scoring Guide", "U9 Softball · Match Rules & Scoring Guide"),
        ("Edgware CC" + EM + " U9 Softball 2026", "Edgware CC · U9 Softball 2026"),
        ("Scores pending</strong>" + EM + " ", "Scores pending</strong>: "),
        ("BOWLING SUMMARY" + EM + " ", "BOWLING SUMMARY · "),
        ("Home" + EM + " Canons High School", "Home · Canons High School"),
        (EM + " Innings ", " · Innings "),
        (EM + " Batting", " · Batting"),
        (EM + " Bowling", " · Bowling"),
        ("th Over" + EM + " ", "th Over · "),
        (EM + " Ov ", ", Ov "),
        (EM + " no wicket", ": no wicket"),
        ("catch dropped" + EM + " ", "catch dropped: "),
        ("FOUR" + EM + " overthrow", "FOUR: overthrow"),
        ("FOUR" + EM + " hat-trick", "FOUR: hat-trick"),
        ("1 run" + EM + " catch dropped", "1 run, catch dropped"),
        ("pairs re-out" + EM + " no wicket", "pairs re-out: no wicket"),
        ("Brilliant fielding" + EM + " ", "Brilliant fielding: "),
    ]
    for old, new in specifics:
        n = text.count(old)
        if n:
            text = text.replace(old, new)
            count += n

    # INNINGS headers (variable spacing)
    text = sub(rf"INNINGS\s+(\d+)\s+{EM}\s+", r"INNINGS \1 · ", text)
    text = sub(rf"Over\s+(\d+)\s+{EM}\s+", r"Over \1 · ", text)

    # Remaining em-dash clause breaks (space-delimited)
    text = sub(rf" {EM} ", ", ", text)

    # Lone em-dashes (labels without spaces)
    text = sub(rf"([^ \n]){EM}([^ \n])", r"\1 · \2", text)

    # Any leftover em-dashes
    n = text.count(EM)
    if n:
        text = text.replace(EM, " · ")
        count += n

    # En-dash ranges and punctuation
    text = sub(r"(\d)&ndash;(\d)", r"\1-\2", text)
    text = sub(r"(\d)" + EN + r"(\d)", r"\1-\2", text)
    text = sub(r"(M\d+)" + EN + r"(M\d+)", r"\1-\2", text)
    text = sub(r"(B\d+)" + EN + r"(B\d+)", r"\1-\2", text)
    text = sub(r"(ov\s+\d+)" + EN + r"(\d+)", r"\1-\2", text, flags=re.I)
    text = sub(r"(overs\s+\d+)" + EN + r"(\d+)", r"\1-\2", text, flags=re.I)
    text = sub(r"(Rows\s+\d+)" + EN + r"(\d+)", r"\1-\2", text)
    text = sub(r"(\d+)" + EN + r"(\d+)", r"\1-\2", text)

    # Comments / prose en-dashes like "M2-M6 plus"
    n = text.count(EN)
    if n:
        text = text.replace(EN, "-")
        count += n

    text, mdash_n = transform_mdash_entities(text)
    count += mdash_n

    return text, count


def iter_files() -> list[Path]:
    out: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if path.name == "remove_em_dashes.py":
            continue
        out.append(path)
    return sorted(out)


def main() -> int:
    total = 0
    touched: list[tuple[str, int]] = []
    for path in iter_files():
        raw = path.read_text(encoding="utf-8")
        new, n = transform(raw)
        if new != raw:
            path.write_text(new, encoding="utf-8")
            touched.append((str(path.relative_to(ROOT)), n))
            total += n
    for rel, n in touched:
        print(f"{rel}: {n}")
    print(f"Touched {len(touched)} files, ~{total} replacements")
    remaining_em = sum(p.read_text(encoding="utf-8").count(EM) for p in iter_files())
    remaining_en = sum(p.read_text(encoding="utf-8").count(EN) for p in iter_files())
    remaining_mdash = sum(p.read_text(encoding="utf-8").count(MDASH) for p in iter_files())
    print(f"Remaining em-dashes: {remaining_em}, en-dashes: {remaining_en}, &mdash;: {remaining_mdash}")
    return 1 if remaining_em or remaining_en or remaining_mdash else 0


if __name__ == "__main__":
    sys.exit(main())
