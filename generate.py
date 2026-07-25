#!/usr/bin/env python3
"""Generate tilbudsavis HTML — retro/monospace design med kvalitetsinfo."""
import json, os, sys
from datetime import datetime
from html import escape

# ── Butikk-konstanter (synkronisert med pipeline) ───────────────────────────

STORE_KEY = {
    'Kiwi': 'kiwi', 'Rema 1000': 'rema', 'Extra': 'extra',
    'Bunnpris': 'bunnpris', 'Spar': 'spar', 'Obs': 'obs', 'Meny': 'meny',
    'Europris': 'europris',
}

STORE_LABEL = {
    'Kiwi': 'Kiwi Mysen', 'Rema 1000': 'Rema 1000 Mysen',
    'Extra': 'Extra Mysen', 'Bunnpris': 'Bunnpris',
    'Spar': 'Spar', 'Obs': 'Coop Obs Slitu 🚗',
    'Meny': 'Meny Askim 🚗', 'Europris': 'Europris Mysen',
}

STORE_ALIASES = {
    'Coop Obs': 'Obs', 'COOP OBS': 'Obs', 'Obs!': 'Obs',
    'Rema 1000': 'Rema 1000', 'REMA 1000': 'Rema 1000', 'Rema': 'Rema 1000',
    'Coop Prix': 'Extra', 'COOP PRIX': 'Extra',
    'MENY': 'Meny', 'Meny': 'Meny',
    'SPAR': 'Spar', 'Eurospar': 'Spar',
    'KIWI': 'Kiwi', 'Kiwi': 'Kiwi',
}

BLOCKED_STORES = {'Joker', 'Coop Mega', 'Nærbutikken', 'Matkroken', 'Mega', 'Gigaboks'}

def is_allowed_store(name):
    n = name.strip().lower()
    for b in BLOCKED_STORES:
        if b.lower() in n:
            return False
    return True

def is_grocery(store):
    return any(kw in store.lower().split() for kw in ['kiwi','rema','coop','extra','bunnpris','spar','obs','meny','europris'])

def normalize_store(name):
    name = name.strip()
    for alias, canonical in STORE_ALIASES.items():
        if name == alias or name.startswith(alias) or alias in name:
            return canonical
    return name

CAT_NAV = {
    'Kylling':'Kylling','Storfe':'Storfe','Svin':'Svin',
    'Laks':'Laks','Reker/scampi':'Reker','Yoghurt':'Yoghurt',
    'Egg':'Egg','Ost':'Ost','Pålegg':'Pålegg','Brød':'Brød',
    'Snacks':'Snacks','Kaffe':'Kaffe','Drikke':'Drikke',
    'Dessert/is':'Is/Des','Grønnsaker':'Grønt','Frukt':'Frukt',
    'Ingredienser':'Tørrvarer',
}

CAT_EMOJI = {
    'Kylling':'🐔','Storfe':'🥩','Svin':'🐷','Laks':'🐟','Reker/scampi':'🦐',
    'Yoghurt':'🥛','Egg':'🥚','Ost':'🧀','Pålegg':'🥪','Brød':'🍞',
    'Snacks':'🍫','Kaffe':'☕','Drikke':'🥤','Dessert/is':'🍦',
    'Grønnsaker':'🥦','Frukt':'🍎','Ingredienser':'🧂',
}

ALL_CATEGORIES = {
    'Kylling', 'Storfe', 'Svin', 'Laks', 'Fisk', 'Reker/scampi',
    'Yoghurt', 'Egg', 'Ost', 'Pålegg', 'Brød',
    'Snacks', 'Kaffe', 'Drikke', 'Dessert/is',
    'Grønnsaker', 'Frukt', 'Ingredienser',
}


