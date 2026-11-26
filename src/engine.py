"""Rendering engine: SS canvas, registered text, physics, noise, 3D, transitions.

Everything is a pure function of the frame number. The only stateful
pieces are per-scene caches (flow field accumulation), keyed and reset
per scene instance, advanced strictly in frame order.
"""
import math
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

import tokens as T

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")
FONT_DIR = os.path.join(ASSETS, "fonts")

_font_cache = {}

def font(kind, px):
    px = max(8, int(round(px)))
    key = (kind, px)
    if key not in _font_cache:
        f = ImageFont.truetype(os.path.join(FONT_DIR, T.FONTS[kind]), px)
        # Both bundled fonts are variable; their default instance is a
        # light weight. Pin the design weights: display Bold, mono Medium.
        try:
            f.set_variation_by_axes([700 if kind == "display" else 500])
        except Exception:
            pass
        _font_cache[key] = f
    return _font_cache[key]


class Canvas:
    """A supersampled canvas. All API coordinates are OUTPUT pixels."""

    def __init__(self, w, h, ss=1.5, record=False):
        self.w, self.h = w, h
        self.ss = ss
        self.u = min(w, h) / 1080.0          # token scale unit
        self.sw, self.sh = int(w * ss), int(h * ss)
        self.img = Image.new("RGB", (self.sw, self.sh), T.BG)
        self.d = ImageDraw.Draw(self.img, "RGBA")
        self.record = record
        self.registry = []                    # text elements for this frame

    # -- scale helpers -------------------------------------------------
    def X(self, v): return v * self.ss
    def U(self, v): return v * self.u        # token units -> output px

    def new_layer(self):
        return Image.new("RGB", (self.sw, self.sh), T.BG)

    # -- primitives (output px coords) ---------------------------------
    def rect(self, box, fill=None, outline=None, width=1):
        b = [self.X(box[0]), self.X(box[1]), self.X(box[2]), self.X(box[3])]
        self.d.rectangle(b, fill=fill, outline=outline, width=max(1, int(self.X(width))))

    def line(self, pts, fill, width=2):
        p = [(self.X(x), self.X(y)) for x, y in pts]
        self.d.line(p, fill=fill, width=max(1, int(self.X(width))), joint="curve")

    def poly(self, pts, fill=None, outline=None, width=1):
        p = [(self.X(x), self.X(y)) for x, y in pts]
        self.d.polygon(p, fill=fill, outline=outline, width=max(1, int(self.X(width))))

    def ellipse(self, box, fill=None, outline=None, width=1):
        b = [self.X(box[0]), self.X(box[1]), self.X(box[2]), self.X(box[3])]
        self.d.ellipse(b, fill=fill, outline=outline, width=max(1, int(self.X(width))))

    def paste(self, img, x=0, y=0):
        self.img.paste(img, (int(self.X(x)), int(self.X(y))))
        self.d = ImageDraw.Draw(self.img, "RGBA")

    # -- text -----------------------------------------------------------
    def text_size(self, s, kind, px):
        f = font(kind, px * self.ss)
        return self.d.textbbox((0, 0), s, font=f)

    def text(self, x, y, s, kind="display", size="meta", color=T.INK,
             anchor="la", tracking=0.0, alpha=255, on=None):
        """Draw text; register (text, bbox, size, color, bg) for QC.
        `on` names the fill color the text sits on, when known.
        anchor: PIL-style two-letter anchor at SS scale."""
        px = T.TYPE[size] if isinstance(size, str) else size
        px_out = px * self.u
        f = font(kind, px_out * self.ss)
        col = color + (alpha,) if len(color) == 3 else color
        if tracking:
            self._tracked_text(x, y, s, f, col, anchor, tracking, px_out)
        else:
            self.d.text((self.X(x), self.X(y)), s, font=f, fill=col, anchor=anchor)
        if self.record:
            bb = self.d.textbbox((self.X(x), self.X(y)), s, font=f, anchor=anchor)
            self.registry.append({
                "text": s, "size": round(px_out, 1),
                "color": "#%02X%02X%02X" % color[:3],
                "on": ("#%02X%02X%02X" % on[:3]) if on else None,
                "bbox": [bb[0] / self.ss, bb[1] / self.ss, bb[2] / self.ss, bb[3] / self.ss],
            })
        return px_out

    def _tracked_text(self, x, y, s, f, col, anchor, tracking, px_out):
        widths = [self.d.textlength(ch, font=f) for ch in s]
        total = sum(widths) + tracking * self.ss * max(0, len(s) - 1)
        asc, desc = f.getmetrics()
        if anchor[0] == "m":
            cx = self.X(x) - total / 2
        elif anchor[0] == "r":
            cx = self.X(x) - total
        else:
            cx = self.X(x)
        if anchor[1] == "m":
            cy = self.X(y) - (asc + desc) / 2
        elif anchor[1] == "d":
            cy = self.X(y) - (asc + desc)
        else:
            cy = self.X(y)
        for ch, wch in zip(s, widths):
            self.d.text((cx, cy), ch, font=f, fill=col, anchor="la")
            cx += wch + tracking * self.ss

    def text_width(self, s, kind, size):
        px = T.TYPE[size] if isinstance(size, str) else size
        f = font(kind, px * self.u * self.ss)
        return self.d.textlength(s, font=f) / self.ss

    # -- finishing -------------------------------------------------------
    def finish(self):
        if self.ss != 1.0:
            return self.img.resize((self.w, self.h), Image.LANCZOS)
        return self.img


