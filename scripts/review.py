"""Optional paid Gemini review. No calls without an explicit model and cost estimate.

python scripts/review.py --kind frame --input out/stills/Launch-0000.png --brief "Launch poster" --estimate-usd 0.10

Loads only this repository's .env, never parent/workspace files. Input media and
brief are sent to Google. The ledger records estimates, NOT provider billing.
"""
import argparse
import datetime as dt
import json
import math
import mimetypes
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROMPTS = {
    'frame': 'Review this animation frame for hierarchy, readable type, composition, intended action, ground contact, eyelines, overlaps and continuity. Treat the supplied style as intentional. Do not penalize missing characters or texture when irrelevant.',
    'audio': 'Review this soundtrack for intelligibility, clicks, distortion, balance, abrupt edits and pacing. Use timestamps. Separate observations from taste.',
    'video': 'Review this short film for readability, timing, continuity, camera logic and audio balance. Use timestamps, state uncertainty, and avoid inferring unseen frames.',
}


def load_env():
    env = ROOT / '.env'
    if env.is_file():
        for raw in env.read_text(encoding='utf-8').splitlines():
            line = raw.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key.strip(), value.strip().strip('\"').strip("'"))


def reserve(ledger, estimate, budget):
    if not all(math.isfinite(v) and v > 0 for v in [estimate, budget]):
        raise ValueError('Budget and estimate must be finite, positive amounts')
    month = dt.datetime.now(dt.timezone.utc).strftime('%Y-%m')
    # Exclusive create prevents simultaneous local calls from racing the ledger.
    lock = ledger.with_suffix('.lock')
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise ValueError('Another review is reserving budget; retry later. If a process crashed, inspect ai_spend.lock.') from None
    try:
        os.close(descriptor)
        rows = [json.loads(line) for line in ledger.read_text(encoding='utf-8').splitlines()] if ledger.exists() else []
        spent = sum(row['estimate_usd'] for row in rows if row['time'].startswith(month))
        if spent + estimate > budget:
            raise ValueError(f'Monthly estimate budget exceeded: ${spent:.2f} + ${estimate:.2f} > ${budget:.2f}')
        row = {'time': dt.datetime.now(dt.timezone.utc).isoformat(), 'estimate_usd': estimate}
        with ledger.open('a', encoding='utf-8') as file:
            file.write(json.dumps(row) + '\n')
    finally:
        lock.unlink()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--kind', choices=PROMPTS, required=True)
    ap.add_argument('--input', required=True)
    ap.add_argument('--reference', help='Optional reference image you have permission to upload')
    ap.add_argument('--brief', default='')
    ap.add_argument('--model', help='Overrides GEMINI_MODEL')
    ap.add_argument('--estimate-usd', type=float, required=True, help='Conservative estimate for this call; not an actual price quote')
    a = ap.parse_args()
    load_env()
    model = a.model or os.environ.get('GEMINI_MODEL')
    key = os.environ.get('GEMINI_API_KEY')
    if not key or not model:
        ap.error('Set GEMINI_API_KEY and GEMINI_MODEL in .env, or supply --model')
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        ap.error('Install requirements-ai.txt first')
    parts = []
    for name in [a.reference, a.input]:
        if name:
            path = Path(name)
            mime = mimetypes.guess_type(path.name)[0]
            expected = 'image/' if name == a.reference or a.kind == 'frame' else a.kind + '/'
            if not mime or not mime.startswith(expected):
                ap.error(f'{path.name}: expected {expected} media')
            if path.stat().st_size > 18_000_000:
                ap.error('Each media file must be under 18 MB; supply a compressed review copy')
            parts.append(types.Part.from_bytes(data=path.read_bytes(), mime_type=mime))
    prompt = PROMPTS[a.kind] + '\nBrief: ' + a.brief
    if a.reference:
        prompt += '\nFirst media is a reference image; last media is the candidate. Compare craft in the candidate style; do not claim an objective quality score.'
    prompt += '\nReturn a concise review: observable issues, uncertainty, and three concrete fixes. This is advice for a human reviewer.'
    try:
        budget = float(os.environ.get('AI_BUDGET_USD', '5'))
        reserve(ROOT / 'ai_spend.jsonl', a.estimate_usd, budget)
    except (ValueError, OSError) as error:
        ap.error(str(error))
    # Reserve before the request; failed attempts remain counted conservatively.
    with genai.Client(api_key=key, http_options={'timeout': 120000}) as client:
        response = client.models.generate_content(model=model, contents=[*parts, prompt])
    out = Path(a.input + '.review.md')
    if not response.text:
        raise SystemExit('Provider returned no review text; estimate remains reserved')
    out.write_text(f'# {a.kind} review\n\nModel: {model}. AI advice; verify findings yourself.\n\n{response.text}\n', encoding='utf-8')
    print(out)


if __name__ == '__main__':
    main()
