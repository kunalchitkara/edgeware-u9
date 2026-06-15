#!/usr/bin/env python3
"""Inject ball-by-ball panels, match sub-tabs, hash routing, and scorecard links into index.html."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
BBB_DIR = ROOT / "bbb"

MATCHES_WITH_BBB = ["m2", "m4", "m5", "m6"]
WALKOVER_MATCHES = ["m1", "m3"]
DEFAULT_MATCH = "m1"

CSS = """
/* Match sub-tabs: Summary | Commentary (underline bar, distinct from .mts pills) */
.mmt{display:flex;width:100%;border-bottom:2px solid #e4e8ef;margin-bottom:16px;}
.mmtb{flex:1;padding:12px 0;border:none;background:transparent;color:var(--mgrey);font-weight:600;font-size:.9rem;cursor:pointer;border-bottom:3px solid transparent;margin-bottom:-2px;transition:color .2s,border-color .2s,background .2s;}
.mmtb:hover{color:var(--dk);background:rgba(61,133,198,.06);}
.mmtb.active{color:var(--dk);border-bottom-color:var(--md);background:rgba(61,133,198,.08);}
.mmview{display:none;}.mmview.active{display:block;}
/* Ball-by-ball list (Howzzat mobile style) */
.bbb-wrap{margin:0;}
.bbb-panel{margin-bottom:8px;box-shadow:0 1px 4px rgba(0,0,0,.06);border-radius:0;overflow:hidden;background:#fff;}
.bbb-toss-panel{box-shadow:0 1px 4px rgba(0,0,0,.06);}
.bbb-toss{padding:12px 14px;background:#f8f9fb;border-bottom:1px solid #eef1f6;font-size:.85rem;color:var(--dgrey);line-height:1.45;}
.bbb-toss strong{color:var(--dk);}
.bbb-inn-bar{display:flex;justify-content:space-between;align-items:center;background:var(--dk);color:#fff;padding:10px 14px;font-weight:700;font-size:.85rem;}
.bbb-inn-bar span:last-child{font-size:.95rem;font-weight:900;}
.bbb-list{background:#fff;}
.bbb-over{border-bottom:1px solid #eef1f6;}
.bbb-over:last-child{border-bottom:none;}
.bbb-over-hd{display:grid;grid-template-columns:1fr auto auto auto;gap:8px;align-items:center;width:100%;padding:10px 14px;border:none;border-bottom:1px solid #eee;background:#fafafa;cursor:pointer;text-align:left;font-size:.82rem;}
.bbb-over-main{display:flex;flex-direction:column;gap:3px;min-width:0;}
.bbb-over-num{font-weight:700;color:var(--dk);font-size:.82rem;}
.bbb-over-batters{font-size:.72rem;color:#666;line-height:1.35;}
.bbb-over-p{color:var(--md);font-weight:600;}
.bbb-over-sum{color:#666;font-size:.78rem;white-space:nowrap;}
.bbb-over-score{font-weight:800;color:var(--dgrey);font-size:.85rem;white-space:nowrap;}
.bbb-chev{color:#999;font-size:.75rem;}
.bbb-over.collapsed .bbb-chev{transform:rotate(-90deg);}
.bbb-over.collapsed .bbb-balls{display:none;}
.bbb-balls{list-style:none;margin:0;padding:0;}
.bbb-ball-row{display:grid;grid-template-columns:2.5rem 2rem 1fr auto;gap:8px;align-items:start;padding:8px 14px;border-bottom:1px solid #f0f0f0;font-size:.8rem;}
.bbb-ball-row.wkt{background:#fff5f5;}
.bbb-ov{color:#999;font-size:.72rem;padding-top:2px;}
.bbb-badge{display:flex;align-items:center;justify-content:center;width:1.6rem;height:1.6rem;border-radius:50%;background:var(--grey);font-weight:800;font-size:.75rem;color:var(--dk);flex-shrink:0;}
.bbb-badge-dot{background:#e8eaed;color:#7f8c8d;font-size:.85rem;}
.bbb-badge-runs{background:var(--grey);color:var(--dk);}
.bbb-badge-4,.bbb-badge.boundary{background:var(--lt);color:var(--md);}
.bbb-badge-wide,.bbb-badge-nb{background:#5d6d7e;color:#fff;}
.bbb-badge-wide{font-size:.9rem;}
.bbb-badge-nb{font-size:.7rem;text-transform:lowercase;}
.bbb-badge-wkt{background:var(--red);color:#fff;}
.bbb-badge-bye{background:var(--grey);color:var(--dk);font-size:.7rem;}
.bbb-badge-other{background:#fff;border:1px solid #ddd;}
.bbb-desc{color:var(--dgrey);line-height:1.35;}
.bbb-meta{display:block;font-size:.7rem;color:#999;margin-top:2px;}
.bbb-score{font-weight:700;color:var(--dk);font-size:.78rem;white-space:nowrap;}
@media(max-width:480px){.bbb-over-hd{grid-template-columns:1fr auto auto;}.bbb-over-sum{display:none;}}
/* Sortable player stats tables (#tab-pl) */
.dt th.th-sort{cursor:pointer;user-select:none;white-space:nowrap;}
.dt th.th-sort:hover{background:#0d4d7a;}
.dt th.th-sort::after{content:'⇅';opacity:.35;font-size:.7rem;margin-left:3px;}
.dt th.th-sort.asc::after{content:'▲';opacity:1;}
.dt th.th-sort.desc::after{content:'▼';opacity:1;}
"""

APP_JS = """const TAB_IDS=['ov','fx','mx','pl','lb','ru','pr'];
const TAB_ALIASES={fixtures:'fx',matches:'mx',overview:'ov',players:'pl',leaders:'lb',rules:'ru',practice:'pr'};
const MATCHES_WITH_BBB=['m2','m4','m5','m6'];

function latestMatch(){
  let latest='m1',n=0;
  document.querySelectorAll('[id^="match-m"]').forEach(el=>{
    const m=el.id.match(/^match-m(\\d+)$/);
    if(m){
      const num=parseInt(m[1],10);
      if(num>n){n=num;latest='m'+num;}
    }
  });
  return latest;
}

function resolveMatch(matchId){
  const id=(matchId||latestMatch()).toLowerCase();
  return document.getElementById('match-'+id)?id:latestMatch();
}

function parseHash(){
  const raw=location.hash.replace(/^#/,'');
  if(!raw)return{tab:'ov'};
  const parts=raw.split('/').filter(Boolean);
  let tab=parts[0]||'ov';
  if(TAB_ALIASES[tab])tab=TAB_ALIASES[tab];
  if(!TAB_IDS.includes(tab))return{tab:'ov'};
  const state={tab};
  if(tab==='mx'){
    state.match=resolveMatch(parts[1]);
    state.view=parts[2]==='bbb'||parts[2]==='commentary'?'bbb':'summary';
  }
  return state;
}

function hashFromState(state){
  let hash=state.tab;
  if(state.tab==='mx'){
    const match=state.match||latestMatch();
    hash+='/'+match;
    if(state.view==='bbb'&&MATCHES_WITH_BBB.includes(match))hash+='/bbb';
  }
  return hash;
}

function updateHash(state,replace){
  const url='#'+hashFromState(state);
  if(location.hash===url)return;
  if(replace)history.replaceState(null,'',url);
  else location.hash=url;
}

function navBtnForTab(tabId){
  let btn=null;
  document.querySelectorAll('.nav button').forEach(b=>{
    const oc=b.getAttribute('onclick')||'';
    if(oc.includes("'"+tabId+"'"))btn=b;
  });
  return btn;
}

function matchBtnForId(matchId){
  let btn=null;
  document.querySelectorAll('.mtb').forEach(b=>{
    const oc=b.getAttribute('onclick')||'';
    if(oc.includes("'"+matchId+"'"))btn=b;
  });
  return btn;
}

function deactivateMatches(){
  document.querySelectorAll('.md2').forEach(d=>d.classList.remove('active'));
  document.querySelectorAll('.mtb').forEach(b=>b.classList.remove('active'));
}

function activateTab(tabId,btn){
  document.querySelectorAll('.tab').forEach(p=>p.classList.remove('active'));
  document.querySelectorAll('.nav button').forEach(b=>b.classList.remove('active'));
  const tabEl=document.getElementById('tab-'+tabId);
  if(tabEl)tabEl.classList.add('active');
  const navBtn=btn||navBtnForTab(tabId);
  if(navBtn)navBtn.classList.add('active');
  if(tabId!=='mx')deactivateMatches();
}

function activateMatchView(matchId,view){
  const root=document.getElementById('match-'+matchId);
  if(!root)return;
  document.querySelectorAll('.md2').forEach(d=>d.classList.remove('active'));
  document.querySelectorAll('.mtb').forEach(b=>b.classList.remove('active'));
  root.classList.add('active');
  const mtb=matchBtnForId(matchId);
  if(mtb)mtb.classList.add('active');
  root.querySelectorAll('.mmtb').forEach(b=>b.classList.remove('active'));
  root.querySelectorAll('.mmview').forEach(v=>v.classList.remove('active'));
  const hasBbb=!!root.querySelector('#match-'+matchId+'-bbb');
  const useView=view==='bbb'&&hasBbb?'bbb':'summary';
  const panel=document.getElementById('match-'+matchId+'-'+useView);
  if(panel)panel.classList.add('active');
  const btns=root.querySelectorAll('.mmtb');
  if(btns.length>=2)btns[useView==='bbb'?1:0].classList.add('active');
}

function applyHash(){
  const state=parseHash();
  activateTab(state.tab);
  if(state.tab==='mx'){
    const matchId=resolveMatch(state.match);
    const view=state.view||'summary';
    activateMatchView(matchId,view);
    const raw=location.hash.replace(/^#/,'');
    const parts=raw.split('/').filter(Boolean);
    if(parts.length===1)updateHash({tab:'mx',match:matchId,view},true);
  }
}

function showMatchView(matchId,view,btn,skipHash){
  activateMatchView(matchId,view);
  if(!skipHash)updateHash({tab:'mx',match:matchId,view},true);
  if(btn){
    const root=document.getElementById('match-'+matchId);
    if(root){
      root.querySelectorAll('.mmtb').forEach(b=>b.classList.remove('active'));
      btn.classList.add('active');
    }
  }
}

function toggleBbbOver(id){
  const el=document.getElementById(id);
  if(!el)return;
  const open=!el.classList.toggle('collapsed');
  const hd=el.querySelector('.bbb-over-hd');
  if(hd)hd.setAttribute('aria-expanded',open?'true':'false');
}

function showTab(id,btn,skipHash){
  activateTab(id,btn);
  if(skipHash)return;
  if(id==='mx'){
    const match=latestMatch();
    activateMatchView(match,'summary');
    updateHash({tab:'mx',match,view:'summary'},true);
  }else{
    updateHash({tab:id},true);
  }
}

function showMatch(id,btn,skipHash){
  activateMatchView(id,'summary');
  if(!skipHash)updateHash({tab:'mx',match:id,view:'summary'},true);
}

function parsePlSortValue(cell){
  const t=(cell?.textContent||'').trim().replace(/\\u2212/g,'-').replace(/^\\+/,'');
  const n=parseFloat(t);
  return Number.isFinite(n)?n:t.toLowerCase();
}

function sortPlTable(table,keys){
  const tbody=table.querySelector('tbody');
  if(!tbody)return;
  const rows=[...tbody.querySelectorAll('tr')];
  rows.sort((a,b)=>{
    for(const{k,dir}of keys){
      const va=parsePlSortValue(a.cells[k]);
      const vb=parsePlSortValue(b.cells[k]);
      if(va<vb)return dir==='asc'?-1:1;
      if(va>vb)return dir==='asc'?1:-1;
    }
    return 0;
  });
  rows.forEach(r=>tbody.appendChild(r));
}

function setPlSortIndicator(table,col,dir){
  table.querySelectorAll('thead th.th-sort').forEach(th=>{
    th.classList.remove('asc','desc');
  });
  const th=table.querySelectorAll('thead th')[col];
  if(th)th.classList.add('th-sort',dir);
}

function initPlTableSort(){
  const tab=document.getElementById('tab-pl');
  if(!tab)return;
  const tables=[...tab.querySelectorAll('table.dt')];
  tables.forEach(table=>{
    table.querySelectorAll('thead th').forEach((th,ci)=>{
      if(ci===0)return;
      th.classList.add('th-sort');
      th.addEventListener('click',()=>{
        const asc=th.classList.contains('asc');
        const active=th.classList.contains('asc')||th.classList.contains('desc');
        const dir=active&&asc?'desc':'asc';
        setPlSortIndicator(table,ci,dir);
        sortPlTable(table,[{k:ci,dir}]);
      });
    });
  });
  const bowl=tables[1];
  if(bowl){
    sortPlTable(bowl,[{k:4,dir:'desc'},{k:7,dir:'asc'}]);
    setPlSortIndicator(bowl,4,'desc');
  }
}

window.addEventListener('hashchange',applyHash);
applyHash();
initPlTableSort();
"""


def extract_match_block(html: str, match_id: str) -> tuple[int, int, str]:
    pattern = rf'<div id="match-{match_id}" class="md2[^"]*">'
    m = re.search(pattern, html)
    if not m:
        raise ValueError(f"Match block not found: {match_id}")
    if "mmt" in html[m.start() : m.start() + 200]:
        raise ValueError(f"Match already patched: {match_id}")

    start = m.start()
    pos = m.end()
    depth = 1
    while depth > 0 and pos < len(html):
        next_open = html.find("<div", pos)
        next_close = html.find("</div>", pos)
        if next_close == -1:
            raise ValueError(f"Unclosed match block: {match_id}")
        if next_open != -1 and next_open < next_close:
            depth += 1
            pos = next_open + 4
        else:
            depth -= 1
            end = next_close + len("</div>")
            pos = end
            if depth == 0:
                inner = html[m.end() : next_close].strip()
                return start, end, inner
    raise ValueError(f"Could not parse match block: {match_id}")


def find_div_block_end(html: str, open_tag_end: int) -> int:
    """Return index after closing </div> for div opened just before open_tag_end."""
    pos = open_tag_end
    depth = 1
    while depth > 0 and pos < len(html):
        next_open = html.find("<div", pos)
        next_close = html.find("</div>", pos)
        if next_close == -1:
            raise ValueError("Unclosed div block")
        if next_open != -1 and next_open < next_close:
            depth += 1
            pos = next_open + 4
        else:
            depth -= 1
            end = next_close + len("</div>")
            pos = end
            if depth == 0:
                return end
    raise ValueError("Could not find div block end")


def strip_broken_prepended_js(html: str) -> str:
    """Remove raw JS accidentally prepended before <!DOCTYPE html>."""
    if html.lstrip().startswith("function showMatchView"):
        idx = html.find("<!DOCTYPE")
        if idx != -1:
            return html[idx:]
    return html


def inject_css(html: str) -> str:
    pattern = r"/\* Match sub-tabs:.*?(?=\n</style>)"
    if re.search(pattern, html, re.DOTALL):
        return re.sub(pattern, CSS.strip(), html, count=1, flags=re.DOTALL)
    if ".bbb-inn-bar{" in html:
        return html
    return html.replace("</style>", CSS + "\n</style>", 1)


def inject_js(html: str) -> str:
    html = strip_broken_prepended_js(html)
    html = re.sub(
        r"<script>\s*(?:// Tab IDs|const TAB_IDS|function showMatchView|function showTab).*?</script>\s*",
        "",
        html,
        flags=re.DOTALL,
    )
    html = html.replace("</body>", "<script>\n" + APP_JS + "\n</script>\n</body>", 1)
    return html


def wrap_match(html: str, match_id: str) -> str:
    start, end, inner = extract_match_block(html, match_id)
    bbb_file = BBB_DIR / f"{match_id}.html"
    bbb_html = bbb_file.read_text(encoding="utf-8") if bbb_file.exists() else ""

    wrapped = (
        f'<div id="match-{match_id}" class="md2">\n'
        f'  <div class="mmt">\n'
        f'    <button type="button" class="mmtb active" onclick="showMatchView(\'{match_id}\',\'summary\',this)">Summary</button>\n'
        f'    <button type="button" class="mmtb" onclick="showMatchView(\'{match_id}\',\'bbb\',this)">Commentary</button>\n'
        f"  </div>\n"
        f'  <div id="match-{match_id}-summary" class="mmview active">\n'
        f"{inner}\n"
        f"  </div>\n"
        f'  <div id="match-{match_id}-bbb" class="mmview">\n'
        f"{bbb_html}\n"
        f"  </div>\n"
        f"</div>"
    )
    return html[:start] + wrapped + html[end:]


def refresh_bbb_panels(html: str) -> str:
    for match_id in MATCHES_WITH_BBB:
        bbb_file = BBB_DIR / f"{match_id}.html"
        if not bbb_file.exists():
            continue
        bbb_html = bbb_file.read_text(encoding="utf-8")
        marker = f'id="match-{match_id}-bbb" class="mmview"'
        m = re.search(rf"<div {re.escape(marker)}>", html)
        if not m:
            continue
        content_start = m.end()
        content_end = find_div_block_end(html, content_start) - len("</div>")
        html = html[:content_start] + "\n" + bbb_html + "\n  " + html[content_end:]
    return html


def _depth_and_stack_before(html: str, pos: int) -> tuple[int, list[str]]:
    """Return div nesting depth and id stack immediately before `pos`."""
    depth = 0
    stack: list[str] = []
    i = 0
    while i < pos:
        if html.startswith("<div", i) and (i + 4 >= len(html) or html[i + 4] in " >/"):
            gt = html.find(">", i)
            if gt == -1 or gt >= pos:
                break
            tag = html[i : gt + 1]
            id_m = re.search(r'\bid="([^"]+)"', tag)
            stack.append(id_m.group(1) if id_m else "?")
            depth += 1
            i = gt + 1
        elif html.startswith("</div>", i):
            if stack:
                stack.pop()
            depth -= 1
            i += 6
        else:
            i += 1
    return depth, stack


def _tab_pl_opens_inside_tab_mx(html: str) -> bool:
    players = html.find("<!-- PLAYERS -->")
    tab_pl = html.find('id="tab-pl"')
    if players == -1 or tab_pl == -1:
        return False
    _, stack = _depth_and_stack_before(html, tab_pl)
    return "tab-mx" in stack


def fix_tab_mx_boundary(html: str) -> str:
    """Remove premature </div> after match-m2 that closes tab-mx before M5/M6."""
    pattern = (
        r'(id="match-m2-bbb" class="mmview">.*?</div>\s*</div>)\s*</div>\s*\n\s*<!-- M5 -->'
    )
    html = re.sub(pattern, r"\1\n\n  <!-- M5 -->", html, count=1, flags=re.DOTALL)
    # Remove spurious close inserted before match-m6 (leftover from nested-block fix).
    html = re.sub(
        r"\n\s*<!-- M6 -->\s*</div>\s*\n\s*<!-- end m5 -->\n\s*<div id=\"match-m6\"",
        '\n\n  <!-- M6 -->\n  <div id="match-m6"',
        html,
        count=1,
    )
    html = re.sub(
        r"\n\s*<!-- M6 -->\s*</div>\s*\n\s*<div id=\"match-m6\"",
        '\n\n  <!-- M6 -->\n  <div id="match-m6"',
        html,
        count=1,
    )
    # tab-pl/tab-lb must be siblings of tab-mx inside .wrap (not nested, not outside).
    if not re.search(r'id="tab-pl"[^>]*class="tab"', html):
        return html

    for _ in range(8):
        if not _tab_pl_opens_inside_tab_mx(html):
            break
        html = re.sub(
            r"\n\s*<!-- PLAYERS -->",
            "\n</div>\n\n<!-- PLAYERS -->",
            html,
            count=1,
        )

    for _ in range(8):
        tab_pl = html.find('id="tab-pl"')
        if tab_pl == -1:
            break
        depth, _ = _depth_and_stack_before(html, tab_pl)
        if depth >= 1:
            break
        updated = re.sub(
            r"(\n\s*)</div>(\s*\n+\s*<!-- PLAYERS -->)",
            r"\1\2",
            html,
            count=1,
        )
        if updated == html:
            break
        html = updated

    return html


def fix_tab_pl_boundary(html: str) -> str:
    """Close #tab-pl / .pgrid correctly; keep all .pc cards inside #tab-pl."""
    # Extra </div> on fielding cards closes #tab-pl early (Ariyan / Avyaan).
    html = re.sub(
        r'(<span class="psl">Run Outs</span><span class="psv">1</span></div></div></div>)</div>\s*\n'
        r'      <div class="pc"><div class="pnb">Avyaan',
        r'\1\n      <div class="pc"><div class="pnb">Avyaan',
        html,
        count=1,
    )
    html = re.sub(
        r'(<span class="psl">Run Outs</span><span class="psv">3</span></div></div></div>)</div>\s*\n'
        r'      <div class="pc"><div class="pnb">Krish',
        r'\1\n      <div class="pc"><div class="pnb">Krish',
        html,
        count=1,
    )
    # Extra </div> on bowling-only cards before the next .pc (Veer, Kaiyan, Drish).
    for dots_val in ("13", "16", "11"):
        html = re.sub(
            rf'(<div class="psr"><span class="psl">Dots</span><span class="psv">{dots_val}</span></div></div></div>)</div>\s*\n'
            r'(\s*<div class="pc"><div class="pnb">)',
            r"\1\n\2",
            html,
            count=1,
        )
    # Shyam card missing .pc close (only when fielding ends with two </div>).
    html = re.sub(
        r'(<span class="psl">Catches</span><span class="psv">1</span></div></div>)\s*\n'
        r'      <div class="pc"><div class="pnb">Qaim',
        r'\1</div>\n      <div class="pc"><div class="pnb">Qaim',
        html,
        count=1,
    )
    # Viaan (last card) missing .pc close before .pgrid close.
    html = re.sub(
        r'(<span class="psl">Run Outs</span><span class="psv">\d+</span></div></div>)\s*\n'
        r"    </div>\s*\n  </div>\s*\n</div>\s*\n\s*\n<!-- LEADERS -->",
        r"\1</div>\n    </div>\n  </div>\n</div>\n\n<!-- LEADERS -->",
        html,
        count=1,
    )
    # Repair accidental backslash-escaped quotes from older patch runs.
    html = html.replace('<div class=\\"pc\\">', '<div class="pc">')
    html = html.replace('<div class=\\"pnb\\">', '<div class="pnb">')
    return html


def fix_tab_lb_boundary(html: str) -> str:
    """Remove extra </div> after #tab-lb that closes .wrap before #tab-ru."""
    pattern = (
        r'(<div class="lbr"><div class="lbrk rn">4</div><div class="lbn">Taran</div><div class="lbv">1</div></div></div>)\n'
        r'    </div></div>\n'
        r'  </div>\n'
        r'</div>\n\n'
        r'<!-- RULES -->'
    )
    replacement = (
        r"\1\n\n"
        r"    </div>\n"
        r"  </div>\n"
        r"</div>\n\n"
        r"<!-- RULES -->"
    )
    return re.sub(pattern, replacement, html, count=1)


def fix_nested_match_blocks(html: str) -> str:
    """Close match blocks that were left open (e.g. m2 nested inside m4)."""
    pattern = r'<div id="match-(m\d+)" class="md2[^"]*">'
    matches = list(re.finditer(pattern, html))
    inserts: list[tuple[int, str]] = []
    for i, m in enumerate(matches[:-1]):
        outer_id = m.group(1)
        inner = matches[i + 1]
        if inner.start() <= m.end():
            continue
        outer_end = find_div_block_end(html, m.end())
        if inner.start() < outer_end:
            inserts.append((inner.start(), f"</div>\n\n  <!-- end {outer_id} -->\n\n  "))
    for pos, text in sorted(inserts, reverse=True):
        html = html[:pos] + text + html[pos:]
    return html


def fix_broken_onclick_quotes(html: str) -> str:
    return html.replace("showMatchView(\\'", "showMatchView('").replace("\\',", "',")


def update_subtab_buttons(html: str) -> str:
    html = fix_broken_onclick_quotes(html)

    def summary_btn(m: re.Match[str]) -> str:
        mid = m.group(1)
        return (
            f'<button type="button" class="mmtb active" '
            f'onclick="showMatchView(\'{mid}\',\'summary\',this)">Summary</button>'
        )

    def bbb_btn(m: re.Match[str]) -> str:
        mid = m.group(1)
        return (
            f'<button type="button" class="mmtb" '
            f'onclick="showMatchView(\'{mid}\',\'bbb\',this)">Commentary</button>'
        )

    html = re.sub(
        r'<button(?:\s+type="button")?\s+class="mmtb active" onclick="showMatchView\(\'([^\']+)\',\'summary\',this\)">[^<]*</button>',
        summary_btn,
        html,
    )
    html = re.sub(
        r'<button(?:\s+type="button")?\s+class="mmtb" onclick="showMatchView\(\'([^\']+)\',\'bbb\',this\)">[^<]*</button>',
        bbb_btn,
        html,
    )
    return html


def match_hash(match_num: int) -> str:
    mid = f"m{match_num}"
    if mid in WALKOVER_MATCHES:
        return f"#mx/{mid}"
    if mid in MATCHES_WITH_BBB:
        return f"#mx/{mid}/bbb"
    if match_num <= 6:
        return f"#mx/{mid}"
    return "#mx"


def update_overview_fixtures_scorecard_links(html: str) -> str:
    """Rename Sheet -> Scorecard; table links open Summary (#mx/mN), not bbb."""
    html = html.replace('<th class="c">Sheet</th>', '<th class="c">Scorecard</th>')
    html = html.replace("&#128202; Sheet</a>", "&#128202; Scorecard</a>")
    html = re.sub(
        r'(<a class="sl" href="#mx/m)(\d+)/bbb(">&#128202;)',
        r"\1\2\3",
        html,
    )
    return html


def replace_spreadsheet_links(html: str) -> str:
    def sub_sheet_link(m: re.Match[str]) -> str:
        tag = m.group(0)
        gid_m = re.search(r"gid=(\d+)", tag)
        if not gid_m:
            return tag.replace(m.group(1), "#mx")
        gid = gid_m.group(1)
        fixture_gid = {
            "104729847": 1,
            "737570712": 2,
            "438479434": 3,
            "1996740206": 4,
            "669851544": 5,
            "489440707": 6,
            "1519458298": 7,
            "978153398": 8,
            "1809916539": 9,
            "267954395": 10,
            "1235630778": 11,
            "1283033244": 12,
        }
        num = fixture_gid.get(gid, 0)
        href = match_hash(num) if num else "#mx"
        tag = re.sub(r'href="[^"]*"', f'href="{href}"', tag)
        if "Open Scorecard in Google Sheets" in tag:
            text = "Walkover — no scorecard" if num in (1, 3) else "Open Commentary scorecard"
            tag = re.sub(r">[^<]*</a>", f">{text}</a>", tag)
        elif "Open Full Scorecard in Google Sheets" in tag:
            tag = re.sub(r">[^<]*</a>", ">Open Commentary scorecard</a>", tag)
        elif "Open Full P1 Scorecard in Google Sheets" in tag:
            tag = re.sub(r">[^<]*</a>", ">Open Practice tab</a>", tag)
            tag = re.sub(r'href="[^"]*"', 'href="#pr"', tag)
        elif "Full Season Scoresheet" in tag:
            return ""
        return tag

    html = re.sub(
        r'(<a[^>]*href="https://docs\.google\.com/spreadsheets[^"]*"[^>]*>.*?</a>)',
        sub_sheet_link,
        html,
        flags=re.DOTALL,
    )
    html = re.sub(r'(<a class="sl" href="#[^"]*") target="_blank"', r"\1", html)
    html = re.sub(r" &nbsp;&middot;&nbsp; #mx", "", html)
    return html


def update_visible_labels(html: str) -> str:
    """Rename Ball by Ball → Commentary in patched index (idempotent)."""
    html = html.replace("Ball by Ball", "Commentary")
    html = html.replace("Ball-by-ball", "Commentary")
    html = html.replace("Open Ball by Ball scorecard", "Open Commentary scorecard")
    return html


def main() -> None:
    html = INDEX.read_text(encoding="utf-8")
    html = inject_css(html)
    html = fix_tab_mx_boundary(html)
    html = fix_tab_pl_boundary(html)
    html = fix_tab_lb_boundary(html)
    html = fix_nested_match_blocks(html)
    html = update_subtab_buttons(html)
    for match_id in MATCHES_WITH_BBB:
        marker = f'id="match-{match_id}"'
        pos = html.find(marker)
        if pos == -1:
            html = wrap_match(html, match_id)
            continue
        snippet = html[pos : pos + 200]
        if "mmt" not in snippet:
            html = wrap_match(html, match_id)
    html = refresh_bbb_panels(html)
    html = fix_nested_match_blocks(html)
    html = replace_spreadsheet_links(html)
    html = update_overview_fixtures_scorecard_links(html)
    html = update_visible_labels(html)
    html = inject_js(html)
    html = fix_tab_mx_boundary(html)
    html = fix_tab_lb_boundary(html)
    html = fix_tab_pl_boundary(html)
    html = fix_nested_match_blocks(html)
    INDEX.write_text(html, encoding="utf-8")
    print(f"Patched {INDEX}")


if __name__ == "__main__":
    main()