# ------------------------------------------------------------------ physics
def spring_series(n, mass=1.0, tension=170.0, friction=13.0, x0=0.0, target=1.0):
    """RK4 integration of a damped spring. Returns array of x per frame."""
    sub = 4
    dt = (1.0 / T.FPS) / sub
    x, v = x0, 0.0
    out = np.empty(n)
    def acc(xx, vv):
        return (-(tension / mass) * (xx - target) - (friction / mass) * vv)
    for i in range(n):
        out[i] = x
        for _ in range(sub):
            k1x, k1v = v, acc(x, v)
            k2x, k2v = v + k1v * dt / 2, acc(x + k1x * dt / 2, v + k1v * dt / 2)
            k3x, k3v = v + k2v * dt / 2, acc(x + k2x * dt / 2, v + k2v * dt / 2)
            k4x, k4v = v + k3v * dt, acc(x + k3x * dt, v + k3v * dt)
            x += dt / 6 * (k1x + 2 * k2x + 2 * k3x + k4x)
            v += dt / 6 * (k1v + 2 * k2v + 2 * k3v + k4v)
    return out


# ------------------------------------------------------------------ noise
class ValueNoise:
    """Seeded 2D value noise with fbm, vectorized over grids."""

    def __init__(self, seed=7, period=256):
        rng = np.random.default_rng(seed)
        self.perm = rng.permutation(period)
        self.vals = rng.random(period * period)
        self.period = period

    def _lattice(self, ix, iy):
        p = self.period
        return self.vals[(self.perm[iy % p] * p + self.perm[ix % p]) % (p * p)]

    def noise(self, xs, ys):
        ix = np.floor(xs).astype(np.int64)
        iy = np.floor(ys).astype(np.int64)
        fx = xs - ix
        fy = ys - iy
        sx = fx * fx * (3 - 2 * fx)
        sy = fy * fy * (3 - 2 * fy)
        a = self._lattice(ix, iy)
        b = self._lattice(ix + 1, iy)
        c = self._lattice(ix, iy + 1)
        d = self._lattice(ix + 1, iy + 1)
        return a + (b - a) * sx + (c - a) * sy + (a - b - c + d) * sx * sy

    def fbm(self, xs, ys, octaves=4):
        out = np.zeros_like(xs, dtype=np.float64)
        amp, freq, tot = 1.0, 1.0, 0.0
        for _ in range(octaves):
            out += amp * self.noise(xs * freq, ys * freq)
            tot += amp
            amp *= 0.5
            freq *= 2.0
        return out / tot


