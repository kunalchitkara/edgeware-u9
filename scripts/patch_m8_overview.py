#!/usr/bin/env python3
"""Integrate M8 results into overview and season stats in index.html."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"

NEXT_MATCH = (
    '  <div class="nm"><div class="nmi">&#128197;</div>'
    '<div class="nminfo"><h3>Next Match · 12 Jul 2026</h3>'
    "<p>&#127968; Edgware vs Hayes &nbsp;&middot;&nbsp; Home &nbsp;&middot;&nbsp; "
    "Canons High School &nbsp;&middot;&nbsp; 09:00 / 10:00 AM</p></div></div>"
)

OVERVIEW_STATS = """  <div class="sgrid">
    <div class="sbox"><div class="v">8</div><div class="l">Played</div></div>
    <div class="sbox win"><div class="v">7</div><div class="l">Wins</div></div>
    <div class="sbox loss"><div class="v">1</div><div class="l">Losses</div></div>
    <div class="sbox"><div class="v">0</div><div class="l">Draws</div></div>
    <div class="sbox"><div class="v">341</div><div class="l">Highest Score</div></div>
    <div class="sbox"><div class="v">+96</div><div class="l">Best Win Margin</div></div>
  </div>"""


def main() -> None:
    html = INDEX.read_text(encoding="utf-8")

    html = re.sub(
        r'<div class="nm">.*?Next Match.*?</div></div>',
        NEXT_MATCH.strip(),
        html,
        count=1,
        flags=re.DOTALL,
    )

    html = re.sub(
        r'<div class="sgrid">\s*<div class="sgrid">.*?Best Win Margin</div>\s*</div>\s*</div>',
        f'<div class="sgrid">\n    {OVERVIEW_STATS.strip()}\n  </div>',
        html,
        count=1,
        flags=re.DOTALL,
    )

    html = html.replace(
        "Based on M2, M4, M5, M6 &amp; M7 (M1 &amp; M3 walkovers).",
        "Based on M2, M4, M5, M6, M7 &amp; M8 (M1 &amp; M3 walkovers).",
    )
    html = html.replace(
        "Based on 5 played matches (M2 vs H Manor, M4 vs Hayes, M5 vs Harefield, M6 vs Pinner, M7 vs H Manor).",
        "Based on 6 played matches (M2-M7 plus M8 vs Harefield).",
    )

    INDEX.write_text(html, encoding="utf-8")
    print(f"Updated M8 overview in {INDEX}")

    import sys

    sys.path.insert(0, str(ROOT / "scripts"))
    import summary_player_stats as sps

    sps.MATCH_IDS = ("m2", "m4", "m5", "m6", "m7", "m8")
    if "Ishaan" not in sps.ECC_NAMES:
        sps.ECC_NAMES = set(sps.ECC_NAMES) | {"Ishaan"}

    from patch_m7_overview import (  # noqa: WPS433
        _replace_batting_table_from_source,
        _replace_bowling_table_from_source,
        _replace_fielding_table_from_source,
        derive_shared_leaderboards,
        _replace_batting_leader_cards,
        _replace_most_wickets_card,
        _replace_best_bowling_figures_card,
        _replace_best_economy_card,
        _replace_most_dot_balls_card,
        _replace_best_partnerships_card,
        _replace_fielding_leader_cards,
    )
    from patch_index import fix_tab_lb_boundary, fix_tab_mx_boundary, fix_tab_ov_boundary, fix_tab_pl_boundary
    from summary_player_stats import collect_summary_season

    html = INDEX.read_text(encoding="utf-8")
    season = collect_summary_season(html)
    leaders = derive_shared_leaderboards(season)
    html = _replace_batting_table_from_source(html, season)
    html = _replace_bowling_table_from_source(html, season)
    html = _replace_fielding_table_from_source(html, season)
    html = _replace_batting_leader_cards(html, leaders)
    html = _replace_most_wickets_card(html, leaders)
    html = _replace_best_bowling_figures_card(html)
    html = _replace_best_economy_card(html, leaders)
    html = _replace_most_dot_balls_card(html, leaders)
    html = _replace_best_partnerships_card(html)
    html = _replace_fielding_leader_cards(html, leaders)
    html = fix_tab_ov_boundary(html)
    html = fix_tab_mx_boundary(html)
    html = fix_tab_lb_boundary(html)
    html = fix_tab_pl_boundary(html)
    INDEX.write_text(html, encoding="utf-8")
    print("Regenerated season stats with M8")

    from patch_strike_rate import main as patch_strike_rate_main

    patch_strike_rate_main()


if __name__ == "__main__":
    main()
