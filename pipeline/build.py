#!/usr/bin/env python3
"""Render a site from data/businesses/<slug>.json (scraped facts) + data/content/<slug>.json (copy + design choices).

  python3 pipeline/build.py <slug> [<slug> ...]      # writes docs/<slug>/{index.html,styles.css,main.js}

Content JSON keys: preset, theme (overrides), hero{variant split|full|stack, kicker, ar_name, title_lines, accent_line,
lede, image, image_alt, caption, secondary{label,href}, badge{label,text}}, brand{name,sub,mark,footer_word},
cta_label, ticker[], sections[] (services|menu|crowd|team|gallery|reviews|asks|faq|visit), review_picks[], socials{}, seo{}.
"""
import json, re, sys, urllib.parse
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parent.parent
KITS = ROOT / "kits"
WA_PATH = "M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2Zm5.2 14.2c-.2.6-1.3 1.2-1.8 1.2-.5.1-1 .2-3.3-.7-2.8-1.1-4.6-4-4.7-4.2-.1-.2-1.1-1.5-1.1-2.9 0-1.4.7-2 1-2.3.2-.3.5-.3.7-.3h.5c.2 0 .4 0 .6.5l.8 2c.1.2.1.4 0 .5l-.3.5-.4.4c-.1.1-.3.3-.1.6.2.3.8 1.3 1.6 2 1.1 1 2 1.3 2.3 1.4.3.1.5.1.6-.1l.9-1.1c.2-.3.4-.2.7-.1l1.9.9c.3.1.5.2.5.3.1.2.1.8-.1 1.4Z"
ICONS = {
    "instagram": '<svg viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.5" cy="6.5" r=".8" fill="currentColor"/></svg>',
    "facebook": '<svg viewBox="0 0 24 24"><path d="M14 8h3V4h-3a4 4 0 0 0-4 4v2H7v4h3v7h4v-7h3l1-4h-4V8.5c0-.3.2-.5.5-.5Z"/></svg>',
    "tiktok": '<svg viewBox="0 0 24 24"><path d="M14 3v11.5a3.5 3.5 0 1 1-3-3.5M14 3c.5 2.5 2.5 4.5 5 4.5"/></svg>',
}
SOCIAL_URL = {"instagram": "https://instagram.com/{}", "facebook": "https://facebook.com/{}", "tiktok": "https://tiktok.com/@{}"}

# Design presets. Every site picks one and may override tokens; vary hero variant/frame per site too.
BASE = {"r": "8px", "btn_r": "8px", "mark_r": "8px", "dstyle": "normal", "dcase": "none", "dtrack": "-0.01em", "dlh": ".98",
        "h1vw": "8vw", "h1max": "124px", "h1lh": ".92", "h2max": "78px", "hero_ratio": "4/5", "hero_pos": "center", "slab_o": "1",
        "arabic": '"Cairo","Noto Kufi Arabic",sans-serif', "max": "1280px", "gut": "clamp(16px,4vw,56px)", "ease": "cubic-bezier(.16,1,.3,1)"}
DARK = {"mode": "dark", "text": "#F4F3EF", "text_2": "#C9C8C2", "dim": "#9C9B95", "line": "rgba(255,255,255,.1)", "line_strong": "rgba(255,255,255,.22)",
        "nav_bg": "rgba(12,12,13,.84)", "card_glass": "rgba(20,20,22,.9)", "tint": "rgba(255,255,255,.07)", "map_filter": "grayscale(1) invert(.9) contrast(.9)",
        "band_bg": "#F2F1ED", "band_text": "#17171A", "band_card": "#FFFFFF", "band_line": "#E1E0DA", "ask_bg": "#111113", "ask_text": "#FFFFFF",
        "quiet": "#55705E", "accent_on_photo": "var(--accent)"}
LIGHT = {"mode": "light", "text": "#17171A", "text_2": "#43434A", "dim": "#6B6B73", "line": "rgba(0,0,0,.09)", "line_strong": "rgba(0,0,0,.2)",
         "nav_bg": "rgba(255,255,255,.86)", "card_glass": "rgba(255,255,255,.92)", "tint": "rgba(0,0,0,.05)", "map_filter": "grayscale(.3)",
         "band_card": "rgba(255,255,255,.06)", "band_line": "rgba(255,255,255,.14)", "ask_bg": "#FFFFFF", "ask_text": "#17171A",
         "quiet": "#9DBFA8", "accent_on_photo": "#FFFFFF"}
