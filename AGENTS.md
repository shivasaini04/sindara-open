# Working in Sindara Studio

For video tasks, read `skills/code-video-studio/SKILL.md` and `docs/workflow.md`.

- Run from the repository root. `npm ci`, `npm run doctor`, `npm run check`.
- Make scenes pure functions of frame/time. No `Math.random()`, wall-clock time, timers, or unseeded simulations.
- Create a production with `npm run new -- MyFilm`, then register its composition in `src/Root.tsx`.
- Use real audio/event timestamps. Demo events live in `src/productions/timing.json`.
- Review stills before rendering, then inspect the rendered video and listen to its audio.
- Default demos and checks make no AI calls. Obtain a budget before running optional paid review.
- Never read, print, copy, or commit a user's private keys. `.env.example` documents optional configuration.
- Never add media without recording its source and redistribution terms in `ASSETS.md`.
- Keep outputs in ignored `out/`; private production assets belong in ignored `public/local/`.
- Before committing, run `npm run check`, `python -m unittest discover -s tests`, and `python scripts/audit_release.py`.
