#!/usr/bin/env python3
"""U9 pairs bowling figures for scorecard display (gross runs conceded)."""

from __future__ import annotations

WKT_GROSS_BONUS = 5


def gross_runs(runs: int, wickets: int) -> int:
    """Total runs on the scorecard R column: ball runs + 5 per wicket taken."""
    return int(runs) + WKT_GROSS_BONUS * int(wickets)


def economy(runs: int, wickets: int, overs: int | float) -> float:
    if not overs:
        return 0.0
    return gross_runs(runs, wickets) / float(overs)


def eco_cell(runs: int, wickets: int, overs: int | float, *, good_at: float = 4.0) -> str:
    v = economy(runs, wickets, overs)
    cls = " eco-good" if v <= good_at else ""
    return f'<td class="c{cls}">{v:.1f}</td>'
