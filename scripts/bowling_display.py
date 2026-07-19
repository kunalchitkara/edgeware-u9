#!/usr/bin/env python3
"""U9 pairs bowling figures for scorecard display (runs conceded)."""

from __future__ import annotations


def runs_conceded(runs: int, wickets: int = 0) -> int:
    """Runs on the bowling table R column: ball-by-ball runs in the bowler's overs.

    Includes extras (wides, no-balls, byes/leg-byes scored off the over).
    Does NOT add the U9 team wicket penalty (5 runs off the team total).
    Does NOT subtract it either. Wickets are shown in the W column.
    """
    _ = wickets
    return int(runs)


def gross_runs(runs: int, wickets: int = 0) -> int:
    """Alias for runs_conceded (legacy name from an incorrect gross = runs + 5×wickets rule)."""
    return runs_conceded(runs, wickets)


def economy(runs: int, wickets: int, overs: int | float) -> float:
    _ = wickets
    if not overs:
        return 0.0
    return runs_conceded(runs) / float(overs)


def eco_cell(runs: int, wickets: int, overs: int | float, *, good_at: float = 4.0) -> str:
    v = economy(runs, wickets, overs)
    cls = " eco-good" if v <= good_at else ""
    return f'<td class="c{cls}">{v:.1f}</td>'
