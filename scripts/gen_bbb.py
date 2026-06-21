#!/usr/bin/env python3
"""Extract ball-by-ball data from Google Sheets and generate list-style HTML."""

from __future__ import annotations

import html
import json
import re
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

SHEET_ID = "1cxSoOdd3rgEp-EtyKzxbeWssac5t0gM4F9CnMwkQFL8"
BASE_SCORE = 200
PAIR_OVERS = 4
DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def pair_batter_summaries(
    batting_order: list[str],
    pair_idx: int,
    striker: str,
    non_striker: str,
    stats: dict[str, BatterStats],
) -> list[tuple[str, int, int, bool]]:
    """U9 pair headers: always show the designated pair, not a substitute from the next block."""
    b1 = batting_order[pair_idx * 2]
    b2 = batting_order[pair_idx * 2 + 1]
    if striker in (b1, b2):
        on, off = striker, (b2 if striker == b1 else b1)
    elif non_striker in (b1, b2):
        on, off = non_striker, (b2 if non_striker == b1 else b1)
    else:
        on, off = b1, b2
    return [
        (on, stats[on].runs, stats[on].balls, True),
        (off, stats[off].runs, stats[off].balls, False),
    ]

MATCHES = {
    "m2": {"gid": "737570712", "label": "M2", "overs": 20},
    "m4": {"gid": "1996740206", "label": "M4", "overs": 20},
    "m5": {"gid": "669851544", "label": "M5", "overs": 20},
    "m6": {
        "gid": "489440707",
        "label": "M6",
        "overs": 16,
        "teams": ("Pinner", "Edgware CC"),
        "local": "data/m6.json",
    },
    "m7": {
        "gid": "1976564850",
        "sheet_id": "1BLANhVMw69HEuN38wgTXkIOFjNw9a7em",
        "label": "M7",
        "overs": 16,
        "teams": ("Edgware CC", "Headstone Manor"),
        "local": "data/m7.json",
    },
}

ROOT = Path(__file__).resolve().parents[1]

COMMENTARY_LABEL = "Commentary"

WKT_SYMBOLS = {"B", "C", "S", "L", "H"}


def format_toss_decision(decision: str) -> str:
    d = (decision or "").strip().lower()
    if d in {"bowl", "bowling", "field", "ball"}:
        return "ball first"
    if d in {"bat", "batting"}:
        return "bat first"
    return decision or "bat first"


def render_toss(toss: dict | None) -> str:
    if not toss or not toss.get("winner"):
        return ""
    winner = html.escape(str(toss["winner"]))
    decision = html.escape(format_toss_decision(str(toss.get("decision", ""))))
    return (
        '<section class="bbb-panel bbb-toss-panel">'
        '<div class="bbb-toss">'
        f"<strong>Toss:</strong> {winner} won the toss &amp; elected to {decision}."
        "</div></section>"
    )


def innings_score_line(inn: dict) -> str:
    total = inn.get("final_total")
    wkts = inn.get("wickets")
    if total is None or wkts is None:
        return ""
    return f"{html.escape(str(inn['batting']))} {total}-{wkts}"


def render_result(match_meta: dict, innings: list[dict]) -> str:
    result = (match_meta.get("result") or "").strip()
    if not result:
        return ""
    score_bits = [line for inn in innings if (line := innings_score_line(inn))]
    parts = [
        '<section class="bbb-panel bbb-result-panel">',
        '<div class="bbb-inn-bar">',
        "<span>Result</span>",
        f"<span>{COMMENTARY_LABEL}</span>",
        "</div>",
        '<div class="bbb-result">',
        f"<strong>{html.escape(result)}</strong>",
    ]
    if score_bits:
        parts.append(f'<div class="bbb-result-scores">{" vs ".join(score_bits)}</div>')
    parts.extend(["</div></section>"])
    return "".join(parts)


@dataclass
class BatterStats:
    runs: int = 0
    balls: int = 0
    out: bool = False
    dismissals: int = 0


@dataclass
class BallEvent:
    symbol: str
    description: str
    badge_class: str
    runs_delta: int
    is_wicket: bool
    is_legal: bool
    bat_runs: int = 0
    is_boundary: bool = False


@dataclass
class Delivery:
    notation: str
    symbol: str
    description: str
    batter: str
    bowler: str
    total_score: int
    wickets: int
    is_wicket: bool
    is_boundary: bool
    badge_class: str


@dataclass
class OverBlock:
    over_num: int
    bowler: str
    is_last: bool
    over_runs: str
    cumulative: str
    deliveries: list[Delivery] = field(default_factory=list)
    batter_summaries: list[tuple[str, int, int, bool]] = field(default_factory=list)
    partnership_label: str = ""
    partnership_runs: int = 0
    partnership_wickets: int = 0
    wickets: int = 0


@dataclass
class Innings:
    title: str
    team_name: str
    innings_num: int
    batsmen: list[tuple[int, str]]
    over_runs_row: int
    cumulative_row: int


