#!/usr/bin/env python3
"""Build data/m7.json from M7 Google Sheet CSV (ball-by-ball only)."""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "m7_sheet.csv"
OUT = ROOT / "data" / "m7.json"

sys.path.insert(0, str(ROOT / "scripts"))
from build_m6 import annotate_notation, simulate_innings  # noqa: E402

SHEET_ID = "1BLANhVMw69HEuN38wgTXkIOFjNw9a7em"
GID = "1976564850"

# Strict source mapping (1-indexed) from M7 sheet.
INN1_HEADER_SHEET_ROW = 5
INN1_BOWLER_SHEET_ROW = 6
INN1_BALL_SHEET_ROW = 7
INN1_BAT_START_SHEET_ROW = 8
INN1_OVER_RUNS_SHEET_ROW = 17
INN1_CUM_SHEET_ROW = 18

INN2_HEADER_SHEET_ROW = 34
INN2_BOWLER_SHEET_ROW = 35
INN2_BALL_SHEET_ROW = 36
INN2_BAT_START_SHEET_ROW = 37
INN2_OVER_RUNS_SHEET_ROW = 46
INN2_CUM_SHEET_ROW = 47
# Row 68 (1-indexed): caught-by / run-out-by fielder names aligned to ball columns.
FIELDER_SHEET_ROW = 68
BATTING_WKTS_COL = 3
BATTING_RUNOUTS_COL = 4
ECC_FIELDERS = frozenset(
    {"Avyaan", "Drish", "Qaim", "Taran", "Krish", "Shyam", "Aanya", "Kaiyan", "Viaan"}
)


def cell(row: list[str], col: int) -> str:
    if col >= len(row):
        return ""
    return (row[col] or "").strip()


def to_int(value: str) -> int:
    try:
        return int((value or "").strip())
    except (TypeError, ValueError):
        return 0


def load_rows() -> list[list[str]]:
    text = CSV_PATH.read_text(encoding="utf-8")
    return list(csv.reader(text.splitlines()))


def parse_over_blocks(header: list[str], ball_row: list[str]) -> list[tuple[int, str, list[int]]]:
    """Return (over_num, default_bowler, ball_cols) using B1-B6 labels (B7-B9 on last over only)."""
    markers: list[tuple[int, int, str]] = []
    for col, label in enumerate(header):
        m = re.match(r"Over\s+(\d+)(?:\s*★)?(?:\s+(.*?))?\s*$", label or "")
        if m:
            onum = int(m.group(1))
            bowler = (m.group(2) or "").strip() or "TBD"
            markers.append((onum, col, bowler))
    markers.sort(key=lambda x: x[1])
    max_over = max(m[0] for m in markers) if markers else 0
    blocks: list[tuple[int, str, list[int]]] = []
    for i, (onum, start, bowler) in enumerate(markers):
        end = markers[i + 1][1] if i + 1 < len(markers) else len(header)
        scan_end = len(header) if onum == max_over else end
        balls: list[int] = []
        for col in range(start, scan_end):
            label = cell(ball_row, col)
            if re.fullmatch(r"B[1-6]", label):
                balls.append(col)
            elif onum == max_over and re.fullmatch(r"B[7-9]", label):
                balls.append(col)
        if onum != max_over:
            balls = balls[:6]
        blocks.append((onum, bowler, balls))
    return blocks


def bowlers_from_row(rows: list[list[str]], bowler_row_idx: int, over_blocks: list[tuple[int, str, list[int]]]) -> dict[int, str]:
    """Read bowler names at each over's start column from the dedicated bowler row."""
    row = rows[bowler_row_idx]
    out: dict[int, str] = {}
    for onum, _default, ball_cols in over_blocks:
        col = ball_cols[0]
        name = cell(row, col)
        if name and not re.fullmatch(r"B\d+", name):
            out[onum] = name
    return out


