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

MATCHES_PLAYED = {
    "Qaim": 5,
    "Avyaan": 5,
    "Ariyan": 4,
    "Kaiyan": 4,
    "Veer": 4,
    "Krish": 4,
    "Drish": 4,
    "Aanya": 4,
    "Shyam": 4,
    "Taran": 3,
    "Viaan": 3,
}
ECC_NAMES = set(MATCHES_PLAYED)
MIN_OVERS_BEST_ECONOMY = 2.0
FIELDING_TOTALS = {
    "Avyaan": (2, 3),
    "Qaim": (1, 2),
    "Drish": (1, 1),
    "Taran": (1, 1),
    "Viaan": (0, 1),
    "Shyam": (1, 0),
    "Ariyan": (0, 1),
    "Krish": (0, 1),
}


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
        m_map = MATCHES_PLAYED
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
_TOP_STRIKE_RATES = '      <div class="lbc"><div class="lbh">&#9889; Top Strike Rates'


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


def _season_best_economy_rows(html: str) -> list[tuple[str, float]]:
    bowl_table_match = re.search(
        r'<thead><tr><th>Bowler</th><th class="c">M</th><th class="c">O</th><th class="c">R</th>'
        r'<th class="c">W</th><th class="c">WD</th><th class="c">NB</th><th class="c">ECO</th><th class="c">Dots</th></tr></thead>\s*<tbody>\s*(.*?)\s*</tbody>',
        html,
        flags=re.DOTALL,
    )
    if not bowl_table_match:
        return []
    body = bowl_table_match.group(1)
    rows: list[tuple[str, float]] = []
    for row_match in re.finditer(r"<tr>(.*?)</tr>", body, flags=re.DOTALL):
        row_html = row_match.group(1)
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row_html, flags=re.DOTALL)
        if len(cells) < 8:
            continue
        values = [re.sub(r"<[^>]+>", "", cell).strip() for cell in cells]
        name = values[0]
        overs_text = values[2]
        eco_text = values[7]
        try:
            overs = float(overs_text)
            eco = float(eco_text)
        except ValueError:
            continue
        if overs >= MIN_OVERS_BEST_ECONOMY:
            rows.append((name, eco))
    rows.sort(key=lambda item: (item[1], item[0]))
    return rows[:5]


def _best_economy_card_from_html(html: str) -> str | None:
    rows = _season_best_economy_rows(html)
    if not rows:
        return None
    lines = ['      <div class="lbc"><div class="lbh">&#128200; Best Economy (min 2 overs)</div>']
    for i, (name, eco) in enumerate(rows):
        rank = f"r{i + 1}" if i < 3 else "rn"
        lines.append(
            f'        <div class="lbr"><div class="lbrk {rank}">{i + 1}</div><div class="lbn">{name}</div><div class="lbv">{eco:.1f}</div></div>'
        )
    lines[-1] = f"{lines[-1]}</div>"
    return "\n".join(lines)


