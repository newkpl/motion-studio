"""All scenes. Each draw function is a pure function of the local frame
(the only clock). Layouts vary per scene: overlay, split, centered,
code-hero. Palette comes only from tokens: monochrome ramp + accent.
"""
import math
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import tokens as T
import engine as E
import timeline as TL
from lottie import LottiePlayer

# ------------------------------------------------------------------ shared
def M(cv):
    return cv.U(T.MARGIN)

def star_widget(cv, right_x, cy, label):
    """Accent star glyph (drawn, not a font glyph) + mono star count."""
    r = cv.U(15)
    cx = right_x - cv.text_width(label, "mono", "meta") - cv.U(26)
    pts = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        rad = r if i % 2 == 0 else r * 0.45
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    cv.poly(pts, fill=T.ACCENT)
    cv.text(right_x, cy, label, kind="mono", size="meta", color=T.INK, anchor="rm")

def header(cv, title, star, size="title", y=None, x=None):
    m = M(cv)
    yy = m if y is None else y
    xx = m if x is None else x
    # auto-fit: a long title shrinks to the available width instead of
    # running under the star widget or off the frame in narrow aspects
    px = cv.U(T.TYPE[size])
    avail = cv.w - xx - m - (cv.U(200) if star else 0)
    tw = cv.text_width(title, "display", px)
    if tw > avail:
        px = max(cv.U(84), px * avail / tw)
    cv.text(xx, yy, title, size=px, color=T.INK, anchor="la")
    if star:
        star_widget(cv, cv.w - m, yy + px * 0.32, star)

def footer(cv, code, idx_label):
    m = M(cv)
    y = cv.h - m - cv.U(10)
    idx_w = cv.text_width(idx_label, "mono", "meta")
    avail = cv.w - 2 * m - idx_w - cv.U(48)
    px = cv.U(T.TYPE["code"])
    if cv.text_width(code, "mono", px) > avail:
        px = max(cv.U(T.TYPE["min"]), px * avail / cv.text_width(code, "mono", px))
    if cv.text_width(code, "mono", px) > avail:
        # narrow canvas: split the code line in two at the break
        # nearest the middle so nothing is clipped or overlapped
        br = -1
        for cand in (" // ", ", ", "(", " {", " / ", " "):
            i = code.rfind(cand, 0, int(len(code) * 0.85))
            if i > len(code) * 0.2:
                br = i + (len(cand) if cand != " {" else 0)
                break
        if br <= 0:
            br = len(code) // 2
        cv.text(m, y - cv.U(46), code[:br].rstrip(), kind="mono", size=px,
                color=T.INK_DIM, anchor="ld")
        cv.text(m, y, code[br:].lstrip(), kind="mono", size=px,
                color=T.INK_DIM, anchor="ld")
    else:
        cv.text(m, y, code, kind="mono", size=px, color=T.INK_DIM, anchor="ld")
    cv.text(cv.w - m, y, idx_label, kind="mono", size="meta", color=T.GRAY, anchor="rd")

def scene_index(sid):
    order = ["anime", "spring", "pixi", "d3", "p5", "mocanvas", "lottie",
             "blender", "three", "remotion", "tone"]
    return "%02d / 11" % (order.index(sid) + 1)

def grid_lines(cv, alpha=255):
    """Faint 12-column grid + margin frame, drawn under demos."""
    m = M(cv)
    for (x0, _x1) in T.col_edges(cv.w, margin=int(m)):
        cv.line([(x0, m), (x0, cv.h - m)], fill=T.RAMP[1], width=1)
    cv.line([(m, m), (cv.w - m, m)], fill=T.RAMP[1], width=1)
    cv.line([(m, cv.h - m), (cv.w - m, cv.h - m)], fill=T.RAMP[1], width=1)

# ------------------------------------------------------------------ cold open
def draw_cold_open(cv, f, dur, ctx):
    cx, cy = cv.w / 2, cv.h / 2
    word1, word2 = "MOTION", "STUDIO"
    size = "title"
    px = cv.U(T.TYPE[size])
    # camera push 1.00 -> 1.07 handled by renderer camera spec; here: type.
    def draw_word(word, y_top, start_f, flash=True):
        widths = [cv.text_width(ch, "display", size) for ch in word]
        total = sum(widths) + cv.U(6) * (len(word) - 1)
        x = cx - total / 2
        cy_letter = y_top + px / 2
        for i, ch in enumerate(word):
            lf = f - (start_f + i * 4)
            ccx = x + widths[i] / 2
            x += widths[i] + cv.U(6)
            if lf < 0:
                continue
            p = min(1.0, lf / 10.0)
            s = 2.3 - 1.3 * T.ease_out_expo(p)   # scale-through settle
            if flash and lf < 3:
                hw = widths[i] * s / 2 + cv.U(10)
                hh = px * s / 2 + cv.U(12)
                cv.rect([ccx - hw, cy_letter - hh, ccx + hw, cy_letter + hh],
                        fill=T.ACCENT)
                cv.text(ccx, cy_letter, ch, size=size, color=T.BG, anchor="mm",
                        on=T.ACCENT)
            else:
                # draw the glyph directly at its scaled size, centered
                fnt = E.font("display", px * s * cv.ss)
                cv.d.text((cv.X(ccx), cv.X(cy_letter)), ch, font=fnt,
                          fill=T.INK, anchor="mm")
                if cv.record:
                    cv.registry.append({"text": ch, "size": round(px, 1),
                                        "color": "#F2F0EA", "on": None,
                                        "bbox": [ccx - widths[i] / 2, y_top,
                                                 ccx + widths[i] / 2, y_top + px]})
    y1 = cy - px - cv.U(30)
    draw_word(word1, y1, 2)
    draw_word(word2, cy + cv.U(6), 30)
    if f >= 62:
        p = min(1.0, (f - 62) / 16.0)
        wline = T.ease_out_expo(p) * cv.U(560)
        yline = cy + px + cv.U(44)
        cv.rect([cx - wline, yline, cx + wline, yline + cv.U(6)], fill=T.ACCENT)
    if f >= 74:
        cv.text(cx, cy + px + cv.U(78), "ELEVEN OPEN SOURCE LIBRARIES - ONE STUDIO",
                kind="mono", size="meta", color=T.GRAY, anchor="ma")

