"""Emit data/exports/paper_explorer.html - a single self-contained page.

No server, no network, no dependencies: open the file and it works. The whole
database is embedded as JSON, which makes the file large (~11 MB) but means it
survives being copied to a laptop or emailed to a co-author.

Deliberately NOT published anywhere - this is unreviewed research data.
"""
from __future__ import annotations

import json
import pathlib
import sqlite3

ROOT = pathlib.Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "paper_explorer.db"
OUT = ROOT / "data" / "exports" / "paper_explorer.html"

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Context Integrity SoK — Paper Explorer</title>
<style>
:root{
  --bg:#fbfaf8; --panel:#fff; --ink:#1c1a17; --muted:#6d6862; --line:#e4e0da;
  --accent:#8a4b2a; --atk:#a4402c; --def:#2f5d7c; --both:#6b4b8a; --none:#8d8880;
  --win:#2f6b4f; --loss:#a4402c; --part:#946a1e; --undet:#8d8880;
}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){
  --bg:#171614; --panel:#211f1c; --ink:#ece8e1; --muted:#9a938a; --line:#36332e;
  --accent:#d9945f; --atk:#e08165; --def:#7fb0d4; --both:#b195d4; --none:#8d8880;
  --win:#6fc095; --loss:#e08165; --part:#d9b164; --undet:#8d8880;}}
:root[data-theme=dark]{
  --bg:#171614; --panel:#211f1c; --ink:#ece8e1; --muted:#9a938a; --line:#36332e;
  --accent:#d9945f; --atk:#e08165; --def:#7fb0d4; --both:#b195d4; --none:#8d8880;
  --win:#6fc095; --loss:#e08165; --part:#d9b164; --undet:#8d8880;}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font:15px/1.55 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}
header{padding:14px 16px;border-bottom:1px solid var(--line);
  display:flex;flex-wrap:wrap;gap:12px;align-items:baseline}
h1{font-size:17px;margin:0;font-weight:650;letter-spacing:-.01em}
.sub{color:var(--muted);font-size:13px}
.wrap{display:grid;grid-template-columns:minmax(300px,380px) 1fr;
  height:calc(100vh - 56px)}
@media(max-width:820px){.wrap{grid-template-columns:1fr;height:auto}
  #list{max-height:46vh}}
#side{border-right:1px solid var(--line);display:flex;flex-direction:column;
  min-height:0;background:var(--panel)}
.controls{padding:10px 12px;border-bottom:1px solid var(--line);
  display:flex;flex-direction:column;gap:8px}
input[type=search]{width:100%;padding:8px 10px;border:1px solid var(--line);
  border-radius:7px;background:var(--bg);color:var(--ink);font-size:14px}
.chips{display:flex;flex-wrap:wrap;gap:5px}
.chip{padding:3px 9px;border:1px solid var(--line);border-radius:999px;
  background:transparent;color:var(--muted);cursor:pointer;font-size:12px}
.chip[aria-pressed=true]{background:var(--ink);color:var(--bg);
  border-color:var(--ink)}
#list{overflow:auto;min-height:0;flex:1}
.item{padding:9px 12px;border-bottom:1px solid var(--line);cursor:pointer}
.item:hover{background:var(--bg)}
.item[aria-selected=true]{background:var(--bg);
  box-shadow:inset 3px 0 0 var(--accent)}
.item .t{font-size:13.5px;line-height:1.35}
.item .m{font-size:11.5px;color:var(--muted);margin-top:3px;
  display:flex;gap:7px;flex-wrap:wrap}
.role{font-weight:650;text-transform:uppercase;letter-spacing:.04em;
  font-size:10.5px}
.role.attack{color:var(--atk)} .role.defense{color:var(--def)}
.role.both{color:var(--both)} .role.neither{color:var(--none)}
main{overflow:auto;padding:22px 26px;min-height:0}
.empty{color:var(--muted);max-width:52ch;margin-top:12vh}
h2{font-size:19px;margin:0 0 6px;line-height:1.3;letter-spacing:-.01em}
.meta{color:var(--muted);font-size:13px;margin-bottom:18px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));
  gap:10px 22px;margin:14px 0 20px}
