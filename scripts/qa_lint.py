"""
qa_lint.py — automatic checks on a rendered video, before any human or AI looks at it.

    python <skill>/scripts/qa_lint.py --video out/<name>/<name>_v1.mp4 [--expect 1080x1920@30] [--json report.json]

Checks (FAIL = must fix, WARN = look at it):
  format     resolution/fps as expected, H.264 yuv420p, AAC audio present                                  FAIL
  flashes    more than 3 whole-frame luminance-flip pairs in any 1 s window (heuristic only)                 FAIL
  black      fully black/white frames lasting > 0.3 s outside the first/last second                          WARN
  dropout    1-3 frame dips: a frame much darker than the frames on BOTH sides (a layer / bloom / effect failed to
             draw — GPU leak or one render tab losing state; railpulse v3 had 32, every 4th frame)    FAIL ≥ 3 / WARN
  static     > 1.2 s where nothing but paper grain moves (a dead frame on Reels = a swipe)                   WARN
  shots      shot lengths from cut detection; any shot > 5 s, and the average (P(doom) ≈ 2.2 s)              WARN
  texture    share of seconds that are "flat vector" (no material: grain, halftone, brush, print noise). The bar
             (P(doom)) has ~5 %, median material 0.0074; the earlier flat-vector videos sat at 0.001        WARN
  audio      integrated loudness −14 ±1.5 LUFS, true peak ≤ −0.5 dBFS, silent gaps > 1.5 s                   WARN
Prints a report and writes <video>.lint.md. Exit code 1 if anything FAILs.
Thresholds were tuned to internal short-form productions; style-dependent warnings need human inspection.
This heuristic does not certify accessibility or photosensitivity safety.
"""
import argparse
import json
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

W, H = 144, 256  # analysis size (keeps 9:16)