def innings_json_to_render_data(inn: dict) -> tuple[list[list[str]], list[tuple[int, str, list[int]]], Innings]:
    """Build sheet-like rows and per-innings overs (with correct bowlers) from JSON."""
    batsmen = list(inn["batsmen"])
    rows: list[list[str]] = []
    bat_row_idx: dict[str, int] = {}

    for name in batsmen:
        bat_row_idx[name] = len(rows)
        rows.append([name] + [""] * 7)

    over_runs_idx = len(rows)
    rows.append(["Over Runs"] + [""] * 7)
    cum_idx = len(rows)
    rows.append(["Cumulative"] + [""] * 7)

    overs_list: list[tuple[int, str, list[int]]] = []
    col = 8
    max_over = max(o["num"] for o in inn["overs"])

    for over in sorted(inn["overs"], key=lambda o: o["num"]):
        ball_cols: list[int] = []
        for d in over["deliveries"]:
            batter = d["batter"]
            if batter not in bat_row_idx:
                bat_row_idx[batter] = len(rows)
                batsmen.append(batter)
                rows.append([batter] + [""] * 7)
            idx = bat_row_idx[batter]
            while len(rows[idx]) <= col:
                rows[idx].append("")
            rows[idx][col] = d["symbol"]
            ball_cols.append(col)
            col += 1
        if ball_cols:
            first_col = ball_cols[0]
            while len(rows[over_runs_idx]) <= first_col:
                rows[over_runs_idx].append("")
                rows[cum_idx].append("")
            rows[over_runs_idx][first_col] = str(over.get("over_runs", ""))
            rows[cum_idx][first_col] = str(over["total"])
        overs_list.append((over["num"], over["bowler"], ball_cols))

    inn_obj = Innings(
        title=f"Innings {inn['num']} — {inn['batting']}",
        team_name=inn["batting"],
        innings_num=inn["num"],
        batsmen=[(bat_row_idx[n], n) for n in batsmen if n in bat_row_idx],
        over_runs_row=over_runs_idx,
        cumulative_row=cum_idx,
    )
    return rows, overs_list, inn_obj


def render_local_match(path: str, match_id: str) -> str:
    data = json.loads((ROOT / path).read_text(encoding="utf-8"))
    parts = ['<div class="bbb-wrap">']
    for inn in sorted(data["innings"], key=lambda x: x["num"]):
        rows, overs, inn_obj = innings_json_to_render_data(inn)
        parts.append(render_innings(inn_obj, rows, overs, match_id))
    parts.append("</div>")
    return "".join(parts)


def load_local_match(path: str) -> list[list[str]]:
    data = json.loads((ROOT / path).read_text(encoding="utf-8"))
    return json_to_sheet_rows(data)


def json_to_sheet_rows(data: dict) -> list[list[str]]:
    """Convert data/m6.json style match file into Google Sheet-like CSV rows."""
    max_over = max(
        max(o["num"] for o in inn["overs"]) for inn in data["innings"]
    )
    inn1_overs = {o["num"]: o["bowler"] for o in data["innings"][0]["overs"]}
    header = [""] * 8
    for onum in range(1, max_over + 1):
        bowler = inn1_overs.get(onum, "TBD")
        star = " ★" if onum == max_over else ""
        header.append(f"Over {onum}{star} {bowler} B1")
        for b in range(2, 7):
            header.append(f"B{b}")
        if onum == max_over:
            for b in range(7, 10):
                header.append(f"B{b}")
    rows: list[list[str]] = [header]

    for inn in data["innings"]:
        inn_num = inn["num"]
        title = (
            f"INNINGS {inn_num} — {inn['batting']} BATTING "
            f"| {inn['bowling']} BOWLING | Base: 200"
        )
        rows.append([title] + [""] * (len(header) - 1))

        batsmen = inn["batsmen"]
        bat_rows: dict[str, list[str]] = {name: [name] + [""] * 7 for name in batsmen}
        over_runs = ["Over Runs"] + [""] * 7
        cumulative = ["Cumulative"] + [""] * 7

        col = 8
        for over in inn["overs"]:
            onum = over["num"]
            deliveries = over["deliveries"]
            legal = 0
            for i, d in enumerate(deliveries):
                batter = d["batter"]
                symbol = d["symbol"]
                if batter not in bat_rows:
                    bat_rows[batter] = [batter] + [""] * 7
                while len(bat_rows[batter]) <= col:
                    bat_rows[batter].append("")
                bat_rows[batter][col] = symbol
                if symbol not in {"+", "WD", "O", "ON", "NB"} and not symbol.startswith("+"):
                    if symbol not in WKT_SYMBOLS and symbol != "R":
                        legal += 1
                col += 1
            while len(over_runs) <= col:
                over_runs.append("")
                cumulative.append("")
            first_col = col - len(deliveries)
            over_runs[first_col] = str(over.get("over_runs", ""))
            cumulative[first_col] = str(over["total"])
            # Pad to next over boundary (6 legal slots) when fewer extras columns used
            if onum < max_over:
                while (col - first_col) < 6:
                    col += 1

        for name in batsmen:
            row = bat_rows[name]
            while len(row) < len(header):
                row.append("")
            rows.append(row)
        while len(over_runs) < len(header):
            over_runs.append("")
            cumulative.append("")
        rows.append(over_runs)
        rows.append(cumulative)

    return rows