.f{font-size:13.5px}
.f dt{color:var(--muted);font-size:11px;text-transform:uppercase;
  letter-spacing:.05em;margin-bottom:2px}
.f dd{margin:0;word-break:break-word}
section.tech{border:1px solid var(--line);border-radius:10px;padding:16px;
  margin:18px 0;background:var(--panel)}
section.tech h3{margin:0 0 3px;font-size:15.5px}
.kind{font-size:10.5px;letter-spacing:.06em;text-transform:uppercase;
  font-weight:650;margin-bottom:8px}
.score{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0}
.s{border:1px solid var(--line);border-radius:8px;padding:7px 11px;min-width:96px}
.s b{display:block;font-size:20px;line-height:1.1;font-variant-numeric:tabular-nums}
.s span{font-size:11px;color:var(--muted)}
.s.win b{color:var(--win)} .s.loss b{color:var(--loss)}
.s.part b{color:var(--part)} .s.undet b{color:var(--undet)}
ul.pairs{list-style:none;padding:0;margin:8px 0 0}
ul.pairs li{border-top:1px solid var(--line);padding:9px 0}
.pn{font-size:13.5px}
.tag{font-size:10.5px;font-weight:650;letter-spacing:.04em;
  text-transform:uppercase;padding:1px 7px;border-radius:4px;
  border:1px solid currentColor;margin-left:7px;white-space:nowrap}
.tag.loses{color:var(--loss)} .tag.holds{color:var(--win)}
.tag.partial{color:var(--part)} .tag.undetermined{color:var(--undet)}
.src{font-size:11.5px;color:var(--muted);margin-top:3px}
.ev{font-size:12.5px;color:var(--muted);margin-top:5px;
  border-left:2px solid var(--line);padding-left:9px}
.note{font-size:12.5px;color:var(--muted);background:var(--bg);
  border:1px solid var(--line);border-radius:8px;padding:10px 12px;margin:14px 0}
</style></head><body>
<header>
  <h1>Context Integrity SoK — Paper Explorer</h1>
  <span class="sub" id="counts"></span>
</header>
<div class="wrap">
  <aside id="side">
    <div class="controls">
      <input type="search" id="q" placeholder="Search title, technique, venue, author…">
      <div class="chips" id="roles"></div>
    </div>
    <div id="list"></div>
  </aside>
  <main id="detail"><p class="empty">Pick a paper on the left.<br><br>
  Every number on a paper's card says <em>who reported it</em>. A defense
  paper claiming a win and an attack paper reporting that same defense broken
  are different kinds of evidence, so they are never added together.</p></main>