def _match_summary_blocks(html: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for match_id in ("m2", "m4", "m5", "m6", "m7"):
        start = html.find(f'id="match-{match_id}-summary"')
        if start == -1:
            continue
        end = html.find(f'id="match-{match_id}-bbb"', start)
        if end == -1:
            continue
        out.append((match_id.upper(), html[start:end]))
    return out


def _best_bowling_figures_rows(html: str) -> list[tuple[str, str, int, int]]:
    # Per player best figure from single match: wickets desc, then lower runs.
    best: dict[str, tuple[str, int, int]] = {}
    for match_label, block in _match_summary_blocks(html):
        for table_body in re.findall(
            r'<table class="sctbl">\s*<thead><tr><th>Bowler</th>.*?</thead>\s*<tbody>(.*?)</tbody>',
            block,
            flags=re.DOTALL,
        ):
            for row_html in re.findall(r"<tr>(.*?)</tr>", table_body, flags=re.DOTALL):
                cells = re.findall(r"<td[^>]*>(.*?)</td>", row_html, flags=re.DOTALL)
                if len(cells) < 4:
                    continue
                values = [re.sub(r"<[^>]+>", "", cell).strip() for cell in cells]
                name = values[0]
                if name not in ECC_NAMES:
                    continue
                try:
                    runs = int(values[2])
                    wickets = int(values[3])
                except ValueError:
                    continue
                if wickets <= 0:
                    continue
                current = best.get(name)
                if current is None or wickets > current[1] or (wickets == current[1] and runs < current[2]):
                    best[name] = (match_label, wickets, runs)
    ranked = sorted(
        ((name, match, wkts, runs) for name, (match, wkts, runs) in best.items()),
        key=lambda row: (-row[2], row[3], row[0]),
    )
    return ranked[:5]


def _best_bowling_figures_map(html: str) -> dict[str, str]:
    # Per player best single-match figure used on player cards.
    best: dict[str, tuple[int, int]] = {}
    for _match_label, block in _match_summary_blocks(html):
        for table_body in re.findall(
            r'<table class="sctbl">\s*<thead><tr><th>Bowler</th>.*?</thead>\s*<tbody>(.*?)</tbody>',
            block,
            flags=re.DOTALL,
        ):
            for row_html in re.findall(r"<tr>(.*?)</tr>", table_body, flags=re.DOTALL):
                cells = re.findall(r"<td[^>]*>(.*?)</td>", row_html, flags=re.DOTALL)
                if len(cells) < 4:
                    continue
                values = [re.sub(r"<[^>]+>", "", cell).strip() for cell in cells]
                name = values[0]
                if name not in ECC_NAMES:
                    continue
                try:
                    runs = int(values[2])
                    wickets = int(values[3])
                except ValueError:
                    continue
                current = best.get(name)
                if current is None or wickets > current[0] or (wickets == current[0] and runs < current[1]):
                    best[name] = (wickets, runs)
    return {name: f"{wkts}/{runs}" for name, (wkts, runs) in best.items()}


def _best_bowling_figures_card(html: str) -> str | None:
    rows = _best_bowling_figures_rows(html)
    if not rows:
        return None
    lines = ['      <div class="lbc"><div class="lbh">&#127942; Best Bowling Figures</div>']
    for i, (name, match, wkts, runs) in enumerate(rows):
        rank = f"r{i + 1}" if i < 3 else "rn"
        lines.append(
            f'        <div class="lbr"><div class="lbrk {rank}">{i + 1}</div>'
            f'<div class="lbn">{name} <span style="font-size:.7rem;color:var(--mgrey);font-weight:400;">{match}</span></div>'
            f'<div class="lbv">{wkts}/{runs}</div></div>'
        )
    lines[-1] = f"{lines[-1]}</div>"
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


_STRIKE_CARD = re.compile(
    r'\n      <div class="lbc"><div class="lbh">&#9889; Top Strike Rates[^\n]*</div>\n'
    r'(?:        <div class="lbr">[^\n]*</div>\n)*'
    r'        <div class="lbr">[^\n]*</div></div>\n'
)
_TAB_LB = '<div id="tab-lb"'
_RULES_MARKER = "<!-- RULES -->"


def patch_leaders_tab(html: str, season: dict) -> str:
    """Insert or refresh Top Strike Rates before Most Fours in #tab-lb."""
    board = build_strike_rate_leaderboard(season)
    tab_lb = html.find(_TAB_LB)
    if tab_lb == -1:
        return html
    tab_end = html.find(_RULES_MARKER, tab_lb)
    if tab_end == -1:
        return html
    section = html[tab_lb:tab_end]
    fours_at = section.find(_MOST_FOURS)
    if fours_at == -1:
        return html
    section = _STRIKE_CARD.sub("\n", section, count=1)
    fours_at = section.find(_MOST_FOURS)
    new_section = section[:fours_at] + "\n" + board + "\n" + section[fours_at:]
    economy_card = _best_economy_card_from_html(html)
    if economy_card:
        new_section = re.sub(
            r'<div class="lbc"><div class="lbh">&#128200; Best Economy \(min 2 overs\)</div>.*?</div>\s*(?=<div class="lbc"><div class="lbh">&#128308; Most Dot Balls</div>)',
            economy_card,
            new_section,
            count=1,
            flags=re.DOTALL,
        )
    new_section = re.sub(
        r'\n\s*<div class="lbc"><div class="lbh">&#127942; Best Bowling Figures</div>.*?</div>\s*(?=<div class="lbc"><div class="lbh">(?:&#9889; Top Strike Rates|&#128308; Most Fours)</div>)',
        "\n",
        new_section,
        count=1,
        flags=re.DOTALL,
    )
    figures_card = _best_bowling_figures_card(html)
    if figures_card:
        new_section = re.sub(
            r'(\s*<div class="lbc"><div class="lbh">&#128308; Most Fours</div>)',
            rf"\n{figures_card}\n\1",
            new_section,
            count=1,
        )
    return html[:tab_lb] + new_section + html[tab_end:]


_PC_GRID_END = re.compile(
    r"\n    </div>\s*\n  </div>\s*\n</div>\s*\n\s*\n<!-- LEADERS -->"
)
_PC_NEXT_CARD = re.compile(r"\n      <div class=\"pc\">")


def _player_card_pattern(name: str) -> str:
    """Match a full .pc card (all stat sections), not just through batting pss."""
    return (
        rf"(<div class=\"pc\"><div class=\"pnb\">{re.escape(name)} <span>ECC</span></div>"
        rf"(?:(?!\n      <div class=\"pc\">).)*?"
        rf"</div>\s*\n      (?=\n      <div class=\"pc\">|\n    </div>))"
    )


def patch_player_cards(html: str, season: dict) -> str:
    bat_rows: dict[str, dict[str, str]] = {}
    for m in re.finditer(
        r'<tr><td><strong>([^<]+)</strong></td><td class="c">\d+</td><td class="c">(\d+)</td><td class="c">(\d+)</td>'
        r'<td class="c">([\d.]+)</td><td class="c">([\d.]+)</td><td class="c">(\d+)</td><td class="c">(\d+)</td><td class="c">(\d+)</td>'
        r'<td class="c (np|nn)">([^<]+)</td></tr>',
        html,
    ):
        bat_rows[m.group(1)] = {
            "inn": m.group(2),
            "runs": m.group(3),
            "avg": m.group(4),
            "sr": m.group(5),
            "hs": m.group(6),
            "fours": m.group(7),
            "sixes": m.group(8),
            "net_cls": m.group(9),
            "net": m.group(10),
        }

    bowl_rows: dict[str, dict[str, str]] = {}
    for m in re.finditer(
        r'<tr><td><strong>([^<]+)</strong></td><td class="c">\d+</td><td class="c">(\d+)</td><td class="c">(\d+)'
        r'</td><td class="c">(?:<strong>)?(\d+)(?:</strong>)?</td><td class="c">\d+</td><td class="c">\d+</td>'
        r'<td class="c(?: (eco-good|eco-bad))?">([\d.]+)</td><td class="c">(?:<strong>)?(\d+)(?:</strong>)?</td></tr>',
        html,
    ):
        bowl_rows[m.group(1)] = {
            "overs": m.group(2),
            "runs": m.group(3),
            "wkts": m.group(4),
            "eco_cls": m.group(5) or "",
            "eco": m.group(6),
            "dots": m.group(7),
        }

    field_rows: dict[str, tuple[str, str]] = {name: ("0", "0") for name in ECC_NAMES}
    for m in re.finditer(
        r'<tr><td><strong>([^<]+)</strong></td><td class="c">\d+</td><td class="c">(?:<strong>)?(\d+)(?:</strong>)?</td><td class="c">(?:<strong>)?(\d+)(?:</strong>)?</td></tr>',
        html,
    ):
        if m.group(1) in field_rows:
            field_rows[m.group(1)] = (m.group(2), m.group(3))
    best_bowl_figures = _best_bowling_figures_map(html)

    card_order = [
        "Ariyan", "Avyaan", "Krish", "Veer", "Kaiyan", "Aanya",
        "Taran", "Drish", "Shyam", "Qaim", "Viaan",
    ]
    cards: list[str] = []
    for name in card_order:
        b = bat_rows.get(name)
        bw = bowl_rows.get(name)
        if not b or not bw:
            continue
        catches, run_outs = field_rows.get(name, ("0", "0"))
        eco_cls = f' class="psv {bw["eco_cls"]}"' if bw["eco_cls"] else ' class="psv"'
        cards.append(
            f'      <div class="pc"><div class="pnb">{name} <span>ECC</span></div>\n'
            '        <div class="pss"><div class="psst"><span><img src="icons/batsman_dark.png" style="width:18px;height:18px;vertical-align:middle;" alt="bat"></span> Batting</div>\n'
            f'          <div class="psr"><span class="psl">Inn</span><span class="psv">{b["inn"]}</span></div>\n'
            f'          <div class="psr"><span class="psl">Bat Runs / Avg</span><span class="psv">{b["runs"]} / {b["avg"]}</span></div>\n'
            f'          <div class="psr"><span class="psl">Best Batting Score</span><span class="psv">{b["hs"]}</span></div>\n'
            f'          <div class="psr"><span class="psl">Strike Rate</span><span class="psv">{b["sr"]}</span></div>\n'
            f'          <div class="psr"><span class="psl">4s / 6s</span><span class="psv">{b["fours"]} / {b["sixes"]}</span></div>\n'
            f'          <div class="psr"><span class="psl">Net Runs</span><span class="psv {b["net_cls"]}">{b["net"]}</span></div></div>\n'
            '        <div class="pss"><div class="psst"><span><img src="icons/cricket-ball-red.png" style="width:18px;height:18px;vertical-align:middle;" alt="ball"></span> Bowling</div>\n'
            f'          <div class="psr"><span class="psl">Overs / Wkts</span><span class="psv">{bw["overs"]} / {bw["wkts"]}</span></div>\n'
            f'          <div class="psr"><span class="psl">Best Bowling Figures</span><span class="psv">{best_bowl_figures.get(name, "0/0")}</span></div>\n'
            f'          <div class="psr"><span class="psl">Runs / ECO</span><span{eco_cls}>{bw["runs"]} / {bw["eco"]}</span></div>\n'
            f'          <div class="psr"><span class="psl">Dots</span><span class="psv">{bw["dots"]}</span></div></div>\n'
            '        <div class="pss"><div class="psst"><span><img src="icons/fielding-role.png" style="width:18px;height:18px;vertical-align:middle;" alt="field"></span> Fielding</div>\n'
            f'          <div class="psr"><span class="psl">Catches</span><span class="psv">{catches}</span></div>\n'
            f'          <div class="psr"><span class="psl">Run Outs</span><span class="psv">{run_outs}</span></div></div></div>'
        )

    cards_html = "\n".join(cards)
    html = re.sub(
        r'(<div class="pgrid">\s*).*?(\s*</div>\s*</div>\s*</div>\s*\n\s*<!-- LEADERS -->)',
        rf"\1{cards_html}\n    \2",
        html,
        count=1,
        flags=re.DOTALL,
    )
    return html


def main() -> None:
    lookup = _build_innings_lookup()
    season = collect_ecc_season()
    html = INDEX.read_text(encoding="utf-8")
    html = patch_match_summaries(html, lookup)
    html = patch_players_tab(html, season)
    html = patch_leaders_tab(html, season)
    html = patch_player_cards(html, season)
    from patch_index import fix_tab_pl_boundary  # noqa: WPS433

    html = fix_tab_pl_boundary(html)
    INDEX.write_text(html, encoding="utf-8")
    print(f"Patched strike rates in {INDEX}")


if __name__ == "__main__":
    main()