def load_sheet(gid: str) -> list[list[str]]:
    url = (
        f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq"
        f"?tqx=out:csv&gid={gid}"
    )
    raw = urllib.request.urlopen(url).read().decode()
    return [list(row) for row in __import__("csv").reader(raw.splitlines())]


def cell(row: list[str], col: int) -> str:
    if col >= len(row):
        return ""
    return (row[col] or "").strip()


def parse_overs(header_row: list[str]) -> list[tuple[int, str, list[int]]]:
    overs: list[tuple[int, str, list[int]]] = []
    col = 8
    max_over = 0
    while col < len(header_row):
        h = header_row[col]
        if h and h.startswith("Over"):
            m = re.match(r"Over\s+(\d+)(?:\s*★)?\s*(.*?)\s*B1", h)
            if m:
                max_over = max(max_over, int(m.group(1)))
        col += 1

    col = 8
    while col < len(header_row):
        h = header_row[col]
        if h and h.startswith("Over"):
            m = re.match(r"Over\s+(\d+)(?:\s*★)?\s*(.*?)\s*B1", h)
            if m:
                onum = int(m.group(1))
                bowler = (m.group(2) or "").strip() or "TBD"
                balls = list(range(col, col + 6))
                if onum == max_over:
                    extra = col + 6
                    while extra < len(header_row):
                        label = header_row[extra]
                        if label and re.fullmatch(r"B[7-9]", label):
                            balls.append(extra)
                            extra += 1
                        else:
                            break
                overs.append((onum, bowler, balls))
            col += 6
        else:
            col += 1
    return overs


def parse_innings(rows: list[list[str]]) -> list[Innings]:
    innings_list: list[Innings] = []
    seen_second = False

    for i, row in enumerate(rows):
        label = cell(row, 0)
        if not label:
            continue

        if label.startswith("INNINGS 2") and "BATTING" in label:
            seen_second = True
            batsmen = collect_batsmen(rows, i + 1)
            innings_list.append(
                Innings(
                    title=label.split("|")[0].strip(),
                    team_name=extract_team_name(label),
                    innings_num=2,
                    batsmen=batsmen[0],
                    over_runs_row=batsmen[1],
                    cumulative_row=batsmen[1] + 1,
                )
            )
        elif not seen_second and "INNINGS 1" in label and "BATTING" in label:
            batsmen = collect_batsmen(rows, 1)
            innings_list.append(
                Innings(
                    title="Innings 1",
                    team_name=extract_team_name(label),
                    innings_num=1,
                    batsmen=batsmen[0],
                    over_runs_row=batsmen[1],
                    cumulative_row=batsmen[1] + 1,
                )
            )

    return innings_list


def extract_team_name(title: str) -> str:
    m = re.search(r"INNINGS\s+\d+\s*[—–-]\s*(.+?)\s+BATTING", title, re.I)
    if m:
        return m.group(1).strip()
    if title.startswith("Innings"):
        return "Edgware CC"
    return title


def collect_batsmen(rows: list[list[str]], start: int) -> tuple[list[tuple[int, str]], int]:
    batsmen: list[tuple[int, str]] = []
    i = start
    while i < len(rows):
        label = cell(rows[i], 0)
        if label == "Over Runs":
            return batsmen, i
        if label and label != "Batsman" and not label.startswith("INNINGS"):
            batsmen.append((i, label))
        i += 1
    raise ValueError("Could not find Over Runs row")


def ord_over(n: int) -> str:
    if 11 <= n % 100 <= 13:
        sfx = "th"
    else:
        sfx = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{sfx} Over"


def ball_label(over_1indexed: int, delivery_index: int, total_deliveries: int) -> str:
    """MJCA-style: deliveries 1..N-1 are (n-1).i; final delivery is n.0."""
    if delivery_index == total_deliveries:
        return f"{over_1indexed}.0"
    return f"{over_1indexed - 1}.{delivery_index}"


def count_over_deliveries(raw: list[tuple[str, str, int | None]]) -> int:
    """Count delivery slots that produce output (B7–B9 extras included)."""
    n = 0
    for _, symbol, ball_idx in raw:
        if not symbol and ball_idx is None:
            continue
        n += 1
    return n


