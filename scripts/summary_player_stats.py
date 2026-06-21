#!/usr/bin/env python3
"""Season player aggregates sourced from match summary tables."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
MATCH_IDS = ("m2", "m4", "m5", "m6", "m7")
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
ECC_FIELDING_TEAMS = {"ECC", "Edgware CC"}


@dataclass
class BatSeason:
    matches: int = 0
    runs: int = 0
    balls: int = 0
    outs: int = 0
    fours: int = 0
    sixes: int = 0
    net: int = 0
    hs: int = 0

    @property
    def innings(self) -> int:
        return self.outs + 1 if self.matches else 0

    @property
    def avg(self) -> float:
        return (self.runs / self.innings) if self.innings else 0.0

    @property
    def sr(self) -> float:
        return (self.runs * 100.0 / self.balls) if self.balls else 0.0


@dataclass
class BowlSeason:
    matches: int = 0
    balls: int = 0
    runs: int = 0
    wickets: int = 0
    wides: int = 0
    noballs: int = 0
    dots: int = 0

    @property
    def overs_text(self) -> str:
        return str(self.balls // 6) if self.balls % 6 == 0 else f"{self.balls // 6}.{self.balls % 6}"

    @property
    def economy(self) -> float:
        return (self.runs / (self.balls / 6.0)) if self.balls else 0.0


@dataclass
class FieldSeason:
    catches: int = 0
    run_outs: int = 0
    matches: set[str] | None = None

    def __post_init__(self) -> None:
        if self.matches is None:
            self.matches = set()


@dataclass
class SummarySeason:
    batting: dict[str, BatSeason]
    bowling: dict[str, BowlSeason]
    fielding: dict[str, FieldSeason]
    best_bowling: dict[str, tuple[str, int, int]]


def _to_int(text: str) -> int:
    t = text.replace("&minus;", "-").replace("−", "-")
    t = re.sub(r"[^\d-]", "", t)
    return int(t) if t and t != "-" else 0


def _overs_to_balls(text: str) -> int:
    t = text.strip()
    if not t:
        return 0
    if "." not in t:
        return int(t) * 6
    whole, part = t.split(".", 1)
    return int(whole) * 6 + int(part or "0")


def _match_block(html: str, match_id: str) -> str:
    start = html.find(f'id="match-{match_id}-summary"')
    if start == -1:
        return ""
    end = html.find(f'id="match-{match_id}-bbb"', start)
    return html[start:end] if end != -1 else html[start:]


def _section_tables(block: str) -> list[tuple[str, str, str]]:
    out: list[tuple[str, str, str]] = []
    pattern = re.compile(
        r'<div class="scih[^"]*"><span>(.*?)</span>.*?</div>\s*'
        r'<div class="tscroll"><table class="sctbl">\s*<thead>.*?</thead>\s*<tbody>(.*?)</tbody>',
        flags=re.DOTALL,
    )
    for m in pattern.finditer(block):
        heading = re.sub(r"<[^>]+>", "", m.group(1)).strip()
        heading = heading.replace("—", "&mdash;")
        if "Batting" in heading:
            kind = "Batting"
        elif "Bowling" in heading:
            kind = "Bowling"
        else:
            continue
        team = heading.split("&mdash;", 1)[0].strip()
        body = m.group(2)
        out.append((team, kind, body))
    return out


def _fielding_sections(block: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    pattern = re.compile(
        r'<div class="scsh">.*?Fielding Highlights \((.*?)\)</div>\s*'
        r'<div class="tscroll"><table class="sctbl">\s*<thead>.*?</thead>\s*<tbody>(.*?)</tbody>',
        flags=re.DOTALL,
    )
    for m in pattern.finditer(block):
        team = re.sub(r"<[^>]+>", "", m.group(1)).strip()
        body = m.group(2)
        out.append((team, body))
    return out


def _parse_batting_row(row_html: str) -> tuple[str, str, int, float, int, int, int] | None:
    cells = re.findall(r"<td[^>]*>(.*?)</td>", row_html, flags=re.DOTALL)
    if len(cells) < 4:
        return None
    vals = [re.sub(r"<[^>]+>", "", c).strip() for c in cells]
    name = vals[0]
    if name not in ECC_NAMES:
        return None
    dismissal = vals[1] if len(vals) > 1 else ""
    runs = _to_int(vals[2]) if len(vals) > 2 else 0
    sr = float(vals[3]) if len(vals) > 3 and re.fullmatch(r"\d+(?:\.\d+)?", vals[3]) else 0.0
    if len(vals) >= 7:
        fours = _to_int(vals[4])
        sixes = _to_int(vals[5])
        net = _to_int(vals[6])
    else:
        fours = 0
        sixes = 0
        net = _to_int(vals[4]) if len(vals) > 4 else 0
    return name, dismissal, runs, sr, fours, sixes, net


def _parse_bowling_row(row_html: str) -> tuple[str, int, int, int, int, int, int] | None:
    cells = re.findall(r"<td[^>]*>(.*?)</td>", row_html, flags=re.DOTALL)
    if len(cells) < 8:
        return None
    vals = [re.sub(r"<[^>]+>", "", c).strip() for c in cells]
    name = vals[0]
    if name not in ECC_NAMES:
        return None
    return (
        name,
        _overs_to_balls(vals[1]),
        _to_int(vals[2]),
        _to_int(vals[3]),
        _to_int(vals[4]),
        _to_int(vals[5]),
        _to_int(vals[7]),
    )


def _parse_fielding_row(row_html: str) -> tuple[str, int, int] | None:
    cells = re.findall(r"<td[^>]*>(.*?)</td>", row_html, flags=re.DOTALL)
    if len(cells) < 3:
        return None
    values = [re.sub(r"<[^>]+>", "", c).strip() for c in cells]
    name = values[0]
    if name not in ECC_NAMES:
        return None
    catches = _to_int(values[1])
    run_outs = _to_int(values[2])
    return name, catches, run_outs


def collect_summary_season(html_override: str | None = None) -> SummarySeason:
    html = html_override if html_override is not None else INDEX.read_text(encoding="utf-8")
    batting = {n: BatSeason() for n in ECC_NAMES}
    bowling = {n: BowlSeason() for n in ECC_NAMES}
    fielding = {n: FieldSeason() for n in ECC_NAMES}
    best_bowling: dict[str, tuple[str, int, int]] = {}

    for match_id in MATCH_IDS:
        block = _match_block(html, match_id)
        if not block:
            continue
        match = match_id.upper()
        sections = _section_tables(block)

        for team, kind, body in sections:
            rows = re.findall(r"<tr[^>]*>(.*?)</tr>", body, flags=re.DOTALL)
            if kind == "Batting":
                if "Edgware" in team:
                    seen: set[str] = set()
                    for row in rows:
                        parsed = _parse_batting_row(row)
                        if not parsed:
                            continue
                        name, dismissal, runs, sr, fours, sixes, net = parsed
                        if name not in seen:
                            batting[name].matches += 1
                            seen.add(name)
                        batting[name].runs += runs
                        batting[name].fours += fours
                        batting[name].sixes += sixes
                        batting[name].net += net
                        batting[name].hs = max(batting[name].hs, runs)
                        if dismissal and "not out" not in dismissal.lower():
                            batting[name].outs += 1
                        if sr > 0 and runs > 0:
                            balls = max(1, round((runs * 100.0) / sr))
                            batting[name].balls += balls

            if kind == "Bowling" and "Edgware" in team:
                for row in rows:
                    parsed = _parse_bowling_row(row)
                    if not parsed:
                        continue
                    name, balls, runs, wkts, wd, nb, dots = parsed
                    bowling[name].matches += 1
                    bowling[name].balls += balls
                    bowling[name].runs += runs
                    bowling[name].wickets += wkts
                    bowling[name].wides += wd
                    bowling[name].noballs += nb
                    bowling[name].dots += dots
                    if wkts > 0:
                        current = best_bowling.get(name)
                        cand = (match, wkts, runs)
                        if current is None or cand[1] > current[1] or (cand[1] == current[1] and cand[2] < current[2]):
                            best_bowling[name] = cand

        # Source-of-truth for fielding is per-match summary fielding sections.
        for team, body in _fielding_sections(block):
            if team not in ECC_FIELDING_TEAMS:
                continue
            for row in re.findall(r"<tr[^>]*>(.*?)</tr>", body, flags=re.DOTALL):
                parsed = _parse_fielding_row(row)
                if not parsed:
                    continue
                name, catches, run_outs = parsed
                if catches == 0 and run_outs == 0:
                    continue
                f = fielding[name]
                f.catches += catches
                f.run_outs += run_outs
                f.matches.add(match)

    return SummarySeason(
        batting=batting,
        bowling=bowling,
        fielding=fielding,
        best_bowling=best_bowling,
    )