# ------------------------------------------------------------------ 3D
def rot_matrix(ax, ay, az):
    cx, sx = math.cos(ax), math.sin(ax)
    cy, sy = math.cos(ay), math.sin(ay)
    cz, sz = math.cos(az), math.sin(az)
    rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return rz @ ry @ rx


def project(pts, cam_z, focal, cx, cy):
    """Perspective project (N,3) points; camera looks down +Z at origin."""
    z = pts[:, 2] + cam_z
    s = focal / np.maximum(z, 1e-6)
    return np.stack([cx + pts[:, 0] * s, cy - pts[:, 1] * s], axis=1), z


def shade(normal, light_dir, ramp=T.RAMP, accent_dir=None):
    """Flat shade from a face normal: gray ramp, accent when facing accent_dir."""
    d = float(np.dot(normal, light_dir))
    if accent_dir is not None and float(np.dot(normal, accent_dir)) > 0.86:
        return T.ACCENT
    idx = int(np.clip((d * 0.5 + 0.5) * (len(ramp) - 1), 0, len(ramp) - 1))
    return ramp[idx]


# ------------------------------------------------------------------ camera
def apply_camera(img, scale=1.0, dx=0.0, dy=0.0):
    """Scale about center + translate, in output px. Returns new image."""
    if abs(scale - 1.0) < 1e-4 and abs(dx) < 0.5 and abs(dy) < 0.5:
        return img
    w, h = img.size
    nw, nh = int(w * scale), int(h * scale)
    big = img.resize((nw, nh), Image.BILINEAR)
    out = Image.new("RGB", (w, h), T.BG)
    out.paste(big, (int(-(nw - w) / 2 + dx), int(-(nh - h) / 2 + dy)))
    return out


def whip_blur(img, amount):
    """Cheap directional smear: horizontal squeeze-blend."""
    if amount <= 0:
        return img
    w, h = img.size
    squeezed = img.resize((max(2, int(w * (1 - 0.55 * amount))), h), Image.BILINEAR)
    smeared = squeezed.resize((w, h), Image.BILINEAR)
    return Image.blend(img, smeared, 0.65 * amount)


# ------------------------------------------------------------------ transitions
def trans_block_wipe(a, b, p):
    """Accent block sweeps in over A, cut under full cover, sweeps off B."""
    w, h = a.size
    out = b.copy() if p >= 0.5 else a.copy()
    d = ImageDraw.Draw(out)
    if p < 0.5:
        x1 = (p * 2) * (w + 2) - 1
        d.rectangle([-2, -2, x1, h + 2], fill=T.ACCENT)
    else:
        x0 = ((p - 0.5) * 2) * (w + 2) - 1
        d.rectangle([x0, -2, w + 2, h + 2], fill=T.ACCENT)
    return out


def trans_whip(a, b, p):
    """Whip pan: A exits left, B enters from right, motion blur peaks mid."""
    w, h = a.size
    e = T.ease_in_out_cubic(p)
    off = int(e * w)
    blur = math.sin(math.pi * p)
    out = Image.new("RGB", (w, h), T.BG)
    out.paste(a, (-off, 0))
    out.paste(b, (w - off, 0))
    if blur > 0.05:
        out = whip_blur(out, blur)
    return out


def trans_scale_through(a, b, p):
    """Outgoing scales up through the camera; incoming settles from 1.18."""
    if p < 0.5:
        s = 1.0 + 1.1 * T.ease_in_cubic(p * 2)
        return apply_camera(a, scale=s)
    s = 1.18 - 0.18 * T.ease_out_cubic((p - 0.5) * 2)
    return apply_camera(b, scale=s)


def trans_cut(a, b, p):
    return b if p >= 0.5 else a


TRANSITIONS = {
    "wipe": trans_block_wipe,
    "whip": trans_whip,
    "scale": trans_scale_through,
    "cut": trans_cut,
}
