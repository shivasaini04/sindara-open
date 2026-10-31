"""Synthesize a 12-second demo score. Python standard library only; no samples or APIs.

python scripts/demo_audio.py --out public/local/demo.wav
Uses the same event timestamps as the Explainer composition.
"""
import argparse
import json
import math
import struct
import wave
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', default='public/local/demo.wav')
    a = ap.parse_args()
    timing = json.loads((Path(__file__).resolve().parents[1] / 'src/productions/timing.json').read_text())
    sample_rate = 48000
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    events = [event['t'] for event in timing['events']]
    pcm = bytearray()
    for i in range(round(timing['duration'] * sample_rate)):
        t = i / sample_rate
        beat = t % 0.5
        note = [220, 261.6256, 329.6276, 391.9954][int(t * 2) % 4]
        sound = 0.12 * math.sin(2 * math.pi * note * t) * math.exp(-beat * 10) * min(1, beat * 400)
        sound += 0.08 * math.sin(2 * math.pi * 110 * t) * (0.7 + 0.3 * math.sin(t))
        for event in events:
            age = t - event
            if 0 <= age < 0.5:
                sound += 0.32 * math.sin(2 * math.pi * (85 * age + 6 * (1 - math.exp(-age * 22)))) * math.exp(-age * 13) * min(1, age * 1000)
        fade = min(1, t / 0.01, (timing['duration'] - t) / 0.2)
        value = max(-32767, min(32767, round(sound * fade * 32767)))
        pcm.extend(struct.pack('<hh', value, value))
    with wave.open(str(out), 'wb') as wav:
        wav.setparams((2, 2, sample_rate, 0, 'NONE', 'not compressed'))
        wav.writeframes(pcm)
    print(out)


if __name__ == '__main__':
    main()
