#!/usr/bin/env python3
"""Update M8 summary tables in index.html from data/m8.json."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
DATA = ROOT / "data" / "m8.json"

sys.path.insert(0, str(ROOT / "scripts"))
from innings_score import format_innings_score  # noqa: E402
from match_awards import BatterLine, BowlerLine, best_batsman, best_bowler, bowl_figure  # noqa: E402
from strike_rate import format_sr  # noqa: E402
from bowling_display import eco_cell, gross_runs  # noqa: E402

OV_RANGES = {
    "P1": "1-4",
    "P2": "5-8",
    "P3": "9-12",
    "P4": "13-16",
    "P5": "17-20",
}


def net_cls(net: int) -> str:
    return "scnp" if net >= 0 else "scnn"


def bat_row(b: dict) -> str:
    net = b.get("net", b["runs"] - 5 * b.get("wkts", 0))
    sign = "+" if net >= 0 else "&minus;"
    sr = format_sr(b["runs"], b.get("balls", 0))
    return (
        f'<tr><td class="scb">{b["name"]}</td><td class="scd">{b["dismissal"]}</td>'
        f'<td class="c scr">{b["runs"]}</td><td class="c">{sr}</td><td class="c">{b["fours"]}</td><td class="c">{b["sixes"]}</td>'
        f'<td class="c {net_cls(net)}">{sign}{abs(net)}</td></tr>'
    )


def bowl_row(b: dict) -> str:
    w = b["wickets"]
    wcell = f"<strong>{w}</strong>" if w else "0"
    gr = gross_runs(b["runs"], w)
    return (
        f'<tr><td class="scb">{b["name"]}</td><td class="c">{b["overs"]}</td><td class="c">{gr}</td>'
        f'<td class="c">{wcell}</td><td class="c">{b["wides"]}</td><td class="c">{b["noballs"]}</td>'
        f'{eco_cell(b["runs"], w, b["overs"])}<td class="c">{b["dots"]}</td></tr>'
    )


def partnership_row(p: dict) -> str:
    net = p["net"]
    sign = "+" if net >= 0 else "&minus;"
    cls = "scnp" if net >= 0 else "scnn"
    ov_range = OV_RANGES[p["label"]]
    return (
        f'<tr><td>{p["label"]} (Ov {ov_range})</td><td class="scpb1">{p["b1"]}</td>'
        f'<td class="c {cls}"><strong>{sign}{abs(net)}</strong></td><td class="scpb2">{p["b2"]}</td></tr>'
    )


def field_row(f: dict) -> str:
    return (
        f'<tr class="scfi"><td class="scb">{f["fielder"]}</td>'
        f'<td class="c"><strong>{f["catches"]}</strong></td>'
        f'<td class="c"><strong>{f["run_outs"]}</strong></td>'
        f'<td>{f["detail"]}</td></tr>'
    )


def top_bat(inn: dict) -> tuple[str, int]:
    best = best_batsman([BatterLine(b["name"], b["runs"]) for b in inn["batting_summary"]])
    assert best is not None
    return best.name, best.runs


def top_bowl(inn: dict) -> tuple[str, int, int]:
    best = best_bowler([BowlerLine(b["name"], b["runs"], b["wickets"]) for b in inn["bowling_summary"]])
    assert best is not None
    return best.name, best.runs, best.wickets


def fielding_from_bbb(inn: dict) -> list[dict]:
    summary: dict[str, dict[str, object]] = {}
    for over in inn.get("overs", []):
        over_num = over.get("num")
        bowler = over.get("bowler", "")
        for delivery in over.get("deliveries", []):
            symbol = delivery.get("symbol")
            fielder = delivery.get("fielder")
            batter = delivery.get("batter", "")
            if symbol == "B" and "run out" in str(delivery.get("description", "")).lower():
                rom = re.search(r"run\s+out\s*\((\w+)\)", delivery.get("description", ""), re.I)
                if rom:
                    symbol = "R"
                    fielder = rom.group(1)
            if symbol not in {"C", "R"} or not fielder:
                continue
            row = summary.setdefault(
                fielder,
                {"fielder": fielder, "catches": 0, "run_outs": 0, "detail_parts": []},
            )
            if symbol == "C":
                row["catches"] = int(row["catches"]) + 1
                row["detail_parts"].append(f"c {batter} b {bowler}, Ov {over_num}")
            else:
                row["run_outs"] = int(row["run_outs"]) + 1
                row["detail_parts"].append(f"run out ({fielder}), Ov {over_num} ({batter})")
    rows: list[dict] = []
    for value in summary.values():
        rows.append(
            {
                "fielder": value["fielder"],
                "catches": int(value["catches"]),
                "run_outs": int(value["run_outs"]),
                "detail": " | ".join(value["detail_parts"]),
            }
        )
    rows.sort(key=lambda item: (-(item["catches"] + item["run_outs"]), item["fielder"]))
    return rows


def build_m8_fun_facts(data: dict) -> str:
    inn1, inn2 = data["innings"]
    hf_total = inn2["final_total"]
    target = inn2.get("target", inn1["final_total"] + 1)
    kaiyan = next((b for b in inn1["batting_summary"] if b["name"] == "Kaiyan"), None)
    p3 = next((p for p in inn1["partnerships"] if p["label"] == "P3"), None)
    p3_net = p3["net"] if p3 else 44
    facts = [
        (
            "&#11088;",
            "<strong>Season-high team score:</strong> Edgware posted <strong>341/2</strong>, "
            "the highest ECC total of the season so far.",
        ),
        (
            "&#127919;",
            "<strong>Biggest win:</strong> ECC won by <strong>96 runs</strong>, "
            "a new best margin for 2026.",
        ),
        (
            "&#127775;",
            "<strong>Debut wicket:</strong> <strong>Ishaan</strong> made his ECC debut and "
            "struck with <strong>Jacob b Ishaan</strong> at <strong>19.0</strong> (over 19).",
        ),
        (
            "&#129309;",
            f"<strong>Season-best partnership:</strong> Kaiyan &amp; Drish added "
            f"<strong>+{p3_net}</strong> in P3 (overs 9-12), the best ECC pair total of 2026.",
        ),
        (
            "&#128681;",
            "<strong>Fielding focus:</strong> <strong>3 catches dropped</strong> today, "
            "tidy that up before the Hayes match; bring your A game.",
        ),
        (
            "&#128680;",
            "<strong>Chase pressure:</strong> Harefield were bowled out for "
            f"<strong>{hf_total}/{inn2['wickets']}</strong> "
            f"(target {target}), <strong>{inn2['wickets']}</strong> counting wickets in U9 pairs format.",
        ),
    ]
    if kaiyan:
        facts.insert(
            3,
            (
                "&#127942;",
                f"<strong>Top bat:</strong> Kaiyan led with <strong>{kaiyan['runs']} runs</strong> "
                f"({kaiyan.get('fours', 0)} fours) in the ECC innings.",
            ),
        )
    body = "".join(
        f'          <div class="ffi"><div class="ffic">{icon}</div><div class="ffit">{text}</div></div>\n'
        for icon, text in facts
    )
    return f"""      <div class="ff">
        <div class="ffh">&#127941; Match 8 Fun Facts</div>
        <div class="ffg">
{body}        </div>
      </div>"""


def build_m8_summary_card(data: dict) -> str:
    inn1, inn2 = data["innings"]
    match = data["match"]
    margin = match["margin_runs"]
    target = inn2.get("target", inn1["final_total"] + 1)
    ecc_total = inn1["final_total"]
    hf_total = inn2["final_total"]
    ecc_top, ecc_top_r = top_bat(inn1)
    hf_top, hf_top_r = top_bat(inn2)
    ecc_bowl, ecc_bowl_r, ecc_bowl_w = top_bowl(inn2)
    ecc_wkts = inn1["wickets"]
    hf_wkts = inn2["wickets"]
    ecc_play = ecc_total - 200 + 5 * ecc_wkts
    hf_play = hf_total - 200 + 5 * hf_wkts

    def tbl(header: str, rows: str, footer: str = "") -> str:
        return (
            f'<div class="tscroll"><table class="sctbl">\n'
            f"          <thead>{header}</thead>\n"
            f"          <tbody>\n{rows}{footer}\n"
            f"          </tbody>\n        </table></div>"
        )

    bat_hdr = '<tr><th>Batter</th><th>Dismissal</th><th class="c">R</th><th class="c">SR</th><th class="c">4s</th><th class="c">6s</th><th class="c">Net</th></tr>'
    bowl_hdr = '<tr><th>Bowler</th><th class="c">O</th><th class="c">R</th><th class="c">W</th><th class="c">WD</th><th class="c">NB</th><th class="c">ECO</th><th class="c">Dots</th></tr>'
    p_hdr = '<tr><th>Partnership</th><th>Batter 1</th><th class="c">Net</th><th class="ra">Batter 2</th></tr>'
    f_hdr = '<tr><th>Fielder</th><th class="c">Catches</th><th class="c">Run Outs</th><th>Detail</th></tr>'

    hf_fielding = ""
    if inn1.get("fielding"):
        hf_fielding = (
            '        <div class="scsh"><img src="icons/fielding-role.png" style="width:18px;height:18px;vertical-align:middle;" alt="field"> Fielding Highlights (Harefield)</div>\n'
            + tbl(f_hdr, "\n".join(field_row(f) for f in inn1["fielding"]))
        )
    ecc_fielding = inn2.get("fielding") or fielding_from_bbb(inn2)
    if ecc_fielding:
        ecc_fielding = sorted(
            ecc_fielding,
            key=lambda item: (-(item.get("catches", 0) + item.get("run_outs", 0)), item["fielder"]),
        )
    fielding_ecc = ""
    if ecc_fielding:
        fielding_ecc = (
            '                <div class="scsh"><img src="icons/fielding-role.png" style="width:18px;height:18px;vertical-align:middle;" alt="field"> Fielding Highlights (ECC)</div>\n'
            + tbl(f_hdr, "\n".join(field_row(f) for f in ecc_fielding))
        )

    return f"""<div class="card">
      <div class="rbanner"><div class="rbm">&#127942; Edgware CC won by {margin} runs</div><div class="rbs">5 July 2026 &nbsp;&middot;&nbsp; Harefield vs Edgware &nbsp;&middot;&nbsp; Away &nbsp;&middot;&nbsp; 20 Overs &nbsp;&middot;&nbsp; Target {target} &nbsp;&middot;&nbsp; Debut: Ishaan</div></div>
      <div class="msg">
        <div class="ms"><div class="mv">{ecc_total}</div><div class="ml">ECC Score</div></div>
        <div class="ms"><div class="mv">{hf_total}</div><div class="ml">Harefield Score</div></div>
        <div class="ms"><div class="mv">+{margin}</div><div class="ml">Won by {margin} runs</div></div>
        <div class="ms"><div class="mv">20</div><div class="ml">Overs</div></div>
        <div class="ms"><div class="mv">{ecc_top}</div><div class="ml">Top Bat ECC</div><div class="mn">{ecc_top_r} runs</div></div>
        <div class="ms"><div class="mv">{hf_top}</div><div class="ml">Top Bat Harefield</div><div class="mn">{hf_top_r} runs</div></div>
        <div class="ms"><div class="mv">{ecc_bowl}</div><div class="ml">Top Bowl ECC</div><div class="mn">{bowl_figure(ecc_bowl_r, ecc_bowl_w)}</div></div>
        <div class="ms" style="background:linear-gradient(135deg,#F4A261,#E67E22);color:#fff;"><div class="mv" style="color:#fff;">&#11088; Kaiyan</div><div class="ml" style="color:rgba(255,255,255,.85);">Lion of the day</div><div class="mn" style="color:rgba(255,255,255,.8);">{ecc_top_r} runs &amp; big win</div></div>
      </div>

      <div class="sci">
        <div class="scih"><span><img src="icons/batsman_light.png" style="width:18px;height:18px;vertical-align:middle;" alt="bat"> Edgware CC · Batting 1st Innings</span><span class="sct">{format_innings_score(ecc_total, ecc_wkts, 20)}</span></div>
        {tbl(bat_hdr, chr(10).join(bat_row(b) for b in inn1["batting_summary"]), f'<tr class="sctot"><td colspan="2"><strong>Total</strong></td><td class="c" colspan="5"><strong>{ecc_total} &nbsp;(20 Ov &nbsp;|&nbsp; Base 200 + {ecc_play} from play &nbsp;|&nbsp; {ecc_wkts} wkts)</strong></td></tr>')}
        <div class="scsh">&#129309; Partnerships</div>
        {tbl(p_hdr, chr(10).join(partnership_row(p) for p in inn1["partnerships"]))}
        {hf_fielding}
      </div>

      <div class="sci" style="margin-top:20px;">
        <div class="scih sct2"><span><img src="icons/ball_light.png" style="width:18px;height:18px;vertical-align:middle;" alt="ball"> Harefield · Bowling</span></div>
        {tbl(bowl_hdr, chr(10).join(bowl_row(b) for b in inn1["bowling_summary"]))}
      </div>

      <div class="sdiv"></div>

      <div class="sci">
        <div class="scih"><span><img src="icons/batsman_light.png" style="width:18px;height:18px;vertical-align:middle;" alt="bat"> Harefield · Batting 2nd Innings</span><span class="sct">{format_innings_score(hf_total, hf_wkts, 20)}</span></div>
        {tbl(bat_hdr, chr(10).join(bat_row(b) for b in inn2["batting_summary"]), f'<tr class="sctot"><td colspan="2"><strong>Total</strong></td><td class="c" colspan="5"><strong>{hf_total} &nbsp;(20 Ov &nbsp;|&nbsp; Base 200 + {hf_play} from play &nbsp;|&nbsp; {hf_wkts} wkts &nbsp;|&nbsp; Target {target})</strong></td></tr>')}
        <div class="scsh">&#129309; Partnerships</div>
        {tbl(p_hdr, chr(10).join(partnership_row(p) for p in inn2["partnerships"]))}
        {fielding_ecc}
      </div>

      <div class="sci" style="margin-top:20px;">
        <div class="scih"><span><img src="icons/ball_light.png" style="width:18px;height:18px;vertical-align:middle;" alt="ball"> Edgware CC · Bowling</span></div>
        {tbl(bowl_hdr, chr(10).join(bowl_row(b) for b in inn2["bowling_summary"]))}
      </div>

