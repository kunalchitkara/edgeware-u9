#!/usr/bin/env python3
"""Set gross runs (ball runs + 5 per wicket) in M2/M4/M5 ECC bowling summary tables."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"

sys.path.insert(0, str(ROOT / "scripts"))
from bowling_display import eco_cell, gross_runs  # noqa: E402
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


def _sim_bowling(match_id: str) -> dict[str, tuple[int, int, int]]:
    """name -> (net_runs, wickets, overs_float)."""
    cfg = MATCHES[match_id]
    if cfg.get("local") and (GEN_ROOT / cfg["local"]).exists():
        out: dict[str, tuple[int, int, int]] = {}
        data = json.loads((GEN_ROOT / cfg["local"]).read_text(encoding="utf-8"))
        for inn in data["innings"]:
            if "Edgware" in inn.get("batting", ""):
                continue
            for b in simulate_innings(inn)["bowling_summary"]:
                out[b["name"]] = (b["runs"], b["wickets"], b["overs"])
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


def _patch_table_body(body: str, figures: dict[str, tuple[int, int, int]]) -> str:
    def repl(m: re.Match[str]) -> str:
        name, overs_txt, old_r, wkts, wd, nb, dots = m.groups()
        wkts_i = int(wkts)
        if name in figures:
            net_r, wkts_i, overs = figures[name]
        else:
            net_r, overs = int(old_r), float(overs_txt)
        gr = gross_runs(net_r, wkts_i)
        wcell = f"<strong>{wkts_i}</strong>" if wkts_i else "0"
        overs_val = float(overs_txt) if "." in overs_txt else int(overs_txt)
        return (
            f'<tr><td class="scb">{name}</td><td class="c">{overs_txt}</td>'
            f'<td class="c">{gr}</td><td class="c">{wcell}</td>'
            f'<td class="c">{wd}</td><td class="c">{nb}</td>'
            f'{eco_cell(net_r, wkts_i, overs_val)}'
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
    figures = _sim_bowling(match_id)
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
    print(f"Updated gross ECC bowling in {INDEX} for {', '.join(SHEET_MATCHES)}")


if __name__ == "__main__":
    main()
