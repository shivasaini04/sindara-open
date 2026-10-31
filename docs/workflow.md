# A repeatable production workflow

## 1. Brief and timeline

Write the audience, message, language, duration, format and sound source in a production `BIBLE.md`. Choose one recurring visual device: a moving chart, stamped labels, a clock, or a sequence of panels.

Give each shot a distinct idea. A sentence is not automatically a visual idea: “the cache is fast” might become a shortcut through a maze. Plan a hook, development and payoff. For dialogue, establish the floor plan, props, eyelines and camera positions before drawing.

Use measured timestamps for recorded speech/music. If you do not have sound yet, use an explicit events list. The demos share `src/productions/timing.json` with the synthesized score. This release does not automatically transcribe or align speech.

## 2. Lock the look on stills

Choose a palette, font treatment, background material and framing. The built-in stage uses SVG paper marks and grid lines; `make_textures.py` can generate richer paper, cloth, grain, newsprint and washi textures.

Render the hook, a wide/diagram shot and a close-up or payoff. View them at phone size. A still should have a focal point, clear hierarchy, intentional overlap and readable words. Keep critical information away from platform UI; inspect the current platform layout rather than assuming a permanent safe-area rule.

For character scenes check ground contact, pose, props, camera logic, levels, eyelines and gestures. Fix composition before spending time on animation. The included starter films are intentionally small examples of timing and structure; they are not a guarantee of professional art direction.

## 3. Build deterministic scenes

Use `useCurrentFrame()` and `useVideoConfig().fps`. Express motion as a function of seconds. Avoid timers, wall-clock state and unseeded randomness: render workers request frames out of order.

The shared `keys()` helper interpolates a time/value track; give it points in strictly increasing time order. `progress()` clamps an interval to 0–1; use a positive duration. Keep camera motion, words and sound events on the same timeline. Vary scale and framing instead of repeatedly showing a centered medium shot.

After changing a shot, render and inspect it at the busiest moment. Check the entry, peak action and exit. Do not judge an entire animation from its opening frame alone.

## 4. Sound

Use your own recording or media you have the rights to use. Run the demo synthesizer for an offline starting point. `sfx.py` makes procedural effects; `mix.py` places them from a cue sheet, ducks music under a voice track and aims for a configurable loudness target.

Mix targets are production choices. Listen for intelligibility, clipped words, clicks, harsh transients, balance and abrupt endings. Analyze the exported file as well as the uncompressed mix. Record asset sources in `ASSETS.md`.

## 5. Render, review, fix

Render stills, then the full video. `qa_lint.py` reports technical failures and heuristic warnings. `render_and_verify.py` measures output audio offset against the supplied track; visual-to-audio timing still needs inspection. The flash heuristic uses whole-frame luminance and cannot certify photosensitivity safety or accessibility compliance.

Review the output at normal speed, frame-step around transitions, and listen. Optional AI review can point out issues but may miss fast events or invent defects. Verify its claims against the frames/audio. Compare against a reference relevant to your style, not a universal score threshold.

## 6. Deliver

Provide the master video, captions when applicable, credits, and known limitations. Keep source and event data so the project can be rerendered. Put transient outputs in `out/` and private assets in `public/local/`; both are ignored by Git.
