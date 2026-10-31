import {existsSync} from 'node:fs';
import {spawnSync} from 'node:child_process';

let failed = false;
function check(label, ok, fix) {
  console.log(`${ok ? 'OK' : 'MISSING'} ${label}${ok ? '' : ` — ${fix}`}`);
  failed ||= !ok;
}
check('Node.js 22+', Number(process.versions.node.split('.')[0]) >= 22, 'use Node.js 22 or newer');
check('Remotion dependencies', existsSync('node_modules/remotion'), 'run npm ci');
check('entry point', existsSync('src/index.ts'), 'run this command from the repository root');
console.log('\nOptional tools (not needed for npm run render):');
for (const tool of ['python3', 'python', 'ffmpeg', 'ffprobe']) {
  const result = spawnSync(tool, [tool.startsWith('python') ? '--version' : '-version'], {stdio: 'ignore'});
  console.log(`${result.status === 0 ? 'FOUND' : 'ABSENT'} ${tool}`);
}
console.log('\nThe first render downloads Chrome Headless Shell if needed. AI keys are optional.');
process.exitCode = failed ? 1 : 0;
