"""
sfx.py — a sound-effects library synthesised from code (numpy + pedalboard). No downloaded samples; MIT project code.

    python <skill>/scripts/sfx.py --out public/<name>/sfx              # writes every effect (48 kHz stereo wav)
    python <skill>/scripts/sfx.py --out … --only whoosh_m hit_heavy     # just these
    python <skill>/scripts/sfx.py --list                                # names + one-line descriptions

Effects that repeat (hits, whooshes, pops, steps, keys) come in 3 variants: name_1, name_2, name_3 — alternate them so a
fight or a typing burst never sounds like a machine gun. mix.py picks a random variant when you ask for "hit_heavy".
All effects are peak-normalised to -1 dBFS; set their level in the mix (typical: whoosh -14 dB, hit -8 dB, UI -16 dB,
ambience -24 dB under voice).

Realism: these are clean, stylised, "animation" sounds — right for graphic/cartoon/paper/ink looks. For photo-real
foley, drop real recordings into the sfx folder under the same names; mix.py does not care where a file came from.
"""
import argparse
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SR = 48000
RNG = np.random.default_rng(7)


# ------------------------------------------------------------------------------------------------ DSP helpers
def T(d):
    return np.arange(int(d * SR)) / SR


def noise(n, color="white", rng=RNG):
    w = rng.standard_normal(n)
    if color == "white":
        return w
    f = np.fft.rfftfreq(n, 1 / SR)
    f[0] = f[1]
    spec = np.fft.rfft(w) / (np.sqrt(f) if color == "pink" else f)
    x = np.fft.irfft(spec, n)
    return x / (np.abs(x).max() + 1e-9)


def env(n, a=0.005, d=0.2, curve=4.0, hold=0.0):
    """attack (linear) → hold → exponential-ish decay over d seconds"""
    t = np.arange(n) / SR
    e = np.clip(t / max(a, 1e-4), 0, 1)
    tail = np.clip((t - a - hold) / max(d, 1e-4), 0, 1)
    return e * (1 - tail) ** curve


def bell_env(n, peak=0.5, sharp=2.0):
    x = np.linspace(0, 1, n)
    return np.where(x < peak, (x / peak) ** sharp, ((1 - x) / (1 - peak)) ** sharp)


def sweep(f0, f1, d, curve="exp"):
    t = T(d)
    k = t / d
    f = f0 * (f1 / f0) ** k if curve == "exp" else f0 + (f1 - f0) * k
    return np.sin(2 * np.pi * np.cumsum(f) / SR)


def biquad(kind, f, q):
    w = 2 * np.pi * np.clip(f, 20, SR * 0.45) / SR
    al = np.sin(w) / (2 * q)
    c = np.cos(w)
    if kind == "lp":
        b = [(1 - c) / 2, 1 - c, (1 - c) / 2]
    elif kind == "hp":
        b = [(1 + c) / 2, -(1 + c), (1 + c) / 2]
    else:  # band-pass, constant peak gain
        b = [al, 0, -al]
    a = [1 + al, -2 * c, 1 - al]
    return np.array(b) / a[0], np.array(a) / a[0]


def filt_sweep(x, kind, f_start, f_end, q=1.0, curve=None, block=256):
    """time-varying biquad: the cutoff glides from f_start to f_end (exp) or follows `curve` (array of Hz per block)"""
    from scipy.signal import lfilter

    n = len(x)
    nb = (n + block - 1) // block
    fs = curve if curve is not None else f_start * (f_end / f_start) ** (np.arange(nb) / max(1, nb - 1))
    y = np.zeros(n)
    zi = np.zeros(2)
    for i in range(nb):
        b, a = biquad(kind, fs[min(i, len(fs) - 1)], q)
        seg = x[i * block:(i + 1) * block]
        y[i * block:i * block + len(seg)], zi = lfilter(b, a, seg, zi=zi)
    return y


def filt(x, kind, f, q=0.707):
    from scipy.signal import lfilter

    b, a = biquad(kind, f, q)
    return lfilter(b, a, x)


def fx(x, reverb=0.0, room=0.5, damp=0.5, drive=0.0, lp=None, hp=None, width=1.0, delay=0.0):
    from pedalboard import Delay, Distortion, HighpassFilter, LowpassFilter, Pedalboard, Reverb

    st = np.stack([x, x]) if x.ndim == 1 else x
    chain = []
    if hp:
        chain.append(HighpassFilter(hp))
    if lp:
        chain.append(LowpassFilter(lp))
    if drive:
        chain.append(Distortion(drive_db=drive))
    if delay:
        chain.append(Delay(delay_seconds=delay, feedback=0.25, mix=0.2))
    if reverb:
        chain.append(Reverb(room_size=room, damping=damp, wet_level=reverb, dry_level=1.0, width=width))
    if chain:
        tail = np.zeros((2, int(SR * (1.5 * room + 0.3) if reverb else 0)))
        st = Pedalboard(chain)(np.concatenate([st, tail], 1).astype(np.float32), SR)
    return st