PRESETS = {
    "noir-red": {**DARK, "bg": "#0A0A0B", "surface": "#141416", "surface_2": "#1E1F23", "accent": "#E0182D", "accent_text": "#FF3B4E", "on_accent": "#FFFFFF", "duo": "#8E0D1B", "busy": "#8E0D1B", "glow": "rgba(224,24,45,.18)", "band_accent": "#E0182D",
                 "display": '"Barlow Condensed","Arial Narrow",sans-serif', "body": '"Barlow",system-ui,sans-serif', "dw": "800", "dstyle": "italic", "dcase": "uppercase", "dlh": ".9", "h1lh": ".86",
                 "google_fonts": "family=Barlow+Condensed:ital,wght@0,700;0,800;1,800&family=Barlow:wght@400;500;600&family=Cairo:wght@700"},
    "steel-volt": {**DARK, "bg": "#0C0E10", "surface": "#14181B", "surface_2": "#1C2226", "accent": "#C6F432", "accent_text": "#C6F432", "on_accent": "#0C0E10", "duo": "#3E4D0E", "busy": "#6C8A12", "glow": "rgba(198,244,50,.12)", "band_accent": "#4F6B00",
                   "display": '"Chakra Petch",system-ui,sans-serif', "body": '"Inter Tight",system-ui,sans-serif', "dw": "700", "dcase": "uppercase", "r": "4px", "btn_r": "4px", "mark_r": "4px",
                   "google_fonts": "family=Chakra+Petch:wght@600;700&family=Inter+Tight:wght@400;500;600&family=Cairo:wght@700"},
    "garage-amber": {**DARK, "bg": "#111214", "surface": "#191B1E", "surface_2": "#23262A", "accent": "#FFB000", "accent_text": "#FFB000", "on_accent": "#111214", "duo": "#5A3E00", "busy": "#9A6A00", "glow": "rgba(255,176,0,.14)", "band_accent": "#B27800",
                     "display": '"Rajdhani",system-ui,sans-serif', "body": '"Barlow",system-ui,sans-serif', "dw": "700", "dcase": "uppercase", "r": "3px", "btn_r": "3px", "mark_r": "3px", "dlh": ".95",
                     "google_fonts": "family=Rajdhani:wght@600;700&family=Barlow:wght@400;500;600&family=Cairo:wght@700"},
    "luxe-gold": {**DARK, "bg": "#0F0D0B", "surface": "#181512", "surface_2": "#221D18", "accent": "#C9A46A", "accent_text": "#D9B57B", "on_accent": "#14110D", "duo": "#4A3A22", "busy": "#7A5E33", "glow": "rgba(201,164,106,.14)", "band_accent": "#9A7536",
                  "display": '"Bodoni Moda",Georgia,serif', "body": '"Jost",system-ui,sans-serif', "dw": "500", "dtrack": "-0.02em", "r": "2px", "btn_r": "999px", "mark_r": "50%", "h1max": "112px",
                  "google_fonts": "family=Bodoni+Moda:ital,opsz,wght@0,6..96,500;1,6..96,500&family=Jost:wght@400;500;600&family=Cairo:wght@700"},
    "rose-blush": {**LIGHT, "bg": "#FBF6F4", "surface": "#FFFFFF", "surface_2": "#F3E8E4", "accent": "#B4475E", "accent_text": "#A23C53", "on_accent": "#FFFFFF", "duo": "#E8C6CD", "busy": "#C9798A", "glow": "rgba(180,71,94,.12)",
                   "band_bg": "#2B1A1E", "band_text": "#F7ECEE", "band_accent": "#F0A3B3", "display": '"Italiana",Georgia,serif', "body": '"Nunito Sans",system-ui,sans-serif', "dw": "400", "r": "18px", "btn_r": "999px", "mark_r": "50%", "dtrack": "0",
                   "google_fonts": "family=Italiana&family=Nunito+Sans:wght@400;600;700&family=Cairo:wght@700"},
    "sage-spa": {**LIGHT, "bg": "#F4F5F0", "surface": "#FFFFFF", "surface_2": "#E6EADF", "accent": "#4F6B57", "accent_text": "#3F5A47", "on_accent": "#FFFFFF", "duo": "#C8D3C2", "busy": "#7E9A86", "glow": "rgba(79,107,87,.12)",
                 "band_bg": "#1E2A22", "band_text": "#EEF2EC", "band_accent": "#A9C7B1", "display": '"Cormorant Garamond",Georgia,serif', "body": '"Karla",system-ui,sans-serif', "dw": "500", "r": "14px", "btn_r": "999px", "mark_r": "50%", "h1lh": ".95",
                 "google_fonts": "family=Cormorant+Garamond:ital,wght@0,500;1,500&family=Karla:wght@400;500;600&family=Cairo:wght@700"},
    "clinic-teal": {**LIGHT, "bg": "#F6FAFA", "surface": "#FFFFFF", "surface_2": "#E3EFEF", "accent": "#0E7C7B", "accent_text": "#0B6A69", "on_accent": "#FFFFFF", "duo": "#BFDCDB", "busy": "#5BA6A5", "glow": "rgba(14,124,123,.12)",
                    "band_bg": "#0D2B2E", "band_text": "#E9F4F4", "band_accent": "#7FD3D1", "display": '"Plus Jakarta Sans",system-ui,sans-serif', "body": '"Plus Jakarta Sans",system-ui,sans-serif', "dw": "700", "dtrack": "-0.03em", "r": "16px", "btn_r": "12px", "mark_r": "12px", "h1max": "96px", "h2max": "64px",
                    "google_fonts": "family=Plus+Jakarta+Sans:wght@400;500;600;700&family=Cairo:wght@700"},
    "clinic-navy": {**LIGHT, "bg": "#F7F8FB", "surface": "#FFFFFF", "surface_2": "#E6EAF3", "accent": "#1F3B73", "accent_text": "#1F3B73", "on_accent": "#FFFFFF", "duo": "#C9D3EA", "busy": "#5A73A8", "glow": "rgba(31,59,115,.1)",
                    "band_bg": "#101C36", "band_text": "#EDF1FA", "band_accent": "#8FB0F0", "display": '"Manrope",system-ui,sans-serif', "body": '"Manrope",system-ui,sans-serif', "dw": "800", "dtrack": "-0.035em", "r": "14px", "btn_r": "10px", "mark_r": "10px", "h1max": "92px", "h2max": "62px",
                    "google_fonts": "family=Manrope:wght@400;500;600;700;800&family=Cairo:wght@700"},
    "bistro-olive": {**LIGHT, "bg": "#F3F0E6", "surface": "#FBF9F2", "surface_2": "#E5E0CF", "accent": "#5D6B2F", "accent_text": "#4C5826", "on_accent": "#FFFFFF", "duo": "#C9CDAA", "busy": "#8E9A5B", "glow": "rgba(93,107,47,.12)",
                     "band_bg": "#22261A", "band_text": "#F1EFE4", "band_accent": "#C8D27F", "display": '"Fraunces",Georgia,serif', "body": '"Work Sans",system-ui,sans-serif', "dw": "600", "dtrack": "-0.02em", "r": "10px", "btn_r": "999px", "mark_r": "50%",
                     "google_fonts": "family=Fraunces:ital,opsz,wght@0,9..144,600;1,9..144,600&family=Work+Sans:wght@400;500;600&family=Cairo:wght@700"},
    "spice-ember": {**DARK, "bg": "#140D0A", "surface": "#1D1410", "surface_2": "#2A1C16", "accent": "#E8642C", "accent_text": "#FF8A52", "on_accent": "#1A0C05", "duo": "#6B2A10", "busy": "#9C3E17", "glow": "rgba(232,100,44,.16)", "band_accent": "#C24E1C",
                    "display": '"DM Serif Display",Georgia,serif', "body": '"DM Sans",system-ui,sans-serif', "dw": "400", "dtrack": "-0.01em", "r": "12px", "btn_r": "999px", "mark_r": "50%",
                    "google_fonts": "family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@400;500;600&family=Cairo:wght@700"},
    "cafe-mocha": {**LIGHT, "bg": "#EFE7DD", "surface": "#F8F3EC", "surface_2": "#E2D4C3", "accent": "#3B2418", "accent_text": "#6A3B22", "on_accent": "#F8F3EC", "duo": "#C8AE93", "busy": "#8C5E3F", "glow": "rgba(106,59,34,.12)",
                   "band_bg": "#2A1A12", "band_text": "#F3E9DE", "band_accent": "#E2A878", "display": '"Syne",system-ui,sans-serif', "body": '"Manrope",system-ui,sans-serif', "dw": "700", "dtrack": "-0.03em", "r": "6px", "btn_r": "6px", "mark_r": "6px",
                   "google_fonts": "family=Syne:wght@600;700;800&family=Manrope:wght@400;500;600&family=Cairo:wght@700"},
    "barber-ink": {**DARK, "bg": "#101113", "surface": "#18191C", "surface_2": "#212226", "accent": "#D7C3A3", "accent_text": "#E3CFAD", "on_accent": "#121214", "duo": "#4C4234", "busy": "#7F6B4D", "glow": "rgba(215,195,163,.12)", "band_accent": "#8C6E3E",
                   "display": '"Oswald",sans-serif', "body": '"Source Sans 3",system-ui,sans-serif', "dw": "600", "dcase": "uppercase", "dtrack": "0.01em", "r": "4px", "btn_r": "4px", "mark_r": "50%",
                   "google_fonts": "family=Oswald:wght@500;600&family=Source+Sans+3:wght@400;600&family=Cairo:wght@700"},
    "pet-sky": {**LIGHT, "bg": "#F5F8FC", "surface": "#FFFFFF", "surface_2": "#E2ECF7", "accent": "#2563EB", "accent_text": "#1D4FC4", "on_accent": "#FFFFFF", "duo": "#C7D8F5", "busy": "#6E95E0", "glow": "rgba(37,99,235,.1)",
                "band_bg": "#13234A", "band_text": "#EEF3FC", "band_accent": "#FFC94D", "display": '"Fredoka",system-ui,sans-serif', "body": '"Nunito",system-ui,sans-serif', "dw": "600", "r": "22px", "btn_r": "999px", "mark_r": "50%", "dtrack": "-0.01em",
                "google_fonts": "family=Fredoka:wght@500;600&family=Nunito:wght@400;600;700&family=Cairo:wght@700"},
    "bakery-butter": {**LIGHT, "bg": "#FFF9EE", "surface": "#FFFFFF", "surface_2": "#F6E9CF", "accent": "#C2452D", "accent_text": "#A93A25", "on_accent": "#FFFFFF", "duo": "#F1D3B4", "busy": "#D9825F", "glow": "rgba(194,69,45,.1)",
                      "band_bg": "#3A1E14", "band_text": "#FFF4E4", "band_accent": "#F6B86A", "display": '"Gloock",Georgia,serif', "body": '"Outfit",system-ui,sans-serif', "dw": "400", "r": "20px", "btn_r": "999px", "mark_r": "50%",
                      "google_fonts": "family=Gloock&family=Outfit:wght@400;500;600&family=Cairo:wght@700"},
    "royal-plum": {**DARK, "bg": "#120E16", "surface": "#1B1521", "surface_2": "#251D2D", "accent": "#B98AE0", "accent_text": "#CBA4EE", "on_accent": "#150F1A", "duo": "#4A3260", "busy": "#7B56A0", "glow": "rgba(185,138,224,.14)", "band_accent": "#7A4FA8",
                   "display": '"Marcellus",Georgia,serif', "body": '"Mulish",system-ui,sans-serif', "dw": "400", "dcase": "uppercase", "dtrack": "0.02em", "r": "6px", "btn_r": "999px", "mark_r": "50%", "h1max": "104px",
                   "google_fonts": "family=Marcellus&family=Mulish:wght@400;600;700&family=Cairo:wght@700"},
    "ocean-wash": {**LIGHT, "bg": "#F2F7F8", "surface": "#FFFFFF", "surface_2": "#DCEBEE", "accent": "#0B5D74", "accent_text": "#0B5D74", "on_accent": "#FFFFFF", "duo": "#BEDBE3", "busy": "#4F93A8", "glow": "rgba(11,93,116,.1)",
                   "band_bg": "#08262F", "band_text": "#E8F4F7", "band_accent": "#5FD0E8", "display": '"Archivo",system-ui,sans-serif', "body": '"Archivo",system-ui,sans-serif', "dw": "800", "dcase": "uppercase", "dtrack": "-0.02em", "r": "10px", "btn_r": "10px", "mark_r": "10px", "dlh": ".9",
                   "google_fonts": "family=Archivo:wght@400;500;600;800&family=Cairo:wght@700"},
}
TOKEN_MAP = {k: "--" + k.replace("_", "-") for k in set(BASE) | {k for p in PRESETS.values() for k in p}}