def fielder_map(rows: list[list[str]]) -> dict[int, str]:
    """Fielding credits from sheet row 68 only (caught by / run out by)."""
    idx = FIELDER_SHEET_ROW - 1
    if idx >= len(rows):
        return {}
    out: dict[int, str] = {}
    for col, raw in enumerate(rows[idx]):
        name = (raw or "").strip()
        if name in ECC_FIELDERS:
            out[col] = name
    return out


def symbol_to_delivery(symbol: str, batter: str, fielders: dict[int, str], col: int, bowler: str) -> dict:
    sym = symbol.strip()
    item: dict = {"symbol": sym, "batter": batter}
    if sym in {"B", "C", "S", "L", "H", "R"}:
        item["wicket"] = True
    if sym == "C" and col in fielders:
        item["fielder"] = fielders[col]
    elif sym == "R" and col in fielders:
        item["fielder"] = fielders[col]
    elif sym in {"+", "WD"}:
        item["extras_type"] = "wide"
    elif sym in {"O", "ON", "NB"}:
        item["extras_type"] = "noball"
    elif sym.startswith("∆"):
        item["extras_type"] = "legbye"
    elif sym.startswith("v"):
        item["extras_type"] = "legbye"
        m = re.match(r"v\+?(\d+)", sym)
        if m:
            item["symbol"] = f"∆+{m.group(1)}"
    return item


def extract_innings(
    rows: list[list[str]],
    *,
    bat_start: int,
    bat_count: int,
    over_blocks: list[tuple[int, str, list[int]]],
    bowler_for_over: dict[int, str] | None,
    over_runs_row: int,
    cum_row: int,
    fielders: dict[int, str],
) -> dict:
    batsmen = [cell(rows[bat_start + i], 0) for i in range(bat_count)]
    overs_out: list[dict] = []
    last_over = over_blocks[-1][0]
    for onum, default_bowler, ball_cols in over_blocks:
        bowler = (bowler_for_over or {}).get(onum, default_bowler)
        if onum == last_over and len(ball_cols) > 6:
            extras = [
                c
                for c in ball_cols[6:]
                if any(cell(rows[bat_start + bi], c) for bi in range(bat_count))
            ]
            ball_cols = ball_cols[:6] + extras
        deliveries: list[dict] = []
        for ball_idx, col in enumerate(ball_cols, start=1):
            events: list[tuple[str, str]] = []
            for bi in range(bat_count):
                ridx = bat_start + bi
                val = cell(rows[ridx], col)
                if val:
                    events.append((val, cell(rows[ridx], 0)))
            if not events:
                events = [(".", batsmen[0])]
            for sym, batter in events:
                item = symbol_to_delivery(sym, batter, fielders, col, bowler)
                item["ball_index"] = ball_idx
                deliveries.append(item)
        first = ball_cols[0]
        overs_out.append(
            {
                "num": onum,
                "bowler": bowler,
                "over_runs": cell(rows[over_runs_row], first),
                "total": cell(rows[cum_row], first),
                "deliveries": deliveries,
            }
        )
    return {"overs": overs_out, "batsmen": batsmen}


def enforce_legal_ball_integrity(inn: dict, *, innings_num: int) -> None:
    for over in inn["overs"]:
        idxs = {int(d.get("ball_index") or 0) for d in over["deliveries"]}
        expected = {1, 2, 3, 4, 5, 6}
        missing = sorted(expected - idxs)
        if missing:
            raise ValueError(
                f"Innings {innings_num} over {over['num']} missing legal balls: {missing}"
            )


