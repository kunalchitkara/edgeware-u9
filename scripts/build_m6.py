#!/usr/bin/env python3
"""Build data/m6.json from user-corrected ball-by-ball notation."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "m6.json"
BASE = 200
WKT_PENALTY = -5
PAIR_OVERS = 4

WKT_SYMBOLS = {"B", "C", "S", "L", "H", "R"}


def pair_batter_summaries(
    order: list[str], pair_idx: int, striker: str, non_striker: str, stats: dict
) -> list[tuple[str, int, int, bool]]:
    """U9 pair headers: always show the designated pair, not a substitute from the next block."""
    b1 = order[pair_idx * 2]
    b2 = order[pair_idx * 2 + 1]
    if striker in (b1, b2):
        on, off = striker, (b2 if striker == b1 else b1)
    elif non_striker in (b1, b2):
        on, off = non_striker, (b2 if non_striker == b1 else b1)
    else:
        on, off = b1, b2
    return [
        (on, stats[on]["runs"], stats[on]["balls"], True),
        (off, stats[off]["runs"], stats[off]["balls"], False),
    ]


def bowler_conceded(runs: int, wicket: bool) -> int:
    """Runs on bowler's figures, U9 wicket -5 penalty is not 'conceded'."""
    if wicket and runs == WKT_PENALTY:
        return 0
    return runs


@dataclass
class BallSpec:
    symbol: str
    batter: str
    description: str = ""
    runs: int | None = None
    bat_runs: int | None = None
    wicket: bool = False
    fielder: str = ""
    extras_type: str = ""


def d(
    symbol: str,
    batter: str,
    *,
    description: str = "",
    runs: int | None = None,
    bat_runs: int | None = None,
    wicket: bool = False,
    fielder: str = "",
    extras_type: str = "",
) -> dict:
    return {
        "symbol": symbol,
        "batter": batter,
        "description": description,
        "runs": runs,
        "bat_runs": bat_runs,
        "wicket": wicket,
        "fielder": fielder,
        "extras_type": extras_type,
    }


def expand_delivery(symbol: str, batter: str, bowler: str) -> list[dict]:
    """Default runs from symbol (matches gen_bbb.expand_symbol)."""
    sym = symbol.strip()
    if sym in {".", "0"}:
        return [{"runs": 0, "bat_runs": 0, "legal": True, "wicket": False}]
    if sym.isdigit():
        n = int(sym)
        return [{"runs": n, "bat_runs": n, "legal": True, "wicket": False}]
    if sym in {"+", "WD"}:
        return [{"runs": 2, "bat_runs": 0, "legal": False, "wicket": False, "extras_type": "wide"}]
    m = re.fullmatch(r"\+(\d+)", sym)
    if m:
        extra = int(m.group(1))
        return [{"runs": 2 + extra, "bat_runs": 0, "legal": False, "wicket": False, "extras_type": "wide"}]
    if sym in {"O", "ON", "NB"}:
        return [{"runs": 2, "bat_runs": 0, "legal": False, "wicket": False, "extras_type": "noball"}]
    m = re.fullmatch(r"O(\d+)", sym)
    if m:
        bat = int(m.group(1))
        out = [{"runs": 2, "bat_runs": 0, "legal": False, "wicket": False, "extras_type": "noball"}]
        if bat:
            out.append({"runs": bat, "bat_runs": bat, "legal": True, "wicket": False})
        return out
    if sym == "O+1":
        return [
            {"runs": 2, "bat_runs": 0, "legal": False, "wicket": False, "extras_type": "noball"},
            {"runs": 1, "bat_runs": 1, "legal": True, "wicket": False},
        ]
    if sym in WKT_SYMBOLS:
        return [{"runs": WKT_PENALTY, "bat_runs": 0, "legal": True, "wicket": True}]
    if sym.startswith("∆"):
        m = re.match(r"∆\+?(\d+)", sym)
        n = int(m.group(1)) if m else 1
        return [{"runs": n, "bat_runs": 0, "legal": False, "wicket": False, "extras_type": "legbye"}]
    if sym == "0+4":
        return [
            {"runs": 2, "bat_runs": 0, "legal": False, "wicket": False, "extras_type": "wide"},
            {"runs": 4, "bat_runs": 4, "legal": True, "wicket": False},
        ]
    return [{"runs": 0, "bat_runs": 0, "legal": True, "wicket": False}]