def expand_symbol(symbol: str, batter: str, bowler: str) -> list[BallEvent]:
    if symbol in {".", "0"}:
        return [
            BallEvent(".", "no run", "bbb-badge-dot", 0, False, True),
        ]

    if symbol.isdigit():
        runs = int(symbol)
        if runs == 4:
            return [BallEvent("4", "FOUR", "bbb-badge-4", 4, False, True, 4, True)]
        if runs == 6:
            return [BallEvent("6", "SIX", "bbb-badge-4", 6, False, True, 6, True)]
        desc = "1 run" if runs == 1 else f"{runs} runs"
        return [BallEvent(str(runs), desc, "bbb-badge-runs", runs, False, True, runs)]

    if symbol in {"+", "WD"}:
        return [BallEvent("+", "Wide (+2)", "bbb-badge-wide", 2, False, False)]

    m = re.fullmatch(r"\+(\d+)", symbol)
    if m:
        extra = int(m.group(1))
        return [
            BallEvent(
                "+",
                f"Wide (+2) + {extra} bye{'s' if extra != 1 else ''}",
                "bbb-badge-wide",
                2 + extra,
                False,
                False,
            )
        ]

    if symbol in {"O", "ON", "NB"}:
        return [BallEvent("o", "No ball (+2)", "bbb-badge-nb", 2, False, False)]

    m = re.fullmatch(r"O(\d+)", symbol)
    if m:
        bat = int(m.group(1))
        events = [BallEvent("o", "No ball (+2)", "bbb-badge-nb", 2, False, False)]
        if bat == 4:
            events.append(BallEvent("4", "FOUR", "bbb-badge-4", 4, False, True, 4, True))
        elif bat == 6:
            events.append(BallEvent("6", "SIX", "bbb-badge-4", 6, False, True, 6, True))
        elif bat > 0:
            desc = "1 run" if bat == 1 else f"{bat} runs"
            events.append(
                BallEvent(str(bat), desc, "bbb-badge-runs", bat, False, True, bat),
            )
        return events

    if symbol in WKT_SYMBOLS:
        if symbol == "C":
            desc = f"{batter} c & b {bowler}"
        elif symbol == "L":
            desc = f"{batter} lbw b {bowler}"
        elif symbol == "S":
            desc = f"{batter} st b {bowler}"
        elif symbol == "H":
            desc = f"{batter} hit wicket b {bowler}"
        else:
            desc = f"{batter} b {bowler}"
        return [BallEvent("W", desc, "bbb-badge-wkt", -5, True, True)]

    if symbol == "R":
        return [BallEvent("W", f"{batter} run out", "bbb-badge-wkt", -5, True, True)]

    if symbol.startswith("∆"):
        m = re.match(r"∆\+?(\d+)", symbol)
        n = int(m.group(1)) if m else 1
        return [
            BallEvent(
                "v",
                f"{n} bye{'s' if n != 1 else ''}",
                "bbb-badge-bye",
                n,
                False,
                False,
            ),
        ]

    if symbol.startswith("v"):
        m = re.match(r"v\+?(\d+)", symbol)
        n = int(m.group(1)) if m else 1
        return [
            BallEvent(
                "v",
                f"{n} leg bye{'s' if n != 1 else ''}",
                "bbb-badge-bye",
                n,
                False,
                False,
            ),
        ]

    if symbol == "0+4":
        return [
            BallEvent("+", "Wide (+2)", "bbb-badge-wide", 2, False, False),
            BallEvent("4", "FOUR", "bbb-badge-4", 4, False, True, 4, True),
        ]

    if symbol == "O+1":
        return [
            BallEvent("o", "No ball (+2)", "bbb-badge-nb", 2, False, False),
            BallEvent("1", "1 run", "bbb-badge-runs", 1, False, True, 1),
        ]

    return [BallEvent(symbol[:3], symbol, "bbb-badge-other", 0, False, True)]


def extract_over_deliveries(
    inn: Innings,
    rows: list[list[str]],
    ball_cols: list[int],
) -> list[tuple[str, str, int | None]]:
    """One entry per sheet column; ball_idx 1–6 for B1–B6, None for B7–B9 extras."""
    found: list[tuple[str, str, int | None]] = []
    for i, col in enumerate(ball_cols):
        ball_idx = (i + 1) if i < 6 else None
        batter = ""
        symbol = ""
        for row_idx, name in inn.batsmen:
            val = cell(rows[row_idx], col)
            if val:
                batter = name
                symbol = val
                break
        found.append((batter, symbol, ball_idx))
    return found