def generate_html(deals, output_path="index.html"):
    now = datetime.now()
    iso = now.isocalendar()
    week_label = f"Uke {iso[1]}"
    generated = now.strftime("%d.%m.%Y kl %H:%M")

    # ── Metadata ──────────────────────────────────────────────────────────
    meta = deals.get('_meta', {})
    quality_score = meta.get('quality_score')
    total_products = meta.get('total_products')
    total_products = total_products or sum(len(c.get("items",[])) for c in deals.get("categories",[]))

    # Missing categories
    found_cats = set(c['name'] for c in deals.get("categories",[]))
    missing_cats = ALL_CATEGORIES - found_cats
    missing_cats.discard('Fisk')  # supplerende kategori

    # ── Filter and collect stores ────────────────────────────────────────
    all_stores = set()
    for cat in deals.get("categories", []):
        kept = []
        for item in cat.get("items", []):
            store_raw = item.get("store", "")
            if not is_allowed_store(store_raw):
                continue
            kept.append(item)
            all_stores.add(normalize_store(store_raw))
        cat["items"] = kept
    for p in list(deals.get("top_picks", [])):
        if not is_allowed_store(p.get("store", "")):
            deals["top_picks"].remove(p)
            continue
        for s in p.get("store", "").split("/"):
            all_stores.add(normalize_store(s.strip()))

    store_order = ["Kiwi","Rema 1000","Extra","Bunnpris","Spar","Obs","Meny","Europris"]
    sorted_stores = sorted(all_stores, key=lambda s: store_order.index(s) if s in store_order else 99)

    # ── Store pills ──────────────────────────────────────────────────────
    pills = '<span class="store-badge active" data-store="all" onclick="filterStore(\'all\')">🌐 Alle</span>\n'
    for s in sorted_stores:
        key = STORE_KEY.get(s, s.lower().replace(' ',''))
        label = STORE_LABEL.get(s, s)
        pills += f'  <span class="store-badge" data-store="{key}" onclick="filterStore(\'{key}\')">{label}</span>\n'

    # ── Cat nav ──────────────────────────────────────────────────────────
    cat_nav = ''
    for ci, cat in enumerate(deals.get("categories", [])):
        cid = f"cat{ci}"
        short = CAT_NAV.get(cat['name'], cat['name'][:8])
        cat_nav += f'<a href="#{cid}">{short}</a>'

    # ── Top 10 ───────────────────────────────────────────────────────────
    top10 = ''
    for p in deals.get("top_picks", [])[:10]:
        name = escape(p.get("name",""))
        price = escape(p.get("price",""))
        merknad = escape(p.get("merknad",""))
        mengde = escape(p.get("mengde","") or '')
        store = normalize_store(p.get("store",""))
        skey = STORE_KEY.get(store, store.lower().replace(' ',''))
        label = STORE_LABEL.get(store, store)
        mn = f' ({merknad})' if merknad else ''
        md = f' {mengde}' if mengde else ''
        top10 += f'<li data-store-filter="{skey}"><strong>{label}</strong> — {name}{md} <strong class="price">{price}</strong>{mn}</li>\n'

    # ── Categories med anbefalt butikk ────────────────────────────────────
    cats_html = ''
    cat_store_winners = {}
    
    def _render_item(tbl, item, is_rec=False):
        """Hjelpefunksjon for å rendere en tabell-rad."""
        name = escape(item.get("name",""))
        mengde = escape(item.get("mengde","") or '')
        price = escape(item.get("price",""))
        merknad = escape(item.get("merknad",""))
        store = normalize_store(item.get("store",""))
        skey = STORE_KEY.get(store, store.lower().replace(' ',''))
        label = STORE_LABEL.get(store, store)
        is_winner = bool(merknad) and ('spar' in merknad.lower() or 'før' in merknad.lower())
        cls = ' class="rec"' if is_rec else (' class="winner"' if is_winner else ' class="other-store"')
        return tbl + f'<tr{cls} data-store="{skey}"><td class="vare">{name}</td><td class="price right">{price}</td><td class="mengde">{mengde}</td><td class="store">{label}</td><td class="desc">{merknad}</td></tr>\n'
    
    for ci, cat in enumerate(deals.get("categories", [])):
        items = cat.get("items", [])
        if not items:
            continue
        cid = f"cat{ci}"
        emoji = CAT_EMOJI.get(cat['name'], '📦')
        
        # Score hver butikk i kategorien
        store_score = {}
        for item in items:
            store = normalize_store(item.get("store",""))
            if store not in store_score:
                store_score[store] = {'count': 0, 'with_savings': 0, 'total_savings': 0}
            store_score[store]['count'] += 1
            mn = item.get("merknad","")
            if mn and ('spar' in mn.lower() or 'før' in mn.lower()):
                store_score[store]['with_savings'] += 1
                # Estimér spart beløp fra merknad
                import re as _re
                m = _re.search(r'spar\s+(\d+)', mn.lower())
                if m:
                    store_score[store]['total_savings'] += int(m.group(1))
        
        # Finn beste butikk for denne kategorien
        best_store = None
        best_score = -1
        for store, sc in store_score.items():
            # Vekt: deals med rabatt (x3) + antall deals (x1) + spart beløp (x2)
            score = sc['with_savings'] * 3 + sc['count'] * 1 + (sc['total_savings'] // 10)
            if score > best_score:
                best_score = score
                best_store = store
        
        cat_store_winners[cat['name']] = best_store
        best_label = STORE_LABEL.get(best_store, best_store) if best_store else ''
        best_key = STORE_KEY.get(best_store, '') if best_store else ''
        
        # Sorter: anbefalt butikk først, så andre butikker
        rec_items = [it for it in items if normalize_store(it.get("store","")) == best_store]
        other_items = [it for it in items if normalize_store(it.get("store","")) != best_store]
        
        tbl = '<table>\n<tr><th>Vare</th><th class="right">Pris</th><th>Mengde</th><th>Butikk</th><th>Merknad</th></tr>\n'
        
        # Anbefalt butikks varer først (med highlight)
        for item in rec_items:
            tbl = _render_item(tbl, item, is_rec=True)
        
        # Andre butikkers varer (dempet)
        if other_items:
            for item in other_items:
                tbl = _render_item(tbl, item, is_rec=False)
        
        tbl += '</table>'
        
        # Kategori-header med anbefalt butikk
        best_tag = f' <span class="best-store">🏪 {best_label}</span>' if best_label else ''
        cats_html += f'\n<h2 id="{cid}">{emoji} {escape(cat["name"])}{best_tag}</h2>\n{tbl}\n'
    
    # ── Handleplan-seksjon ──────────────────────────────────────────────
    handleplan = ''
    if cat_store_winners:
        from collections import Counter
        winner_counts = Counter(cat_store_winners.values())
        top_stores = winner_counts.most_common(3)
        
        handleplan = '<div class="handleplan">\n'
        handleplan += '<h3>🛒 Anbefalt handleplan</h3>\n'
        handleplan += '<p>Basert på ukas tilbud, her er butikkene som dekker mest:</p>\n'
        handleplan += '<div class="handleplan-grid">\n'
        
        for store, count in top_stores:
            if store and store in STORE_LABEL:
                label = STORE_LABEL[store]
                skey = STORE_KEY.get(store, '')
                # Finn hvilke kategorier denne butikken vinner
                cats_won = [c for c, s in cat_store_winners.items() if s == store]
                cat_emojis = ' '.join(CAT_EMOJI.get(c, '📦') for c in cats_won[:5])
                handleplan += f'  <div class="handleplan-card" onclick="filterStore(\'{skey}\')">'
                handleplan += f'<h4>🥇 {label}</h4>'
                handleplan += f'<p class="handleplan-cats">Best i {count} kategorier</p>'
                handleplan += f'<p class="handleplan-emojis">{cat_emojis}</p>'
                # Vis de beste kjøpene hos denne butikken
                best_items = []
                for p in deals.get("top_picks", []):
                    if normalize_store(p.get("store","")) == store and len(best_items) < 2:
                        best_items.append(f'{escape(p["name"])} {escape(p["price"])}')
                if best_items:
                    handleplan += f'<p class="handleplan-items">{" · ".join(best_items)}</p>'
                handleplan += '</div>\n'
        
        handleplan += '</div>\n</div>\n'

    # ── Missing categories warning ──────────────────────────────────────
    missing_html = ''
    if missing_cats:
        missing_html = '<div class="missing-cats"><h3>⚠️ Mangler data for:</h3><p>'
        missing_html += ', '.join(sorted(missing_cats))
        missing_html += '</p><p class="hint">Pipeline har ikke funnet gode tilbud i disse kategoriene denne uken.</p></div>'

    # ── Quality badge ────────────────────────────────────────────────────
    quality_html = ''
    if quality_score is not None:
        color = '#2d5a27' if quality_score >= 80 else '#8b4513' if quality_score >= 60 else '#c0392b'
        quality_html = f'<div class="quality-badge" style="border-left:4px solid {color}">'
        quality_html += f'📊 Datakvalitet: <strong>{quality_score}/100</strong>'
        if total_products:
            quality_html += f' · {total_products} varer'
        quality_html += '</div>'

    # ── Shop cards ───────────────────────────────────────────────────────
    shop_cards = ''
    store_counts = {}
    for c in deals.get("categories", []):
        for i in c.get("items", []):
            s = normalize_store(i.get("store",""))
            store_counts[s] = store_counts.get(s, 0) + 1
    for s in sorted_stores:
        if s in STORE_LABEL:
            skey = STORE_KEY.get(s, '')
            label = STORE_LABEL[s]
            count = store_counts.get(s, 0)
            shop_cards += f'  <div class="shop-card" onclick="filterStore(\'{skey}\')"><h4>{label}</h4><p>{count} tilbud</p></div>\n'

    # ── HTML template ────────────────────────────────────────────────────
    html = f"""<!DOCTYPE html>
<html lang="nb">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Ukens beste tilbud — {week_label}</title>
<style>
  :root {{ --bg: #f5f3e8; --card: #fff; --accent: #2d5a27; --accent2: #8b4513; --border: #d4c9a8; }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Courier New', Courier, monospace; background: var(--bg); color: #222; padding: 20px; max-width: 1100px; margin: auto; }}
  h1 {{ font-size: 1.6em; text-transform: uppercase; letter-spacing: 2px; border-bottom: 3px solid var(--accent); padding-bottom: 10px; margin-bottom: 20px; color: var(--accent); }}
  h2 {{ font-size: 1.1em; text-transform: uppercase; letter-spacing: 1px; background: var(--accent); color: #fff; padding: 8px 14px; margin: 30px 0 15px; display: inline-block; }}
  table {{ width: 100%; border-collapse: collapse; margin-bottom: 15px; background: var(--card); border: 1px solid var(--border); }}
  th {{ background: var(--accent); color: #fff; text-align: left; padding: 6px 10px; font-size: 0.85em; text-transform: uppercase; letter-spacing: 0.5px; }}
  td {{ padding: 5px 10px; border-bottom: 1px solid #eee; font-size: 0.9em; }}
  tr:hover {{ background: #efede0; }}
  .price {{ font-weight: bold; white-space: nowrap; color: var(--accent2); }}
  .right {{ text-align: right; }}
  .vare {{ max-width: 280px; overflow: hidden; text-overflow: ellipsis; }}
  .mengde {{ white-space: nowrap; font-size: 0.85em; color: #555; }}
  .store {{ white-space: nowrap; font-size: 0.85em; }}
  .desc {{ color: #666; font-size: 0.82em; }}
  .winner {{ background: #e8f5e0; }}
  .winner td {{ border-bottom: 1px solid #c8e6b0; }}
  .winner .mengde {{ color: #1b5e20; }}
  .winner .price {{ color: #1b5e20; font-size: 1.05em; }}
  .summary {{ background: var(--card); border: 2px solid var(--accent); padding: 16px; margin: 20px 0; }}
  .summary ol {{ margin-left: 20px; }}
  .summary li {{ margin-bottom: 6px; cursor: pointer; }}
  .summary li:hover {{ text-decoration: underline; }}
  .store-list {{ display: flex; flex-wrap: wrap; gap: 6px; margin: 12px 0; }}
  .store-badge {{ border: 1px solid var(--border); padding: 4px 12px; font-size: 0.85em; background: var(--card); cursor: pointer; user-select: none; }}
  .store-badge:hover, .store-badge.active {{ background: var(--accent); color: #fff; border-color: var(--accent); }}
  .last-updated {{ text-align: right; font-size: 0.8em; color: #888; margin-bottom: 20px; }}
  .hidden {{ display: none !important; }}
  .shop-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 10px; margin: 15px 0; }}
  .shop-card {{ border: 1px solid var(--border); padding: 10px; background: var(--card); cursor: pointer; }}
  .shop-card:hover {{ background: #efede0; }}
  .shop-card h4 {{ font-size: 0.9em; margin-bottom: 4px; }}
  .shop-card p {{ font-size: 0.8em; color: #555; }}
  .cat-nav {{ margin: 12px 0; display: flex; flex-wrap: wrap; gap: 4px; }}
  .cat-nav a {{ font-size: 0.75em; padding: 2px 8px; border: 1px solid var(--border); text-decoration: none; color: #222; }}
  .cat-nav a:hover {{ background: var(--accent); color: #fff; }}
  .quality-badge {{ background: var(--card); padding: 10px 14px; margin-bottom: 15px; font-size: 0.85em; }}
  .missing-cats {{ background: #fff3e0; border: 1px solid #ffe0b2; padding: 12px 16px; margin: 15px 0; font-size: 0.9em; }}
  .missing-cats h3 {{ color: #e65100; font-size: 1em; margin-bottom: 4px; }}
  .missing-cats .hint {{ color: #888; font-size: 0.85em; margin-top: 4px; }}
  .rec {{ background: #e8f5e0; border-left: 3px solid var(--accent); }}
  .rec td {{ border-bottom: 1px solid #c8e6b0; }}
  .rec .price {{ color: #1b5e20; font-size: 1.05em; }}
  .other-store {{ opacity: 0.6; }}
  .other-store:hover {{ opacity: 1; }}
  .best-store {{ font-size: 0.65em; background: #fff; color: var(--accent); padding: 2px 8px; margin-left: 8px; border: 1px solid var(--accent); vertical-align: middle; }}
  .handleplan {{ background: var(--card); border: 2px solid var(--accent); padding: 16px; margin: 20px 0; }}
  .handleplan h3 {{ font-size: 1.1em; color: var(--accent); margin-bottom: 8px; }}
  .handleplan p {{ font-size: 0.85em; color: #555; margin-bottom: 10px; }}
  .handleplan-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 10px; }}
  .handleplan-card {{ border: 1px solid var(--border); padding: 12px; background: #fff; cursor: pointer; transition: all 0.15s; }}
  .handleplan-card:hover {{ background: #efede0; border-color: var(--accent); }}
  .handleplan-card h4 {{ font-size: 0.95em; color: var(--accent); margin-bottom: 4px; }}
  .handleplan-cats {{ font-size: 0.8em; color: #888; }}
  .handleplan-emojis {{ font-size: 1.4em; margin: 4px 0; }}
  .handleplan-items {{ font-size: 0.78em; color: #666; margin-top: 6px; }}
  @media (max-width: 600px) {{ body {{ padding: 10px; }} table {{ font-size: 0.8em; }} td {{ padding: 3px 5px; }} }}
</style>
</head>
<body>

<h1>🛒 Ukens beste tilbud — {week_label}</h1>
<p style="margin-bottom:5px"><strong>Periode:</strong> uke {week_label} | <strong>Område:</strong> Mysen (Indre Østfold)</p>
<p class="last-updated">Oppdatert {generated} | Kilde: eTilbudsavis, Enhver.no</p>

{quality_html}
{missing_html}

{handleplan}

<p style="margin-bottom:8px;font-size:0.9em;"><strong>🔍 Trykk på en butikk</strong> for å filtrere:</p>
<div class="store-list" id="store-filters">
{pills}</div>
<p style="font-size:0.8em;color:#888;margin-bottom:10px;">🚗 = kjøretur (Slitu/Askim)</p>

<div class="cat-nav">
{cat_nav}</div>

<div class="summary">
<h3>🏆 Topp 10 beste kjøp denne uka</h3>
<ol>
{top10}</ol>
</div>

{cats_html}

<h2>📍 Butikker i Mysen-området</h2>
<div class="shop-grid">
{shop_cards}</div>

<div class="summary">
<h3>📊 Oppsummering</h3>
<p>Priser fra eTilbudsavis og Enhver.no — oppdatert {generated}. Klikk på butikknavn for å filtrere varer. Grønn bakgrunn = med rabatt.</p>
</div>

<script>
function filterStore(store) {{
  document.querySelectorAll('#store-filters .store-badge').forEach(b => b.classList.remove('active', 'filter-inactive'));
  if (store === 'all') {{
    document.querySelector('[data-store="all"]').classList.add('active');
  }} else {{
    document.querySelector('[data-store="' + store + '"]').classList.add('active');
    document.querySelector('[data-store="all"]').classList.add('filter-inactive');
  }}
  document.querySelectorAll('[data-store]').forEach(el => {{
    if (el.tagName === 'SPAN' && el.closest('#store-filters')) return;
    const s = el.getAttribute('data-store');
    if (store === 'all') el.classList.remove('hidden');
    else if (s === store) el.classList.remove('hidden');
    else el.classList.add('hidden');
  }});
  document.querySelectorAll('[data-store-filter]').forEach(li => {{
    if (store === 'all') li.classList.remove('hidden');
    else li.getAttribute('data-store-filter') === store ? li.classList.remove('hidden') : li.classList.add('hidden');
  }});
}}

// Dynamisk datalasting fra JSON (latest-data.json)
// Hvis JSON-en oppdateres, vil siden vise nye data uten å måtte generere HTML på nytt.
const DATA_URL = 'latest-data.json';
async function loadDynamicData() {{
  try {{
    const resp = await fetch(DATA_URL + '?t=' + Date.now());
    if (!resp.ok) return; // ingen dynamisk data = bruk statisk HTML
    const data = await resp.json();
    if (!data.products || !data.meta) return;
    
    // Oppdater kvalitets-badge
    const qb = document.querySelector('.quality-badge');
    if (qb && data.meta.quality_score) {{
      const score = data.meta.quality_score;
      const color = score >= 80 ? '#2d5a27' : score >= 60 ? '#8b4513' : '#c0392b';
      qb.style.borderLeftColor = color;
      qb.innerHTML = '📊 Datakvalitet: <strong>' + score + '/100</strong> · ' + data.meta.total_products + ' varer';
    }}
    
    // Oppdater sist-oppdatert
    const upd = document.querySelector('.last-updated');
    if (upd && data.meta.generated) {{
      const dt = new Date(data.meta.generated).toLocaleString('nb-NO', {{day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit'}});
      upd.textContent = 'Oppdatert ' + dt + ' | Kilde: eTilbudsavis, Enhver.no (dynamisk)';
    }}
  }} catch(e) {{
    // stille — bruk statisk HTML som fallback
  }}
}}
loadDynamicData();
</script>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    total = sum(len(c.get("items",[])) for c in deals.get("categories",[]))
    print(f"✅ {output_path} ({len(html)} bytes, {len(sorted_stores)} butikker, {total} varer)")


def push_to_github(repo_dir):
    os.chdir(repo_dir)
    r = os.system("git add index.html && git diff --cached --quiet")
    if r == 0:
        print("ℹ️  Ingen endringer")
        return
    os.system('git commit -m "Oppdater ukens tilbud"')
    os.system("git push origin main")
    print("✅ Pushet til GitHub")


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    if len(sys.argv) > 1:
        path = sys.argv[1]
        if not os.path.isabs(path):
            path = os.path.join(os.getcwd(), path)
        with open(path) as f:
            deals = json.load(f)
    else:
        print("⚠️  Ingen fil — bruker eksempeldata")
        deals = {"top_picks": [], "categories": []}
    generate_html(deals)
    if len(sys.argv) > 2:
        push_to_github(sys.argv[2])
    elif "PUSH" in os.environ:
        push_to_github(os.path.dirname(os.path.abspath(__file__)))
