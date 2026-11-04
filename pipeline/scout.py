#!/usr/bin/env python3
"""UAE lead scout: find businesses with weak/no websites, score them, collect content.

Stdlib only. Needs GOOGLE_MAPS_API_KEY (Places API (New) enabled).

  python3 pipeline/scout.py discover --cats gym,restaurant --areas "Al Quoz, Dubai" "Al Nahda, Sharjah"
  python3 pipeline/scout.py apify --top 10           # Apify Maps scraper: reviews, owner replies, photos, popular times (preferred)
  python3 pipeline/scout.py enrich --top 10          # Places-API-only enrichment (needs a full, non-demo key)
  python3 pipeline/scout.py leads                    # rebuild LEADS.md / leads.csv

Data lands in data/candidates.json and data/businesses/<slug>.json;
photos in docs/<slug>/img/ (docs/ is the GitHub Pages root) so the site build can use them directly.
"""
import argparse, csv, json, math, os, re, sys, time, unicodedata, urllib.error, urllib.parse, urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA, SITES = ROOT / "data", ROOT / "docs"
KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "")
SITE_BASE = os.environ.get("SITE_BASE", "https://mdmd1735.github.io/Business-websites").rstrip("/")
UA = "Mozilla/5.0 (compatible; site-audit/1.0)"

# Search terms -> value weight (how much a site matters / ticket size for this category)
CATEGORIES = {
    "gym": 15, "fitness studio": 14, "martial arts academy": 13, "dental clinic": 15, "physiotherapy clinic": 14,
    "beauty salon": 12, "barber shop": 10, "spa": 13, "restaurant": 12, "cafe": 10, "bakery": 9,
    "car repair garage": 12, "optician": 12, "tailor": 10, "dance studio": 12, "yoga studio": 12, "car wash": 9, "laundry": 8, "music school": 13, "photography studio": 11, "flower shop": 9, "kids play area": 11, "car detailing": 11, "furniture store": 11, "interior design company": 14,
    "nursery school": 14, "tutoring center": 12, "pet grooming": 10, "veterinary clinic": 13, "florist": 9,
}
AREAS = [
    "Al Quoz, Dubai", "Al Barsha, Dubai", "Deira, Dubai", "Bur Dubai", "Jumeirah, Dubai", "Al Nahda, Dubai",
    "Dubai Silicon Oasis", "JLT, Dubai", "Al Karama, Dubai", "Mirdif, Dubai", "Al Khalidiyah, Abu Dhabi",
    "Mussafah, Abu Dhabi", "Al Reem Island, Abu Dhabi", "Al Majaz, Sharjah", "Al Nahda, Sharjah",
    "Ajman", "Al Ain", "Ras Al Khaimah", "Fujairah",
]
SOCIAL_HOSTS = ("instagram.com", "facebook.com", "fb.com", "linktr.ee", "tiktok.com", "wa.me", "linkedin.com")
SEARCH_FIELDS = ",".join("places." + f for f in [
    "id", "displayName", "formattedAddress", "rating", "userRatingCount", "websiteUri", "internationalPhoneNumber",
    "primaryType", "businessStatus", "photos", "googleMapsUri"]) + ",nextPageToken"
DETAIL_FIELDS = ("id,displayName,formattedAddress,location,rating,userRatingCount,websiteUri,internationalPhoneNumber,"
                 "nationalPhoneNumber,regularOpeningHours,reviews,photos,editorialSummary,priceLevel,googleMapsUri,"
                 "primaryTypeDisplayName,types")


# ---------------------------------------------------------------- http
def _req(url, data=None, headers=None, timeout=20, raw=False):
    h = {"User-Agent": UA, **(headers or {})}
    body = json.dumps(data).encode() if data is not None else None
    if body: h["Content-Type"] = "application/json"
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, body, h), timeout=timeout) as r:
                b = r.read()
                return (b, r.headers.get_content_type(), r.geturl()) if raw else json.loads(b)
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 503) and attempt < 2: time.sleep(2 ** attempt); continue
            raise RuntimeError(f"{e.code} {url[:90]}: {e.read()[:300]!r}")


def places(path, data=None, fields="", method_get=False):
    if not KEY: sys.exit("Set GOOGLE_MAPS_API_KEY first (see README).")
    url = f"https://places.googleapis.com/v1/{path}"
    return _req(url, None if method_get else data, {"X-Goog-Api-Key": KEY, "X-Goog-FieldMask": fields})


