#!/usr/bin/env python3
"""Derive Top Bowl / Top Bat from index.html scorecards and patch .msg cells."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
DATA_M6 = ROOT / "data" / "m6.json"

sys.path.insert(0, str(ROOT / "scripts"))
from match_awards import (  # noqa: E402
    BatterLine,
    BowlerLine,
    bat_subtitle,
    best_batsman,
    best_bowler,
    bowl_figure,
)

# Which opponent bowling table feeds the existing Top Bowl label per match.
MATCH_CONFIG = {
    "m2": {
        "top_bowl_label": "Top Bowl HSM",
        "bowling_marker": "Headstone Manor &mdash; Bowling",
        "ecc_bat_marker": "Edgware CC &mdash; Batting",
        "opp_bat_marker": "Headstone Manor &mdash; Batting",
        "opp_short": "HSM",
    },
    "m4": {
        "top_bowl_label": "Top Bowl Hayes",
        "bowling_marker": "Hayes &mdash; Bowling",
        "ecc_bat_marker": "Edgware CC &mdash; Batting",
        "opp_bat_marker": "Hayes &mdash; Batting",
        "opp_short": "Hayes",
    },
    "m5": {
        "top_bowl_label": "Top Bowl Harefield",
        "bowling_marker": "Harefield &mdash; Bowling",
        "ecc_bat_marker": "Edgware CC &mdash; Batting",
        "opp_bat_marker": "Harefield &mdash; Batting",
        "opp_short": "Harefield",
    },
    "m6": {
        "top_bowl_label": "Top Bowl ECC",
        "bowling_marker": "Edgware CC &mdash; Bowling",
        "ecc_bat_marker": "Edgware CC &mdash; Batting",
        "opp_bat_marker": "Pinner &mdash; Batting",
        "opp_short": "Pinner",
        "use_m6_json": True,
    },
}


def parse_runs(text: str) -> int:
    t = text.strip()
    if t in {"&mdash;", "—", "-", ""}:
        return 0
    if "&minus;" in t or t.startswith("-"):
        return -int(re.sub(r"[^\d]", "", t) or "0")
    return int(re.sub(r"[^\d]", "", t) or "0")


def parse_wickets(cell: str) -> int:
    if "<strong>" in cell:
        return int(re.sub(r"[^\d]", "", cell) or "0")
    t = cell.strip()
    if t in {"0", "&mdash;", "—", ""}:
        return 0
    return int(re.sub(r"[^\d]", "", t) or "0")


def cell_text(cell_html: str) -> str:
    return re.sub(r"<[^>]+>", "", cell_html).strip()


def extract_bowling_table(section_html: str) -> list[BowlerLine]:
    rows = re.findall(
        r'<tr><td class="scb">([^<]+)</td>(.*?)</tr>',
        section_html,
        re.DOTALL,
    )
    out: list[BowlerLine] = []
    for name, rest in rows:
        cells = re.findall(r'<td class="c[^"]*">(.*?)</td>', rest, re.DOTALL)
        if len(cells) < 3:
            continue
        if not cell_text(cells[0]).isdigit():
            continue
        runs = parse_runs(cell_text(cells[1]))
        wtxt = cell_text(cells[2])
        wickets = int(re.sub(r"[^\d]", "", wtxt) or "0") if wtxt not in {"—", "&mdash;"} else 0
        out.append(BowlerLine(name.strip(), runs, wickets))
    return out


def normalize_batter_name(name: str) -> str:
    return re.sub(r"\s*\(P\d+\)\s*$", "", name.strip())


def extract_batting_table(section_html: str, team: str) -> list[BatterLine]:
    rows = re.findall(
        r'<tr><td class="scb">([^<]+)</td><td class="scd">[^<]*</td>'
        r'<td class="c scr">([^<]*)</td>',
        section_html,
    )
    totals: dict[str, int] = {}
    for name, runs_cell in rows:
        if runs_cell.strip() in {"&mdash;", "—"}:
            continue
        key = normalize_batter_name(name)
        totals[key] = totals.get(key, 0) + parse_runs(runs_cell)
    return [BatterLine(n, r, team) for n, r in totals.items()]


def section_after_marker(block: str, marker: str) -> str:
    idx = block.find(marker)
    if idx == -1:
        return ""
    sub = block[idx:]
    end = sub.find("<div class=\"sdiv\">")
    if end == -1:
        end = sub.find("<div class=\"ff\">")
    if end == -1:
        end = len(sub)
    return sub[:end]


def m6_bowling_from_json() -> list[BowlerLine]:
    data = json.loads(DATA_M6.read_text(encoding="utf-8"))
    inn1 = data["innings"][0]
    return [BowlerLine(b["name"], b["runs"], b["wickets"]) for b in inn1["bowling_summary"]]


def m6_batting_from_json() -> tuple[list[BatterLine], list[BatterLine]]:
    data = json.loads(DATA_M6.read_text(encoding="utf-8"))
    inn1, inn2 = data["innings"]
    opp = [BatterLine(b["name"], b["runs"], "Pinner") for b in inn1["batting_summary"]]
    ecc = [BatterLine(b["name"], b["runs"], "ECC") for b in inn2["batting_summary"]]
    return ecc, opp


def extract_summary_block(match_block: str, match_id: str) -> str:
    """Summary scorecard only — exclude ball-by-ball commentary HTML."""
    m = re.search(rf'id="match-{match_id}-summary" class="mmview active">(.*)', match_block, re.DOTALL)
    if not m:
        return match_block
    rest = m.group(1)
    end = rest.find(f'id="match-{match_id}-bbb"')
    if end == -1:
        return rest
    return rest[:end]


def extract_match_block(html: str, match_id: str) -> str:
    m = re.search(rf'<div id="match-{match_id}" class="md2">', html)
    if not m:
        return ""
    start = m.start()
    pos = m.end()
    depth = 1
    while depth and pos < len(html):
        o = html.find("<div", pos)
        c = html.find("</div>", pos)
        if c == -1:
            break
        if o != -1 and o < c:
            depth += 1
            pos = o + 4
        else:
            depth -= 1
            end = c + len("</div>")
            pos = end
            if depth == 0:
                return html[start:end]
    return ""


def patch_top_bowl(block: str, label: str, bowler: BowlerLine) -> str:
    pattern = (
        rf'<div class="ms"><div class="mv">[^<]*</div><div class="ml">{re.escape(label)}</div>'
        rf'<div class="mn">[^<]*</div></div>'
    )
    replacement = (
        f'<div class="ms"><div class="mv">{bowler.name}</div><div class="ml">{label}</div>'
        f'<div class="mn">{bowl_figure(bowler.runs, bowler.wickets)}</div></div>'
    )
    new_block, n = re.subn(pattern, replacement, block, count=1)
    if n != 1:
        raise ValueError(f"Top Bowl cell not found for {label}")
    return new_block


def patch_top_bat(block: str, label: str, batter: BatterLine) -> str:
    pattern = (
        rf'<div class="ms"><div class="mv">[^<]*</div><div class="ml">{re.escape(label)}</div>'
        rf'<div class="mn">[^<]*</div></div>'
    )
    replacement = (
        f'<div class="ms"><div class="mv">{batter.name}</div><div class="ml">{label}</div>'
        f'<div class="mn">{bat_subtitle(batter.runs)}</div></div>'
    )
    new_block, n = re.subn(pattern, replacement, block, count=1)
    if n != 1:
        raise ValueError(f"Top Bat cell not found for {label}")
    return new_block


def analyse_match(html: str, match_id: str) -> dict:
    cfg = MATCH_CONFIG[match_id]
    block = extract_match_block(html, match_id)
    if not block:
        raise ValueError(f"Match block missing: {match_id}")
    summary = extract_summary_block(block, match_id)

    if cfg.get("use_m6_json"):
        bowlers = m6_bowling_from_json()
        ecc_batters, opp_batters = m6_batting_from_json()
    else:
        bowl_section = section_after_marker(summary, cfg["bowling_marker"])
        bowlers = extract_bowling_table(bowl_section)
        ecc_section = section_after_marker(summary, cfg["ecc_bat_marker"])
        opp_section = section_after_marker(summary, cfg["opp_bat_marker"])
        ecc_batters = extract_batting_table(ecc_section, "ECC")
        opp_batters = extract_batting_table(opp_section, cfg["opp_short"])

    top_bowl = best_bowler(bowlers)
    top_bat_ecc = best_batsman(ecc_batters)
    top_bat_opp = best_batsman(opp_batters)
    all_bat = ecc_batters + opp_batters
    top_bat = best_batsman(all_bat)

    return {
        "match": match_id.upper(),
        "top_bowl": top_bowl,
        "top_bat": top_bat,
        "top_bat_ecc": top_bat_ecc,
        "top_bat_opp": top_bat_opp,
        "cfg": cfg,
        "block": block,
    }


def patch_index(html: str) -> tuple[str, list[dict]]:
    reports: list[dict] = []
    for match_id in MATCH_CONFIG:
        info = analyse_match(html, match_id)
        cfg = info["cfg"]
        block = info["block"]
        bowl = info["top_bowl"]
        if bowl:
            block = patch_top_bowl(block, cfg["top_bowl_label"], bowl)
        if info["top_bat_ecc"]:
            block = patch_top_bat(block, "Top Bat ECC", info["top_bat_ecc"])
        opp_label = f"Top Bat {cfg['opp_short']}"
        if info["top_bat_opp"]:
            block = patch_top_bat(block, opp_label, info["top_bat_opp"])

        html = html.replace(info["block"], block)
        reports.append(info)
    return html, reports


def print_report(reports: list[dict]) -> None:
    print("\nMatch | Top Bowl | Wkts | Runs | Top Bat | Runs")
    print("--- | --- | --- | --- | --- | ---")
    for info in reports:
        b = info["top_bowl"]
        t = info["top_bat"]
        print(
            f"{info['match']} | {b.name if b else 'N/A'} | {b.wickets if b else '-'} | "
            f"{b.runs if b else '-'} | {t.name if t else 'N/A'} | {t.runs if t else '-'}"
        )


def main() -> None:
    html = INDEX.read_text(encoding="utf-8")
    html, reports = patch_index(html)
    INDEX.write_text(html, encoding="utf-8")
    print(f"Patched awards in {INDEX}")
    print_report(reports)


if __name__ == "__main__":
    main()
