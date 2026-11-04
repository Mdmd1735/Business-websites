#!/usr/bin/env python3
"""Draft a personal WhatsApp pitch for every built site.

  python3 pipeline/messages.py            -> OUTREACH.md + outreach.csv

Each message is assembled from real details on that business's site (staff named in
reviews, signature service, prices, rating) so no two read the same. Edit SENDER first.
"""
import csv, hashlib, json, re, urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SENDER = "Ahmed"
PRICE = "99 AED"

KIND = {  # category -> (what customers do, short noun)
    "gym": ("look up gyms nearby and compare before they join", "gym"),
    "martial arts academy": ("search for classes for their kids before they visit", "academy"),
    "dance studio": ("search for classes for their kids before they visit", "studio"),
    "yoga studio": ("look up classes nearby before they visit", "studio"),
    "beauty salon": ("check photos and prices online before they book", "salon"),
    "barber shop": ("check a barber's work online before they walk in", "shop"),
    "spa": ("check photos and prices online before they book", "spa"),
    "restaurant": ("look at the menu online before deciding where to eat", "restaurant"),
    "cafe": ("look at the menu online before deciding where to go", "café"),
    "bakery": ("look for a cake shop online before they order", "bakery"),
    "car repair garage": ("search for a garage they can trust before they call", "garage"),
    "car detailing": ("compare shops online before they book", "shop"),
    "dental clinic": ("search for a dentist online and compare before they book", "clinic"),
    "optician": ("search for an eye test nearby before they go", "shop"),
    "veterinary clinic": ("search for a vet they can trust before they call", "clinic"),
    "pet grooming": ("look at a groomer's work online before they book", "salon"),
    "flower shop": ("search for a florist online when they need flowers fast", "shop"),
    "tailor": ("search for a tailor nearby before they go", "shop"),
}

OPENERS = [
    "Hi {name} team, hope you're doing well.",
    "Hello {name}, hope all is good.",
    "Hi! Is this {name}? Hope you're well.",
    "Salam {name} team, hope you're doing great.",
    "Hi {name}, good day!",
]
INTROS = [  # intro + one real compliment, one paragraph
    "My name is {sender}, I make websites for small businesses in the UAE. I came across your {noun} on Google Maps. {praise}",
    "I'm {sender}, I do websites for local businesses here. Came across your {noun} on Google Maps. {praise}",
    "This is {sender}. I design websites for businesses around the UAE and your {noun} came up on Google Maps. {praise}",
]
PRAISE = [
    "{rating} stars from {count} reviews is really impressive{extra}.",
    "{count} reviews at {rating} stars, people clearly love you{extra}.",
    "{count} Google reviews at {rating} stars says a lot{extra}.",
]
MOCKUP_NONE = [
    "I noticed you don't have a website yet, so I went ahead and made a mockup of what yours could look like, with your own photos and reviews:",
    "You don't have a website yet so I put together a quick mockup to show you what it could look like. It uses your real photos, hours and reviews:",
    "Since you don't have a site yet, I made you a mockup of what one could look like. Have a look:",
]
MOCKUP_SOCIAL = [
    "I saw you're mostly on Instagram right now, so I went ahead and made a mockup of what your own website could look like, with your photos and reviews:",
    "Right now people only find you on Instagram and Maps, so I put together a quick mockup of a proper website for you. It uses your real photos, hours and reviews:",
    "Instagram is great but it doesn't show up on Google like a real site does, so I made you a mockup of what one could look like. Have a look:",
]
WHY = [
    "Most people {kind}. A simple site helps you show up on Google and sends more {what} straight to your WhatsApp.",
    "A lot of customers {kind}, and right now all they see is your Maps listing. A website puts everything in one place and they can reach you in one tap.",
    "Most people {kind}. Your own site makes you look more established and brings in more {what} without paying for ads.",
]
OFFER = [
    "If you like it, it's yours for {price}, one time. No monthly fees, no subscription. And I can change anything you want: photos, colours, text, prices, whatever suits you.",
    "The price is just {price}, one-time payment, no subscription or hidden fees. I'll adjust anything you'd like before it goes live.",
    "It's a one-time {price}, nothing monthly. Happy to change the design, photos or wording until you're happy with it.",
]
CLOSE = [
    "Let me know what you think, no pressure at all 🙂\n{sender}",
    "Would love to hear your thoughts, even if it's not for you.\nThanks,\n{sender}",
    "Take a look when you get a minute and tell me what you think.\n{sender}",
    "Any questions just reply here. Thanks for your time!\n{sender}",
]
SKIP_ITEMS = {"chicken", "bridal", "strength floor", "shisha"}
WHAT = {"restaurant": "orders and bookings", "cafe": "visits and bookings", "bakery": "orders", "gym": "new members",
        "martial arts academy": "new students", "dance studio": "new students", "yoga studio": "new members",
        "car repair garage": "customers", "car detailing": "bookings", "dental clinic": "patients",
        "veterinary clinic": "clients", "optician": "customers", "flower shop": "orders", "tailor": "customers"}