def slugify(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-z0-9]+", "-", s.lower().replace("&", " and ")).strip("-")
    return re.sub(r"-(llc|l-l-c|fz|fze|fzco|est|establishment|trading)$", "", s)[:48]


# ---------------------------------------------------------------- website audit
def audit_site(url):
    """Classify an existing website: none / social / modern / outdated, and scrape useful info."""
    out = {"url": url, "status": "none", "signals": [], "emails": [], "socials": {}, "prices": [], "text": ""}
    if not url: return out
    host = urllib.parse.urlparse(url).netloc.lower()
    if any(s in host for s in SOCIAL_HOSTS):
        out["status"] = "social"
        for name, pat in {"instagram": r"instagram\.com/([\w.]+)", "facebook": r"facebook\.com/((?:profile\.php\?id=\d+)|[\w.\-]+)", "tiktok": r"tiktok\.com/@([\w.]+)"}.items():
            m = re.search(pat, url, re.I)
            if m: out["socials"][name] = m.group(1)
        return out
    try:
        html, _, final = _req(url, raw=True, timeout=15)
        html = html.decode("utf-8", "ignore")
    except Exception as e:
        out.update(status="broken", signals=[f"unreachable: {str(e)[:80]}"]); return out
    low, sig = html.lower(), []
    if not final.startswith("https"): sig.append("no https")
    if 'name="viewport"' not in low and "name='viewport'" not in low: sig.append("not mobile-friendly (no viewport)")
    years = [int(y) for y in re.findall(r"(?:©|&copy;|copyright)\s*(?:\d{4}\s*[-–]\s*)?(20[0-2]\d)", low)]
    if years and max(years) <= date.today().year - 4: sig.append(f"copyright {max(years)}")
    m = re.search(r"jquery[-.]?(1\.\d+)", low)
    if m: sig.append(f"jquery {m.group(1)}")
    if ".swf" in low or "shockwave" in low: sig.append("flash")
    if low.count("<table") > 4: sig.append("table layout")
    if re.search(r"<font\b|<marquee|<center>", low): sig.append("legacy tags")
    if any(b in low for b in ("wix.com", "weebly", "blogspot", "jimdo", "site123")): sig.append("free builder")
    if "under construction" in low or "coming soon" in low: sig.append("placeholder page")
    out["signals"] = sig
    out["status"] = "outdated" if len(sig) >= 2 or "placeholder page" in sig else "modern"
    out["emails"] = sorted({e for e in re.findall(r"[\w.+-]+@[\w-]+\.[\w.]+", html) if not e.endswith((".png", ".jpg"))})[:5]
    for name, pat in {"instagram": r"instagram\.com/([\w.]+)", "facebook": r"facebook\.com/([\w.\-]+)",
                      "tiktok": r"tiktok\.com/@([\w.]+)", "whatsapp": r"wa\.me/(\d+)"}.items():
        m = re.search(pat, html, re.I)
        if m and m.group(1).lower() not in ("sharer", "share", "tr", "plugins", "p"): out["socials"][name] = m.group(1)
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"(?is)<(script|style).*?</\1>", "", html)))
    out["prices"] = sorted(set(re.findall(r"(?:AED|Dhs?\.?)\s?[\d,]+(?:\.\d+)?|[\d,]+\s?(?:AED|Dhs)", text, re.I)))[:40]
    out["text"] = text[:15000]  # raw copy for Claude to mine (services, about, prices)
    return out


# ---------------------------------------------------------------- scoring
def worth_score(p, weight, site_status):
    """0-100: is a demo site worth building? (content richness x opportunity x category value)"""
    n, r, photos = p.get("userRatingCount", 0), p.get("rating", 0), len(p.get("photos", []))
    s = min(30, 10 * math.log10(n + 1))                 # social proof / content volume
    s += min(15, photos * 1.5)                          # imagery available (API caps at 10)
    s += max(0, min(15, (r - 3.5) * 10))                # rating quality
    s += {"none": 18, "social": 22, "broken": 24, "outdated": 25, "modern": -40}.get(site_status, 0)
    s += weight
    return round(max(0, min(100, s)))


