# Studio build loop (read before building sites)

Goal: as many pitch-ready sites as possible per token. Don't re-explore the repo each time; follow this loop.

0. Keys live in env only (`GOOGLE_MAPS_API_KEY`, `APIFY_TOKEN`). Never commit them.
1. `python3 pipeline/scout.py discover --cats ... --areas ...` (Places: names, ratings, websites, phones), then `python3 pipeline/scout.py apify --top N` (Apify Maps scraper: reviews, owner replies, photos, popular times; about $0.03 per business). `enrich` is the Places-only path for a full, non-demo key.
2. For each `data/businesses/<slug>.json` with `site_status: scouted`:
   - Mine `reviews` (coach names, prices, landmarks), `owner_description`, `amenities`, `review_tags`, `popular_times`, `site_audit.text`. Build ONE contact sheet of `docs/<slug>/img/raw/` (PIL, 6 per row) and Read it to pick the hero and usable shots; copy picks to `img/` with descriptive names and delete `raw/`. Low-res review photos get the duotone treatment (see `docs/champions-gym-karama`).
   - Run `python3 .claude/skills/ui-ux-pro-max/scripts/search.py "<category> <mood>" --design-system` for palette and type ideas, then pick from `playbook/THEMES.md`. Never invent prices: if none are found, use "Ask about memberships" style CTAs.
   - Copy the closest kit from `docs/` (gyms: `docs/champions-gym-karama/` (real data, split hero) or `docs/forge-athletic-club/` (template, full-bleed hero)) and **change the layout, type pair and palette** per `playbook/THEMES.md`. No two sites may share hero layout + palette.
   - Real reviews only (from the JSON). Keep `noindex`. Footer line: "Preview concept prepared for <name>".
   - QA per `playbook/QUALITY_CHECKLIST.md` (Playwright script at `playbook/qa.js`).
   - Set `site_status: built`, adjust `buy_likelihood` and add `notes` (why they'd buy).
3. `python3 pipeline/scout.py leads`, then commit and push to `claude/uae-bulk-website-generation-7gkcoz`.

Efficiency rules: build in parallel batches; keep each site to 3 files (index.html, styles.css, main.js) plus img/; compress images to ≤250 KB (`python3 -c` with PIL, 1600px max, q=72).
