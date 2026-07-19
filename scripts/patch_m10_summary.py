#!/usr/bin/env python3
"""Update M10 summary tables in index.html from data/m10.json."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
DATA = ROOT / "data" / "m10.json"

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
    lines = [
        BowlerLine(b["name"], b["runs"], b["wickets"])
        for b in inn["bowling_summary"]
    ]
    best = best_bowler(lines)
    assert best is not None
    raw = next(b for b in inn["bowling_summary"] if b["name"] == best.name)
    return best.name, best.runs, best.wickets


def build_m10_fun_facts(data: dict) -> str:
    inn1, inn2 = data["innings"]
    match = data["match"]
    margin = match["margin_runs"]
    target = inn2.get("target", inn1["final_total"] + 1)
    hm_total = inn2["final_total"]
    avyaan = next((b for b in inn1["batting_summary"] if b["name"] == "Avyaan"), None)
    ariyan = next((b for b in inn2["bowling_summary"] if b["name"] == "Ariyan"), None)
    ariyan_w = ariyan["wickets"] if ariyan else 4
    avyaan_r = avyaan["runs"] if avyaan else 23
    ariyan_r = ariyan["runs"] if ariyan else 4
    debut = match.get("debut", "Shay, Riyan")
    facts = [
        (
            "&#127775;",
            f"<strong>Double debut:</strong> <strong>{debut}</strong> made their ECC debuts at "
            "Raguvanshi Charitable Trust Cricket Ground.",
        ),
        (
            "&#127942;",
            f"<strong>Lion of the day:</strong> <strong>Ariyan</strong> took <strong>{ariyan_w} wickets</strong> "
            f"in the chase ({ariyan_r} runs conceded).",
        ),
        (
            "&#127919;",
            f"<strong>Club HS:</strong> <strong>Avyaan</strong> hit a new club high score with "
            f"<strong>{avyaan_r} runs</strong> in the ECC innings.",
        ),
        (
            "&#127937;",
            f"<strong>Solid win:</strong> Edgware posted <strong>{inn1['final_total']}/{inn1['wickets']}</strong> "
            f"and defended it by <strong>{margin} runs</strong>.",
        ),
        (
            "&#128680;",
            f"<strong>Chase fell short:</strong> H Manor finished on <strong>{hm_total}/{inn2['wickets']}</strong> "
            f"(target {target}), <strong>{margin} runs</strong> adrift in U9 pairs format.",
        ),
    ]
    body = "".join(
        f'          <div class="ffi"><div class="ffic">{icon}</div><div class="ffit">{text}</div></div>\n'
        for icon, text in facts
    )
    return f"""      <div class="ff">
        <div class="ffh">&#127941; Match 10 Fun Facts</div>
        <div class="ffg">
{body}        </div>
      </div>"""


def build_m10_summary_card(data: dict) -> str:
    inn1, inn2 = data["innings"]
    match = data["match"]
    margin = match["margin_runs"]
    target = inn2.get("target", inn1["final_total"] + 1)
    ecc_total = inn1["final_total"]
    hm_total = inn2["final_total"]
    ecc_top, ecc_top_r = top_bat(inn1)
    hm_top, hm_top_r = top_bat(inn2)
    ecc_bowl, ecc_bowl_r, ecc_bowl_w = top_bowl(inn2)
    avyaan = next((b for b in inn1["batting_summary"] if b["name"] == "Avyaan"), None)
    avyaan_r = avyaan["runs"] if avyaan else ecc_top_r
    ariyan_bowl = next((b for b in inn2["bowling_summary"] if b["name"] == "Ariyan"), None)
    ariyan_w = ariyan_bowl["wickets"] if ariyan_bowl else ecc_bowl_w
    ariyan_fig_r = ariyan_bowl["runs"] if ariyan_bowl else ecc_bowl_r
    debut = match.get("debut", "Shay, Riyan")
    ecc_wkts = inn1["wickets"]
    hm_wkts = inn2["wickets"]
    ecc_play = ecc_total - 200 + 5 * ecc_wkts
    hm_play = hm_total - 200 + 5 * hm_wkts

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

    hm_fielding = ""
    if inn1.get("fielding"):
        hm_fielding = (
            '        <div class="scsh"><img src="icons/fielding-role.png" style="width:18px;height:18px;vertical-align:middle;" alt="field"> Fielding Highlights (H Manor)</div>\n'
            + tbl(f_hdr, "\n".join(field_row(f) for f in inn1["fielding"]))
        )

    return f"""<div class="card">
      <div class="rbanner"><div class="rbm">&#127942; Edgware CC won by {margin} runs</div><div class="rbs">19 July 2026 &nbsp;&middot;&nbsp; H Manor vs Edgware &nbsp;&middot;&nbsp; Away &nbsp;&middot;&nbsp; Raguvanshi Charitable Trust Cricket Ground &nbsp;&middot;&nbsp; 20 Overs &nbsp;&middot;&nbsp; Target {target} &nbsp;&middot;&nbsp; H Manor won toss &amp; fielded first &nbsp;&middot;&nbsp; Debut: {debut}</div></div>
      <div class="msg">
        <div class="ms"><div class="mv">{ecc_total}</div><div class="ml">ECC Score</div></div>
        <div class="ms"><div class="mv">{hm_total}</div><div class="ml">H Manor Score</div></div>
        <div class="ms"><div class="mv">+{margin}</div><div class="ml">Won by {margin} runs</div></div>
        <div class="ms"><div class="mv">20</div><div class="ml">Overs</div></div>
        <div class="ms"><div class="mv">{ecc_top}</div><div class="ml">Top Bat ECC</div><div class="mn">{ecc_top_r} runs</div></div>
        <div class="ms"><div class="mv">{hm_top}</div><div class="ml">Top Bat H Manor</div><div class="mn">{hm_top_r} runs</div></div>
        <div class="ms"><div class="mv">{ecc_bowl}</div><div class="ml">Top Bowl ECC</div><div class="mn">{bowl_figure(ecc_bowl_r, ecc_bowl_w)}</div></div>
        <div class="ms" style="background:linear-gradient(135deg,#F4A261,#E67E22);color:#fff;"><div class="mv" style="color:#fff;">&#11088; Ariyan</div><div class="ml" style="color:rgba(255,255,255,.85);">Lion of the day</div><div class="mn" style="color:rgba(255,255,255,.8);">{ariyan_w} wkts · {bowl_figure(ariyan_fig_r, ariyan_w)}</div></div>
      </div>

      <div class="sci">
        <div class="scih"><span><img src="icons/batsman_light.png" style="width:18px;height:18px;vertical-align:middle;" alt="bat"> Edgware CC · Batting 1st Innings</span><span class="sct">{format_innings_score(ecc_total, ecc_wkts, 20)}</span></div>
        {tbl(bat_hdr, chr(10).join(bat_row(b) for b in inn1["batting_summary"]), f'<tr class="sctot"><td colspan="2"><strong>Total</strong></td><td class="c" colspan="5"><strong>{ecc_total} &nbsp;(20 Ov &nbsp;|&nbsp; Base 200 + {ecc_play} from play &nbsp;|&nbsp; {ecc_wkts} wkts)</strong></td></tr>')}
        <div class="scsh">&#129309; Partnerships</div>
        {tbl(p_hdr, chr(10).join(partnership_row(p) for p in inn1["partnerships"]))}
        {hm_fielding}
      </div>

      <div class="sci" style="margin-top:20px;">
        <div class="scih sct2"><span><img src="icons/ball_light.png" style="width:18px;height:18px;vertical-align:middle;" alt="ball"> H Manor · Bowling</span></div>
        {tbl(bowl_hdr, chr(10).join(bowl_row(b) for b in inn1["bowling_summary"]))}
      </div>

      <div class="sdiv"></div>

      <div class="sci">
        <div class="scih"><span><img src="icons/batsman_light.png" style="width:18px;height:18px;vertical-align:middle;" alt="bat"> H Manor · Batting 2nd Innings</span><span class="sct">{format_innings_score(hm_total, hm_wkts, 20)}</span></div>
        {tbl(bat_hdr, chr(10).join(bat_row(b) for b in inn2["batting_summary"]), f'<tr class="sctot"><td colspan="2"><strong>Total</strong></td><td class="c" colspan="5"><strong>{hm_total} &nbsp;(20 Ov &nbsp;|&nbsp; Base 200 + {hm_play} from play &nbsp;|&nbsp; {hm_wkts} wkts &nbsp;|&nbsp; Target {target})</strong></td></tr>')}
        <div class="scsh">&#129309; Partnerships</div>
        {tbl(p_hdr, chr(10).join(partnership_row(p) for p in inn2["partnerships"]))}
      </div>

      <div class="sci" style="margin-top:20px;">
        <div class="scih"><span><img src="icons/ball_light.png" style="width:18px;height:18px;vertical-align:middle;" alt="ball"> Edgware CC · Bowling</span></div>
        {tbl(bowl_hdr, chr(10).join(bowl_row(b) for b in inn2["bowling_summary"]))}
      </div>

