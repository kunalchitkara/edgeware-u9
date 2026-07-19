#!/usr/bin/env python3
"""Refresh ECC bowling summary R/ECO columns from source match data (runs conceded)."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"

sys.path.insert(0, str(ROOT / "scripts"))
from bowling_display import eco_cell, runs_conceded  # noqa: E402
from build_m6 import simulate_innings  # noqa: E402
from gen_bbb import MATCHES, ROOT as GEN_ROOT, load_sheet  # noqa: E402
from bowling_stats import _accumulate_match_from_sheet, _init_state  # noqa: E402

SHEET_MATCHES = ("m2", "m4", "m5")
ROW_RE = re.compile(
    r"<tr><td class=\"scb\">(\w+)</td><td class=\"c\">(\d+(?:\.\d+)?)</td>"
    r"<td class=\"c\">(\d+)</td>"
    r"<td class=\"c\">(?:<strong>)?(\d+)(?:</strong>)?</td>"
    r"<td class=\"c\">(\d+)</td><td class=\"c\">(\d+)</td>"
    r"<td class=\"c[^\"]*\">\d+(?:\.\d+)?</td>"
    r"<td class=\"c\">(\d+)</td></tr>"
)

# Verified pre-M10 summary R values (runs conceded, not gross). Sheet pipeline does not
# yet emit M2/M5 ECC bowling figures, so these remain the source of truth for those matches.
CANONICAL_SHEET_BOWLING: dict[str, dict[str, tuple[int, int, float]]] = {
    "m2": {
        "Ariyan": (3, 0, 2.0),
        "Aanya": (5, 1, 2.0),
        "Krish": (5, 1, 2.0),
        "Avyaan": (8, 1, 2.0),
        "Veer": (8, 0, 2.0),
        "Kaiyan": (11, 0, 2.0),
        "Viaan": (12, 0, 2.0),
        "Qaim": (17, 0, 2.0),
    },
    "m5": {
        "Krish": (10, 1, 2.0),
        "Avyaan": (11, 1, 2.0),
        "Viaan": (9, 0, 2.0),
        "Shyam": (12, 0, 2.0),
        "Veer": (13, 0, 2.0),
        "Drish": (12, 0, 2.0),
        "Ariyan": (13, 0, 2.0),
        "Aanya": (15, 1, 2.0),
        "Taran": (17, 0, 2.0),
        "Qaim": (25, 0, 2.0),
    },
}


def _sim_bowling(match_id: str) -> dict[str, tuple[int, int, float]]:
    """name -> (runs_conceded, wickets, overs_float)."""
    cfg = MATCHES[match_id]
    if cfg.get("local") and (GEN_ROOT / cfg["local"]).exists():
        out: dict[str, tuple[int, int, float]] = {}
        data = json.loads((GEN_ROOT / cfg["local"]).read_text(encoding="utf-8"))
        for inn in data["innings"]:
            if "Edgware" in inn.get("batting", ""):
                continue
            for b in simulate_innings(inn)["bowling_summary"]:
                out[b["name"]] = (b["runs"], b["wickets"], float(b["overs"]))
        return out

    state = _init_state()
    _accumulate_match_from_sheet(state, match_id, load_sheet(cfg["gid"]))
    out = {}
    for name, season in state.by_player.items():
        if match_id.upper() not in season.matches:
            continue
        overs = season.balls / 6.0 if season.balls else 0.0
        out[name] = (season.runs, season.wickets, overs)
    return out


def _match_figures(match_id: str) -> dict[str, tuple[int, int, float]]:
    figures = _sim_bowling(match_id)
    if figures:
        return figures
    return dict(CANONICAL_SHEET_BOWLING.get(match_id, {}))


def _patch_table_body(body: str, figures: dict[str, tuple[int, int, float]]) -> str:
    def repl(m: re.Match[str]) -> str:
        name, overs_txt, old_r, wkts, wd, nb, dots = m.groups()
        wkts_i = int(wkts)
        if name in figures:
            ball_runs, wkts_i, overs = figures[name]
        else:
            ball_runs, overs = int(old_r), float(overs_txt)
        display_r = runs_conceded(ball_runs, wkts_i)
        wcell = f"<strong>{wkts_i}</strong>" if wkts_i else "0"
        overs_val = float(overs_txt) if "." in overs_txt else int(overs_txt)
        return (
            f'<tr><td class="scb">{name}</td><td class="c">{overs_txt}</td>'
            f'<td class="c">{display_r}</td><td class="c">{wcell}</td>'
            f'<td class="c">{wd}</td><td class="c">{nb}</td>'
            f'{eco_cell(ball_runs, wkts_i, overs_val)}'
            f'<td class="c">{dots}</td></tr>'
        )

    return ROW_RE.sub(repl, body)


def patch_match(html: str, match_id: str) -> str:
    start = html.find(f'id="match-{match_id}-summary"')
    if start == -1:
        return html
    end = html.find(f'id="match-{match_id}-bbb"', start)
    if end == -1:
        return html
    block = html[start:end]
    marker = "Edgware CC · Bowling"
    at = block.find(marker)
    if at == -1:
        return html
    tb = re.search(r"<tbody>(.*?)</tbody>", block[at:], flags=re.DOTALL)
    if not tb:
        return html
    old_body = tb.group(1)
    figures = _match_figures(match_id)
    new_body = _patch_table_body(old_body, figures)
    if new_body == old_body:
        return html
    new_block = block[: at + tb.start(1)] + new_body + block[at + tb.end(1) :]
    return html[:start] + new_block + html[end:]


def main() -> None:
    html = INDEX.read_text(encoding="utf-8")
    for match_id in SHEET_MATCHES:
        html = patch_match(html, match_id)
    INDEX.write_text(html, encoding="utf-8")
    print(f"Updated ECC bowling runs conceded in {INDEX} for {', '.join(SHEET_MATCHES)}")


if __name__ == "__main__":
    main()
