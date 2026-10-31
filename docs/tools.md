# Production tools

Run commands from the repository root. Python 3.11+ is supported; install `requirements.txt` in a virtual environment for offline tools. Some distributions need libsndfile for SoundFile. FFmpeg and ffprobe must be on PATH for media decoding, muxing, and linting.

### Dependency warning

Remotion 4.0.527 requests Zod 4.5.4. This release overrides its transitive Zod dependency to 4.6.6 to address [GHSA-mrhx-c7xc-m3w5](https://github.com/advisories/GHSA-mrhx-c7xc-m3w5). Remotion's CLI therefore prints a version-mismatch warning. Keep the override: the shipped compositions are checked with it, and removing it reintroduces the advisory. Revisit the override when updating Remotion to a version that requests a patched Zod itself.

## Preview and scaffold

```bash
npm run doctor
npm run new -- MyFilm
npm run stills -- Launch 0 120 240
python scripts/contact_sheet.py out/sheet.jpg "out/stills/*.png" --cols 3
```

The stills command defaults to 0.5 scale. Set `SCALE`, `OUT_DIR`, or `GL` in your shell to override those defaults. It bundles once per batch and cleans its temporary bundle on normal completion or exceptions. It downloads Chrome Headless Shell on first use. An abruptly killed process can leave a temporary bundle behind.

## Procedural textures

```bash
python scripts/make_textures.py --out public/local/tex --style riso
python scripts/make_textures.py --out public/local/cloth --style cloth
```

Styles: `riso`, `cloth`, `grain`, `newsprint`, `washi`. Output has four cycling `ground_*.jpg` and `speck_*.jpg` variants; riso also writes paper layers and halftone masks. Sizes default to 1080×1920 and must be multiples of 8, at least 64. Mount them with Remotion's `Img`/`staticFile` and blend them over your artwork. Texture generation does not modify a composition automatically.

## Sound effects and cue mixing

```bash
python scripts/sfx.py --list
python scripts/sfx.py --out public/local/sfx --only stamp whoosh_m ding
python scripts/mix.py --cues docs/example-mix.json --out public/local/mix.wav
```

The supplied cue sheet works after generating those three SFX. Effects are synthesized from code, without samples. `mix.py` can also mix recorded voices, music, ambience and event-mapped cues. Paths in cue sheets are relative to the current working directory. Named effects choose a variant using `--seed`; specify an exact variant name to pin it.

Music cues accept `at`, `from`, `until`, `gain_db`, `fade_in`, `fade_out` and `duck_db`. Ambience cues can loop; `loop` on music cues is not implemented. Voice/music ducking and mastering use heuristics: listen and inspect the exported result. The limiter targets a conservative oversampled peak ceiling but does not certify platform loudness or encoded true peaks. The final fade avoids a click on loops.

## Audio mux and offset

```bash
python scripts/demo_audio.py
python scripts/render_and_verify.py --comp Explainer --audio public/local/demo.wav --out out/final.mp4
```

Or reuse a rendered file with `--video out/explainer.mp4` instead of `--comp`. Source video is copied without video re-encoding. Audio is encoded to AAC, padded/trimmed to the video duration, and checked by cross-correlation over the first 40 seconds. A measured offset of 5 ms or more fails. Silent audio fails because an offset cannot be measured. A JSON report is written next to the MP4.

**Scope:** this checks muxed audio against the supplied audio. It does not check visual beat alignment, audio drift later in a long film, or whether a mouth shape matches a word. `--comp` renders muted in H.264/yuv420p first.

## Captions

```bash
python scripts/captions.py src/productions/timing.json out/explainer.srt
```

Accepts a JSON list of `{s, e, text}` or an object with a `captions` list. Times are seconds and must satisfy `0 <= s < e`. It preserves supplied timings; it does not transcribe or align speech.

## Video lint

```bash
python scripts/qa_lint.py --video out/final.mp4 --json out/lint.json
python scripts/qa_lint.py --video out/launch.mp4 --allow-silent
```

Default expected format: 1080×1920 at 30 fps; override with `--expect 1920x1080@24`. Intentionally silent video requires `--allow-silent`. The script writes a Markdown report next to the video and exits nonzero for detected failures.

Format and codec checks are concrete. Dark-frame/dropout, pacing, static-hold, texture and flash checks are heuristics originally tuned to short portrait motion graphics. Texture scores favor detailed images; a deliberately clean graphic can receive a warning. The flash check uses whole-frame luminance and misses some local/red flashes. **It is not a WCAG or photosensitivity certification.** Warnings need inspection, not automatic edits. Technical checks are not an artistic quality guarantee.

## Optional AI review

Install `requirements-ai.txt`, copy `.env.example` to `.env`, and supply your own credentials and a model available in your Google account. This tool reads only the `.env` at the root of this repository and environment variables; it does not search parent workspaces.

```bash
python scripts/review.py --kind frame --input out/stills/Launch-0000.png --brief "Graphic launch poster" --estimate-usd 0.10
python scripts/review.py --kind audio --input public/local/demo.wav --brief "Short instrumental cue" --estimate-usd 0.10
python scripts/review.py --kind video --input out/explainer-audio.mp4 --brief "Three-step explainer" --estimate-usd 0.20
```

`--model` overrides `GEMINI_MODEL`. `--reference path/to/your-reference.jpg` adds an image for comparison. Each input must be under 18 MB; compress a review copy for larger videos. Model/media support depends on your selected model. Results are written to `<input>.review.md`. The review provides observations and suggested fixes without an automatic pass score.

**Data disclosure:** input media, reference media and the brief are sent to Google. Use only material you have permission to upload, and check the provider's data-use terms for your account. The tool does not upload anything until explicitly invoked with credentials, a model, and `--estimate-usd`.

`AI_BUDGET_USD` defaults to 5 per UTC calendar month. The ignored `ai_spend.jsonl` ledger reserves your estimate before a request; failed requests remain counted. Reservations are serialized by an exclusive local lock. A crash during ledger reservation can leave `ai_spend.lock`; inspect for active processes before removing it. The ledger uses estimates, does not know current model prices, does not limit output tokens, and cannot enforce actual billing. Set provider-side limits separately if you need a billing cap.

No paid review ran during release validation. Unit tests exercise the local budget checks without network calls.