def simulate_innings(
    inn: Innings,
    rows: list[list[str]],
    overs: list[tuple[int, str, list[int]]],
) -> tuple[list[OverBlock], dict[str, BatterStats]]:
    batting_order = [name for _, name in inn.batsmen]
    stats: dict[str, BatterStats] = {name: BatterStats() for name in batting_order}

    total_score = BASE_SCORE
    wickets = 0
    striker = batting_order[0] if batting_order else ""
    non_striker = batting_order[1] if len(batting_order) > 1 else striker
    next_idx = 2

    partnership_idx = 0
    partnership_start = BASE_SCORE
    partnership_wickets = 0

    blocks: list[OverBlock] = []

    for onum, bowler, ball_cols in overs:
        pair_idx = (onum - 1) // PAIR_OVERS
        if pair_idx != partnership_idx:
            partnership_idx = pair_idx
            partnership_start = total_score
            partnership_wickets = 0
            i = pair_idx * 2
            if i < len(batting_order):
                striker = batting_order[i]
            if i + 1 < len(batting_order):
                non_striker = batting_order[i + 1]
            next_idx = max(next_idx, i + 2)

        first_col = ball_cols[0] if ball_cols else 0
        over_runs = cell(rows[inn.over_runs_row], first_col)
        cumulative = cell(rows[inn.cumulative_row], first_col)

        block = OverBlock(
            over_num=onum,
            bowler=bowler,
            is_last=onum == (overs[-1][0] if overs else 0),
            over_runs=over_runs,
            cumulative=cumulative,
            partnership_label=f"P{partnership_idx + 1}",
        )

        raw_deliveries = extract_over_deliveries(inn, rows, ball_cols)
        total_deliveries = count_over_deliveries(raw_deliveries)
        delivery_index = 0
        legal_in_over = 0

        for batter, symbol, ball_idx in raw_deliveries:
            if not symbol:
                if ball_idx is None:
                    continue
                delivery_index += 1
                facing = striker
                notation = ball_label(onum, delivery_index, total_deliveries)
                st = stats.setdefault(facing, BatterStats())
                st.balls += 1
                block.deliveries.append(
                    Delivery(
                        notation=notation,
                        symbol=".",
                        description="no run",
                        batter=facing,
                        bowler=bowler,
                        total_score=total_score,
                        wickets=wickets,
                        is_wicket=False,
                        is_boundary=False,
                        badge_class="bbb-badge-dot",
                    )
                )
                legal_in_over += 1
                continue

            facing = batter or striker
            events = expand_symbol(symbol, facing, bowler)
            delivery_index += 1
            notation = ball_label(onum, delivery_index, total_deliveries)

            for event in events:

                total_score += event.runs_delta
                if event.is_wicket:
                    st.out = True
                    st.dismissals += 1
                    wickets += 1
                    partnership_wickets += 1

                st = stats.setdefault(facing, BatterStats())
                if event.is_legal and not event.is_wicket:
                    st.balls += 1
                if event.bat_runs > 0:
                    st.runs += event.bat_runs

                block.deliveries.append(
                    Delivery(
                        notation=notation,
                        symbol=event.symbol,
                        description=event.description,
                        batter=facing,
                        bowler=bowler,
                        total_score=total_score,
                        wickets=wickets,
                        is_wicket=event.is_wicket,
                        is_boundary=event.is_boundary,
                        badge_class=event.badge_class,
                    )
                )

                if event.is_wicket:
                    pair_limit = (pair_idx + 1) * 2
                    if next_idx < len(batting_order) and next_idx < pair_limit:
                        if facing == striker:
                            striker = batting_order[next_idx]
                        else:
                            non_striker = batting_order[next_idx]
                        next_idx += 1
                elif event.bat_runs % 2 == 1:
                    striker, non_striker = non_striker, striker
                elif facing == non_striker and event.bat_runs > 0:
                    striker, non_striker = non_striker, striker

                if event.is_legal:
                    legal_in_over += 1

        if legal_in_over >= 1:
            striker, non_striker = non_striker, striker

        if block.deliveries and cumulative and re.fullmatch(r"-?\d+", cumulative):
            target = int(cumulative)
            if block.deliveries[-1].total_score != target:
                block.deliveries[-1].total_score = target
            total_score = target

        block.wickets = sum(1 for d in block.deliveries if d.is_wicket)
        block.partnership_runs = total_score - partnership_start
        block.partnership_wickets = partnership_wickets
        block.batter_summaries = pair_batter_summaries(
            batting_order, pair_idx, striker, non_striker, stats
        )
        blocks.append(block)

    return blocks, stats


def format_over_runs_summary(over_runs: str, wickets: int) -> str:
    runs = (over_runs or "0").strip()
    if runs in {"1", "-1"}:
        text = f"{html.escape(runs)} run"
    elif runs:
        text = f"{html.escape(runs)} runs"
    else:
        text = "0 runs"
    if wickets:
        w = "wkt" if wickets == 1 else "wkts"
        text += f" · {wickets} {w}"
    return text


def render_delivery_row(d: Delivery) -> str:
    row_cls = "bbb-ball-row wkt" if d.is_wicket else "bbb-ball-row"
    boundary = " boundary" if d.is_boundary else ""
    return (
        f'<li class="{row_cls}">'
        f'<span class="bbb-ov">{html.escape(d.notation)}</span>'
        f'<span class="bbb-badge {d.badge_class}{boundary}">{html.escape(d.symbol)}</span>'
        f'<span class="bbb-desc">'
        f"{html.escape(d.description)}"
        f'<span class="bbb-meta">{html.escape(d.batter)}*</span>'
        f"</span>"
        f'<span class="bbb-score">{d.total_score}-{d.wickets}</span>'
        f"</li>"
    )


