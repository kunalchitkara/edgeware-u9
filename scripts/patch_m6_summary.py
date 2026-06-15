#!/usr/bin/env python3
"""Update M6 summary tables in index.html from data/m6.json."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
DATA = ROOT / "data" / "m6.json"

import sys

sys.path.insert(0, str(ROOT / "scripts"))
from innings_score import format_innings_score  # noqa: E402
from match_awards import best_batsman, best_bowler, bowl_figure  # noqa: E402
from match_awards import BatterLine, BowlerLine  # noqa: E402
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
    balls = b.get("balls", 0)
    sr = format_sr(b["runs"], balls)
    return (
        f'<tr><td class="scb">{b["name"]}</td><td class="scd">{b["dismissal"]}</td>'
        f'<td class="c scr">{b["runs"]}</td><td class="c">{sr}</td><td class="c">{b["fours"]}</td><td class="c">{b["sixes"]}</td>'
        f'<td class="c {net_cls(net)}">{sign}{abs(net)}</td></tr>'
    )


def bowl_row(b: dict) -> str:
    w = b["wickets"]
    wcell = f'<strong>{w}</strong>' if w else "0"
    return (
        f'<tr><td class="scb">{b["name"]}</td><td class="c">{b["overs"]}</td><td class="c">{b["runs"]}</td>'
        f'<td class="c">{wcell}</td><td class="c">{b["wides"]}</td><td class="c">{b["noballs"]}</td>'
        f'{eco(b["runs"], b["overs"])}<td class="c">{b["dots"]}</td></tr>'
    )


def partnership_row(p: dict) -> str:
    net = p["net"]
    sign = "+" if net >= 0 else "&minus;"
    cls = "scnp" if net >= 0 else "scnn"
    wkt = f' ({p["wickets"]} wkt)' if p.get("wickets") else ""
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
    batters = [BatterLine(b["name"], b["runs"]) for b in inn["batting_summary"]]
    best = best_batsman(batters)
    assert best is not None
    return best.name, best.runs


def top_bowl(inn: dict) -> tuple[str, int, int]:
    bowlers = [BowlerLine(b["name"], b["runs"], b["wickets"]) for b in inn["bowling_summary"]]
    best = best_bowler(bowlers)
    assert best is not None
    return best.name, best.runs, best.wickets


def _fun_fact(icon: str, text: str) -> str:
    return f'          <div class="ffi"><div class="ffic">{icon}</div><div class="ffit">{text}</div></div>\n'


def build_m6_fun_facts(data: dict) -> str:
    inn1, inn2 = data["innings"]
    _, ecc_top_r = top_bat(inn2)
    ecc_p3 = next(p for p in inn2["partnerships"] if p["label"] == "P3")
    avyaan = next(b for b in inn1["bowling_summary"] if b["name"] == "Avyaan")
    avyaan_eco = avyaan["runs"] / avyaan["overs"]
    kaiyan_wkts = next(b for b in inn1["bowling_summary"] if b["name"] == "Kaiyan")["wickets"]

    facts: list[tuple[str, str]] = [
        (
            "&#11088;",
            f"<strong>Lion of the day:</strong> Kaiyan starred all round — <strong>{ecc_top_r} runs</strong> "
            f"(3 fours) batting <em>and</em> <strong>{kaiyan_wkts} wicket</strong> with the ball.",
        ),
        (
            "&#127919;",
            "<strong>Great bowling today:</strong> Qaim and Veer each took <strong>2 bowled wickets in a single over</strong> — "
            "Veer removed Shrihan &amp; Vivaan in over 12; Qaim bowled Ojas &amp; Riyan in over 13.",
        ),
        (
            "&#9889;",
            "<strong>Hat-trick drama:</strong> Qaim took <strong>2 in 2</strong> at over 13 (Ojas &amp; Riyan) — "
            "Ojas&apos;s four on the next ball denied the hat-trick.",
        ),
        (
            "&#127939;",
            "<strong>Laser guided throws:</strong> Ariyan&apos;s direct hit removed Zayden in over 2; "
            "Avyaan ran out Shrihan in over 10 — two sharp moments in the field.",
        ),
        (
            "&#129309;",
            f"<strong>P3 partnership:</strong> Shyam &amp; Viaan added <strong>+{ecc_p3['net']}</strong> unbeaten for ECC (overs 9&ndash;12).",
        ),
        (
            "&#128311;",
            f"<strong>Most economical:</strong> Avyaan conceded just <strong>{avyaan['runs']} runs</strong> "
            f"from {avyaan['overs']} overs (eco <strong>{avyaan_eco:.1f}</strong>) — best of the match.",
        ),
        (
            "&#128680;",
            "<strong>Fielding day:</strong> Overthrows cost ECC <strong>14 runs</strong> — a costly lesson in backing up.",
        ),
        (
            "&#128681;",
            "<strong>Chance gone:</strong> <strong>1 catch dropped</strong> in the field today — one to sharpen up at training.",
        ),
    ]

    body = "".join(_fun_fact(icon, text) for icon, text in facts)
    return f"""      <div class="ff">
        <div class="ffh">&#127941; Match 6 Fun Facts</div>
        <div class="ffg">
{body}        </div>
      </div>"""


def replace_table(html: str, start_marker: str, end_marker: str, header: str, rows: str, footer: str = "") -> str:
    pattern = re.compile(
        re.escape(start_marker) + r".*?" + re.escape(end_marker),
        re.DOTALL,
    )
    body = start_marker + "\n          <thead>" + header + "</thead>\n          <tbody>\n" + rows + footer + "\n          </tbody>\n        </table>"
    return pattern.sub(body, html, count=1)


def innings_wickets(inn: dict) -> int:
    if "wickets" in inn:
        return int(inn["wickets"])
    return sum(1 for o in inn["overs"] for d in o["deliveries"] if d.get("wicket"))


def build_m6_summary_card(data: dict) -> str:
    inn1, inn2 = data["innings"]
    match = data["match"]
    margin = match["margin_runs"]
    target = inn2.get("target", inn1["overs"][-1]["total"] + 1)
    pinner_total = inn1["overs"][-1]["total"]
    ecc_total = inn2["overs"][-1]["total"]
    pinner_top, pinner_top_r = top_bat(inn1)
    ecc_top, ecc_top_r = top_bat(inn2)
    ecc_bowl, ecc_bowl_r, ecc_bowl_w = top_bowl(inn1)
    pinner_wkts = innings_wickets(inn1)
    ecc_wkts = innings_wickets(inn2)
    pinner_play = pinner_total - 200 + 5 * pinner_wkts
    ecc_play = ecc_total - 200 + 5 * ecc_wkts

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

    fielding_pinner = ""
    if inn2.get("fielding"):
        fielding_pinner = (
            '        <div class="scsh"><img src="icons/fielding-role.png" style="width:18px;height:18px;vertical-align:middle;" alt="field"> Fielding Highlights (Pinner)</div>\n'
            + tbl(f_hdr, "\n".join(field_row(f) for f in inn2["fielding"]))
        )
    fielding_ecc = ""
    if inn1.get("fielding"):
        fielding_ecc = (
            '                <div class="scsh"><img src="icons/fielding-role.png" style="width:18px;height:18px;vertical-align:middle;" alt="field"> Fielding Highlights (ECC)</div>\n'
            + tbl(f_hdr, "\n".join(field_row(f) for f in inn1["fielding"]))
        )

    return f"""<div class="card">
      <div class="rbanner"><div class="rbm">&#127942; Edgware CC won by {margin} runs</div><div class="rbs">14 June 2026 &nbsp;&middot;&nbsp; Pinner vs Edgware CC &nbsp;&middot;&nbsp; Pinner (Away) &nbsp;&middot;&nbsp; 16 Overs &nbsp;&middot;&nbsp; Target {target}</div></div>
      <div class="msg">
        <div class="ms"><div class="mv">{pinner_total}</div><div class="ml">Pinner Score</div></div>
        <div class="ms"><div class="mv">{ecc_total}</div><div class="ml">ECC Score</div></div>
        <div class="ms"><div class="mv">+{margin}</div><div class="ml">Won by {margin} runs</div></div>
        <div class="ms"><div class="mv">16</div><div class="ml">Overs</div></div>
        <div class="ms"><div class="mv">{ecc_top}</div><div class="ml">Top Bat ECC</div><div class="mn">{ecc_top_r} runs</div></div>
        <div class="ms"><div class="mv">{pinner_top}</div><div class="ml">Top Bat Pinner</div><div class="mn">{pinner_top_r} runs</div></div>
        <div class="ms"><div class="mv">{ecc_bowl}</div><div class="ml">Top Bowl ECC</div><div class="mn">{bowl_figure(ecc_bowl_r, ecc_bowl_w)}</div></div>
        <div class="ms" style="background:linear-gradient(135deg,#F4A261,#E67E22);color:#fff;"><div class="mv" style="color:#fff;">&#11088; {ecc_top}</div><div class="ml" style="color:rgba(255,255,255,.85);">Lion of the day</div><div class="mn" style="color:rgba(255,255,255,.8);">{ecc_top_r} runs</div></div>
      </div>

      <!-- Pinner Batting -->
      <div class="sci">
        <div class="scih sct2"><span><img src="icons/batsman_light.png" style="width:18px;height:18px;vertical-align:middle;" alt="bat"> Pinner &mdash; Batting 1st Innings</span><span class="sct">{format_innings_score(pinner_total, pinner_wkts, 16)}</span></div>
        {tbl(bat_hdr, chr(10).join(bat_row(b) for b in inn1["batting_summary"]), f'<tr class="sctot"><td colspan="2"><strong>Total</strong></td><td class="c" colspan="5"><strong>{pinner_total} &nbsp;(16 Ov &nbsp;|&nbsp; Base 200 + {pinner_play} from play &nbsp;|&nbsp; {pinner_wkts} wkts)</strong></td></tr>')}
        <div class="scsh">&#129309; Partnerships</div>
        {tbl(p_hdr, chr(10).join(partnership_row(p) for p in inn1["partnerships"]))}
        {fielding_ecc}
      </div>

      <!-- ECC Bowling -->
      <div class="sci" style="margin-top:20px;">
        <div class="scih"><span><img src="icons/ball_light.png" style="width:18px;height:18px;vertical-align:middle;" alt="ball"> Edgware CC &mdash; Bowling</span></div>
        {tbl(bowl_hdr, chr(10).join(bowl_row(b) for b in inn1["bowling_summary"]))}
      </div>

      <div class="sdiv"></div>

      <!-- ECC Batting -->
      <div class="sci">
        <div class="scih"><span><img src="icons/batsman_light.png" style="width:18px;height:18px;vertical-align:middle;" alt="bat"> Edgware CC &mdash; Batting 2nd Innings</span><span class="sct">{format_innings_score(ecc_total, ecc_wkts, 16)}</span></div>
        {tbl(bat_hdr, chr(10).join(bat_row(b) for b in inn2["batting_summary"]), f'<tr class="sctot"><td colspan="2"><strong>Total</strong></td><td class="c" colspan="5"><strong>{ecc_total} &nbsp;(16 Ov &nbsp;|&nbsp; Base 200 + {ecc_play} from play &nbsp;|&nbsp; {ecc_wkts} wkts &nbsp;|&nbsp; Target {target})</strong></td></tr>')}
        <div class="scsh">&#129309; Partnerships</div>
        {tbl(p_hdr, chr(10).join(partnership_row(p) for p in inn2["partnerships"]))}
        {fielding_pinner}
      </div>

      <!-- Pinner Bowling -->
      <div class="sci" style="margin-top:20px;">
        <div class="scih sct2"><span><img src="icons/ball_light.png" style="width:18px;height:18px;vertical-align:middle;" alt="ball"> Pinner &mdash; Bowling</span></div>
        {tbl(bowl_hdr, chr(10).join(bowl_row(b) for b in inn2["bowling_summary"]))}
      </div>