def delivery_runs(item: dict, bowler: str) -> tuple[int, int, bool, bool, str, str]:
    """Return (runs, bat_runs, wicket, legal, extras_type, description)."""
    symbol = item["symbol"]
    batter = item["batter"]
    desc = item.get("description") or ""
    fielder = item.get("fielder") or ""

    if item.get("runs") is not None:
        runs = int(item["runs"])
        bat = item.get("bat_runs")
        bat_runs = int(bat) if bat is not None else (runs if symbol.isdigit() else 0)
        wicket = bool(item.get("wicket"))
        extras = item.get("extras_type") or ""
        if wicket and runs > WKT_PENALTY:
            runs = WKT_PENALTY
        if not desc:
            if symbol == "R" and fielder:
                desc = f"{batter} run out ({fielder})"
            elif symbol == "B":
                desc = f"{batter} b {bowler}"
            elif symbol == "C" and fielder:
                desc = f"{batter} c {fielder} b {bowler}"
            elif symbol == "C":
                desc = f"{batter} c & b {bowler}"
        legal = symbol not in {"+", "WD", "O", "ON", "NB"} and not symbol.startswith("+") and not symbol.startswith("∆") and symbol != "0+4" and symbol != "O+1"
        if symbol == "O+1":
            legal = True  # second component legal
        return runs, bat_runs, wicket, legal, extras, desc

    events = expand_delivery(symbol, batter, bowler)
    total = sum(e["runs"] for e in events)
    bat_runs = sum(e.get("bat_runs", 0) for e in events)
    wicket = any(e.get("wicket") for e in events)
    legal = any(e.get("legal") for e in events)
    extras = next((e.get("extras_type", "") for e in events if e.get("extras_type")), "")
    if not desc:
        if symbol == "R" and fielder:
            desc = f"{batter} run out ({fielder})"
        elif symbol == "B":
            desc = f"{batter} b {bowler}"
        elif symbol == "C" and fielder:
            desc = f"{batter} c {fielder} b {bowler}"
        elif symbol == "C":
            desc = f"{batter} c & b {bowler}"
        elif symbol == "4":
            desc = "FOUR"
        elif symbol == "6":
            desc = "SIX"
        elif symbol == "1":
            desc = "1 run"
        elif symbol == "2":
            desc = "2 runs"
        elif symbol == "5":
            desc = "5 runs"
        elif symbol in {".", "0"}:
            desc = "no run"
        elif symbol in {"+", "WD"}:
            desc = "Wide (+2)"
        elif symbol in {"O", "ON", "NB"}:
            desc = "No ball (+2)"
        elif symbol.startswith("∆"):
            n = int(re.match(r"∆\+?(\d+)", symbol).group(1)) if re.match(r"∆\+?(\d+)", symbol) else 1
            desc = f"{n} leg bye{'s' if n != 1 else ''}"
    return total, bat_runs, wicket, legal, extras, desc


