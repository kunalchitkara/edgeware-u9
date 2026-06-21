#!/usr/bin/env python3
"""Update M7 summary tables in index.html from data/m7.json."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
DATA = ROOT / "data" / "m7.json"

sys.path.insert(0, str(ROOT / "scripts"))
from innings_score import format_innings_score  # noqa: E402
from match_awards import BatterLine, BowlerLine, best_batsman, best_bowler, bowl_figure  # noqa: E402
from strike_rate import format_sr  # noqa: E402


def eco(runs: int, overs: int) -> str:
    if overs == 0:
        return "0.0"
    v = runs / overs
    cls = ' eco-good' if v <= 4.0 else ""
    return f'<td class="c{cls}">{v:.1f}</td>'


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
    return (
        f'<tr><td class="scb">{b["name"]}</td><td class="c">{b["overs"]}</td><td class="c">{b["runs"]}</td>'
        f'<td class="c">{wcell}</td><td class="c">{b["wides"]}</td><td class="c">{b["noballs"]}</td>'
        f'{eco(b["runs"], b["overs"])}<td class="c">{b["dots"]}</td></tr>'
    )


def partnership_row(p: dict) -> str:
    net = p["net"]
    sign = "+" if net >= 0 else "&minus;"
    cls = "scnp" if net >= 0 else "scnn"
    ov_range = {"P1": "1&ndash;4", "P2": "5&ndash;8", "P3": "9&ndash;12", "P4": "13&ndash;16"}[p["label"]]
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


def _fun_fact(icon: str, text: str) -> str:
    return f'          <div class="ffi"><div class="ffic">{icon}</div><div class="ffit">{text}</div></div>\n'


def fielding_from_bbb(inn: dict) -> list[dict]:
    summary: dict[str, dict[str, object]] = {}
    for over in inn.get("overs", []):
        over_num = over.get("num")
        bowler = over.get("bowler", "")
        for delivery in over.get("deliveries", []):
            symbol = delivery.get("symbol")
            fielder = delivery.get("fielder")
            batter = delivery.get("batter", "")
            if symbol not in {"C", "R"} or not fielder:
                continue
            row = summary.setdefault(
                fielder,
                {"fielder": fielder, "catches": 0, "run_outs": 0, "detail_parts": []},
            )
            if symbol == "C":
                row["catches"] = int(row["catches"]) + 1
                row["detail_parts"].append(f"c {batter} b {bowler} — Ov {over_num}")
            else:
                row["run_outs"] = int(row["run_outs"]) + 1
                row["detail_parts"].append(f"run out ({fielder}) — Ov {over_num} ({batter})")

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


def build_m7_fun_facts(data: dict) -> str:
    inn1, inn2 = data["innings"]
    krish = next(b for b in inn2["bowling_summary"] if b["name"] == "Krish")
    avyaan_bowl = next(b for b in inn2["bowling_summary"] if b["name"] == "Avyaan")
    facts: list[tuple[str, str]] = [
        (
            "&#11088;",
            f"<strong>Season-best spell:</strong> Krish finished with <strong>{krish['wickets']} wickets</strong> "
            "to set the best bowling return of the season so far.",
        ),
        (
            "&#127919;",
            f"<strong>Two-over pressure:</strong> Avyaan struck twice in over 2 and Krish struck twice in over 8 — "
            f"a pair of key two-wicket overs that built scoreboard pressure.",
        ),
        (
            "&#9889;",
            "<strong>Big finish:</strong> Krish took <strong>4 wickets in over 15</strong>, "
            "including the <strong>first hat-trick of the season</strong>.",
        ),
        (
            "&#127939;",
            "<strong>Fielding confidence:</strong> Avyaan held <strong>two sharp catches</strong> "
            "(overs 6 and 8) at important moments.",
        ),
        (
            "&#127919;",
            "<strong>Calm close:</strong> Qaim bowled a <strong>maiden final over</strong> to finish the innings.",
        ),
        (
            "&#128680;",
            "<strong>Wickets mattered:</strong> Headstone Manor closed on <strong>192-13</strong>; "
            "preserving wickets proved decisive in this format.",
        ),
    ]

    body = "".join(_fun_fact(icon, text) for icon, text in facts)
    return f"""      <div class="ff">
        <div class="ffh">&#127941; Match 7 Fun Facts</div>
        <div class="ffg">
{body}        </div>
      </div>"""


def build_m7_summary_card(data: dict) -> str:
    inn1, inn2 = data["innings"]
    match = data["match"]
    margin = match["margin_runs"]
    target = inn2.get("target", inn1["final_total"] + 1)
    ecc_total = inn1["final_total"]
    hsm_total = inn2["final_total"]
    ecc_top, ecc_top_r = top_bat(inn1)
    hsm_top, hsm_top_r = top_bat(inn2)
    ecc_bowl, ecc_bowl_r, ecc_bowl_w = top_bowl(inn2)
    krish_bat = next(b for b in inn1["batting_summary"] if b["name"] == "Krish")
    ecc_wkts = inn1["wickets"]
    hsm_wkts = inn2["wickets"]
    ecc_play = ecc_total - 200 + 5 * ecc_wkts
    hsm_play = hsm_total - 200 + 5 * hsm_wkts

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

    fielding_hsm = ""
    if inn1.get("fielding"):
        fielding_hsm = (
            '        <div class="scsh"><img src="icons/fielding-role.png" style="width:18px;height:18px;vertical-align:middle;" alt="field"> Fielding Highlights (Headstone Manor)</div>\n'
            + tbl(f_hdr, "\n".join(field_row(f) for f in inn1["fielding"]))
        )
    ecc_fielding = fielding_from_bbb(inn2)
    fielding_ecc = ""
    if ecc_fielding:
        fielding_ecc = (
            '                <div class="scsh"><img src="icons/fielding-role.png" style="width:18px;height:18px;vertical-align:middle;" alt="field"> Fielding Highlights (ECC)</div>\n'
            + tbl(f_hdr, "\n".join(field_row(f) for f in ecc_fielding))
        )

    return f"""<div class="card">
      <div class="rbanner"><div class="rbm">&#127942; Edgware CC won by {margin} runs</div><div class="rbs">21 June 2026 &nbsp;&middot;&nbsp; Edgware vs Headstone Manor &nbsp;&middot;&nbsp; Home &nbsp;&middot;&nbsp; 16 Overs &nbsp;&middot;&nbsp; Target {target}</div></div>
      <div class="msg">
        <div class="ms"><div class="mv">{ecc_total}</div><div class="ml">ECC Score</div></div>
        <div class="ms"><div class="mv">{hsm_total}</div><div class="ml">H Manor Score</div></div>
        <div class="ms"><div class="mv">+{margin}</div><div class="ml">Won by {margin} runs</div></div>
        <div class="ms"><div class="mv">16</div><div class="ml">Overs</div></div>
        <div class="ms"><div class="mv">{ecc_top}</div><div class="ml">Top Bat ECC</div><div class="mn">{ecc_top_r} runs</div></div>
        <div class="ms"><div class="mv">{hsm_top}</div><div class="ml">Top Bat H Manor</div><div class="mn">{hsm_top_r} runs</div></div>
        <div class="ms"><div class="mv">{ecc_bowl}</div><div class="ml">Top Bowl ECC</div><div class="mn">{bowl_figure(ecc_bowl_r, ecc_bowl_w)}</div></div>
        <div class="ms" style="background:linear-gradient(135deg,#F4A261,#E67E22);color:#fff;"><div class="mv" style="color:#fff;">&#11088; Krish</div><div class="ml" style="color:rgba(255,255,255,.85);">Lion of the day</div><div class="mn" style="color:rgba(255,255,255,.8);">{krish_bat['runs']} runs &amp; {ecc_bowl_w} wkts</div></div>
      </div>

      <div class="sci">
        <div class="scih"><span><img src="icons/batsman_light.png" style="width:18px;height:18px;vertical-align:middle;" alt="bat"> Edgware CC &mdash; Batting 1st Innings</span><span class="sct">{format_innings_score(ecc_total, ecc_wkts, 16)}</span></div>
        {tbl(bat_hdr, chr(10).join(bat_row(b) for b in inn1["batting_summary"]), f'<tr class="sctot"><td colspan="2"><strong>Total</strong></td><td class="c" colspan="5"><strong>{ecc_total} &nbsp;(16 Ov &nbsp;|&nbsp; Base 200 + {ecc_play} from play &nbsp;|&nbsp; {ecc_wkts} wkts)</strong></td></tr>')}
        <div class="scsh">&#129309; Partnerships</div>
        {tbl(p_hdr, chr(10).join(partnership_row(p) for p in inn1["partnerships"]))}
        {fielding_hsm}
      </div>

      <div class="sci" style="margin-top:20px;">
        <div class="scih sct2"><span><img src="icons/ball_light.png" style="width:18px;height:18px;vertical-align:middle;" alt="ball"> Headstone Manor &mdash; Bowling</span></div>
        {tbl(bowl_hdr, chr(10).join(bowl_row(b) for b in inn1["bowling_summary"]))}
      </div>

      <div class="sdiv"></div>

      <div class="sci">
        <div class="scih"><span><img src="icons/batsman_light.png" style="width:18px;height:18px;vertical-align:middle;" alt="bat"> Headstone Manor &mdash; Batting 2nd Innings</span><span class="sct">{format_innings_score(hsm_total, hsm_wkts, 16)}</span></div>
        {tbl(bat_hdr, chr(10).join(bat_row(b) for b in inn2["batting_summary"]), f'<tr class="sctot"><td colspan="2"><strong>Total</strong></td><td class="c" colspan="5"><strong>{hsm_total} &nbsp;(16 Ov &nbsp;|&nbsp; Base 200 + {hsm_play} from play &nbsp;|&nbsp; {hsm_wkts} wkts &nbsp;|&nbsp; Target {target})</strong></td></tr>')}
        <div class="scsh">&#129309; Partnerships</div>
        {tbl(p_hdr, chr(10).join(partnership_row(p) for p in inn2["partnerships"]))}
        {fielding_ecc}
      </div>

      <div class="sci" style="margin-top:20px;">
        <div class="scih"><span><img src="icons/ball_light.png" style="width:18px;height:18px;vertical-align:middle;" alt="ball"> Edgware CC &mdash; Bowling</span></div>
        {tbl(bowl_hdr, chr(10).join(bowl_row(b) for b in inn2["bowling_summary"]))}
      </div>