{build_m6_fun_facts(data)}
      <div style="text-align:center;margin-top:16px;"><a class="sl" href="#mx/m6/bbb">Open Commentary scorecard</a></div>
    </div>"""


def inject_m6_match(html: str, data: dict) -> str:
    """Insert full M6 match block if missing; update overview/fixtures rows."""
    match = data["match"]
    margin = match["margin_runs"]
    inn1, inn2 = data["innings"]
    pinner_total = inn1["overs"][-1]["total"]
    ecc_total = inn2["overs"][-1]["total"]

    if 'id="match-m6"' not in html:
        bbb = (ROOT / "bbb" / "m6.html").read_text(encoding="utf-8") if (ROOT / "bbb" / "m6.html").exists() else ""
        block = (
            "\n  <!-- M6 -->\n"
            '  <div id="match-m6" class="md2">\n'
            '  <div class="mmt">\n'
            '    <button type="button" class="mmtb active" onclick="showMatchView(\'m6\',\'summary\',this)">Summary</button>\n'
            '    <button type="button" class="mmtb" onclick="showMatchView(\'m6\',\'bbb\',this)">Commentary</button>\n'
            "  </div>\n"
            '  <div id="match-m6-summary" class="mmview active">\n'
            + build_m6_summary_card(data)
            + "\n  </div>\n"
            '  <div id="match-m6-bbb" class="mmview">\n'
            + bbb
            + "\n  </div>\n"
            "</div>\n"
        )
        anchor = re.search(r"</div>\s*</div>\s*\n\n<!-- PLAYERS -->", html)
        if not anchor:
            raise SystemExit("Could not find insertion point for M6 match block")
        html = html[: anchor.start()] + block + html[anchor.start() :]

        if 'M6 &mdash; 14 Jun' not in html:
            html = html.replace(
                '<button class="mtb" onclick="showMatch(\'m5\',this)">M5 &mdash; 7 Jun &#127942;</button>\n  </div>',
                '<button class="mtb" onclick="showMatch(\'m5\',this)">M5 &mdash; 7 Jun &#127942;</button>\n'
                '    <button class="mtb" onclick="showMatch(\'m6\',this)">M6 &mdash; 14 Jun</button>\n  </div>',
                1,
            )

    html = html.replace(
        '<tr><td>6</td><td>14 Jun</td><td>Pinner vs Edgware</td><td class="c"><span class="bdg away">Away</span></td><td class="c">&mdash;</td><td class="c">&mdash;</td><td class="c"><span class="bdg tbd">TBD</span></td><td class="c">&mdash;</td><td class="c"><a class="sl" href="#mx">&#128202; Scorecard</a></td></tr>',
        f'<tr><td>6</td><td>14 Jun</td><td>Pinner vs Edgware</td><td class="c"><span class="bdg away">Away</span></td><td class="c"><strong>{ecc_total}</strong></td><td class="c">{pinner_total}</td><td class="c"><span class="bdg win">WIN</span></td><td class="c">Won by {margin} runs</td><td class="c"><a class="sl" href="#mx/m6">&#128202; Scorecard</a></td></tr>',
        1,
    )
    html = html.replace(
        '<tr><td>6</td><td>14 Jun</td><td>Pinner vs Edgware</td><td class="c"><span class="bdg away">Away</span></td><td>Pinner</td><td class="c"><span class="bdg tbd">TBD</span></td><td class="c"><a class="sl" href="#mx">&#128202;</a></td></tr>',
        f'<tr><td>6</td><td>14 Jun</td><td>Pinner vs Edgware</td><td class="c"><span class="bdg away">Away</span></td><td>Pinner</td><td class="c"><span class="bdg win">WIN +{margin} runs</span></td><td class="c"><a class="sl" href="#mx/m6">&#128202;</a></td></tr>',
        1,
    )
    html = re.sub(
        r'(<tr><td>6</td><td>14 Jun</td><td>Pinner vs Edgware</td><td class="c"><span class="bdg away">Away</span></td><td class="c"><strong>)\d+(</strong></td><td class="c">)\d+(</td><td class="c"><span class="bdg win">WIN</span></td><td class="c">Won by )\d+( runs</td>)',
        rf"\g<1>{ecc_total}\g<2>{pinner_total}\g<3>{margin}\g<4>",
        html,
        count=1,
    )
    html = re.sub(
        r'(<tr><td>6</td><td>14 Jun</td><td>Pinner vs Edgware</td><td class="c"><span class="bdg away">Away</span></td><td>Pinner</td><td class="c"><span class="bdg win">WIN \+)\d+( runs</span></td>)',
        rf"\g<1>{margin} runs</span></td>",
        html,
        count=1,
    )
    return html


def main() -> None:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    html = INDEX.read_text(encoding="utf-8")
    html = inject_m6_match(html, data)

    card = build_m6_summary_card(data)
    html, n = re.subn(
        r'(<div id="match-m6-summary" class="mmview active">\s*)<div class="card">.*?</div>(\s*</div>\s*<div id="match-m6-bbb")',
        rf"\1{card}\2",
        html,
        count=1,
        flags=re.DOTALL,
    )
    if n != 1:
        raise SystemExit("M6 summary block not found")

    bbb = (ROOT / "bbb" / "m6.html").read_text(encoding="utf-8") if (ROOT / "bbb" / "m6.html").exists() else ""
    html, n = re.subn(
        r'(<div id="match-m6-bbb" class="mmview">\s*).*?(\s*</div>\s*</div>\s*</div>\s*\n\n<!-- PLAYERS -->)',
        rf"\1{bbb}\2",
        html,
        count=1,
        flags=re.DOTALL,
    )

    INDEX.write_text(html, encoding="utf-8")
    print(f"Updated M6 summary in {INDEX}")

    from patch_strike_rate import main as patch_strike_rate_main

    patch_strike_rate_main()


if __name__ == "__main__":
    main()
