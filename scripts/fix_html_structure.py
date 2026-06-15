#!/usr/bin/env python3
"""Repair tab-pl / pgrid / player-card HTML boundaries in index.html."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"

# Import boundary helpers from patch_index when run as module/script.
sys.path.insert(0, str(ROOT / "scripts"))
from patch_index import fix_tab_lb_boundary, fix_tab_mx_boundary, fix_tab_pl_boundary  # noqa: E402


MOST_WICKETS = """      <div class="lbc"><div class="lbh"><img src="icons/ball_light.png" style="width:18px;height:18px;vertical-align:middle;" alt="ball"> Most Wickets</div>
        <div class="lbr"><div class="lbrk r1">1</div><div class="lbn">Avyaan</div><div class="lbv">3</div></div>
        <div class="lbr"><div class="lbrk r1">1</div><div class="lbn">Qaim</div><div class="lbv">3</div></div>
        <div class="lbr"><div class="lbrk r1">1</div><div class="lbn">Krish</div><div class="lbv">3</div></div>
        <div class="lbr"><div class="lbrk rn">4</div><div class="lbn">Veer</div><div class="lbv">2</div></div>
        <div class="lbr"><div class="lbrk rn">4</div><div class="lbn">Kaiyan</div><div class="lbv">2</div></div></div>"""

MOST_RUN_OUTS = """      <div class="lbc"><div class="lbh"><img src="icons/fielder_light.png" style="width:18px;height:18px;vertical-align:middle;" alt="field"> Most Run Outs</div>
        <div class="lbr"><div class="lbrk r1">1</div><div class="lbn">Avyaan</div><div class="lbv">3</div></div>
        <div class="lbr"><div class="lbrk r2">2</div><div class="lbn">Qaim</div><div class="lbv">2</div></div>
        <div class="lbr"><div class="lbrk r3">3</div><div class="lbn">Ariyan</div><div class="lbv">1</div></div>
        <div class="lbr"><div class="lbrk r3">3</div><div class="lbn">Viaan</div><div class="lbv">1</div></div>
        <div class="lbr"><div class="lbrk r3">3</div><div class="lbn">Krish</div><div class="lbv">1</div></div></div>"""

BOWL_KRISH = (
    '<tr><td><strong>Krish</strong></td><td class="c">3</td><td class="c">6</td>'
    '<td class="c">22</td><td class="c"><strong>3</strong></td><td class="c">3</td>'
    '<td class="c">0</td><td class="c eco-good">3.7</td><td class="c"><strong>19</strong></td></tr>'
)

FIELD_ROWS = {
    "Avyaan": ('<tr><td><strong>Avyaan</strong></td><td class="c">4</td><td class="c">0</td><td class="c"><strong>3</strong></td></tr>', 3),
    "Viaan": ('<tr><td><strong>Viaan</strong></td><td class="c">3</td><td class="c">0</td><td class="c"><strong>1</strong></td></tr>', 1),
    "Qaim": ('<tr><td><strong>Qaim</strong></td><td class="c">4</td><td class="c">0</td><td class="c"><strong>2</strong></td></tr>', 2),
}


def patch_leaderboards(html: str) -> str:
  lb_start = html.find('id="tab-lb"')
  lb_end = html.find("<!-- RULES -->", lb_start)
  if lb_start == -1 or lb_end == -1:
    raise SystemExit("tab-lb or RULES marker missing")
  segment = html[lb_start:lb_end]

  wickets_old = (
    '      <div class="lbc"><div class="lbh"><img src="icons/ball_light.png" style="width:18px;height:18px;vertical-align:middle;" alt="ball"> Most Wickets</div>\n'
    '        <div class="lbr"><div class="lbrk r1">1</div><div class="lbn">Avyaan</div><div class="lbv">3</div></div>\n'
    '        <div class="lbr"><div class="lbrk r1">1</div><div class="lbn">Qaim</div><div class="lbv">3</div></div>\n'
    '        <div class="lbr"><div class="lbrk r3">3</div><div class="lbn">Krish</div><div class="lbv">2</div></div>\n'
    '        <div class="lbr"><div class="lbrk rn">4</div><div class="lbn">Aanya</div><div class="lbv">2</div></div>\n'
    '        <div class="lbr"><div class="lbrk rn">4</div><div class="lbn">Kaiyan</div><div class="lbv">2</div></div></div>'
  )
  if wickets_old in segment:
    segment = segment.replace(wickets_old, MOST_WICKETS.strip(), 1)
  elif MOST_WICKETS.strip() not in segment:
    raise SystemExit("Most Wickets block not found or already updated")

  runouts_old = (
    '      <div class="lbc"><div class="lbh"><img src="icons/fielder_light.png" style="width:18px;height:18px;vertical-align:middle;" alt="field"> Most Run Outs</div>\n'
    '        <div class="lbr"><div class="lbrk r1">1</div><div class="lbn">Avyaan</div><div class="lbv">4</div></div>\n'
    '        <div class="lbr"><div class="lbrk r2">2</div><div class="lbn">Viaan</div><div class="lbv">2</div></div>\n'
    '        <div class="lbr"><div class="lbrk r3">3</div><div class="lbn">Ariyan</div><div class="lbv">1</div></div>\n'
    '        <div class="lbr"><div class="lbrk rn">4</div><div class="lbn">Krish</div><div class="lbv">1</div></div>\n'
    '        <div class="lbr"><div class="lbrk rn">4</div><div class="lbn">Taran</div><div class="lbv">1</div></div></div>'
  )
  runouts_tie_old = (
    '      <div class="lbc"><div class="lbh"><img src="icons/fielder_light.png" style="width:18px;height:18px;vertical-align:middle;" alt="field"> Most Run Outs</div>\n'
    '        <div class="lbr"><div class="lbrk r1">1</div><div class="lbn">Avyaan</div><div class="lbv">3</div></div>\n'
    '        <div class="lbr"><div class="lbrk r2">2</div><div class="lbn">Qaim</div><div class="lbv">2</div></div>\n'
    '        <div class="lbr"><div class="lbrk r3">3</div><div class="lbn">Ariyan</div><div class="lbv">1</div></div>\n'
    '        <div class="lbr"><div class="lbrk rn">4</div><div class="lbn">Viaan</div><div class="lbv">1</div></div>\n'
    '        <div class="lbr"><div class="lbrk rn">4</div><div class="lbn">Krish</div><div class="lbv">1</div></div></div>'
  )
  if runouts_old in segment:
    segment = segment.replace(runouts_old, MOST_RUN_OUTS.strip(), 1)
  elif runouts_tie_old in segment:
    segment = segment.replace(runouts_tie_old, MOST_RUN_OUTS.strip(), 1)
  elif MOST_RUN_OUTS.strip() not in segment:
    raise SystemExit("Most Run Outs block not found or already updated")

  return html[:lb_start] + segment + html[lb_end:]


def patch_stats_tables(html: str) -> str:
    html = re.sub(
        r"<tr><td><strong>Krish</strong></td><td class=\"c\">3</td><td class=\"c\">6</td>"
        r"<td class=\"c\">22</td><td class=\"c\"><strong>2</strong></td>.*?</tr>",
        BOWL_KRISH,
        html,
        count=1,
    )
    for name, (row, _count) in FIELD_ROWS.items():
        html = re.sub(
            rf"<tr><td><strong>{re.escape(name)}</strong></td><td class=\"c\">\d+</td>"
            rf'<td class="c">\d+</td><td class="c"><strong>\d+</strong></td></tr>',
            row,
            html,
            count=1,
        )
    html = re.sub(
        r'(<div class="pc"><div class="pnb">Qaim <span>ECC</span></div>[\s\S]*?'
        r'<span class="psl">Run Outs</span><span class="psv">)\d+(</span>)',
        r"\g<1>2\2",
        html,
        count=1,
    )
    html = re.sub(
        r'(<div class="pc"><div class="pnb">Viaan <span>ECC</span></div>[\s\S]*?'
        r'<span class="psl">Run Outs</span><span class="psv">)\d+(</span>)',
        r"\g<1>1\2",
        html,
        count=1,
    )
    html = re.sub(
        r'(<div class="pc"><div class="pnb">Krish <span>ECC</span></div>[\s\S]*?'
        r'<span class="psl">Overs / Wkts</span><span class="psv">)6 / 2(</span>)',
        r"\g<1>6 / 3\2",
        html,
        count=1,
    )
    return html


def validate_structure(html: str) -> None:
    opens = len(re.findall(r"<div[\s>]", html))
    closes = len(re.findall(r"</div>", html))
    if opens != closes:
        raise SystemExit(f"Div imbalance after fix: {opens - closes}")

    pl = html.find('id="tab-pl"')
    lb = html.find("<!-- LEADERS -->")
    if pl == -1 or lb == -1:
        raise SystemExit("tab-pl or LEADERS marker missing")

    outside = [
        m.start()
        for m in re.finditer(r'<div class="pc">', html)
        if m.start() < pl or m.start() >= lb
    ]
    if outside:
        raise SystemExit(f".pc outside #tab-pl: {len(outside)} occurrences")

    wrap_open = html.find('class="wrap"')
    tab_ru = html.find('id="tab-ru"')
    if wrap_open == -1 or tab_ru == -1:
        raise SystemExit("wrap or tab-ru missing")
    segment = html[wrap_open:tab_ru]
    if segment.count("<div") - segment.count("</div>") <= 0:
        raise SystemExit("tab-ru is not inside .wrap")


def main() -> None:
    html = INDEX.read_text(encoding="utf-8")
    html = fix_tab_mx_boundary(html)
    html = fix_tab_pl_boundary(html)
    html = fix_tab_lb_boundary(html)
    html = patch_leaderboards(html)
    html = patch_stats_tables(html)
    validate_structure(html)
    INDEX.write_text(html, encoding="utf-8")
    print(f"Fixed HTML structure in {INDEX}")


if __name__ == "__main__":
    main()
