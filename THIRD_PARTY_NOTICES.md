# Third-party dependencies

The MIT license applies to Sindara's original code and documentation. Dependencies are installed from their registries and retain their own licenses. This file summarizes the direct dependencies; their distributed license texts remain authoritative.

| Dependency | Purpose | License/source |
| --- | --- | --- |
| Remotion and `@remotion/*` | Studio, bundling and video rendering | [Remotion license](https://github.com/remotion-dev/remotion/blob/main/LICENSE.md), not MIT; free-use eligibility and company requirements apply |
| React, React DOM | UI and scene components | [MIT](https://github.com/facebook/react/blob/main/LICENSE) |
| TypeScript | Static type checking | [Apache-2.0](https://github.com/microsoft/TypeScript/blob/main/LICENSE.txt) |
| React type declarations | React typings | [DefinitelyTyped MIT](https://github.com/DefinitelyTyped/DefinitelyTyped/blob/master/LICENSE) |
| Zod (transitive override) | Remotion schema validation | [MIT](https://github.com/colinhacks/zod/blob/main/LICENSE); pinned to 4.6.6 to address GHSA-mrhx-c7xc-m3w5 |
| NumPy | Numerical/audio/image processing | [BSD-3-Clause](https://github.com/numpy/numpy/blob/main/LICENSE.txt) |
| SciPy | Filters and numerical processing | [BSD-3-Clause](https://github.com/scipy/scipy/blob/main/LICENSE.txt) |
| Pillow | Image processing | [HPND-style Pillow license](https://github.com/python-pillow/Pillow/blob/main/LICENSE) |
| SoundFile | WAV decoding/writing | [BSD-3-Clause](https://github.com/bastibe/python-soundfile/blob/master/LICENSE); libsndfile has separate terms |
| pyloudnorm | Loudness measurement | [MIT](https://github.com/csteinmetz1/pyloudnorm/blob/master/LICENSE) |
| Pedalboard | Audio processing | [GPL-3.0](https://github.com/spotify/pedalboard/blob/master/LICENSE) |
| Google Gen AI SDK (optional) | User-invoked remote review | [Apache-2.0](https://github.com/googleapis/python-genai/blob/main/LICENSE); service usage has separate terms |

Pedalboard is an optional separately installed GPL dependency used by `sfx.py` and `mix.py`. Those scripts import it at runtime; its inclusion is not a grant to relicense Pedalboard. If you distribute a combined application or binary, review and satisfy the applicable dependency terms, including GPL obligations. Sindara's source license does not waive them.

FFmpeg/ffprobe and Chromium are external tools. Their binaries are not checked into this repository. Remotion may install/download platform-specific tools, which carry their own license notices. Review the tools' distribution terms if packaging a runtime yourself.

No Remotion implementation code is vendored or relicensed here. The starter compositions use its public API.
