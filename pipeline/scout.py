#!/usr/bin/env python3
"""UAE lead scout: find businesses with weak/no websites, score them, collect content.

Stdlib only. Needs GOOGLE_MAPS_API_KEY (Places API (New) enabled).

  python3 pipeline/scout.py discover --cats gym,restaurant --areas "Al Quoz, Dubai" "Al Nahda, Sharjah"
  python3 pipeline/scout.py enrich --top 10          # details + reviews + photos + old-site scrape
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
    "car repair garage": 12, "car detailing": 11, "furniture store": 11, "interior design company": 14,
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
        out["status"] = "social"; return out
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
                    if p.get("userRatingCount", 0) < args.min_reviews or len(p.get("photos", [])) < 5: continue
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


def leads(_args=None):
    rows = []
    for f in sorted((DATA / "businesses").glob("*.json")):
        b = json.loads(f.read_text())
        built = (SITES / b["slug"] / "index.html").exists()
        ph = b.get("phone", "")
        rows.append({
            "business": b["name"], "category": b["category"], "area": b["area"],
            "site_url": b["site_url"] if built else "(not built)", "buy_likelihood_10": b.get("buy_likelihood", ""),
            "phone": ph, "whatsapp": "https://wa.me/" + re.sub(r"\D", "", ph) if ph.startswith("+971 5") else "",
            "email": ", ".join(b.get("emails", [])), "instagram": b.get("socials", {}).get("instagram", ""),
            "current_website": b.get("website", "") or "none", "site_issue": b["site_audit"]["status"],
            "google": f"{b.get('rating', '')}★ ({b.get('userRatingCount', 0)})", "maps": b.get("maps_url", ""),
            "status": b.get("site_status", ""), "notes": b.get("notes", ""),
        })
    rows.sort(key=lambda r: -(r["buy_likelihood_10"] or 0))
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
    sub.add_parser("leads")
    a = ap.parse_args(); {"discover": discover, "enrich": enrich, "leads": leads}[a.cmd](a)