def buy_likelihood(b):
    """1-10 estimate that the owner pays for the site. Claude refines this after building."""
    site, n = b["site_audit"]["status"], b.get("userRatingCount", 0)
    x = 4.0
    x += {"outdated": 2.5, "broken": 2.5, "social": 1.5, "none": 1.0}.get(site, -3)
    x += 1.0 if n >= 50 else 0.5 if n >= 25 else 0
    x += 1.0 if b.get("category_weight", 0) >= 13 else 0.5 if b.get("category_weight", 0) >= 11 else 0
    x += 0.5 if b.get("phone", "").startswith("+971 5") else 0      # mobile = reachable on WhatsApp
    x += 0.5 if b["site_audit"].get("emails") else 0
    x -= 1.0 if (b.get("rating") or 0) < 4.0 else 0
    x += 1.0 if b.get("owner_reply_rate", 0) >= 0.5 else 0      # owner actively manages their Google profile
    return max(1, min(10, round(x)))


# ---------------------------------------------------------------- commands
def discover(args):
    cand_file = DATA / "candidates.json"
    cands = json.loads(cand_file.read_text()) if cand_file.exists() else {}
    cats = args.cats.split(",") if args.cats else list(CATEGORIES)
    for area in args.areas or AREAS:
        for cat in cats:
            body, pages = {"textQuery": f"{cat} in {area}", "regionCode": "AE", "pageSize": 20}, 0
            while pages < args.pages:
                res = places("places:searchText", body, SEARCH_FIELDS); pages += 1
                for p in res.get("places", []):
                    if p["id"] in cands or p.get("businessStatus") != "OPERATIONAL": continue
                    if p.get("userRatingCount", 0) < args.min_reviews: continue
                    if "photos" in p and len(p["photos"]) < 5: continue  # some keys (demo) never return photos
                    host = urllib.parse.urlparse(p.get("websiteUri", "")).netloc
                    pre = "none" if not host else "social" if any(s in host for s in SOCIAL_HOSTS) else "unknown"
                    p["photos"] = p.get("photos", [])[:10]
                    cands[p["id"]] = {**p, "category": cat, "category_weight": CATEGORIES.get(cat, 10), "area": area,
                                      "pre_status": pre, "score": worth_score(p, CATEGORIES.get(cat, 10), pre)}
                if not res.get("nextPageToken"): break
                body["pageToken"] = res["nextPageToken"]; time.sleep(1.5)
            print(f"{area:28} {cat:24} -> {len(cands)} total candidates")
    DATA.mkdir(exist_ok=True); cand_file.write_text(json.dumps(cands, indent=1, ensure_ascii=False))


def enrich(args):
    cands = json.loads((DATA / "candidates.json").read_text())
    done = {p.stem for p in (DATA / "businesses").glob("*.json")}
    ranked = sorted(cands.values(), key=lambda c: -c["score"])
    count = 0
    for c in ranked:
        if count >= args.top: break
        slug = slugify(c["displayName"]["text"])
        if slug in done or c.get("rejected"): continue
        audit = audit_site(c.get("websiteUri", ""))
        score = worth_score(c, c["category_weight"], audit["status"])
        if audit["status"] == "modern" or score < args.min_score:
            c["rejected"] = f"{audit['status']} site / score {score}"; print("skip", slug, c["rejected"]); continue
        d = places(f"places/{c['id']}", fields=DETAIL_FIELDS, method_get=True)
        name = d["displayName"]["text"]
        img_dir = SITES / slug / "img"; img_dir.mkdir(parents=True, exist_ok=True)
        photos = []
        for i, ph in enumerate(d.get("photos", [])[: args.photos]):
            authors = [a.get("displayName", "") for a in ph.get("authorAttributions", [])]
            try:
                blob, ctype, _ = _req(f"https://places.googleapis.com/v1/{ph['name']}/media?maxWidthPx=1600&key={KEY}", raw=True, timeout=30)
                fn = f"gmaps-{i:02d}.jpg"; (img_dir / fn).write_bytes(blob)
                photos.append({"file": f"img/{fn}", "w": ph.get("widthPx"), "h": ph.get("heightPx"), "authors": authors,
                               "owner_upload": any(name.lower()[:10] in a.lower() for a in authors)})
            except Exception as e:
                print("  photo fail", e)
        biz = {
            "slug": slug, "name": name, "place_id": c["id"], "category": c["category"], "category_weight": c["category_weight"],
            "area": c["area"], "address": d.get("formattedAddress"), "location": d.get("location"),
            "phone": d.get("internationalPhoneNumber", ""), "rating": d.get("rating"), "userRatingCount": d.get("userRatingCount", 0),
            "maps_url": d.get("googleMapsUri"), "website": d.get("websiteUri", ""), "hours": d.get("regularOpeningHours", {}).get("weekdayDescriptions", []),
            "summary": d.get("editorialSummary", {}).get("text", ""), "type": d.get("primaryTypeDisplayName", {}).get("text", ""),
            "reviews": [{"author": rv.get("authorAttribution", {}).get("displayName"), "rating": rv.get("rating"),
                         "when": rv.get("relativePublishTimeDescription"), "text": rv.get("text", {}).get("text", "")}
                        for rv in d.get("reviews", [])],
            "photos": photos, "site_audit": audit, "worth_score": score,
            "socials": audit["socials"], "emails": audit["emails"],
            "todo_manual": ["Check Instagram/Facebook for prices, menu, extra photos", "Pick hero image", "Confirm prices"],
            "site_status": "scouted", "site_url": f"{SITE_BASE}/{slug}/",
        }
        biz["buy_likelihood"] = buy_likelihood(biz)
        (DATA / "businesses").mkdir(parents=True, exist_ok=True)
        (DATA / "businesses" / f"{slug}.json").write_text(json.dumps(biz, indent=1, ensure_ascii=False))
        print(f"OK {slug:40} score={score} buy={biz['buy_likelihood']}/10 site={audit['status']} photos={len(photos)}")
        count += 1
    (DATA / "candidates.json").write_text(json.dumps(cands, indent=1, ensure_ascii=False))
    leads(args)


