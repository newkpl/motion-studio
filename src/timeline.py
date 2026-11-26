"""Timeline: segments, cuts, transitions. All lengths are multiples of
the 15-frame beat (120 BPM at 30 fps), so every cut lands on a beat.
Audio and video both read this file: one source of truth for sync.
"""

# (id, duration_frames, transition_in)  transition applies across the cut
# into this segment (window straddles the boundary, switch at boundary).
SEGMENTS = [
    ("cold_open",   120, None),
    ("ch_motion",    30, "wipe"),
    ("anime",       105, "scale"),
    ("spring",      105, "whip"),
    ("pixi",        105, "wipe"),
    ("ch_data",      30, "whip"),
    ("d3",          120, "scale"),
    ("ch_2d3d",      30, "wipe"),
    ("p5",          105, "whip"),
    ("mocanvas",    105, "wipe"),
    ("lottie",      105, "scale"),
    ("blender",     105, "whip"),
    ("three",       105, "wipe"),
    ("ch_vidsnd",    30, "whip"),
    ("remotion",    105, "scale"),
    ("tone",        120, "cut"),
    ("closing",     120, "wipe"),
]

TRANS_HALF = 5  # transition window = [cut-5, cut+5), switch at the cut

def starts():
    out, acc = {}, 0
    for sid, dur, _ in SEGMENTS:
        out[sid] = acc
        acc += dur
    return out

STARTS = starts()
TOTAL = sum(d for _, d, _ in SEGMENTS)
CUTS = [STARTS[sid] for sid, _, _ in SEGMENTS[1:]]  # every segment boundary

CHAPTERS = {
    "ch_motion": ("01", "MOTION", ["anime.js", "react-spring", "PixiJS"]),
    "ch_data":   ("02", "DATA", ["D3"]),
    "ch_2d3d":   ("03", "2D / 3D", ["p5.js", "Motion Canvas", "Lottie Web", "Blender", "three.js"]),
    "ch_vidsnd": ("04", "VIDEO / SOUND", ["Remotion Skills", "Tone.js"]),
}

STARS = {
    "anime": "75.0K", "spring": "29.3K", "pixi": "48.9K", "p5": "24.4K",
    "d3": "114.0K", "mocanvas": "20.2K", "blender": "22.4K", "three": "119.2K",
    "remotion": "7.9K", "lottie": "32.6K", "tone": "14.9K",
}

# Tone.js scene: 8 steps of one beat each (15 frames). Rows: kick, hat, pluck.
TONE_STEPS = 8
TONE_STEP_F = 15
TONE_PATTERN = {
    "kick":  [1, 0, 0, 0, 1, 0, 0, 0],
    "hat":   [0, 0, 1, 0, 0, 0, 1, 0],
    "pluck": [1, 0, 1, 1, 0, 1, 1, 0],
}
TONE_NOTES = ["C4", "D4", "E4", "G4", "A4", "G4", "E4", "D4"]  # per step index
NOTE_FREQ = {"C4": 261.63, "D4": 293.66, "E4": 329.63, "G4": 392.00, "A4": 440.00}

# Closing lockup hit lands when the lockup settles (closing start + 60).
LOCKUP_HIT_F = STARTS["closing"] + 60
