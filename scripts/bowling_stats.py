#!/usr/bin/env python3
"""Season bowling aggregates from source ball-by-ball data."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable

from gen_bbb import MATCHES, ROOT, WKT_SYMBOLS, cell, extract_over_deliveries, load_sheet, parse_innings, parse_overs

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

_BALL_IDX_RE = re.compile(r"B(\d+)$")
_OVER_COL_RE = re.compile(r"Over\s+(\d+)(?:\s*★)?\s*(.*?)\s*B1")


@dataclass
class BowlingSeason:
    matches: set[str] = field(default_factory=set)
    balls: int = 0
    runs: int = 0
    wickets: int = 0
    wides: int = 0
    noballs: int = 0
    dots: int = 0


@dataclass
class MatchFigure:
    match: str
    wickets: int
    runs: int


@dataclass
class BowlingState:
    by_player: dict[str, BowlingSeason]
    best_figures: dict[str, MatchFigure]


def _init_state() -> BowlingState:
    return BowlingState(
        by_player={name: BowlingSeason() for name in sorted(ECC_NAMES)},
        best_figures={},
    )


def _symbol_wide_count(symbol: str) -> int:
    if symbol in {"+", "WD"} or symbol.startswith("+"):
        return 1
    if symbol == "0+4":
        return 1
    return 0


def _symbol_noball_count(symbol: str) -> int:
    if symbol in {"O", "ON", "NB"}:
        return 1
    if symbol.startswith("O"):
        return 1
    if symbol == "O+1":
        return 1
    return 0


def _is_legal_symbol(symbol: str) -> bool:
    if not symbol:
        return True
    if symbol in {"+", "WD", "O", "ON", "NB"}:
        return False
    if symbol.startswith("+") or symbol.startswith("O"):
        return False
    return True


def _symbol_conceded_runs(symbol: str) -> int:
    sym = (symbol or "").strip()
    if not sym:
        return 0
    if sym in {".", "0"}:
        return 0
    if sym in WKT_SYMBOLS or sym == "R":
        return 0
    if sym.startswith(("∆", "v")):
        return 0
    if sym.isdigit():
        return int(sym)
    if sym in {"+", "WD"}:
        return 2
    if sym.startswith("+"):
        return 2 + int(sym[1:] or "0")
    if sym in {"O", "ON", "NB"}:
        return 2
    if sym.startswith("O") and sym[1:].isdigit():
        return 2 + int(sym[1:])
    if sym == "0+4":
        return 6
    if sym == "O+1":
        return 3
    return 0


def _runs_from_json_delivery(delivery: dict) -> int:
    symbol = (delivery.get("symbol") or "").strip()
    bat_runs = delivery.get("bat_runs")
    extras_type = (delivery.get("extras_type") or "").strip().lower()
    if bat_runs is not None:
        return int(bat_runs)
    if extras_type in {"wide", "noball"}:
        return int(delivery.get("runs", 0) or 0)
    return _symbol_conceded_runs(symbol)


def _is_wicket_symbol(symbol: str, wicket_flag: bool) -> bool:
    return bool(wicket_flag) or symbol in WKT_SYMBOLS or symbol == "R"


def _update_bowler(
    season: BowlingSeason,
    symbol: str,
    conceded_runs: int,
    is_wicket: bool,
) -> None:
    legal = _is_legal_symbol(symbol)
    season.runs += conceded_runs
    season.wides += _symbol_wide_count(symbol)
    season.noballs += _symbol_noball_count(symbol)
    if legal:
        season.balls += 1
        if conceded_runs == 0 and not is_wicket:
            season.dots += 1
    if is_wicket and symbol != "R":
        season.wickets += 1


def _record_best_figure(
    state: BowlingState,
    name: str,
    match_id: str,
    wickets: int,
    runs: int,
) -> None:
    if wickets <= 0:
        return
    current = state.best_figures.get(name)
    candidate = MatchFigure(match=match_id.upper(), wickets=wickets, runs=runs)
    if current is None or candidate.wickets > current.wickets or (
        candidate.wickets == current.wickets and candidate.runs < current.runs
    ):
        state.best_figures[name] = candidate


def _sheet_team_name(label: str) -> str:
    m = re.search(r"INNINGS\s+\d+\s*[·-]\s*(.+?)\s+BATTING", label, re.I)
    return m.group(1).strip() if m else label


def _iter_sheet_innings(
    rows: list[list[str]],
) -> Iterable[tuple[str, list[tuple[int, str, list[int]]], list[list[str]], object]]:
    overs = parse_overs(rows[0])
    for inn in parse_innings(rows):
        yield inn.team_name or _sheet_team_name(inn.title), overs, rows, inn


def _accumulate_match_from_sheet(state: BowlingState, match_id: str, rows: list[list[str]]) -> None:
    for team_name, overs, sheet_rows, inn in _iter_sheet_innings(rows):
        if "Edgware" in team_name:
            continue
        match_fig: dict[str, tuple[int, int]] = {}
        for onum, bowler, ball_cols in overs:
            if bowler not in ECC_NAMES:
                continue
            season = state.by_player[bowler]
            season.matches.add(match_id.upper())
            wkts, runs = match_fig.get(bowler, (0, 0))
            raw = extract_over_deliveries(inn, sheet_rows, ball_cols)
            for _batter, symbol, _ball_idx in raw:
                sym = (symbol or "").strip()
                if not sym:
                    sym = "."
                conceded = _symbol_conceded_runs(sym)
                is_wicket = _is_wicket_symbol(sym, sym in WKT_SYMBOLS or sym == "R")
                _update_bowler(season, sym, conceded, is_wicket)
                runs += conceded
                if is_wicket and sym != "R":
                    wkts += 1
            match_fig[bowler] = (wkts, runs)
        for name, (wkts, runs) in match_fig.items():
            _record_best_figure(state, name, match_id, wkts, runs)


def _accumulate_match_from_json(state: BowlingState, match_id: str, payload: dict) -> None:
    for innings in payload.get("innings", []):
        batting = innings.get("batting", innings.get("team", ""))
        if "Edgware" in batting:
            continue
        match_fig: dict[str, tuple[int, int]] = {}
        for over in innings.get("overs", []):
            bowler = (over.get("bowler") or "").strip()
            if bowler not in ECC_NAMES:
                continue
            season = state.by_player[bowler]
            season.matches.add(match_id.upper())
            wkts, runs = match_fig.get(bowler, (0, 0))
            for delivery in over.get("deliveries", []):
                symbol = (delivery.get("symbol") or "").strip() or "."
                conceded = _runs_from_json_delivery(delivery)
                is_wicket = _is_wicket_symbol(symbol, bool(delivery.get("wicket")))
                _update_bowler(season, symbol, conceded, is_wicket)
                runs += conceded
                if is_wicket and symbol != "R":
                    wkts += 1
            match_fig[bowler] = (wkts, runs)
        for name, (wkts, runs) in match_fig.items():
            _record_best_figure(state, name, match_id, wkts, runs)


def collect_bowling_state() -> BowlingState:
    state = _init_state()
    for match_id, cfg in MATCHES.items():
        local = cfg.get("local")
        if local and (ROOT / local).exists():
            import json

            data = json.loads((ROOT / local).read_text(encoding="utf-8"))
            _accumulate_match_from_json(state, match_id, data)
            continue
        rows = load_sheet(cfg["gid"])
        _accumulate_match_from_sheet(state, match_id, rows)
    return state


def overs_text(balls: int) -> str:
    return str(balls // 6) if balls % 6 == 0 else f"{balls // 6}.{balls % 6}"


def economy(season: BowlingSeason) -> float:
    if season.balls == 0:
        return 0.0
    return season.runs / (season.balls / 6)
