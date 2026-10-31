---
name: code-video-studio
description: Create code-drawn short videos with Sindara Studio and Remotion. Use for launch videos, explainers, kinetic type, narrated stories, motion comics and data films. Plan a timeline, lock the look on stills, build scenes, mix sound, render and review.
---

# Code Video Studio

Read `docs/workflow.md`, `docs/examples.md`, and the repository's `AGENTS.md`.
This skill assumes the full Sindara repository is available; it is not a standalone script bundle.

1. Establish the audience, message, language, duration, aspect ratio and audio source. Use 1080×1920 at 30 fps for a vertical short unless instructed otherwise.
2. Run `npm run doctor`. `npm ci` installs the demo dependencies. Python and AI credentials are optional.
3. Pick a starting point: `launch.tsx` for type and launch graphics, `explainer.tsx` for a step-by-step diagram, `data-pulse.tsx` for a data film.
4. Create a production with `npm run new -- MyFilm`. Fill its `BIBLE.md` with the idea, audience, palette, shots, audio events and sources. Register it in `src/Root.tsx` as printed by the command.
5. Make a shot table with one visual idea per beat. Open on a strong graphic frame, vary framing, and plan the payoff. If there are characters, record the floor plan, camera positions, props and eyelines.
6. Measure audio or use explicit event timestamps. Bind cuts, words and sound to those times. `timing.json` and `demo_audio.py` show a shared event source. Do not label approximate word timings as forced alignment.
7. Lock the look with stills before animation. `npm run stills -- MyFilm 0 120 240`. Inspect each image for hierarchy, legibility, overlaps, continuity, ground contact, cropping and phone UI clearance. View all shots at phone size.
8. Build deterministic scenes as functions of time. Reuse `src/lib/time.js` and `Stage.tsx`. Render changed shots after edits. Use seeded noise; never wall-clock time, unseeded randomness or state that depends on render order.
9. Add a cleared recording or synthesized sound. The optional Python tools provide procedural textures, SFX, cue-based mixing, captions and audio muxing. See `docs/tools.md`.
10. Render, inspect the video, and listen. Run the technical linter. An optional AI review is advice, not proof; request a budget before any paid call and explain that media is uploaded to Google. Use only references the user may upload.
11. Fix observed defects, rerender, and deliver the video, captions when relevant, credits, and known limitations. Never claim a review pass unless that review actually ran.

The demo compositions are small starting points, not complete templates for every genre. Story rigs, lip-sync, forced alignment, AI image/video/music generation and cloud rendering are not included in this initial release. Do not invent commands for them.