def add(*xs):
    """sum signals of different lengths (pads the shorter ones with silence)"""
    n = max(len(x) for x in xs)
    return sum(np.pad(x, (0, n - len(x))) for x in xs)


def pan(x, p):
    """equal-power pan, p in -1..1 (mono in → stereo out)"""
    a = (p + 1) * np.pi / 4
    return np.stack([x * np.cos(a), x * np.sin(a)])


def stereo_sweep(x, p0, p1):
    a = (np.linspace(p0, p1, len(x)) + 1) * np.pi / 4
    return np.stack([x * np.cos(a), x * np.sin(a)])


def done(st):
    st = np.asarray(st, dtype=np.float64)
    if st.ndim == 1:
        st = np.stack([st, st])
    # trim trailing silence, tiny fades, normalise to -1 dBFS
    mag = np.abs(st).max(0)
    nz = np.nonzero(mag > 1e-4)[0]
    if len(nz):
        st = st[:, :nz[-1] + 1]
    f = min(64, st.shape[1] // 4)
    st[:, :f] *= np.linspace(0, 1, f)
    st[:, -f:] *= np.linspace(1, 0, f)
    return (st / (np.abs(st).max() + 1e-9) * 10 ** (-1 / 20)).T.astype(np.float32)


# ------------------------------------------------------------------------------------------------ recipes
LIB = {}


def sfx(name, desc, variants=1):
    def reg(fn):
        LIB[name] = (fn, desc, variants)
        return fn

    return reg


# ---- motion
@sfx("whoosh_s", "short air whoosh (0.35 s): a quick move, a camera whip, a card flying in", 3)
def _(v):
    d = 0.3 + 0.05 * v
    n = int(d * SR)
    x = filt_sweep(noise(n, "pink"), "bp", 350 + 80 * v, 2600 + 300 * v, q=1.4) * bell_env(n, 0.55, 1.6)
    return stereo_sweep(x, -0.5 + 0.3 * v, 0.6 - 0.2 * v)


@sfx("whoosh_m", "medium whoosh (0.6 s): a character dash, a big swing, a transition", 3)
def _(v):
    d = 0.55 + 0.05 * v
    n = int(d * SR)
    x = filt_sweep(noise(n, "pink"), "bp", 220 + 50 * v, 1800 + 250 * v, q=1.2) * bell_env(n, 0.6, 1.8)
    x += 0.4 * filt_sweep(noise(n), "bp", 2500, 6000, q=2) * bell_env(n, 0.62, 3)
    return fx(stereo_sweep(x, -0.7, 0.7), reverb=0.15, room=0.3)


@sfx("whoosh_l", "long heavy whoosh (1.1 s): a scene transition, a giant object passing", 2)
def _(v):
    d = 1.05 + 0.1 * v
    n = int(d * SR)
    x = filt_sweep(noise(n, "brown"), "bp", 120, 1400 + 200 * v, q=0.9) * bell_env(n, 0.65, 1.5)
    x += 0.3 * filt_sweep(noise(n, "pink"), "bp", 800, 4000, q=1.5) * bell_env(n, 0.66, 2.5)
    return fx(stereo_sweep(x, -0.8, 0.8), reverb=0.25, room=0.5)


@sfx("swish", "sharp swish (0.18 s): a sword, a fast punch, a whip", 3)
def _(v):
    n = int((0.16 + 0.02 * v) * SR)
    x = filt_sweep(noise(n), "bp", 1200 + 300 * v, 7000, q=2.2) * bell_env(n, 0.45, 2.2)
    return pan(x, (v - 2) * 0.3)


@sfx("zip", "fast upward zip (0.25 s): something shoots up / zooms in")
def _(v):
    n = int(0.25 * SR)
    x = sweep(300, 2400, 0.25) * bell_env(n, 0.7, 1.5) * 0.5 + filt_sweep(noise(n), "bp", 800, 6000, q=3) * bell_env(n, 0.7, 2)
    return pan(x, 0)


# ---- impacts
def _thump(f0, f1, d, drive=0.0):
    t = T(d)
    body = sweep(f0, f1, d) * env(len(t), 0.002, d, 3)
    return body


@sfx("hit_light", "light hit (a tap, a slap, a small punch)", 3)
def _(v):
    n = int(0.25 * SR)
    x = _thump(180 + 20 * v, 70, 0.25) * 0.8 + filt(noise(n), "hp", 1800) * env(n, 0.001, 0.03, 4) * 0.8
    return fx(x, reverb=0.08, room=0.2)


@sfx("hit_med", "medium punch/kick connecting", 3)
def _(v):
    n = int(0.4 * SR)
    x = _thump(140 + 15 * v, 48, 0.4) + filt(noise(n), "bp", 2200 + 300 * v, 0.8) * env(n, 0.001, 0.06, 3) * 0.9
    return fx(x, drive=8, reverb=0.12, room=0.3)


@sfx("hit_heavy", "heavy hit with crunch and room (the big punch, a body slam)", 3)
def _(v):
    n = int(0.8 * SR)
    x = _thump(110 + 10 * v, 34, 0.8) * 1.2 + filt(noise(n, "pink"), "bp", 1500 + 200 * v, 0.6) * env(n, 0.001, 0.12, 2.5)
    x += filt(noise(n), "hp", 4000) * env(n, 0.0005, 0.02, 4) * 0.6
    return fx(x, drive=14, reverb=0.22, room=0.5, lp=9000)


@sfx("impact_boom", "cinematic boom: a title slam, a giant landing, the moment everything stops")
def _(v):
    n = int(2.4 * SR)
    x = _thump(70, 26, 2.4) * 1.3 + filt(noise(n, "brown"), "lp", 600) * env(n, 0.003, 1.2, 2) * 0.9
    x += filt(noise(n), "bp", 2500, 0.7) * env(n, 0.001, 0.08, 3) * 0.5
    return fx(x, drive=10, reverb=0.45, room=0.85, damp=0.6)


@sfx("slam", "door/body slam on wood: a sharp snap + boxy body")
def _(v):
    n = int(0.6 * SR)
    snap = filt(noise(int(0.012 * SR)), "hp", 2500) * np.linspace(1, 0, int(0.012 * SR)) ** 2 * 1.4
    body = filt(noise(n, "pink"), "bp", 1100, 1.4) * env(n, 0.0005, 0.12, 3) * 0.8
    x = add(snap, _thump(110, 55, 0.45) * 0.8, body)
    x = x - 0.5 * filt(x, "bp", 400, 1.5)  # scoop the boxy 400 Hz
    return fx(x, reverb=0.28, room=0.35, damp=0.7)


@sfx("clang", "metal clang (swords meeting, a pot, a gong-ish hit)", 2)
def _(v):
    t = T(1.6)
    f = 520 + 90 * v
    x = sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t * dcy) for r, a, dcy in [(1, 1, 3.5), (2.76, 0.6, 5), (5.4, 0.4, 8), (8.93, 0.25, 12), (13.3, 0.15, 18)])
    x = x + filt(noise(len(t)), "hp", 3000) * env(len(t), 0.0005, 0.03, 4) * 1.2
    return fx(x, reverb=0.3, room=0.5)