def simulate_innings(inn: dict) -> dict:
    order = inn["batsmen"]
    stats = {n: {"runs": 0, "balls": 0, "fours": 0, "sixes": 0, "out": False, "dismissal": ""} for n in order}
    bowl = {name: {"runs": 0, "wickets": 0, "wides": 0, "noballs": 0, "dots": 0, "legal": 0} for name in set(o["bowler"] for o in inn["overs"])}
    fielding: dict[str, dict] = {}

    total = BASE
    wickets = 0
    striker = order[0]
    non_striker = order[1] if len(order) > 1 else order[0]
    next_idx = 2
    partnership_idx = 0
    partnership_start = BASE
    partnerships: list[dict] = []
    p_wkts = 0

    for over in inn["overs"]:
        onum = over["num"]
        bowler = over["bowler"]
        pair_idx = (onum - 1) // PAIR_OVERS
        if pair_idx != partnership_idx:
            if partnership_idx > 0 or onum > 1:
                partnerships.append(
                    {
                        "label": f"P{partnership_idx + 1}",
                        "b1": inn["batsmen"][partnership_idx * 2],
                        "b2": inn["batsmen"][partnership_idx * 2 + 1],
                        "net": total - partnership_start,
                        "wickets": p_wkts,
                    }
                )
            partnership_idx = pair_idx
            partnership_start = total
            p_wkts = 0
            i = pair_idx * 2
            striker = order[i]
            non_striker = order[i + 1] if i + 1 < len(order) else striker
            next_idx = max(next_idx, i + 2)
            # U9 pairs: designated pair members resume at each 4-over block
            for name in (striker, non_striker):
                if stats[name]["out"]:
                    stats[name]["out"] = False
                    stats[name]["dismissal"] = ""

        legal_in_over = 0
        legal_balls_seen: set[int] = set()
        for item in over["deliveries"]:
            facing = item.get("batter") or striker
            symbol = item["symbol"]
            ball_idx = item.get("ball_index")

            if symbol == "O+1":
                nb_runs = 2
                if item.get("runs") is not None and int(item["runs"]) == 3:
                    nb_runs = 1  # No ball (+1) shorthand
                total += nb_runs
                bowl[bowler]["runs"] += nb_runs
                bowl[bowler]["noballs"] += 1
                bat2 = int(item["bat_runs"]) if item.get("bat_runs") is not None else 1
                runs2, _, wkt2, legal2, ex2, desc2 = delivery_runs(
                    {**item, "symbol": "1", "runs": bat2, "bat_runs": bat2}, bowler
                )
                total += runs2
                if wkt2:
                    wickets += 1
                    p_wkts += 1
                    stats[facing]["out"] = True
                    stats[facing]["dismissal"] = desc2 or f"b {bowler} (Ov {onum})"
                    pair_limit = (pair_idx + 1) * 2
                    if next_idx < len(order) and next_idx < pair_limit:
                        if facing == striker:
                            striker = order[next_idx]
                        else:
                            non_striker = order[next_idx]
                        next_idx += 1
                else:
                    st = stats[facing]
                    st["runs"] += bat2
                    st["balls"] += 1
                    bowl[bowler]["runs"] += bowler_conceded(runs2, False)
                    bowl[bowler]["legal"] += 1
                    legal_in_over += 1
                    if bat2 % 2 == 1:
                        striker, non_striker = non_striker, striker
                continue

            if symbol == "0+4":
                total += 2
                bowl[bowler]["runs"] += 2
                bowl[bowler]["wides"] += 1
                total += 4
                bowl[bowler]["runs"] += 4
                bowl[bowler]["legal"] += 1
                legal_in_over += 1
                st = stats[facing]
                st["runs"] += 4
                st["balls"] += 1
                st["fours"] += 1
                continue

            runs, bat_runs, wkt, legal, extras, desc = delivery_runs(item, bowler)
            if item.get("runs") is not None:
                runs = int(item["runs"])
            if item.get("bat_runs") is not None:
                bat_runs = int(item["bat_runs"])
            if item.get("wicket"):
                wkt = True
                if runs > WKT_PENALTY:
                    runs = WKT_PENALTY
            if item.get("description"):
                desc = item["description"]
            if item.get("fielder"):
                fielder = item["fielder"]
            else:
                fielder = item.get("fielder", "")

            total += runs
            bowl[bowler]["runs"] += bowler_conceded(runs, wkt)

            if extras == "wide":
                bowl[bowler]["wides"] += 1
            elif extras == "noball":
                bowl[bowler]["noballs"] += 1

            if wkt:
                if stats[facing]["out"]:
                    if symbol in {"B", "C", "S", "L", "H"}:
                        bowl[bowler]["wickets"] += 1
                    continue
                wickets += 1
                p_wkts += 1
                stats[facing]["out"] = True
                if symbol == "R":
                    stats[facing]["dismissal"] = f"run out ({fielder}) (Ov {onum})" if fielder else f"run out (Ov {onum})"
                    if fielder:
                        fielding.setdefault(fielder, {"catches": 0, "run_outs": 0, "detail_parts": []})
                        fielding[fielder]["run_outs"] += 1
                        fielding[fielder]["detail_parts"].append(
                            f"run out ({fielder}), Ov {onum} ({facing})"
                        )
                elif symbol == "C":
                    stats[facing]["dismissal"] = f"c {fielder} b {bowler} (Ov {onum})" if fielder else f"c & b {bowler} (Ov {onum})"
                    bowl[bowler]["wickets"] += 1
                    if fielder:
                        fielding.setdefault(fielder, {"catches": 0, "run_outs": 0, "detail_parts": []})
                        fielding[fielder]["catches"] += 1
                        fielding[fielder]["detail_parts"].append(f"c {facing} b {bowler}, Ov {onum}")
                else:
                    stats[facing]["dismissal"] = f"b {bowler} (Ov {onum})"
                    bowl[bowler]["wickets"] += 1
                pair_limit = (pair_idx + 1) * 2
                if next_idx < len(order) and next_idx < pair_limit:
                    if facing == striker:
                        striker = order[next_idx]
                    else:
                        non_striker = order[next_idx]
                    next_idx += 1
            elif legal:
                st = stats[facing]
                st["balls"] += 1
                if ball_idx is None or ball_idx not in legal_balls_seen:
                    if ball_idx is not None:
                        legal_balls_seen.add(ball_idx)
                    bowl[bowler]["legal"] += 1
                    legal_in_over += 1
                if bat_runs == 0 and runs == 0:
                    bowl[bowler]["dots"] += 1
                if bat_runs:
                    st["runs"] += bat_runs
                    if bat_runs == 4:
                        st["fours"] += 1
                    elif bat_runs == 6:
                        st["sixes"] += 1
                if bat_runs % 2 == 1:
                    striker, non_striker = non_striker, striker
                elif facing == non_striker and bat_runs > 0:
                    striker, non_striker = non_striker, striker

        if legal_in_over >= 1:
            striker, non_striker = non_striker, striker

        target = int(over["total"])
        if total != target:
            total = target

    # final partnership
    pair_idx = (inn["overs"][-1]["num"] - 1) // PAIR_OVERS
    partnerships.append(
        {
            "label": f"P{pair_idx + 1}",
            "b1": inn["batsmen"][pair_idx * 2],
            "b2": inn["batsmen"][pair_idx * 2 + 1],
            "net": total - partnership_start,
            "wickets": p_wkts,
        }
    )

    batting_summary = []
    for name in order:
        s = stats[name]
        runs = s["runs"]
        wkts = 1 if s["out"] else 0
        net = runs - 5 * wkts
        batting_summary.append(
            {
                "name": name,
                "dismissal": s["dismissal"] if s["out"] else "not out",
                "runs": runs,
                "balls": s["balls"],
                "fours": s["fours"],
                "sixes": s["sixes"],
                "wkts": wkts,
                "net": net,
            }
        )

    bowler_order: list[str] = []
    for o in inn["overs"]:
        if o["bowler"] not in bowler_order:
            bowler_order.append(o["bowler"])
    bowling_summary = []
    for name in bowler_order:
        b = bowl[name]
        overs_count = sum(1 for o in inn["overs"] if o["bowler"] == name)
        bowling_summary.append(
            {
                "name": name,
                "overs": overs_count,
                "runs": b["runs"],
                "wickets": b["wickets"],
                "wides": b["wides"],
                "noballs": b["noballs"],
                "dots": b["dots"],
            }
        )

    field_list = []
    for name, f in fielding.items():
        field_list.append(
            {
                "fielder": name,
                "catches": f["catches"],
                "run_outs": f["run_outs"],
                "detail": " | ".join(f["detail_parts"]),
            }
        )

    return {
        "final_total": total,
        "wickets": wickets,
        "partnerships": partnerships,
        "batting_summary": batting_summary,
        "bowling_summary": bowling_summary,
        "fielding": field_list,
    }


