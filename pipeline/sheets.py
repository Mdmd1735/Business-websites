#!/usr/bin/env python3
"""Contact sheets of docs/<slug>/img/raw for every scouted business (owner photos first, max 36).
  python3 pipeline/sheets.py <outdir> [slug ...]"""
import glob, json, os, sys
from pathlib import Path
from PIL import Image, ImageDraw
ROOT = Path(__file__).resolve().parent.parent
out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
slugs = sys.argv[2:] or [json.load(open(f))["slug"] for f in sorted((ROOT / "data/businesses").glob("*.json")) if json.load(open(f)).get("site_status") == "scouted"]
for slug in slugs:
    fs = sorted(glob.glob(str(ROOT / f"docs/{slug}/img/raw/*.jpg")))
    fs = ([f for f in fs if "/owner-" in f] + [f for f in fs if "/review-" in f])[:36]
    if not fs: print("no photos", slug); continue
    W, cols = 220, 9; rows = (len(fs) + cols - 1) // cols
    sh = Image.new("RGB", (cols * W, rows * W), "white")
    for i, p in enumerate(fs):
        try: im = Image.open(p).convert("RGB")
        except Exception: continue
        sz = im.size; im.thumbnail((W - 4, W - 18)); x, y = (i % cols) * W, (i // cols) * W
        sh.paste(im, (x + 2, y + 16)); ImageDraw.Draw(sh).text((x + 3, y + 2), f"{os.path.basename(p)[:-4]} {sz[0]}x{sz[1]}", fill="black")
    sh.save(out / f"{slug}.jpg", quality=80); print(slug, len(fs))