def _apify(actor, payload, timeout=1800):
    """Start an actor run, poll until it finishes, return dataset items (works for long runs)."""
    tok = os.environ.get("APIFY_TOKEN") or sys.exit("Set APIFY_TOKEN first.")
    run = _req(f"https://api.apify.com/v2/acts/{actor}/runs?token={tok}", payload, timeout=60)["data"]
    t0 = time.time()
    while run["status"] in ("READY", "RUNNING") and time.time() - t0 < timeout:
        run = _req(f"https://api.apify.com/v2/actor-runs/{run['id']}?token={tok}&waitForFinish=60", timeout=90)["data"]
        print(f"  apify {run['status']} {int(time.time() - t0)}s", flush=True)
    if run["status"] != "SUCCEEDED": sys.exit(f"Apify run {run['id']} ended {run['status']}")
    return _req(f"https://api.apify.com/v2/datasets/{run['defaultDatasetId']}/items?token={tok}&clean=true", timeout=120)


def _save_img(url, path):
    blob, _, _ = _req(url, raw=True, timeout=30)
    try:
        from PIL import Image, ImageOps; import io
        im = ImageOps.exif_transpose(Image.open(io.BytesIO(blob))).convert("RGB")
        im.thumbnail((1600, 1600)); im.save(path, quality=72, optimize=True, progressive=True)
        return im.size
    except ImportError:
        path.write_bytes(blob); return None


