#!/usr/bin/env python3
"""Synthesize royalty-free SFX and a music bed for shorts (standard library only).

Usage:
  sound.py sfx <out_dir>              # tick, click, pop, swoosh, boom, hit, whoosh, suck, riser, ding, logo .wav
  sound.py music <out.wav> <seconds> <drop_s> [--bpm 120] [--style tv|trap]
      tv:   tense ticking pulse until drop_s, then a brighter four-on-the-floor groove.
      trap: laid-back half-time beat (default 76 bpm) on a heavy 808 bass, plucked
            minor melody; drop_s brings in the full drums. Suits info-style reels
            where the narration leads.

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


def noise_lp(n, alpha, poles=1):
    """Low-passed white noise (cascade of one-pole filters); alpha 0..1, higher = brighter."""
    ys, out = [0.0] * poles, []
    for _ in range(n):
        v = random.uniform(-1, 1)
        for p in range(poles):
            ys[p] += alpha * (v - ys[p])
            v = ys[p]
        out.append(v)
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


def click():
    """Very short high snap (UI-style 'ttak')."""
    n = int(0.04 * SR)
    nz = noise_lp(n, 0.5, poles=3)
    return [(0.6 * nz[i] + 0.9 * math.sin(2 * math.pi * 3000 * i / SR)) * math.exp(-i / (0.006 * SR))
            for i in range(n)]


def pop():
    """Bubble 'ppok': sine that sweeps up fast, mid-high, short."""
    n = int(0.16 * SR)
    out, ph = [], 0.0
    for i in range(n):
        t = i / SR
        ph += 2 * math.pi * (900 + 2200 * (1 - math.exp(-t / 0.012))) / SR
        out.append(math.sin(ph) * math.exp(-t / 0.035) * min(1, t / 0.002))
    return out


def swoosh(sec=0.45):
    """Soft mid swoosh for caption changes."""
    n = int(sec * SR)
    out, ys = [], [0.0, 0.0, 0.0]
    for i in range(n):
        t = i / n
        a, v = 0.12 + 0.35 * math.sin(math.pi * t), random.uniform(-1, 1)
        for p in range(3):
            ys[p] += a * (v - ys[p])
            v = ys[p]
        out.append(v * math.sin(math.pi * t) ** 2)
    return out


def boom():
    """808 hit with a long tail for the reveal."""
    n = int(1.2 * SR)
    out, ph = [], 0.0
    for i in range(n):
        t = i / SR
        ph += 2 * math.pi * (48 + 90 * math.exp(-t / 0.04)) / SR
        out.append(math.tanh(2.2 * math.sin(ph)) * math.exp(-t / 0.45))
    return out


def ding():
    n = int(1.2 * SR)
    return [sum(a * math.sin(2 * math.pi * f * i / SR) for f, a in ((1318.5, 0.6), (1975.5, 0.35), (2637, 0.15)))
            * math.exp(-i / (0.35 * SR)) for i in range(n)]


def logo():
    """Sound logo: ttak-ttak-ppok, then a two-note rising chime (about 1.3 s)."""
    out = buf(1.3)
    add(out, click(), 0.0, 0.8)
    add(out, click(), 0.14, 0.8)
    add(out, pop(), 0.3, 1.0)
    for at, f in ((0.52, 1046.5), (0.7, 1568.0)):
        n = int(0.6 * SR)
        add(out, [(math.sin(2 * math.pi * f * i / SR) + 0.3 * math.sin(4 * math.pi * f * i / SR))
                  * math.exp(-i / (0.22 * SR)) for i in range(n)], at, 0.55)
    return out


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


def bass808(freq, sec):
    n = int(sec * SR)
    out, ph = [], 0.0
    for i in range(n):
        t = i / SR
        ph += 2 * math.pi * (freq * (1 + 0.6 * math.exp(-t / 0.03))) / SR
        out.append(math.tanh(1.8 * math.sin(ph)) * math.exp(-t / 0.9) * min(1, (sec - t) / 0.03))
    return out


def snare():
    n = int(0.25 * SR)
    nz = noise_lp(n, 0.6)
    return [(0.8 * nz[i] * math.exp(-i / (0.07 * SR)) + 0.5 * math.sin(2 * math.pi * 190 * i / SR)
             * math.exp(-i / (0.04 * SR))) for i in range(n)]


def pluck(freq, sec=0.5):
    n = int(sec * SR)
    return [sum(a * math.sin(2 * math.pi * freq * h * i / SR) * math.exp(-i * h / (0.25 * SR))
                for h, a in ((1, 1.0), (2, 0.6), (3, 0.45), (4, 0.3), (6, 0.2), (8, 0.12)))
            * math.exp(-i / (0.2 * SR)) * min(1, i / (0.003 * SR)) for i in range(n)]


def trap(sec, drop, bpm=76):
    out = buf(sec)
    beat = 60 / bpm
    bar = 4 * beat
    k, s_, h = kick(), snare(), hat()
    roots = [55.0, 43.65, 49.0, 41.2]            # A1  F1  G1  E1
    arp = [[220, 261.63, 329.63, 261.63], [174.61, 220, 261.63, 220],
           [196, 246.94, 293.66, 246.94], [164.81, 207.65, 246.94, 207.65]]
    t, b = 0.0, 0
    while t < sec:
        r = roots[b % 4]
        add(out, bass808(r, min(bar * 0.5, sec - t)), t, 0.3)
        add(out, bass808(r, min(bar * 0.45, max(0.01, sec - t - bar * 0.625))), t + bar * 0.625, 0.24)
        for j, f in enumerate(arp[b % 4] * 2):     # eighth-note plucked arpeggio
            add(out, pluck(f), t + j * beat / 2, 0.55)
        add(out, pad([arp[b % 4][0], arp[b % 4][1], arp[b % 4][2]], min(bar, sec - t), 0.4), t, 0.3)
        full = t >= drop - 1e-6
        for q in range(16):                        # 16th grid
            tq = t + q * beat / 4
            if tq >= sec:
                break
            if q in (0, 10) or (full and q == 7):
                add(out, k, tq, 0.8)
            if q in (8,) and (full or b % 2 == 1):
                add(out, s_, tq, 0.55)
            if full and (q % 2 == 0 or (b % 2 == 1 and q >= 12)):   # hats + roll at bar end
                add(out, h, tq, 0.45)
        t += bar
        b += 1
    fade = int(0.6 * SR)
    for j in range(min(fade, len(out))):
        out[-1 - j] *= j / fade
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
        for name, fn in (("tick", tick), ("click", click), ("pop", pop), ("swoosh", swoosh),
                         ("boom", boom), ("hit", hit), ("whoosh", whoosh), ("suck", suck),
                         ("riser", riser), ("ding", ding), ("logo", logo)):
            write(f"{d}/{name}.wav", fn())
            print(f"{d}/{name}.wav")
    elif sys.argv[1] == "music":
        style = sys.argv[sys.argv.index("--style") + 1] if "--style" in sys.argv else "tv"
        default_bpm = 76 if style == "trap" else 120
        bpm = float(sys.argv[sys.argv.index("--bpm") + 1]) if "--bpm" in sys.argv else default_bpm
        fn = trap if style == "trap" else music
        write(sys.argv[2], fn(float(sys.argv[3]), float(sys.argv[4]), bpm))
        print(sys.argv[2])
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