# ------------------------------------------------------------------ chapters
def draw_chapter(cv, f, dur, ctx, sid):
    num, name, repos = TL.CHAPTERS[sid]
    m = M(cv)
    cv.text(m, m + cv.U(60), "CHAPTER " + num, kind="mono", size="meta",
            color=T.ACCENT, anchor="la")
    # name slams in with a 3-frame accent flash behind the first letter block
    y = m + cv.U(150)
    cpx = cv.U(T.TYPE["chapter"])
    w = cv.text_width(name, "display", cpx)
    if w > cv.w - 2 * m:
        cpx = cpx * (cv.w - 2 * m) / w
        w = cv.text_width(name, "display", cpx)
    if f < 3:
        cv.rect([m - cv.U(12), y - cv.U(10), m + w + cv.U(12),
                 y + cpx + cv.U(16)], fill=T.ACCENT)
        cv.text(m, y, name, size=cpx, color=T.BG, anchor="la", on=T.ACCENT)
    else:
        cv.text(m, y, name, size=cpx, color=T.INK, anchor="la")
    yy = y + cpx + cv.U(90)
    for i, r in enumerate(repos):
        if f >= 4 + i * 3:
            cv.text(m, yy + i * cv.U(52), r.upper(), kind="mono", size="meta",
                    color=T.INK_DIM, anchor="la")
    # all-chapter progress: right side in landscape; in narrow aspects
    # the fitted title spans the full width, so the list moves to the
    # empty bottom-right zone above the hairline
    names = ["MOTION", "DATA", "2D / 3D", "VIDEO / SOUND"]
    cur = int(num) - 1
    if cv.w < 1400:
        ly = cv.h - m - cv.U(228)
    else:
        ly = m + cv.U(60)
    for i, nm in enumerate(names):
        col = T.ACCENT if i == cur else T.GRAY
        cv.text(cv.w - m, ly + i * cv.U(52), "0%d %s" % (i + 1, nm),
                kind="mono", size="meta", color=col, anchor="ra")
    # continuous hairline sweep so the beat never holds a static frame
    hy = cv.h - m
    cv.line([(m, hy), (cv.w - m, hy)], fill=T.RAMP[2], width=3)
    cv.line([(m, hy), (m + (cv.w - 2 * m) * (f / max(1, dur - 1)), hy)],
            fill=T.ACCENT, width=3)

# ------------------------------------------------------------------ anime.js
def _shape_points(kind, n=72, r=1.0):
    th = np.linspace(0, 2 * math.pi, n, endpoint=False)
    if kind == "circle":
        return np.stack([np.cos(th), np.sin(th)], axis=1) * r
    if kind == "square":
        # walk the perimeter of a square with n points
        per = np.linspace(0, 4, n, endpoint=False)
        side = np.floor(per).astype(int)
        frac = per - side
        pts = np.zeros((n, 2))
        for k in range(n):
            s, u = side[k], frac[k]
            if s == 0: pts[k] = (-r + 2 * r * u, -r)
            elif s == 1: pts[k] = (r, -r + 2 * r * u)
            elif s == 2: pts[k] = (r - 2 * r * u, r)
            else: pts[k] = (-r, r - 2 * r * u)
        return pts
    if kind == "star":
        # true 5-point star polygon, perimeter-walked with n points
        verts = []
        for k in range(10):
            ang = -math.pi / 2 + k * math.pi / 5
            rad = r if k % 2 == 0 else r * 0.45
            verts.append((rad * math.cos(ang), rad * math.sin(ang)))
        verts = np.array(verts)
        pts = []
        per = []
        for k in range(10):
            a = verts[k]
            b = verts[(k + 1) % 10]
            per.append(np.linalg.norm(b - a))
        per = np.array(per)
        total = per.sum()
        for k in range(n):
            d = total * k / n
            seg = int(np.searchsorted(np.cumsum(per), d))
            seg = min(seg, 9)
            d0 = np.cumsum(per)[seg] - per[seg]
            u = (d - d0) / per[seg]
            pts.append(verts[seg] * (1 - u) + verts[(seg + 1) % 10] * u)
        return np.array(pts)
    raise ValueError(kind)

def draw_anime(cv, f, dur, ctx):
    # staggered grid, full bleed background; cell pitch stays
    # near-square in every aspect
    if cv.h > cv.w:
        cols, rows = 10, 18
    elif cv.w == cv.h:
        cols, rows = 12, 12
    else:
        cols, rows = 14, 7
    cw, chh = cv.w / cols, cv.h / rows
    period = 96
    for i in range(cols):
        for j in range(rows):
            delay = (i + j) * 3
            ph = (f - delay) % period
            if ph < 0:
                ph += period
            p = min(1.0, ph / 34.0)
            s = 0.15 + 0.85 * T.ease_out_expo(p)
            accent = ((i * 7 + j * 13) % 29 == 0)
            col = T.ACCENT if accent else T.RAMP[1 + ((i + j) % 3)]
            if ph > 80:
                s *= max(0.15, 1.0 - (ph - 80) / 16.0)
            ccx, ccy = (i + 0.5) * cw, (j + 0.5) * chh
            half = min(cw, chh) * 0.30 * s
            cv.rect([ccx - half, ccy - half, ccx + half, ccy + half], fill=col)
    # morph path hero, right of center, with a gray parallax echo
    shapes = [_shape_points("circle"), _shape_points("star"),
              _shape_points("square"), _shape_points("circle")]
    seg = min(2, int(f / 36))
    lt = (f - seg * 36) / 36.0
    e = T.ease_in_out_cubic(min(1.0, lt))
    pts = shapes[seg] * (1 - e) + shapes[seg + 1] * e
    cx0, cy0, R = cv.w * 0.66, cv.h * 0.56, cv.U(215)
    for scale, col, wdt, par in ((1.07, T.RAMP[3], 3, 0.94), (1.0, T.ACCENT, 6, 1.0)):
        pp = pts * (R * scale) + np.array([cx0 * par + cv.w * 0.66 * (1 - par), cy0])
        cv.line([tuple(p) for p in pp] + [tuple(pp[0])], fill=col, width=wdt)
    header(cv, "anime.js", TL.STARS["anime"])
    footer(cv, 'anime({ targets: ".dot", delay: stagger(60) })', scene_index("anime"))

# ------------------------------------------------------------------ react-spring
def draw_spring(cv, f, dur, ctx):
    series = ctx["spring_series"]  # two launches inside 105 frames
    val = float(series[min(f, len(series) - 1)])
    m = M(cv)
    header(cv, "react-spring", TL.STARS["spring"], size="title_sm")
    # stage
    x0, x1 = m, cv.w - m
    ytop, ybot = cv.U(400), cv.h - cv.U(240)
    # target line: marching dashes keep the settled tail alive
    ty = ybot - (ybot - ytop) * 1.0
    off = (f * 2) % 46
    for xx in range(int(x0) - 46 + off, int(x1), 46):
        cv.line([(max(xx, int(x0)), ty), (min(xx + 24, int(x1)), ty)],
                fill=T.GRAY, width=2)
    cv.text(x1, ty - cv.U(46), "TARGET", kind="mono", size="min", color=T.GRAY, anchor="ra")
    # axis
    cv.line([(x0, ybot), (x1, ybot)], fill=T.RAMP[3], width=2)
    # curve drawn live up to current frame; the relaunch at frame 55
    # breaks the polyline instead of drawing a vertical reset cliff
    upto = min(f, 104)
    runs = [(0, min(upto, 54)), (55, upto)] if upto >= 55 else [(0, upto)]
    for a, b in runs:
        pts = []
        for i in range(a, b + 1):
            v = float(series[i])
            px = x0 + (x1 - x0) * (i / 104.0)
            py = ybot - (ybot - ytop) * v
            pts.append((px, py))
        if len(pts) > 1:
            cv.line(pts, fill=T.ACCENT, width=5)
    # travelling block on the curve + readout kept inside the margins
    bx = x0 + (x1 - x0) * (min(f, 104) / 104.0)
    by = ybot - (ybot - ytop) * val
    half = cv.U(26)
    cv.rect([bx - half, by - half, bx + half, by + half], fill=T.INK)
    label = "x = %.3f" % val
    tw = cv.text_width(label, "mono", "meta")
    rx = min(max(bx, m + tw / 2 + cv.U(4)), cv.w - m - tw / 2 - cv.U(4))
    if by < cv.U(560):
        ry = by + half + cv.U(18)   # block rides high: readout goes below
    else:
        ry = by - half - cv.U(56)
    cv.text(rx, ry, label, kind="mono", size="meta", color=T.INK, anchor="ma")
    footer(cv, "useSpring({ mass: 1, tension: 170, friction: 13 })", scene_index("spring"))

