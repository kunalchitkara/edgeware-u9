#!/usr/bin/env python3
"""Extract ball-by-ball data from Google Sheets and generate list-style HTML."""

from __future__ import annotations

import html
import re
import urllib.request
from dataclasses import dataclass, field

SHEET_ID = "1cxSoOdd3rgEp-EtyKzxbeWssac5t0gM4F9CnMwkQFL8"
BASE_SCORE = 200
PAIR_OVERS = 4

MATCHES = {
    "m2": {"gid": "737570712", "label": "M2"},
    "m4": {"gid": "1996740206", "label": "M4"},
    "m5": {"gid": "669851544", "label": "M5"},
}

WKT_SYMBOLS = {"B", "C", "S", "L", "H"}


@dataclass
class BatterStats:
    runs: int = 0
    balls: int = 0


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
            m = re.match(r"Over\s+(\d+)(?:\s*★)?\s+(.+?)\s+B1", h)
            if m:
                max_over = max(max_over, int(m.group(1)))
        col += 1

    col = 8
    while col < len(header_row):
        h = header_row[col]
        if h and h.startswith("Over"):
            m = re.match(r"Over\s+(\d+)(?:\s*★)?\s+(.+?)\s+B1", h)
            if m:
                onum = int(m.group(1))
                bowler = m.group(2).strip()
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
        elif not seen_second and i == 0 and "INNINGS 1" in label:
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
) -> list[OverBlock]:
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
                    if next_idx < len(batting_order):
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
        block.batter_summaries = [
            (striker, stats[striker].runs, stats[striker].balls, True),
            (non_striker, stats[non_striker].runs, stats[non_striker].balls, False),
        ]
        blocks.append(block)

    return blocks


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
        f'<span class="bbb-meta">{html.escape(d.batter)}* · {html.escape(d.bowler)}</span>'
        f"</span>"
        f'<span class="bbb-score">{d.total_score}-{d.wickets}</span>'
        f"</li>"
    )


def render_over(block: OverBlock, uid: str) -> str:
    star = " ★" if block.is_last else ""
    over_label = ord_over(block.over_num) + star

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
    balls_html = "".join(render_delivery_row(d) for d in block.deliveries)
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


def render_innings(
    inn: Innings,
    rows: list[list[str]],
    overs: list[tuple[int, str, list[int]]],
    match_id: str,
) -> str:
    blocks = simulate_innings(inn, rows, overs)
    inn_label = f"{html.escape(inn.team_name)} — Innings {inn.innings_num}"

    parts = [
        '<section class="bbb-panel">',
        '<div class="bbb-inn-bar">',
        f"<span>{inn_label}</span>",
        "<span>Ball-by-ball</span>",
        "</div>",
        '<div class="bbb-list">',
    ]
    for block in blocks:
        uid = f"bbb-{match_id}-i{inn.innings_num}-o{block.over_num}"
        parts.append(render_over(block, uid))
    parts.extend(["</div></section>"])
    return "".join(parts)


def render_match(match_id: str) -> str:
    cfg = MATCHES[match_id]
    rows = load_sheet(cfg["gid"])
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
