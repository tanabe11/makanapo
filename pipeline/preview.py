"""Generate data/preview.html — a self-contained, filterable viewer of deals.json.

Internal dev tool (output is gitignored). Run:  python3 -m pipeline.preview
Data is embedded in a <script type="application/json"> block (safe for ';' and
'</script>' in values), so the page never breaks on deal text.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEALS = ROOT / "data" / "deals.json"
OUT = ROOT / "data" / "preview.html"

_TEMPLATE = r"""<!doctype html><html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>makanapo — deals preview</title>
<style>
:root{--bg:#faf8f3;--card:#fff;--bd:#e6e2d8;--tx:#2c2c2a;--mut:#6b6a64;}
*{box-sizing:border-box}body{font:15px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;margin:0;background:var(--bg);color:var(--tx)}
.wrap{max-width:1100px;margin:0 auto;padding:24px}
h1{font-size:20px;font-weight:600;margin:0 0 4px}.sub{color:var(--mut);margin:0 0 16px;font-size:13px}
.cards{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:16px}
.c{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:10px 14px;min-width:96px}
.c .n{font-size:22px;font-weight:600}.c .l{font-size:12px;color:var(--mut)}
.ctl{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:12px}
input,select{font:14px inherit;padding:7px 10px;border:1px solid var(--bd);border-radius:8px;background:#fff}
button{font:13px inherit;padding:6px 12px;border:1px solid var(--bd);border-radius:8px;background:#fff;cursor:pointer}
button.on{background:#2c2c2a;color:#fff;border-color:#2c2c2a}
table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--bd);border-radius:10px;overflow:hidden}
th,td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--bd);font-size:13px;vertical-align:top}
th{background:#f1efe8;font-weight:600;cursor:pointer}
tr:last-child td{border-bottom:0}
.b{display:inline-block;padding:2px 8px;border-radius:20px;font-size:12px;font-weight:600}
.active{background:#e1f5ee;color:#0f6e56}.unverified{background:#f1efe8;color:#5f5e5a}.expired{background:#fcebeb;color:#a32d2d}
a{color:#185fa5;text-decoration:none}a:hover{text-decoration:underline}.muted{color:var(--mut)}
</style></head><body><div class="wrap">
<h1>makanapo — 公開データ プレビュー</h1>
<p class="sub">data/deals.json（一次情報・公式のみ）。active=確認済 / unverified=要確認(リンク) / expired=期限切れ。</p>
<div class="cards" id="cards"></div>
<div class="ctl">
  <input id="q" placeholder="検索（店名・割引・地区）" style="flex:1;min-width:200px">
  <span id="statusbtns"></span>
  <select id="cat"><option value="">全カテゴリ</option><option>food</option><option>service</option></select>
  <select id="hood"></select>
</div>
<table><thead><tr>
<th data-k="name">店名</th><th data-k="category">カテゴリ</th><th data-k="neighborhood">地区</th>
<th data-k="discount">割引</th><th data-k="requires_id">ID</th><th data-k="status">状態</th>
<th data-k="last_verified">確認日</th><th>出典</th>
</tr></thead><tbody id="tb"></tbody></table>
<p class="sub" id="count"></p>
</div>
<script type="application/json" id="deals">__PAYLOAD__</script>
<script>
const DATA=JSON.parse(document.getElementById('deals').textContent);
let statusF="",sortK="status",sortDir=1;
const esc=s=>(s==null?"":String(s)).replace(/[&<>]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));
function cards(){const by=s=>DATA.filter(d=>d.status===s).length;
 document.getElementById('cards').innerHTML=[['総数',DATA.length],['active',by('active')],['unverified',by('unverified')],['expired',by('expired')]]
 .map(([l,n])=>`<div class="c"><div class="n">${n}</div><div class="l">${l}</div></div>`).join('');}
function statusBtns(){const s=['','active','unverified','expired'];
 document.getElementById('statusbtns').innerHTML=s.map(v=>`<button data-s="${v}" class="${v===statusF?'on':''}">${v||'全状態'}</button>`).join(' ');
 document.querySelectorAll('#statusbtns button').forEach(b=>b.onclick=()=>{statusF=b.dataset.s;statusBtns();render();});}
function hoods(){const hs=[...new Set(DATA.map(d=>d.neighborhood).filter(Boolean))].sort();
 document.getElementById('hood').innerHTML='<option value="">全地区</option>'+hs.map(h=>`<option>${esc(h)}</option>`).join('');}
function render(){const q=document.getElementById('q').value.toLowerCase();
 const cat=document.getElementById('cat').value,hood=document.getElementById('hood').value;
 let rows=DATA.filter(d=>{if(statusF&&d.status!==statusF)return false;if(cat&&d.category!==cat)return false;
  if(hood&&d.neighborhood!==hood)return false;
  if(q&&!((d.name||'')+(d.discount||'')+(d.neighborhood||'')).toLowerCase().includes(q))return false;return true;});
 rows.sort((a,b)=>{const x=esc(a[sortK]),y=esc(b[sortK]);return x<y?-sortDir:x>y?sortDir:0;});
 document.getElementById('tb').innerHTML=rows.map(d=>`<tr><td>${esc(d.name)}</td>
  <td class="muted">${esc(d.category)}${d.subcategory?' / '+esc(d.subcategory):''}</td>
  <td>${esc(d.neighborhood)}</td><td>${esc(d.discount)||'<span class=muted>（未取得）</span>'}</td>
  <td>${d.requires_id?'✔':''}</td>
  <td><span class="b ${d.status}">${d.status}</span>${d.valid_until?'<br><span class=muted style=font-size:11px>~'+esc(d.valid_until)+'</span>':''}</td>
  <td class="muted">${esc(d.last_verified)}</td>
  <td>${d.source_url?`<a href="${esc(d.source_url)}" target="_blank" rel="noopener">確認 ↗</a>`:''}</td></tr>`).join('');
 document.getElementById('count').textContent=`${rows.length} 件表示 / 全 ${DATA.length} 件`;}
document.querySelectorAll('th[data-k]').forEach(th=>th.onclick=()=>{const k=th.dataset.k;sortDir=(sortK===k)?-sortDir:1;sortK=k;render();});
document.getElementById('q').oninput=render;document.getElementById('cat').onchange=render;document.getElementById('hood').onchange=render;
cards();statusBtns();hoods();render();
</script></body></html>"""


def main() -> int:
    data = json.loads(DEALS.read_text())
    order = {"active": 0, "unverified": 1, "expired": 2}
    data.sort(key=lambda r: (order.get(r.get("status"), 9), r.get("neighborhood") or "zz", r.get("name", "")))
    slim = [
        {
            "name": r.get("name"),
            "category": r.get("category"),
            "subcategory": r.get("subcategory", ""),
            "neighborhood": r.get("neighborhood", ""),
            "discount": r.get("discount", ""),
            "requires_id": bool(r.get("requires_id")),
            "status": r.get("status"),
            "last_verified": r.get("last_verified", ""),
            "valid_until": r.get("valid_until", ""),
            "source_url": r.get("source_url", ""),
        }
        for r in data
    ]
    payload = json.dumps(slim, ensure_ascii=False).replace("</", "<\\/")
    OUT.write_text(_TEMPLATE.replace("__PAYLOAD__", payload), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}  ({len(slim)} records, {dict(Counter(r['status'] for r in slim))})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
