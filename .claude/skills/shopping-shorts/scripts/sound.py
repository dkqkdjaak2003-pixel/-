#!/usr/bin/env python3
"""Synthesize royalty-free SFX and a music bed for shorts (standard library only).

Usage:
  sound.py sfx <out_dir>                       # tick, hit, whoosh, suck, riser, ding .wav
  sound.py music <out.wav> <seconds> <drop_s> [--bpm 120]
      tense ticking pulse until drop_s, then a brighter four-on-the-floor groove.

Everything is generated from oscillators and noise, so there is no licensing issue.
"""
import math
import random
import struct
import sys
import wave

SR = 44100
random.seed(7)


def write(path, samples):
    peak = max(1e-9, max(abs(s) for s in samples))
    gain = 0.89 / peak if peak > 0.89 else 1.0
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, s * gain)) * 32767)) for s in samples))


def buf(sec):
    return [0.0] * int(sec * SR)


def add(dst, src, at, gain=1.0):
    i0 = int(at * SR)
    for i, s in enumerate(src):
        j = i0 + i
        if 0 <= j < len(dst):
            dst[j] += s * gain


def noise_lp(n, alpha):
    """One-pole low-passed white noise; alpha 0..1 (higher = brighter)."""
    y, out = 0.0, []
    for _ in range(n):
        y += alpha * (random.uniform(-1, 1) - y)
        out.append(y)
    return out


# ---------- one-shots ----------

def tick():
    """Hard wood-block 'ttak': bright click + short tone."""
    n = int(0.09 * SR)
    nz = noise_lp(n, 0.9)
    return [(0.9 * math.sin(2 * math.pi * 1900 * i / SR) + 0.6 * math.sin(2 * math.pi * 3100 * i / SR)
             + 0.8 * nz[i] * math.exp(-i / (0.004 * SR))) * math.exp(-i / (0.018 * SR)) for i in range(n)]


def hit():
    """Cinematic impact: pitch-dropping sub + noise crack."""
    n = int(0.9 * SR)
    nz = noise_lp(n, 0.5)
    out, ph = [], 0.0
    for i in range(n):
        t = i / SR
        f = 45 + 110 * math.exp(-t / 0.05)
        ph += 2 * math.pi * f / SR
        out.append(math.sin(ph) * math.exp(-t / 0.28) + 0.7 * nz[i] * math.exp(-t / 0.04))
    return out


def whoosh(sec=0.35):
    n = int(sec * SR)
    out, y = [], 0.0
    for i in range(n):
        t = i / n
        alpha = 0.05 + 0.5 * math.sin(math.pi * t)       # brightness sweeps up then down
        y += alpha * (random.uniform(-1, 1) - y)
        out.append(y * math.sin(math.pi * t) ** 1.5)
    return out


def suck(sec=0.8):
    """Air being pulled out: bright hiss that darkens and falls in pitch."""
    n = int(sec * SR)
    out, y, ph = [], 0.0, 0.0
    for i in range(n):
        t = i / n
        y += (0.7 * (1 - t) + 0.03) * (random.uniform(-1, 1) - y)
        ph += 2 * math.pi * (600 * (1 - t) ** 2 + 60) / SR
        env = min(1, t * 12) * (1 - t) ** 0.6
        out.append((0.8 * y + 0.25 * math.sin(ph)) * env)
    return out


def riser(sec=1.2):
    n = int(sec * SR)
    out, y, ph = [], 0.0, 0.0
    for i in range(n):
        t = i / n
        y += (0.05 + 0.6 * t) * (random.uniform(-1, 1) - y)
        ph += 2 * math.pi * (200 + 1400 * t * t) / SR
        out.append((0.6 * y + 0.35 * math.sin(ph)) * t ** 2)
    return out


def ding():
    n = int(1.2 * SR)
    return [sum(a * math.sin(2 * math.pi * f * i / SR) for f, a in ((1318.5, 0.6), (1975.5, 0.35), (2637, 0.15)))
            * math.exp(-i / (0.35 * SR)) for i in range(n)]


