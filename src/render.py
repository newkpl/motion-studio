"""Deterministic renderer. Frame number is the only clock.

Usage:
  python3 render.py --w 1920 --h 1080 --ss 1.5 --out video.mp4 \
      [--registry qc/registry.json] [--frames 0,45,90] [--pngdir dir]
Without --frames it streams raw frames into ffmpeg (libx264).
"""
import argparse
import json
import os
import subprocess
import sys
import time

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tokens as T
import engine as E
import timeline as TL
import scenes as S

LEAD_TYPES = ("wipe", "whip", "scale")

def eff_start(sid):
    st = TL.STARTS[sid]
    tr = dict((s, t) for s, _, t in TL.SEGMENTS)[sid]
    if tr in LEAD_TYPES:
        return st - TL.TRANS_HALF
    return st

SEG_AT = []
for sid, dur, _ in TL.SEGMENTS:
    SEG_AT += [sid] * dur

def render_frame(f, W, H, SS, ctx, record=False):
    sid = SEG_AT[f]
    start = TL.STARTS[sid]
    dur = dict((s, d) for s, d, _ in TL.SEGMENTS)[sid]
    # transition window?
    for cut_sid, _d, tr in TL.SEGMENTS[1:]:
        c = TL.STARTS[cut_sid]
        if tr and c - TL.TRANS_HALF <= f < c + TL.TRANS_HALF:
            # outgoing = previous segment
            idx = [s for s, _, _ in TL.SEGMENTS].index(cut_sid)
            out_sid = TL.SEGMENTS[idx - 1][0]
            out_dur = TL.SEGMENTS[idx - 1][1]
            cv_a = E.Canvas(W, H, SS, record=False)
            S.draw_segment(cv_a, out_sid, f - eff_start(out_sid), out_dur, ctx)
            cv_b = E.Canvas(W, H, SS, record=record)
            S.draw_segment(cv_b, cut_sid, max(0, f - eff_start(cut_sid)), _d, ctx)
            p = (f - (c - TL.TRANS_HALF)) / (2 * TL.TRANS_HALF)
            img = E.TRANSITIONS[tr](cv_a.img, cv_b.img, p)
            return img, (cv_b.registry if record else [])
    cv = E.Canvas(W, H, SS, record=record)
    S.draw_segment(cv, sid, f - eff_start(sid), dur, ctx)
    img = cv.img
    cam = S.CAMERA.get(sid)
    if cam:
        prog = min(1.0, max(0.0, (f - start) / max(1, dur - 1)))
        sc = cam[0] + (cam[1] - cam[0]) * prog
        dx = (cam[2] + (cam[3] - cam[2]) * prog) * SS
        img = E.apply_camera(img, scale=sc, dx=dx)
    return img, (cv.registry if record else [])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--w", type=int, default=1920)
    ap.add_argument("--h", type=int, default=1080)
    ap.add_argument("--ss", type=float, default=1.5)
    ap.add_argument("--out", default=None)
    ap.add_argument("--registry", default=None)
    ap.add_argument("--frames", default=None, help="comma list; render PNGs only")
    ap.add_argument("--pngdir", default=".")
    args = ap.parse_args()
    W, H, SS = args.w, args.h, args.ss
    ctx = S.build_ctx(W, H)
    if args.frames:
        os.makedirs(args.pngdir, exist_ok=True)
        for f in [int(x) for x in args.frames.split(",")]:
            img, _ = render_frame(f, W, H, SS, ctx, record=False)
            if SS != 1.0:
                img = img.resize((W, H), Image.LANCZOS)
            img.save(os.path.join(args.pngdir, "f%04d.png" % f))
            print("frame", f, "ok", flush=True)
        return
    assert args.out, "--out required for full render"
    registry = {}
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", "%dx%d" % (int(W * SS), int(H * SS)), "-r", "30", "-i", "-",
           "-vf", "scale=%d:%d:flags=lanczos" % (W, H),
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "17",
           "-preset", "medium", "-movflags", "+faststart", args.out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t0 = time.time()
    for f in range(TL.TOTAL):
        record = bool(args.registry)
        img, reg = render_frame(f, W, H, SS, ctx, record=record)
        if record:
            registry[f] = reg
        proc.stdin.write(img.tobytes())
        if f % 90 == 0:
            print("frame %d/%d  %.1fs elapsed" % (f, TL.TOTAL, time.time() - t0),
                  flush=True)
    proc.stdin.close()
    proc.wait()
    print("render done", TL.TOTAL, "frames in %.1fs" % (time.time() - t0), flush=True)
    if args.registry:
        with open(args.registry, "w") as fh:
            json.dump(registry, fh)
        print("registry written", args.registry, flush=True)

if __name__ == "__main__":
    main()
