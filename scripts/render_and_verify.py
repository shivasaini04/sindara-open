"""Render or reuse video, mux audio to its exact duration, and measure audio offset.

python scripts/render_and_verify.py --video out/explainer.mp4 --audio public/local/demo.wav --out out/final.mp4
python scripts/render_and_verify.py --comp Explainer --audio public/local/demo.wav --out out/final.mp4

Requires ffmpeg/ffprobe on PATH plus requirements.txt. The measured offset compares
the muxed audio with the supplied audio; it does NOT validate visual beat alignment.
"""
import argparse
import json
import shutil
import subprocess
import tempfile
from fractions import Fraction
from pathlib import Path


def run(cmd):
    subprocess.run([str(part) for part in cmd], check=True)


def probe(video):
    result = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(video)], check=True, capture_output=True, text=True)
    info = json.loads(result.stdout)
    stream = next(s for s in info['streams'] if s['codec_type'] == 'video')
    fps = float(Fraction(stream['r_frame_rate']))
    duration = float(stream.get('duration') or info['format']['duration'])
    return duration, fps


def offset_ms(video, audio, directory):
    import numpy as np
    import soundfile as sf
    signals = []
    for name, source in [('mux', video), ('reference', audio)]:
        target = directory / f'{name}.wav'
        run(['ffmpeg', '-v', 'error', '-y', '-i', source, '-t', '40', '-ac', '1', '-ar', '22050', target])
        data, sr = sf.read(target)
        signals.append(data)
    n = min(map(len, signals))
    if n < 2:
        raise ValueError('Audio is empty or too short for offset measurement')
    a, b = [signal[:n] - signal[:n].mean() for signal in signals]
    if min(float(np.dot(a, a)), float(np.dot(b, b))) < 1e-8:
        raise ValueError('Audio is silent; offset cannot be measured')
    correlation = np.fft.irfft(np.fft.rfft(a, 2 * n) * np.conj(np.fft.rfft(b, 2 * n)))
    lag = int(np.argmax(np.abs(correlation)))
    if lag > n:
        lag -= 2 * n
    return lag / sr * 1000


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    source = ap.add_mutually_exclusive_group(required=True)
    source.add_argument('--video', help='Reuse a rendered video (its existing audio is replaced)')
    source.add_argument('--comp', help='Remotion composition to render muted')
    ap.add_argument('--audio', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--concurrency', type=int, default=2)
    a = ap.parse_args()
    for exe in ['ffmpeg', 'ffprobe']:
        if not shutil.which(exe):
            ap.error(f'{exe} must be on PATH')
    output = Path(a.out)
    if not output.name.endswith('.mp4'):
        ap.error('--out must end in .mp4')
    if a.video and output.resolve() == Path(a.video).resolve():
        ap.error('Use different input and output paths')
    if output.resolve() == Path(a.audio).resolve():
        ap.error('Output must not overwrite the audio source')
    output.parent.mkdir(parents=True, exist_ok=True)
    video = Path(a.video) if a.video else output.with_name(output.stem + '_silent.mp4')
    if a.comp:
        npx = shutil.which('npx')
        if not npx:
            ap.error('npx not found; install Node.js')
        run([npx, 'remotion', 'render', 'src/index.ts', a.comp, video, '--muted', f'--concurrency={a.concurrency}', '--pixel-format=yuv420p'])
    duration, fps = probe(video)
    run(['ffmpeg', '-v', 'error', '-y', '-i', video, '-i', a.audio, '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'copy', '-af', 'apad', '-t', duration, '-c:a', 'aac', '-b:a', '320k', '-movflags', '+faststart', output])
    with tempfile.TemporaryDirectory(prefix='sindara-sync-') as tmp:
        offset = offset_ms(output, a.audio, Path(tmp))
    report = {'duration_seconds': duration, 'fps': fps, 'audio_offset_ms': round(offset, 3), 'passed': abs(offset) < 5,
              'scope': 'Muxed audio vs supplied audio, not visual-to-audio synchronization. Audio is padded/trimmed to video duration.'}
    output.with_suffix('.sync.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    if not report['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
