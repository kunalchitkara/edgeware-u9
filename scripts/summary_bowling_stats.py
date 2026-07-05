#!/usr/bin/env python3
"""Season bowling wickets/figures from match summary bowling tables."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
MATCH_IDS = ("m2", "m4", "m5", "m6", "m7")
ECC_NAMES = {
    "Ariyan",
    "Qaim",
    "Veer",
    "Avyaan",
    "Kaiyan",
    "Viaan",
    "Krish",
    "Taran",
    "Drish",
    "Shyam",
    "Aanya",
}


@dataclass(frozen=True)
class MatchBowlingFigure:
    name: str
    runs: int
    wickets: int


def _match_summary_block(html: str, match_id: str) -> str:
    start = html.find(f'id="match-{match_id}-summary"')
    if start == -1:
        return ""
    end = html.find(f'id="match-{match_id}-bbb"', start)
    if end == -1:
        return html[start:]
    return html[start:end]


def _extract_ecc_bowling_table(block: str) -> str:
    marker = "Edgware CC · Bowling"
    at = block.find(marker)
    if at == -1:
        return ""
    after = block[at:]
    m = re.search(
        r'<table class="sctbl">\s*<thead><tr><th>Bowler</th>.*?</thead>\s*<tbody>(.*?)</tbody>',
        after,
        flags=re.DOTALL,
    )
    return m.group(1) if m else ""


def _parse_bowling_rows(table_body: str) -> list[MatchBowlingFigure]:
    out: list[MatchBowlingFigure] = []
    for row_html in re.findall(r"<tr>(.*?)</tr>", table_body, flags=re.DOTALL):
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row_html, flags=re.DOTALL)
        if len(cells) < 4:
            continue
        values = [re.sub(r"<[^>]+>", "", c).strip() for c in cells]
        name = values[0]
        if name not in ECC_NAMES:
            continue
        try:
            runs = int(values[2])
            wickets = int(values[3])
        except ValueError:
            continue
        out.append(MatchBowlingFigure(name=name, runs=runs, wickets=wickets))
    return out


def match_bowling_figures_from_summaries() -> dict[str, list[MatchBowlingFigure]]:
    html = INDEX.read_text(encoding="utf-8")
    out: dict[str, list[MatchBowlingFigure]] = {}
    for match_id in MATCH_IDS:
        block = _match_summary_block(html, match_id)
        body = _extract_ecc_bowling_table(block)
        out[match_id.upper()] = _parse_bowling_rows(body)
    return out


def season_wickets_from_summaries() -> dict[str, int]:
    totals = {name: 0 for name in ECC_NAMES}
    for _match, rows in match_bowling_figures_from_summaries().items():
        for row in rows:
            totals[row.name] += row.wickets
    return totals


def best_figures_from_summaries() -> dict[str, tuple[str, int, int]]:
    best: dict[str, tuple[str, int, int]] = {}
    for match, rows in match_bowling_figures_from_summaries().items():
        for row in rows:
            if row.wickets <= 0:
                continue
            current = best.get(row.name)
            candidate = (match, row.wickets, row.runs)
            if current is None or candidate[1] > current[1] or (
                candidate[1] == current[1] and candidate[2] < current[2]
            ):
                best[row.name] = candidate
    return best
