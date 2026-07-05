#!/usr/bin/env python3
"""Build data/m8.json from data/m8_draft_bbb.txt (U9 pairs, 20 overs)."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRAFT = ROOT / "data" / "m8_draft_bbb.txt"
OUT = ROOT / "data" / "m8.json"

sys.path.insert(0, str(ROOT / "scripts"))
from build_m6 import d, simulate_innings  # noqa: E402


def cricket_notation(onum: int, ball_idx: int, total_deliveries: int | None = None) -> str:
    """MJCA-style: over n balls are (n-1).1 … (n-1).5, n.0; last-over extras extend (n-1).6+."""
    if total_deliveries is not None and total_deliveries > 6:
        if ball_idx == total_deliveries:
            return f"{onum}.0"
        return f"{onum - 1}.{ball_idx}"
    if ball_idx == 6:
        return f"{onum}.0"
    return f"{onum - 1}.{ball_idx}"


def ball_index_from_label(onum: int, label: str) -> int:
    m = re.match(r"(\d+)\.(\d+)", label.strip())
    if not m:
        return 1
    over_part, ball_part = int(m.group(1)), int(m.group(2))
    # Correct MJCA notation
    if ball_part == 0 and over_part == onum:
        return 6
    if over_part == onum - 1 and ball_part >= 1:
        return ball_part
    # Legacy wrong notation (n.1 … n.5, (n+1).0)
    if ball_part == 0 and over_part == onum + 1:
        return 6
    if over_part == onum and 1 <= ball_part <= 5:
        return ball_part
    if over_part == onum + 1 and ball_part >= 1:
        return 6 + ball_part
    return ball_part


def annotate_cricket_notation(inn: dict) -> None:
    for over in inn["overs"]:
        onum = over["num"]
        total = len(over["deliveries"])
        for item in over["deliveries"]:
            ball_i = item.get("ball_index") or 1
            item["over"] = onum
            item["ball_in_over"] = ball_i if ball_i <= 6 else 6
            item["notation"] = cricket_notation(onum, ball_i, total)
            item["bowler"] = over["bowler"]


def parse_wicket(text: str, batter: str) -> dict:
    t = text.strip().strip("()")
    m = re.search(r"run\s+out\s*(?:\((\w+)\)|by\s+(\w+)|\s+(\w+)\s*$)", t, re.I)
    if m:
        fielder = m.group(1) or m.group(2) or m.group(3)
        return {
            "symbol": "R",
            "wicket": True,
            "fielder": fielder,
            "description": f"{batter} run out ({fielder})",
        }
    m = re.search(r"c\s+(\w+)\s+b\s+(\w+)", t, re.I)
    if m:
        return {
            "symbol": "C",
            "wicket": True,
            "fielder": m.group(1),
            "description": f"{batter} c {m.group(1)} b {m.group(2)}",
        }
    m = re.search(r"(\w+)\s+b\s+(\w+)", t, re.I)
    if m:
        return {"symbol": "B", "wicket": True, "description": f"{batter} b {m.group(2)}"}
    m = re.search(r"b\s+(\w+)", t, re.I)
    if m:
        return {"symbol": "B", "wicket": True, "description": f"{batter} b {m.group(1)}"}
    return {"symbol": "B", "wicket": True, "description": t}


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
    if s.upper().startswith("C"):
        inner = re.search(r"\((.+)\)", s)
        if inner:
            w = parse_wicket(inner.group(1), batter)
            return d("C", batter, wicket=True, fielder=w.get("fielder"), description=w.get("description"))
        return d("C", batter, wicket=True)
    if s.upper().startswith("W") or " b " in s or "run out" in s.lower() or s.startswith("("):
        # Nested parens in e.g. W (Emily run out (Kaiyan)), extract fielder directly.
        if "run out" in s.lower():
            rom = re.search(r"run\s+out\s*\((\w+)\)", s, re.I)
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


def parse_batter(raw: str) -> str:
    m = re.match(r"\((.+)\)", raw.strip())
    return m.group(1) if m else raw.strip()


def parse_over_block(lines: list[str], start: int) -> tuple[dict | None, int]:
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
        label = bm.group(1)
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


def parse_batsmen(section: str) -> list[str]:
    names: list[str] = []
    for line in section.splitlines():
        if "Pairs:" not in line and "&" not in line:
            continue
        for pair in re.findall(r"(\w+)&(\w+)", line):
            names.extend(pair)
    return names


def parse_innings_bbb(text: str, marker: str) -> dict:
    idx = text.find(marker)
    if idx == -1:
        raise ValueError(f"Missing section: {marker}")
    chunk = text[idx:]
    end = chunk.find("\n----\nINNINGS")
    if end == -1:
        end = chunk.find("\n--------------------------------------------------------------------------------\nINNINGS")
    section = chunk[:end] if end != -1 else chunk
    lines = section.splitlines()
    batsmen = parse_batsmen(section)
    overs: list[dict] = []
    i = 0
    while i < len(lines):
        if lines[i].startswith("Over "):
            ob, i = parse_over_block(lines, i)
            if ob:
                overs.append(ob)
        else:
            i += 1
    return {"batsmen": batsmen, "overs": overs}


def apply_m8_corrections(inn2: dict) -> None:
    o3 = next(o for o in inn2["overs"] if o["num"] == 3)
    b3 = next(dv for dv in o3["deliveries"] if dv.get("ball_index") == 3)
    b3["wicket"] = True
    b3["symbol"] = "B"
    b3["description"] = "George b Ariyan (pairs re-out)"
    b3["runs"] = -5
    b3["bat_runs"] = 0

    for onum in range(17, 21):
        over = next(o for o in inn2["overs"] if o["num"] == onum)
        for item in over["deliveries"]:
            if item.get("batter") == "Jacob" and item.get("wicket"):
                item["pairs_redismissal"] = True
            if item.get("batter") == "Miraya" and item.get("wicket") and onum == 17:
                item["fielder"] = "Ariyan"

    o3_george = next(dv for dv in o3["deliveries"] if dv.get("batter") == "George" and dv.get("ball_index") == 3)
    o3_george["pairs_redismissal"] = True


# Authoritative scorer corrections, summaries use these when they differ from simulation.
M8_BAT_INN1 = {
    "Ishaan": {"runs": 1, "wkts": 1, "net": -4, "dismissal": "c Bailey b Sia (Ov 8)"},
    "Viaan": {"runs": 6, "wkts": 0, "net": 6, "dismissal": "not out"},
    "Krish": {"runs": 5, "wkts": 0, "net": 5, "dismissal": "not out"},
}

M8_BAT_INN2 = {
    "Sia": {"runs": 4, "wkts": 0, "net": 4, "dismissal": "not out"},
    "Khiyan": {"runs": 24, "wkts": 0, "net": 24, "dismissal": "not out"},
    "Bailey": {"runs": 6, "wkts": 0, "net": 6, "dismissal": "not out"},
    "Emily": {
        "runs": 5,
        "wkts": 2,
        "net": -5,
        "dismissal": "run out (Kaiyan) (Ov 5); b Viaan (Ov 8)",
    },
    "Blake": {"runs": 7, "wkts": 1, "net": 2, "dismissal": "run out (Kaiyan) (Ov 13)"},
    "Louie": {"runs": 2, "wkts": 1, "net": -3, "dismissal": "c Krish b Veer (Ov 13)"},
    "George": {
        "runs": 8,
        "wkts": 2,
        "net": -2,
        "dismissal": "b Krish (Ov 2); b Ariyan (Ov 3)",
    },
    "Rosie": {"runs": 5, "wkts": 0, "net": 5, "dismissal": "not out"},
    "Jacob": {
        "runs": 0,
        "wkts": 4,
        "net": -20,
        "dismissal": "b Qaim (Ov 17); b Viaan (Ov 18); b Ishaan (Ov 19); b Taran (Ov 20)",
    },
}

M8_BOWL_INN1 = {
    "Bailey": {"runs": 15},
    "Blake": {"runs": 11},
    "Louie": {"runs": 23},
}

M8_BOWL_INN2 = {
    "Avyaan": {"runs": 8, "wickets": 0},
    "Qaim": {"runs": 12},
    "Kaiyan": {"runs": 9},
    "Veer": {"runs": 13, "wickets": 1},
    "Krish": {"runs": 14, "wickets": 1},
    "Ariyan": {"runs": 7, "wickets": 1},
    "Viaan": {"runs": 8},
}

M8_FIELD_INN2_EXTRA = [
    {"fielder": "Kaiyan", "catches": 0, "run_outs": 2, "detail_parts": ["run out (Kaiyan), Ov 5 (Emily)", "run out (Kaiyan), Ov 13 (Blake)"]},
]

# Innings 2, ECC fielding drops (over num, ball_index → appended to ball description).
M8_DROP_COMMENTARY = [
    (3, 2, "catch dropped: George (Avyaan)"),
    (6, 4, "catch dropped: Bailey (Drish)"),
    (12, 6, "catch dropped: Khiyan (Taran)"),
]


def apply_drop_commentary(inn: dict, drops: list[tuple[int, int, str]]) -> None:
    """Append catch-dropped notes to matching deliveries (over num + ball_index)."""
    drop_map = {(onum, ball_idx): note for onum, ball_idx, note in drops}
    for over in inn.get("overs", []):
        onum = over.get("num", 0)
        for item in over.get("deliveries", []):
            ball_idx = item.get("ball_index")
            note = drop_map.get((onum, ball_idx))
            if not note:
                continue
            desc = (item.get("description") or "").strip()
            item["description"] = f"{desc}, {note}" if desc else note


def apply_authoritative_summaries(inn: dict, bat_fixes: dict, bowl_fixes: dict | None = None, field_extra: list | None = None) -> None:
    """Patch batting/bowling summaries with scorer-authoritative totals."""
    for row in inn["batting_summary"]:
        fix = bat_fixes.get(row["name"])
        if not fix:
            continue
        row["runs"] = fix["runs"]
        row["wkts"] = fix.get("wkts", row.get("wkts", 0))
        row["net"] = fix.get("net", row["runs"] - 5 * row["wkts"])
        row["dismissal"] = fix.get("dismissal", row["dismissal"])

    if bowl_fixes:
        for row in inn["bowling_summary"]:
            fix = bowl_fixes.get(row["name"])
            if not fix:
                continue
            if "runs" in fix:
                row["runs"] = fix["runs"]
            if "wickets" in fix:
                row["wickets"] = fix["wickets"]

    if field_extra:
        by_name = {f["fielder"]: f for f in inn.get("fielding", [])}
        for extra in field_extra:
            name = extra["fielder"]
            if name in by_name:
                existing = by_name[name]
                existing["run_outs"] = max(int(existing.get("run_outs", 0)), int(extra["run_outs"]))
                parts = existing.get("detail", "").split(" | ") if existing.get("detail") else []
                for part in extra.get("detail_parts", []):
                    if part not in parts:
                        parts.append(part)
                existing["detail"] = " | ".join(parts)
            else:
                inn.setdefault("fielding", []).append(
                    {
                        "fielder": name,
                        "catches": extra.get("catches", 0),
                        "run_outs": extra["run_outs"],
                        "detail": " | ".join(extra.get("detail_parts", [])),
                    }
                )


def over_ball_to_notation(over: int, ball_in_over: int) -> str:
    """Convert 1-based ball index within an over to MJCA notation."""
    return cricket_notation(over, ball_in_over)


def relabel_draft_notation(text: str) -> str:
    """Relabel all BBB ball lines from legacy n.1 notation to MJCA (n-1).1 … n.0."""
    lines = text.splitlines()
    out: list[str] = []
    cur_over = 0
    pending: list[tuple[str, str, str]] = []

    def flush_over() -> None:
        nonlocal pending, cur_over
        if not cur_over or not pending:
            pending = []
            return
        total = len(pending)
        for idx, (indent, batter_part, sym_part) in enumerate(pending, 1):
            label = cricket_notation(cur_over, idx, total)
            out.append(f"{indent}{label} {batter_part}: {sym_part}")
        pending = []

    over_end = re.compile(
        r"^\s*(→|Over\s+\d+\s+·|={3,}|-{3,}|Last over:|Extras:|NOTE:|$|\|)"
    )

    for line in lines:
        m = re.match(r"Over\s+(\d+)\s+·", line)
        if m:
            flush_over()
            cur_over = int(m.group(1))
            out.append(line)
            continue
        bm = re.match(r"(\s+)(\d+\.\d+)\s*(.+?):\s*(.*)$", line)
        if bm and cur_over:
            pending.append((bm.group(1), bm.group(3), bm.group(4)))
            continue
        if pending and over_end.match(line):
            flush_over()
        out.append(line)
    flush_over()
    return "\n".join(out) + "\n"


def fix_draft_over_order(text: str) -> str:
    """Ensure ball lines precede the → net/total summary within each over block."""
    lines = text.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        if re.match(r"Over\s+\d+\s+·", lines[i]):
            header = lines[i]
            i += 1
            summary: str | None = None
            balls: list[str] = []
            tail: list[str] = []
            while i < len(lines):
                line = lines[i]
                if re.match(r"Over\s+\d+\s+·", line) or line.startswith("===") or line.startswith("---"):
                    break
                if line.strip().startswith("→"):
                    summary = line
                elif re.match(r"\s+\d+\.\d+\s", line):
                    balls.append(line)
                else:
                    tail.append(line)
                i += 1
            out.append(header)
            out.extend(balls)
            if summary:
                out.append(summary)
            out.extend(tail)
        else:
            out.append(lines[i])
            i += 1
    return "\n".join(out) + "\n"


def relabel_wicket_tables(text: str) -> str:
    """Fix wicket-summary ball refs to MJCA notation."""

    def wicket_notation(over: int, ball: int) -> str:
        # Table mixes over.ball index with legacy cricket labels, normalize both.
        legacy_cricket = {
            (20, 0): (19, 6),  # Jacob b Ishaan, ov 19 ball 6
            (20, 1): (20, 1),  # Jacob b Taran, ov 20 ball 1
            (13, 0): (13, 2),  # Blake RO on no-ball, ov 13 ball 2
        }
        if (over, ball) in legacy_cricket:
            over, ball = legacy_cricket[(over, ball)]
        return over_ball_to_notation(over, ball)

    def repl_row(m: re.Match[str]) -> str:
        num = m.group(1)
        over = int(m.group(2))
        ball = int(m.group(3))
        return f"| {num} | {wicket_notation(over, ball):>5} |"

    text = re.sub(
        r"\|\s*(\d+)\s*\|\s*(\d+)\.(\d+)\s*\|",
        repl_row,
        text,
    )
    text = text.replace(
        "Jacob b Ishaan (20.0 / ov 19 ball 6)",
        "Jacob b Ishaan (19.0 / ov 19 ball 6)",
    )
    text = text.replace("George b Ariyan (3.3)", "George b Ariyan (2.3)")
    text = text.replace("← 13.0; on no-ball", "← 12.2; on no-ball")
    text = text.replace("← 13.2", "← 12.3")
    return text


def main() -> None:
    draft = DRAFT.read_text(encoding="utf-8")
    ordered = fix_draft_over_order(draft)
    relabeled = relabel_draft_notation(ordered)
    if relabeled != draft:
        DRAFT.write_text(relabeled, encoding="utf-8")
        print(f"Relabeled ball notation in {DRAFT}")
    raw = relabeled

    inn1_raw = parse_innings_bbb(raw, "INNINGS 1 · Edgware CC batting")
    inn2_raw = parse_innings_bbb(raw, "INNINGS 2 · Harefield batting")

    inn1 = {
        "num": 1,
        "batting": "Edgware CC",
        "bowling": "Harefield",
        "batsmen": inn1_raw["batsmen"],
        "overs": inn1_raw["overs"],
    }
    inn2 = {
        "num": 2,
        "batting": "Harefield",
        "bowling": "Edgware CC",
        "batsmen": inn2_raw["batsmen"],
        "overs": inn2_raw["overs"],
    }

    apply_m8_corrections(inn2)
    annotate_cricket_notation(inn1)
    annotate_cricket_notation(inn2)
    apply_drop_commentary(inn2, M8_DROP_COMMENTARY)

    s1 = simulate_innings(inn1)
    s2 = simulate_innings(inn2)

    chase = 342
    margin = 96
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

    apply_authoritative_summaries(inn1, M8_BAT_INN1, M8_BOWL_INN1)
    apply_authoritative_summaries(inn2, M8_BAT_INN2, M8_BOWL_INN2, M8_FIELD_INN2_EXTRA)

    inn1["final_total"] = 341
    inn1["wickets"] = 2
    inn2["final_total"] = 245
    inn2["wickets"] = 11

    data = {
        "match": {
            "label": "M8",
            "date": "5 July 2026",
            "venue": "Harefield",
            "home": "Harefield",
            "away": "Edgware CC",
            "format": "20 overs",
            "result": f"Edgware CC won by {margin} runs",
            "margin_runs": margin,
            "toss": {"winner": "Edgware CC", "decision": "bat"},
            "debut": "Ishaan",
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