def pick(options, slug, salt):
    h = int(hashlib.md5(f"{slug}{salt}".encode()).hexdigest(), 16)
    return options[h % len(options)]


def extra_detail(b, c, name):
    """One genuine, specific compliment pulled from the site content."""
    if not c: return ""
    for sec in c.get("sections", []):
        if sec["type"] == "team":
            top = [m for m in sec.get("items", []) if m.get("count")]
            if top:
                m = max(top, key=lambda m: m["count"])
                who = m["name"].replace("Coach ", "")
                first = who.replace("Dr. ", "").replace("Mrs. ", "").split()[0]
                if first.lower() in name.lower(): return ""  # owner named after the shop: reads odd
                return (f", and loads of people mention {who} by name" if m["count"] >= 5
                        else f", and I saw people mention {who} by name")
    for sec in c.get("sections", []):
        if sec["type"] == "services" and sec.get("items"):
            it = re.split(r"[,(&]", sec["items"][0]["name"])[0].strip().lower()
            if it and len(it) < 28 and it not in SKIP_ITEMS: return f", and people really rave about the {it}"
    return ""


def has_site_note(b):
    st = (b.get("site_audit") or {}).get("status")
    return st in ("social",)


def build():
    rows = []
    for f in sorted((ROOT / "data/businesses").glob("*.json")):
        b = json.loads(f.read_text())
        if b.get("site_status") != "built": continue
        slug = b["slug"]
        cfile = ROOT / "data/content" / f"{slug}.json"
        c = json.loads(cfile.read_text()) if cfile.exists() else None
        name = re.sub(r"\s*\(.*?\)", "", b.get("display_name") or re.split(r"\s[|(\-–]\s?", b["name"])[0]).strip()
        if re.search(r"clinic|vet", name, re.I): noun = "clinic"
        greet = re.sub(r"^The\s+", "", name)
        kind, noun = KIND.get(b.get("category"), ("look businesses up online first", "business"))
        what = WHAT.get(b.get("category"), "customers")
        rating = f"{float(b['rating']):.1f}" if b.get("rating") else ""
        count = f"{int(b.get('userRatingCount') or 0):,}"
        mock = pick(MOCKUP_SOCIAL if has_site_note(b) else MOCKUP_NONE, slug, 3)
        praise = pick(PRAISE, slug, 4).format(rating=rating, count=count, extra=extra_detail(b, c, name)) if rating else ""
        intro = pick(INTROS, slug, 2)
        if not praise: intro = intro.replace(" {praise}", "")
        parts = [
            pick(OPENERS, slug, 1).format(name=greet),
            intro.format(sender=SENDER, noun=noun, praise=praise),
            mock,
            b["site_url"],
            pick(WHY, slug, 5).format(kind=kind, what=what),
            pick(OFFER, slug, 6).format(price=PRICE),
            pick(CLOSE, slug, 7).format(sender=SENDER),
        ]
        msg = "\n\n".join(p for p in parts if p)
        phone = b.get("phone", "")
        digits = re.sub(r"\D", "", (c or {}).get("whatsapp") or phone)
        is_mobile = digits.startswith("9715")
        rows.append({"business": name, "category": b.get("category"), "area": b.get("area"), "buy": b.get("buy_likelihood"),
                     "phone": phone, "channel": "WhatsApp" if is_mobile else "Landline: call or visit, then send this",
                     "send_link": f"https://wa.me/{digits}?text={urllib.parse.quote(msg)}" if is_mobile else "",
                     "site": b["site_url"], "message": msg})
    rows.sort(key=lambda r: -(r["buy"] or 0))
    with open(ROOT / "outreach.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
    md = ["# WhatsApp outreach", "", f"{len(rows)} messages, sorted by likelihood to buy. Signed as **{SENDER}**; change `SENDER` in `pipeline/messages.py` to resend under another name."
          "", "",
          "On a phone, tap **Open in WhatsApp** and the message is pre-filled. Landline-only businesses are marked: call or visit, then send the text from your own WhatsApp.", ""]
    for i, r in enumerate(rows, 1):
        md += [f"## {i}. {r['business']}", f"{r['category']} · {r['area']} · buy {r['buy']}/10 · {r['phone']}", ""]
        md += [f"[Open in WhatsApp]({r['send_link']})" if r["send_link"] else f"_{r['channel']}_", ""]
        md += ["```", r["message"], "```", ""]
    (ROOT / "OUTREACH.md").write_text("\n".join(md))
    print(f"wrote OUTREACH.md + outreach.csv ({len(rows)} messages, {sum(1 for r in rows if r['send_link'])} with WhatsApp links)")


if __name__ == "__main__":
    build()
