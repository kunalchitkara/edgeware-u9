#!/usr/bin/env python3
"""Shared helpers for Top Bowl / Top Bat selection from scorecard stats."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BowlerLine:
    name: str
    runs: int
    wickets: int


@dataclass(frozen=True)
class BatterLine:
    name: str
    runs: int
    team: str = ""


@dataclass(frozen=True)
class MatchAwards:
    top_bowl: BowlerLine | None
    top_bat: BatterLine | None
    top_bat_ecc: BatterLine | None
    top_bat_opp: BatterLine | None


def best_bowler(bowlers: list[BowlerLine]) -> BowlerLine | None:
    """Most wickets; ties broken by fewest runs conceded."""
    if not bowlers:
        return None
    return min(bowlers, key=lambda b: (-b.wickets, b.runs))


def best_batsman(batters: list[BatterLine]) -> BatterLine | None:
    """Highest individual runs in the match (either innings)."""
    if not batters:
        return None
    return max(batters, key=lambda b: b.runs)


def bowl_figure(runs: int, wickets: int) -> str:
    """Display as runs-wickets, e.g. 14-2."""
    r = str(runs)
    if runs < 0:
        r = f"&minus;{abs(runs)}"
    return f"{r}-{wickets}"


def bat_subtitle(runs: int) -> str:
    return f"{runs} runs"
