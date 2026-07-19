#!/usr/bin/env python3
"""Integrate M7 results into overview, player stats, and leaderboards in index.html."""

from __future__ import annotations

import re
from pathlib import Path

from partnership_stats import collect_ecc_partnerships
from summary_player_stats import (
    SummarySeason,
    collect_summary_season,
    derive_shared_leaderboards,
    render_leader_card,
)

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"

NEXT_MATCH = (
    '  <div class="nm"><div class="nmi">&#128197;</div>'
    '<div class="nminfo"><h3>Next Match · 5 Jul 2026</h3>'
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
    "Net Runs = Bat Runs &minus; 5 per wicket lost. Inn = dismissals + 1. "
    "Avg/M = Bat Runs &divide; M. Avg/Inn = Bat Runs &divide; Inn. "
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

FIELD_TABLE_BODY = """        <tr><td><strong>Avyaan</strong></td><td class="c"><strong>2</strong></td><td class="c"><strong>3</strong></td></tr>
        <tr><td><strong>Qaim</strong></td><td class="c"><strong>1</strong></td><td class="c"><strong>3</strong></td></tr>
        <tr><td><strong>Taran</strong></td><td class="c"><strong>1</strong></td><td class="c"><strong>2</strong></td></tr>
        <tr><td><strong>Drish</strong></td><td class="c"><strong>1</strong></td><td class="c"><strong>1</strong></td></tr>
        <tr><td><strong>Krish</strong></td><td class="c"><strong>1</strong></td><td class="c"><strong>1</strong></td></tr>
        <tr><td><strong>Shyam</strong></td><td class="c"><strong>1</strong></td><td class="c">0</td></tr>
        <tr><td><strong>Ariyan</strong></td><td class="c">0</td><td class="c"><strong>1</strong></td></tr>
        <tr><td><strong>Viaan</strong></td><td class="c">0</td><td class="c"><strong>1</strong></td></tr>"""

LEADERS_NOTE = (
    '<p style="font-size:.8rem;color:var(--mgrey);margin-bottom:16px;">'
    "Based on 5 played matches (M2 vs H Manor, M4 vs Hayes, M5 vs Harefield, M6 vs Pinner, M7 vs H Manor). "
    "M1 &amp; M3 walkovers. Best Batting Averages uses the same Players innings rule (outs + 1) "
    "with minimum 2 matches played eligibility.</p>"
)

LEADERS_GRID = """    <div class="lbg">
      <div class="lbc"><div class="lbh"><img src="icons/batsman_light.png" style="width:18px;height:18px;vertical-align:middle;" alt="bat"> Most Bat Runs</div>
        <div class="lbr"><div class="lbrk r1">1</div><div class="lbn">Qaim</div><div class="lbv">42</div></div>
        <div class="lbr"><div class="lbrk r2">2</div><div class="lbn">Ariyan</div><div class="lbv">34</div></div>
        <div class="lbr"><div class="lbrk r3">3</div><div class="lbn">Kaiyan</div><div class="lbv">28</div></div>
        <div class="lbr"><div class="lbrk rn">4</div><div class="lbn">Veer</div><div class="lbv">26</div></div>
        <div class="lbr"><div class="lbrk rn">5</div><div class="lbn">Avyaan</div><div class="lbv">25</div></div></div>
      <div class="lbc"><div class="lbh">&#127942; Best Batting Averages</div>
        <div class="lbr"><div class="lbrk r1">1</div><div class="lbn">Qaim</div><div class="lbv">8.4</div></div>
        <div class="lbr"><div class="lbrk r2">2</div><div class="lbn">Ariyan</div><div class="lbv">8.5</div></div>
        <div class="lbr"><div class="lbrk r3">3</div><div class="lbn">Kaiyan</div><div class="lbv">7.0</div></div>
        <div class="lbr"><div class="lbrk rn">4</div><div class="lbn">Veer</div><div class="lbv">6.5</div></div>
        <div class="lbr"><div class="lbrk rn">5</div><div class="lbn">Taran</div><div class="lbv">6.0</div></div></div>
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

MATCH_BUTTON_LABELS: dict[str, str] = {
    "m1": "Pinner · 26 Apr",
    "m2": "H Manor · 10 May &#127942;",
    "m3": "Harefield · 24 May",
    "m4": "Hayes · 31 May",
    "m5": "Harefield · 7 Jun &#127942;",
    "m6": "Pinner · 14 Jun",
    "m7": "H Manor · 21 Jun &#127942;",
}

M2_ECC_FIELDING_ROWS = """<tr class="scfi"><td class="scb">Krish</td><td class="c"><strong>1</strong></td><td class="c"><strong>0</strong></td><td>c Aryan b Viaan, Ov 9</td></tr>
<tr class="scfi"><td class="scb">Qaim</td><td class="c"><strong>0</strong></td><td class="c"><strong>1</strong></td><td>run out (Qaim), Ov 11 (Rafe)</td></tr>"""

M2_ECC_BOWLING_SECTION = """      <div class="sci" style="margin-top:20px;">
        <div class="scih"><span><img src="icons/ball_light.png" style="width:18px;height:18px;vertical-align:middle;" alt="ball"> Edgware CC · Bowling</span></div>
        <div class="tscroll"><table class="sctbl">
          <thead><tr><th>Bowler</th><th class="c">O</th><th class="c">R</th><th class="c">W</th><th class="c">WD</th><th class="c">NB</th><th class="c">ECO</th><th class="c">Dots</th></tr></thead>
          <tbody>
            <tr><td class="scb">Ariyan</td><td class="c">2</td><td class="c">3</td><td class="c">0</td><td class="c">0</td><td class="c">1</td><td class="c eco-good">1.5</td><td class="c"><strong>10</strong></td></tr>
            <tr><td class="scb">Aanya</td><td class="c">2</td><td class="c">5</td><td class="c"><strong>1</strong></td><td class="c">1</td><td class="c">1</td><td class="c eco-good">2.5</td><td class="c">6</td></tr>
            <tr><td class="scb">Krish</td><td class="c">2</td><td class="c">5</td><td class="c"><strong>1</strong></td><td class="c">2</td><td class="c">0</td><td class="c eco-good">2.5</td><td class="c">5</td></tr>
            <tr><td class="scb">Avyaan</td><td class="c">2</td><td class="c">8</td><td class="c"><strong>1</strong></td><td class="c">2</td><td class="c">0</td><td class="c">4.0</td><td class="c">6</td></tr>
            <tr><td class="scb">Veer</td><td class="c">2</td><td class="c">8</td><td class="c">0</td><td class="c">2</td><td class="c">0</td><td class="c">4.0</td><td class="c">6</td></tr>
            <tr><td class="scb">Kaiyan</td><td class="c">2</td><td class="c">11</td><td class="c">0</td><td class="c">1</td><td class="c">1</td><td class="c">5.5</td><td class="c">5</td></tr>
            <tr><td class="scb">Viaan</td><td class="c">2</td><td class="c">12</td><td class="c">0</td><td class="c">2</td><td class="c">1</td><td class="c">6.0</td><td class="c">7</td></tr>
            <tr><td class="scb">Qaim</td><td class="c">2</td><td class="c">17</td><td class="c">0</td><td class="c">2</td><td class="c">1</td><td class="c eco-bad">8.5</td><td class="c">5</td></tr>
          </tbody>
        </table></div>
      </div>"""

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


def _replace_bowling_table_from_source(html: str, season: SummarySeason) -> str:
    items = sorted(
        season.bowling.items(),
        key=lambda kv: (-kv[1].wickets, kv[1].economy, kv[0]),
    )
    max_wickets = max((s.wickets for _n, s in items), default=0)
    max_dots = max((s.dots for _n, s in items), default=0)
    rows: list[str] = []
    for name, stats in items:
        if stats.matches == 0 and stats.balls == 0:
            continue
        matches = stats.matches
        overs = stats.overs_text
        eco_value = stats.economy
        eco_cls = " eco-good" if eco_value <= 4.0 else (" eco-bad" if eco_value >= 6.0 else "")
        wickets = stats.wickets
        w_cell = f"<strong>{wickets}</strong>" if wickets == max_wickets and wickets > 0 else str(wickets)
        dots_cell = f"<strong>{stats.dots}</strong>" if stats.dots == max_dots and stats.dots > 0 else str(stats.dots)
        rows.append(
            f'        <tr><td><strong>{name}</strong></td><td class="c">{matches}</td><td class="c">{overs}</td>'
            f'<td class="c">{stats.runs}</td><td class="c">{w_cell}</td><td class="c">{stats.wides}</td>'
            f'<td class="c">{stats.noballs}</td><td class="c{eco_cls}">{eco_value:.2f}</td><td class="c">{dots_cell}</td></tr>'
        )
    from patch_m6_overview import _replace_table_body  # noqa: WPS433

    return _replace_table_body(
        html,
        '<tr><th>Bowler</th><th class="c">M</th><th class="c">O</th><th class="c">R</th><th class="c">W</th><th class="c">WD</th><th class="c">NB</th><th class="c">ECO</th><th class="c">Dots</th></tr>',
        "\n".join(rows),
    )


def _replace_batting_table_from_source(html: str, season: SummarySeason) -> str:
    rows: list[str] = []
    ranked = sorted(
        season.batting.items(),
        key=lambda kv: (-kv[1].runs, -kv[1].hs, kv[0]),
    )
    for name, stats in ranked:
        if stats.matches == 0:
            continue
        net_cls = "np" if stats.net >= 0 else "nn"
        net_text = f"+{stats.net}" if stats.net >= 0 else f"&minus;{abs(stats.net)}"
        rows.append(
            f'        <tr><td><strong>{name}</strong></td><td class="c">{stats.matches}</td><td class="c">{stats.innings}</td>'
            f'<td class="c">{stats.runs}</td><td class="c">{stats.avg_match:.1f}</td><td class="c">{stats.avg_inn:.1f}</td>'
            f'<td class="c">{stats.sr:.1f}</td><td class="c">{stats.hs}</td><td class="c">{stats.fours}</td>'
            f'<td class="c">{stats.sixes}</td><td class="c {net_cls}">{net_text}</td></tr>'
        )
    from patch_m6_overview import _replace_table_body  # noqa: WPS433
    return _replace_table_body(
        html,
        '<tr><th>Batter</th><th class="c">M</th><th class="c">Inn</th><th class="c">Bat Runs</th>'
        '<th class="c">Avg/M</th><th class="c">Avg/Inn</th><th class="c">SR</th><th class="c">HS</th>'
        '<th class="c">4s</th><th class="c">6s</th><th class="c">Net Runs</th></tr>',
        "\n".join(rows),
    )


def _replace_fielding_table_from_source(html: str, season: SummarySeason) -> str:
    rows: list[str] = []
    ranked = sorted(
        season.fielding.items(),
        key=lambda kv: (-kv[1].catches, -kv[1].run_outs, kv[0]),
    )
    for name, stats in ranked:
        if stats.catches == 0 and stats.run_outs == 0:
            continue
        rows.append(
            f'        <tr><td><strong>{name}</strong></td><td class="c">{stats.catches}</td><td class="c">{stats.run_outs}</td></tr>'
        )
    return _replace_players_fielding_table(html, "\n".join(rows))


def _replace_players_fielding_table(html: str, body_rows: str) -> str:
    tab_pl_start = html.find('<div id="tab-pl" class="tab">')
    if tab_pl_start == -1:
        raise SystemExit("tab-pl missing")
    tab_lb_start = html.find('<div id="tab-lb" class="tab">', tab_pl_start)
    if tab_lb_start == -1:
        raise SystemExit("tab-lb missing")
    tab_pl = html[tab_pl_start:tab_lb_start]
    table_matches = list(
        re.finditer(
            r"<table class=\"dt\">\s*<thead><tr>.*?</tr></thead>\s*<tbody>.*?</tbody>\s*</table>",
            tab_pl,
            flags=re.DOTALL,
        )
    )
    if len(table_matches) < 3:
        raise SystemExit("Fielding table not found in tab-pl")
    fielding_match = table_matches[2]
    fielding_table = tab_pl[fielding_match.start() : fielding_match.end()]
    fielding_table = re.sub(
        r"<thead><tr>.*?</tr></thead>",
        '<thead><tr><th>Fielder</th><th class="c">Catches</th><th class="c">Run Outs</th></tr></thead>',
        fielding_table,
        count=1,
        flags=re.DOTALL,
    )
    fielding_table = re.sub(
        r"(<tbody>\s*).*?(\s*</tbody>)",
        rf"\1\n{body_rows}\n      \2",
        fielding_table,
        count=1,
        flags=re.DOTALL,
    )
    tab_pl = tab_pl[: fielding_match.start()] + fielding_table + tab_pl[fielding_match.end() :]
    return html[:tab_pl_start] + tab_pl + html[tab_lb_start:]


def _leader_card(
    title_html: str,
    rows: list[tuple[str, str, int | float]],
    *,
    limit: int = 5,
) -> str:
    display = [(name, value) for name, value, _sort in rows]
    sort_keys = [sort for _name, _value, sort in rows]
    return render_leader_card(title_html, display, sort_keys, limit=limit)


def _replace_most_wickets_card(html: str, leaders: dict[str, list[tuple[str, str]]]) -> str:
    rows = leaders["wickets"]
    card = _leader_card(
        '<img src="icons/ball_light.png" style="width:18px;height:18px;vertical-align:middle;" alt="ball"> Most Wickets',
        rows,
    )
    return re.sub(
        r'<div class="lbc"><div class="lbh"><img src="icons/ball_light\.png"[^>]*> Most Wickets</div>.*?</div>\s*(?=<div class="lbc"><div class="lbh">&#128308; Most Fours</div>)',
        card,
        html,
        count=1,
        flags=re.DOTALL,
    )


def _replace_most_dot_balls_card(html: str, leaders: dict[str, list[tuple[str, str]]]) -> str:
    rows = leaders["dots"]
    card = _leader_card("&#128308; Most Dot Balls", rows)
    return re.sub(
        r'<div class="lbc"><div class="lbh">&#128308; Most Dot Balls</div>.*?</div>\s*(?=<div class="lbc"><div class="lbh">&#129309; Best Partnerships \(ECC\)</div>)',
        card,
        html,
        count=1,
        flags=re.DOTALL,
    )


def _replace_best_economy_card(html: str, leaders: dict[str, list[tuple[str, str]]]) -> str:
    rows = leaders["economy"]
    card = _leader_card("&#128200; Best Economy (min 2 overs)", rows)
    return re.sub(
        r'<div class="lbc"><div class="lbh">&#128200; Best Economy \(min 2 overs\)</div>.*?</div>\s*(?=<div class="lbc"><div class="lbh">&#128308; Most Dot Balls</div>)',
        card,
        html,
        count=1,
        flags=re.DOTALL,
    )


def _replace_best_bowling_figures_card(html: str) -> str:
    best = collect_summary_season(html).best_bowling
    ranked = sorted(
        best.items(),
        key=lambda kv: (-kv[1][1], kv[1][2], kv[0]),
    )[:5]
    rows = [
        (
            f'{name} <span style="font-size:.7rem;color:var(--mgrey);font-weight:400;">{fig[0]}</span>',
            f"{fig[1]}/{fig[2]}",
            (fig[1], fig[2]),
        )
        for name, fig in ranked
    ]
    card = _leader_card("&#127942; Best Bowling Figures", rows)
    html = re.sub(
        r'\n\s*<div class="lbc"><div class="lbh">&#127942; Best Bowling Figures</div>.*?</div>\s*(?=<div class="lbc"><div class="lbh">&#128308; Most Fours</div>)',
        "\n",
        html,
        count=1,
        flags=re.DOTALL,
    )
    return re.sub(
        r'(\s*<div class="lbc"><div class="lbh">&#128308; Most Fours</div>)',
        rf"\n{card}\n\1",
        html,
        count=1,
    )


def _replace_generic_leader_card(html: str, title_regex: str, title_html: str, rows: list[tuple[str, str]], next_title_regex: str) -> str:
    card = _leader_card(title_html, rows)
    return re.sub(
        rf'<div class="lbc"><div class="lbh">{title_regex}</div>.*?</div>\s*(?=<div class="lbc"><div class="lbh">{next_title_regex}</div>)',
        card,
        html,
        count=1,
        flags=re.DOTALL,
    )


def _replace_batting_leader_cards(
    html: str,
    leaders: dict[str, list[tuple[str, str]]],
) -> str:
    most_runs = leaders["bat_runs"]
    html = _replace_generic_leader_card(
        html,
        r'<img src="icons/batsman_light\.png"[^>]*> Most Bat Runs',
        '<img src="icons/batsman_light.png" style="width:18px;height:18px;vertical-align:middle;" alt="bat"> Most Bat Runs',
        most_runs,
        r'&#127942; Best Batting Averages',
    )
    html = _replace_generic_leader_card(
        html,
        r'&#127942; Best Batting Averages',
        '&#127942; Best Batting Averages',
        leaders["batting_avg"],
        r'&#127775; Highest Score \(single match\)',
    )
    highest = leaders["high_score"]
    html = _replace_generic_leader_card(
        html,
        r'&#127775; Highest Score \(single match\)',
        '&#127775; Highest Score (single match)',
        highest,
        r'&#127942; Best Net Runs',
    )
    net = leaders["net_runs"]
    html = _replace_generic_leader_card(
        html,
        r'&#127942; Best Net Runs',
        '&#127942; Best Net Runs',
        net,
        r'<img src="icons/ball_light\.png"[^>]*> Most Wickets',
    )
    fours = leaders["fours"]
    html = _replace_generic_leader_card(
        html,
        r'&#128308; Most Fours',
        '&#128308; Most Fours',
        fours,
        r'&#128200; Best Economy \(min 2 overs\)',
    )
    return html


def _replace_fielding_leader_cards(
    html: str,
    leaders: dict[str, list[tuple[str, str]]],
) -> str:
    catches = leaders["catches"]
    html = _replace_generic_leader_card(
        html,
        r'<img src="icons/fielder_light\.png"[^>]*> Most Catches',
        '<img src="icons/fielder_light.png" style="width:18px;height:18px;vertical-align:middle;" alt="field"> Most Catches',
        catches,
        r'<img src="icons/fielder_light\.png"[^>]*> Most Run Outs',
    )
    runout_card = _leader_card(
        '<img src="icons/fielder_light.png" style="width:18px;height:18px;vertical-align:middle;" alt="field"> Most Run Outs',
        leaders["run_outs"],
    )
    # Replace from the run-outs card start through the .lbg close so stale loose rows cannot survive.
    tab_start = html.find('<div id="tab-lb" class="tab">')
    rules_start = html.find("\n<!-- RULES -->", tab_start if tab_start != -1 else 0)
    if tab_start == -1 or rules_start == -1:
        return html
    tab_lb = html[tab_start:rules_start]
    runouts_marker = (
        '<div class="lbc"><div class="lbh"><img src="icons/fielder_light.png" '
        'style="width:18px;height:18px;vertical-align:middle;" alt="field"> Most Run Outs</div>'
    )
    runouts_start = tab_lb.find(runouts_marker)
    if runouts_start == -1:
        return html
    lbg_close = tab_lb.find("\n    </div>\n  </div>\n</div>", runouts_start)
    if lbg_close == -1:
        return html
    tab_lb = tab_lb[:runouts_start] + runout_card + tab_lb[lbg_close:]
    html = html[:tab_start] + tab_lb + html[rules_start:]
    return html


def _replace_best_partnerships_card(html: str) -> str:
    ranked = sorted(
        collect_ecc_partnerships(),
        key=lambda p: (-p.net, p.match, p.label, p.b1, p.b2),
    )[:5]
    rows = [
        (
            f'{p.b1} &amp; {p.b2} <span style="font-size:.7rem;color:var(--mgrey);font-weight:400;">{p.match}</span>',
            f"+{p.net}",
            p.net,
        )
        for p in ranked
    ]
    card = _leader_card("&#129309; Best Partnerships (ECC)", rows)
    return re.sub(
        r'<div class="lbc"><div class="lbh">&#129309; Best Partnerships \(ECC\)</div>.*?</div>\s*(?=<div class="lbc"><div class="lbh"><img src="icons/fielder_light\.png")',
        card,
        html,
        count=1,
        flags=re.DOTALL,
    )


def _replace_tab_lb_block(html: str) -> str:
    """Rebuild tab-lb shell to prevent leaked leaderboard rows."""
    tab_start = html.find('<div id="tab-lb" class="tab">')
    rules_marker = html.find("\n<!-- RULES -->", tab_start if tab_start != -1 else 0)
    if tab_start == -1 or rules_marker == -1:
        raise SystemExit("Could not locate tab-lb / rules boundary")

    replacement = (
        '<div id="tab-lb" class="tab">\n'
        '  <div class="card">\n'
        '    <div class="ctitle">&#127942; Season Leaderboards · ECC Players</div>\n'
        f"    {LEADERS_NOTE}\n"
        f"{LEADERS_GRID}\n"
        "  </div>\n"
        "</div>\n"
    )
    return html[:tab_start] + replacement + html[rules_marker + 1 :]


def _replace_match_button_labels(html: str) -> str:
    for match_id, label in MATCH_BUTTON_LABELS.items():
        html = re.sub(
            rf'(<button class="mtb(?: active)?" onclick="showMatch\(\x27{match_id}\x27,this\)">).*?(</button>)',
            rf"\1{label}\2",
            html,
            count=1,
            flags=re.DOTALL,
        )
    return html


def _repair_m2_summary_fielding_ecc(html: str) -> str:
    start = html.find('id="match-m2-summary"')
    if start == -1:
        return html
    end = html.find('id="match-m2-bbb"', start)
    if end == -1:
        return html
    block = html[start:end]
    repaired = re.sub(
        r'(Fielding Highlights \(ECC\)</div>\s*<div class="tscroll"><table class="sctbl">\s*<thead>\s*<tr>).*?(</tr>\s*</thead>\s*<tbody>).*?(</tbody>)',
        r'\1<th>Fielder</th><th class="c">Catches</th><th class="c">Run Outs</th><th>Detail</th>\2'
        + f"\n{M2_ECC_FIELDING_ROWS}\n"
        + r"\3",
        block,
        count=1,
        flags=re.DOTALL,
    )
    return html[:start] + repaired + html[end:]


def _repair_m2_summary_bowling_ecc(html: str) -> str:
    start = html.find('id="match-m2-summary"')
    if start == -1:
        return html
    end = html.find('id="match-m2-bbb"', start)
    if end == -1:
        return html
    block = html[start:end]

    section_pat = re.compile(
        r'<div class="sci" style="margin-top:20px;">\s*<div class="scih"><span><img src="icons/ball_light\.png"[^>]*> Edgware CC · Bowling</span></div>.*?</div>\s*</div>',
        flags=re.DOTALL,
    )
    if section_pat.search(block):
        repaired = section_pat.sub(M2_ECC_BOWLING_SECTION, block, count=1)
    else:
        repaired = re.sub(
            r'(\n\s*<div class="ff">)',
            "\n" + M2_ECC_BOWLING_SECTION + r"\1",
            block,
            count=1,
            flags=re.DOTALL,
        )
    return html[:start] + repaired + html[end:]


def main() -> None:
    from patch_m6_overview import (  # noqa: WPS433
        _most_sixes_block,
        _replace_table_body,
        patch_leaders,
        patch_most_sixes,
        patch_players,
    )

    html = INDEX.read_text(encoding="utf-8")

    html = html.replace(
        '<h3>Next Match · 21 Jun 2026</h3><p>&#127968; Edgware vs H Manor &nbsp;&middot;&nbsp; Home &nbsp;&middot;&nbsp; Canons High School &nbsp;&middot;&nbsp; 09:00 / 10:00 AM</p>',
        '<h3>Next Match · 5 Jul 2026</h3><p>&#9992;&#65039; Harefield vs Edgware &nbsp;&middot;&nbsp; Away &nbsp;&middot;&nbsp; Harefield &nbsp;&middot;&nbsp; 09:00 / 10:00 AM</p>',
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
        '<tr><th>Batter</th><th class="c">M</th><th class="c">Inn</th><th class="c">Bat Runs</th>'
        '<th class="c">Avg/M</th><th class="c">Avg/Inn</th><th class="c">SR</th><th class="c">HS</th>'
        '<th class="c">4s</th><th class="c">6s</th><th class="c">Net Runs</th></tr>',
        BAT_TABLE_BODY,
    )
    html = _replace_table_body(
        html,
        '<tr><th>Bowler</th><th class="c">M</th><th class="c">O</th><th class="c">R</th><th class="c">W</th><th class="c">WD</th><th class="c">NB</th><th class="c">ECO</th><th class="c">Dots</th></tr>',
        BOWL_TABLE_BODY,
    )
    html = _replace_players_fielding_table(html, FIELD_TABLE_BODY)

    html = _replace_tab_lb_block(html)

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

    from patch_index import fix_tab_lb_boundary, fix_tab_mx_boundary, fix_tab_pl_boundary

    html = _repair_m2_summary_fielding_ecc(html)
    html = _repair_m2_summary_bowling_ecc(html)
    season = collect_summary_season(html)
    leaders = derive_shared_leaderboards(season)
    html = _replace_batting_table_from_source(html, season)
    html = _replace_bowling_table_from_source(html, season)
    html = _replace_fielding_table_from_source(html, season)
    html = _replace_batting_leader_cards(html, leaders)
    html = _replace_most_wickets_card(html, leaders)
    html = _replace_best_economy_card(html, leaders)
    html = _replace_best_bowling_figures_card(html)
    html = _replace_most_dot_balls_card(html, leaders)
    html = _replace_best_partnerships_card(html)
    html = _replace_fielding_leader_cards(html, leaders)
    html = _replace_match_button_labels(html)
    html = fix_tab_mx_boundary(html)
    html = fix_tab_lb_boundary(html)
    html = fix_tab_pl_boundary(html)
    INDEX.write_text(html, encoding="utf-8")
    print(f"Updated overview, players, and leaders in {INDEX}")

    from patch_strike_rate import main as patch_strike_rate_main

    patch_strike_rate_main()


if __name__ == "__main__":
    main()