# ------------------------------------------------------------------ PixiJS
def draw_pixi(cv, f, dur, ctx):
    P = ctx["pixi"]
    pos = P["pos_at"](f)
    # background starfield layer (parallax 0.4)
    bg = P["bg"]
    pan = (f / dur - 0.5) * cv.U(60)
    cv.d.point([(cv.X(x + pan * 0.4), cv.X(y)) for x, y in bg], fill=T.RAMP[4])
    # main particles by color group
    for mask, col, sz in ((P["accent_mask"], T.ACCENT, 3), (~P["accent_mask"], T.INK_DIM, 3)):
        pp = pos[mask]
        xy = [(cv.X(x + pan), cv.X(y)) for x, y in pp]
        if sz <= 2:
            cv.d.point(xy, fill=col)
        else:
            for (xx, yy) in xy:
                cv.d.rectangle([xx, yy, xx + cv.ss * 2, yy + cv.ss * 2], fill=col)
    header(cv, "PixiJS", TL.STARS["pixi"])
    footer(cv, "stage.addChild(particles) // 6000 points, one draw call",
           scene_index("pixi"))

# ------------------------------------------------------------------ D3
D3_DATA = np.array([42, 78, 55, 96, 63, 88, 34, 71], dtype=float)

def _treemap_rects(values, x0, y0, x1, y1):
    """Two-row treemap: split the dataset into two value-balanced rows,
    slice each row horizontally. Areas stay proportional to value."""
    total = values.sum()
    acc, split = 0.0, len(values)
    for i, v in enumerate(values):
        acc += v
        if acc >= total / 2:
            split = i + 1
            break
    rects = [None] * len(values)
    rows = [(0, split, y0, y0 + (y1 - y0) * (values[:split].sum() / total)),
            (split, len(values), y0 + (y1 - y0) * (values[:split].sum() / total), y1)]
    for a, b, ry0, ry1 in rows:
        cx = x0
        seg = values[a:b]
        for k in range(a, b):
            last = k == b - 1
            w = (x1 - cx) if last else (x1 - cx) * (values[k] / seg[k - a:].sum())
            rects[k] = (cx, ry0, cx + w, ry1)
            cx += w
    return rects

def draw_d3(cv, f, dur, ctx):
    m = M(cv)
    header(cv, "D3", TL.STARS["d3"])
    x0, x1 = m, cv.w - m
    ytop, ybot = cv.U(360), cv.h - cv.U(220)
    n = len(D3_DATA)
    vmax = D3_DATA.max()
    slot = (x1 - x0) / n
    tree = _treemap_rects(D3_DATA, x0, ytop, x1, ybot)
    # phases: bars 0-44, morph line 44-64, line 64-74, morph tree 74-96, tree 96+
    for i, v in enumerate(D3_DATA):
        bx0 = x0 + i * slot + slot * 0.18
        bx1 = x0 + (i + 1) * slot - slot * 0.18
        bh = (ybot - ytop) * (v / vmax)
        grow = T.ease_out_expo(min(1.0, max(0.0, (f - i * 3)) / 30.0))
        bar_top = ybot - bh * grow
        cx = (bx0 + bx1) / 2
        col = T.ACCENT if i == 3 else T.RAMP[5]
        if f < 44:
            cv.rect([bx0, bar_top, bx1, ybot], fill=col)
            if grow > 0.6:
                cv.text(cx, bar_top - cv.U(44), str(int(v)), kind="mono", size="meta",
                        color=T.INK, anchor="ma")
        elif f < 74:
            p = T.ease_in_out_cubic(min(1.0, (f - 44) / 20.0)) if f < 64 else 1.0
            w = (bx1 - bx0) * (1 - p) + 8 * p
            cv.rect([cx - w / 2, bar_top, cx + w / 2, ybot], fill=col)
            if p > 0.4:
                cv.ellipse([cx - 9, bar_top - 9, cx + 9, bar_top + 9], fill=T.INK)
        else:
            p = T.ease_in_out_cubic(min(1.0, (f - 74) / 22.0)) if f < 96 else 1.0
            tx0, ty0, tx1, ty1 = tree[i]
            rx0 = cx - 4 + (tx0 - (cx - 4)) * p
            ry0 = bar_top - 4 + (ty0 - (bar_top - 4)) * p
            rx1 = cx + 4 + (tx1 - (cx + 4)) * p
            ry1 = bar_top + 4 + (ty1 - (bar_top + 4)) * p
            tcol = T.ACCENT if i == 3 else T.RAMP[4]
            cv.rect([rx0, ry0, rx1, ry1], fill=tcol)
            if i == 3 and p >= 1.0:
                # pulse on the hero rect keeps the held treemap alive
                pr = cv.U(7 + 3 * math.sin(f * 0.4))
                ccx, ccy = (rx0 + rx1) / 2, ry1 - cv.U(34)
                cv.ellipse([ccx - pr, ccy - pr, ccx + pr, ccy + pr], fill=T.BG)
            if p > 0.75:
                cv.text((rx0 + rx1) / 2, (ry0 + ry1) / 2, str(int(v)), kind="mono",
                        size="meta", color=T.BG if tcol == T.ACCENT else T.INK,
                        anchor="mm", on=tcol)
    if 50 <= f < 96:
        # the line itself during line phase
        p = min(1.0, (f - 50) / 14.0)
        fade_end = 1.0 if f < 74 else max(0.0, 1.0 - (f - 74) / 12.0)
        if fade_end > 0:
            pts = []
            for i, v in enumerate(D3_DATA):
                cx = x0 + (i + 0.5) * slot
                bh = (ybot - ytop) * (v / vmax)
                pts.append((cx, ybot - bh))
            upto = max(2, int(len(pts) * p))
            cv.line(pts[:upto], fill=T.INK, width=4)
            if f >= 64:
                # data cursor travelling the line during the hold
                u = ((f - 64) % 20) / 19.0 * (len(pts) - 1)
                i0 = int(u)
                i1 = min(len(pts) - 1, i0 + 1)
                fr = u - i0
                dx = pts[i0][0] + (pts[i1][0] - pts[i0][0]) * fr
                dy = pts[i0][1] + (pts[i1][1] - pts[i0][1]) * fr
                cv.ellipse([dx - 10, dy - 10, dx + 10, dy + 10], fill=T.ACCENT)
    cv.line([(x0, ybot), (x1, ybot)], fill=T.RAMP[3], width=2)
    footer(cv, "bars.transition().attr(\"height\", d => y(d.value))", scene_index("d3"))