# ---------- music bed ----------

def kick():
    n = int(0.35 * SR)
    out, ph = [], 0.0
    for i in range(n):
        t = i / SR
        ph += 2 * math.pi * (50 + 120 * math.exp(-t / 0.03)) / SR
        out.append(math.sin(ph) * math.exp(-t / 0.12))
    return out


def hat(open_=False):
    n = int((0.12 if open_ else 0.04) * SR)
    nz = noise_lp(n, 0.95)
    hp, prev = [], 0.0
    for s in nz:                       # crude high-pass
        hp.append(s - prev)
        prev = s
    return [hp[i] * math.exp(-i / ((0.04 if open_ else 0.008) * SR)) for i in range(n)]


def clap():
    n = int(0.2 * SR)
    nz = noise_lp(n, 0.7)
    env = [sum(math.exp(-(i - k * 0.01 * SR) / (0.006 * SR)) if i >= k * 0.01 * SR else 0 for k in range(3))
           + 0.5 * math.exp(-i / (0.06 * SR)) for i in range(n)]
    return [nz[i] * env[i] for i in range(n)]


def pad(freqs, sec, bright=0.3):
    n = int(sec * SR)
    out = []
    for i in range(n):
        t = i / SR
        s = 0.0
        for f in freqs:
            for h, a in ((1, 1.0), (2, bright), (3, bright * 0.5)):
                s += a * math.sin(2 * math.pi * f * h * t + h)
        out.append(s / len(freqs) * min(1, t / 0.05) * min(1, (sec - t) / 0.05))
    return out


def music(sec, drop, bpm=120):
    out = buf(sec)
    beat = 60 / bpm
    k, h, ho, c = kick(), hat(), hat(True), clap()
    # tension: clock-like 16th ticks, sub pulse on each beat, dark A-minor drone rising
    t = 0.0
    while t < drop:
        add(out, h, t, 0.35)
        t += beat / 4
    t = 0.0
    while t < drop:
        add(out, pad([55.0], beat * 0.9, 0.1), t, 0.55)
        t += beat
    add(out, pad([110.0, 130.81, 164.81], drop, 0.25), 0.0, 0.18)
    # release: four-on-the-floor in C major, claps on 2 and 4, offbeat open hats
    n = 0
    t = drop
    while t < sec:
        add(out, k, t, 0.9)
        if n % 2 == 1:
            add(out, c, t, 0.45)
        add(out, ho, t + beat / 2, 0.25)
        add(out, h, t + beat / 4, 0.18)
        add(out, h, t + 3 * beat / 4, 0.18)
        t += beat
        n += 1
    bar = 4 * beat
    chords = [[130.81, 164.81, 196.0], [110.0, 130.81, 164.81], [87.31, 110.0, 130.81], [98.0, 123.47, 146.83]]
    t, i = drop, 0
    while t < sec:
        add(out, pad(chords[i % 4], min(bar, sec - t), 0.45), t, 0.22)
        add(out, pad([chords[i % 4][0] / 2], min(bar, sec - t), 0.2), t, 0.35)
        t += bar
        i += 1
    fade = int(0.6 * SR)
    for j in range(fade):
        out[-1 - j] *= j / fade
    return out


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    if sys.argv[1] == "sfx":
        d = sys.argv[2]
        for name, fn in (("tick", tick), ("hit", hit), ("whoosh", whoosh), ("suck", suck),
                         ("riser", riser), ("ding", ding)):
            write(f"{d}/{name}.wav", fn())
            print(f"{d}/{name}.wav")
    elif sys.argv[1] == "music":
        bpm = float(sys.argv[sys.argv.index("--bpm") + 1]) if "--bpm" in sys.argv else 120
        write(sys.argv[2], music(float(sys.argv[3]), float(sys.argv[4]), bpm))
        print(sys.argv[2])
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