def apify_enrich(args):
    """Enrich top candidates through Apify's Google Maps scraper: reviews + owner replies, photos,
    popular times, owner description, amenities. Works with any Places key (demo keys return no photos/reviews).
    Cost: roughly $0.02-0.03 per business with 40 reviews + 30 photos."""
    cands = json.loads((DATA / "candidates.json").read_text())
    done = {p.stem for p in (DATA / "businesses").glob("*.json")}
    picked = []
    pool = [cands[i] for i in args.ids.split(",")] if args.ids else sorted(cands.values(), key=lambda c: -c["score"])
    for c in pool:
        if len(picked) >= args.top: break
        slug = slugify(c["displayName"]["text"])
        if slug in done or c.get("rejected"): continue
        audit = audit_site(c.get("websiteUri", ""))
        score = worth_score(c, c["category_weight"], audit["status"])
        if audit["status"] == "modern" or score < args.min_score:
            c["rejected"] = f"{audit['status']} site / score {score}"; print("skip", slug, c["rejected"]); continue
        picked.append((c, slug, audit, score))
    (DATA / "candidates.json").write_text(json.dumps(cands, indent=1, ensure_ascii=False))
    if not picked: return print("nothing to enrich")
    print(f"Apify: scraping {len(picked)} places…")
    items = _apify("compass~crawler-google-places", {
        "startUrls": [{"url": c["googleMapsUri"]} for c, *_ in picked], "maxImages": args.photos, "maxReviews": args.reviews,
        "reviewsSort": "mostRelevant", "language": "en", "maxCrawledPlacesPerSearch": 1, "includeWebResults": False})
    by_id = {it.get("placeId"): it for it in items}
    for c, slug, audit, score in picked:
        d = by_id.get(c["id"])
        if not d: print("  no apify result for", slug); continue
        img_dir = SITES / slug / "img" / "raw"; img_dir.mkdir(parents=True, exist_ok=True)
        photos = []
        srcs = [("owner", re.sub(r"=w\d+-h\d+.*$", "=w1600", u)) for u in d.get("imageUrls") or []]
        srcs += [("review", u) for r in d.get("reviews") or [] for u in r.get("reviewImageUrls") or []]
        for i, (kind, u) in enumerate(srcs):
            fn = img_dir / f"{kind}-{i:02d}.jpg"
            try: photos.append({"file": str(fn.relative_to(SITES / slug)), "source": kind, "size": _save_img(u, fn)})
            except Exception as e: print("  photo fail", str(e)[:60])
        revs = d.get("reviews") or []
        biz = {
            "slug": slug, "name": d.get("title") or c["displayName"]["text"], "place_id": c["id"], "category": c["category"],
            "category_weight": c["category_weight"], "area": c["area"], "address": d.get("address"), "building": d.get("locatedIn"),
            "location": d.get("location"), "phone": c.get("internationalPhoneNumber", d.get("phone", "")),
            "rating": d.get("totalScore"), "userRatingCount": d.get("reviewsCount", 0), "rating_distribution": d.get("reviewsDistribution"),
            "maps_url": d.get("url"), "website": c.get("websiteUri", ""), "categories": d.get("categories"),
            "hours": d.get("openingHours"), "owner_description": d.get("ownerDescription", ""), "amenities": d.get("additionalInfo"),
            "review_tags": [t.get("title") for t in d.get("reviewsTags") or []], "popular_times": d.get("popularTimesHistogram"),
            "owner_reply_rate": round(sum(1 for r in revs if r.get("responseFromOwnerText")) / len(revs), 2) if revs else 0,
            "reviews": [{"author": r.get("name"), "rating": r.get("stars"), "when": r.get("publishAt"),
                         "text": (r.get("text") or "").replace("<br>", "\n"), "owner_reply": r.get("responseFromOwnerText")} for r in revs],
            "photos": photos, "site_audit": audit, "worth_score": score, "socials": audit["socials"], "emails": audit["emails"],
            "todo_manual": ["Pick hero + usable photos from img/raw (Read a contact sheet)", "Search Instagram (verify by phone number)"],
            "site_status": "scouted", "site_url": f"{SITE_BASE}/{slug}/",
        }
        biz["buy_likelihood"] = buy_likelihood(biz)
        (DATA / "businesses").mkdir(parents=True, exist_ok=True)
        (DATA / "businesses" / f"{slug}.json").write_text(json.dumps(biz, indent=1, ensure_ascii=False))
        print(f"OK {slug:40} score={score} buy={biz['buy_likelihood']}/10 photos={len(photos)} reviews={len(revs)} replies={biz['owner_reply_rate']:.0%}")
    leads(args)