# ------------------------------------------------------------------ p5.js
class FlowField:
    """Stateful accumulation canvas, advanced strictly in frame order.
    Deterministic: fixed seed, fixed step sequence."""

    def __init__(self, w, h, seed=11):
        self.w, self.h = w, h
        self.noise = E.ValueNoise(seed=seed)
        self.img = Image.new("RGB", (w, h), T.BG)
        rng = np.random.default_rng(seed)
        self.n = 2400
        self.pos = rng.random((self.n, 2)) * np.array([w, h], dtype=float)
        self.age = rng.integers(0, 240, self.n)
        self.accent = rng.random(self.n) < 0.12
        self.frame = -1
        gx, gy = 64, 36
        xs = np.linspace(0, 6.4, gx)
        ys = np.linspace(0, 3.6, gy)
        self.X, self.Y = np.meshgrid(xs, ys)
        self.gx, self.gy = gx, gy

    def _angles(self, f):
        t = f * 0.006
        return self.noise.fbm(self.X + t, self.Y - t * 0.7, 3) * math.pi * 4.0

    def step_to(self, f):
        while self.frame < f:
            self.frame += 1
            self._step(self.frame)
        return self.img

    def _step(self, f):
        arr = (np.asarray(self.img).astype(np.float32) * 0.90).astype(np.uint8)
        self.img = Image.fromarray(arr, "RGB")
        d = ImageDraw.Draw(self.img)
        ang = self._angles(f)
        # bilinear sample of the angle grid at particle positions
        gx = self.pos[:, 0] / self.w * (self.gx - 1)
        gy = self.pos[:, 1] / self.h * (self.gy - 1)
        ix = np.clip(np.floor(gx).astype(int), 0, self.gx - 2)
        iy = np.clip(np.floor(gy).astype(int), 0, self.gy - 2)
        fx = gx - ix
        fy = gy - iy
        a = (ang[iy, ix] * (1 - fx) * (1 - fy) + ang[iy, ix + 1] * fx * (1 - fy) +
             ang[iy + 1, ix] * (1 - fx) * fy + ang[iy + 1, ix + 1] * fx * fy)
        step = 7.0
        new = self.pos + np.stack([np.cos(a), np.sin(a)], axis=1) * step
        ink = (168, 171, 175)
        for k in range(self.n):
            col = T.ACCENT if self.accent[k] else ink
            d.line([tuple(self.pos[k]), tuple(new[k])], fill=col, width=2)
        self.pos = new
        self.age += 1
        dead = ((self.age > 260) | (self.pos[:, 0] < 0) | (self.pos[:, 0] > self.w) |
                (self.pos[:, 1] < 0) | (self.pos[:, 1] > self.h))
        if dead.any():
            rng = np.random.default_rng(1000 + f)
            self.pos[dead] = rng.random((int(dead.sum()), 2)) * np.array([self.w, self.h])
            self.age[dead] = 0

def draw_p5(cv, f, dur, ctx):
    img = ctx["flow"].step_to(f)
    cv.img.paste(img.resize((cv.sw, cv.sh), Image.BILINEAR), (0, 0))
    cv.d = ImageDraw.Draw(cv.img, "RGBA")
    header(cv, "p5.js", TL.STARS["p5"])
    footer(cv, "function draw() { /* your sketch, 60x per second */ }", scene_index("p5"))

# ------------------------------------------------------------------ Motion Canvas
def draw_mocanvas(cv, f, dur, ctx):
    m = M(cv)
    header(cv, "Motion Canvas", TL.STARS["mocanvas"], size="title_sm")
    x0, x1 = m, cv.w - m
    raw = min(1.0, f / (dur - 1))
    eased = T.ease_in_out_cubic(raw)
    # stage: easing curve + node (stage inset so the node never
    # carries its label across the safe margin)
    sx0, sx1 = x0 + cv.U(84), x1 - cv.U(84)
    sy0, sy1 = cv.U(330), cv.U(660)
    cv.line([(sx0, sy1), (sx1, sy1)], fill=T.RAMP[3], width=2)
    curve = [(sx0 + (sx1 - sx0) * t, sy1 - (sy1 - sy0) * T.ease_in_out_cubic(t))
             for t in np.linspace(0, 1, 60)]
    cv.line(curve, fill=T.RAMP[4], width=3)
    nx = sx0 + (sx1 - sx0) * eased
    ny = sy1 - (sy1 - sy0) * eased
    cv.rect([nx - cv.U(70), ny - cv.U(44), nx + cv.U(70), ny + cv.U(44)], fill=T.ACCENT)
    cv.text(nx, ny, "NODE", kind="mono", size="min", color=T.BG, anchor="mm", on=T.ACCENT)
    # timeline
    ty0, ty1 = cv.h - cv.U(300), cv.h - cv.U(190)
    blocks = [("SCENE A", 0.0, 0.40, T.RAMP[3]), ("SCENE B", 0.40, 0.75, T.RAMP[4]),
              ("SCENE C", 0.75, 1.0, T.RAMP[3])]
    for label, a, b, col in blocks:
        bx0 = x0 + (x1 - x0) * a + 3
        bx1 = x0 + (x1 - x0) * b - 3
        cv.rect([bx0, ty0, bx1, ty1], fill=col)
        cv.text(bx0 + cv.U(18), (ty0 + ty1) / 2, label, kind="mono", size="min",
                color=T.INK, anchor="lm")
    px = x0 + (x1 - x0) * raw
    cv.line([(px, ty0 - cv.U(26)), (px, ty1 + cv.U(26))], fill=T.ACCENT, width=5)
    cv.poly([(px - cv.U(11), ty0 - cv.U(48)), (px + cv.U(11), ty0 - cv.U(48)),
             (px, ty0 - cv.U(26))], fill=T.ACCENT)
    tc = "T 00:%04.1f" % (f / 30.0)
    cv.text(x1, ty0 - cv.U(58), tc, kind="mono", size="meta", color=T.GRAY, anchor="ra")
    footer(cv, "yield* node().position.x(320, 1.2)", scene_index("mocanvas"))

