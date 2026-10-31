"""
mix.py — build the final soundtrack from a cue sheet: voice + music cues (ducked under the voice) + SFX + ambience,
mastered to streaming loudness. Run from the Remotion project root.

    python <skill>/scripts/mix.py --cues src/productions/<name>/mix.json --out public/<name>/mix.wav

mix.json:
{
  "duration": "voice",                      # seconds, or "voice" (= voice.wav length) or "music" (= end of last music cue)
  "voice": {"file": "public/x/voice/voice.wav", "gain_db": 0},
  "music": [                                # cues on the timeline; overlapping cues cross-fade by their fades
    {"file": "public/x/music/cue_a.mp3", "at": 0.0, "from": 0.0, "until": 23.6, "gain_db": -4,
     "fade_in": 0.2, "fade_out": 1.5, "duck_db": 9, "loop": false}
  ],
  "sfx_dir": "public/x/sfx",
  "sfx": [                                  # t = where the sound STARTS; "align": "end" makes it END at t (risers, swells)
    {"t": 3.52, "name": "whoosh_m", "gain_db": -12, "pan": 0.3},
    {"t": 23.6, "name": "riser_2s", "align": "end", "gain_db": -10}
  ],
  "events": {"file": "src/productions/x/data/events.json",     # optional: sounds for the film's own event list
             "map": {"hit": {"name": "hit_heavy", "gain_db": -6}, "land": {"name": "thud_soft", "gain_db": -10},
                     "clash": [{"name": "sword_clash", "gain_db": -6}, {"name": "swish", "gain_db": -10, "offset": -0.12}]}},
  "ambience": [{"file": "public/x/sfx/amb_river.wav", "at": 4, "until": 40, "gain_db": -24, "loop": true, "fade_in": 1.5, "fade_out": 1.5}],
  "master": {"lufs": -14, "true_peak": -2.0, "fade_out": 0.35}  # -2 dBTP: AAC encoding adds ~1.2 dB; fade_out (s)
}                                                                  # ends the mix in silence so a looping reel doesn't click
  * "name" picks a random variant (name_1/_2/_3) from sfx_dir when the plain file is missing; pin one with "hit_heavy_2".
  * duck_db: how far the cue drops while someone speaks (8-12 dB for narration; 0 for a music video).
  * events.json is a list of {"t": seconds, "type": "hit", ...} — the same file the scenes read, so a punch is heard exactly
    when it is drawn.
Prints a report: loudness, peak, and the voice-over-music margin in speech regions (aim for ≥ 10 dB so words stay clear
on phone speakers). Then run listen.py --kind mix on the result.
"""
import argparse
import json
import random
import subprocess
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SR = 48000


