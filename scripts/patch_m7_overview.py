#!/usr/bin/env python3
"""Integrate M7 results into overview, player stats, and leaderboards in index.html."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"

NEXT_MATCH = (
    '  <div class="nm"><div class="nmi">&#128197;</div>'
    '<div class="nminfo"><h3>Next Match &mdash; 5 Jul 2026</h3>'
    "<p>&#9992;&#65039; Harefield vs Edgware &nbsp;&middot;&nbsp; Away &nbsp;&middot;&nbsp; "
    "Harefield &nbsp;&middot;&nbsp; 09:00 / 10:00 AM</p></div></div>"
)

OVERVIEW_STATS = """  <div class="sgrid">
    <div class="sbox"><div class="v">7</div><div class="l">Played</div></div>
    <div class="sbox win"><div class="v">6</div><div class="l">Wins</div></div>
    <div class="sbox loss"><div class="v">1</div><div class="l">Losses</div></div>
    <div class="sbox"><div class="v">0</div><div class="l">Draws</div></div>
    <div class="sbox"><div class="v">315</div><div class="l">Highest Score</div></div>
    <div class="sbox"><div class="v">+61</div><div class="l">Best Win Margin</div></div>
  </div>"""

PLAYERS_NOTE = (
    '<p style="font-size:.8rem;color:var(--mgrey);margin-bottom:16px;">'
    "Based on M2, M4, M5, M6 &amp; M7 (M1 &amp; M3 walkovers). "
    "Net Runs = Bat Runs &minus; 5 per wicket lost. Avg = Bat Runs &divide; Innings. "
    "SR = runs &divide; balls faced &times; 100. Updated with M7 pressure-phase bowling and fielding highlights.</p>"
)

BAT_TABLE_BODY = """        <tr><td><strong>Qaim</strong></td><td class="c">5</td><td class="c">5</td><td class="c">42</td><td class="c">8.4</td><td class="c">75.0</td><td class="c">13</td><td class="c">6</td><td class="c">0</td><td class="c np">+22</td></tr>
        <tr><td><strong>Ariyan</strong></td><td class="c">4</td><td class="c">4</td><td class="c">34</td><td class="c">8.5</td><td class="c">83.9</td><td class="c">11</td><td class="c">4</td><td class="c">0</td><td class="c np">+19</td></tr>
        <tr><td><strong>Kaiyan</strong></td><td class="c">4</td><td class="c">4</td><td class="c">28</td><td class="c">7.0</td><td class="c">85.7</td><td class="c">14</td><td class="c">3</td><td class="c">0</td><td class="c np">+18</td></tr>
        <tr><td><strong>Veer</strong></td><td class="c">4</td><td class="c">4</td><td class="c">26</td><td class="c">6.5</td><td class="c">83.9</td><td class="c">10</td><td class="c">1</td><td class="c">0</td><td class="c np">+16</td></tr>
        <tr><td><strong>Avyaan</strong></td><td class="c">5</td><td class="c">5</td><td class="c">25</td><td class="c">5.0</td><td class="c">53.7</td><td class="c">9</td><td class="c">1</td><td class="c">1</td><td class="c np">+15</td></tr>
        <tr><td><strong>Krish</strong></td><td class="c">4</td><td class="c">4</td><td class="c">23</td><td class="c">5.8</td><td class="c">85.7</td><td class="c">9</td><td class="c">0</td><td class="c">0</td><td class="c nn">&minus;2</td></tr>
        <tr><td><strong>Viaan</strong></td><td class="c">3</td><td class="c">3</td><td class="c">18</td><td class="c">6.0</td><td class="c">85.7</td><td class="c">11</td><td class="c">2</td><td class="c">0</td><td class="c np">+13</td></tr>
        <tr><td><strong>Taran</strong></td><td class="c">3</td><td class="c">3</td><td class="c">18</td><td class="c">6.0</td><td class="c">85.7</td><td class="c">7</td><td class="c">1</td><td class="c">0</td><td class="c np">+8</td></tr>
        <tr><td><strong>Drish</strong></td><td class="c">4</td><td class="c">4</td><td class="c">17</td><td class="c">4.2</td><td class="c">85.7</td><td class="c">5</td><td class="c">1</td><td class="c">0</td><td class="c np">+7</td></tr>
        <tr><td><strong>Aanya</strong></td><td class="c">4</td><td class="c">4</td><td class="c">12</td><td class="c">3.0</td><td class="c">25.0</td><td class="c">7</td><td class="c">0</td><td class="c">0</td><td class="c nn">&minus;8</td></tr>
        <tr><td><strong>Shyam</strong></td><td class="c">4</td><td class="c">4</td><td class="c">11</td><td class="c">2.8</td><td class="c">85.7</td><td class="c">5</td><td class="c">1</td><td class="c">0</td><td class="c nn">&minus;9</td></tr>"""

BOWL_TABLE_BODY = """        <tr><td><strong>Krish</strong></td><td class="c">4</td><td class="c">8</td><td class="c">18</td><td class="c"><strong>6</strong></td><td class="c">3</td><td class="c">0</td><td class="c eco-good">2.2</td><td class="c"><strong>23</strong></td></tr>
        <tr><td><strong>Qaim</strong></td><td class="c">5</td><td class="c">10</td><td class="c">63</td><td class="c"><strong>5</strong></td><td class="c">6</td><td class="c">1</td><td class="c eco-bad">6.3</td><td class="c">24</td></tr>
        <tr><td><strong>Avyaan</strong></td><td class="c">5</td><td class="c">10</td><td class="c">46</td><td class="c"><strong>4</strong></td><td class="c">8</td><td class="c">6</td><td class="c">4.6</td><td class="c">26</td></tr>
        <tr><td><strong>Aanya</strong></td><td class="c">4</td><td class="c">8</td><td class="c">25</td><td class="c"><strong>2</strong></td><td class="c">3</td><td class="c">3</td><td class="c eco-good">3.1</td><td class="c">23</td></tr>
        <tr><td><strong>Kaiyan</strong></td><td class="c">4</td><td class="c">8</td><td class="c">45</td><td class="c"><strong>2</strong></td><td class="c">3</td><td class="c">2</td><td class="c">5.6</td><td class="c">23</td></tr>
        <tr><td><strong>Veer</strong></td><td class="c">4</td><td class="c">8</td><td class="c">49</td><td class="c"><strong>2</strong></td><td class="c">5</td><td class="c">0</td><td class="c">6.1</td><td class="c">13</td></tr>
        <tr><td><strong>Shyam</strong></td><td class="c">4</td><td class="c">8</td><td class="c">54</td><td class="c"><strong>2</strong></td><td class="c">4</td><td class="c">3</td><td class="c eco-bad">6.8</td><td class="c">22</td></tr>
        <tr><td><strong>Ariyan</strong></td><td class="c">4</td><td class="c">8</td><td class="c">39</td><td class="c"><strong>1</strong></td><td class="c">4</td><td class="c">2</td><td class="c">4.9</td><td class="c"><strong>25</strong></td></tr>
        <tr><td><strong>Taran</strong></td><td class="c">3</td><td class="c">6</td><td class="c">34</td><td class="c"><strong>1</strong></td><td class="c">1</td><td class="c">0</td><td class="c">5.7</td><td class="c">19</td></tr>
        <tr><td><strong>Viaan</strong></td><td class="c">3</td><td class="c">6</td><td class="c">31</td><td class="c">0</td><td class="c">4</td><td class="c">2</td><td class="c">5.2</td><td class="c">19</td></tr>
        <tr><td><strong>Drish</strong></td><td class="c">4</td><td class="c">8</td><td class="c">44</td><td class="c">0</td><td class="c">5</td><td class="c">2</td><td class="c">5.5</td><td class="c">17</td></tr>"""

FIELD_TABLE_BODY = """        <tr><td><strong>Avyaan</strong></td><td class="c">5</td><td class="c"><strong>2</strong></td><td class="c"><strong>3</strong></td></tr>
        <tr><td><strong>Qaim</strong></td><td class="c">5</td><td class="c"><strong>1</strong></td><td class="c"><strong>2</strong></td></tr>
        <tr><td><strong>Drish</strong></td><td class="c">4</td><td class="c"><strong>1</strong></td><td class="c"><strong>1</strong></td></tr>
        <tr><td><strong>Taran</strong></td><td class="c">3</td><td class="c"><strong>1</strong></td><td class="c"><strong>1</strong></td></tr>
        <tr><td><strong>Viaan</strong></td><td class="c">3</td><td class="c">0</td><td class="c"><strong>1</strong></td></tr>
        <tr><td><strong>Shyam</strong></td><td class="c">4</td><td class="c"><strong>1</strong></td><td class="c">0</td></tr>
        <tr><td><strong>Ariyan</strong></td><td class="c">4</td><td class="c">0</td><td class="c"><strong>1</strong></td></tr>
        <tr><td><strong>Krish</strong></td><td class="c">4</td><td class="c">0</td><td class="c"><strong>1</strong></td></tr>"""

LEADERS_NOTE = (
    '<p style="font-size:.8rem;color:var(--mgrey);margin-bottom:16px;">'
    "Based on 5 played matches (M2 vs H Manor, M4 vs Hayes, M5 vs Harefield, M6 vs Pinner, M7 vs H Manor). "
    "M1 &amp; M3 walkovers. Updated after each match with a positive focus on impact moments.</p>"
)

LEADERS_GRID = """    <div class="lbg">
      <div class="lbc"><div class="lbh"><img src="icons/batsman_light.png" style="width:18px;height:18px;vertical-align:middle;" alt="bat"> Most Bat Runs</div>
        <div class="lbr"><div class="lbrk r1">1</div><div class="lbn">Qaim</div><div class="lbv">42</div></div>
        <div class="lbr"><div class="lbrk r2">2</div><div class="lbn">Ariyan</div><div class="lbv">34</div></div>
        <div class="lbr"><div class="lbrk r3">3</div><div class="lbn">Kaiyan</div><div class="lbv">28</div></div>
        <div class="lbr"><div class="lbrk rn">4</div><div class="lbn">Veer</div><div class="lbv">26</div></div>
        <div class="lbr"><div class="lbrk rn">5</div><div class="lbn">Avyaan</div><div class="lbv">25</div></div></div>
      <div class="lbc"><div class="lbh">&#127775; Highest Score (single match)</div>
        <div class="lbr"><div class="lbrk r1">1</div><div class="lbn">Kaiyan</div><div class="lbv">14</div></div>
        <div class="lbr"><div class="lbrk r2">2</div><div class="lbn">Qaim</div><div class="lbv">13</div></div>
        <div class="lbr"><div class="lbrk r3">3</div><div class="lbn">Ariyan</div><div class="lbv">11</div></div>
        <div class="lbr"><div class="lbrk rn">4</div><div class="lbn">Viaan</div><div class="lbv">11</div></div>
        <div class="lbr"><div class="lbrk rn">5</div><div class="lbn">Veer</div><div class="lbv">10</div></div></div>
      <div class="lbc"><div class="lbh">&#127942; Best Net Runs</div>
        <div class="lbr"><div class="lbrk r1">1</div><div class="lbn">Qaim</div><div class="lbv">+22</div></div>
        <div class="lbr"><div class="lbrk r2">2</div><div class="lbn">Ariyan</div><div class="lbv">+19</div></div>
        <div class="lbr"><div class="lbrk r3">3</div><div class="lbn">Kaiyan</div><div class="lbv">+18</div></div>
        <div class="lbr"><div class="lbrk rn">4</div><div class="lbn">Veer</div><div class="lbv">+16</div></div>
        <div class="lbr"><div class="lbrk rn">5</div><div class="lbn">Avyaan</div><div class="lbv">+15</div></div></div>
      <div class="lbc"><div class="lbh"><img src="icons/ball_light.png" style="width:18px;height:18px;vertical-align:middle;" alt="ball"> Most Wickets</div>
        <div class="lbr"><div class="lbrk r1">1</div><div class="lbn">Krish</div><div class="lbv">6</div></div>
        <div class="lbr"><div class="lbrk r2">2</div><div class="lbn">Qaim</div><div class="lbv">5</div></div>
        <div class="lbr"><div class="lbrk r3">3</div><div class="lbn">Avyaan</div><div class="lbv">4</div></div>
        <div class="lbr"><div class="lbrk rn">4</div><div class="lbn">Veer</div><div class="lbv">2</div></div>
        <div class="lbr"><div class="lbrk rn">4</div><div class="lbn">Kaiyan</div><div class="lbv">2</div></div></div>
      <div class="lbc"><div class="lbh">&#128308; Most Fours</div>
        <div class="lbr"><div class="lbrk r1">1</div><div class="lbn">Qaim</div><div class="lbv">6</div></div>
        <div class="lbr"><div class="lbrk r2">2</div><div class="lbn">Ariyan</div><div class="lbv">4</div></div>
        <div class="lbr"><div class="lbrk r3">3</div><div class="lbn">Kaiyan</div><div class="lbv">3</div></div>
        <div class="lbr"><div class="lbrk rn">4</div><div class="lbn">Viaan</div><div class="lbv">2</div></div>
        <div class="lbr"><div class="lbrk rn">5</div><div class="lbn">Veer</div><div class="lbv">1</div></div></div>
      <div class="lbc"><div class="lbh">&#128200; Best Economy (min 2 overs)</div>
        <div class="lbr"><div class="lbrk r1">1</div><div class="lbn">Krish</div><div class="lbv">2.2</div></div>
        <div class="lbr"><div class="lbrk r2">2</div><div class="lbn">Aanya</div><div class="lbv">3.1</div></div>
        <div class="lbr"><div class="lbrk r3">3</div><div class="lbn">Avyaan</div><div class="lbv">4.6</div></div>
        <div class="lbr"><div class="lbrk rn">4</div><div class="lbn">Ariyan</div><div class="lbv">4.9</div></div>
        <div class="lbr"><div class="lbrk rn">5</div><div class="lbn">Viaan</div><div class="lbv">5.2</div></div></div>
      <div class="lbc"><div class="lbh">&#128308; Most Dot Balls</div>
        <div class="lbr"><div class="lbrk r1">1</div><div class="lbn">Avyaan</div><div class="lbv">26</div></div>
        <div class="lbr"><div class="lbrk r2">2</div><div class="lbn">Ariyan</div><div class="lbv">25</div></div>
        <div class="lbr"><div class="lbrk r3">3</div><div class="lbn">Qaim</div><div class="lbv">24</div></div>
        <div class="lbr"><div class="lbrk rn">4</div><div class="lbn">Krish</div><div class="lbv">23</div></div>
        <div class="lbr"><div class="lbrk rn">4</div><div class="lbn">Aanya</div><div class="lbv">23</div></div></div>
      <div class="lbc"><div class="lbh">&#129309; Best Partnerships (ECC)</div>
        <div class="lbr"><div class="lbrk r1">1</div><div class="lbn">Avyaan &amp; Taran <span style="font-size:.7rem;color:var(--mgrey);font-weight:400;">M5</span></div><div class="lbv">+32</div></div>
        <div class="lbr"><div class="lbrk r2">2</div><div class="lbn">Shyam &amp; Viaan <span style="font-size:.7rem;color:var(--mgrey);font-weight:400;">M6</span></div><div class="lbv">+30</div></div>
        <div class="lbr"><div class="lbrk r3">3</div><div class="lbn">Qaim &amp; Krish <span style="font-size:.7rem;color:var(--mgrey);font-weight:400;">M5</span></div><div class="lbv">+29</div></div>
        <div class="lbr"><div class="lbrk rn">4</div><div class="lbn">Krish &amp; Qaim <span style="font-size:.7rem;color:var(--mgrey);font-weight:400;">M7</span></div><div class="lbv">+21</div></div>
        <div class="lbr"><div class="lbrk rn">5</div><div class="lbn">Shyam &amp; Drish <span style="font-size:.7rem;color:var(--mgrey);font-weight:400;">M5</span></div><div class="lbv">+27</div></div></div>
      <div class="lbc"><div class="lbh"><img src="icons/fielder_light.png" style="width:18px;height:18px;vertical-align:middle;" alt="field"> Most Catches</div>
        <div class="lbr"><div class="lbrk r1">1</div><div class="lbn">Avyaan <span style="font-size:.7rem;color:var(--mgrey);font-weight:400;">M7</span></div><div class="lbv">2</div></div>
        <div class="lbr"><div class="lbrk r2">2</div><div class="lbn">Drish <span style="font-size:.7rem;color:var(--mgrey);font-weight:400;">M7</span></div><div class="lbv">1</div></div>
        <div class="lbr"><div class="lbrk r2">2</div><div class="lbn">Taran</div><div class="lbv">1</div></div>
        <div class="lbr"><div class="lbrk r2">2</div><div class="lbn">Shyam</div><div class="lbv">1</div></div>
        <div class="lbr"><div class="lbrk r2">2</div><div class="lbn">Qaim <span style="font-size:.7rem;color:var(--mgrey);font-weight:400;">M7</span></div><div class="lbv">1</div></div></div>
      <div class="lbc"><div class="lbh"><img src="icons/fielder_light.png" style="width:18px;height:18px;vertical-align:middle;" alt="field"> Most Run Outs</div>
        <div class="lbr"><div class="lbrk r1">1</div><div class="lbn">Avyaan</div><div class="lbv">3</div></div>
        <div class="lbr"><div class="lbrk r2">2</div><div class="lbn">Qaim</div><div class="lbv">2</div></div>
        <div class="lbr"><div class="lbrk r3">3</div><div class="lbn">Drish <span style="font-size:.7rem;color:var(--mgrey);font-weight:400;">M7</span></div><div class="lbv">1</div></div>
        <div class="lbr"><div class="lbrk r3">3</div><div class="lbn">Taran <span style="font-size:.7rem;color:var(--mgrey);font-weight:400;">M7</span></div><div class="lbv">1</div></div>
        <div class="lbr"><div class="lbrk r3">3</div><div class="lbn">Ariyan</div><div class="lbv">1</div></div></div>
    </div>"""

SIX_HITTER_LEADER_ROWS: list[tuple[str, str, int]] = [
    ("Avyaan", "M6", 1),
]

BEST_ECONOMY_CARD = """      <div class="lbc"><div class="lbh">&#128200; Best Economy (min 2 overs)</div>
        <div class="lbr"><div class="lbrk r1">1</div><div class="lbn">Krish</div><div class="lbv">2.2</div></div>
        <div class="lbr"><div class="lbrk r2">2</div><div class="lbn">Aanya</div><div class="lbv">3.1</div></div>
        <div class="lbr"><div class="lbrk r3">3</div><div class="lbn">Avyaan</div><div class="lbv">4.6</div></div>
        <div class="lbr"><div class="lbrk rn">4</div><div class="lbn">Ariyan</div><div class="lbv">4.9</div></div>
        <div class="lbr"><div class="lbrk rn">5</div><div class="lbn">Viaan</div><div class="lbv">5.2</div></div></div>"""

MOST_SIXES_BEFORE_ECONOMY = (
    '        <div class="lbr"><div class="lbrk rn">5</div><div class="lbn">Veer</div><div class="lbv">1</div></div></div>\n'
    '      <div class="lbc"><div class="lbh">&#128200; Best Economy (min 2 overs)</div>'
)

PLAYER_CARD_UPDATES: dict[str, dict[str, str]] = {
    "Krish": {
        "bat": """          <div class="psr"><span class="psl">Inn</span><span class="psv">4</span></div>
          <div class="psr"><span class="psl">Bat Runs / Avg</span><span class="psv">23 / 5.8</span></div>
          <div class="psr"><span class="psl">4s / 6s</span><span class="psv">0 / 0</span></div>
          <div class="psr"><span class="psl">Net Runs</span><span class="psv nn">&minus;2</span></div>""",
        "bowl": """          <div class="psr"><span class="psl">Overs / Wkts</span><span class="psv">8 / 6</span></div>
          <div class="psr"><span class="psl">Runs / ECO</span><span class="psv eco-good">18 / 2.2</span></div>
          <div class="psr"><span class="psl">Dots</span><span class="psv">23</span></div>""",
    },
    "Qaim": {
        "bat": """          <div class="psr"><span class="psl">Inn</span><span class="psv">5</span></div>
          <div class="psr"><span class="psl">Bat Runs / Avg</span><span class="psv">42 / 8.4</span></div>
          <div class="psr"><span class="psl">4s / 6s</span><span class="psv">6 / 0</span></div>
          <div class="psr"><span class="psl">Net Runs</span><span class="psv np">+22</span></div>""",
        "bowl": """          <div class="psr"><span class="psl">Overs / Wkts</span><span class="psv">10 / 5</span></div>
          <div class="psr"><span class="psl">Runs / ECO</span><span class="psv eco-bad">63 / 6.3</span></div>
          <div class="psr"><span class="psl">Dots</span><span class="psv">24</span></div>""",
        "field": """        <div class="pss"><div class="psst"><span><img src="icons/fielding-role.png" style="width:18px;height:18px;vertical-align:middle;" alt="field"></span> Fielding</div>
          <div class="psr"><span class="psl">Catches</span><span class="psv">1</span></div>
          <div class="psr"><span class="psl">Run Outs</span><span class="psv">2</span></div></div>""",
    },
    "Avyaan": {
        "bat": """          <div class="psr"><span class="psl">Inn</span><span class="psv">5</span></div>
          <div class="psr"><span class="psl">Bat Runs / Avg</span><span class="psv">25 / 5.0</span></div>
          <div class="psr"><span class="psl">4s / 6s</span><span class="psv">1 / 1</span></div>
          <div class="psr"><span class="psl">Net Runs</span><span class="psv np">+15</span></div>""",
        "bowl": """          <div class="psr"><span class="psl">Overs / Wkts</span><span class="psv">10 / 4</span></div>
          <div class="psr"><span class="psl">Runs / ECO</span><span class="psv">46 / 4.6</span></div>
          <div class="psr"><span class="psl">Dots</span><span class="psv">26</span></div>""",
        "field": """        <div class="pss"><div class="psst"><span><img src="icons/fielding-role.png" style="width:18px;height:18px;vertical-align:middle;" alt="field"></span> Fielding</div>
          <div class="psr"><span class="psl">Catches</span><span class="psv">2</span></div>
          <div class="psr"><span class="psl">Run Outs</span><span class="psv">3</span></div></div>""",
    },
    "Kaiyan": {
        "bat": """          <div class="psr"><span class="psl">Inn</span><span class="psv">4</span></div>
          <div class="psr"><span class="psl">Bat Runs / Avg</span><span class="psv">28 / 7.0</span></div>
          <div class="psr"><span class="psl">4s / 6s</span><span class="psv">3 / 0</span></div>
          <div class="psr"><span class="psl">Net Runs</span><span class="psv np">+18</span></div>""",
        "bowl": """          <div class="psr"><span class="psl">Overs / Wkts</span><span class="psv">8 / 2</span></div>
          <div class="psr"><span class="psl">Runs / ECO</span><span class="psv">45 / 5.6</span></div>
          <div class="psr"><span class="psl">Dots</span><span class="psv">23</span></div>""",
    },
    "Taran": {
        "bat": """          <div class="psr"><span class="psl">Inn</span><span class="psv">3</span></div>
          <div class="psr"><span class="psl">Bat Runs / Avg</span><span class="psv">18 / 6.0</span></div>
          <div class="psr"><span class="psl">4s / 6s</span><span class="psv">1 / 0</span></div>
          <div class="psr"><span class="psl">Net Runs</span><span class="psv np">+8</span></div>""",
        "bowl": """          <div class="psr"><span class="psl">Overs / Wkts</span><span class="psv">6 / 1</span></div>
          <div class="psr"><span class="psl">Runs / ECO</span><span class="psv">34 / 5.7</span></div>
          <div class="psr"><span class="psl">Dots</span><span class="psv">19</span></div>""",
        "field": """        <div class="pss"><div class="psst"><span><img src="icons/fielding-role.png" style="width:18px;height:18px;vertical-align:middle;" alt="field"></span> Fielding</div>
          <div class="psr"><span class="psl">Catches</span><span class="psv">1</span></div>
          <div class="psr"><span class="psl">Run Outs</span><span class="psv">1</span></div></div>""",
    },
    "Drish": {
        "bat": """          <div class="psr"><span class="psl">Inn</span><span class="psv">4</span></div>
          <div class="psr"><span class="psl">Bat Runs / Avg</span><span class="psv">17 / 4.2</span></div>
          <div class="psr"><span class="psl">4s / 6s</span><span class="psv">1 / 0</span></div>
          <div class="psr"><span class="psl">Net Runs</span><span class="psv np">+7</span></div>""",
        "bowl": """          <div class="psr"><span class="psl">Overs / Wkts</span><span class="psv">8 / 0</span></div>
          <div class="psr"><span class="psl">Runs / ECO</span><span class="psv">44 / 5.5</span></div>
          <div class="psr"><span class="psl">Dots</span><span class="psv">17</span></div>""",
        "field": """        <div class="pss"><div class="psst"><span><img src="icons/fielding-role.png" style="width:18px;height:18px;vertical-align:middle;" alt="field"></span> Fielding</div>
          <div class="psr"><span class="psl">Catches</span><span class="psv">1</span></div>
          <div class="psr"><span class="psl">Run Outs</span><span class="psv">1</span></div></div>""",
    },
    "Shyam": {
        "bat": """          <div class="psr"><span class="psl">Inn</span><span class="psv">4</span></div>
          <div class="psr"><span class="psl">Bat Runs / Avg</span><span class="psv">11 / 2.8</span></div>
          <div class="psr"><span class="psl">4s / 6s</span><span class="psv">1 / 0</span></div>
          <div class="psr"><span class="psl">Net Runs</span><span class="psv nn">&minus;9</span></div>""",
        "bowl": """          <div class="psr"><span class="psl">Overs / Wkts</span><span class="psv">8 / 2</span></div>
          <div class="psr"><span class="psl">Runs / ECO</span><span class="psv eco-bad">54 / 6.8</span></div>
          <div class="psr"><span class="psl">Dots</span><span class="psv">22</span></div>""",
    },
    "Aanya": {
        "bat": """          <div class="psr"><span class="psl">Inn</span><span class="psv">4</span></div>
          <div class="psr"><span class="psl">Bat Runs / Avg</span><span class="psv">12 / 3.0</span></div>
          <div class="psr"><span class="psl">4s / 6s</span><span class="psv">0 / 0</span></div>
          <div class="psr"><span class="psl">Net Runs</span><span class="psv nn">&minus;8</span></div>""",
        "bowl": """          <div class="psr"><span class="psl">Overs / Wkts</span><span class="psv">8 / 2</span></div>
          <div class="psr"><span class="psl">Runs / ECO</span><span class="psv eco-good">25 / 3.1</span></div>
          <div class="psr"><span class="psl">Dots</span><span class="psv">23</span></div>""",
    },
}


def main() -> None:
    from patch_m6_overview import (  # noqa: WPS433
        _most_sixes_block,
        _replace_table_body,
        _update_player_card,
        patch_leaders,
        patch_most_sixes,
        patch_players,
    )

    html = INDEX.read_text(encoding="utf-8")

    html = html.replace(
        '<h3>Next Match &mdash; 21 Jun 2026</h3><p>&#127968; Edgware vs H Manor &nbsp;&middot;&nbsp; Home &nbsp;&middot;&nbsp; Canons High School &nbsp;&middot;&nbsp; 09:00 / 10:00 AM</p>',
        '<h3>Next Match &mdash; 5 Jul 2026</h3><p>&#9992;&#65039; Harefield vs Edgware &nbsp;&middot;&nbsp; Away &nbsp;&middot;&nbsp; Harefield &nbsp;&middot;&nbsp; 09:00 / 10:00 AM</p>',
        1,
    )

    for old_margin in ("+45", "+61"):
        html = html.replace(
            f'<div class="sbox"><div class="v">6</div><div class="l">Played</div></div>\n'
            '    <div class="sbox win"><div class="v">5</div><div class="l">Wins</div></div>\n'
            '    <div class="sbox loss"><div class="v">1</div><div class="l">Losses</div></div>\n'
            '    <div class="sbox"><div class="v">0</div><div class="l">Draws</div></div>\n'
            '    <div class="sbox"><div class="v">315</div><div class="l">Highest Score</div></div>\n'
            f'    <div class="sbox"><div class="v">{old_margin}</div><div class="l">Best Win Margin</div></div>',
            OVERVIEW_STATS.strip(),
            1,
        )

    if "Based on M2, M4, M5, M6 &amp; M7" not in html:
        html = html.replace(
            '<p style="font-size:.8rem;color:var(--mgrey);margin-bottom:16px;">Based on M2, M4, M5 &amp; M6 (M1 &amp; M3 walkovers). Net Runs = Bat Runs &minus; 5 per wicket lost. Avg = Bat Runs &divide; Innings. SR = runs &divide; balls faced &times; 100.</p>',
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

    lb_start = html.find('id="tab-lb"')
    if lb_start == -1:
        raise SystemExit("tab-lb missing")
    html = re.sub(
        r'(<div id="tab-lb" class="tab">\s*<div class="card">\s*<div class="ctitle">[^<]+</div>\s*)<p style="font-size:\.8rem;color:var\(--mgrey\);margin-bottom:16px;">.*?</p>(\s*<div class="lbg">).*?(</div>\s*</div>\s*</div>\s*\n\n<!-- RULES -->)',
        rf"\1{LEADERS_NOTE}\n{LEADERS_GRID}\3",
        html,
        count=1,
        flags=re.DOTALL,
    )

    if len(SIX_HITTER_LEADER_ROWS) < 2 or MOST_SIXES_BEFORE_ECONOMY not in html:
        pass
    else:
        html = html.replace(
            MOST_SIXES_BEFORE_ECONOMY,
            '        <div class="lbr"><div class="lbrk rn">5</div><div class="lbn">Veer</div><div class="lbv">1</div></div></div>\n'
            + _most_sixes_block(SIX_HITTER_LEADER_ROWS)
            + '\n      <div class="lbc"><div class="lbh">&#128200; Best Economy (min 2 overs)</div>',
            1,
        )
    html = re.sub(
        r'<div class="lbc"><div class="lbh">&#128200; Best Economy \(min 2 overs\)</div>.*?</div>\s*(?=<div class="lbc"><div class="lbh">&#128308; Most Dot Balls</div>)',
        BEST_ECONOMY_CARD,
        html,
        count=1,
        flags=re.DOTALL,
    )

    from patch_index import fix_tab_pl_boundary

    html = fix_tab_pl_boundary(html)
    INDEX.write_text(html, encoding="utf-8")
    print(f"Updated overview, players, and leaders in {INDEX}")

    from patch_strike_rate import main as patch_strike_rate_main

    patch_strike_rate_main()


if __name__ == "__main__":
    main()