@sfx("sword_clash", "two blades clashing with a ring and a scrape", 2)
def _(v):
    t = T(1.3)
    f = 1150 + 150 * v
    ring = sum(a * np.sin(2 * np.pi * f * r * t + v) * np.exp(-t * dcy) for r, a, dcy in [(1, 1, 5), (1.51, 0.7, 6), (2.93, 0.4, 9), (4.2, 0.3, 14)])
    scrape = filt_sweep(noise(len(t)), "bp", 5000, 2500, q=4) * env(len(t), 0.001, 0.35, 2) * 0.6
    x = ring + scrape + filt(noise(len(t)), "hp", 2500) * env(len(t), 0.0005, 0.02, 4) * 1.5
    return fx(pan(x, 0.1 * (v - 1.5) * 2), reverb=0.3, room=0.55)


@sfx("wood_crack", "wood crack / branch snap: a few splintering resonant snaps")
def _(v):
    n = int(0.4 * SR)
    x = np.zeros(n)
    t = 0.0
    for k in range(6):
        i = int(t * SR)
        m = int(RNG.uniform(0.004, 0.012) * SR)
        burst = filt(RNG.standard_normal(m) * np.linspace(1, 0, m) ** 2, "bp", RNG.uniform(1400, 4200), 7) * RNG.uniform(0.6, 1.4)
        x[i:i + m] += burst
        t += RNG.uniform(0.004, 0.018)
    x = add(x * 3, _thump(240, 110, 0.1) * 0.5)
    return fx(x, reverb=0.18, room=0.3)


@sfx("splash", "water splash (something falls into a river): spray + hollow plonks + droplets")
def _(v):
    n = int(1.4 * SR)
    spray = filt_sweep(noise(n, "pink"), "bp", 2500, 900, q=0.8) * env(n, 0.004, 0.7, 2.5) * 0.6
    x = spray + _thump(120, 45, 1.4) * 0.35
    for k in range(5):  # the hollow 'plonk' of air pockets
        s0 = int(RNG.uniform(0.0, 0.12) * SR)
        m = int(0.07 * SR)
        f0 = RNG.uniform(250, 500)
        x[s0:s0 + m] += sweep(f0, f0 * 2.4, 0.07) * np.sin(np.linspace(0, np.pi, m)) * RNG.uniform(0.4, 0.8)
    for k in range(45):  # droplets falling back
        s0 = int(RNG.uniform(0.15, 1.2) * SR)
        f0 = RNG.uniform(900, 3000)
        m = int(0.03 * SR)
        x[s0:s0 + m] += sweep(f0, f0 * 1.9, 0.03) * np.exp(-np.arange(m) / (0.007 * SR)) * RNG.uniform(0.05, 0.3)
    return fx(x, reverb=0.2, room=0.4)