def load(path):
    import soundfile as sf

    p = Path(path)
    if p.suffix.lower() == ".wav":
        x, sr = sf.read(str(p), dtype="float32", always_2d=True)
        if sr == SR:
            return np.repeat(x, 2, 1) if x.shape[1] == 1 else x[:, :2]
    tmp = Path(str(p) + ".mixdec.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(p), "-ac", "2", "-ar", str(SR), str(tmp)], check=True)
    x, _ = sf.read(str(tmp), dtype="float32", always_2d=True)
    tmp.unlink()
    return x


def db(x):
    return 10 ** (x / 20)


def place(bus, x, at, gain=1.0, fade_in=0.0, fade_out=0.0):
    i0 = int(round(at * SR))
    if i0 < 0:
        x = x[-i0:]
        i0 = 0
    n = min(len(x), len(bus) - i0)
    if n <= 0:
        return
    y = x[:n].copy() * gain
    fi, fo = int(fade_in * SR), int(fade_out * SR)
    if fi > 0:
        y[:min(fi, n)] *= np.linspace(0, 1, min(fi, n))[:, None]
    if fo > 0:
        y[-min(fo, n):] *= np.linspace(1, 0, min(fo, n))[:, None] ** 1.3
    bus[i0:i0 + n] += y


def voice_env(v):
    """0..1 'someone is talking' envelope with 80 ms attack / 450 ms release (drives the music ducking)"""
    m = np.abs(v).mean(1)
    hop = 240
    r = np.sqrt(np.convolve(m ** 2, np.ones(hop * 6) / (hop * 6), mode="same"))[::hop]
    on = (r > db(-42)).astype(float)
    e = np.zeros_like(on)
    for k in range(1, len(on)):
        a = 1 - np.exp(-hop / SR / (0.08 if on[k] > e[k - 1] else 0.45))
        e[k] = e[k - 1] + a * (on[k] - e[k - 1])
    return np.interp(np.arange(len(v)), np.arange(len(e)) * hop, e)


def sfx_file(d, name):
    p = Path(d) / f"{name}.wav"
    if p.exists():
        return p
    vs = sorted(Path(d).glob(f"{name}_[0-9].wav"))
    if not vs:
        sys.exit(f"sfx {name!r} not found in {d} (run sfx.py --out {d})")
    return random.choice(vs)


def main():
    import pyloudnorm as pyln
    import soundfile as sf
    from pedalboard import Compressor, Limiter, Pedalboard

    ap = argparse.ArgumentParser()
    ap.add_argument("--cues", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    random.seed(a.seed)
    cue = json.loads(Path(a.cues).read_text(encoding="utf-8"))
    voice = load(cue["voice"]["file"]) * db(cue["voice"].get("gain_db", 0)) if cue.get("voice") else None
    dur = cue.get("duration", "voice")
    if dur == "voice":
        dur = len(voice) / SR
    elif dur == "music":
        dur = max(m.get("until", m.get("at", 0) + len(load(m["file"])) / SR) for m in cue["music"])
    N = int(float(dur) * SR)
    vbus = np.zeros((N, 2), np.float32)
    if voice is not None:
        place(vbus, voice, 0)
    duck = voice_env(vbus) if voice is not None else np.zeros(N)

    mbus = np.zeros((N, 2), np.float32)
    for m in cue.get("music", []):
        x = load(m["file"])[int(m.get("from", 0) * SR):]
        at = m.get("at", 0)
        until = m.get("until", at + len(x) / SR)
        need = int((until - at) * SR)
        if m.get("loop") and len(x) < need:
            x = np.concatenate([x] * (need // len(x) + 1))
        x = x[:need]
        seg = np.zeros((N, 2), np.float32)
        place(seg, x, at, db(m.get("gain_db", 0)), m.get("fade_in", 0.05), m.get("fade_out", 0.5))
        d = m.get("duck_db", 0)
        if d:
            seg *= (1 - (1 - db(-d)) * duck)[:, None]
        mbus += seg

    abus = np.zeros((N, 2), np.float32)
    for m in cue.get("ambience", []):
        x = load(m["file"])
        at, until = m.get("at", 0), m.get("until", dur)
        need = int((until - at) * SR)
        if m.get("loop", True) and len(x) < need:
            x = np.concatenate([x] * (need // len(x) + 1))
        place(abus, x[:need], at, db(m.get("gain_db", -24)), m.get("fade_in", 1.0), m.get("fade_out", 1.0))

    sbus = np.zeros((N, 2), np.float32)
    sd = cue.get("sfx_dir", "")
    hits = list(cue.get("sfx", []))
    if cue.get("events"):
        ev = json.loads(Path(cue["events"]["file"]).read_text(encoding="utf-8"))
        for e in ev:
            spec = cue["events"]["map"].get(e.get("type"))
            for sp in (spec if isinstance(spec, list) else [spec] if spec else []):  # one type can layer several sounds
                hits.append({**sp, "t": e["t"] + sp.get("offset", 0)})
    for h in hits:
        x = load(h["file"]) if "file" in h else load(sfx_file(sd, h["name"]))
        if h.get("rate", 1) != 1:  # pitch/speed variation
            idx = np.arange(0, len(x) - 1, h["rate"])
            x = np.stack([np.interp(idx, np.arange(len(x)), x[:, c]) for c in range(2)], 1).astype(np.float32)
        p = h.get("pan", 0)
        if p:
            ang = (p + 1) * np.pi / 4
            x = x * np.array([np.cos(ang), np.sin(ang)]) * np.sqrt(2)
        at = h["t"] - (len(x) / SR if h.get("align") == "end" else 0)
        place(sbus, x, at, db(h.get("gain_db", -10)))

    # phones can't play sub-bass; it only eats headroom and makes small speakers distort. Thin the SFX low end,
    # take everything below 30 Hz off the master.
    from pedalboard import HighpassFilter, LowShelfFilter

    sbus = Pedalboard([HighpassFilter(45), LowShelfFilter(110, -5, 0.7)])(sbus.T.copy().astype(np.float32), SR).T
    mix = vbus + mbus + abus + sbus
    mix = Pedalboard([HighpassFilter(30), Compressor(threshold_db=-16, ratio=2.0, attack_ms=15, release_ms=200)])(mix.T.copy().astype(np.float32), SR).T
    ms = cue.get("master", {})
    # a sound still ringing at the last sample (a sting longer than the film) ends in a click, heard on every loop
    fo = min(len(mix), int(ms.get("fade_out", 0) * SR))
    if fo:
        mix[-fo:] *= (np.cos(np.linspace(0, np.pi, fo)) * 0.5 + 0.5)[:, None]
    meter = pyln.Meter(SR)
    target = ms.get("lufs", -14)
    ceil = ms.get("true_peak", -2.0) - 0.5  # true-peak ceiling; AAC adds ~1.2 dB on dense mixes, so -2 dBTP → ≈-1 after upload

    def limit(x):
        """true-peak limiter: 4x-oversampled peak detection, 1.5 ms lookahead, 60 ms release. Sample-peak limiters
        (pedalboard's) let inter-sample peaks through, and AAC then clips them on upload."""
        from scipy.ndimage import minimum_filter1d
        from scipy.signal import resample_poly

        up = np.abs(resample_poly(x, 4, 1, axis=0)).max(1)
        tp = up[: len(x) * 4].reshape(-1, 4).max(1)
        need = np.minimum(1.0, db(ceil) / np.maximum(tp, 1e-9))
        L = int(0.0015 * SR)
        g = minimum_filter1d(need, size=2 * L + 1)
        a = np.exp(-1 / (0.06 * SR))
        out = np.empty_like(g)
        cur = 1.0
        for i in range(len(g)):
            cur = g[i] if g[i] < cur else a * cur + (1 - a) * g[i]
            out[i] = cur
        return (x * out[:, None]).astype(np.float32)

    g = target - meter.integrated_loudness(mix)
    for _ in range(3):  # limiting shaves loudness: re-aim twice
        out = limit(mix * db(g))
        g += target - meter.integrated_loudness(out)
    mix = out
    lufs2 = meter.integrated_loudness(mix)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    sf.write(a.out, mix, SR, subtype="PCM_24")

    # report
    sp = duck > 0.7
    if sp.any() and (mbus[sp] ** 2).mean() > 0:
        vr = 10 * np.log10((vbus[sp] ** 2).mean() / ((mbus[sp] + abus[sp]) ** 2).mean())
        margin = f"voice over music+ambience while speaking: {vr:+.1f} dB " + ("(ok)" if vr >= 10 else "(LOW: lower music gain_db or raise duck_db)")
    else:
        margin = "no voice/music overlap"
    print(f"[mix] {a.out}  {dur:.2f}s  {lufs2:.1f} LUFS  peak {20 * np.log10(np.abs(mix).max() + 1e-9):.1f} dBFS  |  {margin}")
    print(f"[mix] {len(cue.get('music', []))} music cues, {len(hits)} sfx, {len(cue.get('ambience', []))} ambience beds")


if __name__ == "__main__":
    main()
