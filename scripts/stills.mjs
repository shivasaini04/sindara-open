// One bundle per batch, cleaned even on failure. No shell-specific env syntax required.
import {mkdir, rm} from 'node:fs/promises';
import path from 'node:path';
import {bundle} from '@remotion/bundler';
import {renderStill, selectComposition} from '@remotion/renderer';

const [id, ...requested] = process.argv.slice(2);
const frames = requested.length ? requested.map(Number) : [0, 120, 240];
if (!id || frames.some((f) => !Number.isInteger(f) || f < 0)) {
  console.error('Usage: npm run stills -- Launch [0 120 240]');
  process.exit(1);
}
const directory = path.resolve(process.env.OUT_DIR ?? 'out/stills');
await mkdir(directory, {recursive: true});
const serveUrl = await bundle({entryPoint: path.resolve('src/index.ts')});
try {
  const chromiumOptions = {gl: process.env.GL ?? 'swangle'};
  const composition = await selectComposition({serveUrl, id, chromiumOptions});
  for (const frame of frames) {
    const output = path.join(directory, `${id}-${String(frame).padStart(4, '0')}.png`);
    await renderStill({serveUrl, composition, frame, output, scale: Number(process.env.SCALE ?? 0.5), chromiumOptions});
    console.log(output);
  }
} finally {
  await rm(serveUrl, {recursive: true, force: true});
}
