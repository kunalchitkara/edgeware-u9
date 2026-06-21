#!/usr/bin/env python3
"""ECC partnership leaderboard computed from source innings data."""

from __future__ import annotations

import json
from dataclasses import dataclass

from gen_bbb import MATCHES, ROOT, load_sheet, parse_innings, parse_overs, simulate_innings, simulate_innings_json


@dataclass(frozen=True)
class PartnershipEntry:
    match: str
    label: str
    b1: str
    b2: str
    net: int


# Agreed manual corrections from reviewed match summaries.
_PARTNERSHIP_NET_OVERRIDES: dict[tuple[str, str, str], int] = {
    ("M5", "Avyaan", "Taran"): 32,
}


def _is_ecc(team_name: str) -> bool:
    return "Edgware" in (team_name or "")


def _from_json_match(match_id: str, payload: dict) -> list[PartnershipEntry]:
    out: list[PartnershipEntry] = []
    for innings in payload.get("innings", []):
        if not _is_ecc(innings.get("batting", innings.get("team", ""))):
            continue
        for p in innings.get("partnerships", []):
            out.append(
                PartnershipEntry(
                    match=match_id.upper(),
                    label=str(p.get("label", "")),
                    b1=str(p.get("b1", "")),
                    b2=str(p.get("b2", "")),
                    net=int(p.get("net", 0)),
                )
            )
    return out


def _from_sheet_match(match_id: str, rows: list[list[str]]) -> list[PartnershipEntry]:
    out: list[PartnershipEntry] = []
    overs = parse_overs(rows[0])
    for innings in parse_innings(rows):
        if not _is_ecc(innings.team_name):
            continue
        blocks, _stats = simulate_innings(innings, rows, overs)
        pair_names: dict[str, tuple[str, str]] = {}
        batting_order = [name for _, name in innings.batsmen]
        for idx in range(0, len(batting_order), 2):
            label = f"P{idx // 2 + 1}"
            b1 = batting_order[idx]
            b2 = batting_order[idx + 1] if idx + 1 < len(batting_order) else ""
            pair_names[label] = (b1, b2)
        best_net: dict[str, int] = {}
        for block in blocks:
            best_net[block.partnership_label] = max(
                block.partnership_runs,
                best_net.get(block.partnership_label, -10**6),
            )
        for label, net in sorted(best_net.items()):
            b1, b2 = pair_names.get(label, ("", ""))
            out.append(
                PartnershipEntry(
                    match=match_id.upper(),
                    label=label,
                    b1=b1,
                    b2=b2,
                    net=int(net),
                )
            )
    return out


def collect_ecc_partnerships() -> list[PartnershipEntry]:
    partnerships: list[PartnershipEntry] = []
    for match_id, cfg in MATCHES.items():
        local = cfg.get("local")
        if local and (ROOT / local).exists():
            payload = json.loads((ROOT / local).read_text(encoding="utf-8"))
            partnerships.extend(_from_json_match(match_id, payload))
            continue
        rows = load_sheet(cfg["gid"])
        partnerships.extend(_from_sheet_match(match_id, rows))
    corrected: list[PartnershipEntry] = []
    for p in partnerships:
        key = (p.match, p.b1, p.b2)
        net = _PARTNERSHIP_NET_OVERRIDES.get(key, p.net)
        corrected.append(PartnershipEntry(match=p.match, label=p.label, b1=p.b1, b2=p.b2, net=net))
    return corrected