def render_over(block: OverBlock, uid: str) -> str:
    star = " ★" if block.is_last else ""
    over_label = f"{ord_over(block.over_num)} — {html.escape(block.bowler)}{star}"

    batters_bits = []
    for name, runs, balls, is_striker in block.batter_summaries:
        star_mark = "*" if is_striker else ""
        batters_bits.append(f"{html.escape(name)} {runs}{star_mark} ({balls})")

    p_wkt = ""
    if block.partnership_wickets:
        p_wkt = f" ({block.partnership_wickets} wkt)"

    end_score = ""
    if block.deliveries:
        last = block.deliveries[-1]
        end_score = f"{last.total_score}-{last.wickets}"
    elif block.cumulative:
        end_score = html.escape(block.cumulative)

    batters_line = " ".join(batters_bits)
    balls_html = "".join(render_delivery_row(d) for d in reversed(block.deliveries))
    if not balls_html:
        balls_html = '<li class="bbb-ball-row empty"><span class="bbb-desc">No balls recorded</span></li>'

    return (
        f'<div class="bbb-over" id="{uid}">'
        f'<button type="button" class="bbb-over-hd" onclick="toggleBbbOver(\'{uid}\')" aria-expanded="true">'
        f'<div class="bbb-over-main">'
        f'<span class="bbb-over-num">{html.escape(over_label)}</span>'
        f'<span class="bbb-over-batters">'
        f"{batters_line} "
        f'<span class="bbb-over-p">{html.escape(block.partnership_label)}: '
        f"{block.partnership_runs}{html.escape(p_wkt)}</span>"
        f"</span></div>"
        f'<span class="bbb-over-sum">{format_over_runs_summary(block.over_runs, block.wickets)}</span>'
        f'<span class="bbb-over-score">{end_score}</span>'
        f'<span class="bbb-chev">▾</span>'
        f"</button>"
        f'<ul class="bbb-balls">{balls_html}</ul>'
        f"</div>"
    )


def events_from_item(item: dict, facing: str, bowler: str) -> list[BallEvent]:
    """Build BallEvents from JSON delivery, honouring explicit runs/description/fielder."""
    symbol = (item.get("symbol") or "").strip()
    desc_override = (item.get("description") or "").strip()
    fielder = (item.get("fielder") or "").strip()
    runs_override = item.get("runs")
    bat_override = item.get("bat_runs")
    wicket_override = item.get("wicket")

    if symbol == "0+4":
        events = expand_symbol("0+4", facing, bowler)
    elif symbol == "O+1":
        events = expand_symbol("O+1", facing, bowler)
    else:
        events = expand_symbol(symbol, facing, bowler)

    if wicket_override:
        for ev in events:
            ev.is_wicket = True
            ev.runs_delta = -5
            ev.bat_runs = 0
    if runs_override is not None:
        events = [BallEvent(
            symbol=events[0].symbol if events else symbol[:3],
            description=desc_override or events[0].description if events else symbol,
            badge_class=events[0].badge_class if events else "bbb-badge-other",
            runs_delta=int(runs_override),
            is_wicket=bool(wicket_override or (events and events[0].is_wicket)),
            is_legal=events[0].is_legal if events else True,
            bat_runs=int(bat_override) if bat_override is not None else (events[0].bat_runs if events else 0),
            is_boundary=bool(bat_override == 4 or bat_override == 6 or symbol in {"4", "6"}),
        )]
    elif bat_override is not None:
        for ev in events:
            if ev.is_legal and not ev.is_wicket:
                ev.bat_runs = int(bat_override)
                if bat_override == 4:
                    ev.is_boundary = True
                    ev.runs_delta = 4 if ev.runs_delta < 4 else ev.runs_delta
                elif bat_override == 6:
                    ev.is_boundary = True
                    ev.runs_delta = 6 if ev.runs_delta < 6 else ev.runs_delta

    if desc_override:
        if symbol == "O+1" and len(events) > 1:
            events[0].description = desc_override
        elif len(events) == 1:
            events[0].description = desc_override
        elif events:
            events[-1].description = desc_override

    if fielder and symbol == "R":
        for ev in events:
            if ev.is_wicket:
                ev.description = desc_override or f"{facing} run out ({fielder})"
    elif fielder and symbol == "C":
        for ev in events:
            if ev.is_wicket:
                ev.description = desc_override or f"{facing} c {fielder} b {bowler}"

    if symbol == "5" and not desc_override:
        for ev in events:
            ev.description = "5 runs"

    return events