def build_innings_1() -> dict:
    totals = [203, 201, 205, 217, 224, 223, 231, 236, 243, 240, 244, 236, 236, 253, 254, 263]
    over_runs = ["3", "-2", "4", "12", "7", "-1", "8", "5", "7", "-3", "4", "-8", "0", "17", "1", "9"]
    bowlers = [
        "Avyaan", "Viaan", "Ariyan", "Veer", "Qaim", "Kaiyan", "Shyam", "Drish",
        "Viaan", "Avyaan", "Ariyan", "Veer", "Qaim", "Kaiyan", "Shyam", "Drish",
    ]
    overs = []
    specs = [
        [  # ov 1
            d(".", "Dev"), d(".", "Dev"), d("1", "Dev"), d(".", "Zayden"), d(".", "Zayden"),
            d("O", "Zayden", extras_type="noball"),
        ],
        [  # ov 2
            d(".", "Dev"), d(".", "Dev"), d(".", "Dev"), d("2", "Dev"), d("R", "Zayden", fielder="Ariyan", wicket=True,
              description="Zayden run out (Ariyan), brilliant fielding"),
            d("1", "Dev"),
        ],
        [  # ov 3
            d("+", "Dev", extras_type="wide"), d("1", "Dev"), d(".", "Dev"), d(".", "Dev"), d("1", "Dev"), d(".", "Dev"),
        ],
        [  # ov 4
            d("1", "Dev"), d("4", "Dev"), d("1", "Dev"),
            d("4", "Dev", description="FOUR: overthrow Avyaan", bat_runs=4),
            d("1", "Dev", description="1 run, catch dropped Qaim"),
            d("1", "Dev"),
        ],
        [  # ov 5
            d("+", "Rafi", extras_type="wide"), d("4", "Rafi"), d(".", "Henry"), d("1", "Rafi"), d(".", "Henry"), d(".", "Rafi"),
        ],
        [  # ov 6
            d(".", "Henry"), d(".", "Rafi"), d(".", "Henry"), d("4", "Rafi"),
            d("B", "Rafi", wicket=True, description="Rafi b Kaiyan"),
            d(".", "Henry"),
        ],
        [  # ov 7
            d("1", "Henry"), d(".", "Rafi"), d("0+4", "Rafi"),
            d(".", "Henry"), d(".", "Rafi"), d("1", "Henry"),
        ],
        [  # ov 8
            d("+", "Henry", extras_type="wide"), d("+", "Rafi", extras_type="wide"),
            d(".", "Henry"), d(".", "Rafi"), d("1", "Henry"),
        ],
        [  # ov 9
            d(".", "Shrihan"), d("1", "Vivaan"), d("1", "Shrihan"),
            d("5", "Vivaan", runs=5, bat_runs=1, description="5 runs (incl 4 overthrow Qaim)"),
            d(".", "Shrihan"), d(".", "Vivaan"),
        ],
        [  # ov 10, Shrihan run out (Avyaan) 9.1; Vivaan continues
            d("R", "Shrihan", fielder="Avyaan", wicket=True, description="Shrihan run out (Avyaan)"),
            d(".", "Vivaan"), d(".", "Vivaan"), d(".", "Vivaan"),
            d(".", "Vivaan"), d("+", "Vivaan", extras_type="wide"),
        ],
        [  # ov 11
            d(".", "Shrihan"), d("+", "Shrihan", extras_type="wide"), d(".", "Shrihan"),
            d("1", "Shrihan"), d(".", "Shrihan"), d("1", "Shrihan"),
        ],
        [  # ov 12, Veer: . 1 1 . B B, Shrihan (11.5) then Vivaan (12.0) bowled
            d(".", "Shrihan"), d("1", "Shrihan"), d("1", "Vivaan"), d(".", "Shrihan"),
            d("B", "Shrihan", wicket=True, description="Shrihan b Veer"),
            d("B", "Vivaan", wicket=True, description="Vivaan b Veer"),
        ],
        [  # ov 13, Qaim: Ojas & Riyan bowled; Ojas four on next ball denies hat-trick
            d("4", "Riyan"),
            d("B", "Ojas", wicket=True, description="Ojas b Qaim"),
            d("B", "Riyan", wicket=True, description="Riyan b Qaim"),
            d("4", "Ojas", description="FOUR: hat-trick missed (Ojas)"),
            d("1", "Ojas", runs=1, bat_runs=1), d("1", "Ojas"),
        ],
        [  # ov 14
            d("1", "Ojas"), d("4", "Ojas"), d("4", "Ojas"), d(".", "Ojas"),
            d("4", "Ojas"), d("4", "Ojas"),
        ],
        [  # ov 15, Riyan on strike first 3 balls; Riyan b Shyam ball 3; Ojas last 3
            d(".", "Riyan"), d("O", "Riyan", extras_type="noball"), d("B", "Riyan", wicket=True, description="Riyan b Shyam"),
            d(".", "Ojas"),
            d("+", "Ojas", extras_type="wide"), d("O", "Ojas", extras_type="noball"),
        ],
        [  # ov 16
            d("O", "Ojas", extras_type="noball"), d(".", "Ojas"), d("1", "Ojas"), d(".", "Ojas"),
            d("5", "Ojas", runs=5, bat_runs=1, description="5 runs (incl 4 overthrow Shyam)"),
            d("1", "Ojas"),
        ],
    ]
    for i, (bowler, balls) in enumerate(zip(bowlers, specs), start=1):
        overs.append({"num": i, "bowler": bowler, "over_runs": over_runs[i - 1], "total": totals[i - 1], "deliveries": balls})
    return {
        "num": 1,
        "batting": "Pinner",
        "bowling": "Edgware CC",
        "batsmen": ["Dev", "Zayden", "Henry", "Rafi", "Shrihan", "Vivaan", "Ojas", "Riyan"],
        "overs": overs,
    }


