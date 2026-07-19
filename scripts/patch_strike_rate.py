#!/usr/bin/env python3
"""Add strike rate to match summaries, Players tab, and Leaders in index.html."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"

sys.path.insert(0, str(ROOT / "scripts"))
from batting_stats import collect_all_innings  # noqa: E402
from summary_player_stats import collect_summary_season, render_leader_card  # noqa: E402
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

ECC_NAMES = {
    "Ariyan",
    "Qaim",
    "Veer",
    "Avyaan",
    "Kaiyan",
    "Viaan",
    "Krish",
    "Taran",
    "Drish",
    "Shyam",
    "Aanya",
    "Ishaan",
    "Shay",
    "Riyan",
}
MIN_OVERS_BEST_ECONOMY = 2.0
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
        if s.matches == 0:
            continue
        net = f"+{s.net}" if s.net >= 0 else f"&minus;{abs(s.net)}"
        net_cls = "np" if net.startswith("+") else "nn"
        sr = format_sr_value(s.sr)
        rows.append(
            f'        <tr><td><strong>{name}</strong></td><td class="c">{s.matches}</td>'
            f'<td class="c">{s.innings}</td><td class="c">{s.runs}</td>'
            f'<td class="c">{s.avg_match:.1f}</td><td class="c">{s.avg_inn:.1f}</td>'
            f'<td class="c">{sr}</td><td class="c">{s.hs}</td><td class="c">{s.fours}</td>'
            f'<td class="c">{s.sixes}</td><td class="c {net_cls}">{net}</td></tr>'
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
    top = ranked[:5]
    title = (
        '&#9889; Top Strike Rates '
        f'<span style="font-size:.7rem;color:var(--mgrey);font-weight:400;">'
        f"(min {MIN_BALLS_LEADERBOARD} balls)</span>"
    )
    rows = [(name, f"{s.sr:.1f}") for name, s in top]
    sort_keys = [s.sr or 0 for _name, s in top]
    return render_leader_card(title, rows, sort_keys)


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
    rows: list[tuple[str, float, float]] = []
    for row_match in re.finditer(r"<tr>(.*?)</tr>", body, flags=re.DOTALL):
        row_html = row_match.group(1)
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row_html, flags=re.DOTALL)
        if len(cells) < 8:
            continue
        values = [re.sub(r"<[^>]+>", "", cell).strip() for cell in cells]
        name = values[0]
        try:
            overs = float(values[2])
            runs = int(values[3])
        except ValueError:
            continue
        if overs >= MIN_OVERS_BEST_ECONOMY:
            rows.append((name, runs / overs, overs))
    rows.sort(key=lambda item: (item[1], item[0]))
    return [(name, eco) for name, eco, _overs in rows[:5]]


def _best_economy_card_from_html(html: str) -> str | None:
    rows = _season_best_economy_rows(html)
    if not rows:
        return None
    display = [(name, f"{eco:.2f}") for name, eco in rows]
    sort_keys = [eco for _name, eco in rows]
    return render_leader_card("&#128200; Best Economy (min 2 overs)", display, sort_keys)


def _match_summary_blocks(html: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for match_id in ("m2", "m4", "m5", "m6", "m7", "m8", "m10"):
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
    display = [
        (
            f'{name} <span style="font-size:.7rem;color:var(--mgrey);font-weight:400;">{match}</span>',
            f"{wkts}/{runs}",
        )
        for name, match, wkts, runs in rows
    ]
    sort_keys = [(wkts, runs) for _name, _match, wkts, runs in rows]
    return render_leader_card("&#127942; Best Bowling Figures", display, sort_keys)


def patch_players_tab(html: str, season: dict) -> str:
    html = re.sub(
        r"Net Runs = Bat Runs &minus; 5 per wicket lost\.(?: Inn = dismissals \+ 1\.)? "
        r"(?:Avg/M = Bat Runs &divide; M\. Avg/Inn = Bat Runs &divide; Inn\.|Avg = Bat Runs &divide; Innings\.) "
        r"SR = runs &divide; balls faced &times; 100\.",
        "Net Runs = Bat Runs &minus; 5 per wicket lost. Inn = dismissals + 1. "
        "Avg/M = Bat Runs &divide; M. Avg/Inn = Bat Runs &divide; Inn. "
        "SR = runs &divide; balls faced &times; 100.",
        html,
    )
    html = re.sub(
        r'<thead><tr><th>Batter</th><th class="c">M</th><th class="c">Inn</th>'
        r'<th class="c">Bat Runs</th><th class="c">(?:Avg/M|Avg)</th>'
        r'(?:<th class="c">Avg/Inn</th>)?'
        r'(?:<th class="c">SR</th>)?'
        r'<th class="c">HS</th><th class="c">4s</th><th class="c">6s</th><th class="c">Net Runs</th></tr></thead>',
        '<thead><tr><th>Batter</th><th class="c">M</th><th class="c">Inn</th>'
        '<th class="c">Bat Runs</th><th class="c">Avg/M</th><th class="c">Avg/Inn</th>'
        '<th class="c">SR</th><th class="c">HS</th><th class="c">4s</th><th class="c">6s</th>'
        '<th class="c">Net Runs</th></tr></thead>',
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


def _find_matching_div_end(html: str, open_tag_end: int) -> int:
    depth = 1
    pos = open_tag_end
    while depth > 0 and pos < len(html):
        next_open = html.find("<div", pos)
        next_close = html.find("</div>", pos)
        if next_close == -1:
            raise SystemExit("Unclosed div block while patching player cards")
        if next_open != -1 and next_open < next_close:
            depth += 1
            pos = next_open + 4
        else:
            depth -= 1
            pos = next_close + len("</div>")
            if depth == 0:
                return pos
    raise SystemExit("Could not locate closing div while patching player cards")


def patch_player_cards(html: str, season: dict) -> str:
    bat_rows: dict[str, dict[str, str]] = {}
    for m in re.finditer(
        r'<tr><td><strong>([^<]+)</strong></td><td class="c">\d+</td><td class="c">(\d+)</td><td class="c">(\d+)</td>'
        r'<td class="c">([\d.]+)</td><td class="c">([\d.]+)</td><td class="c">([\d.]+)</td><td class="c">(\d+)</td>'
        r'<td class="c">(\d+)</td><td class="c">(\d+)</td>'
        r'<td class="c (np|nn)">([^<]+)</td></tr>',
        html,
    ):
        bat_rows[m.group(1)] = {
            "inn": m.group(2),
            "runs": m.group(3),
            "avg_match": m.group(4),
            "avg_inn": m.group(5),
            "sr": m.group(6),
            "hs": m.group(7),
            "fours": m.group(8),
            "sixes": m.group(9),
            "net_cls": m.group(10),
            "net": m.group(11),
        }

    bowl_rows: dict[str, dict[str, str]] = {}
    for m in re.finditer(
        r'<tr><td><strong>([^<]+)</strong></td><td class="c">\d+</td><td class="c">([\d.]+)</td><td class="c">(\d+)'
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
    tab_pl_start = html.find('<div id="tab-pl" class="tab">')
    tab_lb_start = html.find('<div id="tab-lb" class="tab">', tab_pl_start) if tab_pl_start != -1 else -1
    if tab_pl_start != -1 and tab_lb_start != -1:
        tab_pl = html[tab_pl_start:tab_lb_start]
        tables = list(
            re.finditer(
                r"<table class=\"dt\">\s*<thead><tr>.*?</tr></thead>\s*<tbody>(.*?)</tbody>\s*</table>",
                tab_pl,
                flags=re.DOTALL,
            )
        )
        if len(tables) >= 3:
            body = tables[2].group(1)
            for m in re.finditer(
                r'<tr><td><strong>([^<]+)</strong></td><td class="c">(?:<strong>)?(\d+)(?:</strong>)?</td><td class="c">(?:<strong>)?(\d+)(?:</strong>)?</td></tr>',
                body,
            ):
                if m.group(1) in field_rows:
                    field_rows[m.group(1)] = (m.group(2), m.group(3))
    best_bowl_figures = _best_bowling_figures_map(html)

    card_order = sorted(
        bat_rows.keys(),
        key=lambda name: (-int(bat_rows[name]["runs"]), name),
    )
    cards: list[str] = []
    for name in card_order:
        b = bat_rows.get(name)
        if not b:
            continue
        bw = bowl_rows.get(name) or {
            "overs": "0",
            "runs": "0",
            "wkts": "0",
            "eco_cls": "",
            "eco": "0.0",
            "dots": "0",
        }
        catches, run_outs = field_rows.get(name, ("0", "0"))
        eco_cls = f' class="psv {bw["eco_cls"]}"' if bw["eco_cls"] else ' class="psv"'
        cards.append(
            f'      <div class="pc"><div class="pnb">{name} <span>ECC</span></div>\n'
            '        <div class="pss"><div class="psst"><span><img src="icons/batsman_dark.png" style="width:18px;height:18px;vertical-align:middle;" alt="bat"></span> Batting</div>\n'
            f'          <div class="psr"><span class="psl">Inn</span><span class="psv">{b["inn"]}</span></div>\n'
            f'          <div class="psr"><span class="psl">Bat Runs</span><span class="psv">{b["runs"]}</span></div>\n'
            f'          <div class="psr"><span class="psl">Avg/Match</span><span class="psv">{b["avg_match"]}</span></div>\n'
            f'          <div class="psr"><span class="psl">Avg/Inn</span><span class="psv">{b["avg_inn"]}</span></div>\n'
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
    tab_pl_marker = '<div id="tab-pl" class="tab">'
    tab_pl_start = html.find(tab_pl_marker)
    if tab_pl_start == -1:
        raise SystemExit("tab-pl not found while patching player cards")
    tab_pl_open_end = html.find(">", tab_pl_start) + 1
    tab_pl_end = _find_matching_div_end(html, tab_pl_open_end)
    tab_pl_block = html[tab_pl_start:tab_pl_end]
    pgrid_marker = '<div class="pgrid">'
    pgrid_local = tab_pl_block.find(pgrid_marker)
    if pgrid_local == -1:
        raise SystemExit("pgrid not found while patching player cards")
    pgrid_start = tab_pl_start + pgrid_local
    pgrid_open_end = html.find(">", pgrid_start) + 1
    pgrid_end = _find_matching_div_end(html, pgrid_open_end)
    pgrid_inner_end = pgrid_end - len("</div>")
    html = html[:pgrid_open_end] + "\n" + cards_html + "\n    " + html[pgrid_inner_end:]
    return html


def main() -> None:
    lookup = _build_innings_lookup()
    html = INDEX.read_text(encoding="utf-8")
    full_season = collect_summary_season(html)
    from patch_m7_overview import _replace_bowling_table_from_source  # noqa: WPS433

    html = _replace_bowling_table_from_source(html, full_season)
    season = full_season.batting
    html = patch_match_summaries(html, lookup)
    html = patch_players_tab(html, season)
    html = patch_leaders_tab(html, season)
    html = patch_player_cards(html, season)
    from patch_m7_overview import (  # noqa: WPS433
        _replace_best_economy_card,
        derive_shared_leaderboards as _derive_leaders,
    )

    leaders = _derive_leaders(full_season)
    html = _replace_best_economy_card(html, leaders)
    from patch_index import fix_tab_lb_boundary, fix_tab_mx_boundary, fix_tab_pl_boundary  # noqa: WPS433

    html = fix_tab_mx_boundary(html)
    html = fix_tab_lb_boundary(html)
    html = fix_tab_pl_boundary(html)
    INDEX.write_text(html, encoding="utf-8")
    print(f"Patched strike rates in {INDEX}")


if __name__ == "__main__":
    main()