{build_m10_fun_facts(data)}
      <div style="text-align:center;margin-top:16px;"><a class="sl" href="#mx/m10/bbb">Open Commentary</a></div>
    </div>"""


def inject_m10_match(html: str, data: dict) -> str:
    match = data["match"]
    margin = match["margin_runs"]
    inn1, inn2 = data["innings"]
    ecc_total = inn1["final_total"]
    hm_total = inn2["final_total"]

    if 'id="match-m10"' not in html:
        bbb = (ROOT / "bbb" / "m10.html").read_text(encoding="utf-8") if (ROOT / "bbb" / "m10.html").exists() else ""
        block = (
            "\n  <!-- M10 -->\n"
            '  <div id="match-m10" class="md2">\n'
            '  <div class="mmt">\n'
            '    <button type="button" class="mmtb active" onclick="showMatchView(\'m10\',\'summary\',this)">Summary</button>\n'
            '    <button type="button" class="mmtb" onclick="showMatchView(\'m10\',\'bbb\',this)">Commentary</button>\n'
            "  </div>\n"
            '  <div id="match-m10-summary" class="mmview active">\n'
            + build_m10_summary_card(data)
            + "\n  </div>\n"
            '  <div id="match-m10-bbb" class="mmview">\n'
            + bbb
            + "\n  </div>\n"
            "</div>\n"
        )
        anchor = (
            '      <div style="text-align:center;"><a class="sl" href="#mx/m9">Walkover: no scorecard</a></div>\n'
            "    </div>\n"
            "  </div>\n\n\n<!-- PLAYERS -->"
        )
        if anchor not in html:
            raise SystemExit("Could not find insertion point for M10 match block (after match-m9)")
        html = html.replace(anchor, anchor.replace("\n\n<!-- PLAYERS -->", f"\n{block}\n<!-- PLAYERS -->"), 1)

        if "M10 · 19 Jul" not in html:
            html = html.replace(
                '<button class="mtb" onclick="showMatch(\'m9\',this)">Hayes · 12 Jul</button>\n  </div>',
                '<button class="mtb" onclick="showMatch(\'m9\',this)">Hayes · 12 Jul</button>\n'
                '    <button class="mtb" onclick="showMatch(\'m10\',this)">H Manor · 19 Jul &#127942;</button>\n  </div>',
                1,
            )

    html = html.replace(
        '<tr><td>10</td><td>19 Jul</td><td>H Manor vs Edgware</td><td class="c"><span class="bdg away">Away</span></td><td class="c">-</td><td class="c">-</td><td class="c"><span class="bdg tbd">TBD</span></td><td class="c">-</td><td class="c"><a class="sl" href="#mx">&#128202; Scorecard</a></td></tr>',
        f'<tr><td>10</td><td>19 Jul</td><td>H Manor vs Edgware</td><td class="c"><span class="bdg away">Away</span></td><td class="c"><strong>{ecc_total}</strong></td><td class="c">{hm_total}</td><td class="c"><span class="bdg win">WIN</span></td><td class="c">Won by {margin} runs</td><td class="c"><a class="sl" href="#mx/m10">&#128202; Scorecard</a></td></tr>',
        1,
    )
    html = html.replace(
        '<tr><td>10</td><td>19 Jul</td><td>H Manor vs Edgware</td><td class="c"><span class="bdg away">Away</span></td><td>Headstone Manor</td><td class="c"><span class="bdg tbd">TBD</span></td><td class="c"><a class="sl" href="#mx">&#128202;</a></td></tr>',
        f'<tr><td>10</td><td>19 Jul</td><td>H Manor vs Edgware</td><td class="c"><span class="bdg away">Away</span></td><td>Raguvanshi Charitable Trust Cricket Ground</td><td class="c"><span class="bdg win">WIN +{margin} runs</span></td><td class="c"><a class="sl" href="#mx/m10">&#128202;</a></td></tr>',
        1,
    )

    html = html.replace(
        "const MATCHES_WITH_BBB=['m2','m4','m5','m6','m7','m8'];",
        "const MATCHES_WITH_BBB=['m2','m4','m5','m6','m7','m8','m10'];",
    )
    return html


def main() -> None:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    html = INDEX.read_text(encoding="utf-8")
    html = inject_m10_match(html, data)

    card = build_m10_summary_card(data)
    if 'id="match-m10-summary"' in html:
        html, n = re.subn(
            r'(<div id="match-m10-summary" class="mmview active">\s*)<div class="card">.*?</div>(\s*</div>\s*<div id="match-m10-bbb")',
            rf"\1{card}\2",
            html,
            count=1,
            flags=re.DOTALL,
        )
        if n != 1:
            raise SystemExit("M10 summary block not found")

    if (ROOT / "bbb" / "m10.html").exists():
        bbb = (ROOT / "bbb" / "m10.html").read_text(encoding="utf-8")
        html, n = re.subn(
            r'(<div id="match-m10-bbb" class="mmview">\s*).*?(\s*</div>\s*</div>\s*\n\n<!-- PLAYERS -->)',
            rf"\1{bbb}\2",
            html,
            count=1,
            flags=re.DOTALL,
        )

    INDEX.write_text(html, encoding="utf-8")
    print(f"Updated M10 summary in {INDEX}")

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
    print("Repaired tab boundaries after M10 injection")

    from patch_strike_rate import main as patch_strike_rate_main

    patch_strike_rate_main()


if __name__ == "__main__":
    main()
