"""Minimal Bodymovin/Lottie player.

Parses a real Lottie JSON (layers, keyframed transforms, bezier path
shapes, ellipses, trim paths with animated start/end/offset, strokes)
and returns polylines per frame. Only the feature subset used by
assets/heart-pulse.json is implemented, but values are genuinely read
from the JSON at render time: keyframes, easing tangents, trim ranges.
"""
import json
import math
import numpy as np


def _bezier_ease(x1, y1, x2, y2, u):
    """Cubic bezier easing: solve x(t) = u, return y(t)."""
    if u <= 0:
        return 0.0
    if u >= 1:
        return 1.0
    t = u
    for _ in range(24):
        mt = 1 - t
        x = 3 * mt * mt * t * x1 + 3 * mt * t * t * x2 + t ** 3
        dx = 3 * mt * mt * x1 + 6 * mt * t * (x2 - x1) + 3 * t * t * (1 - x2)
        if abs(dx) < 1e-9:
            break
        step = (x - u) / dx
        t -= step
        if abs(step) < 1e-7:
            break
    mt = 1 - t
    return 3 * mt * mt * t * y1 + 3 * mt * t * t * y2 + t ** 3


def eval_prop(prop, frame):
    """Evaluate a Lottie property (static or keyframed) at a frame."""
    if not isinstance(prop, dict):
        return prop
    if prop.get("a", 0) == 0:
        return prop["k"]
    kfs = prop["k"]
    if frame <= kfs[0]["t"]:
        return kfs[0]["s"]
    if frame >= kfs[-1]["t"]:
        return kfs[-1]["s"]
    for i in range(len(kfs) - 1):
        a, b = kfs[i], kfs[i + 1]
        if a["t"] <= frame < b["t"]:
            u = (frame - a["t"]) / max(1e-9, b["t"] - a["t"])
            o = a.get("o", {"x": [0.33], "y": [0.0]})
            ii = b.get("i", {"x": [0.67], "y": [1.0]})
            e = _bezier_ease(o["x"][0], o["y"][0], ii["x"][0], ii["y"][0], u)
            va, vb = a["s"], b.get("s", a["s"])
            if isinstance(va, (int, float)):
                return va + (vb - va) * e
            return [x + (y - x) * e for x, y in zip(va, vb)]
    return kfs[-1]["s"]


def _sample_path(v, i_tan, o_tan, closed, per_seg=28):
    """Sample a Lottie bezier path into an (N,2) polyline."""
    pts = []
    n = len(v)
    segs = n if closed else n - 1
    for k in range(segs):
        p0 = np.array(v[k], dtype=float)
        p3 = np.array(v[(k + 1) % n], dtype=float)
        p1 = p0 + np.array(o_tan[k], dtype=float)
        p2 = p3 + np.array(i_tan[(k + 1) % n], dtype=float)
        ts = np.linspace(0, 1, per_seg, endpoint=False)
        for t in ts:
            mt = 1 - t
            pts.append(mt ** 3 * p0 + 3 * mt * mt * t * p1 +
                       3 * mt * t * t * p2 + t ** 3 * p3)
    pts.append(np.array(v[0] if closed else v[-1], dtype=float))
    return np.array(pts)


def _sample_ellipse(size, per=160):
    rx, ry = size[0] / 2.0, size[1] / 2.0
    ts = np.linspace(0, 2 * math.pi, per, endpoint=False)
    pts = np.stack([rx * np.cos(ts), ry * np.sin(ts)], axis=1)
    return np.vstack([pts, pts[:1]])


def _trim(pts, start_pct, end_pct, offset_pct, closed):
    """Apply Lottie trim paths: keep the [start, end] arc-length window."""
    total_pts = pts
    seg = np.linalg.norm(np.diff(total_pts, axis=0), axis=1)
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    length = cum[-1]
    if length <= 0:
        return total_pts
    s = ((start_pct + offset_pct) % 100.0) / 100.0 * length
    e = ((end_pct + offset_pct) % 100.0) / 100.0 * length
    if end_pct - start_pct >= 99.99:
        return total_pts

    def window(a, b):
        if b - a <= 0:
            return None
        mask = (cum >= a) & (cum <= b)
        out = list(total_pts[mask])
        # interpolate exact endpoints
        def at(d):
            j = int(np.searchsorted(cum, d))
            j = max(1, min(j, len(cum) - 1))
            f = (d - cum[j - 1]) / max(1e-9, cum[j] - cum[j - 1])
            return total_pts[j - 1] + f * (total_pts[j] - total_pts[j - 1])
        return np.array([at(a)] + out + [at(b)])

    if e >= s:
        w = window(s, e)
        return w if w is not None else total_pts[:0]
    w1 = window(s, length)
    w2 = window(0.0, e)
    parts = [p for p in (w1, w2) if p is not None and len(p)]
    return parts if parts else [total_pts[:0]]


def _xform(pts, pos, scale, rot_deg):
    th = math.radians(rot_deg)
    c, s = math.cos(th), math.sin(th)
    R = np.array([[c, -s], [s, c]])
    return (pts * np.array(scale[:2]) / 100.0) @ R.T + np.array(pos[:2])


class LottiePlayer:
    def __init__(self, path):
        with open(path) as fh:
            self.doc = json.load(fh)
        self.w = self.doc["w"]
        self.h = self.doc["h"]
        self.op = self.doc["op"]

    def frame_polylines(self, frame):
        """Return list of (points (N,2) in doc coords, rgb, width)."""
        t = frame % self.op
        out = []
        for layer in self.doc["layers"]:
            if not (layer["ip"] <= t < layer["op"]):
                continue
            ks = layer["ks"]
            pos = eval_prop(ks["p"], t)
            scl = eval_prop(ks["s"], t)
            rot = eval_prop(ks["r"], t)
            for group in layer["shapes"]:
                if group["ty"] != "gr":
                    continue
                path_pts = None
                closed = True
                trim = None
                stroke = None
                for item in group["it"]:
                    if item["ty"] == "sh":
                        k = item["ks"]["k"]
                        path_pts = _sample_path(k["v"], k["i"], k["o"], k["c"])
                        closed = k["c"]
                    elif item["ty"] == "el":
                        size = eval_prop(item["s"], t)
                        ctr = eval_prop(item["p"], t)
                        path_pts = _sample_ellipse(size) + np.array(ctr)
                        closed = True
                    elif item["ty"] == "tm":
                        def _scalar(v):
                            return float(v[0]) if isinstance(v, list) else float(v)
                        trim = (_scalar(eval_prop(item["s"], t)),
                                _scalar(eval_prop(item["e"], t)),
                                _scalar(eval_prop(item["o"], t)))
                    elif item["ty"] == "st":
                        col = eval_prop(item["c"], t)
                        stroke = (tuple(int(round(c * 255)) for c in col[:3]),
                                  eval_prop(item["w"], t))
                if path_pts is None or stroke is None:
                    continue
                if trim is not None:
                    res = _trim(path_pts, trim[0], trim[1], trim[2], closed)
                    lines = res if isinstance(res, list) else [res]
                else:
                    lines = [path_pts]
                for ln in lines:
                    if len(ln) < 2:
                        continue
                    out.append((_xform(ln, pos, scl, rot), stroke[0], stroke[1]))
        return out
