#!/usr/bin/env python3
"""Integrate M6 results into overview, player stats, and leaderboards in index.html."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"

NEXT_MATCH = (
    '  <div class="nm"><div class="nmi">&#128197;</div>'
    '<div class="nminfo"><h3>Next Match &mdash; 21 Jun 2026</h3>'
    "<p>&#127968; Edgware vs H Manor &nbsp;&middot;&nbsp; Home &nbsp;&middot;&nbsp; "
    "Canons High School &nbsp;&middot;&nbsp; 09:00 / 10:00 AM</p></div></div>"
)

OVERVIEW_STATS = """  <div class="sgrid">
    <div class="sbox"><div class="v">6</div><div class="l">Played</div></div>
    <div class="sbox win"><div class="v">5</div><div class="l">Wins</div></div>
    <div class="sbox loss"><div class="v">1</div><div class="l">Losses</div></div>
    <div class="sbox"><div class="v">0</div><div class="l">Draws</div></div>
    <div class="sbox"><div class="v">315</div><div class="l">Highest Score</div></div>
    <div class="sbox"><div class="v">+45</div><div class="l">Best Win Margin</div></div>
  </div>"""

PLAYERS_NOTE = (
    '<p style="font-size:.8rem;color:var(--mgrey);margin-bottom:16px;">'
    "Based on M2, M4, M5 &amp; M6 (M1 &amp; M3 walkovers). "
    "Net Runs = Bat Runs &minus; 5 per wicket lost. Avg = Bat Runs &divide; Innings.</p>"
)

BAT_TABLE_BODY = """        <tr><td><strong>Ariyan</strong></td><td class="c">4</td><td class="c">4</td><td class="c">34</td><td class="c">8.5</td><td class="c">83.9</td><td class="c">11</td><td class="c">4</td><td class="c">0</td><td class="c np">+19</td></tr>
        <tr><td><strong>Qaim</strong></td><td class="c">4</td><td class="c">4</td><td class="c">33</td><td class="c">8.3</td><td class="c">75.0</td><td class="c">13</td><td class="c">5</td><td class="c">0</td><td class="c np">+13</td></tr>
        <tr><td><strong>Veer</strong></td><td class="c">4</td><td class="c">4</td><td class="c">26</td><td class="c">6.5</td><td class="c">83.9</td><td class="c">10</td><td class="c">1</td><td class="c">0</td><td class="c np">+16</td></tr>
        <tr><td><strong>Avyaan</strong></td><td class="c">4</td><td class="c">4</td><td class="c">23</td><td class="c">5.8</td><td class="c">53.7</td><td class="c">9</td><td class="c">1</td><td class="c">1</td><td class="c np">+18</td></tr>
        <tr><td><strong>Kaiyan</strong></td><td class="c">3</td><td class="c">3</td><td class="c">20</td><td class="c">6.7</td><td class="c">14</td><td class="c">3</td><td class="c">0</td><td class="c np">+15</td></tr>
        <tr><td><strong>Viaan</strong></td><td class="c">3</td><td class="c">3</td><td class="c">18</td><td class="c">6.0</td><td class="c">11</td><td class="c">2</td><td class="c">0</td><td class="c np">+13</td></tr>
        <tr><td><strong>Krish</strong></td><td class="c">3</td><td class="c">3</td><td class="c">17</td><td class="c">5.7</td><td class="c">9</td><td class="c">0</td><td class="c">0</td><td class="c nn">&minus;8</td></tr>
        <tr><td><strong>Taran</strong></td><td class="c">2</td><td class="c">2</td><td class="c">12</td><td class="c">6.0</td><td class="c">7</td><td class="c">1</td><td class="c">0</td><td class="c np">+2</td></tr>
        <tr><td><strong>Drish</strong></td><td class="c">3</td><td class="c">3</td><td class="c">12</td><td class="c">4.0</td><td class="c">5</td><td class="c">1</td><td class="c">0</td><td class="c np">+7</td></tr>
        <tr><td><strong>Shyam</strong></td><td class="c">3</td><td class="c">3</td><td class="c">9</td><td class="c">3.0</td><td class="c">5</td><td class="c">1</td><td class="c">0</td><td class="c nn">&minus;11</td></tr>
        <tr><td><strong>Aanya</strong></td><td class="c">3</td><td class="c">3</td><td class="c">5</td><td class="c">1.7</td><td class="c">3</td><td class="c">0</td><td class="c">0</td><td class="c nn">&minus;10</td></tr>"""

BOWL_TABLE_BODY = """        <tr><td><strong>Avyaan</strong></td><td class="c">4</td><td class="c">8</td><td class="c">36</td><td class="c"><strong>3</strong></td><td class="c">8</td><td class="c">5</td><td class="c">4.5</td><td class="c">23</td></tr>
        <tr><td><strong>Qaim</strong></td><td class="c">4</td><td class="c">8</td><td class="c">66</td><td class="c"><strong>3</strong></td><td class="c">6</td><td class="c">1</td><td class="c eco-bad">8.2</td><td class="c">17</td></tr>
        <tr><td><strong>Veer</strong></td><td class="c">4</td><td class="c">8</td><td class="c">49</td><td class="c"><strong>2</strong></td><td class="c">5</td><td class="c">0</td><td class="c">6.1</td><td class="c">13</td></tr>
        <tr><td><strong>Krish</strong></td><td class="c">3</td><td class="c">6</td><td class="c">22</td><td class="c"><strong>3</strong></td><td class="c">3</td><td class="c">0</td><td class="c eco-good">3.7</td><td class="c"><strong>19</strong></td></tr>
        <tr><td><strong>Aanya</strong></td><td class="c">3</td><td class="c">6</td><td class="c">27</td><td class="c"><strong>2</strong></td><td class="c">3</td><td class="c">2</td><td class="c">4.5</td><td class="c">14</td></tr>
        <tr><td><strong>Kaiyan</strong></td><td class="c">3</td><td class="c">6</td><td class="c">40</td><td class="c"><strong>2</strong></td><td class="c">3</td><td class="c">2</td><td class="c">6.7</td><td class="c">16</td></tr>
        <tr><td><strong>Shyam</strong></td><td class="c">3</td><td class="c">6</td><td class="c">43</td><td class="c"><strong>2</strong></td><td class="c">4</td><td class="c">3</td><td class="c eco-bad">7.2</td><td class="c">16</td></tr>
        <tr><td><strong>Ariyan</strong></td><td class="c">4</td><td class="c">8</td><td class="c">39</td><td class="c"><strong>1</strong></td><td class="c">4</td><td class="c">2</td><td class="c">4.9</td><td class="c"><strong>25</strong></td></tr>
        <tr><td><strong>Viaan</strong></td><td class="c">3</td><td class="c">6</td><td class="c">31</td><td class="c">0</td><td class="c">4</td><td class="c">2</td><td class="c">5.2</td><td class="c">19</td></tr>
        <tr><td><strong>Drish</strong></td><td class="c">3</td><td class="c">6</td><td class="c">36</td><td class="c">0</td><td class="c">4</td><td class="c">2</td><td class="c">6.0</td><td class="c">11</td></tr>
        <tr><td><strong>Taran</strong></td><td class="c">2</td><td class="c">4</td><td class="c">29</td><td class="c"><strong>1</strong></td><td class="c">1</td><td class="c">0</td><td class="c eco-bad">7.2</td><td class="c">4</td></tr>"""

FIELD_TABLE_BODY = """        <tr><td><strong>Avyaan</strong></td><td class="c">4</td><td class="c">0</td><td class="c"><strong>3</strong></td></tr>
        <tr><td><strong>Qaim</strong></td><td class="c">4</td><td class="c">0</td><td class="c"><strong>2</strong></td></tr>
        <tr><td><strong>Viaan</strong></td><td class="c">3</td><td class="c">0</td><td class="c"><strong>1</strong></td></tr>
        <tr><td><strong>Taran</strong></td><td class="c">2</td><td class="c"><strong>1</strong></td><td class="c"><strong>1</strong></td></tr>
        <tr><td><strong>Shyam</strong></td><td class="c">3</td><td class="c"><strong>1</strong></td><td class="c">0</td></tr>
        <tr><td><strong>Ariyan</strong></td><td class="c">4</td><td class="c">0</td><td class="c"><strong>1</strong></td></tr>
        <tr><td><strong>Krish</strong></td><td class="c">3</td><td class="c">0</td><td class="c"><strong>1</strong></td></tr>"""

LEADERS_NOTE = (
    '<p style="font-size:.8rem;color:var(--mgrey);margin-bottom:16px;">'
    "Based on 4 played matches (M2 vs H Manor, M4 vs Hayes, M5 vs Harefield, M6 vs Pinner). "
    "M1 &amp; M3 walkovers. Updated after each match.</p>"
)

# Top Strike Rates card is inserted by patch_strike_rate.py (before Most Fours).
LEADERS_GRID = """    <div class="lbg">
      <div class="lbc"><div class="lbh"><img src="icons/batsman_light.png" style="width:18px;height:18px;vertical-align:middle;" alt="bat"> Most Bat Runs</div>
        <div class="lbr"><div class="lbrk r1">1</div><div class="lbn">Ariyan</div><div class="lbv">34</div></div>
        <div class="lbr"><div class="lbrk r2">2</div><div class="lbn">Qaim</div><div class="lbv">33</div></div>
        <div class="lbr"><div class="lbrk r3">3</div><div class="lbn">Veer</div><div class="lbv">26</div></div>
        <div class="lbr"><div class="lbrk rn">4</div><div class="lbn">Avyaan</div><div class="lbv">23</div></div>
        <div class="lbr"><div class="lbrk rn">5</div><div class="lbn">Kaiyan</div><div class="lbv">20</div></div></div>
      <div class="lbc"><div class="lbh">&#127775; Highest Score (single match)</div>
        <div class="lbr"><div class="lbrk r1">1</div><div class="lbn">Kaiyan</div><div class="lbv">14</div></div>
        <div class="lbr"><div class="lbrk r2">2</div><div class="lbn">Qaim</div><div class="lbv">13</div></div>
        <div class="lbr"><div class="lbrk r3">3</div><div class="lbn">Ariyan</div><div class="lbv">11</div></div>
        <div class="lbr"><div class="lbrk rn">4</div><div class="lbn">Viaan</div><div class="lbv">11</div></div>
        <div class="lbr"><div class="lbrk rn">5</div><div class="lbn">Veer</div><div class="lbv">10</div></div></div>
      <div class="lbc"><div class="lbh">&#127942; Best Net Runs</div>
        <div class="lbr"><div class="lbrk r1">1</div><div class="lbn">Ariyan</div><div class="lbv">+19</div></div>
        <div class="lbr"><div class="lbrk r2">2</div><div class="lbn">Avyaan</div><div class="lbv">+18</div></div>
        <div class="lbr"><div class="lbrk r3">3</div><div class="lbn">Veer</div><div class="lbv">+16</div></div>
        <div class="lbr"><div class="lbrk rn">4</div><div class="lbn">Kaiyan</div><div class="lbv">+15</div></div>
        <div class="lbr"><div class="lbrk rn">5</div><div class="lbn">Viaan</div><div class="lbv">+13</div></div></div>
      <div class="lbc"><div class="lbh"><img src="icons/ball_light.png" style="width:18px;height:18px;vertical-align:middle;" alt="ball"> Most Wickets</div>
        <div class="lbr"><div class="lbrk r1">1</div><div class="lbn">Avyaan</div><div class="lbv">3</div></div>
        <div class="lbr"><div class="lbrk r1">1</div><div class="lbn">Qaim</div><div class="lbv">3</div></div>
        <div class="lbr"><div class="lbrk r1">1</div><div class="lbn">Krish</div><div class="lbv">3</div></div>
        <div class="lbr"><div class="lbrk rn">4</div><div class="lbn">Veer</div><div class="lbv">2</div></div>
        <div class="lbr"><div class="lbrk rn">4</div><div class="lbn">Kaiyan</div><div class="lbv">2</div></div></div>
      <div class="lbc"><div class="lbh">&#128308; Most Fours</div>
        <div class="lbr"><div class="lbrk r1">1</div><div class="lbn">Qaim</div><div class="lbv">5</div></div>
        <div class="lbr"><div class="lbrk r2">2</div><div class="lbn">Ariyan</div><div class="lbv">4</div></div>
        <div class="lbr"><div class="lbrk r3">3</div><div class="lbn">Kaiyan</div><div class="lbv">3</div></div>
        <div class="lbr"><div class="lbrk rn">4</div><div class="lbn">Viaan</div><div class="lbv">2</div></div>
        <div class="lbr"><div class="lbrk rn">5</div><div class="lbn">Veer</div><div class="lbv">1</div></div></div>
      <div class="lbc"><div class="lbh">&#128200; Best Economy (min 2 overs)</div>
        <div class="lbr"><div class="lbrk r1">1</div><div class="lbn">Krish</div><div class="lbv">3.7</div></div>
        <div class="lbr"><div class="lbrk r2">2</div><div class="lbn">Avyaan</div><div class="lbv">4.5</div></div>
        <div class="lbr"><div class="lbrk r3">3</div><div class="lbn">Aanya</div><div class="lbv">4.5</div></div>
        <div class="lbr"><div class="lbrk rn">4</div><div class="lbn">Ariyan</div><div class="lbv">4.9</div></div>
        <div class="lbr"><div class="lbrk rn">5</div><div class="lbn">Viaan</div><div class="lbv">5.2</div></div></div>
      <div class="lbc"><div class="lbh">&#128308; Most Dot Balls</div>
        <div class="lbr"><div class="lbrk r1">1</div><div class="lbn">Ariyan</div><div class="lbv">25</div></div>
        <div class="lbr"><div class="lbrk r2">2</div><div class="lbn">Avyaan</div><div class="lbv">23</div></div>
        <div class="lbr"><div class="lbrk r3">3</div><div class="lbn">Krish</div><div class="lbv">19</div></div>
        <div class="lbr"><div class="lbrk rn">4</div><div class="lbn">Viaan</div><div class="lbv">19</div></div>
        <div class="lbr"><div class="lbrk rn">5</div><div class="lbn">Aanya</div><div class="lbv">14</div></div></div>
      <div class="lbc"><div class="lbh">&#129309; Best Partnerships (ECC)</div>
        <div class="lbr"><div class="lbrk r1">1</div><div class="lbn">Avyaan &amp; Taran <span style="font-size:.7rem;color:var(--mgrey);font-weight:400;">M5</span></div><div class="lbv">+32</div></div>
        <div class="lbr"><div class="lbrk r2">2</div><div class="lbn">Shyam &amp; Viaan <span style="font-size:.7rem;color:var(--mgrey);font-weight:400;">M6</span></div><div class="lbv">+30</div></div>
        <div class="lbr"><div class="lbrk r3">3</div><div class="lbn">Qaim &amp; Krish <span style="font-size:.7rem;color:var(--mgrey);font-weight:400;">M5</span></div><div class="lbv">+29</div></div>
        <div class="lbr"><div class="lbrk rn">4</div><div class="lbn">Shyam &amp; Drish <span style="font-size:.7rem;color:var(--mgrey);font-weight:400;">M5</span></div><div class="lbv">+27</div></div>
        <div class="lbr"><div class="lbrk rn">5</div><div class="lbn">Ariyan &amp; Viaan <span style="font-size:.7rem;color:var(--mgrey);font-weight:400;">M5</span></div><div class="lbv">+19</div></div></div>
      <div class="lbc"><div class="lbh"><img src="icons/fielder_light.png" style="width:18px;height:18px;vertical-align:middle;" alt="field"> Most Catches</div>
        <div class="lbr"><div class="lbrk r1">1</div><div class="lbn">Taran</div><div class="lbv">1</div></div>
        <div class="lbr"><div class="lbrk r1">1</div><div class="lbn">Shyam</div><div class="lbv">1</div></div></div>
      <div class="lbc"><div class="lbh"><img src="icons/fielder_light.png" style="width:18px;height:18px;vertical-align:middle;" alt="field"> Most Run Outs</div>
        <div class="lbr"><div class="lbrk r1">1</div><div class="lbn">Avyaan</div><div class="lbv">3</div></div>
        <div class="lbr"><div class="lbrk r2">2</div><div class="lbn">Qaim</div><div class="lbv">2</div></div>
        <div class="lbr"><div class="lbrk r3">3</div><div class="lbn">Ariyan</div><div class="lbv">1</div></div>
        <div class="lbr"><div class="lbrk r3">3</div><div class="lbn">Viaan</div><div class="lbv">1</div></div>
        <div class="lbr"><div class="lbrk r3">3</div><div class="lbn">Krish</div><div class="lbv">1</div></div></div>
    </div>"""

# Player card snippets — batting / bowling / fielding lines only
PLAYER_CARD_UPDATES: dict[str, dict[str, str]] = {
    "Ariyan": {
        "bat": """          <div class="psr"><span class="psl">Inn</span><span class="psv">4</span></div>
          <div class="psr"><span class="psl">Bat Runs / Avg</span><span class="psv">34 / 8.5</span></div>
          <div class="psr"><span class="psl">4s / 6s</span><span class="psv">4 / 0</span></div>
          <div class="psr"><span class="psl">Net Runs</span><span class="psv np">+19</span></div>""",
        "bowl": """          <div class="psr"><span class="psl">Overs / Wkts</span><span class="psv">8 / 1</span></div>
          <div class="psr"><span class="psl">Runs / ECO</span><span class="psv">39 / 4.9</span></div>
          <div class="psr"><span class="psl">Dots</span><span class="psv">25</span></div>""",
        "field": """        <div class="pss"><div class="psst"><span><img src="icons/fielding-role.png" style="width:18px;height:18px;vertical-align:middle;" alt="field"></span> Fielding</div>
          <div class="psr"><span class="psl">Run Outs</span><span class="psv">1</span></div></div>""",
    },
    "Avyaan": {
        "bat": """          <div class="psr"><span class="psl">Inn</span><span class="psv">4</span></div>
          <div class="psr"><span class="psl">Bat Runs / Avg</span><span class="psv">23 / 5.8</span></div>
          <div class="psr"><span class="psl">4s / 6s</span><span class="psv">1 / 1</span></div>
          <div class="psr"><span class="psl">Net Runs</span><span class="psv np">+18</span></div>""",
        "bowl": """          <div class="psr"><span class="psl">Overs / Wkts</span><span class="psv">8 / 3</span></div>
          <div class="psr"><span class="psl">Runs / ECO</span><span class="psv">36 / 4.5</span></div>
          <div class="psr"><span class="psl">Dots</span><span class="psv">23</span></div>""",
        "field": """        <div class="pss"><div class="psst"><span><img src="icons/fielding-role.png" style="width:18px;height:18px;vertical-align:middle;" alt="field"></span> Fielding</div>
          <div class="psr"><span class="psl">Run Outs</span><span class="psv">3</span></div></div>""",
    },
    "Veer": {
        "bat": """          <div class="psr"><span class="psl">Inn</span><span class="psv">4</span></div>
          <div class="psr"><span class="psl">Bat Runs / Avg</span><span class="psv">26 / 6.5</span></div>
          <div class="psr"><span class="psl">4s / 6s</span><span class="psv">1 / 0</span></div>
          <div class="psr"><span class="psl">Net Runs</span><span class="psv np">+16</span></div>""",
        "bowl": """          <div class="psr"><span class="psl">Overs / Wkts</span><span class="psv">8 / 2</span></div>
          <div class="psr"><span class="psl">Runs / ECO</span><span class="psv">49 / 6.1</span></div>
          <div class="psr"><span class="psl">Dots</span><span class="psv">13</span></div>""",
    },
    "Kaiyan": {
        "bat": """          <div class="psr"><span class="psl">Inn</span><span class="psv">3</span></div>
          <div class="psr"><span class="psl">Bat Runs / Avg</span><span class="psv">20 / 6.7</span></div>
          <div class="psr"><span class="psl">4s / 6s</span><span class="psv">3 / 0</span></div>
          <div class="psr"><span class="psl">Net Runs</span><span class="psv np">+15</span></div>""",
        "bowl": """          <div class="psr"><span class="psl">Overs / Wkts</span><span class="psv">6 / 2</span></div>
          <div class="psr"><span class="psl">Runs / ECO</span><span class="psv">40 / 6.7</span></div>
          <div class="psr"><span class="psl">Dots</span><span class="psv">16</span></div>""",
    },
    "Qaim": {
        "bat": """          <div class="psr"><span class="psl">Inn</span><span class="psv">4</span></div>
          <div class="psr"><span class="psl">Bat Runs / Avg</span><span class="psv">33 / 8.3</span></div>
          <div class="psr"><span class="psl">4s / 6s</span><span class="psv">5 / 0</span></div>
          <div class="psr"><span class="psl">Net Runs</span><span class="psv np">+13</span></div>""",
        "bowl": """          <div class="psr"><span class="psl">Overs / Wkts</span><span class="psv">8 / 3</span></div>
          <div class="psr"><span class="psl">Runs / ECO</span><span class="psv eco-bad">66 / 8.2</span></div>
          <div class="psr"><span class="psl">Dots</span><span class="psv">17</span></div>""",
        "field": """        <div class="pss"><div class="psst"><span><img src="icons/fielding-role.png" style="width:18px;height:18px;vertical-align:middle;" alt="field"></span> Fielding</div>
          <div class="psr"><span class="psl">Run Outs</span><span class="psv">2</span></div></div>""",
    },
    "Viaan": {
        "bat": """          <div class="psr"><span class="psl">Inn</span><span class="psv">3</span></div>
          <div class="psr"><span class="psl">Bat Runs / Avg</span><span class="psv">18 / 6.0</span></div>
          <div class="psr"><span class="psl">4s / 6s</span><span class="psv">2 / 0</span></div>
          <div class="psr"><span class="psl">Net Runs</span><span class="psv np">+13</span></div>""",
        "bowl": """          <div class="psr"><span class="psl">Overs / Wkts</span><span class="psv">6 / 0</span></div>
          <div class="psr"><span class="psl">Runs / ECO</span><span class="psv">31 / 5.2</span></div>
          <div class="psr"><span class="psl">Dots</span><span class="psv">19</span></div>""",
        "field": """        <div class="pss"><div class="psst"><span><img src="icons/fielding-role.png" style="width:18px;height:18px;vertical-align:middle;" alt="field"></span> Fielding</div>
          <div class="psr"><span class="psl">Run Outs</span><span class="psv">1</span></div></div>""",
    },
    "Drish": {
        "bat": """          <div class="psr"><span class="psl">Inn</span><span class="psv">3</span></div>
          <div class="psr"><span class="psl">Bat Runs / Avg</span><span class="psv">12 / 4.0</span></div>
          <div class="psr"><span class="psl">4s / 6s</span><span class="psv">1 / 0</span></div>
          <div class="psr"><span class="psl">Net Runs</span><span class="psv np">+7</span></div>""",
        "bowl": """          <div class="psr"><span class="psl">Overs / Wkts</span><span class="psv">6 / 0</span></div>
          <div class="psr"><span class="psl">Runs / ECO</span><span class="psv">36 / 6.0</span></div>
          <div class="psr"><span class="psl">Dots</span><span class="psv">11</span></div>""",
    },
    "Shyam": {
        "bat": """          <div class="psr"><span class="psl">Inn</span><span class="psv">3</span></div>
          <div class="psr"><span class="psl">Bat Runs / Avg</span><span class="psv">9 / 3.0</span></div>
          <div class="psr"><span class="psl">4s / 6s</span><span class="psv">1 / 0</span></div>
          <div class="psr"><span class="psl">Net Runs</span><span class="psv nn">&minus;11</span></div>""",
        "bowl": """          <div class="psr"><span class="psl">Overs / Wkts</span><span class="psv">6 / 2</span></div>
          <div class="psr"><span class="psl">Runs / ECO</span><span class="psv eco-bad">43 / 7.2</span></div>
          <div class="psr"><span class="psl">Dots</span><span class="psv">16</span></div>""",
    },
}


def _replace_table_body(html: str, header_marker: str, new_body: str) -> str:
    pattern = re.compile(
        rf"(<thead>{re.escape(header_marker)}</thead>\s*<tbody>\s*).*?(</tbody>)",
        re.DOTALL,
    )
    out, n = pattern.subn(rf"\1\n{new_body}\n      \2", html, count=1)
    if n != 1:
        raise SystemExit(f"Table body not found for: {header_marker[:40]}...")
    return out


def _extract_player_card_block(html: str, name: str) -> tuple[int, int, str]:
    marker = f'<div class="pc"><div class="pnb">{name} <span>ECC</span></div>'
    start = html.find(marker)
    if start == -1:
        raise SystemExit(f"Player card not found: {name}")
    rest = html[start:]
    depth = 0
    i = 0
    while i < len(rest):
        if rest.startswith("<div", i):
            depth += 1
            i = rest.find(">", i) + 1
        elif rest.startswith("</div>", i):
            depth -= 1
            i += 6
            if depth == 0:
                return start, start + i, rest[:i]
        else:
            i += 1
    raise SystemExit(f"Unclosed player card: {name}")


def _update_player_card(html: str, name: str, updates: dict[str, str]) -> str:
    start, end, block = _extract_player_card_block(html, name)

    bat_pat = re.compile(
        r'(<div class="pss"><div class="psst"><span><img src="icons/batsman[^"]*\.png"[^>]*></span> Batting</div>\n)(.*?)(</div>\s*\n        <div class="pss"><div class="psst"><span><img src="icons/cricket-ball)',
        re.DOTALL,
    )
    bowl_pat = re.compile(
        r'(<div class="pss"><div class="psst"><span><img src="icons/cricket-ball[^"]*\.png"[^>]*></span> Bowling</div>\n)(.*?)'
        r'(</div>\s*(?=\n        <div class="pss"><div class="psst"><span><img src="icons/fielding-role'
        r'|\n      <div class="pc">|</div>\s*$))',
        re.DOTALL,
    )
    field_pat = re.compile(
        r'<div class="pss"><div class="psst"><span><img src="icons/fielding-role\.png"[^>]*></span> Fielding</div>\n\s*<div class="psr">.*?</div>\s*</div>',
        re.DOTALL,
    )

    if "bat" in updates:
        m = bat_pat.search(block)
        if not m:
            raise SystemExit(f"Batting section not found for {name}")
        block = block[: m.start(2)] + updates["bat"] + block[m.end(2) :]

    if "bowl" in updates:
        m = bowl_pat.search(block)
        if not m:
            raise SystemExit(f"Bowling section not found for {name}")
        block = block[: m.start(2)] + updates["bowl"] + block[m.end(2) :]

    if "field" in updates:
        if field_pat.search(block):
            block = field_pat.sub(updates["field"].strip(), block, count=1)
        else:
            insert_at = block.rfind("</div></div>")
            block = block[:insert_at] + "\n" + updates["field"] + "\n" + block[insert_at:]

    return html[:start] + block + html[end:]


def patch_overview(html: str) -> str:
    html = html.replace(
        '<h3>Next Match &mdash; 14 Jun 2026</h3><p>&#9992;&#65039; Pinner vs Edgware &nbsp;&middot;&nbsp; Away &nbsp;&middot;&nbsp; Pinner &nbsp;&middot;&nbsp; 09:00 / 10:00 AM</p>',
        '<h3>Next Match &mdash; 21 Jun 2026</h3><p>&#127968; Edgware vs H Manor &nbsp;&middot;&nbsp; Home &nbsp;&middot;&nbsp; Canons High School &nbsp;&middot;&nbsp; 09:00 / 10:00 AM</p>',
        1,
    )
    for old_margin in ("+32", "+45"):
        html = html.replace(
            f'<div class="sbox"><div class="v">5</div><div class="l">Played</div></div>\n'
            '    <div class="sbox win"><div class="v">4</div><div class="l">Wins</div></div>\n'
            '    <div class="sbox loss"><div class="v">1</div><div class="l">Losses</div></div>\n'
            '    <div class="sbox"><div class="v">0</div><div class="l">Draws</div></div>\n'
            '    <div class="sbox"><div class="v">315</div><div class="l">Highest Score</div></div>\n'
            f'    <div class="sbox"><div class="v">{old_margin}</div><div class="l">Best Win Margin</div></div>',
            '<div class="sbox"><div class="v">6</div><div class="l">Played</div></div>\n'
            '    <div class="sbox win"><div class="v">5</div><div class="l">Wins</div></div>\n'
            '    <div class="sbox loss"><div class="v">1</div><div class="l">Losses</div></div>\n'
            '    <div class="sbox"><div class="v">0</div><div class="l">Draws</div></div>\n'
            '    <div class="sbox"><div class="v">315</div><div class="l">Highest Score</div></div>\n'
            '    <div class="sbox"><div class="v">+45</div><div class="l">Best Win Margin</div></div>',
            1,
        )
    return html


def patch_players(html: str) -> str:
    if "Based on M2, M4, M5 &amp; M6" not in html:
        html = html.replace(
            '<p style="font-size:.8rem;color:var(--mgrey);margin-bottom:16px;">Based on M2, M4 &amp; M5 (M1 &amp; M3 walkovers). Net Runs = Bat Runs &minus; 5 per wicket lost. Avg = Bat Runs &divide; Innings.</p>',
            PLAYERS_NOTE,
            1,
        )
    html = _replace_table_body(
        html,
        '<tr><th>Batter</th><th class="c">M</th><th class="c">Inn</th><th class="c">Bat Runs</th><th class="c">Avg</th><th class="c">SR</th><th class="c">HS</th><th class="c">4s</th><th class="c">6s</th><th class="c">Net Runs</th></tr>',
        BAT_TABLE_BODY,
    )
    html = _replace_table_body(
        html,
        '<tr><th>Bowler</th><th class="c">M</th><th class="c">O</th><th class="c">R</th><th class="c">W</th><th class="c">WD</th><th class="c">NB</th><th class="c">ECO</th><th class="c">Dots</th></tr>',
        BOWL_TABLE_BODY,
    )
    html = _replace_table_body(
        html,
        '<tr><th>Fielder</th><th class="c">M</th><th class="c">Catches</th><th class="c">Run Outs</th></tr>',
        FIELD_TABLE_BODY,
    )
    for name, updates in PLAYER_CARD_UPDATES.items():
        html = _update_player_card(html, name, updates)
    return html


# (name, match label, six count) — show Most Sixes board only when len >= 2
SIX_HITTER_LEADER_ROWS: list[tuple[str, str, int]] = [
    ("Avyaan", "M6", 1),
]

MOST_SIXES_BEFORE_ECONOMY = (
    '        <div class="lbr"><div class="lbrk rn">5</div><div class="lbn">Veer</div><div class="lbv">1</div></div></div>\n'
    '      <div class="lbc"><div class="lbh">&#128200; Best Economy (min 2 overs)</div>'
)

BEST_ECONOMY_CARD = """      <div class="lbc"><div class="lbh">&#128200; Best Economy (min 2 overs)</div>
        <div class="lbr"><div class="lbrk r1">1</div><div class="lbn">Krish</div><div class="lbv">3.7</div></div>
        <div class="lbr"><div class="lbrk r2">2</div><div class="lbn">Avyaan</div><div class="lbv">4.5</div></div>
        <div class="lbr"><div class="lbrk r3">3</div><div class="lbn">Aanya</div><div class="lbv">4.5</div></div>
        <div class="lbr"><div class="lbrk rn">4</div><div class="lbn">Ariyan</div><div class="lbv">4.9</div></div>
        <div class="lbr"><div class="lbrk rn">5</div><div class="lbn">Viaan</div><div class="lbv">5.2</div></div></div>"""


def _most_sixes_block(rows: list[tuple[str, str, int]]) -> str:
    lines = ['      <div class="lbc"><div class="lbh">&#127919; Most Sixes</div>']
    for i, (name, match, count) in enumerate(rows[:5]):
        rank = f"r{i + 1}" if i < 3 else "rn"
        match_tag = (
            f' <span style="font-size:.7rem;color:var(--mgrey);font-weight:400;">{match}</span>'
            if match
            else ""
        )
        lines.append(
            f'        <div class="lbr"><div class="lbrk {rank}">{i + 1}</div>'
            f'<div class="lbn">{name}{match_tag}</div><div class="lbv">{count}</div></div>'
        )
    lines.append("</div>")
    return "\n".join(lines)


def patch_most_sixes(html: str) -> str:
    html = re.sub(
        r'\n\s*<div class="lbc"><div class="lbh">&#127919; Most Sixes</div>.*?</div>\n',
        "\n",
        html,
        count=1,
        flags=re.DOTALL,
    )
    if len(SIX_HITTER_LEADER_ROWS) < 2 or MOST_SIXES_BEFORE_ECONOMY not in html:
        return html
    return html.replace(
        MOST_SIXES_BEFORE_ECONOMY,
        '        <div class="lbr"><div class="lbrk rn">5</div><div class="lbn">Veer</div><div class="lbv">1</div></div></div>\n'
        + _most_sixes_block(SIX_HITTER_LEADER_ROWS)
        + '\n      <div class="lbc"><div class="lbh">&#128200; Best Economy (min 2 overs)</div>',
        1,
    )


def patch_leaders(html: str) -> str:
    lb_start = html.find('id="tab-lb"')
    if lb_start == -1:
        raise SystemExit("tab-lb missing")
    segment = html[lb_start : html.find("<!-- RULES -->", lb_start)]
    card_count = segment.count('class="lbc"')
    needs_wickets_fix = "Krish</div><div class=\"lbv\">2</div></div>" in segment and "Veer</div><div class=\"lbv\">2</div></div>" not in segment
    needs_runouts_fix = (
        "Avyaan</div><div class=\"lbv\">4</div></div>" in segment
        or 'lbn">Viaan</div><div class="lbv">1</div></div>\n        <div class="lbr"><div class="lbrk rn">4' in segment
    )
    if card_count >= 10 and not needs_wickets_fix and not needs_runouts_fix:
        return html
    html = re.sub(
        r'(<div id="tab-lb" class="tab">\s*<div class="card">\s*<div class="ctitle">[^<]+</div>\s*)<p style="font-size:\.8rem;color:var\(--mgrey\);margin-bottom:16px;">.*?</p>(\s*<div class="lbg">).*?(</div>\s*</div>\s*</div>\s*\n\n<!-- RULES -->)',
        rf"\1{LEADERS_NOTE}\n{LEADERS_GRID}\4",
        html,
        count=1,
        flags=re.DOTALL,
    )
    html = re.sub(
        r'<div class="lbc"><div class="lbh">&#128200; Best Economy \(min 2 overs\)</div>.*?</div>\s*(?=<div class="lbc"><div class="lbh">&#128308; Most Dot Balls</div>)',
        BEST_ECONOMY_CARD,
        html,
        count=1,
        flags=re.DOTALL,
    )
    return html


def main() -> None:
    html = INDEX.read_text(encoding="utf-8")
    html = patch_overview(html)
    html = patch_players(html)
    html = patch_leaders(html)
    html = patch_most_sixes(html)
    from patch_index import fix_tab_pl_boundary

    html = fix_tab_pl_boundary(html)
    INDEX.write_text(html, encoding="utf-8")
    print(f"Updated overview, players, and leaders in {INDEX}")

    # Re-apply strike rates after table/card replacements (Players/Leaders lack SR in static templates).
    from patch_strike_rate import main as patch_strike_rate_main

    patch_strike_rate_main()


if __name__ == "__main__":
    main()