def apply_m7_specific_corrections(inn2: dict) -> None:
    """
    Manual scorer correction:
    - Dillon 1 + Hayen run out (Drish) belongs to 11.4 (12th over), not 10.4.
    - In innings 2 over 6 ball 2 (notation 5.2), Milan was caught:
      c Avyaan b Drish.
    """
    # Keep strict sheet-column mapping intact: convert the existing legal-ball slot
    # (over 6, ball_index 2) into a caught dismissal in-place.
    o6 = next((o for o in inn2["overs"] if o["num"] == 6), None)
    if o6 is not None:
        ball_52 = next((d for d in o6["deliveries"] if d.get("ball_index") == 2), None)
        if ball_52 is not None:
            ball_52["symbol"] = "C"
            ball_52["wicket"] = True
            ball_52["fielder"] = "Avyaan"
            ball_52.pop("extras_type", None)
            ball_52.pop("bat_runs", None)
            ball_52.pop("runs", None)
            ball_52.pop("description", None)

    # Innings 2 over 14 ball 2 (notation 13.2): Arun was bowled by Shyam.
    o14 = next((o for o in inn2["overs"] if o["num"] == 14), None)
    if o14 is not None:
        ball_132 = next((d for d in o14["deliveries"] if d.get("ball_index") == 2), None)
        if ball_132 is not None:
            ball_132["symbol"] = "B"
            ball_132["wicket"] = True
            ball_132.pop("fielder", None)
            ball_132.pop("extras_type", None)
            ball_132.pop("bat_runs", None)
            ball_132.pop("runs", None)
            ball_132.pop("description", None)

    o11 = next(o for o in inn2["overs"] if o["num"] == 11)
    o12 = next(o for o in inn2["overs"] if o["num"] == 12)
    runout_idx = next(
        (
            i
            for i, d in enumerate(o11["deliveries"])
            if d.get("symbol") == "R" and d.get("batter") == "Hayen" and d.get("ball_index") == 4
        ),
        None,
    )
    if runout_idx is None:
        return

    runout = dict(o11["deliveries"].pop(runout_idx))
    runout["ball_index"] = 4
    runout["fielder"] = "Drish"
    insert_at = next(
        (
            i + 1
            for i, d in enumerate(o12["deliveries"])
            if d.get("batter") == "Dillon" and d.get("symbol") == "1" and d.get("ball_index") == 4
        ),
        None,
    )
    if insert_at is None:
        o12["deliveries"].append(runout)
    else:
        o12["deliveries"].insert(insert_at, runout)


def batting_row_wicket_events(rows: list[list[str]], *, bat_start: int, bat_count: int) -> int:
    total = 0
    for i in range(bat_count):
        row = rows[bat_start + i]
        total += to_int(cell(row, BATTING_WKTS_COL))
        total += to_int(cell(row, BATTING_RUNOUTS_COL))
    return total


def delivery_wicket_events(inn: dict) -> int:
    return sum(
        1
        for over in inn.get("overs", [])
        for delivery in over.get("deliveries", [])
        if delivery.get("wicket")
    )


