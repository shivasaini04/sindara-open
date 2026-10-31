import {mkdir, readFile, writeFile} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const name = process.argv[2];
if (!name || !/^[A-Z][A-Za-z0-9]*$/.test(name)) {
  console.error('Usage: npm run new -- MyFilm (letters/numbers, start with an uppercase letter)');
  process.exit(1);
}
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const target = path.join(root, 'src/productions', name);
// A new folder per production; never overwrite an existing project.
await mkdir(target);
let code = await readFile(path.join(root, 'src/productions/launch.tsx'), 'utf8');
code = code.replaceAll("'../lib/", "'../../lib/").replace('export const Launch:', `export const ${name}:`);
await writeFile(path.join(target, 'Film.tsx'), code);
await writeFile(path.join(target, 'BIBLE.md'), `# ${name}\n\nAudience:\nOne-sentence idea:\nLook and palette:\nAudio source and rights:\n\n| Time | Idea | Framing | Sound/event |\n| --- | --- | --- | --- |\n| 0–4s | Hook | Extreme close-up or oversized type | |\n| 4–8s | Development | Diagram or wide | |\n| 8–12s | Payoff | Type or close-up | |\n\nReview stills for readability, overlap, framing, continuity and ground contact.\n`);
console.log(`Created src/productions/${name}/Film.tsx and BIBLE.md.\nAdd to src/Root.tsx:\nimport {${name}} from './productions/${name}/Film';\n<Composition id="${name}" component={${name}} durationInFrames={360} fps={30} width={1080} height={1920} />`);
