"""Strike rate helpers: SR = (runs / balls faced) × 100."""

from __future__ import annotations

# Leaders: minimum legal balls faced in the season (M2-M6 ECC batting).
MIN_BALLS_LEADERBOARD = 10


def strike_rate(runs: int, balls: int) -> float | None:
    if balls <= 0:
        return None
    return runs * 100.0 / balls


def format_sr(runs: int, balls: int) -> str:
    sr = strike_rate(runs, balls)
    if sr is None:
        return "-"
    return f"{sr:.1f}"


def format_sr_value(sr: float | None) -> str:
    if sr is None:
        return "-"
    return f"{sr:.1f}"
