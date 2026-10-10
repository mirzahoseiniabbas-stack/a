import assert from 'node:assert/strict';
import test from 'node:test';
import { marketSession } from './session.mjs';

test('session labels stay stable around the close', () => {
  assert.equal(marketSession(new Date('2026-10-10T09:00:00Z')).phase, 'open');
  assert.equal(marketSession(new Date('2026-10-10T09:01:00Z')).phase, 'closed');
});
