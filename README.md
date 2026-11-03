# UAE Website Studio: bulk pitch-site pipeline

Find UAE businesses with no website or a bad one. Pull their real content (reviews, photos, prices, hours, socials). Build each a polished site with its own theme. Publish it to a preview link. Hand over a ranked list of leads to pitch.

```
 SCOUT ──► QUALIFY ──► ENRICH ──► BUILD ──► QA ──► PUBLISH ──► LEADS.md
 Places    score ≥60   details,   Claude    UI/UX   GitHub      ranked by
 API       & no good   reviews,   Code      check-  Pages       likelihood
 search    website     photos,              list    (docs/)     to buy
                       old-site scrape
```

## 1. Scout (`pipeline/scout.py discover`)
- Runs Google Places API (New) Text Search over **category × area**: 20 categories (gyms, clinics, salons, restaurants, garages, nurseries…) × 19 areas across Dubai, Abu Dhabi, Sharjah, Ajman, Al Ain, RAK and Fujairah.
- **Hard filters:** operational, **≥25 reviews**, **≥5 photos**.
- **Website pre-check:** a business with no website, or one that only links to Instagram, Facebook or Linktree, is a prime target.

## 2. Qualify: worth score 0–100
| Signal | Points |
|---|---|
| Review volume (log scale; 100 reviews ≈ 20) | up to 30 |
| Photos on Maps | up to 15 |
| Rating above 3.5 | up to 15 |
| Website status: outdated 25 · broken 24 · social-only 22 · none 18 · **modern −40** | |
| Category value (gym or clinic 15, café 10…) | up to 15 |

Only businesses scoring **60 or more** get built. Under this scoring, 1 review with 3 photos gets filtered out, while 40+ reviews with an outdated site full of information scores about 80. `audit_site()` flags an existing site as outdated when it has at least two of these: no HTTPS, no mobile viewport, copyright year 4+ years old, jQuery 1.x, Flash, table layout, `<font>`/`<marquee>` tags, a free-builder subdomain, or an "under construction" page.

## 3. Enrich (`pipeline/scout.py enrich --top N`)
- **Place Details:** phone, hours, address and coordinates, up to 5 Google reviews, editorial summary.
- **Photos:** up to 10 Maps photos are downloaded into `docs/<slug>/img/`. Photos the owner uploaded are flagged and preferred, because they're the business's own images, often including menus and price boards.
- **Old website scrape:** emails, Instagram, Facebook, TikTok and WhatsApp links, every `AED` price, and the page text (services and about copy) for Claude to mine.
- **Instagram/Facebook:** both require a login, and the sandbox blocks them. See "What I need from you".
- **Image rule:** use the business's real photos first. Stock photos are only for neutral backgrounds such as textures or close-ups, colour-graded to match the site. Don't use obviously AI-generated people or places.
- Output goes to `data/businesses/<slug>.json`.

## 4. Build (Claude Code, one folder per site in `docs/<slug>/`)
- Each category has its own theme kit (`playbook/THEMES.md`): layout, type pairing, palette and motion. The palette is then tuned to the business's logo and photos, so two gyms don't look the same.
- **Single page by default.** Multi-page only when the content justifies it (a big menu, many services, many branches).
- **Always included:** a strong hero with a real photo, the Google rating badge and review wall, prices or a menu where available, hours with live open/closed status (Dubai time), a map, a floating WhatsApp button, social links, schema.org data, and `noindex` until the client signs.
- **Optional:** Claude Design (MCP) for the top ~10% of leads, when a fully bespoke design is worth the extra tokens.

## 5. QA (`playbook/QUALITY_CHECKLIST.md`)
Playwright screenshots at 1440px and 390px, a check for horizontal overflow, console errors, contrast and focus states, reduced-motion support, 44px tap targets, and an image weight budget.

## 6. Publish
Every site lives at `docs/<slug>/` and is served by GitHub Pages at `https://mdmd1735.github.io/Business-websites/<slug>/`. The slug is the business name (e.g. `/al-noor-fitness/`). For cleaner links, see "Domains" below.

## 7. Leads (`pipeline/scout.py leads`)
Writes `LEADS.md` and `leads.csv` with the business name, preview link, **likelihood to buy (out of 10)**, phone, WhatsApp, email, Instagram, current site status, rating and Maps link. The score is a heuristic (outdated site > social-only > none, review volume, category ticket size, reachable mobile number), and Claude adjusts it after building.

---

## What I need from you

| # | Item | Why | Cost |
|---|---|---|---|
| 1 | **Google Maps Platform API key** with *Places API (New)* enabled → set it as env var `GOOGLE_MAPS_API_KEY` in this cloud environment's settings | Scouting, reviews and photos. `places.googleapis.com` is already reachable from the sandbox. | Monthly free usage caps per SKU. Set a daily quota cap in Google Cloud so it can't bill you. |
| 2 | **Network access:** set it to *Full*, or allow `*.googleusercontent.com`, `images.unsplash.com`, `*.instagram.com`, `*.facebook.com`, plus "any" for scraping old business sites | Photo downloads redirect to googleusercontent. Old business websites are on random domains. | Free |
| 3 | **GitHub Pages:** make this repo **public** (free plan) or keep it private on GitHub Pro. Then Settings → Pages → *Deploy from a branch* → `claude/uae-bulk-website-generation-7gkcoz`, folder **`/docs`** | Pages on private repos needs a paid plan | Free if public |
| 4 | *(Optional)* **Apify token** (`APIFY_TOKEN`) + allow `api.apify.com` | Instagram/Facebook profile and post scraping (prices in captions, more photos). Free tier ≈ $5/month in credit. | Free tier |
| 5 | *(Optional)* A studio name, one domain (~AED 40/yr), and a WhatsApp number for the footer credit | Cleaner preview links and branding | ~AED 40/yr |

**Privacy if you go public:** `data/` and `LEADS.md` hold public business info only, but it's cleaner to keep them out of a public repo. The best setup is to keep this repo private as the engine, and add a second public repo (e.g. `previews`) that only receives `docs/`. Create it and I'll push sites there.

## Domains
- **$0:** create a free GitHub organisation named after your studio (e.g. `noorweb`) and a repo `noorweb.github.io`. Links become `https://noorweb.github.io/al-noor-fitness/`.
- **~AED 40/yr:** one domain like `previews.yourstudio.ae`. Links become `previews.yourstudio.ae/al-noor-fitness`. When a client buys, move their site to their own domain.

## Running a batch (cloud session)
```bash
python3 pipeline/scout.py discover --cats gym,"dental clinic",restaurant --areas "Al Quoz, Dubai" "Al Nahda, Sharjah"
python3 pipeline/scout.py enrich --top 10
# Claude builds docs/<slug>/ for each business JSON, runs QA, commits, pushes
python3 pipeline/scout.py leads
```
`CLAUDE.md` holds the build loop, so any new session can just be told: **"run the next batch of 10"**.
