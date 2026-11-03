#!/usr/bin/env python3
"""Copy chosen raw photos to docs/<slug>/img/<name>.jpg, then delete img/raw.
  python3 pipeline/pick.py <slug> hero=owner-02 floor=review-03 ...   (add --keep to keep raw/)"""
import shutil, sys
from pathlib import Path
from PIL import Image, ImageOps
slug, pairs = sys.argv[1], [a for a in sys.argv[2:] if "=" in a]
d = Path(__file__).resolve().parent.parent / "docs" / slug / "img"
for p in pairs:
    name, src = p.split("=", 1)
    im = ImageOps.exif_transpose(Image.open(d / "raw" / f"{src}.jpg")).convert("RGB"); im.thumbnail((1600, 1600))
    im.save(d / f"{name}.jpg", quality=74, optimize=True, progressive=True); print(name, im.size)
if "--keep" not in sys.argv: shutil.rmtree(d / "raw", ignore_errors=True)