def main() -> None:
    rows = load_rows()
    fielders = fielder_map(rows)

    inn1_header = rows[INN1_HEADER_SHEET_ROW - 1]
    inn1_ball_row = rows[INN1_BALL_SHEET_ROW - 1]
    inn1_blocks = parse_over_blocks(inn1_header, inn1_ball_row)
    inn1_bowlers = bowlers_from_row(rows, INN1_BOWLER_SHEET_ROW - 1, inn1_blocks)

    inn1 = extract_innings(
        rows,
        bat_start=INN1_BAT_START_SHEET_ROW - 1,
        bat_count=8,
        over_blocks=inn1_blocks,
        bowler_for_over=inn1_bowlers,
        over_runs_row=INN1_OVER_RUNS_SHEET_ROW - 1,
        cum_row=INN1_CUM_SHEET_ROW - 1,
        fielders=fielders,
    )
    inn1.update(
        {
            "num": 1,
            "batting": "Edgware CC",
            "bowling": "Headstone Manor",
        }
    )
    inn1_wickets_sheet = batting_row_wicket_events(
        rows, bat_start=INN1_BAT_START_SHEET_ROW - 1, bat_count=8
    )

    inn2_header = rows[INN2_HEADER_SHEET_ROW - 1]
    inn2_ball_row = rows[INN2_BALL_SHEET_ROW - 1]
    inn2_blocks = parse_over_blocks(inn2_header, inn2_ball_row)
    inn2_bowlers = bowlers_from_row(rows, INN2_BOWLER_SHEET_ROW - 1, inn2_blocks)

    inn2 = extract_innings(
        rows,
        bat_start=INN2_BAT_START_SHEET_ROW - 1,
        bat_count=8,
        over_blocks=inn2_blocks,
        bowler_for_over=inn2_bowlers,
        over_runs_row=INN2_OVER_RUNS_SHEET_ROW - 1,
        cum_row=INN2_CUM_SHEET_ROW - 1,
        fielders=fielders,
    )
    apply_m7_specific_corrections(inn2)
    inn2_wickets_sheet = batting_row_wicket_events(
        rows, bat_start=INN2_BAT_START_SHEET_ROW - 1, bat_count=8
    )
    enforce_legal_ball_integrity(inn1, innings_num=1)
    enforce_legal_ball_integrity(inn2, innings_num=2)
    inn2.update(
        {
            "num": 2,
            "batting": "Headstone Manor",
            "bowling": "Edgware CC",
        }
    )

    annotate_notation(inn1, 16)
    annotate_notation(inn2, 16)

    s1 = simulate_innings(inn1)
    s2 = simulate_innings(inn2)
    margin = s1["final_total"] - s2["final_total"]
    chase = s1["final_total"] + 1
    inn2["target"] = chase

    def batting_wickets(inn: dict) -> int:
        return sum(1 for b in inn["batting_summary"] if b.get("dismissal") != "not out")

    for inn, stats, sheet_wkts in (
        (inn1, s1, inn1_wickets_sheet),
        (inn2, s2, inn2_wickets_sheet),
    ):
        symbol_wkts = delivery_wicket_events(inn)
        unique_wkts = sum(
            1 for b in stats["batting_summary"] if b.get("dismissal") != "not out"
        )
        inn.update(
            {
                k: stats[k]
                for k in (
                    "partnerships",
                    "batting_summary",
                    "bowling_summary",
                    "fielding",
                    "final_total",
                    "wickets",
                )
            }
        )
        inn["wickets_symbol_events"] = symbol_wkts
        inn["wickets_unique_dismissals"] = unique_wkts
        inn["wickets_sheet_events"] = sheet_wkts
        # Display scorelines should follow scorer event totals from strict batting rows.
        inn["wickets"] = sheet_wkts

    data = {
        "match": {
            "label": "M7",
            "date": "21 June 2026",
            "venue": "Canons High School",
            "home": "Edgware CC",
            "away": "Headstone Manor",
            "format": "16 overs",
            "result": f"Edgware CC won by {margin} runs",
            "margin_runs": margin,
            "toss": {"winner": "Headstone Manor", "decision": "bowl"},
            "sheet_id": SHEET_ID,
            "gid": GID,
        },
        "innings": [inn1, inn2],
    }

    OUT.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT}")
    print(
        "Innings 1 (ECC): "
        f"{s1['final_total']}-{inn1['wickets']} "
        f"(sheet events {inn1['wickets_sheet_events']}, "
        f"symbol events {inn1['wickets_symbol_events']}, "
        f"unique {inn1['wickets_unique_dismissals']})"
    )
    print(
        "Innings 2 (HSM): "
        f"{s2['final_total']}-{inn2['wickets']} (target {chase}) "
        f"(sheet events {inn2['wickets_sheet_events']}, "
        f"symbol events {inn2['wickets_symbol_events']}, "
        f"unique {inn2['wickets_unique_dismissals']})"
    )
    print(f"Margin: ECC by {margin} runs")
    ov1_2 = next(o for o in inn1["overs"] if o["num"] == 2)
    ov2_2 = next(o for o in inn2["overs"] if o["num"] == 2)
    print(f"Inn1 over 2 bowler: {ov1_2['bowler']} (sheet row {INN1_BOWLER_SHEET_ROW})")
    print(f"Inn2 over 2 bowler: {ov2_2['bowler']} (sheet row {INN2_BOWLER_SHEET_ROW})")
    if margin != 61:
        print(f"WARNING: expected margin 61, got {margin}")


if __name__ == "__main__":
    main()
