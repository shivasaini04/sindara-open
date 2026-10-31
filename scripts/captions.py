"""Write SRT from a JSON list of {s, e, text}, or a timing.json with a captions list."""
import argparse
import json
from pathlib import Path


def timestamp(seconds):
    millis = max(0, round(float(seconds) * 1000))
    hours, millis = divmod(millis, 3600000)
    minutes, millis = divmod(millis, 60000)
    seconds, millis = divmod(millis, 1000)
    return f'{hours:02}:{minutes:02}:{seconds:02},{millis:03}'


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('input')
    ap.add_argument('output')
    a = ap.parse_args()
    data = json.loads(Path(a.input).read_text(encoding='utf-8'))
    lines = data['captions'] if isinstance(data, dict) else data
    rows = []
    for i, line in enumerate(lines, 1):
        if line['s'] < 0 or line['e'] <= line['s']:
            raise ValueError(f'Caption {i}: expected 0 <= s < e')
        rows.append(f"{i}\n{timestamp(line['s'])} --> {timestamp(line['e'])}\n{line['text']}\n")
    out = Path(a.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text('\n'.join(rows), encoding='utf-8')
    print(out)


if __name__ == '__main__':
    main()