@sfx("thud_soft", "soft landing thud (feet on grass, a sack dropped)", 3)
def _(v):
    n = int(0.3 * SR)
    x = _thump(90 + 10 * v, 45, 0.3) + filt(noise(n, "brown"), "lp", 500) * env(n, 0.002, 0.1, 3) * 0.6
    return x


@sfx("footstep", "single footstep (soft ground)", 3)
def _(v):
    n = int(0.18 * SR)
    x = filt(noise(n, "pink"), "bp", 500 + 150 * v, 1.0) * env(n, 0.003, 0.08, 3) + _thump(110, 60, 0.18) * 0.3
    return pan(x, (v - 2) * 0.2)


# ---- cartoon
@sfx("pop", "bubbly pop: something appears, a sticker lands, an idea", 3)
def _(v):
    n = int(0.09 * SR)
    f0 = 380 + 120 * v
    x = sweep(f0, f0 * 2.6, 0.09) * env(n, 0.001, 0.08, 2) + np.pad(noise(40) * 0.5, (0, n - 40))
    return fx(x, reverb=0.1, room=0.2)


@sfx("bloop", "rounder bloop (softer pop, a UI bubble)", 2)
def _(v):
    n = int(0.16 * SR)
    x = sweep(220 + 60 * v, 520 + 60 * v, 0.16) * np.sin(np.linspace(0, np.pi, n)) ** 0.6
    return fx(x, reverb=0.12, room=0.2)


@sfx("boing", "cartoon spring boing (a bounce, a comedic jump)")
def _(v):
    t = T(0.7)
    f = 180 * (1 + 0.35 * np.sin(2 * np.pi * 16 * t) * np.exp(-t * 4))
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(len(t), 0.002, 0.7, 1.5)
    return fx(x, reverb=0.1)


@sfx("slide_up", "slide whistle up (something rises / a comic realisation)")
def _(v):
    t = T(0.6)
    f = 400 * (4 ** (t / 0.6)) * (1 + 0.01 * np.sin(2 * np.pi * 6 * t))
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * bell_env(len(t), 0.8, 0.8)
    return fx(x, reverb=0.15)


@sfx("slide_down", "slide whistle down (a fall, a fail)")
def _(v):
    t = T(0.7)
    f = 1600 * (0.25 ** (t / 0.7)) * (1 + 0.01 * np.sin(2 * np.pi * 6 * t))
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * bell_env(len(t), 0.2, 0.8)
    return fx(x, reverb=0.15)


@sfx("bonk", "hollow bonk (a head bump, a coconut)")
def _(v):
    t = T(0.35)
    x = (np.sin(2 * np.pi * 330 * t) + 0.5 * np.sin(2 * np.pi * 870 * t)) * np.exp(-t * 18) + np.pad(noise(60), (0, len(t) - 60)) * 0.3
    return fx(x, reverb=0.15, room=0.3)


@sfx("sparkle", "magic sparkle / twinkle (pentatonic glints with shimmer)")
def _(v):
    n = int(1.4 * SR)
    x = np.zeros(n)
    scale = [0, 2, 4, 7, 9, 12, 14, 16, 19, 21, 24]
    for k in range(14):
        s = int(k * 0.06 * SR + RNG.uniform(0, 0.02) * SR)
        f = 1046.5 * 2 ** (RNG.choice(scale) / 12)
        m = int(0.5 * SR)
        tt = np.arange(m) / SR
        g = (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * f * 2.01 * tt)) * np.exp(-tt * 9) * (1 - k / 16)
        x[s:s + m] += g[: len(x[s:s + m])]
    return fx(stereo_sweep(x, -0.6, 0.6), reverb=0.5, room=0.7, delay=0.12)


@sfx("twinkle", "single soft twinkle (an eye glint, a star)")
def _(v):
    t = T(0.8)
    x = (np.sin(2 * np.pi * 2093 * t) + 0.4 * np.sin(2 * np.pi * 3136 * t)) * np.exp(-t * 7)
    return fx(x, reverb=0.45, room=0.6)