def simulate_innings_json(inn_data: dict) -> tuple[list[OverBlock], dict[str, BatterStats]]:
    """Simulate one innings from data/m6.json style local match file."""
    batting_order = inn_data["batsmen"]
    stats: dict[str, BatterStats] = {name: BatterStats() for name in batting_order}

    total_score = BASE_SCORE
    wickets = 0
    striker = batting_order[0] if batting_order else ""
    non_striker = batting_order[1] if len(batting_order) > 1 else striker
    next_idx = 2

    partnership_idx = 0
    partnership_start = BASE_SCORE
    partnership_wickets = 0

    blocks: list[OverBlock] = []
    overs_list = inn_data["overs"]
    max_over = overs_list[-1]["num"] if overs_list else 0

    for over in overs_list:
        onum = over["num"]
        bowler = over["bowler"]
        pair_idx = (onum - 1) // PAIR_OVERS
        if pair_idx != partnership_idx:
            partnership_idx = pair_idx
            partnership_start = total_score
            partnership_wickets = 0
            i = pair_idx * 2
            if i < len(batting_order):
                striker = batting_order[i]
            if i + 1 < len(batting_order):
                non_striker = batting_order[i + 1]
            next_idx = max(next_idx, i + 2)

        block = OverBlock(
            over_num=onum,
            bowler=bowler,
            is_last=onum == max_over,
            over_runs=str(over.get("over_runs", "")),
            cumulative=str(over.get("total", "")),
            partnership_label=f"P{partnership_idx + 1}",
        )

        wickets_at_over_start = wickets
        deliveries = over["deliveries"]
        legal_in_over = 0
        legal_balls_seen: set[int] = set()

        for item in deliveries:
            facing = item.get("batter") or striker
            symbol = (item.get("symbol") or "").strip()
            ball_idx = item.get("ball_index")
            if item.get("notation"):
                notation = item["notation"]
            elif ball_idx is not None:
                max_ball = max((d.get("ball_index") or 0) for d in deliveries) or ball_idx
                notation = f"{onum}.0" if ball_idx == max_ball else f"{onum - 1}.{ball_idx}"
            else:
                notation = f"{onum}.0"

            if not symbol:
                st = stats.setdefault(facing, BatterStats())
                st.balls += 1
                block.deliveries.append(
                    Delivery(
                        notation=notation,
                        symbol=".",
                        description=item.get("description") or "no run",
                        batter=facing,
                        bowler=bowler,
                        total_score=total_score,
                        wickets=wickets,
                        is_wicket=False,
                        is_boundary=False,
                        badge_class="bbb-badge-dot",
                    )
                )
                if ball_idx is None or ball_idx not in legal_balls_seen:
                    if ball_idx is not None:
                        legal_balls_seen.add(ball_idx)
                    legal_in_over += 1
                continue

            events = events_from_item(item, facing, bowler)

            for event in events:
                st = stats.setdefault(facing, BatterStats())
                total_score += event.runs_delta
                if event.is_wicket:
                    st.out = True
                    st.dismissals += 1
                    wickets += 1
                    partnership_wickets += 1

                if event.is_legal and not event.is_wicket:
                    st.balls += 1
                if event.bat_runs > 0:
                    st.runs += event.bat_runs

                block.deliveries.append(
                    Delivery(
                        notation=notation,
                        symbol=event.symbol,
                        description=event.description,
                        batter=facing,
                        bowler=bowler,
                        total_score=total_score,
                        wickets=wickets,
                        is_wicket=event.is_wicket,
                        is_boundary=event.is_boundary,
                        badge_class=event.badge_class,
                    )
                )

                if event.is_wicket:
                    pair_limit = (pair_idx + 1) * 2
                    if next_idx < len(batting_order) and next_idx < pair_limit:
                        if facing == striker:
                            striker = batting_order[next_idx]
                        else:
                            non_striker = batting_order[next_idx]
                        next_idx += 1
                elif event.bat_runs % 2 == 1:
                    striker, non_striker = non_striker, striker
                elif facing == non_striker and event.bat_runs > 0:
                    striker, non_striker = non_striker, striker

                if event.is_legal:
                    if ball_idx is None or ball_idx not in legal_balls_seen:
                        if ball_idx is not None:
                            legal_balls_seen.add(ball_idx)
                        legal_in_over += 1

        if legal_in_over >= 1:
            striker, non_striker = non_striker, striker

        cumulative = over.get("total", "")
        if block.deliveries and cumulative and re.fullmatch(r"-?\d+", str(cumulative)):
            target = int(cumulative)
            if block.deliveries[-1].total_score != target:
                block.deliveries[-1].total_score = target
            total_score = target

        block.wickets = wickets - wickets_at_over_start
        block.partnership_runs = total_score - partnership_start
        block.partnership_wickets = partnership_wickets
        block.batter_summaries = pair_batter_summaries(
            batting_order, pair_idx, striker, non_striker, stats
        )
        blocks.append(block)

    return blocks, stats


def render_innings_json(inn_data: dict, match_id: str) -> str:
    blocks, _stats = simulate_innings_json(inn_data)
    inn_label = (
        f"{html.escape(inn_data['batting'])} — Innings {inn_data['num']}"
    )
    parts = [
        '<section class="bbb-panel">',
        '<div class="bbb-inn-bar">',
        f"<span>{inn_label}</span>",
        f"<span>{COMMENTARY_LABEL}</span>",
        "</div>",
        '<div class="bbb-list">',
    ]
    for block in reversed(blocks):
        uid = f"bbb-{match_id}-i{inn_data['num']}-o{block.over_num}"
        parts.append(render_over(block, uid))
    parts.extend(["</div></section>"])
    return "".join(parts)


