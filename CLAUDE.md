# Studio build loop (read before building sites)

Goal: as many pitch-ready sites as possible per token. Don't re-explore the repo each time; follow this loop.

0. Keys live in env only (`GOOGLE_MAPS_API_KEY`, `APIFY_TOKEN`). Never commit them. Setup once per container:
   `pip install opencv-contrib-python-headless jinja2` and download `EDSR_x4.pb` (URL in `pipeline/upscale.py`) into `$SR_MODELS`.
1. Scout: `python3 pipeline/scout.py discover --cats ... --areas ...` (Places: names, ratings, websites, phones; free tier).
   Pick independent businesses (no chains or resort outlets, no massage-at-home) with many reviews and no website or a social-only one.
2. Enrich: `python3 pipeline/scout.py apify --ids <place ids> --photos 20 --min-score 50` (reviews, owner replies, photos, popular times; ≈$0.03 per business),
   then `python3 pipeline/scout.py socials` (Instagram, verified by phone or name+location only).
3. For each `data/businesses/<slug>.json` with `site_status: scouted`:
   - Contact sheet of `docs/<slug>/img/raw/` (PIL, 6 per row, labelled), Read it once, copy the picks to `img/` with descriptive names, delete `raw/`.
   - `python3 pipeline/upscale.py docs/<slug>/img/*.jpg` (EDSR x4 on anything < 1000px; ≈45 s each, so run it in the background).
   - Write `data/content/<slug>.json` (copy + design: preset, hero variant, frame, sections). Mine reviews for staff names, prices, landmarks, signature items.
     Never invent prices or facts; when there are no prices, use the `asks` section (pre-filled WhatsApp questions).
     Vary preset + hero variant (`split`/`full`/`stack`) + frame (`slant`/`arch`/`round`/`square`) so no two sites look alike.
     Presets are in `pipeline/build.py`; `python3 .claude/skills/ui-ux-pro-max/scripts/search.py "<category> <mood>" --design-system` for ideas.
   - `python3 pipeline/build.py <slug>` → `docs/<slug>/`. QA with `node playbook/qa.js <slug> <outdir>` and look at the hero screenshot.
   - Set `site_status: built`, adjust `buy_likelihood`, add `notes` (why they'd buy).
4. `python3 pipeline/scout.py leads` and `python3 pipeline/messages.py` (WhatsApp pitches → `OUTREACH.md`, `outreach.csv`), commit, push to `claude/uae-bulk-website-generation-7gkcoz` (GitHub Pages serves `/docs`).

Bespoke sites (not generated): `docs/champions-gym-karama/`, `docs/forge-athletic-club/` (fictional template, never pitch it).
