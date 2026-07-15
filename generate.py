#!/usr/bin/env python3
"""Generate tilbudsavis HTML — uke 27 retro design."""
import json, os, sys
from datetime import datetime
from html import escape

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

BLOCKED_STORES = {'Joker', 'Coop Mega', 'Nærbutikken', 'Matkroken', 'Mega'}
GROCERY_KW = ['kiwi','rema','coop','extra','bunnpris','spar','obs','meny','europris']

def is_allowed_store(name):
    n = name.strip().lower()
    for b in BLOCKED_STORES:
        if b.lower() in n:
            return False
    return True

def is_grocery(store):
    return any(kw in store.lower() for kw in GROCERY_KW)

def normalize_store(name):
    name = name.strip()
    for alias, canonical in STORE_ALIASES.items():
        if name == alias or name.startswith(alias) or alias in name:
            return canonical
    return name

def generate_html(deals, output_path="index.html"):
    now = datetime.now()
    iso = now.isocalendar()
    week_label = f"Uke {iso[1]}"
    period = now.strftime("%d.%m.%Y")
    generated = now.strftime("%d.%m.%Y kl %H:%M")

    # Collect stores from deals
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

    # Build store pills
    pills = '<span class="store-badge active" data-store="all" onclick="filterStore(\'all\')">🌐 Alle</span>\n'
    for s in sorted_stores:
        key = STORE_KEY.get(s, s.lower().replace(' ',''))
        label = STORE_LABEL.get(s, s)
        pills += f'  <span class="store-badge" data-store="{key}" onclick="filterStore(\'{key}\')">{label}</span>\n'

    # Cat nav with short names
    cat_nav = ''
    SHORT_NAMES = {
        'Kylling':'Kylling','Storfe':'Storfe','Svin':'Svin',
        'Laks':'Laks','Reker/scampi':'Reker','Yoghurt':'Yoghurt',
        'Egg':'Egg','Ost':'Ost','Pålegg':'Pålegg','Brød':'Brød',
        'Snacks':'Snacks','Kaffe':'Kaffe','Drikke':'Drikke',
        'Dessert/is':'Is/Des','Grønnsaker':'Grønt','Frukt':'Frukt',
        'Ingredienser':'Tørrvarer',
    }
    for ci, cat in enumerate(deals.get("categories", [])):
        cid = f"cat{ci}"
        short = SHORT_NAMES.get(cat['name'], cat['name'][:8])
        cat_nav += f'<a href="#{cid}">{short}</a>'

    # Top 10
    top10 = ''
    for p in deals.get("top_picks", [])[:10]:
        name = escape(p.get("name",""))
        price = escape(p.get("price",""))
        sv = escape(p.get("savings",""))
        sv_html = f' <span class="sv">{sv}</span>' if sv else ''
        store = normalize_store(p.get("store",""))
        skey = STORE_KEY.get(store, store.lower().replace(' ',''))
        top10 += f'<li data-store-filter="{skey}"><strong>{store}</strong> — {name} <strong class="price">{price}</strong>{sv_html}</li>\n'

    # Categories
    cats_html = ''
    for ci, cat in enumerate(deals.get("categories", [])):
        items = cat.get("items", [])
        if not items:
            continue
        cid = f"cat{ci}"
        emoji_map = {
            'Kylling':'🐔','Storfe':'🥩','Svin':'🐷','Laks':'🐟','Reker/scampi':'🦐',
            'Yoghurt':'🥛','Egg':'🥚','Ost':'🧀','Pålegg':'🥪','Brød':'🍞',
            'Snacks':'🍫','Kaffe':'☕','Drikke':'🥤','Dessert/is':'🍦',
            'Grønnsaker':'🥦','Frukt':'🍎','Ingredienser':'🧂',
        }
        emoji = emoji_map.get(cat['name'], '📦')
        
        tbl = '<table>\n<tr><th>Vare</th><th>Pris</th><th>Rabatt</th><th>Butikk</th></tr>\n'
        for item in items:
            name = escape(item.get("name",""))
            price = escape(item.get("price",""))
            sv = escape(item.get("savings",""))
            store = normalize_store(item.get("store",""))
            skey = STORE_KEY.get(store, store.lower().replace(' ',''))
            
            is_winner = bool(sv)
            cls = ' class="winner"' if is_winner else ''
            price_cls = ' class="price"' if is_winner else ''
            
            sv_cell = f'<td class="desc">{sv}</td>' if sv else '<td class="desc"></td>'
            
            tbl += f'<tr{cls} data-store="{skey}"><td>{name}</td><td{price_cls}>{price}</td>{sv_cell}<td class="store">{store}</td></tr>\n'
        
        tbl += '</table>'
        cats_html += f'\n<h2 id="{cid}">{emoji} {escape(cat["name"])}</h2>\n{tbl}\n'

    # Store recommendation cards
    recs = {
        'Kiwi': 'Kiwi Mysen', 'Rema 1000': 'Rema 1000 Mysen',
        'Extra': 'Extra Mysen', 'Bunnpris': 'Bunnpris',
        'Spar': 'Spar', 'Obs': 'Coop Obs Slitu 🚗',
        'Meny': 'Meny Askim 🚗',
    }
    shop_cards = ''
    for s in sorted_stores:
        if s in recs:
            skey = STORE_KEY.get(s, '')
            label = recs[s]
            # Count items for this store
            count = sum(1 for c in deals.get("categories",[]) for i in c.get("items",[]) if normalize_store(i.get("store","")) == s)
            shop_cards += f'  <div class="shop-card" onclick="filterStore(\'{skey}\')"><h4>{label}</h4><p>{count} tilbud denne uken</p></div>\n'

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
  .store {{ white-space: nowrap; font-size: 0.85em; }}
  .store-badge {{ display: inline-block; padding: 1px 6px; border: 1px solid var(--border); font-size: 0.78em; margin: 1px; cursor: pointer; }}
  .store-badge.active {{ background: var(--accent); color: #fff; border-color: var(--accent); }}
  .store-badge.filter-inactive {{ opacity: 0.3; }}
  .desc {{ color: #666; font-size: 0.82em; }}
  .winner {{ background: #e8f5e0; }}
  .winner td {{ border-bottom: 1px solid #c8e6b0; }}
  .winner .price {{ color: #1b5e20; font-size: 1.05em; }}
  .summary {{ background: var(--card); border: 2px solid var(--accent); padding: 16px; margin: 20px 0; }}
  .summary ol {{ margin-left: 20px; }}
  .summary li {{ margin-bottom: 6px; cursor: pointer; }}
  .summary li:hover {{ text-decoration: underline; }}
  .store-list {{ display: flex; flex-wrap: wrap; gap: 6px; margin: 12px 0; }}
  .store-badge {{ border: 1px solid var(--border); padding: 4px 12px; font-size: 0.85em; background: var(--card); cursor: pointer; user-select: none; }}
  .store-badge:hover, .store-badge.active {{ background: var(--accent); color: #fff; border-color: var(--accent); }}
  .last-updated {{ text-align: right; font-size: 0.8em; color: #888; margin-bottom: 20px; }}
  .active-filter {{ background: var(--accent); color: #fff; padding: 3px 10px; display: inline-block; margin-bottom: 10px; font-size: 0.85em; cursor: pointer; }}
  .hidden {{ display: none !important; }}
  .shop-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 10px; margin: 15px 0; }}
  .shop-card {{ border: 1px solid var(--border); padding: 10px; background: var(--card); cursor: pointer; }}
  .shop-card:hover {{ background: #efede0; }}
  .shop-card h4 {{ font-size: 0.9em; margin-bottom: 4px; }}
  .shop-card p {{ font-size: 0.8em; color: #555; }}
  .tag {{ display: inline-block; background: #e0dcc0; padding: 1px 6px; font-size: 0.7em; margin-left: 4px; }}
  .cat-nav {{ margin: 12px 0; display: flex; flex-wrap: wrap; gap: 4px; }}
  .cat-nav a {{ font-size: 0.75em; padding: 2px 8px; border: 1px solid var(--border); text-decoration: none; color: #222; }}
  .cat-nav a:hover {{ background: var(--accent); color: #fff; }}
  .sv {{ font-size: 0.85em; color: var(--accent2); }}
  @media (max-width: 600px) {{ body {{ padding: 10px; }} table {{ font-size: 0.8em; }} }}
</style>
</head>
<body>

<h1>🛒 Ukens beste tilbud — {week_label}</h1>
<p style="margin-bottom:5px"><strong>Periode:</strong> uke {week_label} | <strong>Område:</strong> Mysen (Indre Østfold)</p>
<p class="last-updated">Oppdatert {generated} | Kilde: eTilbudsavis, Enhver.no</p>

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
<p>Priser fra eTilbudsavis, Enhver.no — oppdatert {generated}. Klikk på butikknavn for å filtrere.</p>
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
