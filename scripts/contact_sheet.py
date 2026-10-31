"""Build a labelled contact sheet: python scripts/contact_sheet.py out/sheet.jpg out/stills/*.png"""
import argparse
import glob
from pathlib import Path
from PIL import Image, ImageDraw


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('output')
    ap.add_argument('images', nargs='+')
    ap.add_argument('--cols', type=int, default=3)
    a = ap.parse_args()
    paths = [Path(p) for pattern in a.images for p in sorted(glob.glob(pattern))]
    if not paths or a.cols < 1:
        ap.error('Provide images and a positive column count')
    thumb_w, thumb_h = 270, 480
    sheet = Image.new('RGB', (a.cols * thumb_w, ((len(paths) + a.cols - 1) // a.cols) * (thumb_h + 35)), '#172B2B')
    draw = ImageDraw.Draw(sheet)
    for i, path in enumerate(paths):
        x, y = (i % a.cols) * thumb_w, (i // a.cols) * (thumb_h + 35)
        with Image.open(path) as im:
            im = im.convert('RGB')
            im.thumbnail((thumb_w, thumb_h), Image.Resampling.LANCZOS)
            sheet.paste(im, (x + (thumb_w - im.width) // 2, y + (thumb_h - im.height) // 2))
        draw.text((x + 6, y + thumb_h + 8), path.stem[:35], fill='#F3ECD9')
    out = Path(a.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    print(out)


if __name__ == '__main__':
    main()