def probe(v):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,codec_name,width,height,r_frame_rate,pix_fmt,sample_rate:format=duration",
                        "-of", "json", str(v)], capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def frames(v, w, h, gray=False):
    cmd = ["ffmpeg", "-v", "error", "-i", str(v), "-vf", f"scale={w}:{h}:flags=area", "-f", "rawvideo", "-pix_fmt", "gray" if gray else "rgb24", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    sz = w * h * (1 if gray else 3)
    try:
        while True:
            b = p.stdout.read(sz)
            if len(b) < sz:
                break
            yield np.frombuffer(b, np.uint8).reshape(h, w) if gray else np.frombuffer(b, np.uint8).reshape(h, w, 3)
        if p.wait() != 0:
            raise RuntimeError('FFmpeg decoding failed; install a full FFmpeg build on PATH')
    finally:
        p.stdout.close()
        if p.poll() is None:
            p.terminate()
        p.wait()


def blur(x):
    k = np.array([1, 4, 6, 4, 1], float) / 16
    y = np.apply_along_axis(lambda r: np.convolve(r, k, mode="same"), 1, x)
    return np.apply_along_axis(lambda c: np.convolve(c, k, mode="same"), 0, y)


def lint(video, expect="1080x1920@30", allow_silent=False):
    info = probe(video)
    vs = next(s for s in info["streams"] if s["codec_type"] == "video")
    au = [s for s in info["streams"] if s["codec_type"] == "audio"]
    fps = float(Fraction(vs["r_frame_rate"]))
    dur = float(info["format"]["duration"])
    res = []

    def add(level, check, msg):
        res.append((level, check, msg))

    ew, eh, ef = [float(x) for x in expect.replace("@", "x").split("x")]
    if (vs["width"], vs["height"]) != (int(ew), int(eh)) or abs(fps - ef) > 0.01:
        add("FAIL", "format", f"{vs['width']}x{vs['height']}@{fps:.2f}, expected {expect}")
    if vs["codec_name"] != "h264":
        add("FAIL", "format", f"video codec {vs['codec_name']} — Instagram/TikTok/Shorts want H.264")
    elif vs.get("pix_fmt") != "yuv420p":
        add("WARN", "format", f"pixel format {vs.get('pix_fmt')} (full-range JPEG colour, Remotion's default): most apps cope, "
                              "but some players shift colours — render using remotion.config.ts (BT.709 / yuv420p)")
    if not au and not allow_silent:
        add("FAIL", "format", "no audio stream")
    elif au and au[0]["codec_name"] != "aac":
        add("WARN", "format", f"audio codec {au[0]['codec_name']} (aac is safest)")

    lum, motion, hists, tex = [], [], [], []
    prev = None
    prevh = None
    for i, f in enumerate(frames(video, W, H)):
        c = f.astype(np.float32) / 255
        g = (np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)) @ np.array([0.2126, 0.7152, 0.0722])  # linear light
        lum.append(float(g.mean()))
        b = blur(g)
        motion.append(float(np.abs(b - prev).mean()) if prev is not None else 1.0)
        prev = b
        hq = np.histogramdd(f.reshape(-1, 3) // 32, bins=(8, 8, 8), range=((0, 8),) * 3)[0].ravel()
        hq /= hq.sum()
        hists.append(float(0.5 * np.abs(hq - prevh).sum()) if prevh is not None else 0.0)
        prevh = hq
    n = len(lum)
    if n == 0:
        raise ValueError('No video frames decoded')
    # texture: 1 frame/s at 360x640. Material (paper grain, halftone, brush, print noise) = small-scale residual left
    # after a 5x5 median filter, measured AWAY from drawn edges. Calibrated: P(doom) median 0.0074 (5th pct 0.0036);
    # flat-vector videos 0.0009-0.0015. Below 0.003 = "flat".
    from scipy.ndimage import median_filter, sobel

    detail = []
    for k, f in enumerate(frames(video, 360, 640, gray=True)):
        if k % max(1, int(round(fps))):
            continue
        x = f.astype(np.float32) / 255
        med = median_filter(x, size=5)
        edge = np.hypot(sobel(med, 0), sobel(med, 1))
        m = edge < 0.08
        detail.append(float(np.abs(x - med)[m].mean()) if m.any() else 0.0)
    lum, motion, hists = map(np.array, (lum, motion, hists))

    # flashes (WCAG 2.3.1 style): a flash = a PAIR of opposing relative-luminance changes of >= 10 % where the darker
    # state is < 0.8. More than 3 flashes in any 1 s window = FAIL. Whole-frame mean luminance (linear light).
    dl = np.diff(lum)
    big = np.where((np.abs(dl) > 0.10) & (np.minimum(lum[:-1], lum[1:]) < 0.8))[0]
    worst, worst_t = 0, 0
    for i in big:
        win = big[(big >= i) & (big < i + fps)]
        flips = 1 + int(np.sum(np.sign(dl[win][1:]) != np.sign(dl[win][:-1]))) if len(win) else 0
        if flips // 2 > worst:
            worst, worst_t = flips // 2, i / fps
    if worst > 3:
        add("FAIL", "flashes", f"{worst} whole-frame luminance flips inside 1 s at {worst_t:.1f}s (heuristic limit 3); inspect and soften them")
    elif worst:
        add("INFO", "flashes", f"max {worst} flash(es) per second (limit 3), worst at {worst_t:.1f}s")
    # black/white frames
    blank = (lum < 0.002) | (lum > 0.97)
    run = 0
    for i, bl in enumerate(np.append(blank, False)):
        if bl:
            run += 1
        else:
            if run / fps > 0.3 and fps < i - run and i < n - fps:
                add("WARN", "black", f"{run / fps:.1f}s blank frame at {(i - run) / fps:.1f}s")
            run = 0
    # dropouts: frame i is < 50 % (linear light) of the brightest frame within 3 frames on EACH side, so a cut into a
    # darker shot (dark on one side only) or the frames around a white flash don't count
    drops = []
    for i in range(3, n - 3):
        lo = min(lum[i - 3:i].max(), lum[i + 1:i + 4].max())
        if lo > 0.003 and lum[i] < 0.5 * lo:
            drops.append(i)
    if drops:
        lvl = "FAIL" if len(drops) >= 3 else "WARN"
        add(lvl, "dropout", f"{len(drops)} frame(s) far darker than both neighbours, first at {drops[0] / fps:.2f}s, last at {drops[-1] / fps:.2f}s "
                            f"(frames {', '.join(str(d) for d in drops[:12])}) — a layer/effect failed to draw: look for per-frame GPU allocation "
                            "(effect props that change every frame, geometry rebuilt per frame) or a render tab that lost its state")
    # cuts + shots
    # a cut = colour histogram jumps, OR the layout jumps (blurred frame difference spikes far above its neighbours):
    # scenes that share one palette (a red-lattice film) only show up in the second test
    cuts = [0]
    for i in range(1, n):
        loc = np.median(motion[max(1, i - 8):min(n, i + 9)])
        if (hists[i] > 0.45 and motion[i] > 0.02) or (motion[i] > 0.045 and motion[i] > 5 * loc):
            if i - cuts[-1] > 6:
                cuts.append(i)
    cuts.append(n)
    shots = np.diff(cuts) / fps
    if len(shots):
        for k, s in enumerate(shots):
            a0, a1 = cuts[k], cuts[k + 1]
            events = int(np.sum(hists[a0 + 1:a1] > 0.12))  # new elements / big changes inside the shot
            if s > 5 and events < s / 3:
                add("WARN", "shots", f"shot {k} at {a0 / fps:.1f}s lasts {s:.1f}s with only {events} visual events — add a new element, move or cut")
        add("INFO", "shots", f"{len(shots)} shots, average {shots.mean():.1f}s (P(doom) ≈ 2.2 s; narrated stories 2.5-4 s)")
    # static stretches (blurred motion ~ 0 → only grain moving)
    still = motion < 0.0025
    run = 0
    for i, st in enumerate(np.append(still, False)):
        if st:
            run += 1
        else:
            if run / fps > 1.2:
                add("WARN", "static", f"{run / fps:.1f}s with no real motion from {(i - run) / fps:.1f}s — add camera drift, idle motion or a new element")
            run = 0
    flat = np.array(detail) < 0.003
    if len(detail):
        share = flat.mean()
        lvl = "WARN" if share > 0.10 else "INFO"
        add(lvl, "texture", f"{share * 100:.0f}% of seconds look flat/untextured, median material {np.median(detail):.4f} "
                            f"(P(doom): 5 %, median 0.0074; flat vector ≈ 0.001). "
                            + ("Seconds: " + ", ".join(str(i) for i in np.where(flat)[0][:25]) if share else ""))
    # audio
    if au:
        import soundfile as sf

        tmp = Path(str(video) + ".lint.wav")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-ac", "2", "-ar", "48000", str(tmp)], check=True)
        x, sr = sf.read(str(tmp))
        tmp.unlink()
        try:
            import pyloudnorm as pyln

            L = pyln.Meter(sr).integrated_loudness(x)
            if abs(L + 14) > 1.5:
                add("WARN", "audio", f"integrated loudness {L:.1f} LUFS (Reels/Shorts/TikTok normalise to about −14)")
            else:
                add("INFO", "audio", f"loudness {L:.1f} LUFS")
        except ImportError:
            pass
        pk = 20 * np.log10(np.abs(x).max() + 1e-9)
        if pk > -0.5:
            add("WARN", "audio", f"peak {pk:.1f} dBFS — will distort after platform encoding; limit to −1")
        m = np.abs(x).mean(1)
        hop = sr // 20
        r = np.sqrt(np.convolve(m ** 2, np.ones(hop) / hop, mode="same"))[::hop]
        q = r < 10 ** (-55 / 20)
        run = 0
        for i, s in enumerate(np.append(q, False)):
            if s:
                run += 1
            else:
                if run / 20 > 1.5 and i - run > 20 and i < len(q) - 20:
                    add("WARN", "audio", f"{run / 20:.1f}s of silence at {(i - run) / 20:.1f}s")
                run = 0
    return res, {"frames": n, "fps": fps, "duration": dur, "shots": [round(float(s), 2) for s in shots],
                 "flat_share": float(flat.mean()) if len(detail) else None, "detail_per_sec": [round(float(d), 3) for d in detail]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--expect", default="1080x1920@30")
    ap.add_argument("--json")
    ap.add_argument("--allow-silent", action="store_true", help="permit intentionally silent demos and previews")
    a = ap.parse_args()
    res, stats = lint(a.video, a.expect, a.allow_silent)
    order = {"FAIL": 0, "WARN": 1, "INFO": 2}
    lines = [f"# lint: {Path(a.video).name}  ({stats['duration']:.1f}s, {stats['frames']} frames)"]
    for lvl, chk, msg in sorted(res, key=lambda r: order[r[0]]):
        lines.append(f"{lvl:4s} {chk:8s} {msg}")
    fails = sum(1 for r in res if r[0] == "FAIL")
    lines.append(f"-> {fails} FAIL, {sum(1 for r in res if r[0] == 'WARN')} WARN")
    txt = "\n".join(lines)
    print(txt)
    Path(str(a.video) + ".lint.md").write_text(txt + "\n", encoding="utf-8")
    if a.json:
        Path(a.json).write_text(json.dumps({"results": res, **stats}, indent=1))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
