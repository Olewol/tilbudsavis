#!/usr/bin/env python3
"""Generate filterable tilbudsavis page with store pills — localized for Mysen."""

import json, os, sys
from datetime import datetime
from html import escape

STORE_COLORS = {
    'Kiwi': '#e17055', 'Rema 1000': '#fdcb6e', 'Rema': '#fdcb6e',
    'Extra': '#d63031', 'Coop': '#d63031', 'Coop Prix': '#d63031',
    'Coop Mega': '#6c5ce7', 'Coop Obs': '#2d3436', 'Obs': '#2d3436',
    'Meny': '#e84393', 'MENY': '#e84393', 'Bunnpris': '#f1c40f',
    'Spar': '#dc1e21', 'SPAR': '#dc1e21', 'Eurospar': '#dc1e21',
    'Joker': '#00b894', 'Nærbutikken': '#636e72', 'Matkroken': '#636e72',
    'Gigaboks': '#2d3436',
}

STORE_ALIASES = {
    'Coop Obs': 'Obs', 'COOP OBS': 'Obs', 'Obs!': 'Obs',
    'Rema 1000': 'Rema 1000', 'REMA 1000': 'Rema 1000', 'Rema': 'Rema 1000',
    'Coop Prix': 'Extra', 'COOP PRIX': 'Extra',
    'MENY': 'Meny', 'Meny': 'Meny',
    'SPAR': 'Spar', 'Eurospar': 'Spar',
    'KIWI': 'Kiwi', 'Kiwi': 'Kiwi',
}

# Butikker som IKKE finnes i Mysen-området — skal filtreres bort
BLOCKED_STORES = {'Joker', 'Coop Mega', 'Nærbutikken', 'Matkroken', 'Mega'}

def is_allowed_store(store_name):
    """Return True if the store exists in Mysen area."""
    name = store_name.strip().lower()
    for blocked in BLOCKED_STORES:
        if blocked.lower() in name:
            return False
    return True

