#!/usr/bin/env python3
"""Collect batter runs/balls from BBB simulation (sheets + local JSON)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from gen_bbb import (
    MATCHES,
    ROOT,
    load_sheet,
    parse_innings,
    parse_overs,
    simulate_innings,
    simulate_innings_json,
)
from strike_rate import strike_rate

ECC_NAMES = {
    "Ariyan", "Qaim", "Veer", "Avyaan", "Kaiyan", "Viaan", "Krish", "Taran",
    "Drish", "Shyam", "Aanya",
}


@dataclass
class InningsBatting:
    match_id: str
    team: str
    batters: dict[str, tuple[int, int]]  # name -> (runs, balls)
    dismissals: dict[str, int]  # name -> dismissals in innings


@dataclass
class SeasonBatting:
    runs: int = 0
    balls: int = 0
    dismissals: int = 0
    appearances: int = 0
    hs: int = 0

    def add_innings(self, runs: int, balls: int, dismissals: int) -> None:
        self.appearances += 1
        self.runs += runs
        self.balls += balls
        self.dismissals += dismissals
        if runs > self.hs:
            self.hs = runs

    @property
    def innings(self) -> int:
        if self.appearances == 0:
            return 0
        return self.dismissals + 1

    @property
    def avg(self) -> float:
        return self.runs / self.innings if self.innings else 0.0

    @property
    def sr(self) -> float | None:
        return strike_rate(self.runs, self.balls)


def _innings_from_sheet(match_id: str) -> list[InningsBatting]:
    cfg = MATCHES[match_id]
    rows = load_sheet(cfg["gid"])
    overs = parse_overs(rows[0])
    out: list[InningsBatting] = []
    for inn in parse_innings(rows):
        _blocks, stats = simulate_innings(inn, rows, overs)
        batters = {name: (st.runs, st.balls) for name, st in stats.items()}
        dismissals = {name: st.dismissals for name, st in stats.items()}
        out.append(InningsBatting(match_id, inn.team_name, batters, dismissals))
    return out


def _innings_from_json(match_id: str, path: Path) -> list[InningsBatting]:
    data = json.loads(path.read_text(encoding="utf-8"))
    out: list[InningsBatting] = []
    for inn in data["innings"]:
        _blocks, stats = simulate_innings_json(inn)
        batters = {name: (st.runs, st.balls) for name, st in stats.items()}
        dismissals = {name: st.dismissals for name, st in stats.items()}
        team = inn.get("batting", inn.get("team", ""))
        out.append(InningsBatting(match_id, team, batters, dismissals))
    return out


def collect_all_innings() -> list[InningsBatting]:
    all_innings: list[InningsBatting] = []
    for match_id, cfg in MATCHES.items():
        local = cfg.get("local")
        if local and (ROOT / local).exists():
            all_innings.extend(_innings_from_json(match_id, ROOT / local))
        else:
            all_innings.extend(_innings_from_sheet(match_id))
    return all_innings


def collect_ecc_season() -> dict[str, SeasonBatting]:
    """Aggregate ECC batting across M2-M6 (Edgware CC innings only)."""
    season: dict[str, SeasonBatting] = {name: SeasonBatting() for name in ECC_NAMES}
    for inn in collect_all_innings():
        if "Edgware" not in inn.team and inn.team != "Edgware CC":
            continue
        for name, (runs, balls) in inn.batters.items():
            if name not in season:
                continue
            dismissals = inn.dismissals.get(name, 0)
            if balls == 0 and runs == 0 and dismissals == 0:
                continue
            season[name].add_innings(runs, balls, dismissals)
    return season


def lookup_batter(innings_list: list[InningsBatting], match_id: str, team_substr: str, name: str) -> tuple[int, int] | None:
    for inn in innings_list:
        if inn.match_id != match_id:
            continue
        if team_substr not in inn.team:
            continue
        if name in inn.batters:
            return inn.batters[name]
    return None
