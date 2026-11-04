#!/usr/bin/env python3
"""Hero montage for QA: python3 pipeline/montage.py <qa_dir> <out.png> slug [slug ...]"""
import os, sys
from PIL import Image, ImageDraw
qa, out, slugs = sys.argv[1], sys.argv[2], sys.argv[3:]
for kind, (W, H), cols in [("desktop", (480, 300), 4), ("mobile", (195, 422), 10)]:
    rows = (len(slugs) + cols - 1) // cols; sh = Image.new("RGB", (cols * W, rows * (H + 16)), "white")
    for i, s in enumerate(slugs):
        p = f"{qa}/{s}-{kind}-hero.png"
        if not os.path.exists(p): continue
        im = Image.open(p).convert("RGB").resize((W, H)); x, y = (i % cols) * W, (i // cols) * (H + 16)
        sh.paste(im, (x, y + 16)); ImageDraw.Draw(sh).text((x + 4, y + 2), s, fill="black")
    sh.save(out.replace(".png", f"-{kind}.png"))