{build_m7_fun_facts(data)}
      <div style="text-align:center;margin-top:16px;"><a class="sl" href="#mx/m7/bbb">Open Commentary scorecard</a></div>
    </div>"""


def inject_m7_match(html: str, data: dict) -> str:
    match = data["match"]
    margin = match["margin_runs"]
    inn1, inn2 = data["innings"]
    ecc_total = inn1["final_total"]
    hsm_total = inn2["final_total"]

    if 'id="match-m7"' not in html:
        bbb = (ROOT / "bbb" / "m7.html").read_text(encoding="utf-8") if (ROOT / "bbb" / "m7.html").exists() else ""
        block = (
            "\n  <!-- M7 -->\n"
            '  <div id="match-m7" class="md2">\n'
            '  <div class="mmt">\n'
            '    <button type="button" class="mmtb active" onclick="showMatchView(\'m7\',\'summary\',this)">Summary</button>\n'
            '    <button type="button" class="mmtb" onclick="showMatchView(\'m7\',\'bbb\',this)">Commentary</button>\n'
            "  </div>\n"
            '  <div id="match-m7-summary" class="mmview active">\n'
            + build_m7_summary_card(data)
            + "\n  </div>\n"
            '  <div id="match-m7-bbb" class="mmview">\n'
            + bbb
            + "\n  </div>\n"
            "</div>\n"
        )
        anchor = re.search(r"</div>\s*</div>\s*\n\n<!-- PLAYERS -->", html)
        if not anchor:
            raise SystemExit("Could not find insertion point for M7 match block")
        html = html[: anchor.start()] + block + html[anchor.start() :]

        if "M7 &mdash; 21 Jun" not in html:
            html = html.replace(
                '<button class="mtb" onclick="showMatch(\'m6\',this)">M6 &mdash; 14 Jun</button>\n  </div>',
                '<button class="mtb" onclick="showMatch(\'m6\',this)">M6 &mdash; 14 Jun</button>\n'
                '    <button class="mtb" onclick="showMatch(\'m7\',this)">M7 &mdash; 21 Jun &#127942;</button>\n  </div>',
                1,
            )

    html = html.replace(
        '<tr><td>7</td><td>21 Jun</td><td>Edgware vs H Manor</td><td class="c"><span class="bdg home">Home</span></td><td class="c">&mdash;</td><td class="c">&mdash;</td><td class="c"><span class="bdg tbd">TBD</span></td><td class="c">&mdash;</td><td class="c"><a class="sl" href="#mx">&#128202; Scorecard</a></td></tr>',
        f'<tr><td>7</td><td>21 Jun</td><td>Edgware vs H Manor</td><td class="c"><span class="bdg home">Home</span></td><td class="c"><strong>{ecc_total}</strong></td><td class="c">{hsm_total}</td><td class="c"><span class="bdg win">WIN</span></td><td class="c">Won by {margin} runs</td><td class="c"><a class="sl" href="#mx/m7">&#128202; Scorecard</a></td></tr>',
        1,
    )
    html = html.replace(
        '<tr><td>7</td><td>21 Jun</td><td>Edgware vs H Manor</td><td class="c"><span class="bdg home">Home</span></td><td>Canons High School</td><td class="c"><span class="bdg tbd">TBD</span></td><td class="c"><a class="sl" href="#mx">&#128202;</a></td></tr>',
        f'<tr><td>7</td><td>21 Jun</td><td>Edgware vs H Manor</td><td class="c"><span class="bdg home">Home</span></td><td>Canons High School</td><td class="c"><span class="bdg win">WIN +{margin} runs</span></td><td class="c"><a class="sl" href="#mx/m7">&#128202;</a></td></tr>',
        1,
    )
    return html


def main() -> None:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    html = INDEX.read_text(encoding="utf-8")
    html = inject_m7_match(html, data)

    card = build_m7_summary_card(data)
    html, n = re.subn(
        r'(<div id="match-m7-summary" class="mmview active">\s*)<div class="card">.*?</div>(\s*</div>\s*<div id="match-m7-bbb")',
        rf"\1{card}\2",
        html,
        count=1,
        flags=re.DOTALL,
    )
    if n != 1 and 'id="match-m7-summary"' in html:
        raise SystemExit("M7 summary block not found")

    bbb = (ROOT / "bbb" / "m7.html").read_text(encoding="utf-8")
    html, n = re.subn(
        r'(<div id="match-m7-bbb" class="mmview">\s*).*?(\s*</div>\s*</div>\s*\n\n<!-- PLAYERS -->)',
        rf"\1{bbb}\2",
        html,
        count=1,
        flags=re.DOTALL,
    )

    INDEX.write_text(html, encoding="utf-8")
    print(f"Updated M7 summary in {INDEX}")

    from patch_strike_rate import main as patch_strike_rate_main

    patch_strike_rate_main()


if __name__ == "__main__":
    main()
