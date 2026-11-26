"""Audio/video sync verification.

Extracts the audio from the final MP4, detects onsets (short-window
energy transients), and checks that every video cut has a kick
transient within plus/minus 1 frame, and that every Tone.js pluck
step sounds within plus/minus 1 frame of its visual step.
"""
import subprocess
import sys
import wave

import numpy as np

import timeline as TL

SR = 44100

def extract_wav(mp4, wav_path):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", mp4, "-ac", "1",
                    "-ar", str(SR), wav_path], check=True)
    with wave.open(wav_path) as w:
        data = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    return data.astype(np.float64) / 32768.0

def onsets(x, hop=128):
    win = 512
    n = (len(x) - win) // hop
    env = np.empty(n)
    for i in range(n):
        seg = x[i * hop:i * hop + win]
        env[i] = np.sqrt(np.mean(seg ** 2))
    flux = np.maximum(0, np.diff(env, prepend=env[0]))
    times = []
    thr = max(0.06, flux.max() * 0.18)
    i = 1
    while i < len(flux) - 1:
        if flux[i] > thr and flux[i] >= flux[i - 1] and flux[i] >= flux[i + 1]:
            times.append(i * hop / SR)
            i += int(0.09 * SR / hop)  # 90 ms refractory
        else:
            i += 1
    return times, flux.max()

def check(mp4, wav_path):
    x = extract_wav(mp4, wav_path)
    # pad 100 ms of silence so the frame-0 kick produces a measurable
    # flux peak; reported times are shifted back by the pad
    pad = int(0.1 * SR)
    times, peak = onsets(np.concatenate([np.zeros(pad), x]))
    times = [o - 0.1 for o in times]
    rows = []
    ok_all = True
    targets = [("frame 0", 0)] + [("cut -> %s" % sid, TL.STARTS[sid])
                                  for sid, _, _ in TL.SEGMENTS[1:]]
    targets.append(("lockup hit", TL.LOCKUP_HIT_F))
    for label, f in targets:
        t = f / 30.0
        if times:
            dt = min(abs(o - t) for o in times)
        else:
            dt = 99
        ok = dt <= (1.0 / 30.0)
        ok_all = ok_all and ok
        rows.append((label, f, t, dt * 1000.0, ok))
    t0 = TL.STARTS["tone"]
    for s in range(TL.TONE_STEPS):
        if not TL.TONE_PATTERN["pluck"][s]:
            continue
        f = t0 + s * TL.TONE_STEP_F
        t = f / 30.0
        dt = min(abs(o - t) for o in times)
        ok = dt <= (1.0 / 30.0)
        ok_all = ok_all and ok
        rows.append(("tone pluck step %d (%s)" % (s, TL.TONE_NOTES[s]), f, t,
                     dt * 1000.0, ok))
    return rows, ok_all, len(times)

if __name__ == "__main__":
    mp4 = sys.argv[1]
    wav = sys.argv[2] if len(sys.argv) > 2 else "qc/sync-audio.wav"
    rows, ok, n_on = check(mp4, wav)
    print("onsets detected: %d" % n_on)
    print("%-28s %6s %8s %9s  %s" % ("target", "frame", "t (s)", "err (ms)", "ok"))
    for label, f, t, err, good in rows:
        print("%-28s %6d %8.3f %9.1f  %s" % (label, f, t, err, "OK" if good else "MISS"))
    print("SYNC:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)