def build_innings_2() -> dict:
    # Ov 1 cumulative corrected to 202-1 (sheet row still 211 from ov 2); ovs 2-16 unchanged.
    totals = [202, 211, 217, 225, 228, 232, 245, 251, 252, 257, 273, 281, 285, 296, 299, 308]
    over_runs = ["2", "0", "6", "8", "3", "4", "13", "6", "1", "5", "16", "8", "4", "11", "3", "9"]
    bowlers = [
        "Ojas", "Riyan", "Vivaan", "Shrihan", "Henry", "Rafi", "Zayden", "Dev",
        "Ojas", "Riyan", "Vivaan", "Shrihan", "Henry", "Rafi", "Zayden", "Dev",
    ]
    specs = [
        [  # ov 1, Veer bowled ball 2; Ariyan 2 runs; ends 202-1
            d("+", "Veer", extras_type="wide"),
            d("B", "Veer", wicket=True, description="Veer b Ojas"),
            d("1", "Ariyan"),
            d("+", "Ariyan", extras_type="wide"),
            d("1", "Ariyan"),
            d("1", "Veer"),
        ],
        [  # ov 2
            d("1", "Ariyan"), d("O+1", "Veer", description="No ball (+1)"),
            d("O", "Ariyan", extras_type="noball"),
            d("+", "Ariyan", extras_type="wide"), d("1", "Ariyan"), d(".", "Veer"),
        ],
        [  # ov 3
            d(".", "Ariyan"), d("+", "Veer", extras_type="wide"), d("1", "Ariyan"),
            d("+", "Veer", extras_type="wide"), d(".", "Veer"), d("1", "Veer"),
        ],
        [  # ov 4
            d("+", "Veer", extras_type="wide"), d("+", "Veer", extras_type="wide"),
            d("2", "Veer"), d(".", "Ariyan"), d("1", "Veer"), d("1", "Ariyan"),
        ],
        [  # ov 5
            d("+", "Kaiyan", extras_type="wide"), d(".", "Kaiyan"), d(".", "Kaiyan"),
            d(".", "Kaiyan"), d(".", "Kaiyan"), d("1", "Kaiyan"),
        ],
        [  # ov 6, Drish 1 on 6.1; rest Kaiyan (pair 2)
            d("1", "Drish"), d(".", "Kaiyan"),
            d("4", "Kaiyan"), d("+", "Kaiyan", extras_type="wide"), d(".", "Kaiyan"),
            d("O", "Kaiyan", extras_type="noball"),
        ],
        [  # ov 7, Drish 4 on 7.3 only; other runs Kaiyan; RO after four
            d("1", "Kaiyan"), d("+", "Kaiyan", extras_type="wide"), d("4", "Drish"),
            d("R", "Drish", fielder="Ojas", wicket=True, description="Drish run out (Ojas)"),
            d("4", "Kaiyan"), d(".", "Shyam"),
        ],
        [  # ov 8, Kaiyan all balls (user: Kaiyan/Drish pair after RO)
            d(".", "Kaiyan"), d(".", "Kaiyan"), d("4", "Kaiyan"), d("+", "Kaiyan", extras_type="wide"),
            d(".", "Kaiyan"), d(".", "Kaiyan"),
        ],
        [  # ov 9, Viaan only ball 1
            d("1", "Viaan"), d(".", "Shyam"), d(".", "Shyam"), d(".", "Shyam"), d(".", "Shyam"), d(".", "Shyam"),
        ],
        [  # ov 10, Shyam only ball 3
            d(".", "Viaan"), d("1", "Viaan"), d("1", "Shyam"), d(".", "Viaan"),
            d("+", "Viaan", extras_type="wide"), d("1", "Viaan"),
        ],
        [  # ov 11
            d("+", "Viaan", extras_type="wide"), d("4", "Viaan"), d("4", "Viaan"),
            d("+", "Viaan", extras_type="wide"), d("O", "Viaan", extras_type="noball"), d("+", "Viaan", extras_type="wide"),
        ],
        [  # ov 12
            d("+", "Shyam", extras_type="wide"), d(".", "Shyam"), d(".", "Shyam"),
            d("4", "Shyam"), d("+", "Shyam", extras_type="wide"), d(".", "Shyam"),
        ],
        [  # ov 13, Avyaan first 3 balls
            d(".", "Avyaan"), d(".", "Avyaan"), d("1", "Avyaan"), d("1", "Qaim"), d(".", "Qaim"), d("+", "Qaim", extras_type="wide"),
        ],
        [  # ov 14, Avyaan faces ball 6 only
            d("4", "Qaim"), d("O", "Qaim", extras_type="noball"), d(".", "Qaim"),
            d("4", "Qaim"), d("1", "Qaim"), d(".", "Avyaan"),
        ],
        [  # ov 15, Avyaan last 3 balls; Qaim caught ball 3
            d(".", "Avyaan"), d(".", "Qaim"),
            d("C", "Qaim", fielder="Ojas", wicket=True, description="Qaim c Ojas b Zayden"),
            d("6", "Avyaan"), d("+", "Avyaan", extras_type="wide"), d(".", "Avyaan"),
        ],
        [  # ov 16
            d("1", "Qaim"), d("∆+1", "Qaim", extras_type="legbye"), d("1", "Qaim"),
            d("∆+1", "Qaim", extras_type="legbye"), d("1", "Qaim"), d("∆+1", "Qaim", extras_type="legbye"),
        ],
    ]
    overs = []
    for i, (bowler, balls) in enumerate(zip(bowlers, specs), start=1):
        overs.append({"num": i, "bowler": bowler, "over_runs": over_runs[i - 1], "total": totals[i - 1], "deliveries": balls})
    return {
        "num": 2,
        "batting": "Edgware CC",
        "bowling": "Pinner",
        "batsmen": ["Ariyan", "Veer", "Drish", "Kaiyan", "Shyam", "Viaan", "Avyaan", "Qaim"],
        "overs": overs,
    }