def parse_hours(rows):
    """[{'day':'Monday','hours':'9 AM to 1 PM, 4 to 10 PM'}] -> ({jsday: [[o,c],...]}, table rows)"""
    days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    out, table = {}, []
    tre = re.compile(r"(\d{1,2})(?::(\d{2}))?\s*(AM|PM)?", re.I)
    for r in rows or []:
        d = days.index(r["day"]) if r.get("day") in days else None
        if d is None: continue
        txt = r["hours"].replace(" ", " ").replace(" ", " ").replace("–", "-").strip()
        spans = []
        if re.search(r"open 24", txt, re.I): spans = [[0, 1440]]
        elif not re.search(r"closed", txt, re.I):
            for part in txt.split(","):
                m = re.split(r"\s+to\s+|\s*-\s*", part.strip())
                if len(m) != 2: continue
                a, b = tre.search(m[0]), tre.search(m[1])
                if not a or not b: continue
                ap_b = (b.group(3) or "").upper(); ap_a = (a.group(3) or ap_b).upper()
                def mins(g, ap):
                    h = int(g.group(1)) % 12 + (12 if ap == "PM" else 0); return h * 60 + int(g.group(2) or 0)
                o, c = mins(a, ap_a), mins(b, ap_b)
                if not a.group(3) and o > c: o -= 720  # "11 to 2 PM" -> 11 AM
                if c <= o: c += 1440
                spans.append([o, c])
        out[d] = spans
        nice = re.sub(r"\s+to\s+", " – ", txt).replace("Open 24 hours", "Open 24 hours")
        table.append({"d": d, "day": r["day"], "text": nice})
    order = [1, 2, 3, 4, 5, 6, 0]
    table.sort(key=lambda x: order.index(x["d"]))
    return out, table