# ---- paper / craft
@sfx("paper_rustle", "paper rustle (a sheet moves, a cut-out slides in): crinkly, jagged", 3)
def _(v):
    n = int(0.5 * SR)
    step = int(SR / 380)  # sample-and-hold amplitude: thousands of tiny crinkles
    sh = np.repeat(RNG.uniform(0, 1, n // step + 1) ** 3, step)[:n]
    x = filt(filt(noise(n), "hp", 1800), "lp", 10000) * sh
    for k in range(25):
        i = int(RNG.uniform(0, 0.45) * SR)
        m = int(0.002 * SR)
        x[i:i + m] += RNG.standard_normal(m) * RNG.uniform(0.5, 1.5)
    return pan(x * bell_env(n, 0.35, 0.8), (v - 2) * 0.3)


@sfx("paper_tear", "paper tear (a torn-paper transition)", 2)
def _(v):
    n = int(0.7 * SR)
    grains = np.zeros(n)
    t = 0.0
    while t < 0.62:
        s = int(t * SR)
        m = int(RNG.uniform(0.002, 0.008) * SR)
        grains[s:s + m] += RNG.standard_normal(m) * RNG.uniform(0.4, 1)
        t += RNG.uniform(0.002, 0.012)
    x = filt_sweep(grains, "bp", 1500, 4500 + 500 * v, q=0.9) * bell_env(n, 0.3, 0.7)
    return stereo_sweep(x, -0.5, 0.5)


@sfx("page_flip", "page flip / card flip")
def _(v):
    n = int(0.35 * SR)
    x = filt_sweep(noise(n, "pink"), "bp", 600, 3500, q=1) * bell_env(n, 0.35, 1.5) + filt(noise(n), "hp", 3000) * env(n, 0.25, 0.05, 3) * 0.3
    return stereo_sweep(x, 0.4, -0.4)


@sfx("stamp", "rubber stamp thump (a label slams on)")
def _(v):
    n = int(0.3 * SR)
    x = _thump(150, 70, 0.3) + filt(noise(n, "pink"), "bp", 900, 1) * env(n, 0.001, 0.05, 3) * 0.7
    return fx(x, reverb=0.12, room=0.25, damp=0.8)


@sfx("scissors", "scissors snip")
def _(v):
    n = int(0.25 * SR)
    x = np.zeros(n)
    for s in (0.0, 0.11):
        i = int(s * SR)
        m = int(0.06 * SR)
        x[i:i + m] += filt(noise(m), "bp", 5000, 2) * env(m, 0.001, 0.05, 3)
    return x


# ---- UI / tech
@sfx("click", "UI click", 3)
def _(v):
    n = int(0.03 * SR)
    return filt(noise(n), "bp", 3000 + 600 * v, 3) * env(n, 0.0003, 0.02, 5)


@sfx("tick", "clock tick / counter tick", 2)
def _(v):
    n = int(0.05 * SR)
    t = np.arange(n) / SR
    return np.sin(2 * np.pi * (2400 + 300 * v) * t) * np.exp(-t * 180)


@sfx("key", "typewriter/keyboard key", 3)
def _(v):
    n = int(0.08 * SR)
    x = filt(noise(n), "bp", 2500 + 500 * v, 1.5) * env(n, 0.0005, 0.03, 5) + _thump(300, 150, 0.08) * 0.3
    return pan(x, (v - 2) * 0.25)


@sfx("ding", "notification ding (bright two-partial bell)")
def _(v):
    t = T(1.2)
    x = sum(a * np.sin(2 * np.pi * 1318.5 * r * t) * np.exp(-t * d) for r, a, d in [(1, 1, 4), (2.0, 0.3, 6), (3.0, 0.15, 9)])
    return fx(x, reverb=0.25, room=0.4)


@sfx("success", "success chime (rising arpeggio)")
def _(v):
    n = int(1.2 * SR)
    x = np.zeros(n)
    for k, st in enumerate([0, 4, 7, 12]):
        s = int(k * 0.08 * SR)
        tt = np.arange(n - s) / SR
        x[s:] += np.sin(2 * np.pi * 784 * 2 ** (st / 12) * tt) * np.exp(-tt * 5)
    return fx(x, reverb=0.3, room=0.5)


@sfx("error", "error buzz (two low square blips)")
def _(v):
    n = int(0.45 * SR)
    t = np.arange(n) / SR
    sq = np.sign(np.sin(2 * np.pi * 150 * t))
    g = ((t < 0.16) | ((t > 0.22) & (t < 0.38))).astype(float)
    return filt(sq * g, "lp", 2500) * 0.6


@sfx("glitch", "digital glitch burst (bit-crushed stutters)", 2)
def _(v):
    from pedalboard import Bitcrush, Pedalboard

    n = int(0.45 * SR)
    x = np.zeros(n)
    s = 0
    while s < n:
        m = int(RNG.uniform(0.01, 0.05) * SR)
        f = RNG.uniform(200, 3000)
        seg = np.sign(np.sin(2 * np.pi * f * np.arange(m) / SR)) * RNG.uniform(0.3, 1) if RNG.random() < 0.5 else RNG.standard_normal(m) * 0.6
        x[s:s + m] += seg[: len(x[s:s + m])]
        s += m + int(RNG.uniform(0, 0.02) * SR)
    x = Pedalboard([Bitcrush(bit_depth=5)])(x[None].astype(np.float32), SR)[0]
    return pan(x, (v - 1.5) * 0.6)


@sfx("blip", "data blip (tiny sine chirp)", 3)
def _(v):
    n = int(0.06 * SR)
    return sweep(1800 + 300 * v, 2600 + 300 * v, 0.06) * env(n, 0.001, 0.05, 2)


@sfx("scan", "scanner sweep (a beam passes over)")
def _(v):
    t = T(0.9)
    f = 600 + 1800 * np.sin(np.pi * t / 0.9)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.4 * bell_env(len(t), 0.5, 1) + filt_sweep(noise(len(t)), "bp", 500, 5000, q=5) * bell_env(len(t), 0.5, 1) * 0.5
    return stereo_sweep(x, -0.8, 0.8)


# ---- tension / transitions
@sfx("riser_2s", "2-second riser (noise + rising tone): into a reveal/drop — place it to END on the hit")
def _(v):
    d = 2.0
    n = int(d * SR)
    x = filt_sweep(noise(n, "pink"), "bp", 300, 7000, q=1.5) * np.linspace(0, 1, n) ** 2.2
    x += sweep(110, 880, d) * np.linspace(0, 1, n) ** 2 * 0.35
    return fx(x, reverb=0.3, room=0.6)


@sfx("riser_4s", "4-second riser: a long build (place it to END on the hit)")
def _(v):
    d = 4.0
    n = int(d * SR)
    x = filt_sweep(noise(n, "pink"), "bp", 200, 8000, q=1.3) * np.linspace(0, 1, n) ** 2.5
    x += (sweep(55, 440, d) + 0.5 * sweep(82.5, 660, d)) * np.linspace(0, 1, n) ** 2 * 0.3
    return fx(x, reverb=0.3, room=0.6)


@sfx("downlifter", "downlifter (falling noise): energy drains, a scene settles")
def _(v):
    n = int(1.6 * SR)
    x = filt_sweep(noise(n, "pink"), "bp", 6000, 200, q=1.4) * np.linspace(1, 0, n) ** 1.6
    return fx(x, reverb=0.3, room=0.6)


@sfx("reverse_swell", "reverse cymbal swell (1.2 s): sucks into a cut — END it on the cut")
def _(v):
    n = int(1.2 * SR)
    x = filt(noise(n), "hp", 3000) * np.linspace(0, 1, n) ** 3
    return fx(x, reverb=0.2, room=0.5)


@sfx("braam", "cinematic braam (low brassy blast): an ominous reveal")
def _(v):
    t = T(2.5)
    f = 55
    saw = sum(np.sin(2 * np.pi * f * k * t * (1 + 0.003 * dt)) / k for k in range(1, 30) for dt in (-1, 1))
    x = filt_sweep(saw, "lp", 300, 1600, q=0.9, curve=None) * env(len(t), 0.08, 2.2, 1.6)
    return fx(x, drive=6, reverb=0.4, room=0.8)


@sfx("sub_drop", "sub drop (sine 80→30 Hz): weight under a hit or a cut")
def _(v):
    t = T(1.4)
    return phone_harmonics(sweep(80, 28, 1.4) * env(len(t), 0.002, 1.4, 1.5), 0.4)


def phone_harmonics(x, amt=0.45):
    """add 2nd/3rd harmonics (≈90–180 Hz) of a sub-bass sound so phone speakers can reproduce the hit"""
    sat = np.tanh(x * 4.0)
    return x + filt(filt(sat, "hp", 85), "lp", 220) * amt


@sfx("heartbeat", "two heartbeat thumps (tension) — with phone-speaker harmonics")
def _(v):
    n = int(0.9 * SR)
    x = np.zeros(n)
    for s, a in ((0.0, 1.0), (0.24, 0.7)):
        i = int(s * SR)
        th = _thump(70, 40, 0.25) * a
        x[i:i + len(th)] += th[: len(x[i:i + len(th)])]
    return phone_harmonics(filt(x, "lp", 300), 0.6)


@sfx("gong", "gong (a ceremonial hit, a chapter card)")
def _(v):
    t = T(4.0)
    x = sum(a * np.sin(2 * np.pi * 98 * r * t) * np.exp(-t * dcy) for r, a, dcy in [(1, 1, 0.8), (1.47, 0.6, 1.1), (2.09, 0.5, 1.4), (2.56, 0.35, 1.8), (3.9, 0.2, 2.5), (5.1, 0.12, 3)])
    x *= 1 + 0.15 * np.sin(2 * np.pi * 3.5 * t)
    x += filt(noise(len(t)), "bp", 1200, 0.8) * env(len(t), 0.002, 0.2, 3) * 0.4
    return fx(x, reverb=0.35, room=0.8)


@sfx("train_horn", "Indian-Railways-style electric-loco horn: two-tone, bright attack (v0 short toot, v1 long 'paaa-paaa')", 2)
def _(v):
    blasts = [(0.0, 0.55)] if v == 0 else [(0.0, 0.85), (1.0, 1.1)]
    d = blasts[-1][0] + blasts[-1][1] + 0.1
    t = T(d)
    x = np.zeros(len(t))
    for start, dur in blasts:
        i0, n = int(start * SR), int(dur * SR)
        tt = np.arange(n) / SR
        bend = 1 - 0.035 * np.exp(-tt * 18) - 0.012 * np.clip((tt - (dur - 0.25)) / 0.25, 0, 1)  # "bwaa" onset, sag at the end
        blast = 0
        for f0, a in ((415.3, 1.0), (523.3, 0.8)):  # the two horn tones
            ph = 2 * np.pi * np.cumsum(f0 * bend) / SR
            for h in range(1, 13):  # reedy, saw-like spectrum
                blast = blast + a * np.sin(h * ph + 0.3 * h) / h ** 0.9
        e = np.clip(tt / 0.03, 0, 1) * np.clip((dur - tt) / 0.12, 0, 1)
        x[i0:i0 + n] += np.tanh(blast * e * 0.9)
    x = filt(x, "lp", 5200)
    presence = filt(x, "bp", 1900, 1.2) * 0.6  # 1.5-2.5 kHz: cuts through on a phone
    return fx(x + presence, reverb=0.4, room=0.85, damp=0.55, delay=0.11)


@sfx("rail_clack", "train wheels over rail joints: clickety-clack (4 s, rolling past)")
def _(v):
    d = 4.0
    n = int(d * SR)
    x = np.zeros(n)
    period, axle = 0.56, 0.11
    k = 0
    tt = 0.05
    while tt < d - 0.3:
        for off, a in ((0.0, 1.0), (axle, 0.8)):
            i = int((tt + off) * SR)
            m = int(0.06 * SR)
            if i + m >= n:
                break
            burst = filt(noise(m), "bp", 2800 + 400 * (k % 2), 2.5) * np.exp(-np.arange(m) / SR * 70) * 0.6
            thump = np.sin(2 * np.pi * 95 * np.arange(m) / SR) * np.exp(-np.arange(m) / SR * 45)
            x[i:i + m] += (burst + thump * 0.9) * a
        tt += period * (1 + 0.02 * np.sin(k))
        k += 1
    x *= bell_env(n, 0.5, 1.2) * 0.9 + 0.1
    x += filt(noise(n, "pink"), "lp", 260) * 0.12 * bell_env(n, 0.5, 1.2)  # the rumble
    return fx(stereo_sweep(x, -0.6, 0.6), reverb=0.2, room=0.5)


@sfx("taiko", "taiko drum hit (big, ceremonial, for action beats)", 3)
def _(v):
    t = T(1.2)
    x = sweep(95 + 8 * v, 62, 1.2) * np.exp(-t * 4) * 1.2 + filt(noise(len(t), "pink"), "bp", 400, 1.0) * np.exp(-t * 30) * 0.6
    return fx(x, drive=4, reverb=0.35, room=0.7)


@sfx("tabla_na", "tabla 'na' (bright ringing stroke)", 2)
def _(v):
    t = T(0.6)
    f = 520 + 40 * v
    x = (np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 2.02 * t) + 0.3 * np.sin(2 * np.pi * f * 3.1 * t)) * np.exp(-t * 9)
    return fx(x + filt(noise(len(t)), "hp", 3000) * np.exp(-t * 200) * 0.5, reverb=0.2, room=0.3)


@sfx("tabla_ge", "tabla 'ge' (bass bayan with pitch bend)", 2)
def _(v):
    t = T(0.7)
    x = np.sin(2 * np.pi * np.cumsum(75 + 5 * v + 45 * np.clip(t / 0.15, 0, 1)) / SR)  # the bayan's pitch glide
    return fx(x * np.exp(-t * 6), reverb=0.2, room=0.3)


# ---- ambience loops (10 s, seamless)
def _loop(x, xf=0.5):
    n = int(xf * SR)
    y = x[..., n:].copy()
    r = np.linspace(0, 1, n)
    y[..., -n:] = y[..., -n:] * (1 - r) + x[..., :n] * r
    return y


@sfx("amb_wind", "wind loop (10 s): open plains, a cliff, night")
def _(v):
    n = int(10.5 * SR)
    lfo = 700 + 450 * np.sin(np.linspace(0, 2 * np.pi * 3, (n + 255) // 256)) + 200 * np.sin(np.linspace(0, 2 * np.pi * 7.3, (n + 255) // 256))
    L = filt_sweep(noise(n, "pink"), "bp", 0, 0, q=1.6, curve=lfo)
    R = filt_sweep(noise(n, "pink", np.random.default_rng(3)), "bp", 0, 0, q=1.6, curve=lfo[::-1])
    return _loop(np.stack([L, R]))


@sfx("amb_river", "river/stream loop (10 s): rolling water with bubbling")
def _(v):
    n = int(10.5 * SR)
    nb = (n + 255) // 256
    chans = []
    for c in range(2):
        g = np.random.default_rng(60 + c)
        x = filt(filt(noise(n, "pink", g), "hp", 200), "lp", 4000) * 0.25
        for b in range(4):  # slowly wandering resonances = moving water
            f = 400 * 2 ** b * (1 + 0.35 * np.sin(np.linspace(0, 2 * np.pi * g.uniform(1.3, 4.1), nb) + g.uniform(0, 6)))
            x += filt_sweep(noise(n, "white", g), "bp", 0, 0, q=6, curve=f) * 0.18
        for k in range(220):  # bubbles
            s0 = int(g.uniform(0, 10.3) * SR)
            f0 = g.uniform(500, 1600)
            m = int(0.05 * SR)
            x[s0:s0 + m] += sweep(f0, f0 * 1.7, 0.05) * np.sin(np.linspace(0, np.pi, m)) * g.uniform(0.03, 0.12)
        chans.append(x)
    return _loop(np.stack(chans))


@sfx("amb_night", "night crickets loop (10 s)")
def _(v):
    n = int(10.5 * SR)
    t = np.arange(n) / SR
    out = []
    for ch, f in ((0, 4300), (1, 4700)):
        chirp = (np.sin(2 * np.pi * 30 * t + ch) > 0.6).astype(float) * (np.sin(2 * np.pi * 0.9 * t + ch * 2) > 0.1)
        x = np.sin(2 * np.pi * f * t) * filt(chirp, "lp", 200) * 0.5 + filt(noise(n, "pink", np.random.default_rng(5 + ch)), "lp", 800) * 0.08
        out.append(x)
    return _loop(np.stack(out))


@sfx("amb_fire", "fire crackle loop (10 s)")
def _(v):
    n = int(10.5 * SR)
    chans = []
    for c in range(2):
        x = filt(noise(n, "brown", np.random.default_rng(20 + c)), "lp", 400) * 0.5
        for k in range(260):
            s = int(RNG.uniform(0, 10.4) * SR)
            m = int(RNG.uniform(0.001, 0.006) * SR)
            x[s:s + m] += RNG.standard_normal(m) * RNG.uniform(0.2, 1)
        chans.append(filt(x, "hp", 60))
    return _loop(np.stack(chans))


@sfx("amb_rain", "rain loop (10 s)")
def _(v):
    n = int(10.5 * SR)
    chans = []
    for c in range(2):
        x = filt(filt(noise(n, "pink", np.random.default_rng(30 + c)), "hp", 700), "lp", 9000) * 0.5
        for k in range(900):
            s = int(RNG.uniform(0, 10.4) * SR)
            m = int(0.004 * SR)
            x[s:s + m] += RNG.standard_normal(m) * RNG.uniform(0.05, 0.4)
        chans.append(x)
    return _loop(np.stack(chans))


@sfx("amb_room", "room tone loop (10 s): quiet air so silence never sounds digital")
def _(v):
    n = int(10.5 * SR)
    return _loop(np.stack([filt(filt(noise(n, "pink", np.random.default_rng(40 + c)), "lp", 1500), "hp", 60) * 0.3 for c in range(2)]))


@sfx("amb_birds", "daytime birds loop (10 s): garden, forest edge, a riverbank morning")
def _(v):
    n = int(10.5 * SR)
    chans = [filt(filt(noise(n, "pink", np.random.default_rng(50 + c)), "hp", 300), "lp", 3000) * 0.04 for c in range(2)]
    g = np.random.default_rng(9)
    for k in range(30):
        c = k % 2
        s0 = int(g.uniform(0, 9.6) * SR)
        kind = g.integers(0, 3)
        f0 = g.uniform(2200, 4200)
        for j in range(g.integers(2, 6)):
            d = g.uniform(0.04, 0.12)
            m = int(d * SR)
            tt = np.arange(m) / SR
            if kind == 0:
                fc = f0 * (1.3 - 0.5 * tt / d)  # falling whistle
            elif kind == 1:
                fc = f0 * (1 + 0.15 * np.sin(2 * np.pi * g.uniform(25, 45) * tt))  # trill
            else:
                fc = f0 * (0.8 + 0.6 * tt / d)  # rising chirp
            mod = np.sin(2 * np.pi * np.cumsum(fc * 2.0) / SR) * (1.5 * np.sin(np.pi * tt / d))  # FM: reedy, bird-like
            chirp = np.sin(2 * np.pi * np.cumsum(fc) / SR + mod) * np.sin(np.pi * tt / d) ** 1.5 * g.uniform(0.08, 0.25)
            i = s0 + int(j * g.uniform(0.09, 0.16) * SR)
            chans[c][i:i + m] += chirp[: len(chans[c][i:i + m])]
    return _loop(np.stack([filt(ch, "lp", 7000) for ch in chans]))


def main():
    import soundfile as sf

    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    if a.list or not a.out:
        for k, (_, d, nv) in LIB.items():
            print(f"{k:14s} {'x' + str(nv) if nv > 1 else '  '}  {d}")
        return
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    names = a.only or list(LIB)
    for k in names:
        fn, d, nv = LIB[k]
        for v in range(1, nv + 1):
            x = done(fn(v))
            name = f"{k}_{v}.wav" if nv > 1 else f"{k}.wav"
            sf.write(str(out / name), x, SR, subtype="PCM_16")
        print(f"[sfx] {k:14s} {nv} file(s)")
    print(f"[done] {out}")


if __name__ == "__main__":
    main()