def annotate_notation(inn: dict, max_over: int) -> None:
    for over in inn["overs"]:
        onum = over["num"]
        deliveries = over["deliveries"]
        max_ball = max((d.get("ball_index") or 0) for d in deliveries) if deliveries else 0
        for item in deliveries:
            item["over"] = onum
            ball_i = item.get("ball_index") or 1
            item["ball_in_over"] = ball_i
            if ball_i == max_ball:
                item["notation"] = f"{onum}.0"
            else:
                item["notation"] = f"{onum - 1}.{ball_i}"
            item["bowler"] = over["bowler"]
            if not item.get("description"):
                _, _, wkt, _, _, desc = delivery_runs(item, over["bowler"])
                item["description"] = desc
            if item.get("runs") is None:
                runs, bat, wkt, _, ex, _ = delivery_runs(item, over["bowler"])
                item["runs"] = runs
                if item.get("bat_runs") is None and bat:
                    item["bat_runs"] = bat
            item["wicket"] = bool(item.get("wicket"))


def main() -> None:
    inn1 = build_innings_1()
    inn2 = build_innings_2()
    annotate_notation(inn1, 16)
    annotate_notation(inn2, 16)

    s1 = simulate_innings(inn1)
    s2 = simulate_innings(inn2)

    chase_target = s1["final_total"] + 1
    margin = s2["final_total"] - s1["final_total"]
    inn2["target"] = chase_target

    inn1.update({k: s1[k] for k in ("partnerships", "batting_summary", "bowling_summary", "fielding", "final_total", "wickets")})
    inn2.update({k: s2[k] for k in ("partnerships", "batting_summary", "bowling_summary", "fielding", "final_total", "wickets")})

    data = {
        "match": {
            "label": "M6",
            "date": "14 June 2026",
            "venue": "Pinner",
            "home": "Pinner",
            "away": "Edgware CC",
            "format": "16 overs",
            "result": f"Edgware CC won by {margin} runs",
            "margin_runs": margin,
            "toss": {
                "winner": "Edgware",
                "decision": "bowl",
            },
        },
        "innings": [inn1, inn2],
    }

    OUT.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT}")
    print(f"Innings 1: {s1['final_total']}-{s1['wickets']}")
    print(f"Innings 2: {s2['final_total']}-{s2['wickets']} (target {chase_target})")
    print(f"Margin: ECC by {margin} runs")
    print("\nECC bowling (inn1):")
    for b in s1["bowling_summary"]:
        print(f"  {b['name']}: {b['overs']} ov, {b['runs']} r, {b['wickets']} w")
    for inn, label in [(s1, "Pinner bat"), (s2, "ECC bat")]:
        print(f"\n{label}:")
        for b in inn["batting_summary"]:
            print(f"  {b['name']}: {b['runs']} ({b['dismissal']}) net {b.get('net', b['runs'] - 5*b['wkts'])}")


if __name__ == "__main__":
    main()
