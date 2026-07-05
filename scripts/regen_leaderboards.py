#!/usr/bin/env python3
"""Regenerate season leaderboards in index.html from summary aggregates."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"

sys.path.insert(0, str(ROOT / "scripts"))
import summary_player_stats as sps

sps.MATCH_IDS = ("m2", "m4", "m5", "m6", "m7", "m8")
if "Ishaan" not in sps.ECC_NAMES:
    sps.ECC_NAMES = set(sps.ECC_NAMES) | {"Ishaan"}

from patch_index import fix_tab_lb_boundary, fix_tab_mx_boundary, fix_tab_pl_boundary  # noqa: E402
from patch_m7_overview import (  # noqa: E402
    _replace_batting_leader_cards,
    _replace_batting_table_from_source,
    _replace_best_bowling_figures_card,
    _replace_best_economy_card,
    _replace_best_partnerships_card,
    _replace_bowling_table_from_source,
    _replace_fielding_leader_cards,
    _replace_fielding_table_from_source,
    _replace_most_dot_balls_card,
    _replace_most_wickets_card,
)
from summary_player_stats import collect_summary_season, derive_shared_leaderboards  # noqa: E402


def main() -> None:
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
    html = fix_tab_mx_boundary(html)
    html = fix_tab_lb_boundary(html)
    html = fix_tab_pl_boundary(html)
    INDEX.write_text(html, encoding="utf-8")
    print(f"Regenerated leaderboards in {INDEX}")

    from patch_strike_rate import main as patch_strike_rate_main  # noqa: WPS433

    patch_strike_rate_main()


if __name__ == "__main__":
    main()
