# Studio build loop (read before building sites)

Goal: as many pitch-ready sites as possible per token. Don't re-explore the repo each time; follow this loop.

1. `python3 pipeline/scout.py enrich --top N` (or `discover` first if `data/candidates.json` is thin).
2. For each `data/businesses/<slug>.json` with `site_status: scouted`:
   - Mine `site_audit.text`, `prices`, `reviews`, `hours`, `summary`. Look at 3–4 photos in `docs/<slug>/img/` with Read to pick the hero and spot menus or price boards. Never invent prices: if none are found, use "Ask about memberships" style CTAs.
   - Copy the closest kit from `docs/` (e.g. `docs/forge-athletic-club/` for gyms) and **change the layout, type pair and palette** per `playbook/THEMES.md`. No two sites may share hero layout + palette.
   - Real reviews only (from the JSON). Keep `noindex`. Footer line: "Preview concept prepared for <name>".
   - QA per `playbook/QUALITY_CHECKLIST.md` (Playwright script at `playbook/qa.js`).
   - Set `site_status: built`, adjust `buy_likelihood` and add `notes` (why they'd buy).
3. `python3 pipeline/scout.py leads`, then commit and push to `claude/uae-bulk-website-generation-7gkcoz`.

Efficiency rules: build in parallel batches; keep each site to 3 files (index.html, styles.css, main.js) plus img/; compress images to ≤250 KB (`python3 -c` with PIL, 1600px max, q=72).
