#!/usr/bin/env python3
"""Mark M9 (Edgware vs Hayes, 12 Jul 2026) as walkover win for Edgware."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"

M9_BLOCK = """
  <div id="match-m9" class="md2">
    <div class="card">
      <div class="rbanner"><div class="rbm">&#127942; Edgware CC · WIN (Walkover)</div><div class="rbs">12 July 2026 &nbsp;&middot;&nbsp; Edgware vs Hayes &nbsp;&middot;&nbsp; Canons High School (Home)</div></div>
      <p style="text-align:center;color:var(--mgrey);font-size:.9rem;padding:20px 0;">Hayes conceded before the match. Edgware awarded the win.</p>
      <div style="text-align:center;"><a class="sl" href="#mx/m9">Walkover: no scorecard</a></div>
    </div>
  </div>
"""

REPLACEMENTS = [
    (
        '<div class="nm"><div class="nmi">&#128197;</div><div class="nminfo"><h3>Next Match · 12 Jul 2026</h3><p>&#127968; Edgware vs Hayes &nbsp;&middot;&nbsp; Home &nbsp;&middot;&nbsp; Canons High School &nbsp;&middot;&nbsp; 09:00 / 10:00 AM</p></div></div>',
        '<div class="nm"><div class="nmi">&#128197;</div><div class="nminfo"><h3>Next Match · 19 Jul 2026</h3><p>&#128205; H Manor vs Edgware &nbsp;&middot;&nbsp; Away &nbsp;&middot;&nbsp; Headstone Manor &nbsp;&middot;&nbsp; 09:00 / 10:00 AM</p></div></div>',
    ),
    (
        '<div class="sbox"><div class="v">8</div><div class="l">Played</div></div>\n    <div class="sbox win"><div class="v">7</div><div class="l">Wins</div></div>',
        '<div class="sbox"><div class="v">9</div><div class="l">Played</div></div>\n    <div class="sbox win"><div class="v">8</div><div class="l">Wins</div></div>',
    ),
    (
        '<tr><td>9</td><td>12 Jul</td><td>Edgware vs Hayes</td><td class="c"><span class="bdg home">Home</span></td><td class="c">-</td><td class="c">-</td><td class="c"><span class="bdg tbd">TBD</span></td><td class="c">-</td><td class="c"><a class="sl" href="#mx">&#128202; Scorecard</a></td></tr>',
        '<tr><td>9</td><td>12 Jul</td><td>Edgware vs Hayes</td><td class="c"><span class="bdg home">Home</span></td><td class="c">W/O</td><td class="c">W/O</td><td class="c"><span class="bdg wo">WIN</span></td><td class="c">Walkover (Hayes conceded)</td><td class="c"><a class="sl" href="#mx/m9">&#128202; Scorecard</a></td></tr>',
    ),
    (
        '<tr><td>9</td><td>12 Jul</td><td>Edgware vs Hayes</td><td class="c"><span class="bdg home">Home</span></td><td>Canons High School</td><td class="c"><span class="bdg tbd">TBD</span></td><td class="c"><a class="sl" href="#mx">&#128202;</a></td></tr>',
        '<tr><td>9</td><td>12 Jul</td><td>Edgware vs Hayes</td><td class="c"><span class="bdg home">Home</span></td><td>Canons High School</td><td class="c"><span class="bdg wo">WIN (Walkover)</span></td><td class="c"><a class="sl" href="#mx/m9">&#128202;</a></td></tr>',
    ),
    (
        '<button class="mtb" onclick="showMatch(\'m8\',this)">Harefield · 5 Jul &#127942;</button>\n  </div>',
        '<button class="mtb" onclick="showMatch(\'m8\',this)">Harefield · 5 Jul &#127942;</button>\n    <button class="mtb" onclick="showMatch(\'m9\',this)">Hayes · 12 Jul</button>\n  </div>',
    ),
    (
        "M1 &amp; M3 walkovers",
        "M1, M3 &amp; M9 walkovers",
    ),
    (
        "Based on 6 played matches (M2-M7 plus M8 vs Harefield). M1 &amp; M3 walkovers.",
        "Based on 6 played matches (M2-M7 plus M8 vs Harefield). M1, M3 &amp; M9 walkovers.",
    ),
]

INSERT_AFTER = "</div>\n</div>\n</div>\n\n<!-- PLAYERS -->"


def main() -> None:
    html = INDEX.read_text(encoding="utf-8")
    for old, new in REPLACEMENTS:
        if old not in html:
            raise SystemExit(f"patch target not found:\n{old[:120]}...")
        html = html.replace(old, new, 1)

    if 'id="match-m9"' in html:
        print("match-m9 already present, skipping block insert")
    else:
        if INSERT_AFTER not in html:
            raise SystemExit("insert anchor not found")
        html = html.replace(INSERT_AFTER, f"</div>\n</div>\n</div>\n{M9_BLOCK}\n\n<!-- PLAYERS -->", 1)

    INDEX.write_text(html, encoding="utf-8")
    print(f"Patched {INDEX}")


if __name__ == "__main__":
    main()