</div>
<script id="data" type="application/json">__DATA__</script>
<script>
const D = JSON.parse(document.getElementById('data').textContent);
const esc = s => String(s ?? '').replace(/[&<>"]/g, c =>
  ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const OUT = {holds:'defense held', loses:'defense broken',
  partial:'reduced, not stopped', undetermined:'no directional result'};
const DIR = {defense_paper:"the defense paper's own claim",
  attack_paper:'reported by the ATTACK paper'};

let role = 'all', q = '';
const roles = ['all','attack','defense','both','neither'];
document.getElementById('roles').innerHTML = roles.map(r =>
  `<button class="chip" data-r="${r}" aria-pressed="${r==='all'}">${r}</button>`
).join('');
document.getElementById('roles').onclick = e => {
  const b = e.target.closest('.chip'); if (!b) return;
  role = b.dataset.r;
  document.querySelectorAll('.chip').forEach(c =>
    c.setAttribute('aria-pressed', c.dataset.r === role));
  render();
};
document.getElementById('q').oninput = e => { q = e.target.value.toLowerCase(); render(); };

function haystack(p){
  if (p._h) return p._h;
  return p._h = [p.title, p.authors, p.venue, p.year,
    (D.byPaper[p.paper_id]||[]).map(t => t.name).join(' ')]
    .join(' ').toLowerCase();
}
function matches(p){
  if (role !== 'all' && p.role !== role) return false;
  return !q || haystack(p).includes(q);
}

const CAP = 400;
function render(){
  const hits = D.papers.filter(matches);
  document.getElementById('counts').textContent =
    `${hits.length} of ${D.papers.length} papers · ${D.nAttacks} attacks · ` +
    `${D.nDefenses} defenses · ${D.nPairs} reported pairs · ${D.nRuns} runs of our own`;
  document.getElementById('list').innerHTML = hits.slice(0, CAP).map(p => `
    <div class="item" data-id="${p.paper_id}" aria-selected="${p.paper_id===sel}">
      <div class="t">${esc(p.title)}</div>
      <div class="m"><span class="role ${p.role}">${p.role}</span>
        <span>${p.year ?? '—'}</span><span>${esc(p.venue || 'no venue')}</span>
        <span>${esc(p.track || '')}</span></div>
    </div>`).join('') + (hits.length > CAP
      ? `<div class="item" style="color:var(--muted)">…${hits.length-CAP} more — narrow the search</div>` : '');
}
let sel = null;
document.getElementById('list').onclick = e => {
  const it = e.target.closest('.item[data-id]'); if (!it) return;
  sel = it.dataset.id; render(); detail(sel);
  document.getElementById('detail').scrollTop = 0;
};

function scoreRow(cells){
  return `<div class="score">` + cells.map(([n,l,c]) =>
    `<div class="s ${c}"><b>${n}</b><span>${l}</span></div>`).join('') + `</div>`;
}
function pairList(ps){
  if (!ps.length) return `<p class="src">No pair recorded in either direction.</p>`;
  const order = {loses:0, partial:1, holds:2, undetermined:3};
  return `<ul class="pairs">` + ps.slice().sort((a,b)=>order[a.outcome]-order[b.outcome])
    .map(p => `<li>
      <div class="pn">${esc(p.other)}<span class="tag ${p.outcome}">${OUT[p.outcome]}</span></div>
      <div class="src">${DIR[p.direction]}${p.reported_by_title ? ' — ' + esc(p.reported_by_title) : ''}</div>
      ${p.evidence ? `<div class="ev">${esc(p.evidence.slice(0,600))}</div>` : ''}
    </li>`).join('') + `</ul>`;
}

function detail(id){
  const p = D.papers.find(x => x.paper_id === id);
  const techs = D.byPaper[id] || [];
  const f = (l,v) => v ? `<div class="f"><dt>${l}</dt><dd>${esc(v)}</dd></div>` : '';
  let h = `<h2>${esc(p.title)}</h2><div class="meta">
    <span class="role ${p.role}">${p.role} paper</span> ·
    ${esc(p.authors || 'unknown authors')} · ${p.year ?? '—'} ·
    ${esc(p.venue || 'no venue')}${p.url ? ` · <a href="${esc(p.url)}" target="_blank" rel="noopener">link</a>` : ''}</div>
  <div class="grid">
    ${f('track', p.track)}${f('screening', p.screening)}
    ${f('evidence grade', p.evidence_grade)}${f('artifacts released', p.artifacts_released)}
    ${f('citations', p.citation_count)}${f('channel', p.channel)}
    ${f('consequence', p.consequence)}${f('intervention point', p.defense_intervention_point)}
    ${f('persistence', p.temporal_persistence)}${f('doi', p.doi)}${f('arXiv', p.arxiv_id)}
  </div>
  <div class="grid">
    ${f('threat model', p.threat_model)}${f('models evaluated', p.models_evaluated)}
    ${f('benchmarks', p.datasets_benchmarks)}${f('baselines compared', p.baselines_compared)}
    ${f('key result', p.key_result)}${f('stated limitations', p.stated_limitations)}
    ${f('summary', p.technical_summary)}${f('abstract', p.abstract)}
  </div>`;

  for (const t of techs){
    const s = t.score;
    h += `<section class="tech"><div class="kind" style="color:var(--${t.kind==='attack'?'atk':'def'})">
      ${t.kind === 'attack' ? 'Attack introduced' : 'Defense introduced'}</div>
      <h3>${esc(t.name)}</h3>`;
    h += t.kind === 'defense'
      ? scoreRow([[s.attacks_tested,'attacks tested against it',''],
                  [s.self_reported_win,'its paper claims it stopped','win'],
                  [s.refuted,'an attack paper broke it','loss'],
                  [s.partial,'reduced, not stopped','part'],
                  [s.undetermined,'ran, no result given','undet']])
      : scoreRow([[s.defenses_tested,'defenses run against it',''],
                  [s.defenses_broken,'it broke','loss'],
                  [s.defenses_partial,'it only weakened','part'],
                  [s.defenses_held_claimed,'held, per that defense','win'],
                  [s.undetermined,'ran, no result given','undet']]);
    h += pairList(t.pairs) + `</section>`;
  }
  if (!techs.length) h += `<p class="note">This paper is in the corpus but
    introduced neither a named attack nor a named defense — background, a
    survey, or a technique that did not meet the registry's naming bar.</p>`;
  const runs = D.runs.filter(r => techs.some(t => t.name === r.attack));
  if (runs.length) h += `<p class="note">This paper's attack also appears in
    our own executed runs. Those are a separate table and are never mixed into
    the counts above.</p>`;
  document.getElementById('detail').innerHTML = h;
}
render();
</script></body></html>
"""


def main():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    papers = [dict(r) for r in c.execute("SELECT * FROM paper ORDER BY year DESC, title")]

    pair_by_def, pair_by_atk = {}, {}
    for r in c.execute("SELECT * FROM pair"):
        pair_by_def.setdefault(r["defense_name"], []).append(
            {"other": r["attack_name"], "outcome": r["outcome"],
             "direction": r["direction"], "reported_by_title": r["reported_by_title"],
             "evidence": r["evidence"]})
        pair_by_atk.setdefault(r["attack_name"], []).append(
            {"other": r["defense_name"], "outcome": r["outcome"],
             "direction": r["direction"], "reported_by_title": r["reported_by_title"],
             "evidence": r["evidence"]})

    by_paper: dict[str, list] = {}
    for r in c.execute("SELECT * FROM v_defense_scorecard"):
        by_paper.setdefault(r["paper_id"], []).append(
            {"kind": "defense", "name": r["defense"],
             "score": {k: r[k] or 0 for k in
                       ("attacks_tested", "self_reported_win", "refuted",
                        "partial", "undetermined")},
             "pairs": pair_by_def.get(r["defense"], [])})
    for r in c.execute("SELECT * FROM v_attack_scorecard"):
        by_paper.setdefault(r["paper_id"], []).append(
            {"kind": "attack", "name": r["attack"],
             "score": {k: r[k] or 0 for k in
                       ("defenses_tested", "defenses_broken", "defenses_partial",
                        "defenses_held_claimed", "undetermined")},
             "pairs": pair_by_atk.get(r["attack"], [])})

    one = lambda s: c.execute(s).fetchone()[0]
    data = {
        "papers": papers, "byPaper": by_paper,
        "runs": [dict(r) for r in c.execute("SELECT * FROM our_run")],
        "nAttacks": one("SELECT COUNT(*) FROM attack"),
        "nDefenses": one("SELECT COUNT(*) FROM defense"),
        "nPairs": one("SELECT COUNT(*) FROM pair"),
        "nRuns": one("SELECT COUNT(*) FROM our_run"),
    }
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    OUT.write_text(PAGE.replace("__DATA__", blob), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}  ({OUT.stat().st_size/1e6:.1f} MB)")


if __name__ == "__main__":
    main()
