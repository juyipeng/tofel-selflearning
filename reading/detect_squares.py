"""Detect the sentence-insertion '■' markers via image processing.

The ■ markers are SOLID TEAL SQUARES (RGB ~ (20,129,124), ~28-32 px), not black.
They appear only in sentence-insertion questions, inline in the article (left
column) plus a click-target square in the question (right column).

Detection: saturation > 25 (teal is saturated, gray text/background are not)
-> scipy connected components -> keep components that are solid (fill > 0.8),
square-ish (aspect ~1), and reasonably sized (>= 15 px).
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).parent
IMAGES = ROOT / 'images'


def detect_squares(img_path, min_size=15, fill_thresh=0.8):
    """Return a list of (x, y, w, h) for solid colored squares in the image."""
    im = Image.open(img_path).convert('RGB')
    arr = np.array(im).astype(int)
    # saturation = max-min channel; teal has high saturation, gray does not
    sat = arr.max(axis=2) - arr.min(axis=2)
    colored = sat > 25
    lbl, n = ndimage.label(colored)
    comps = ndimage.find_objects(lbl)
    squares = []
    for i, sl in enumerate(comps, 1):
        ys, xs = sl
        h = ys.stop - ys.start
        w = xs.stop - xs.start
        if h < min_size or w < min_size:
            continue
        area = int((lbl[sl] == i).sum())
        fill = area / (h * w)
        if fill > fill_thresh and 0.6 <= w / h <= 1.6:
            # dominant color
            sub = arr[sl][lbl[sl] == i]
            dom = tuple(np.median(sub, axis=0).astype(int))
            squares.append((int(xs.start), int(ys.start), int(w), int(h), fill, dom))
    return squares


def main():
    manifest = json.loads((IMAGES / 'manifest.json').read_text(encoding='utf-8'))
    hits = []
    for m in manifest:
        path = ROOT / m['image_file']
        sq = detect_squares(path)
        if sq:
            # ignore squares in the top header band (y < ~120) — those are UI
            body = [s for s in sq if s[1] > 120]
            if body:
                hits.append((m['image_file'], body))
                print(f'{m["image_file"]}: {len(body)} squares -> {[(s[0],s[1]) for s in body]}')
    print(f'\nTotal images with ■ markers: {len(hits)}')


if __name__ == '__main__':
    main()