def pick_reviews(b, picks=None, n=4):
    revs = [r for r in b.get("reviews", []) if r.get("text")]
    if picks: return [revs[i] for i in picks if i < len(revs)]
    good = [r for r in revs if (r.get("rating") or 0) >= 4 and 90 <= len(r["text"]) <= 420]
    good.sort(key=lambda r: (bool(r.get("owner_reply")), len(r["text"])), reverse=True)
    return good[:n]


def clean(t):
    t = re.sub(r"\s+", " ", (t or "").replace("<br>", " ")).strip()
    return t


def build(slug):
    b = json.loads((ROOT / "data/businesses" / f"{slug}.json").read_text())
    c = json.loads((ROOT / "data/content" / f"{slug}.json").read_text())
    tok = {**BASE, **PRESETS[c["preset"]], **c.get("theme", {})}
    hours, table = parse_hours(b.get("hours"))
    phone = b.get("phone", "")
    digits = re.sub(r"\D", "", phone)
    wa = phone.startswith("+971 5") or digits.startswith("9715")
    wa_base = f"https://wa.me/{digits}"
    cta_label = c.get("cta_label", "Message us on WhatsApp" if wa else "Call us")
    cta = {"wa": wa, "ext": wa, "label": cta_label, "short": "WhatsApp" if wa else "Call",
           "href": f"{wa_base}?text=" + urllib.parse.quote(c.get("cta_text", f"Hi {b['name']}, I'd like to know more.")) if wa else f"tel:+{digits}"}
    socials = []
    for k, v in {**b.get("socials", {}), **c.get("socials", {})}.items():
        if k in ICONS and v: socials.append({"label": k.capitalize(), "icon": ICONS[k], "url": v if v.startswith("http") else SOCIAL_URL[k].format(v)})
    dist = None
    rd = b.get("rating_distribution")
    if rd:
        vals = [rd.get(k, 0) for k in ["fiveStar", "fourStar", "threeStar", "twoStar", "oneStar"]]; tot = sum(vals) or 1
        dist = [{"stars": 5 - i, "n": v, "pct": round(100 * v / tot, 1)} for i, v in enumerate(vals)]
    reviews = [{**r, "text": clean(r["text"]), "owner_reply": clean(r.get("owner_reply"))[:180] or None} for r in pick_reviews(b, c.get("review_picks"))]
    pt = b.get("popular_times")
    busy = None
    if pt and any(pt.values()):
        keys = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"]
        busy = {i: [next((x["occupancyPercent"] for x in (pt.get(k) or []) if x["hour"] == h), 0) for h in range(24)] for i, k in enumerate(keys)}
    use_crowd = busy is not None and any(s["type"] == "crowd" for s in c["sections"])
    for s in c["sections"]: s.setdefault("id", s["type"])
    nav = c.get("nav") or [{"id": s["id"], "label": s.get("nav", s["type"].capitalize())} for s in c["sections"] if s.get("nav")]
    addr = b.get("address", "").replace(" - United Arab Emirates", "").replace(", United Arab Emirates", "")
    address_html = "<br>".join(x.strip() for x in ([b["building"]] if b.get("building") and b["building"] not in addr else []) + addr.split(" - ") if x.strip())
    schema = {"@context": "https://schema.org", "@type": c.get("schema_type", "LocalBusiness"), "name": b["name"], "telephone": phone,
              "address": {"@type": "PostalAddress", "streetAddress": addr, "addressCountry": "AE"},
              **({"geo": {"@type": "GeoCoordinates", "latitude": b["location"]["lat"], "longitude": b["location"]["lng"]}} if b.get("location") else {}),
              **({"aggregateRating": {"@type": "AggregateRating", "ratingValue": str(b["rating"]), "reviewCount": str(b["userRatingCount"])}} if b.get("rating") else {})}
    brand = {"name": b["name"], "sub": b["area"], "mark": b["name"][0], "footer_word": b["name"].split()[0], **c.get("brand", {})}
    hero = {"variant": "split", "accent_line": len(c["hero"]["title_lines"]) - 1, "secondary": {"label": "Plan your visit", "href": "#visit"}, **c["hero"]}
    env = Environment(loader=FileSystemLoader(KITS), autoescape=True)
    html = env.get_template("site.html.j2").render(
        b=b, t=tok, hero=hero, brand=brand, nav=nav, cta=cta, wa_path=WA_PATH, wa_base=wa_base, ticker=c.get("ticker"),
        sections=c["sections"], crowd=use_crowd, hours=table if hours else None, dist=dist, reviews=reviews, socials=socials,
        proof_note=c.get("proof_note"), address_html=address_html, phone_tel="+" + digits, seo=c["seo"],
        schema=json.dumps(schema, ensure_ascii=False),
        ask_href=lambda a: f"{wa_base}?text=" + urllib.parse.quote(a) if wa else f"tel:+{digits}",
        site_js=json.dumps({"hours": hours or None, "busy": busy if use_crowd else None}))
    out = ROOT / "docs" / slug; out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(html)
    root = ":root{" + ";".join(f"{TOKEN_MAP[k]}:{v}" for k, v in tok.items() if k in TOKEN_MAP and k not in ("mode", "google_fonts")) + "}\n"
    (out / "styles.css").write_text(root + (KITS / "site.css").read_text() + c.get("extra_css", ""))
    (out / "main.js").write_text((KITS / "site.js").read_text())
    print("built", slug)


if __name__ == "__main__":
    for s in sys.argv[1:]: build(s)