# ------------------------------------------------------------------ Lottie Web
def draw_lottie(cv, f, dur, ctx):
    m = M(cv)
    cv.text(cv.w / 2, m, "Lottie Web", size="title_sm", color=T.INK, anchor="ma")
    star_widget(cv, cv.w - m, m + cv.U(T.TYPE["title_sm"]) * 0.32, TL.STARS["lottie"])
    player = ctx["lottie"]
    scale = cv.U(800) / player.w
    ox = cv.w / 2 - player.w * scale / 2
    oy = cv.h * 0.54 - player.h * scale / 2
    for pts, col, lw in player.frame_polylines(f):
        pp = [(ox + x * scale, oy + y * scale) for x, y in pts]
        if len(pp) > 1:
            cv.line(pp, fill=col, width=max(2, int(lw * scale)))
    y = cv.h - m - cv.U(10)
    cv.text(cv.w / 2, y, 'lottie.loadAnimation({ path: "heart.json" })',
            kind="mono", size="code", color=T.INK_DIM, anchor="md")
    cv.text(cv.w - m, y, scene_index("lottie"), kind="mono", size="meta",
            color=T.GRAY, anchor="rd")

# ------------------------------------------------------------------ Blender (stand-in)
def draw_blender(cv, f, dur, ctx):
    m = M(cv)
    mesh = ctx["ico"]
    cv.text(m, m, "Blender", size="title_sm", color=T.INK, anchor="la")
    star_widget(cv, cv.w - m, m + cv.U(T.TYPE["title_sm"]) * 0.32, TL.STARS["blender"])
    # viewport: cols 5..12 in landscape; stacked full width in portrait
    if cv.h > cv.w:
        vx0, vx1 = m, cv.w - m
        vy0, vy1 = m + cv.U(310), cv.h - m - cv.U(120)
        scl = (vx1 - vx0) * 0.36
    else:
        edges = T.col_edges(cv.w, margin=int(m))
        vx0 = edges[5][0]
        vy0, vy1 = m + cv.U(150), cv.h - m - cv.U(120)
        vx1 = cv.w - m
        scl = cv.U(215)
    R = E.rot_matrix(0.7 + 0.15 * math.sin(f * 0.02), f * 0.03, 0.25)
    verts = mesh["verts"] @ R.T
    ccx, ccy = (vx0 + vx1) / 2, (vy0 + vy1) / 2
    proj = np.stack([ccx + verts[:, 0] * scl, ccy - verts[:, 1] * scl], axis=1)
    light = np.array([0.4, 0.75, 0.65])
    light = light / np.linalg.norm(light)
    # wireframe layer
    wire = Image.new("RGB", (cv.sw, cv.sh), T.BG_PANEL)
    wd = ImageDraw.Draw(wire)
    for a, b in mesh["edges"]:
        wd.line([tuple(proj[a] * cv.ss), tuple(proj[b] * cv.ss)],
                fill=T.INK_DIM, width=max(1, int(2 * cv.ss)))
    # shaded layer
    sh = Image.new("RGB", (cv.sw, cv.sh), T.BG_PANEL)
    sd = ImageDraw.Draw(sh)
    faces = []
    for tri in mesh["faces"]:
        n = np.cross(verts[tri[1]] - verts[tri[0]], verts[tri[2]] - verts[tri[0]])
        ln = np.linalg.norm(n)
        if ln < 1e-9:
            continue
        n = n / ln
        zavg = verts[np.array(tri)][:, 2].mean()
        faces.append((zavg, tri, n))
    faces.sort(key=lambda t: t[0])
    acc_dir = np.array([0.9, 0.2, 0.35])
    acc_dir = acc_dir / np.linalg.norm(acc_dir)
    for _z, tri, n in faces:
        col = E.shade(n, light, accent_dir=acc_dir)
        sd.polygon([tuple(proj[i] * cv.ss) for i in tri], fill=col)
    if f < 48:
        layer = wire
    elif f > 60:
        layer = sh
    else:
        layer = Image.blend(wire, sh, (f - 48) / 12.0)
    # paste only the viewport window so the title and star survive
    box = (int(cv.X(vx0)), int(cv.X(vy0)), int(cv.X(vx1)), int(cv.X(vy1)))
    cv.img.paste(layer.crop(box), box[:2])
    cv.d = ImageDraw.Draw(cv.img, "RGBA")
    cv.rect([vx0, vy0, vx1, vy1], outline=T.RAMP[3], width=2)
    cv.text(vx0 + cv.U(20), vy0 + cv.U(16), "VIEWPORT - SOFTWARE 3D", kind="mono",
            size="min", color=T.GRAY, anchor="la")
    footer(cv, "bpy.ops.render.render(animation=True)", scene_index("blender"))

# ------------------------------------------------------------------ three.js
def draw_three(cv, f, dur, ctx):
    knot = ctx["knot"]
    # ground grid on its own layer, focus pull in the first 30 frames
    grid = Image.new("RGB", (cv.sw, cv.sh), T.BG)
    gd = ImageDraw.Draw(grid)
    R = E.rot_matrix(0.9, f * 0.02, 0.0)
    cam_z = 47.0 - 7.0 * T.ease_out_cubic(min(1.0, f / 100.0))
    focal = min(cv.w, cv.h) * 1.0   # aspect-safe: knot size is stable
    ccx, ccy = cv.w / 2, cv.h * 0.56
    glines = []
    for g in np.linspace(-10, 10, 11):
        glines.append(np.array([[g, -7.5, -10], [g, -7.5, 10]]))
        glines.append(np.array([[-10, -7.5, g], [10, -7.5, g]]))
    for ln in glines:
        pr, _z = E.project(ln @ R.T, cam_z, focal, ccx, ccy)
        gd.line([tuple(pr[0] * cv.ss), tuple(pr[1] * cv.ss)], fill=T.RAMP[2],
                width=max(1, int(cv.ss)))
    blur = max(0.0, 7.0 - f * 0.25)
    if blur > 0.3:
        grid = grid.filter(ImageFilter.GaussianBlur(blur * cv.ss))
    cv.img.paste(grid, (0, 0))
    cv.d = ImageDraw.Draw(cv.img, "RGBA")
    # torus knot, flat shaded, accent key light
    verts = knot["verts"] @ R.T
    proj, _z = E.project(verts, cam_z, focal, ccx, ccy)
    faces = knot["faces"]
    v0 = verts[faces[:, 0]]
    v1 = verts[faces[:, 1]]
    v2 = verts[faces[:, 2]]
    normals = np.cross(v1 - v0, v2 - v0)
    nl = np.linalg.norm(normals, axis=1, keepdims=True)
    normals = normals / np.maximum(nl, 1e-9)
    centers = (v0 + v1 + v2) / 3.0
    cam_pos = np.array([0.0, 0.0, -cam_z])
    vis = np.einsum("ij,ij->i", normals, cam_pos - centers) > 0
    light = np.array([0.4, 0.7, -0.6])
    light = light / np.linalg.norm(light)
    acc_dir = np.array([0.9, 0.15, -0.42])
    acc_dir = acc_dir / np.linalg.norm(acc_dir)
    dots = normals @ light
    accs = normals @ acc_dir
    order = np.argsort(-centers[:, 2])
    d = cv.d
    for idx in order:
        if not vis[idx]:
            continue
        tri = faces[idx]
        if accs[idx] > 0.965:
            col = T.ACCENT
        else:
            ri = int(np.clip((dots[idx] * 0.5 + 0.5) * (len(T.RAMP) - 1), 0, len(T.RAMP) - 1))
            col = T.RAMP[ri]
        d.polygon([(cv.X(proj[tri[0]][0]), cv.X(proj[tri[0]][1])),
                   (cv.X(proj[tri[1]][0]), cv.X(proj[tri[1]][1])),
                   (cv.X(proj[tri[2]][0]), cv.X(proj[tri[2]][1]))], fill=col)
    header(cv, "three.js", TL.STARS["three"])
    footer(cv, "new THREE.TorusKnotGeometry(10, 3, 220, 36)", scene_index("three"))

