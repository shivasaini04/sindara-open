# Starter films

Each example is 12 seconds at 30 fps, portrait 1080×1920. They render without external assets, API keys or Python. They intentionally start silent. Source artwork and synthetic data are covered by the repository's MIT license.

## Launch: kinetic type

`src/productions/launch.tsx` has three four-second shots: an oversized idea poster, a dark rhythmic type panel, and a tilted closing stamp. Edit the text, named palette and SVG geometry. The `title` prop controls the closing line; very long text needs manual layout adjustment.

```bash
npm run render
npm run stills -- Launch 0 45 120 165 240 285
```

Use `npm run new -- MyFilm` to copy this into a separate folder. The command prints registration instructions rather than rewriting the shared root file. Change duration in the composition registration and update scene cuts accordingly.

## Explainer: one clock

`src/productions/explainer.tsx` reads the event times from `timing.json`. Three cards enter at 0, 4 and 8 seconds. The Python demo score reads the same JSON and places sound hits at those times. This is a minimal example of sharing timing between visuals and sound.

```bash
npm run render:explainer
python scripts/demo_audio.py
python scripts/render_and_verify.py --video out/explainer.mp4 --audio public/local/demo.wav --out out/explainer-audio.mp4
python scripts/captions.py src/productions/timing.json out/explainer.srt
```

Install the optional Python requirements and FFmpeg first for mux verification. Captions describe the steps; the soundtrack has no spoken narration.

## DataPulse: synthetic weekly activity

`src/productions/data-pulse.tsx` animates a count-up and seven bars from `data.json`. The visible label explicitly calls the data synthetic. It describes a fictional community and must not be presented as real usage.

```bash
npm run render:data
npm run stills -- DataPulse 0 90 210 330
```

For a real dataset, replace the JSON, update the on-screen labels/source, and document its license. Adjust the fixed seven-bar layout for a different number of categories. The starter is not a general charting library.
