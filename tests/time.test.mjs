import test from 'node:test';
import assert from 'node:assert/strict';
import {keys, progress} from '../src/lib/time.js';

test('timeline clamps before/after its extent, including out-of-order requests', () => {
  const track = [[2, 10], [4, 30], [8, 50]];
  const times = [9, 3, 0, 8, 4, 2];
  assert.deepEqual(times.map((t) => keys(t, track)), [50, 20, 10, 50, 30, 10]);
  assert.deepEqual(times.map((t) => keys(t, track)), [50, 20, 10, 50, 30, 10]);
  assert.equal(progress(1, 2, 4), 0);
  assert.equal(progress(20, 2, 4), 1);
});

test('empty tracks fail explicitly instead of producing a broken frame', () => {
  assert.throws(() => keys(0, []), /at least one/);
});
