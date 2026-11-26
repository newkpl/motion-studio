"""Design tokens for MOTION STUDIO (technical cinema).

Single source of truth: colors, type scale, spacing, grid, easing.
Every module imports from here. No literal colors or sizes elsewhere.
All sizes are in OUTPUT pixels for the 1920x1080 master; the renderer
scales them by (canvas_height / 1080) so variants keep the same system.
"""

# ---------------------------------------------------------------- colors
BG        = (11, 13, 16)      # #0B0D10 dark base
BG_PANEL  = (18, 21, 26)      # panel lift, still inside the dark base family
BG_PANEL2 = (24, 28, 34)      # second panel lift
INK       = (242, 240, 234)   # #F2F0EA off-white text
ACCENT    = (255, 77, 46)     # #FF4D2E the one accent
GRAY      = (138, 143, 152)   # #8A8F98 muted gray
GRAY_DIM  = (84, 89, 97)      # darker gray for grid lines and inactive cells
INK_DIM   = (196, 198, 200)   # off-white at reduced strength (still > 4.5:1 on BG)

# Demo palette: monochrome ramp + accent only. Index 0 = BG, last = INK.
RAMP = [
    (11, 13, 16), (26, 30, 36), (43, 48, 56), (64, 70, 79),
    (92, 99, 109), (124, 131, 141), (160, 165, 172), (200, 202, 204),
    (242, 240, 234),
]

# ---------------------------------------------------------------- type scale
# Minimum text size anywhere: 28 px at 1080p. Nothing below this is allowed.
TYPE = {
    "title":    190,   # hero repo titles, kinetic type (range 140-220)
    "title_sm": 150,   # hero title when the name is long
    "chapter":  132,   # chapter beat titles
    "lockup":   120,   # closing lockup
    "sub":      44,    # subtitles / one-line descriptions
    "code":     36,    # the one code line per scene
    "code_lg":  54,    # code-as-hero scenes
    "meta":     30,    # star counts, counters, labels
    "min":      28,    # absolute floor
}

FONTS = {
    "display": "SpaceGrotesk.ttf",
    "mono":    "JetBrainsMono.ttf",
}

# ---------------------------------------------------------------- spacing / grid
MARGIN   = 96        # safe margin on every side at 1080p master scale
COLS     = 12        # 12-column grid
GUTTER   = 24
BASELINE = 8         # spacing unit

def col_edges(width, margin=None, cols=COLS, gutter=GUTTER):
    """Return list of (x0, x1) for each column at the given canvas width."""
    if margin is None:
        margin = MARGIN * width // 1920
    inner = width - 2 * margin
    step = (inner + gutter) / cols
    edges = []
    for i in range(cols):
        x0 = margin + i * step
        edges.append((x0, x0 + step - gutter))
    return edges

# ---------------------------------------------------------------- motion
FPS = 30
BPM = 120
BEAT_F = 15          # frames per beat at 120 BPM / 30 fps

# Easing curves as pure functions of t in [0, 1]. Names mirror the
# vocabulary the demos themselves show (anime.js / web easing canon).
def _clamp01(t):
    return 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)

def ease_linear(t):
    return _clamp01(t)

def ease_out_expo(t):
    t = _clamp01(t)
    return 1.0 if t >= 1.0 else 1.0 - 2.0 ** (-10.0 * t)

def ease_in_expo(t):
    t = _clamp01(t)
    return 0.0 if t <= 0.0 else 2.0 ** (10.0 * t - 10.0)

def ease_in_out_cubic(t):
    t = _clamp01(t)
    return 4 * t ** 3 if t < 0.5 else 1.0 - (-2 * t + 2) ** 3 / 2.0

def ease_out_cubic(t):
    t = _clamp01(t)
    return 1.0 - (1.0 - t) ** 3

def ease_in_cubic(t):
    t = _clamp01(t)
    return t ** 3

def ease_out_back(t, s=1.70158):
    t = _clamp01(t)
    return 1.0 + (s + 1.0) * (t - 1.0) ** 3 + s * (t - 1.0) ** 2

def ease_in_out_quad(t):
    t = _clamp01(t)
    return 2 * t * t if t < 0.5 else 1.0 - (-2 * t + 2) ** 2 / 2.0

EASE = {
    "linear": ease_linear,
    "out_expo": ease_out_expo,
    "in_expo": ease_in_expo,
    "in_out_cubic": ease_in_out_cubic,
    "out_cubic": ease_out_cubic,
    "in_cubic": ease_in_cubic,
    "out_back": ease_out_back,
    "in_out_quad": ease_in_out_quad,
}
