import assert from 'node:assert/strict';
import test from 'node:test';
import { add } from './index.mjs';

test('reusable Node smoke: valid values', () => {
  assert.equal(add(2, 3), 5);
  assert.equal(add(-3, 3), 0);
});

test('reusable Node smoke: rejects invalid arguments', () => {
  assert.throws(() => add(Number.NaN, 2), TypeError);
});