# ------------------------------------------------------------------ Remotion
REMOTION_CODE = [
    "const frame = useCurrentFrame();",
    "const scale = spring({",
    "  frame, fps: 30,",
    "  config: { damping: 14 },",
    "});",
    "return <Title scale={scale} />;",
]

# the same snippet, wrapped for the narrow side-by-side square layout
REMOTION_CODE_NARROW = [
    "const frame =",
    "  useCurrentFrame();",
    "const scale = spring({",
    "  frame, fps: 30,",
    "  config:",
    "    { damping: 14 },",
    "});",
    "return <Title",
    "  scale={scale} />;",
]

def draw_remotion(cv, f, dur, ctx):
    m = M(cv)
    f = min(f, dur - 1)  # transition-out overlap must not overrun the counter
    header(cv, "Remotion Skills", TL.STARS["remotion"], size="title_sm")
    # layout: side-by-side in landscape, stacked in portrait,
    # side-by-side with wrapped code in square
    top = cv.U(330)
    if cv.w < 1400 and cv.h > cv.w:
        lx0, lx1 = m, cv.w - m
        bot = top + cv.U(500)
        rx0, rx1 = m, cv.w - m
        rtop, rbot = bot + cv.U(28), cv.h - cv.U(200)
        lines, csize, step = REMOTION_CODE, "code", cv.U(56)
    elif cv.w < 1400:
        lx0, lx1 = m, cv.w * 0.50
        rx0, rx1 = cv.w * 0.54, cv.w - m
        bot = cv.h - cv.U(200)
        rtop, rbot = top, bot
        lines, csize, step = REMOTION_CODE_NARROW, cv.U(30), cv.U(50)
    else:
        lx0, lx1 = m, cv.w * 0.47
        rx0, rx1 = cv.w * 0.53, cv.w - m
        bot = cv.h - cv.U(200)
        rtop, rbot = top, bot
        lines, csize, step = REMOTION_CODE, "code", cv.U(56)
    cv.rect([lx0, top, lx1, bot], fill=T.BG_PANEL, outline=T.RAMP[2], width=2)
    active = (f // 15) % len(lines)
    yy = top + cv.U(36)
    for i, line_txt in enumerate(lines):
        if i == active:
            cv.rect([lx0 + cv.U(14), yy - cv.U(6), lx0 + cv.U(20),
                     yy + cv.U(40)], fill=T.ACCENT)
        col = T.INK if i == active else T.INK_DIM
        cv.text(lx0 + cv.U(40), yy, line_txt, kind="mono", size=csize, color=col,
                anchor="la")
        yy += step
    cv.text(lx0 + cv.U(40), yy + cv.U(8), "frame = %03d" % f, kind="mono",
            size=csize, color=T.ACCENT, anchor="la")
    # rendered side
    cv.rect([rx0, rtop, rx1, rbot], fill=T.BG_PANEL, outline=T.RAMP[2], width=2)
    val = float(ctx["remotion_spring"][min(f, len(ctx["remotion_spring"]) - 1)])
    label = "SPRING IN"
    base_px = cv.U(88)
    # fit the spring title inside narrow render panels
    probe = E.font("display", base_px * cv.ss)
    tw_probe = ImageDraw.Draw(cv.img).textlength(label, font=probe) / cv.ss
    inner = (rx1 - rx0) - cv.U(40)
    if tw_probe > inner:
        base_px = max(cv.U(40), base_px * inner / tw_probe)
    lay = Image.new("RGB", (int(cv.X(rx1 - rx0 - 40)), int(cv.X(120))), T.BG_PANEL)
    ld = ImageDraw.Draw(lay)
    fnt = E.font("display", base_px * cv.ss)
    tw = ld.textlength(label, font=fnt)
    ld.text(((lay.width - tw) / 2, 20 * cv.ss), label, font=fnt, fill=T.INK)
    s = max(0.05, val)
    lay = lay.resize((max(2, int(lay.width * s)), max(2, int(lay.height * s))),
                     Image.BILINEAR)
    cv.img.paste(lay, (int(cv.X((rx0 + rx1) / 2) - lay.width / 2),
                       int(cv.X(rtop + cv.U(170)) - lay.height / 2)))
    cv.d = ImageDraw.Draw(cv.img, "RGBA")
    bar_y = rbot - cv.U(110)
    cv.rect([rx0 + cv.U(30), bar_y, rx1 - cv.U(30), bar_y + cv.U(10)], fill=T.RAMP[2])
    cv.rect([rx0 + cv.U(30), bar_y,
             rx0 + cv.U(30) + (rx1 - rx0 - cv.U(60)) * (f / dur), bar_y + cv.U(10)],
            fill=T.ACCENT)
    cv.text(rx0 + cv.U(30), rbot - cv.U(70), "FRAME %03d / %d" % (f, dur),
            kind="mono", size="meta", color=T.INK_DIM, anchor="la")
    footer(cv, "const frame = useCurrentFrame() // frame is the only clock",
           scene_index("remotion"))

# ------------------------------------------------------------------ Tone.js
def draw_tone(cv, f, dur, ctx):
    m = M(cv)
    header(cv, "Tone.js", TL.STARS["tone"])
    x0, x1 = m, cv.w - m - cv.U(150)   # room for row labels at right
    y0, y1 = cv.U(330), cv.h - cv.U(330)
    rows = ["kick", "hat", "pluck"]
    gap = cv.U(16)
    cw = (x1 - x0 - gap * 7) / 8
    chh = (y1 - y0 - gap * 2) / 3
    step = min(TL.TONE_STEPS - 1, f // TL.TONE_STEP_F)
    for r, row in enumerate(rows):
        for s in range(TL.TONE_STEPS):
            bx0 = x0 + s * (cw + gap)
            by0 = y0 + r * (chh + gap)
            on = TL.TONE_PATTERN[row][s] == 1
            cur = (s == step)
            if cur and on:
                col = T.ACCENT if row == "pluck" else (T.INK if row == "kick" else T.RAMP[6])
            elif cur:
                col = T.RAMP[2]
            elif on:
                col = T.RAMP[4] if row != "pluck" else T.RAMP[5]
            else:
                col = T.RAMP[1]
            cv.rect([bx0, by0, bx0 + cw, by0 + chh], fill=col)
        cv.text(cv.w - m, y0 + r * (chh + gap) + chh / 2, row.upper(), kind="mono",
                size="meta", color=T.GRAY, anchor="rm")
    for s in range(TL.TONE_STEPS):
        if TL.TONE_PATTERN["pluck"][s]:
            bx0 = x0 + s * (cw + gap)
            cv.text(bx0 + cw / 2, y1 + cv.U(26), TL.TONE_NOTES[s], kind="mono",
                    size="meta", color=T.GRAY, anchor="ma")
    # continuous step-progress hairline (also the scene's clock readout)
    py = y1 + cv.U(84)
    cv.line([(x0, py), (x1, py)], fill=T.RAMP[2], width=3)
    cv.line([(x0, py), (x0 + (x1 - x0) * (f / max(1, dur - 1)), py)],
            fill=T.ACCENT, width=3)
    footer(cv, "new Tone.Sequence((t, n) => synth.triggerAttackRelease(n), notes)",
           scene_index("tone"))

# ------------------------------------------------------------------ closing
CLOSING_NAMES = [
    ("anime.js", "75.0K"), ("react-spring", "29.3K"), ("PixiJS", "48.9K"),
    ("D3", "114.0K"), ("p5.js", "24.4K"), ("Motion Canvas", "20.2K"),
    ("Lottie Web", "32.6K"), ("Blender", "22.4K"), ("three.js", "119.2K"),
    ("Remotion Skills", "7.9K"), ("Tone.js", "14.9K"),
]

def draw_closing(cv, f, dur, ctx):
    m = M(cv)
    if cv.w >= 1400:
        cols = 3
    elif cv.w >= 820:
        cols = 2
    else:
        cols = 1
    rows = int(math.ceil(len(CLOSING_NAMES) / cols))
    gx0, gx1 = m, cv.w - m
    gy0, gy1 = cv.U(240), cv.h - cv.U(240)
    cw = (gx1 - gx0) / cols
    chh = (gy1 - gy0) / rows
    for i, (name, star) in enumerate(CLOSING_NAMES):
        c, r = i % cols, i // cols
        start = i * 4
        p = T.ease_out_expo(min(1.0, max(0.0, (f - start) / 18.0)))
        if p <= 0:
            continue
        dirn = -1 if i % 2 == 0 else 1
        off = dirn * (1 - p) * cv.U(320)
        ex = gx0 + c * cw + off
        ey = gy0 + r * chh
        cv.text(ex, ey, "%02d" % (i + 1), kind="mono", size="meta", color=T.ACCENT,
                anchor="la")
        cv.text(ex + cv.U(64), ey - cv.U(4), name, kind="mono", size="code",
                color=T.INK, anchor="la")
        cv.text(ex + cv.U(64), ey + cv.U(48), star, kind="mono", size="min",
                color=T.GRAY, anchor="la")
    if f >= 62:
        p = T.ease_out_cubic(min(1.0, (f - 62) / 20.0))
        # dim the assembled grid toward the base so the lockup owns the frame
        dim = Image.new("RGB", (cv.sw, cv.sh), T.BG)
        cv.img = Image.blend(cv.img, dim, 0.88 * p)
        cv.d = ImageDraw.Draw(cv.img, "RGBA")
        lw = cv.text_width("MOTION STUDIO", "display", "lockup")
        fit = min(1.0, (cv.w - 2 * m) / lw)
        lw = lw * fit
        cx, cy = cv.w / 2, cv.h / 2
        cv.rect([cx - lw / 2, cy - cv.U(118), cx + lw / 2, cy - cv.U(112)],
                fill=T.ACCENT)
        ms = 0.7 + 0.3 * p
        lay = Image.new("RGB", (int(cv.X(lw)), int(cv.X(150))), T.BG)
        ld = ImageDraw.Draw(lay)
        fnt = E.font("display", cv.U(T.TYPE["lockup"] * fit) * cv.ss)
        tw = ld.textlength("MOTION STUDIO", font=fnt)
        ld.text(((lay.width - tw) / 2, 6 * cv.ss), "MOTION STUDIO", font=fnt, fill=T.INK)
        lay = lay.resize((int(lay.width * ms), int(lay.height * ms)), Image.BILINEAR)
        cv.img.paste(lay, (int(cv.X(cx) - lay.width / 2), int(cv.X(cy - 95))))
        cv.d = ImageDraw.Draw(cv.img, "RGBA")
        if cv.record:
            cv.registry.append({"text": "MOTION STUDIO", "size": round(cv.U(T.TYPE["lockup"]), 1),
                                "color": "#F2F0EA", "on": None,
                                "bbox": [cx - lw / 2, cy - 95, cx + lw / 2, cy + 55]})
        cv.text(cx, cy + cv.U(78), "ELEVEN LIBRARIES - ONE STUDIO", kind="mono",
                size="meta", color=T.GRAY, anchor="ma")
        pulse = cv.U(9 + 3 * math.sin(f * 0.3))
        cv.ellipse([cx - pulse, cy + cv.U(120) - pulse, cx + pulse,
                    cy + cv.U(120) + pulse], fill=T.ACCENT)

# ------------------------------------------------------------------ context
def _icosahedron():
    t = (1 + math.sqrt(5)) / 2
    verts = []
    for a, b in [(-1, t), (1, t), (-1, -t), (1, -t)]:
        verts.append((a, b, 0))
    for a, b in [(-1, t), (1, t), (-1, -t), (1, -t)]:
        verts.append((0, a, b))
    for a, b in [(-1, t), (1, t), (-1, -t), (1, -t)]:
        verts.append((b, 0, a))
    verts = np.array(verts, dtype=float)
    verts = verts / np.linalg.norm(verts[0])
    # faces by convex hull via brute force planes
    faces = []
    n = len(verts)
    for i in range(n):
        for j in range(i + 1, n):
            for k in range(j + 1, n):
                nrm = np.cross(verts[j] - verts[i], verts[k] - verts[i])
                if np.linalg.norm(nrm) < 1e-9:
                    continue
                d = np.dot(nrm, verts[i])
                dots = verts @ nrm
                if np.all(dots <= d + 1e-6) or np.all(dots >= d - 1e-6):
                    faces.append((i, j, k))
    # subdivide once
    cache = {}
    def mid(a, b):
        key = (min(a, b), max(a, b))
        if key not in cache:
            m = (verts[a] + verts[b]) / 2
            m = m / np.linalg.norm(m)
            cache[key] = len(verts_list)
            verts_list.append(m)
        return cache[key]
    verts_list = list(verts)
    new_faces = []
    for a, b, c in faces:
        ab, bc, ca = mid(a, b), mid(b, c), mid(c, a)
        new_faces += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
    verts = np.array(verts_list)
    edges = set()
    for a, b, c in new_faces:
        for e in [(a, b), (b, c), (c, a)]:
            edges.add((min(e), max(e)))
    return {"verts": verts, "faces": new_faces, "edges": sorted(edges)}

def _torus_knot(tub=150, rad=20, p=2, q=3, R=10.0, r=2.6):
    verts = []
    for i in range(tub + 1):
        uu = i / tub * 2 * math.pi
        # centerline of a (p, q) torus knot
        phi = uu * p
        rr = R + 1.6 * math.cos(q * uu)
        cen = np.array([rr * math.cos(phi), 1.6 * math.sin(q * uu), rr * math.sin(phi)])
        # frame: tangent approx
        uu2 = uu + 0.01
        phi2 = uu2 * p
        rr2 = R + 1.6 * math.cos(q * uu2)
        cen2 = np.array([rr2 * math.cos(phi2), 1.6 * math.sin(q * uu2), rr2 * math.sin(phi2)])
        tang = cen2 - cen
        tang = tang / np.linalg.norm(tang)
        nrm = np.cross(tang, [0, 1, 0])
        if np.linalg.norm(nrm) < 1e-6:
            nrm = np.array([1.0, 0, 0])
        nrm = nrm / np.linalg.norm(nrm)
        binm = np.cross(tang, nrm)
        for j in range(rad + 1):
            v = j / rad * 2 * math.pi
            off = nrm * (r * math.cos(v)) + binm * (r * math.sin(v))
            verts.append(cen + off)
    verts = np.array(verts)
    faces = []
    W = rad + 1
    for i in range(tub):
        for j in range(rad):
            a = i * W + j
            b = (i + 1) * W + j
            c = (i + 1) * W + j + 1
            dd = i * W + j + 1
            faces.append((a, b, dd))
            faces.append((b, c, dd))
    return {"verts": verts, "faces": np.array(faces)}

def build_ctx(w, h):
    ctx = {}
    s1 = E.spring_series(120)
    combined = np.concatenate([s1[:55], s1[:50]])
    ctx["spring_series"] = combined
    ctx["remotion_spring"] = E.spring_series(105, tension=120.0, friction=14.0)
    ctx["lottie"] = LottiePlayer(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "assets", "heart-pulse.json"))
    ctx["ico"] = _icosahedron()
    ctx["knot"] = _torus_knot()
    ctx["flow"] = FlowField(w, h)
    # PixiJS particle system
    rng = np.random.default_rng(42)
    n = 6000
    cxp, cyp = w / 2, h * 0.54
    unit = min(w, h)
    ring_n = 4200
    th = rng.random(ring_n) * 2 * math.pi
    rr = unit * 0.30 + rng.normal(0, unit * 0.008, ring_n)
    ring = np.stack([cxp + rr * np.cos(th), cyp + rr * np.sin(th)], axis=1)
    disc_n = n - ring_n
    th2 = rng.random(disc_n) * 2 * math.pi
    rr2 = unit * 0.105 * np.sqrt(rng.random(disc_n))
    disc = np.stack([cxp + rr2 * np.cos(th2), cyp + rr2 * np.sin(th2)], axis=1)
    target1 = np.vstack([ring, disc])
    half = unit * 0.26
    per = rng.random(n)
    side = (per * 4).astype(int)
    frac = per * 4 - side
    sq = np.zeros((n, 2))
    sq[side == 0] = np.stack([cxp - half + 2 * half * frac[side == 0],
                             np.full((side == 0).sum(), cyp - half)], axis=1)
    sq[side == 1] = np.stack([np.full((side == 1).sum(), cxp + half),
                             cyp - half + 2 * half * frac[side == 1]], axis=1)
    sq[side == 2] = np.stack([cxp + half - 2 * half * frac[side == 2],
                             np.full((side == 2).sum(), cyp + half)], axis=1)
    sq[side == 3] = np.stack([np.full((side == 3).sum(), cxp - half),
                             cyp + half - 2 * half * frac[side == 3]], axis=1)
    scatter = rng.random((n, 2)) * np.array([w, h])
    delay = rng.random(n) * 12
    direction = target1 - np.array([cxp, cyp])
    dl = np.linalg.norm(direction, axis=1, keepdims=True)
    direction = direction / np.maximum(dl, 1e-6)
    direction = direction + rng.normal(0, 0.25, direction.shape)
    direction = direction / np.linalg.norm(direction, axis=1, keepdims=True)
    burst_d = unit * 0.20
    sq = sq + rng.normal(0, 6, sq.shape)   # particle grain on the square form

    def rot(pts, ang):
        c, s = math.cos(ang), math.sin(ang)
        R = np.array([[c, -s], [s, c]])
        return (pts - [cxp, cyp]) @ R.T + [cxp, cyp]

    def pos_at(f):
        if f < 38:
            u = np.clip((f - delay) / 26.0, 0, 1)
            e = 1 - (1 - u) ** 3
            return scatter + (target1 - scatter) * e[:, None]
        if f < 56:
            return rot(target1, (f - 38) * 0.012)
        base = rot(target1, 18 * 0.012)
        if f < 70:
            e = T.ease_in_expo((f - 56) / 14.0)
            return base + direction * (e * burst_d)
        start = base + direction * burst_d
        e = T.ease_in_out_cubic(min(1.0, (f - 70) / 32.0))
        return start + (sq - start) * e
    ctx["pixi"] = {
        "pos_at": pos_at,
        "accent_mask": rng.random(n) < 0.15,
        "bg": rng.random((700, 2)) * np.array([w, h]),
    }
    return ctx

SCENES = {
    "cold_open": draw_cold_open,
    "anime": draw_anime,
    "spring": draw_spring,
    "pixi": draw_pixi,
    "d3": draw_d3,
    "p5": draw_p5,
    "mocanvas": draw_mocanvas,
    "lottie": draw_lottie,
    "blender": draw_blender,
    "three": draw_three,
    "remotion": draw_remotion,
    "tone": draw_tone,
    "closing": draw_closing,
}

def draw_segment(cv, sid, f, dur, ctx):
    if sid.startswith("ch_"):
        draw_chapter(cv, f, dur, ctx, sid)
    else:
        SCENES[sid](cv, f, dur, ctx)

# camera specs per segment: (scale0, scale1, dx0, dx1) in output px
CAMERA = {
    "cold_open": (1.00, 1.07, 0, 0),
    "anime": (1.02, 1.06, 0, 0),
    "pixi": (1.03, 1.03, -30, 30),
    "p5": (1.05, 1.02, 0, 0),
    "three": (1.00, 1.04, 0, 0),
    "closing": (1.08, 1.00, 0, 0),
}