def normalize_store(name):
    name = name.strip()
    for alias, canonical in STORE_ALIASES.items():
        if name == alias or name.startswith(alias) or alias in name:
            return canonical
    return name

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="nb">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Ukens Tilbud — {week_label} | Mysen</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: 'Inter', -apple-system, sans-serif; background: #f5f0eb; color: #1a1a1a; line-height: 1.6; }}
  .container {{ max-width: 960px; margin: 0 auto; padding: 20px; }}
  
  header {{ background: linear-gradient(135deg, #2d3436 0%, #1a1a2e 100%); color: #fff; padding: 40px 20px; text-align: center; border-radius: 16px; margin-bottom: 24px; }}
  header h1 {{ font-size: 2em; font-weight: 800; margin-bottom: 6px; letter-spacing: -0.5px; }}
  header .sub {{ font-size: 1em; opacity: 0.8; }}
  header .date {{ font-size: 0.85em; opacity: 0.6; margin-top: 8px; }}
  
  .stores {{ background: #fff; border-radius: 12px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
  .stores h2 {{ font-size: 1.1em; font-weight: 700; margin-bottom: 12px; color: #2d3436; }}
  .store-grid {{ display: flex; flex-wrap: wrap; gap: 8px; }}
  .store-pill {{ padding: 8px 16px; border-radius: 20px; font-size: 0.85em; font-weight: 600; cursor: pointer; border: 2px solid transparent; transition: all 0.2s; user-select: none; }}
  .store-pill:hover {{ transform: scale(1.05); }}
  .store-pill.active {{ border-color: #2d3436; box-shadow: 0 0 0 2px #fff, 0 0 0 4px currentColor; }}
  .store-pill.all-pill {{ background: #2d3436; color: #fff; }}
  .store-pill.all-pill.active {{ border-color: #e17055; }}
  
  .top10 {{ background: #fff; border-radius: 12px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); border-left: 4px solid #e17055; }}
  .top10 h2 {{ font-size: 1.1em; font-weight: 700; margin-bottom: 12px; color: #e17055; }}
  .top10 ol {{ padding-left: 20px; }}
  .top10 li {{ margin-bottom: 8px; font-size: 0.95em; }}
  .top10 li span.price {{ font-weight: 700; color: #e17055; }}
  .top10 li span.sname {{ font-weight: 600; color: #636e72; }}
  
  .category {{ background: #fff; border-radius: 12px; padding: 20px; margin-bottom: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
  .category h3 {{ font-size: 1em; font-weight: 700; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 2px solid #f0ebe6; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.9em; }}
  th {{ text-align: left; font-weight: 600; color: #636e72; font-size: 0.8em; text-transform: uppercase; letter-spacing: 0.5px; padding: 6px 8px; border-bottom: 1px solid #f0ebe6; }}
  td {{ padding: 8px; border-bottom: 1px solid #f5f0eb; }}
  td.price {{ font-weight: 700; white-space: nowrap; color: #d63031; }}
  td.savings {{ font-size: 0.8em; color: #27ae60; font-weight: 600; white-space: nowrap; }}
  .badge {{ display: inline-block; font-size: 0.7em; padding: 2px 8px; border-radius: 10px; font-weight: 600; cursor: pointer; transition: opacity 0.2s; }}
  .badge:hover {{ opacity: 0.8; }}
  .store-row {{ transition: all 0.2s; }}
  .store-row.hidden {{ display: none; }}
  .store-row.fade {{ opacity: 0.3; }}
  
  .recommendation {{ background: linear-gradient(135deg, #00b894, #00cec9); color: #fff; border-radius: 12px; padding: 20px; margin-bottom: 20px; }}
  .recommendation h2 {{ font-size: 1.1em; font-weight: 700; margin-bottom: 8px; }}
  .recommendation p {{ font-size: 0.95em; opacity: 0.95; }}
  
  .footer {{ text-align: center; font-size: 0.8em; color: #b2bec3; padding: 20px 0; }}
  
  .count-bar {{ text-align: center; font-size: 0.85em; color: #636e72; margin-bottom: 16px; padding: 8px; background: #fff; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }}
  
  @media (max-width: 600px) {{ .container {{ padding: 10px; }} header {{ padding: 24px 16px; }} header h1 {{ font-size: 1.5em; }} .category {{ padding: 12px; }} table {{ font-size: 0.8em; }} td.price {{ font-size: 0.85em; }} }}
</style>
</head>
<body>
<div class="container">

<header>
  <h1>🛒 Ukens Tilbud — {week_label}</h1>
  <div class="sub">{week_sub}</div>
  <div class="date">Mysen-området • Oppdatert {generated_at}</div>
</header>

<div class="stores">
  <h2>🏪 Velg butikk</h2>
  <div class="store-grid">
    <span class="store-pill all-pill active" onclick="filterStore('all')" data-store="all">📋 Alle butikker</span>
    {store_pills}
  </div>
</div>

<div class="count-bar" id="countBar">Viser alle tilbud</div>

<div class="top10">
  <h2>🏆 Ukas 10 beste kjøp</h2>
  <ol>
    {top10_items}
  </ol>
</div>

{categories_html}

<div class="footer">
  Generert av Hermes Agent • Data: eTilbudsavis • <a href="https://github.com/Olewol/tilbudsavis" style="color:#b2bec3;">Olewol/tilbudsavis</a>
</div>

</div>

<script>
function filterStore(store) {{
  document.querySelectorAll('.store-pill').forEach(p => p.classList.remove('active'));
  document.querySelector(`.store-pill[data-store="${{store}}"]`).classList.add('active');
  
  let visible = 0;
  document.querySelectorAll('.store-row').forEach(row => {{
    const stores = row.dataset.stores.split('|');
    if (store === 'all' || stores.some(s => s.toLowerCase().includes(store.toLowerCase()))) {{
      row.classList.remove('hidden');
      row.classList.remove('fade');
      visible++;
    }} else {{
      row.classList.add('hidden');
    }}
  }});
  
  // Also filter top10 items
  document.querySelectorAll('.top10-item').forEach(item => {{
    const stores = item.dataset.stores.split('|');
    if (store === 'all' || stores.some(s => s.toLowerCase().includes(store.toLowerCase()))) {{
      item.style.display = '';
    }} else {{
      item.style.display = 'none';
    }}
  }});
  
  const name = store === 'all' ? 'alle butikker' : store;
  document.getElementById('countBar').textContent = `Viser ${{visible}} varer — ${{name}}`;
}}
</script>
</body>
</html>"""

def generate_html(deals, output_path="index.html"):
    now = datetime.now()
    iso = now.isocalendar()
    week_label = f"Uke {iso[1]}"
    week_sub = f"{now.strftime('%d. %B %Y')}"
    generated_at = now.strftime("%d.%m.%Y kl %H:%M")
    
    # Collect unique stores (filtered for Mysen area)
    all_stores = set()
    for cat in deals.get("categories", []):
        items = []
        for item in cat.get("items", []):
            store_raw = item.get("store", "")
            if not is_allowed_store(store_raw):
                continue  # filter out non-Mysen stores
            items.append(item)
            all_stores.add(normalize_store(store_raw))
        cat["items"] = items
    for p in list(deals.get("top_picks", [])):
        if not is_allowed_store(p.get("store", "")):
            deals["top_picks"].remove(p)
            continue
        for s in p.get("store", "").split("/"):
            all_stores.add(normalize_store(s.strip()))
    
    # Mysen store order
    store_order = ["Kiwi", "Rema 1000", "Extra", "Bunnpris", "Spar", "Obs", "Meny"]
    sorted_stores = sorted(all_stores, key=lambda s: store_order.index(s) if s in store_order else 99)
    
    # Store pills
    pills = ""
    for s in sorted_stores:
        color = STORE_COLORS.get(s, "#636e72")
        is_drive = s in ["Obs", "Meny"]
        emoji = "🚗 " if is_drive else ""
        pills += f'<span class="store-pill" onclick="filterStore(\'{s}\')" data-store="{s}" style="background:{color};color:#fff;">{emoji}{s}</span>\n    '
    
    # Top 10
    top10 = ""
    for p in deals.get("top_picks", [])[:10]:
        name = escape(p["name"])
        price = escape(p["price"])
        savings = escape(p.get("savings", ""))
        stores = "|".join([normalize_store(s.strip()) for s in p.get("store", "").split("/")])
        store_display = escape(p["store"])
        
        sv_html = f' <span class="sav">{savings}</span>' if savings else ""
        top10 += f'<li class="top10-item" data-stores="{stores}"><span class="sname">{store_display}:</span> {name} — <span class="price">{price}</span>{sv_html}</li>\n    '
    
    # Categories
    cats_html = ""
    for cat in deals.get("categories", []):
        items = cat.get("items", [])
        if not items:
            continue
        
        cat_html = f'<div class="category"><h3>{escape(cat["name"])}</h3><table>\n'
        cat_html += '<tr><th>Vare</th><th>Pris</th><th>Rabatt</th><th>Butikk</th></tr>\n'
        
        for item in items:
            name = escape(item["name"])
            price = escape(item["price"])
            savings = escape(item.get("savings", ""))
            store = normalize_store(item.get("store", ""))
            store_display = escape(item.get("store", ""))
            color = STORE_COLORS.get(store, "#636e72")
            badge = f'<span class="badge" style="background:{color};color:#fff;" onclick="filterStore(\'{store}\')">{store_display}</span>'
            
            row_class = ' class="store-row"'
            data_stores = f' data-stores="{store}"'
            if "/" in store_display:
                stores_multi = "|".join([normalize_store(s.strip()) for s in store_display.split("/")])
                data_stores = f' data-stores="{stores_multi}"'
            
            sv = f'<td class="savings">{savings}</td>' if savings else '<td class="savings"></td>'
            cat_html += f'<tr{row_class}{data_stores}><td>{name}</td><td class="price">{price}</td>{sv}<td>{badge}</td></tr>\n'
        
        cat_html += '</table></div>\n'
        cats_html += cat_html
    
    html = HTML_TEMPLATE.format(
        week_label=escape(week_label),
        week_sub=escape(week_sub),
        generated_at=escape(generated_at),
        store_pills=pills,
        top10_items=top10 if top10 else "<li>Ingen topp-tilbud denne uken</li>",
        categories_html=cats_html if cats_html else "<p>Ingen kategorier med tilbud denne uken.</p>"
    )
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ {output_path} ({len(html)} bytes, {len(sorted_stores)} butikker, {sum(len(c.get('items',[])) for c in deals.get('categories',[]))} varer)")


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
    import os as _os
    _os.chdir(_os.path.dirname(_os.path.abspath(__file__)))
    if len(sys.argv) > 1:
        path = sys.argv[1]
        if not _os.path.isabs(path):
            path = _os.path.join(_os.getcwd(), path)
        with open(path) as f:
            deals = json.load(f)
    else:
        print("⚠️  Ingen fil — bruker eksempeldata")
        deals = {"top_picks": [], "categories": []}
    generate_html(deals)
    if len(sys.argv) > 2:
        push_to_github(sys.argv[2])
    elif "PUSH" in os.environ:
        push_to_github(_os.path.dirname(_os.path.abspath(__file__)))
