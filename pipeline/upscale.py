#!/usr/bin/env python3
"""Upscale small photos (review/selfie shots) with OpenCV super-resolution, then mild sharpen + save ≤1600px q72.

  python3 pipeline/upscale.py docs/<slug>/img/*.jpg            # in place, only images < 1000px on the long side
  python3 pipeline/upscale.py --model fsrcnn file.jpg          # fast model (EDSR is better, ~10x slower)

Models (download once, kept outside the repo; set SR_MODELS to the folder):
  EDSR_x4.pb   https://raw.githubusercontent.com/Saafke/EDSR_Tensorflow/master/models/EDSR_x4.pb
  FSRCNN_x4.pb https://raw.githubusercontent.com/Saafke/FSRCNN_Tensorflow/master/models/FSRCNN_x4.pb
Requires: pip install opencv-contrib-python-headless
"""
import argparse, os, sys, time
import cv2

MODELS = os.environ.get("SR_MODELS", "/tmp/sr-models")


def upscale(path, model="edsr", min_side=1000, max_out=1600):
    img = cv2.imread(path)
    if img is None: return print("skip (unreadable)", path)
    h, w = img.shape[:2]
    if max(h, w) >= min_side: return print(f"skip (already {w}x{h})", path)
    sr = cv2.dnn_superres.DnnSuperResImpl_create()
    sr.readModel(os.path.join(MODELS, f"{model.upper()}_x4.pb")); sr.setModel(model, 4)
    t = time.time(); out = sr.upsample(img)
    blur = cv2.GaussianBlur(out, (0, 0), 1.2)
    out = cv2.addWeighted(out, 1.25, blur, -0.25, 0)            # gentle unsharp mask
    oh, ow = out.shape[:2]; k = min(1.0, max_out / max(oh, ow))
    if k < 1: out = cv2.resize(out, (int(ow * k), int(oh * k)), interpolation=cv2.INTER_AREA)
    cv2.imwrite(path, out, [cv2.IMWRITE_JPEG_QUALITY, 74, cv2.IMWRITE_JPEG_PROGRESSIVE, 1])
    print(f"{w}x{h} -> {out.shape[1]}x{out.shape[0]} in {time.time() - t:.1f}s", path)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("files", nargs="+"); ap.add_argument("--model", default="edsr", choices=["edsr", "fsrcnn"])
    ap.add_argument("--min-side", type=int, default=1000); a = ap.parse_args()
    for f in a.files: upscale(f, a.model, a.min_side)