def find_socials(args):
    """Find Instagram accounts for built/scouted businesses that have none. Accept only verified matches:
    phone digits in bio/link, or strong name match + UAE location words. ~$0.003 per search."""
    from concurrent.futures import ThreadPoolExecutor
    files = sorted((DATA / "businesses").glob("*.json"))
    todo = [f for f in files if not json.loads(f.read_text()).get("socials", {}).get("instagram") and json.loads(f.read_text()).get("site_status") != "backup"]
    def norm(x): return re.sub(r"[^a-z0-9]", "", (x or "").lower())
    def one(f):
        b = json.loads(f.read_text())
        city = "Sharjah" if "Sharjah" in b["area"] else "Abu Dhabi" if "Abu Dhabi" in b["area"] else "Dubai"
        base = re.split(r"[|(\-]", b["name"])[0].strip()
        try:
            res = _apify("apify~instagram-search-scraper", {"search": f"{base} {city}", "searchType": "user", "searchLimit": 6}, timeout=300)
        except (SystemExit, RuntimeError) as e:
            return f.stem, None, str(e)[:80].split("token=")[0]
        tail = re.sub(r"\D", "", b.get("phone", ""))[-7:]
        key = norm(base)
        best = None
        for u in res:
            if not u.get("username"): continue
            blob = " ".join([u.get("biography") or "", u.get("externalUrl") or "", json.dumps(u.get("externalUrls") or [])])
            digits = re.sub(r"\D", "", blob)
            uname, full = norm(u["username"]), norm(u.get("fullName"))
            phone_hit = bool(tail) and tail in digits
            name_hit = len(key) >= 5 and (key[:10] in uname or key[:10] in full or (uname and uname in key and len(uname) >= 6))
            loc_hit = re.search(r"dubai|sharjah|uae|abu ?dhabi|ajman|971", blob, re.I)
            score = 3 if phone_hit else 2 if (name_hit and loc_hit) else 0
            if score and (not best or score > best[0]): best = (score, u["username"], u.get("followersCount"))
        if best:
            b.setdefault("socials", {})["instagram"] = best[1]
            b["instagram_match"] = {"how": "phone" if best[0] == 3 else "name+location", "followers": best[2]}
            f.write_text(json.dumps(b, indent=1, ensure_ascii=False))
        return f.stem, best, None
    with ThreadPoolExecutor(3) as ex:  # Apify free plan: max 5 concurrent runs
        for slug, best, err in ex.map(one, todo):
            print(f"{slug:42} {'@' + best[1] + ' (' + ('phone' if best[0] == 3 else 'name+loc') + ')' if best else (err or 'no verified match')}")


def leads(_args=None):
    rows = []
    for f in sorted((DATA / "businesses").glob("*.json")):
        b = json.loads(f.read_text())
        built = (SITES / b["slug"] / "index.html").exists()
        ph = b.get("phone", "")
        rows.append({
            "business": b.get("display_name") or b["name"], "category": b["category"], "area": b["area"],
            "site_url": b["site_url"] if built else "(not built)", "buy_likelihood_10": b.get("buy_likelihood", ""),
            "phone": ph, "whatsapp": "https://wa.me/" + re.sub(r"\D", "", ph) if ph.startswith("+971 5") else "",
            "email": ", ".join(b.get("emails", [])), "instagram": b.get("socials", {}).get("instagram", ""),
            "current_website": b.get("website", "") or "none", "site_issue": b["site_audit"]["status"],
            "google": f"{b.get('rating', '')}★ ({b.get('userRatingCount', 0)})", "maps": b.get("maps_url", ""),
            "status": b.get("site_status", ""), "notes": b.get("notes", ""),
        })
    rows.sort(key=lambda r: (r["site_url"] == "(not built)", -(r["buy_likelihood_10"] or 0)))
    if not rows: return print("no businesses yet")
    with open(ROOT / "leads.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
    md = ["# Leads", "", f"_Updated {date.today()} · sorted by likelihood to buy_", "",
          "| # | Business | Type / area | Preview site | Buy /10 | Contact | Current site | Google |", "|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(rows, 1):
        contact = " · ".join(x for x in [r["phone"], r["email"], ("IG @" + r["instagram"]) if r["instagram"] else ""] if x)
        site = f"[open]({r['site_url']})" if r["site_url"].startswith("http") else r["site_url"]
        md.append(f"| {i} | **{r['business']}** | {r['category']} · {r['area']} | {site} | **{r['buy_likelihood_10']}** | {contact} | {r['site_issue']} | {r['google']} |")
    (ROOT / "LEADS.md").write_text("\n".join(md) + "\n")
    print(f"wrote LEADS.md + leads.csv ({len(rows)} leads)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("discover"); d.add_argument("--cats"); d.add_argument("--areas", nargs="*")
    d.add_argument("--pages", type=int, default=1); d.add_argument("--min-reviews", type=int, default=25)
    e = sub.add_parser("enrich"); e.add_argument("--top", type=int, default=10); e.add_argument("--photos", type=int, default=10)
    e.add_argument("--min-score", type=int, default=60)
    a2 = sub.add_parser("apify"); a2.add_argument("--top", type=int, default=10); a2.add_argument("--photos", type=int, default=30); a2.add_argument("--reviews", type=int, default=40)
    a2.add_argument("--min-score", type=int, default=60); a2.add_argument("--ids", help="comma-separated place ids to enrich")
    sub.add_parser("socials")
    sub.add_parser("leads")
    a = ap.parse_args(); {"discover": discover, "enrich": enrich, "apify": apify_enrich, "socials": find_socials, "leads": leads}[a.cmd](a)