def render_from_json(match_id: str, data: dict) -> str:
    """Commentary panels top-to-bottom: Result, Inn2, Inn1, Toss."""
    parts = ['<div class="bbb-wrap">']
    match_meta = data.get("match") or {}
    innings = data.get("innings") or []
    result_html = render_result(match_meta, innings)
    if result_html:
        parts.append(result_html)
    for inn in sorted(innings, key=lambda x: x["num"], reverse=True):
        parts.append(render_innings_json(inn, match_id))
    toss_html = render_toss(match_meta.get("toss"))
    if toss_html:
        parts.append(toss_html)
    parts.append("</div>")
    return "".join(parts)


def render_innings(
    inn: Innings,
    rows: list[list[str]],
    overs: list[tuple[int, str, list[int]]],
    match_id: str,
) -> str:
    blocks, _stats = simulate_innings(inn, rows, overs)
    inn_label = f"{html.escape(inn.team_name)} — Innings {inn.innings_num}"

    parts = [
        '<section class="bbb-panel">',
        '<div class="bbb-inn-bar">',
        f"<span>{inn_label}</span>",
        f"<span>{COMMENTARY_LABEL}</span>",
        "</div>",
        '<div class="bbb-list">',
    ]
    for block in reversed(blocks):
        uid = f"bbb-{match_id}-i{inn.innings_num}-o{block.over_num}"
        parts.append(render_over(block, uid))
    parts.extend(["</div></section>"])
    return "".join(parts)


def sheet_has_ball_data(rows: list[list[str]]) -> bool:
    """True when at least one delivery cell has a scoring symbol."""
    symbols = WKT_SYMBOLS | {".", "0", "+", "WD", "O", "ON", "NB", "R"}
    for row in rows:
        for val in row[8:]:
            v = (val or "").strip()
            if not v:
                continue
            if v in symbols or v.isdigit() or re.fullmatch(r"[+O]\d+", v) or v.startswith(("∆", "v")):
                return True
    return False


def sheet_result_pending(rows: list[list[str]]) -> bool:
    for row in rows:
        label = cell(row, 0)
        if label.startswith("RESULT:") and "TBD" in label.upper():
            return True
    return not sheet_has_ball_data(rows)


def render_pending(match_id: str, cfg: dict) -> str:
    teams = cfg.get("teams", ("Opposition", "Edgware CC"))
    overs = cfg.get("overs", 16)
    return (
        '<div class="bbb-wrap">'
        '<section class="bbb-panel">'
        '<div class="bbb-inn-bar">'
        f"<span>{html.escape(teams[0])} — Innings 1</span>"
        f"<span>{COMMENTARY_LABEL}</span>"
        "</div>"
        '<div class="bbb-list">'
        '<li class="bbb-ball-row empty" style="display:block;padding:20px 14px;">'
        "<span class=\"bbb-desc\" style=\"text-align:center;\">"
        f"<strong>Scores pending</strong> — {html.escape(cfg['label'])} ball-by-ball will appear here "
        "once the Google Sheet is scored."
        "</span></li>"
        "</div></section>"
        '<section class="bbb-panel">'
        '<div class="bbb-inn-bar">'
        f"<span>{html.escape(teams[1])} — Innings 2</span>"
        f"<span>{COMMENTARY_LABEL}</span>"
        "</div>"
        '<div class="bbb-list">'
        '<li class="bbb-ball-row empty" style="display:block;padding:20px 14px;">'
        "<span class=\"bbb-desc\" style=\"text-align:center;\">"
        f"<strong>Scores pending</strong> — {overs} overs per innings · base score 200."
        "</span></li>"
        "</div></section>"
        "</div>"
    )


def render_match(match_id: str) -> str:
    cfg = MATCHES[match_id]
    local = cfg.get("local")
    if local and (ROOT / local).exists():
        data = json.loads((ROOT / local).read_text(encoding="utf-8"))
        return render_from_json(match_id, data)
    rows = load_sheet(cfg["gid"])
    if sheet_result_pending(rows):
        return render_pending(match_id, cfg)
    overs = parse_overs(rows[0])
    innings = parse_innings(rows)

    parts = ['<div class="bbb-wrap">']
    for inn in innings:
        parts.append(render_innings(inn, rows, overs, match_id))
    parts.append("</div>")
    return "".join(parts)


def main() -> None:
    for match_id in MATCHES:
        content = render_match(match_id)
        out = f"/Users/kunalchitkara/howzzat/edgeware-u9/bbb/{match_id}.html"
        with open(out, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Wrote {out} ({len(content)} chars)")


if __name__ == "__main__":
    main()
