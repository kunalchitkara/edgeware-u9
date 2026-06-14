#!/usr/bin/env python3
"""Add strike rate to match summaries, Players tab, and Leaders in index.html."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"

sys.path.insert(0, str(ROOT / "scripts"))
from batting_stats import collect_all_innings, collect_ecc_season  # noqa: E402
from strike_rate import MIN_BALLS_LEADERBOARD, format_sr, format_sr_value  # noqa: E402

BAT_HDR_FULL = (
    '<thead><tr><th>Batter</th><th>Dismissal</th><th class="c">R</th>'
    '<th class="c">SR</th><th class="c">4s</th><th class="c">6s</th><th class="c">Net</th></tr></thead>'
)
BAT_HDR_SHORT = (
    '<thead><tr><th>Batter</th><th>Dismissal</th><th class="c">R</th>'
    '<th class="c">SR</th><th class="c">Net</th></tr></thead>'
)
BAT_HDR_OLD_FULL = (
    '<thead><tr><th>Batter</th><th>Dismissal</th><th class="c">R</th>'
    '<th class="c">4s</th><th class="c">6s</th><th class="c">Net</th></tr></thead>'
)
BAT_HDR_OLD_SHORT = (
    '<thead><tr><th>Batter</th><th>Dismissal</th><th class="c">R</th>'
    '<th class="c">Net</th></tr></thead>'
)


def _build_innings_lookup() -> dict[str, list[dict[str, tuple[int, int]]]]:
    """match_id -> list of per-innings {batter: (runs, balls)} dicts."""
    lookup: dict[str, list[dict[str, tuple[int, int]]]] = {}
    for inn in collect_all_innings():
        lookup.setdefault(inn.match_id, []).append(dict(inn.batters))
    return lookup


def _sr_cell(name: str, batters: dict[str, tuple[int, int]]) -> str:
    runs, balls = batters.get(name, (0, 0))
    return format_sr(runs, balls)


def _patch_batter_row_full(row: str, batters: dict[str, tuple[int, int]]) -> str:
    if '<th class="c">SR</th>' in row or 'class="scex"' in row or 'class="sctot"' in row:
        return row
    m = re.match(
        r'(<tr><td class="scb">([^<]+)</td><td class="scd">[^<]*</td>'
        r'<td class="c scr">[^<]*</td>)'
        r'(?:<td class="c">[^<]*</td>)?'  # existing SR if re-run
        r'(<td class="c">[^<]*</td><td class="c">[^<]*</td><td class="c[^"]*">[^<]*</td></tr>)',
        row,
    )
    if not m:
        # Already has SR column
        m2 = re.match(
            r'(<tr><td class="scb">([^<]+)</td><td class="scd">[^<]*</td>'
            r'<td class="c scr">[^<]*</td><td class="c">[^<]*</td>)'
            r'(<td class="c">[^<]*</td><td class="c">[^<]*</td><td class="c[^"]*">[^<]*</td></tr>)',
            row,
        )
        if m2:
            return row
        return row
    prefix, name, suffix = m.group(1), m.group(2), m.group(3)
    return f'{prefix}<td class="c">{_sr_cell(name, batters)}</td>{suffix}'


def _patch_batter_row_short(row: str, batters: dict[str, tuple[int, int]]) -> str:
    if 'class="scex"' in row or 'class="sctot"' in row:
        return row
    m = re.match(
        r'(<tr><td class="scb">([^<]+)</td><td class="scd">[^<]*</td>'
        r'<td class="c scr">[^<]*</td>)'
        r'(?:<td class="c">[^<]*</td>)?'  # optional existing SR
        r'(<td class="c[^"]*">[^<]*</td></tr>)',
        row,
    )
    if not m:
        m2 = re.match(
            r'(<tr><td class="scb">([^<]+)</td><td class="scd">[^<]*</td>'
            r'<td class="c scr">[^<]*</td><td class="c">[^<]*</td>)'
            r'(<td class="c[^"]*">[^<]*</td></tr>)',
            row,
        )
        if m2:
            return row
        return row
    prefix, name, suffix = m.group(1), m.group(2), m.group(3)
    return f'{prefix}<td class="c">{_sr_cell(name, batters)}</td>{suffix}'


def _patch_extras_row(row: str, extra_cols: int) -> str:
    if 'class="scex"' not in row:
        return row
    return re.sub(
        r'(<td class="c") colspan="(\d+)"',
        lambda m: f'{m.group(1)} colspan="{extra_cols}"',
        row,
        count=1,
    )


def patch_match_summaries(html: str, lookup: dict[str, list[dict[str, tuple[int, int]]]]) -> str:
    for match_id in ("m2", "m4", "m5", "m6"):
        marker = f'id="match-{match_id}-summary"'
        start = html.find(marker)
        if start == -1:
            continue
        end = html.find(f'id="match-{match_id}-bbb"', start)
        if end == -1:
            end = len(html)
        block = html[start:end]
        innings = lookup.get(match_id, [])
        inn_idx = 0

        def patch_table(table_html: str) -> str:
            nonlocal inn_idx
            if inn_idx >= len(innings):
                return table_html
            batters = innings[inn_idx]
            inn_idx += 1

            if BAT_HDR_OLD_FULL in table_html:
                table_html = table_html.replace(BAT_HDR_OLD_FULL, BAT_HDR_FULL, 1)
                row_pat = re.compile(
                    r'<tr><td class="scb">[^<]+</td><td class="scd">[^<]*</td>'
                    r'<td class="c scr">[^<]*</td><td class="c">[^<]*</td>'
                    r'<td class="c">[^<]*</td><td class="c[^"]*">[^<]*</td></tr>'
                )
                table_html = row_pat.sub(lambda m: _patch_batter_row_full(m.group(0), batters), table_html)
                table_html = re.sub(r'colspan="4"', 'colspan="5"', table_html)
            elif BAT_HDR_OLD_SHORT in table_html:
                table_html = table_html.replace(BAT_HDR_OLD_SHORT, BAT_HDR_SHORT, 1)
                row_pat = re.compile(
                    r'<tr><td class="scb">[^<]+</td><td class="scd">[^<]*</td>'
                    r'<td class="c scr">[^<]*</td><td class="c[^"]*">[^<]*</td></tr>'
                )
                table_html = row_pat.sub(lambda m: _patch_batter_row_short(m.group(0), batters), table_html)
                table_html = re.sub(r'colspan="4"', 'colspan="5"', table_html)
            elif '<th class="c">SR</th>' in table_html:
                row_pat = re.compile(
                    r'<tr><td class="scb">([^<]+)</td><td class="scd">[^<]*</td>'
                    r'<td class="c scr">[^<]*</td><td class="c">[^<]*</td>'
                    r'<td class="c">[^<]*</td><td class="c">[^<]*</td><td class="c[^"]*">[^<]*</td></tr>'
                )

                def repl(m: re.Match[str]) -> str:
                    name = m.group(1)
                    sr = _sr_cell(name, batters)
                    return re.sub(
                        r'(<td class="c scr">[^<]*</td><td class="c">)[^<]*(</td>)',
                        rf'\g<1>{sr}\2',
                        m.group(0),
                        count=1,
                    )

                table_html = row_pat.sub(repl, table_html)
            return table_html

        # Patch each batting scorecard table in the match summary block.
        parts = re.split(r'(<div class="tscroll"><table class="sctbl">.*?</table></div>)', block, flags=re.DOTALL)
        new_parts = []
        for part in parts:
            if part.startswith('<div class="tscroll"><table class="sctbl">') and "Batter</th><th>Dismissal" in part:
                new_parts.append(patch_table(part))
            else:
                new_parts.append(part)
        html = html[:start] + "".join(new_parts) + html[end:]
    return html


def build_players_table_body(season: dict) -> str:
    rows = []
    order = sorted(season.items(), key=lambda x: x[1].runs, reverse=True)
    for name, s in order:
        if s.innings == 0:
            continue
        net_sign = "+" if True else ""  # placeholder
        # Net runs from existing table — keep manual values aligned with patch_m6_overview
        net_map = {
            "Ariyan": "+19", "Qaim": "+13", "Veer": "+16", "Avyaan": "+18", "Kaiyan": "+15",
            "Viaan": "+13", "Krish": "&minus;8", "Taran": "+2", "Drish": "+7",
            "Shyam": "&minus;11", "Aanya": "&minus;10",
        }
        net = net_map.get(name, "+0")
        net_cls = "np" if net.startswith("+") else "nn"
        m_map = {"Ariyan": 4, "Qaim": 4, "Veer": 4, "Avyaan": 4, "Kaiyan": 3, "Viaan": 3,
                 "Krish": 3, "Taran": 2, "Drish": 3, "Shyam": 3, "Aanya": 3}
        fours = {"Ariyan": 4, "Qaim": 5, "Veer": 1, "Avyaan": 1, "Kaiyan": 3, "Viaan": 2,
                 "Krish": 0, "Taran": 1, "Drish": 1, "Shyam": 1, "Aanya": 0}
        sixes = {"Avyaan": 1}
        hs = {"Ariyan": 11, "Qaim": 13, "Veer": 10, "Avyaan": 9, "Kaiyan": 14, "Viaan": 11,
              "Krish": 9, "Taran": 7, "Drish": 5, "Shyam": 5, "Aanya": 3}
        sr = format_sr_value(s.sr)
        rows.append(
            f'        <tr><td><strong>{name}</strong></td><td class="c">{m_map.get(name, 0)}</td>'
            f'<td class="c">{s.innings}</td><td class="c">{s.runs}</td>'
            f'<td class="c">{s.avg:.1f}</td><td class="c">{sr}</td>'
            f'<td class="c">{hs.get(name, s.hs)}</td><td class="c">{fours.get(name, 0)}</td>'
            f'<td class="c">{sixes.get(name, 0)}</td><td class="c {net_cls}">{net}</td></tr>'
        )
    return "\n".join(rows)


# Anchor for inserting Top Strike Rates before Most Fours (avoids catastrophic regex backtracking).
_MOST_FOURS = '      <div class="lbc"><div class="lbh">&#128308; Most Fours</div>'


def build_strike_rate_leaderboard(season: dict) -> str:
    ranked = [
        (name, s)
        for name, s in season.items()
        if s.balls >= MIN_BALLS_LEADERBOARD and s.sr is not None
    ]
    ranked.sort(key=lambda x: x[1].sr or 0, reverse=True)
    lines = [
        '      <div class="lbc"><div class="lbh">&#9889; Top Strike Rates '
        f'<span style="font-size:.7rem;color:var(--mgrey);font-weight:400;">'
        f"(min {MIN_BALLS_LEADERBOARD} balls)</span></div>"
    ]
    for i, (name, s) in enumerate(ranked[:5]):
        rank = f"r{i + 1}" if i < 3 else "rn"
        row = (
            f'        <div class="lbr"><div class="lbrk {rank}">{i + 1}</div>'
            f'<div class="lbn">{name}</div><div class="lbv">{s.sr:.1f}</div></div>'
        )
        if i == len(ranked[:5]) - 1:
            row += "</div>"
        lines.append(row)
    if not ranked[:5]:
        lines.append("      </div>")
    return "\n".join(lines)


def patch_players_tab(html: str, season: dict) -> str:
    html = re.sub(
        r"Net Runs = Bat Runs &minus; 5 per wicket lost\. Avg = Bat Runs &divide; Innings\.(?: SR = runs &divide; balls faced &times; 100\.)?",
        "Net Runs = Bat Runs &minus; 5 per wicket lost. "
        "Avg = Bat Runs &divide; Innings. SR = runs &divide; balls faced &times; 100.",
        html,
    )
    html = re.sub(
        r'<thead><tr><th>Batter</th><th class="c">M</th><th class="c">Inn</th>'
        r'<th class="c">Bat Runs</th><th class="c">Avg</th>'
        r'(?:<th class="c">SR</th>)?'
        r'<th class="c">HS</th><th class="c">4s</th><th class="c">6s</th><th class="c">Net Runs</th></tr></thead>',
        '<thead><tr><th>Batter</th><th class="c">M</th><th class="c">Inn</th>'
        '<th class="c">Bat Runs</th><th class="c">Avg</th><th class="c">SR</th><th class="c">HS</th>'
        '<th class="c">4s</th><th class="c">6s</th><th class="c">Net Runs</th></tr></thead>',
        html,
        count=1,
    )
    body = build_players_table_body(season)
    html = re.sub(
        r'(<div class="tscroll" style="margin-bottom:24px;"><table class="dt">\s*'
        r'<thead><tr><th>Batter</th>.*?</thead>\s*<tbody>\s*)'
        r'(?:<tr>.*?</tr>\s*)+'
        r'(</tbody>)',
        rf"\1{body}\n      \2",
        html,
        count=1,
        flags=re.DOTALL,
    )
    return html


_WICKETS_END = (
    '        <div class="lbr"><div class="lbrk rn">4</div><div class="lbn">Aanya</div>'
    '<div class="lbv">2</div></div></div>'
)
_STRIKE_HEADER = '      <div class="lbc"><div class="lbh">&#9889; Top Strike Rates'


def patch_leaders_tab(html: str, season: dict) -> str:
    board = build_strike_rate_leaderboard(season)
    start = html.find(_WICKETS_END)
    if start == -1:
        return html
    insert_at = start + len(_WICKETS_END)
    rest = html[insert_at:]
    if rest.lstrip().startswith(_STRIKE_HEADER):
        fours_at = rest.find(_MOST_FOURS)
        if fours_at == -1:
            return html
        rest = rest[fours_at:]
    fours_at = rest.find(_MOST_FOURS)
    if fours_at == -1:
        return html
    rest = rest[fours_at:]
    return html[:insert_at] + "\n" + board + "\n" + rest


def _player_card_pattern(name: str) -> str:
    return (
        rf'(<div class="pc"><div class="pnb">{re.escape(name)} <span>ECC</span></div>'
        rf'(?:(?!</div>\s*<div class="pc">).)*?</div>\s*</div>)'
    )


def patch_player_cards(html: str, season: dict) -> str:
    for name, s in season.items():
        if s.innings == 0:
            continue
        sr = format_sr_value(s.sr)
        pat = _player_card_pattern(name)
        m = re.search(pat, html, flags=re.DOTALL)
        if not m:
            continue
        card = m.group(1)
        if '<span class="psl">Strike Rate</span>' in card:
            continue
        inner_pat = (
            r'(<span class="psl">Bat Runs / Avg</span><span class="psv">)(\d+ / [\d.]+)(</span></div>\s*)'
            r'(<div class="psr"><span class="psl">4s / 6s</span>)'
        )
        new_card = re.sub(
            inner_pat,
            lambda m2: (
                f"{m2.group(1)}{s.runs} / {s.avg:.1f}{m2.group(3)}"
                f'          <div class="psr"><span class="psl">Strike Rate</span>'
                f'<span class="psv">{sr}</span></div>\n          {m2.group(4)}'
            ),
            card,
            count=1,
            flags=re.DOTALL,
        )
        html = html[: m.start()] + new_card + html[m.end() :]
    return html


def main() -> None:
    lookup = _build_innings_lookup()
    season = collect_ecc_season()
    html = INDEX.read_text(encoding="utf-8")
    html = patch_match_summaries(html, lookup)
    html = patch_players_tab(html, season)
    html = patch_leaders_tab(html, season)
    html = patch_player_cards(html, season)
    INDEX.write_text(html, encoding="utf-8")
    print(f"Patched strike rates in {INDEX}")


if __name__ == "__main__":
    main()
