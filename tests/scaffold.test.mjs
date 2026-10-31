import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp, mkdir, copyFile, readFile, rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';

test('scaffold fixes nested imports and refuses to overwrite a production', async () => {
  const root = await mkdtemp(path.join(tmpdir(), 'sindara-scaffold-'));
  try {
    await mkdir(path.join(root, 'scripts'));
    await mkdir(path.join(root, 'src/productions'), {recursive: true});
    await copyFile('scripts/new.mjs', path.join(root, 'scripts/new.mjs'));
    await copyFile('src/productions/launch.tsx', path.join(root, 'src/productions/launch.tsx'));
    const script = path.join(root, 'scripts/new.mjs');
    const first = spawnSync(process.execPath, [script, 'MyFilm'], {encoding: 'utf8'});
    assert.equal(first.status, 0, first.stderr);
    const output = path.join(root, 'src/productions/MyFilm/Film.tsx');
    const code = await readFile(output, 'utf8');
    assert.ok(code.includes("from '../../lib/Stage'"));
    assert.ok(code.includes("from '../../lib/time.js'"));
    assert.ok(code.includes('export const MyFilm:'));
    assert.notEqual(spawnSync(process.execPath, [script, 'MyFilm']).status, 0);
    assert.equal(await readFile(output, 'utf8'), code);
    assert.notEqual(spawnSync(process.execPath, [script, '../escape']).status, 0);
  } finally {
    await rm(root, {recursive: true, force: true});
  }
});
