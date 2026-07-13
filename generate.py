#!/usr/bin/env python3
"""Generate ukens-tilbud index.html from scraped deals and push to GitHub Pages."""

import json, os, sys
from datetime import datetime
from html import escape

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="nb">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Ukens tilbud — {week_label}</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    :root {{
      --bg: #f5f3ee; --card: #ffffff; --accent: #2d5a27;
      --accent-light: #e8f0e6; --text: #1a1a1a; --muted: #6b6b6b;
      --border: #e0ddd5; --new-badge: #c0392b;
    }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
      background: var(--bg); color: var(--text); line-height: 1.6;
      padding: 2rem 1rem;
    }}
    .container {{ max-width: 800px; margin: 0 auto; }}
    header {{ text-align: center; padding: 2rem 0 1.5rem; border-bottom: 2px solid var(--accent); margin-bottom: 2rem; }}
    header h1 {{ font-size: 1.8rem; font-weight: 700; color: var(--accent); }}
    header p {{ color: var(--muted); font-size: 0.9rem; margin-top: 0.3rem; }}
    .section-title {{
      font-size: 1.3rem; font-weight: 700; padding: 1rem 0 0.5rem;
      margin: 2rem 0 1rem; border-bottom: 1px solid var(--border);
      color: var(--accent);
    }}
    .card {{
      background: var(--card); border-radius: 12px; padding: 1rem 1.2rem;
      margin: 0.6rem 0; box-shadow: 0 1px 3px rgba(0,0,0,0.06);
      display: flex; justify-content: space-between; align-items: flex-start;
      gap: 1rem; border: 1px solid var(--border);
    }}
    .card .info {{ flex: 1; }}
    .card .name {{ font-weight: 600; font-size: 1rem; margin-bottom: 0.2rem; }}
    .card .store {{ font-size: 0.8rem; color: var(--muted); }}
    .card .price {{ text-align: right; white-space: nowrap; flex-shrink: 0; }}
    .card .price .current {{ font-size: 1.1rem; font-weight: 700; color: var(--accent); }}
    .card .price .savings {{ font-size: 0.8rem; color: var(--new-badge); font-weight: 600; }}
    .badge-new {{
      display: inline-block; background: var(--new-badge); color: white;
      font-size: 0.65rem; font-weight: 700; padding: 0.1rem 0.4rem;
      border-radius: 4px; margin-right: 0.4rem; text-transform: uppercase;
    }}
    .top-picks {{
      background: var(--accent-light); border-radius: 12px; padding: 1.2rem 1.5rem;
      margin-bottom: 2rem; border-left: 4px solid var(--accent);
    }}
    .top-picks h2 {{ font-size: 1.1rem; margin-bottom: 0.8rem; color: var(--accent); }}
    .top-picks ol {{ padding-left: 1.2rem; }}
    .top-picks li {{ padding: 0.3rem 0; font-size: 0.95rem; }}
    .footer {{ text-align: center; padding: 2rem 0; color: var(--muted); font-size: 0.8rem; }}
    @media (max-width: 500px) {{ body {{ padding: 1rem 0.5rem; }} .card {{ padding: 0.8rem; }} header h1 {{ font-size: 1.4rem; }} }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1>🛒 Ukens tilbud</h1>
      <p>{week_label} • Oppdatert {generated_at}</p>
    </header>

    {top_picks_html}

    {categories_html}

    <div class="footer">
      Automatisk generert · <a href="https://github.com/Olewol/tilbudsavis">Olewol/tilbudsavis</a>
    </div>
  </div>
</body>
</html>"""


def render_top_picks(picks):
    if not picks:
        return ""
    items = "".join(
        f'<li><strong>{escape(p["name"])}</strong> — {escape(p["store"])} — '
        f'<strong>{escape(p["price"])}</strong> ({escape(p["savings"])})</li>\n'
        for p in picks[:10]
    )
    return (
        '<div class="top-picks">\n'
        '  <h2>⭐ Ukas beste kjøp</h2>\n'
        f'  <ol>\n{items}  </ol>\n'
        "</div>\n"
    )


def render_category(name, items):
    if not items:
        return ""
    cat_html = f'<div class="section-title">📦 {escape(name)}</div>\n'
    for item in items:
        badge = '<span class="badge-new">Ny</span> ' if item.get("is_new") else ""
        cat_html += (
            '<div class="card">\n'
            f'  <div class="info">\n'
            f'    {badge}<div class="name">{escape(item["name"])}</div>\n'
            f'    <div class="store">{escape(item["store"])}</div>\n'
            f'  </div>\n'
            f'  <div class="price">\n'
            f'    <div class="current">{escape(item["price"])}</div>\n'
        )
        if item.get("savings"):
            cat_html += f'    <div class="savings">{escape(item["savings"])}</div>\n'
        cat_html += "  </div>\n</div>\n"
    return cat_html


def generate_html(deals, output_path="index.html"):
    """deals: dict with 'top_picks' list and 'categories' list of {name, items[]}"""
    now = datetime.now()
    week_label = f"Uke {now.isocalendar()[1]} — {now.strftime('%d. %B %Y')}"
    generated_at = now.strftime("%d.%m.%Y kl %H:%M")

    top_html = render_top_picks(deals.get("top_picks", []))
    cats_html = ""
    for cat in deals.get("categories", []):
        cats_html += render_category(cat["name"], cat["items"])

    html = HTML_TEMPLATE.format(
        week_label=escape(week_label),
        generated_at=escape(generated_at),
        top_picks_html=top_html,
        categories_html=cats_html,
    )
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ {output_path} generert ({len(html)} bytes)")


def push_to_github(repo_dir):
    """Commit index.html and push to GitHub Pages (main branch)."""
    os.chdir(repo_dir)
    if os.system("git add index.html && git diff --cached --quiet") == 0:
        print("ℹ️  Ingen endringer å committe")
        return
    os.system('git commit -m "Oppdater ukens tilbud"')
    os.system("git push origin main")
    print("✅ Pushet til GitHub")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            deals = json.load(f)
    else:
        # Demo data
        deals = {
            "top_picks": [
                {"name": "Ribbe grillet", "store": "Rema 1000", "price": "79 kr", "savings": "spar 40 kr"},
            ],
            "categories": [
                {
                    "name": "Kylling",
                    "items": [
                        {"name": "Kyllingfilet 400g", "store": "Kiwi", "price": "59 kr", "savings": "-25%", "is_new": True},
                        {"name": "Kyllingkjøttdeig", "store": "Rema 1000", "price": "49 kr", "savings": "spar 15 kr"},
                    ]
                },
                {
                    "name": "Pålegg",
                    "items": [
                        {"name": "Stranda spekeskinke", "store": "Extra", "price": "32 kr", "savings": "spar 12 kr"},
                        {"name": "Jacobs utvalgte skinke", "store": "Kiwi", "price": "28 kr", "savings": "spar 8 kr"},
                    ]
                }
            ]
        }
        generate_html(deals)
