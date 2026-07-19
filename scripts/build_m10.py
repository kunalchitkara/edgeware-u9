#!/usr/bin/env python3
"""Build data/m10.json from data/m10_draft_bbb.txt (U9 pairs, 20 overs)."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRAFT = ROOT / "data" / "m10_draft_bbb.txt"
OUT = ROOT / "data" / "m10.json"

sys.path.insert(0, str(ROOT / "scripts"))
from build_m6 import d, simulate_innings  # noqa: E402
from build_m8 import (  # noqa: E402
    annotate_cricket_notation,
    apply_authoritative_summaries,
    apply_drop_commentary,
    cricket_notation,
    fix_draft_over_order,
    parse_batter,
    parse_over_block,
    parse_wicket,
    relabel_draft_notation,
)


def parse_symbol(raw: str, batter: str, bowler: str) -> dict:
    s = raw.strip()
    if not s or s == ".":
        return d(".", batter)
    if s in {"+", "WD"}:
        return d("+", batter, extras_type="wide")
    if s == "O":
        return d("O", batter, extras_type="noball")
    if s == "O+1":
        return d("O+1", batter)
    if re.fullmatch(r"O\+2∆?", s):
        return d("O", batter, extras_type="noball")
    if s.startswith("∆"):
        n = int(re.search(r"(\d+)", s).group(1))
        return d(f"∆+{n}", batter, extras_type="legbye")
    if s.isdigit():
        return d(s, batter)
    if re.match(r"^R\b", s, re.I) or "run-out" in s.lower() or "run out" in s.lower():
        m = re.search(r"run[- ]?out\s*\(?(\w+)\)?", s, re.I)
        fielder = m.group(1) if m else ""
        desc = f"{batter} run out ({fielder})" if fielder else f"{batter} run out"
        return d("R", batter, wicket=True, fielder=fielder, description=desc)
    if re.match(r"^B\b", s, re.I):
        m = re.search(r"b\s+(\w+)", s, re.I)
        b = m.group(1) if m else bowler
        return d("B", batter, wicket=True, description=f"{batter} b {b}")
    if s.upper().startswith("C"):
        inner = re.search(r"\((.+)\)", s)
        if inner:
            w = parse_wicket(inner.group(1), batter)
            return d("C", batter, wicket=True, fielder=w.get("fielder"), description=w.get("description"))
        return d("C", batter, wicket=True)
    if s.upper().startswith("W") or " b " in s or s.startswith("("):
        if "run-out" in s.lower() or "run out" in s.lower():
            rom = re.search(r"run[- ]?out\s*\(?(\w+)\)?", s, re.I)
            if rom:
                fielder = rom.group(1)
                return d(
                    "R",
                    batter,
                    wicket=True,
                    fielder=fielder,
                    description=f"{batter} run out ({fielder})",
                )
        inner = re.search(r"\((.+)\)", s)
        text = inner.group(1) if inner else s.strip("()")
        w = parse_wicket(text, batter)
        sym = w.pop("symbol")
        return d(sym, batter, **w)
    return d(s, batter)


def parse_batsmen(section: str) -> list[str]:
    names: list[str] = []
    in_pairs = False
    for line in section.splitlines():
        if "Pairs:" in line:
            in_pairs = True
            line = line.split("Pairs:", 1)[1]
        elif in_pairs and (
            line.startswith("Over ")
            or line.startswith("Declared")
            or line.startswith("U9")
        ):
            break
        elif not in_pairs:
            continue
        for m in re.finditer(r"P\d+\s+(\w+)\s*&\s*(\w+)", line):
            names.extend([m.group(1), m.group(2)])
    return names


def parse_over_block_m10(lines: list[str], start: int) -> tuple[dict | None, int]:
    header = lines[start]
    m = re.match(r"Over\s+(\d+)\s+·\s+(\w+)", header)
    if not m:
        return None, start + 1
    onum, bowler = int(m.group(1)), m.group(2)
    deliveries: list[dict] = []
    total = 0
    i = start + 1
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if line.startswith("Over ") or line.startswith("---") or line.startswith("==="):
            break
        if line.startswith("→"):
            tm = re.search(r"total\s+(\d+)", line, re.I)
            if tm:
                total = int(tm.group(1))
            i += 1
            continue
        if line.startswith(("Last over:", "Extras:", "NOTE:")):
            i += 1
            continue
        bm = re.match(r"(\d+\.\d+)\s*(.+?):\s*(.+)$", line)
        if not bm:
            i += 1
            continue
        batter = parse_batter(bm.group(2))
        sym_raw = bm.group(3).strip()
        ball_idx = len(deliveries) + 1
        if sym_raw.lower().startswith("nb"):
            nm = re.search(r"\(\+(\d+)\)", sym_raw)
            extra = int(nm.group(1)) if nm else 2
            item = d("O", batter, extras_type="noball", runs=extra, bat_runs=0)
        else:
            item = parse_symbol(sym_raw, batter, bowler)
        item["ball_index"] = ball_idx
        deliveries.append(item)
        i += 1
    if not deliveries:
        return None, i
    return {"num": onum, "bowler": bowler, "over_runs": "", "total": total, "deliveries": deliveries}, i


def parse_innings_bbb(text: str, marker: str) -> dict:
    idx = text.find(marker)
    if idx == -1:
        raise ValueError(f"Missing section: {marker}")
    chunk = text[idx:]
    end_patterns = [
        r"\n={10,}\nINNINGS 2",
        r"\nCalculate batting",
        r"\n={10,}\nDROPS",
    ]
    for pat in end_patterns:
        m = re.search(pat, chunk)
        if m:
            chunk = chunk[: m.start()]
            break
    section = chunk
    lines = section.splitlines()
    batsmen = parse_batsmen(section)
    overs: list[dict] = []
    i = 0
    while i < len(lines):
        if lines[i].startswith("Over "):
            ob, i = parse_over_block_m10(lines, i)
            if ob:
                overs.append(ob)
        else:
            i += 1
    return {"batsmen": batsmen, "overs": overs}


def apply_m10_corrections(inn1: dict, inn2: dict) -> None:
    """Mark pairs re-outs for commentary and duplicate-dismissal batters."""
    for onum, ball_idx, batter in (
        (18, 2, "Khushmeet"),
        (20, 3, "Khushmeet"),
        (3, 4, "Adidev"),
        (19, 1, "Jiyan"),
        (19, 6, "Jiyan"),
        (20, 5, "Jiyan"),
    ):
        inn = inn1 if batter in {"Khushmeet"} and onum >= 17 else inn2
        if batter == "Khushmeet":
            inn = inn1
        over = next(o for o in inn["overs"] if o["num"] == onum)
        for item in over["deliveries"]:
            if item.get("ball_index") == ball_idx and item.get("batter") == batter:
                item["pairs_redismissal"] = True


M10_BAT_INN1 = {
    "Avyaan": {"runs": 23, "wkts": 1, "net": 18, "dismissal": "b Jash (Ov 19)"},
    "Qaim": {"runs": 11, "wkts": 1, "net": 6, "dismissal": "b Diyan (Ov 3)"},
    "Shyam": {"runs": 9, "wkts": 0, "net": 9, "dismissal": "not out"},
    "Drish": {"runs": 9, "wkts": 0, "net": 9, "dismissal": "not out"},
    "Shay": {"runs": 6, "wkts": 0, "net": 6, "dismissal": "not out"},
    "Ariyan": {"runs": 5, "wkts": 0, "net": 5, "dismissal": "not out"},
    "Riyan": {"runs": 4, "wkts": 1, "net": -1, "dismissal": "run out (Maya) (Ov 10)"},
    "Aanya": {"runs": 3, "wkts": 0, "net": 3, "dismissal": "not out"},
    "Khushmeet": {
        "runs": 2,
        "wkts": 2,
        "net": -8,
        "dismissal": "b Maya (Ov 18); b Adidev (Ov 20)",
    },
}

M10_BAT_INN2 = {
    "Diyan": {"runs": 7, "wkts": 1, "net": 2, "dismissal": "b Aanya (Ov 2)"},
    "Aaron": {"runs": 7, "wkts": 1, "net": 2, "dismissal": "b Ariyan (Ov 15)"},
    "Hiyan": {"runs": 6, "wkts": 0, "net": 6, "dismissal": "not out"},
    "Akshay": {"runs": 5, "wkts": 0, "net": 5, "dismissal": "not out"},
    "Jash": {"runs": 5, "wkts": 0, "net": 5, "dismissal": "not out"},
    "Khiyan": {"runs": 4, "wkts": 0, "net": 4, "dismissal": "not out"},
    "Sid": {"runs": 3, "wkts": 0, "net": 3, "dismissal": "not out"},
    "Maya": {"runs": 2, "wkts": 1, "net": -3, "dismissal": "b Drish (Ov 8)"},
    "Jiyan": {
        "runs": 1,
        "wkts": 3,
        "net": -14,
        "dismissal": "b Ariyan (Ov 19); b Ariyan (Ov 19); b Aanya (Ov 20)",
    },
    "Adidev": {
        "runs": 0,
        "wkts": 2,
        "net": -10,
        "dismissal": "b Aanya (Ov 2); b Ariyan (Ov 3)",
    },
}

M10_BOWL_INN1 = {
    "Adidev": {"runs": 8, "wickets": 1},
    "Diyan": {"runs": 5, "wickets": 1},
    "Jash": {"runs": 7, "wickets": 1},
    "Maya": {"runs": 11, "wickets": 1},
}

M10_BOWL_INN2 = {
    "Ariyan": {"runs": 4, "wickets": 4},
    "Aanya": {"runs": 6, "wickets": 3},
    "Drish": {"runs": 7, "wickets": 1},
    "Avyaan": {"runs": 5},
    "Khushmeet": {"runs": 14},
    "Qaim": {"runs": 7},
    "Riyan": {"runs": 12},
    "Shay": {"runs": 9},
    "Shyam": {"runs": 8},
}

M10_FIELD_INN1_EXTRA = [
    {
        "fielder": "Maya",
        "catches": 0,
        "run_outs": 1,
        "detail_parts": ["run out (Maya), Ov 10 (Riyan)"],
    },
]

M10_DROP_COMMENTARY = [
    (9, 4, "overthrow (+1)"),
    (12, 1, "overthrow (2 runs)"),
    (19, 4, "catch dropped (Aanya c&b missed)"),
]


def merge_duplicate_batting_rows(inn: dict) -> None:
    merged: dict[str, dict] = {}
    order: list[str] = []
    for row in inn["batting_summary"]:
        name = row["name"]
        if name not in merged:
            merged[name] = dict(row)
            order.append(name)
    inn["batting_summary"] = [merged[name] for name in order]


def main() -> None:
    draft = DRAFT.read_text(encoding="utf-8")
    ordered = fix_draft_over_order(draft)
    relabeled = relabel_draft_notation(ordered)
    if relabeled != draft:
        DRAFT.write_text(relabeled, encoding="utf-8")
        print(f"Relabeled ball notation in {DRAFT}")
    raw = relabeled

    inn1_raw = parse_innings_bbb(raw, "INNINGS 1 · Edgeware CC batting")
    inn2_raw = parse_innings_bbb(raw, "INNINGS 2 · H Manor batting")

    inn1 = {
        "num": 1,
        "batting": "Edgware CC",
        "bowling": "H Manor",
        "batsmen": inn1_raw["batsmen"],
        "overs": inn1_raw["overs"],
    }
    inn2 = {
        "num": 2,
        "batting": "H Manor",
        "bowling": "Edgware CC",
        "batsmen": inn2_raw["batsmen"],
        "overs": inn2_raw["overs"],
    }

    apply_m10_corrections(inn1, inn2)
    annotate_cricket_notation(inn1)
    annotate_cricket_notation(inn2)

    s1 = simulate_innings(inn1)
    s2 = simulate_innings(inn2)

    chase = 286
    margin = 51
    inn2["target"] = chase

    for inn, stats in ((inn1, s1), (inn2, s2)):
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

    merge_duplicate_batting_rows(inn1)
    merge_duplicate_batting_rows(inn2)

    apply_authoritative_summaries(inn1, M10_BAT_INN1, M10_BOWL_INN1, M10_FIELD_INN1_EXTRA)
    apply_authoritative_summaries(inn2, M10_BAT_INN2, M10_BOWL_INN2)
    apply_drop_commentary(inn2, M10_DROP_COMMENTARY)

    inn1["final_total"] = 285
    inn1["wickets"] = 5
    inn2["final_total"] = 234
    inn2["wickets"] = 8

    data = {
        "match": {
            "label": "M10",
            "date": "19 July 2026",
            "venue": "Raguvanshi Charitable Trust Cricket Ground",
            "home": "H Manor",
            "away": "Edgware CC",
            "format": "20 overs",
            "result": f"Edgware CC won by {margin} runs",
            "margin_runs": margin,
            "toss": {"winner": "H Manor", "decision": "field"},
            "debut": "Khushmeet, Shay, Riyan",
        },
        "innings": [inn1, inn2],
    }

    OUT.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT}")
    print(f"Innings 1: {len(inn1['overs'])} overs → {inn1['final_total']}-{inn1['wickets']}")
    print(f"Innings 2: {len(inn2['overs'])} overs → {inn2['final_total']}-{inn2['wickets']} (target {chase})")
    print(f"Margin: ECC by {margin} runs")


if __name__ == "__main__":
    main()
