# 🛒 Tilbudsavis — ukentlig dagligvaretilbud-pipeline

Automatisk pipeline som hver uke henter, filtrerer, kuraterer og publiserer ukens beste dagligvaretilbud fra norske butikker. Resultatet er en statisk nettside (GitHub Pages) + JSON-datasett, generert uten manuelt arbeid.

**Live side:** https://olewol.github.io/tilbudsavis/

---

## Hva dette repoet inneholder

| Fil | Beskrivelse |
|---|---|
| `generate.py` | HTML-generator — retro/monospace design, butikkfilter, handleplan, kvalitetsbadge |
| `index.html` | Siste genererte nettside |
| `latest-data.json` | Offentlig datasett for dynamisk lasting (`meta` + `products` med kategori, pris, butikk) |
| `data_ukeXX.json` | Ukentlig arkiv av offentlig datasett |
| `deals_ukeXX.json` | Ukentlig arkiv av kuratert utvalg (`top_picks` + `categories`) |
| `ukeXX.html` | Ukentlig arkiv av nettsiden |

> ⚠️ Selve datainnsamlingsskriptet (`tilbudsavis-pipeline.py`) ligger ikke i dette repoet — det kjører som en cron-jobb hos eieren. Se [Arkitektur](#arkitektur) og [Slik konfigurerer AI-agenten din dette](#-slik-konfigurerer-ai-agenten-din-dette).

---

## Arkitektur

Én ukentlig jobb (mandag 08:00) med 8 faser:

1. **Datainnsamling** — ekstraherer tilbud fra eTilbudsavis (embedded JSON i `<app-data>`-taggen på tilbudssidene), kryssjekker mot Enhver.no, Gjerrigknark og VG Kupp
2. **Butikkfiltrering** — bare godkjente dagligvarekjeder; blokkerte kjeder filtreres (word-boundary matching — aldri substring)
3. **Varefiltrering** — non-food (dyrefôr, klær, interiør, elektronikk, kosmetikk), markedsføringsinnhold og kampanjeord blokkeres
4. **Datofilter** — kun tilbud gyldige siste 14 dager + 7 dager frem
5. **Kategorisering** — `guess_category()` med nøkkelord per kategori (prioritert rekkefølge)
6. **Kuratering** — deal-score per vare, toppliste med dedup/spredning, kategori-cap
7. **Kvalitetsscoring** (0–100) — under 80 → re-ekstraksjon med forbedret strategi (maks 3 forsøk)
8. **Deploy** — genererer HTML + JSON, git commit/push → GitHub Pages, Telegram-rapport

### Nøkkelkonsepter

- **`_deal_score`** — vektet tilbudsscore: spart beløp i kr + bonus for høy %-rabatt (≥25 % → +15, ≥15 % → +8, ≥10 % → +3, 3-for-2 → +10)
- **`_has_deal`** — varen har dokumentert rabatt (savings / relativeSavings / fromPrice / 3-for-2)
- **Toppliste** — kun varer med `_has_deal` og score ≥ 10, deduplisert på tvers av butikker (normaliserte navn med **sorterte tokens**: «FROKOSTKAFFE FRIELE» == «Friele frokostkaffe»), maks 1 per kategori, maks 2 per butikk, totalt 10
- **Kategori-cap** — maks 10 varer per kategori, sortert på deal-score; topp-varer ekskluderes fra kategoriene (ingen duplikater)
- **Savings-sanity** — hvis `savings > pris × 1,2` nullstilles spart-beløpet, med mindre beskrivelsen bekrefter det (inneholder «FØR X» / «SPAR Y»)
- **Husholdning** — vaskemiddel, såpe, dopapir, sjampo, tannkrem vises i egen kategori, **kun med deal**
- **Kvalitetsscore** — vekter kategoridekning, pris-data og lokale butikker; historikk lagres for selvforbedring

---

## 🧠 Slik konfigurerer AI-agenten din dette

Dette repoet er skrevet slik at en AI-agent (Claude Code, ChatGPT, Hermes, etc.) kan lese det og sette opp en tilsvarende pipeline for sin eier. Følg disse stegene:

### Steg 1 — Intervju brukeren om preferanser

Sett opp følgende for brukeren din FØR du skriver noe kode:

1. **Butikker** — hvilke kjeder og lokasjoner handler de på? (eTilbudsavis har Kiwi, Rema 1000, Extra, Coop Obs/Prix/Mega, Spar, Bunnpris, Meny, Joker, Europris m.fl.)
2. **Kategorier** — hvilke varegrupper er relevante? (kylling, storfe, svin, laks, reker, yoghurt, egg, ost, pålegg, brød, snacks, kaffe, drikke, dessert/is, grønnsaker, frukt, ingredienser, husholdning)
3. **Preferanser** — kun varer med reell rabatt, eller også ordinære priser? Maks antall varer per kategori? Kjører de bil til større kjøpesentre (obs/meny med 🚗)?
4. **Målform/område** — nettsiden genereres på norsk; hvilket område skal stå i overskriften?

### Steg 2 — Skriv datainnsamlingsskriptet

Skriptet skal:

- Hente tilbud fra eTilbudsavis. JSON-data ligger i `<app-data data-key="..." data-size="N" data-status="success">...</app-data>`-taggen i HTML-en (første tag med `data-key` som base64-dekoder til noe som starter med `["offers"`). Regex: `r'<app-data data-key="[^"]*" data-size="(\d+)" data-status="success">(.*?)</app-data>'` med `re.S` → `html.unescape` → `json.loads`
- **Pitfall:** nøklene i HTML-en er `&quot;`-encodet — søk aldri på rå anførselstegn i rå HTML
- Kryssjekke mot minst én sekundærkilde (Enhver.no, Gjerrigknark, VG Kupp) for kvalitet
- Returnere råprodukter med felt som `name`, `description`, `price`, `savings`, `relativeSavings`, `fromPrice`, `validFrom`, `business.name`

### Steg 3 — Implementer filtrene (kopier logikken)

Alle filtre skal være **ORD-basert (word boundary)** — aldri substring:

| Filter | Regel |
|---|---|
| `is_grocery_store()` | `kw in name.split()` — ALDRI `kw in name` («obs» i «Jacobs» = false positive) |
| `BLOCKED_STORES` | kjeder brukeren ikke handler hos (f.eks. `coop prix`, `joker`, `coop mega`, `nærbutikken`, `matkroken`, `mega`, `gigaboks`) |
| `is_non_food()` | dyrefôr/merkenavn (sheba, whiskas, friskies, pedigree, gourmet, applaws, mjau), klær, interiør, elektronikk, kosmetikk, leker, strand/bad, verktøy |
| `is_marketing()` | generisk kampanjeinnhold («god frokost», «grilltid», «ukas middag» …) |
| `is_household()` | vaskemiddel, såpe, dopapir, sjampo, tannkrem — vises **kun med deal** |
| `is_current_week()` | `validFrom` innenfor siste 14 dager + 7 dager frem (ISO-format, husk +0000 → +00:00) |

### Steg 4 — Kategorisering

`guess_category(name, desc)` med nøkkelord-tabell. **Rekkefølgen betyr noe:**

- Svin **før** Storfe (svinekjøttdeig vs kjøttdeig)
- Drikke **før** Kylling (lollipop = brus, ikke kylling)
- Brød **før** Storfe (burgerbrød)

Spesialtilfeller som må håndteres: fiskeburger/fiskekake/fiskepinne → Fisk (ikke Storfe via «burger»), hamburgerrygg → Svin, parmigiano/mozzarella/feta/cheddar/gouda → Ost (ikke Egg), frokostkaffe/friele/evergood → Kaffe (ikke Ost via «frokOSTkaffe»!), noodle/nudel → Ingredienser (ikke Egg via «egg noodles»).

### Steg 5 — Kuratering

- Deal-score: `savings_kr + bonus_for_pct` (se [Arkitektur](#arkitektur))
- Toppliste: kun `_has_deal` + score ≥ 10 → dedup (sorterte tokens) → maks 1/kategori, 2/butikk, 10 totalt
- Kategorier: maks 10 per kategori, sortert deal-score desc, topp-varer ekskludert
- Savings-sanity: `savings > price × 1,2` → nullstill med mindre desc bekrefter

### Steg 6 — Generer HTML + datasett

- `index.html` — statisk side (kopier designet fra `generate.py` eller lag ditt eget)
- `latest-data.json` — `{"meta": {"generated", "week", "quality_score", "total_products"}, "products": [...]}` for dynamisk lasting
- Arkiv: `ukeXX.html`, `data_ukeXX.json`, `deals_ukeXX.json`

### Steg 7 — Deploy + planlegging

- GitHub Pages fra `main`-branch (repoets rot)
- Ukentlig cron/planlagt kjøring (mandag morgen passer bra — nye tilbud gjelder fra mandag)
- Git: `git add` alle genererte filer → commit «Uke XX - pipeline (score:Y)» → push

### Steg 8 — Kvalitetssikring

- Poengsett hver kjøring (0–100): kategoridekning, pris-data, lokale butikker
- Under terskel (80) → re-ekstraher med justert strategi, maks 3 forsøk
- Lagre historikk for selvforbedring (siste N scores)

---

## 🤖 Ferdig prompt til din AI-agent

Kopier dette inn i AI-agenten din (tilpass butikker/preferanser):

```text
Gå inn på https://github.com/Olewol/tilbudsavis og les README-en og generate.py.

Jeg vil ha en tilsvarende ukentlig tilbudsavis-pipeline for MINE butikker.
Mine butikker er: [f.eks. Kiwi Oslo, Rema 1000 Grünerløkka, Meny Ullevål]
Mine kategorier: [f.eks. kylling, storfe, laks, egg, ost, brød, kaffe, grønnsaker, frukt]
Preferanser:
- Kun varer med reell rabatt (deal-score ≥ 10)
- Maks 8 varer per kategori
- Ikke vis husholdning/dopapir/vaskemiddel
- Nettside på norsk, område: [f.eks. Oslo]
- Deploy til GitHub Pages, ukentlig kjøring mandag 08:00

Sett opp hele pipelinen: datainnsamling fra eTilbudsavis, filtrering
(word-boundary matching, aldri substring), kategorisering med prioritert
nøkkelord-rekkefølge, kuratering med deal-score og dedup, HTML+JSON-generering,
kvalitetsscore med re-ekstraksjon, git push til Pages, og en Telegram/chat-rapport.
Forklar hva du har konfigurert og be meg bekrefte butikker/preferanser først.
```

---

## Viktige pitfalls (oppsummert)

1. **ALDRI substring-matching på butikknavn eller varenavn** — «obs» ≠ «Jacobs», «olje» ≠ «olivenolje», «ost» ≠ «frokostkaffe»
2. **Kategori-rekkefølge** — Svin før Storfe, Drikke før Kylling, Brød før Storfe
3. **eTilbudsavis-nøkler er encodet** — bruk `html.unescape` før `json.loads`, søk aldri på rå anførselstegn
4. **Dato-format** — `+0000` må konverteres til `+00:00` før ISO-parsing
5. **Savings-sanity** — stol ikke blindt på «spar X kr» fra kilden; verifiser mot beskrivelsen
6. **Dedup** — samme produkt kan stå hos flere butikker med ulik navneform; normaliser med sorterte tokens

---

## Kilder & data

- [eTilbudsavis](https://etilbudsavis.no) — primærkilde (tilbudssider)
- Enhver.no, Gjerrigknark, VG Kupp — sekundærkilder (kryssvalidering)
- Priser/varer kan variere mellom publiseringstidspunkt og faktisk butikk — dobbeltsjekk alltid i butikk

## Lisens

Repoet er åpent for gjenbruk. Dataene tilhører respektive kilder/kjeder.
