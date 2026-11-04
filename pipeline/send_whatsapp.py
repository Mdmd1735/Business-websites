#!/usr/bin/env python3
"""Send the next N outreach messages through a running whatsapp-mcp bridge.

  python3 pipeline/send_whatsapp.py --n 15 [--dry]

Needs the Go bridge from github.com/lharries/whatsapp-mcp running and paired (REST on :8080).
Picks the highest buy-likelihood leads that have a mobile number and haven't been messaged,
waits a random 60-150 s between sends so it doesn't look like a blast, and records every
send in data/outreach_log.json so nobody gets the same message twice.
"""
import argparse, csv, json, random, re, sqlite3, time, urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "data/outreach_log.json"
SKIP = {"Champions Gym"}  # first sample site, pitched by hand


def send(api, number, text):
    req = urllib.request.Request(f"{api}/api/send", data=json.dumps({"recipient": number, "message": text}).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def chatted_before(store, number):
    """True if this number has any chat on the linked phone (by phone JID or its LID alias)."""
    m = sqlite3.connect(f"{store}/messages.db"); w = sqlite3.connect(f"{store}/whatsapp.db")
    jids = {f"{number}@s.whatsapp.net"}
    try:
        jids |= {f"{lid}@lid" for (lid,) in w.execute("select lid from whatsmeow_lid_map where pn=?", (number,))}
    except sqlite3.Error:
        pass
    q = ",".join("?" * len(jids))
    hit = m.execute(f"select count(*) from chats where jid in ({q})", tuple(jids)).fetchone()[0] \
        + m.execute(f"select count(*) from messages where chat_jid in ({q}) or sender in ({q})", tuple(jids) * 2).fetchone()[0]
    return hit > 0


def hold(slug_url, business):
    """Put the site on hold: the owner already has a chat with us, so don't cold-pitch it."""
    for f in (ROOT / "data/businesses").glob("*.json"):
        b = json.loads(f.read_text())
        if b.get("site_url") == slug_url:
            b["site_status"] = "on_hold"
            b["notes"] = (b.get("notes", "") + " On hold: already have a WhatsApp chat with this number.").strip()
            f.write_text(json.dumps(b, indent=1, ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=15)
    ap.add_argument("--api", default="http://localhost:8080")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--store", help="whatsapp-bridge store/ dir: skip anyone we've chatted with before")
    a = ap.parse_args()
    log = json.loads(LOG.read_text()) if LOG.exists() else {}
    rows = [r for r in csv.DictReader(open(ROOT / "outreach.csv"))
            if r["send_link"] and r["business"] not in SKIP and r["site"] not in log]
    batch = []
    for r in rows:
        if len(batch) == a.n: break
        number = re.search(r"wa\.me/(\d+)", r["send_link"]).group(1)
        if a.store and chatted_before(a.store, number):
            print(f"HOLD {r['business']} -> +{number} (already chatted)", flush=True)
            if not a.dry:
                log[r["site"]] = {"business": r["business"], "number": f"+{number}", "status": "on_hold"}
                LOG.write_text(json.dumps(log, indent=1, ensure_ascii=False)); hold(r["site"], r["business"])
            continue
        batch.append((r, number))
    for i, (r, number) in enumerate(batch):
        if a.dry:
            print(f"[dry] {r['business']} -> +{number}"); continue
        try:
            res = send(a.api, number, r["message"])
        except Exception as e:
            res = {"success": False, "message": str(e)}
        ok = bool(res.get("success"))
        print(f"{'sent' if ok else 'FAIL'} {r['business']} -> +{number} {'' if ok else res.get('message')}", flush=True)
        if not ok and "500" in str(res.get("message")):  # bridge returns 500 when the number has no WhatsApp
            log[r["site"]] = {"business": r["business"], "number": f"+{number}", "status": "failed (probably not on WhatsApp)"}
            LOG.write_text(json.dumps(log, indent=1, ensure_ascii=False))
        if ok:
            log[r["site"]] = {"business": r["business"], "number": f"+{number}",
                              "sent_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "status": "sent"}
            LOG.write_text(json.dumps(log, indent=1, ensure_ascii=False))
        if i < len(batch) - 1:
            time.sleep(random.uniform(60, 150))


if __name__ == "__main__":
    main()
