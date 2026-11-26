"""Automated layout QC from the renderer's text registry.

Checks per sampled frame:
- min font size >= 28 px (at output scale)
- every text bbox inside the 96 px safe margin (scaled by unit u)
- no unintended pairwise text-bbox overlaps
- WCAG contrast of each text color vs its background >= 4.5
  (background = explicit `on` fill when registered, else the worst of
  the dark token backgrounds BG / BG_PANEL / BG_PANEL2)

Intentional exceptions (kinetic type, assembly flight, lockup):
- cold_open frames: letter scale-through overlaps allowed
- closing frames before the lockup lands: names in flight may cross
- closing frames after lockup start: lockup sits over the name grid
"""
import json
import sys

import timeline as TL

def lum(rgb):
    def ch(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)

def hx(s):
    return tuple(int(s[i:i + 2], 16) for i in (1, 3, 5))

def contrast(a, b):
    la, lb = lum(a), lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)

DARK_BGS = [(11, 13, 16), (18, 21, 26), (24, 28, 34)]

def seg_of(f):
    for sid, dur, _ in TL.SEGMENTS:
        if TL.STARTS[sid] <= f < TL.STARTS[sid] + dur:
            return sid
    return "?"

def overlap(a, b):
    x = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    y = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = x * y
    if inter <= 0:
        return 0.0
    smaller = min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1]))
    return inter / max(1.0, smaller)

def run(registry_path, W, H):
    with open(registry_path) as fh:
        reg = json.load(fh)
    u = min(W, H) / 1080.0
    m = 96 * u
    defects = []
    checked = 0
    for fstr, elems in sorted(reg.items(), key=lambda kv: int(kv[0])):
        f = int(fstr)
        sid = seg_of(f)
        for el in elems:
            checked += 1
            if el["size"] < 27.9:
                defects.append("f%d [%s] SIZE %.1f < 28: %r" % (f, sid, el["size"], el["text"]))
            col = hx(el["color"])
            if el.get("on"):
                ratio = contrast(col, hx(el["on"]))
            else:
                ratio = min(contrast(col, bg) for bg in DARK_BGS)
            if ratio < 4.5:
                defects.append("f%d [%s] CONTRAST %.2f < 4.5: %r color %s on %s"
                               % (f, sid, ratio, el["text"], el["color"], el.get("on")))
            bb = el["bbox"]
            # closing assembly: names intentionally fly in from off-frame
            # (including the 5 transition lead frames before the segment)
            in_closing_flight = (f >= TL.STARTS["closing"] - TL.TRANS_HALF
                                 and f < TL.LOCKUP_HIT_F)
            if not in_closing_flight:
                if bb[0] < m - 3 or bb[1] < m - 3 or bb[2] > W - m + 3 or bb[3] > H - m + 3:
                    defects.append("f%d [%s] MARGIN bbox %s outside %.0f: %r"
                                   % (f, sid, [round(v) for v in bb], m, el["text"]))
        # pairwise overlaps
        for i in range(len(elems)):
            for j in range(i + 1, len(elems)):
                ov = overlap(elems[i]["bbox"], elems[j]["bbox"])
                if ov > 0.04:
                    if sid == "cold_open":
                        continue
                    if sid == "closing":
                        continue
                    defects.append("f%d [%s] OVERLAP %.2f: %r x %r"
                                   % (f, sid, ov, elems[i]["text"], elems[j]["text"]))
    return checked, defects

if __name__ == "__main__":
    path = sys.argv[1]
    W = int(sys.argv[2]) if len(sys.argv) > 2 else 1920
    H = int(sys.argv[3]) if len(sys.argv) > 3 else 1080
    n, defects = run(path, W, H)
    print("checked %d text elements" % n)
    if defects:
        print("DEFECTS: %d" % len(defects))
        for d in defects[:60]:
            print(" -", d)
        sys.exit(1)
    print("layout QC: PASS")
