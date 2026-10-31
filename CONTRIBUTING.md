# Contributing

Issues and pull requests are welcome. Include the operating system, Node/Python versions, exact command, expected result and a minimal reproduction. Do not paste credentials or private production media.

For a change:

1. Create a branch and keep the change focused.
2. Run `npm ci` and `npm run check`.
3. For Python changes, install `requirements.txt` and run `python -m unittest discover -s tests`.
4. For visual changes, render the affected stills and a short clip. Describe what you inspected. Keep generated outputs out of Git except deliberately reviewed documentation previews.
5. Update docs and `ASSETS.md` for new features/assets. Explain any new dependencies and their terms.
6. Stage your changes and run `python scripts/audit_release.py`.

Tests and CI must never make paid AI calls. Prefer offline fixtures and mocked responses. Do not introduce wall-clock animation state or unseeded randomness. Preserve the JavaScript-only first-render path.

Contributions are provided under the repository's MIT license. Only submit material you have the right to contribute. New external media must have clear redistribution rights and attribution. Use discussions/issues to propose large changes before building them.
