"""
make_textures.py — the MATERIAL layer of a look: full-frame texture plates that are laid over every frame
(multiply = darkens only, screen = lightens only) and cycled at 12 fps so the image never looks like flat vector.

    python make_textures.py --out <remotion-project>/public/<production>/tex --style riso   [--w 1080 --h 1920] [--fibres 260]
    python make_textures.py --out … --style cloth      # Pattachitra / Kalamkari: chalk-primed cotton, weave, craquelure
    python make_textures.py --out … --style grain      # glow-flat explainers: film grain + soft tonal blotches
    python make_textures.py --out … --style newsprint  # comic book: yellowed pulp paper, fibres, press dot screen
    python make_textures.py --out … --style washi      # sumi-e / ink manga: kozo paper with long fibres + cloudy thickness

Every style writes ground_0..3.jpg (multiply) + speck_0..3.jpg (screen); riso also keeps its historical names
paper_0..3.jpg and the halftone masks. The template's <Grain/> reads paper_*; the look kits read ground_*.

Writes (as JPG, ~0.3-0.5 MB each):
  paper_0..3.jpg   multiply layer: warm near-white paper with soft mottling, fine tooth and a few fibres.
                   Near-white, so with mix-blend-mode:multiply it only darkens (ink stays ink).
  speck_0..3.jpg   screen layer: near-black with sparse pale specks = riso ink drop-outs. Screen only lightens.
  ht_vgrad.png     halftone mask, no dots at the top → merged dots at the bottom (light beams, fades)
  ht_radial.png    halftone mask, full at the centre → none at the edge (spotlights, vignettes)
  ht_cone.png      halftone mask shaped like a stage-light cone
Four variants exist so the film can cycle them on the boil cadence (12 fps) — every frame looks freshly printed.

Taste notes (learned the hard way): fibres must be subtle. At amplitude 1.0 they read as hay/scratches on a phone;
0.10 with 260 short fibres reads as paper. Always test on a coloured block, not only on blank paper.
"""
import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter


def fibres(rng, W, H, n, length, width, amp):
    img = np.zeros((H, W), np.float32)
    for _ in range(n):
        x, y = rng.uniform(0, W), rng.uniform(0, H)
        a = rng.uniform(0, np.pi)
        L = rng.uniform(0.3, 1.0) * length
        steps = int(L)
        da = rng.normal(0, 0.02, steps).cumsum()
        xs = (x + np.cumsum(np.cos(a + da))).astype(int)
        ys = (y + np.cumsum(np.sin(a + da))).astype(int)
        ok = (xs >= 0) & (xs < W) & (ys >= 0) & (ys < H)
        img[ys[ok], xs[ok]] += amp * rng.uniform(0.4, 1.0)
    return gaussian_filter(img, width)


