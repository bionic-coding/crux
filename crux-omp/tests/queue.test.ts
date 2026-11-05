import { test } from 'node:test'
import assert from 'node:assert/strict'
import { commandQueue, queueMode } from '../lib/command.ts'
import { panelLines } from '../lib/render.ts'
import { queueParsed } from './fixtures/queue.ts'
import { queueExpanded } from '../../crux-mods/hooks/lib/queue.ts'

test('OMP shares six-row queue rendering and exposes all IDs through explicit expansion', () => {
  for (const count of [0, 1, 6, 7, 14, 51, 500]) {
    const parsed = queueParsed(count)
    const collapsed = panelLines(parsed, 60) ?? []
    assert.equal(collapsed.filter(row => row.includes('◌ Q-')).length, Math.min(count, 6))
    if (count > 6) {
      assert.equal(collapsed.some(row => row.includes(`+${count - 6} more`)), true)
      assert.equal(collapsed.includes('Queue: /crux-dashboard queue'), true)
      const expanded = panelLines(parsed, 60, undefined, undefined, 0, true) ?? []
      assert.equal(expanded.some(row => row.includes('Show less')), true)
      for (let n = 1; n <= count; n++) assert.equal(expanded.some(row => row.includes(`Q-${String(n).padStart(4, '0')} `)), true)
    }
    for (const width of [1, 20, 30, 40, 60]) {
      for (const row of panelLines(parsed, width, undefined, undefined, 0, true) ?? []) assert.ok(row.length <= width)
    }
  }
})

test('OMP command fallback is explicit, root-bound and independent of prompt or terminal input', () => {
  assert.equal(queueMode('queue'), 'toggle')
  assert.equal(queueMode(' queue EXPAND '), 'expand')
  assert.equal(queueMode('queue collapse'), 'collapse')
  for (const text of ['', 'next', 'q', 'expand', 'queue wrong']) assert.equal(queueMode(text), null)
  const expanded = commandQueue(queueParsed(14), null, '/one', 'expand')!
  assert.equal(queueExpanded(expanded, '/one'), true)
  assert.equal(commandQueue(queueParsed(14), expanded, '/one', 'expand'), null)
  assert.equal(queueExpanded(expanded, '/two'), false)
  assert.equal(queueExpanded(expanded, '/one'), true)
  const collapsed = commandQueue(queueParsed(51), expanded, '/one', 'collapse')!
  assert.equal(queueExpanded(collapsed, '/one'), false)
  assert.equal(commandQueue(queueParsed(6), expanded, '/one', 'toggle'), null)
})