{build_m8_fun_facts(data)}
      <div style="text-align:center;margin-top:16px;"><a class="sl" href="#mx/m8/bbb">Open Commentary</a></div>
    </div>"""


def inject_m8_match(html: str, data: dict) -> str:
    match = data["match"]
    margin = match["margin_runs"]
    inn1, inn2 = data["innings"]
    ecc_total = inn1["final_total"]
    hf_total = inn2["final_total"]

    if 'id="match-m8"' not in html:
        bbb = (ROOT / "bbb" / "m8.html").read_text(encoding="utf-8") if (ROOT / "bbb" / "m8.html").exists() else ""
        block = (
            "\n  <!-- M8 -->\n"
            '  <div id="match-m8" class="md2">\n'
            '  <div class="mmt">\n'
            '    <button type="button" class="mmtb active" onclick="showMatchView(\'m8\',\'summary\',this)">Summary</button>\n'
            '    <button type="button" class="mmtb" onclick="showMatchView(\'m8\',\'bbb\',this)">Commentary</button>\n'
            "  </div>\n"
            '  <div id="match-m8-summary" class="mmview active">\n'
            + build_m8_summary_card(data)
            + "\n  </div>\n"
            '  <div id="match-m8-bbb" class="mmview">\n'
            + bbb
            + "\n  </div>\n"
            "</div>\n"
        )
        anchor = re.search(r"</div>\s*</div>\s*\n\n(?:  <!-- M\d+ -->|  <div id=\"match-m)", html)
        if not anchor:
            raise SystemExit("Could not find insertion point for M8 match block")
        html = html[: anchor.start()] + block + html[anchor.start() :]

        if "M8 · 5 Jul" not in html:
            html = html.replace(
                '<button class="mtb" onclick="showMatch(\'m7\',this)">H Manor · 21 Jun &#127942;</button>\n  </div>',
                '<button class="mtb" onclick="showMatch(\'m7\',this)">H Manor · 21 Jun &#127942;</button>\n'
                '    <button class="mtb" onclick="showMatch(\'m8\',this)">Harefield · 5 Jul &#127942;</button>\n  </div>',
                1,
            )

    html = html.replace(
        '<tr><td>8</td><td>5 Jul</td><td>Harefield vs Edgware</td><td class="c"><span class="bdg away">Away</span></td><td class="c">-</td><td class="c">-</td><td class="c"><span class="bdg tbd">TBD</span></td><td class="c">-</td><td class="c"><a class="sl" href="#mx">&#128202; Scorecard</a></td></tr>',
        f'<tr><td>8</td><td>5 Jul</td><td>Harefield vs Edgware</td><td class="c"><span class="bdg away">Away</span></td><td class="c"><strong>{ecc_total}</strong></td><td class="c">{hf_total}</td><td class="c"><span class="bdg win">WIN</span></td><td class="c">Won by {margin} runs</td><td class="c"><a class="sl" href="#mx/m8">&#128202; Scorecard</a></td></tr>',
        1,
    )
    html = html.replace(
        '<tr><td>8</td><td>5 Jul</td><td>Harefield vs Edgware</td><td class="c"><span class="bdg away">Away</span></td><td>Harefield</td><td class="c"><span class="bdg tbd">TBD</span></td><td class="c"><a class="sl" href="#mx">&#128202;</a></td></tr>',
        f'<tr><td>8</td><td>5 Jul</td><td>Harefield vs Edgware</td><td class="c"><span class="bdg away">Away</span></td><td>Harefield</td><td class="c"><span class="bdg win">WIN +{margin} runs</span></td><td class="c"><a class="sl" href="#mx/m8">&#128202;</a></td></tr>',
        1,
    )

    html = html.replace(
        "const MATCHES_WITH_BBB=['m2','m4','m5','m6','m7'];",
        "const MATCHES_WITH_BBB=['m2','m4','m5','m6','m7','m8'];",
    )
    return html


def main() -> None:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    html = INDEX.read_text(encoding="utf-8")
    html = inject_m8_match(html, data)

    card = build_m8_summary_card(data)
    if 'id="match-m8-summary"' in html:
        html, n = re.subn(
            r'(<div id="match-m8-summary" class="mmview active">\s*)<div class="card">.*?</div>(\s*</div>\s*<div id="match-m8-bbb")',
            rf"\1{card}\2",
            html,
            count=1,
            flags=re.DOTALL,
        )
        if n != 1:
            raise SystemExit("M8 summary block not found")

    if (ROOT / "bbb" / "m8.html").exists():
        bbb = (ROOT / "bbb" / "m8.html").read_text(encoding="utf-8")
        html, n = re.subn(
            r'(<div id="match-m8-bbb" class="mmview">\s*).*?(\s*</div>\s*</div>\s*\n\n(?:  <!-- M\d+ -->|  <div id="match-m))',
            rf"\1{bbb}\2",
            html,
            count=1,
            flags=re.DOTALL,
        )

    INDEX.write_text(html, encoding="utf-8")
    print(f"Updated M8 summary in {INDEX}")

    from patch_index import (  # noqa: E402
        fix_nested_match_blocks,
        fix_tab_mx_boundary,
        fix_tab_ov_boundary,
    )

    html = INDEX.read_text(encoding="utf-8")
    html = fix_tab_ov_boundary(html)
    html = fix_nested_match_blocks(html)
    html = fix_tab_mx_boundary(html)
    INDEX.write_text(html, encoding="utf-8")
    print("Repaired tab boundaries after M8 injection")

    from patch_strike_rate import main as patch_strike_rate_main

    patch_strike_rate_main()


if __name__ == "__main__":
    main()