def paper_layers(out, W, H, nfib):
    for v in range(4):
        rng = np.random.default_rng(100 + v)
        mott = gaussian_filter(rng.standard_normal((H // 8, W // 8)), 6)
        mott = np.kron(mott, np.ones((8, 8)))[:H, :W]
        mott = (mott - mott.min()) / (mott.max() - mott.min())
        grain = gaussian_filter(rng.standard_normal((H, W)), 0.7)
        fib = fibres(rng, W, H, nfib, 40, 0.9, 0.10)
        dark = np.clip(0.07 * mott + 0.03 * np.clip(grain, -3, 3) / 3 + 0.9 * fib - 0.01, 0, 0.35)
        rgb = np.clip(np.stack([1 - dark * 0.85, 1 - dark * 0.95, 1 - dark * 1.15], -1) * 255, 0, 255).astype(np.uint8)
        Image.fromarray(rgb).save(out / f"paper_{v}.jpg", quality=88)
        sp = np.zeros((H, W), np.float32)
        n = 2600
        ys, xs = rng.integers(0, H, n), rng.integers(0, W, n)
        sp[ys, xs] = rng.uniform(0.4, 1.0, n)
        sp = gaussian_filter(sp, 0.9) * 6
        sp += fibres(rng, W, H, 60, 50, 0.6, 0.35)
        sp += 0.06 * np.clip(gaussian_filter(rng.standard_normal((H, W)), 1.2), 0, None)
        sp = np.clip(sp, 0, 1) * 0.55
        rgb = np.clip(np.stack([sp, sp * 0.97, sp * 0.92], -1) * 255, 0, 255).astype(np.uint8)
        Image.fromarray(rgb).save(out / f"speck_{v}.jpg", quality=88)
        print("paper/speck variant", v)


def grid_dots(w, h, step, angle, radius_fn, ss=3):
    im = Image.new("L", (w * ss, h * ss), 0)
    d = ImageDraw.Draw(im)
    ca, sa = np.cos(angle), np.sin(angle)
    R = int(np.hypot(w, h))
    for i in range(-R // step - 2, R // step + 2):
        for j in range(-R // step - 2, R // step + 2):
            u, v = i * step, j * step
            x = w / 2 + u * ca - v * sa
            y = h / 2 + u * sa + v * ca
            if -step < x < w + step and -step < y < h + step:
                r = radius_fn(min(max(x / w, 0), 1), min(max(y / h, 0), 1)) * step * 0.72
                if r > 0.25:
                    d.ellipse([(x - r) * ss, (y - r) * ss, (x + r) * ss, (y + r) * ss], fill=255)
    return im.resize((w, h), Image.LANCZOS)


def halftones(out):
    grid_dots(512, 1024, 16, np.radians(45), lambda x, y: y ** 1.1).save(out / "ht_vgrad.png")
    grid_dots(1024, 1024, 18, np.radians(45), lambda x, y: max(0, 1 - np.hypot(x - .5, y - .5) * 2) ** 0.9).save(out / "ht_radial.png")
    grid_dots(512, 1024, 14, np.radians(30), lambda x, y: max(0, (1 - y) ** 0.8 * (1 - abs(x - .5) * 1.6))).save(out / "ht_cone.png")
    print("halftone masks")


def norm01(x):
    return (x - x.min()) / (x.max() - x.min() + 1e-9)


def save_rgb(path, dark, tint=(0.85, 0.95, 1.15)):
    """dark (0 = white … 1 = black) → warm multiply plate"""
    rgb = np.clip(np.stack([1 - dark * tint[0], 1 - dark * tint[1], 1 - dark * tint[2]], -1) * 255, 0, 255).astype(np.uint8)
    Image.fromarray(rgb).save(path, quality=88)


def voronoi_edges(rng, W, H, cell, jitter_amp=6):
    """thin network of irregular cell borders (craquelure, cracked earth, leather)"""
    from scipy.spatial import cKDTree

    n = int(W * H / cell ** 2)
    pts = np.stack([rng.uniform(0, W, n), rng.uniform(0, H, n)], 1)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    jx = gaussian_filter(rng.standard_normal(((H + 3) // 4, (W + 3) // 4)), 3)
    jy = gaussian_filter(rng.standard_normal(((H + 3) // 4, (W + 3) // 4)), 3)
    jx = np.kron(jx, np.ones((4, 4)))[:H, :W] * jitter_amp * 4
    jy = np.kron(jy, np.ones((4, 4)))[:H, :W] * jitter_amp * 4
    d, _ = cKDTree(pts).query(np.stack([(xx + jx).ravel(), (yy + jy).ravel()], 1), k=2)
    gap = (d[:, 1] - d[:, 0]).reshape(H, W)
    return np.clip(1 - gap / 1.6, 0, 1)


def cloth_layers(out, W, H):
    """Pattachitra patta: cotton cloth primed with chalk + tamarind gum, painted, burnished, aged."""
    for v in range(4):
        rng = np.random.default_rng(300 + v)
        t = 3  # thread pitch (px)
        rows = np.repeat(rng.uniform(-1, 1, H // t + 2), t)[:H]
        cols = np.repeat(rng.uniform(-1, 1, W // t + 2), t)[:W]
        yy, xx = np.mgrid[0:H, 0:W]
        over = ((xx // t + yy // t) % 2).astype(bool)
        weave = np.where(over, rows[:, None] + 0 * xx, cols[None, :] + 0 * yy)
        edge = (((xx % t) == 0) | ((yy % t) == 0)).astype(np.float32)  # tiny gaps between threads
        weave = gaussian_filter(weave * 0.6 + edge * 0.8, 0.55)
        prime = norm01(gaussian_filter(rng.standard_normal(((H + 5) // 6, (W + 5) // 6)), 5))
        prime = np.kron(prime, np.ones((6, 6)))[:H, :W]
        streak = norm01(gaussian_filter(rng.standard_normal((H, (W + 9) // 10)), (1.5, 0.8)))  # vertical brush streaks
        streak = np.kron(streak, np.ones((1, 10)))[:, :W]
        cracks = voronoi_edges(rng, W, H, cell=rng.uniform(55, 75))
        where = norm01(gaussian_filter(rng.standard_normal(((H + 15) // 16, (W + 15) // 16)), 4))
        where = np.kron(where, np.ones((16, 16)))[:H, :W]
        cracks *= np.clip((where - 0.35) * 2.5, 0, 1)
        pool = norm01(gaussian_filter(rng.standard_normal((H, W)), 9))  # pigment pooling: uneven hand-ground colour
        vign = np.clip((np.hypot((xx - W / 2) / (W / 2), (yy - H / 2) / (H / 2)) - 0.75) * 0.5, 0, 0.25)
        dark = 0.07 * weave + 0.07 * prime + 0.03 * streak + 0.09 * pool + 0.32 * cracks + vign - 0.05
        save_rgb(out / f"ground_{v}.jpg", np.clip(dark, 0, 0.5), tint=(0.8, 0.95, 1.25))
        # screen layer: paint chipped off along the cracks (irregular flakes, not round dots) + faint light crack edges
        chips = np.zeros((H, W), np.float32)
        cy, cx = np.nonzero(cracks > 0.6)
        if len(cy):
            pick = rng.choice(len(cy), size=min(700, len(cy)), replace=False)
            for i in pick:
                y0, x0 = cy[i], cx[i]
                L = rng.integers(2, 7)
                ang = rng.uniform(0, np.pi)
                for k in range(L):
                    yy0 = int(y0 + np.sin(ang) * k)
                    xx0 = int(x0 + np.cos(ang) * k)
                    if 0 <= yy0 < H - 1 and 0 <= xx0 < W - 1:
                        chips[yy0:yy0 + 2, xx0:xx0 + 2] = rng.uniform(0.5, 1.0)
        k = 250
        ys, xs = rng.integers(0, H, k), rng.integers(0, W, k)
        chips[ys, xs] = rng.uniform(0.3, 0.7, k)
        sp = gaussian_filter(chips, 0.7) * 2.2 + 0.25 * np.roll(cracks, 1, 0)
        sp = np.clip(sp, 0, 1) * 0.42
        rgb = np.clip(np.stack([sp, sp * 0.96, sp * 0.86], -1) * 255, 0, 255).astype(np.uint8)
        Image.fromarray(rgb).save(out / f"speck_{v}.jpg", quality=88)
        print("cloth variant", v)


def washi_layers(out, W, H):
    """sumi-e / ink manga: Japanese kozo paper — long curly fibres, cloudy thickness (light through thin spots), a few
    embedded flecks. Ink absorbs unevenly on it, which the look kit fakes with turbulence edges."""
    for v in range(4):
        rng = np.random.default_rng(900 + v)
        cloud = norm01(gaussian_filter(rng.standard_normal((H // 4 + 1, W // 4 + 1)), 10))
        cloud = np.kron(cloud, np.ones((4, 4)))[:H, :W]
        fib = fibres(rng, W, H, 180, 160, 0.7, 0.2)  # long kozo fibres
        fib2 = fibres(rng, W, H, 500, 30, 0.5, 0.08)
        grain = gaussian_filter(rng.standard_normal((H, W)), 0.9)
        # visible at phone size (the first version measured "flat" in qa_lint: material median 0.0027)
        dark = np.clip(0.12 * cloud + 1.8 * fib + 1.6 * fib2 + 0.06 * np.clip(grain, -3, 3) / 3 - 0.01, 0, 0.4)
        save_rgb(out / f"ground_{v}.jpg", dark, tint=(0.75, 0.9, 1.2))
        # screen: bright fibres that show on ink (paper texture visible through black)
        light = np.clip(fibres(rng, W, H, 260, 140, 0.8, 0.7) + 0.08 * (1 - cloud) + 0.05 * np.clip(-grain, 0, 3) / 3, 0, 0.6) * 0.6
        rgb = np.clip(np.stack([light, light * 0.97, light * 0.9], -1) * 255, 0, 255).astype(np.uint8)
        Image.fromarray(rgb).save(out / f"speck_{v}.jpg", quality=88)
        print("washi variant", v)


def newsprint_layers(out, W, H):
    """comic-book newsprint: warm yellowed pulp paper, visible fibres, uneven ink absorption (blotches), a faint
    printing-press dot screen, and pale specks where ink didn't take."""
    for v in range(4):
        rng = np.random.default_rng(700 + v)
        mott = norm01(gaussian_filter(rng.standard_normal((H // 6 + 1, W // 6 + 1)), 5))
        mott = np.kron(mott, np.ones((6, 6)))[:H, :W]
        grain = gaussian_filter(rng.standard_normal((H, W)), 0.8)
        fib = fibres(rng, W, H, 420, 36, 0.8, 0.16)
        yy, xx = np.mgrid[0:H, 0:W]
        screen = (np.sin(xx * 0.9 + yy * 0.52) * np.sin(yy * 0.9 - xx * 0.52) > 0.6).astype(np.float32)
        vign = np.clip((np.hypot((xx - W / 2) / (W / 2), (yy - H / 2) / (H / 2)) - 0.8) * 0.35, 0, 0.18)
        dark = np.clip(0.09 * mott + 0.05 * np.clip(grain, -3, 3) / 3 + fib + 0.025 * screen + vign, 0, 0.4)
        save_rgb(out / f"ground_{v}.jpg", dark, tint=(0.8, 0.95, 1.35))
        sp = np.zeros((H, W), np.float32)
        n = 1400
        ys, xs = rng.integers(0, H, n), rng.integers(0, W, n)
        sp[ys, xs] = rng.uniform(0.4, 1.0, n)
        sp = np.clip(gaussian_filter(sp, 0.9) * 5, 0, 1) * 0.45
        rgb = np.clip(np.stack([sp, sp * 0.97, sp * 0.9], -1) * 255, 0, 255).astype(np.uint8)
        Image.fromarray(rgb).save(out / f"speck_{v}.jpg", quality=88)
        print("newsprint variant", v)


def grain_layers(out, W, H):
    """'glow-flat' explainers (Kurzgesagt-grade vector): clean shapes need FILM GRAIN + soft tonal blotches so they read
    as printed/filmed, not as flat vector. Multiply plate darkens light areas; screen plate lifts dark areas (on navy
    backgrounds the screen grain is what you see)."""
    for v in range(4):
        rng = np.random.default_rng(500 + v)
        g = gaussian_filter(rng.standard_normal((H, W)), 0.55)
        g = g / (np.abs(g).max() + 1e-9)
        blot = norm01(gaussian_filter(rng.standard_normal((H // 8 + 1, W // 8 + 1)), 6))
        blot = np.kron(blot, np.ones((8, 8)))[:H, :W]
        # LESSON (explainer test 1): grain this subtle passes a pixel metric but reads as "sterile digital gradients"
        # at phone size. It must be VISIBLE: ~2x what feels right on a monitor.
        dark = np.clip(0.15 * np.clip(g, 0, 1) + 0.06 * blot, 0, 0.4)
        save_rgb(out / f"ground_{v}.jpg", dark, tint=(1.0, 1.0, 1.0))
        light = np.clip(0.22 * np.clip(-g, 0, 1) + 0.05 * (1 - blot), 0, 0.5)
        rgb = np.clip(np.stack([light, light, light * 1.05], -1) * 255, 0, 255).astype(np.uint8)
        Image.fromarray(rgb).save(out / f"speck_{v}.jpg", quality=90)
        print("grain variant", v)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--style", default="riso", choices=["riso", "cloth", "grain", "newsprint", "washi"])
    ap.add_argument("--w", type=int, default=1080)
    ap.add_argument("--h", type=int, default=1920)
    ap.add_argument("--fibres", type=int, default=260)
    a = ap.parse_args()
    if a.w < 64 or a.h < 64 or a.w % 8 or a.h % 8:
        ap.error('--w and --h must be multiples of 8, at least 64')
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    if a.style == "riso":
        paper_layers(out, a.w, a.h, a.fibres)
        halftones(out)
        for v in range(4):  # generic names for the look kits
            import shutil

            shutil.copy(out / f"paper_{v}.jpg", out / f"ground_{v}.jpg")
    elif a.style == "cloth":
        cloth_layers(out, a.w, a.h)
    elif a.style == "grain":
        grain_layers(out, a.w, a.h)
    elif a.style == "newsprint":
        newsprint_layers(out, a.w, a.h)
    elif a.style == "washi":
        washi_layers(out, a.w, a.h)
    print("wrote", out)
