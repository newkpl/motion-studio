"""Offline score synthesis on the same beat grid as the video.

120 BPM, beat = 15 frames = 0.5 s. Kicks land on every cut, risers run
into each chapter beat, one hit lands on the closing lockup, and the
Tone.js scene plucks sound exactly when its steps light (same pattern
and step grid as timeline.TONE_PATTERN).
"""
import numpy as np

import timeline as TL

SR = 44100
FPS = 30.0

def f2s(frame):
    return int(round(frame / FPS * SR))

def kick(n):
    t = np.arange(n) / SR
    pitch = 42 + 90 * np.exp(-t * 55)
    phase = np.cumsum(pitch) / SR * 2 * np.pi
    env = np.exp(-t * 16)
    return np.sin(phase) * env * 0.95

def pulse(n):
    t = np.arange(n) / SR
    return np.sin(2 * np.pi * 55 * t) * np.exp(-t * 9) * 0.35

def hat(n):
    rng = np.random.default_rng(3)
    t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    hp = np.diff(np.concatenate([[0], noise]))
    return hp * np.exp(-t * 90) * 0.16

def pluck(freq, n):
    t = np.arange(n) / SR
    env = np.exp(-t * 7)
    return (np.sin(2 * np.pi * freq * t) * 0.6 +
            np.sin(2 * np.pi * freq * 2 * t) * 0.25 +
            np.sin(2 * np.pi * freq * 3 * t) * 0.1) * env * 0.5

def riser(n):
    t = np.arange(n) / SR
    u = t / max(1e-6, t[-1])
    freq = 180 * (2.2 ** u)
    phase = np.cumsum(freq) / SR * 2 * np.pi
    rng = np.random.default_rng(5)
    noise = rng.standard_normal(n)
    lp = np.cumsum(noise) / 60.0
    env = u ** 2
    return (np.sin(phase) * 0.22 + lp * 0.5) * env

def hit(n):
    t = np.arange(n) / SR
    out = kick(n) * 1.0
    for fq in (523.25, 659.25, 783.99):
        out = out + pluck(fq, n) * 0.5
    return out

def synth():
    total_f = TL.TOTAL
    total_s = f2s(total_f)
    mix = np.zeros(total_s + SR // 2)
    def add(sig, frame, gain=1.0):
        s = f2s(frame)
        e = min(len(mix), s + len(sig))
        mix[s:e] += sig[:e - s] * gain
    k = kick(int(0.30 * SR))
    pu = pulse(int(0.22 * SR))
    ha = hat(int(0.06 * SR))
    # kick on frame 0 and every cut
    add(k, 0)
    for c in TL.CUTS:
        add(k, c)
    # beat pulse through hero scenes (not during chapter beats)
    hero_ranges = []
    for sid, dur, _ in TL.SEGMENTS:
        if sid.startswith("ch_") or sid in ("cold_open", "closing"):
            continue
        hero_ranges.append((TL.STARTS[sid], TL.STARTS[sid] + dur))
    for a, b in hero_ranges:
        f = a
        while f < b:
            add(pu, f, 0.8)
            add(ha, f + 7, 0.7)   # offbeat tick, sample-exact at half beat
            f += 15
    # risers into each chapter: the chapter segment itself carries the rise
    for sid in TL.CHAPTERS:
        add(riser(int(0.95 * SR)), TL.STARTS[sid] + 1)
    # cold open build: extra pulses on beats
    f = 0
    while f < 120:
        add(pu, f, 0.7)
        f += 15
    # Tone.js scene: pattern sounds exactly when the steps light
    t0 = TL.STARTS["tone"]
    for s in range(TL.TONE_STEPS):
        fr = t0 + s * TL.TONE_STEP_F
        if TL.TONE_PATTERN["kick"][s]:
            add(k, fr, 0.9)
        if TL.TONE_PATTERN["hat"][s]:
            add(ha, fr, 1.0)
        if TL.TONE_PATTERN["pluck"][s]:
            add(pluck(TL.NOTE_FREQ[TL.TONE_NOTES[s]], int(0.45 * SR)), fr, 1.0)
    # closing: pulses + lockup hit
    f = TL.STARTS["closing"]
    while f < TL.TOTAL:
        add(pu, f, 0.7)
        f += 15
    add(hit(int(0.7 * SR)), TL.LOCKUP_HIT_F)
    # master: soft clip + normalize
    mix = np.tanh(mix * 0.9)
    peak = np.max(np.abs(mix))
    if peak > 0:
        mix = mix / peak * 0.89
    return mix[:total_s]

def write_wav(path):
    import wave
    mix = synth()
    data = (mix * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())
    return len(mix) / SR

if __name__ == "__main__":
    import sys
    print("wrote", sys.argv[1], write_wav(sys.argv[1]), "s")
