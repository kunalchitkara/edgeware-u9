#!/usr/bin/env python3
"""Innings score line format for match summary headers."""

from __future__ import annotations

import re


def format_innings_score(runs: int, wickets: int, overs: int) -> str:
    """Return ``{runs} - {wickets} ({overs} Ov)`` for summary panel headers."""
    return f"{runs} - {wickets} ({overs} Ov)"


# (runs, wickets, overs) per innings — sourced from summary totals / fall-of-wickets.
STATIC_MATCH_INNINGS: dict[str, list[tuple[int, int, int]]] = {
    # Hayes vs ECC (31 May) — wicket counts from innings total rows.
    "m4": [(281, 9, 20), (230, 15, 20)],
    # H Manor vs ECC (10 May) — inn1: 3 FoW; inn2: 4 FoW (Pranil out twice).
    "m2": [(297, 3, 16), (265, 4, 16)],
    # ECC vs Harefield (7 Jun) — inn1: 4 wkts total row; inn2: 3 bowler + 7 run-outs.
    "m5": [(315, 4, 20), (307, 10, 20)],
    "m6": [(263, 4, 16), (308, 3, 16)],
    "m7": [(253, 4, 16), (192, 6, 16)],
}

OLD_SCORE_RE = re.compile(r"^(\d+) \((\d+) Ov\)$")


def patch_summary_block(html: str, match_id: str, innings: list[tuple[int, int, int]]) -> str:
    """Replace batting-innings ``sct`` score lines inside one match summary block."""
    start = html.find(f'id="match-{match_id}-summary"')
    if start < 0:
        raise SystemExit(f"match-{match_id}-summary not found")
    end = html.find(f'id="match-{match_id}-bbb"', start)
    if end < 0:
        raise SystemExit(f"match-{match_id}-bbb not found")

    block = html[start:end]
    idx = 0

    def repl(m: re.Match[str]) -> str:
        nonlocal idx
        if idx >= len(innings):
            return m.group(0)
        runs, wickets, overs = innings[idx]
        idx += 1
        expected = format_innings_score(runs, wickets, overs)
        if m.group(1) == expected:
            return m.group(0)
        return f'<span class="sct">{expected}</span>'

    new_block = re.sub(
        r'<span class="sct">([^<]+)</span>',
        repl,
        block,
        count=len(innings),
    )
    if idx != len(innings):
        raise SystemExit(f"Expected {len(innings)} innings scores in match-{match_id}-summary, found {idx}")
    return html[:start] + new_block + html[end:]
