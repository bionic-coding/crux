// The step line of a current-format cycle record in crux-omp: the card draws every step through the
// shared track and its width fallbacks, and the band states the status once and shows the steps.
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { panelLines, readView } from '../lib/render.ts'
import { buildOmpBandLine } from '../lib/live.ts'
import type { Line } from '../../crux-mods/hooks/lib/draw.ts'
import { jsonText } from './fixtures/plain.ts'

const STEPS = ['planning', 'working', 'reviewing', 'reviewed', 'completed']
const closed = (status: string) => status === 'completed' || status === 'abandoned'
const current = (status: string, phase: string, done: number, total: number, over: Record<string, unknown> = {}) => ({
  id: 'CYC-0194', schema_version: 'crux.cycle.v1', revision: 4, assignments: [], classification_count: 0, exception: null,
  title: 'Restore the step line', type: 'pilot', status, phase, pass: 1, pass_limit: 1, phases: STEPS,
  tasks: Array.from({ length: total }, (_, i) => ({ id: `t${i}`, phase: 'working', description: `Task ${i}`, status: i < done ? 'done' : 'pending' })),
  returns: [], waits: [], blocker: status === 'paused' ? 'Owner decision needed' : null, reflection: null, modified_s: 1780000000,
  started_s: 1779999000, ended_s: closed(status) ? 1779999900 : null, paused_s: 0,
  open_started_s: closed(status) ? null : 1779999000, basis: 'derived', phase_times: [], ...over,
})
const doc = (cycles: unknown[]) => ({ format: 'crux.cycle-progress', format_version: 5, ok: true, docs_dir: 'bionic', now_s: 1780000000, cycles })
const parsed = (c: unknown) => {
  const p = readView(() => ({ ok: true, stdout: jsonText(doc([c])) }))
  assert.ok(p !== null && p.ok && p.view.cycles !== undefined, 'the document did not read as a view')
  return p
}
const plain = (l: Line) => l.map(s => s.text).join('')
const cardOf = (c: unknown, width: number) => panelLines(parsed(c), width)!.join('\n')
const bandOf = (c: unknown) => {
  const p = parsed(c)
  assert.ok(p.ok && p.view.cycles !== undefined)
  return plain(buildOmpBandLine(p.view.cycles, 1780000000, undefined, 120)!)
}

const OPEN: [string, string, string, number, number, string][] = [
  ['planning', 'active', 'planning', 0, 0, '▸ planning › ◌ working › ◌ reviewing › ◌ reviewed › ◌ completed'],
  ['working', 'active', 'working', 0, 2, '✓ planning › ▸ working › ◌ reviewing › ◌ reviewed › ◌ completed'],
  ['reviewing', 'active', 'reviewing', 2, 2, '✓ planning › ✓ working › ▸ reviewing › ◌ reviewed › ◌ completed'],
  ['reviewed', 'reviewed', 'reviewed', 2, 2, '✓ planning › ✓ working › ✓ reviewing › ✓ reviewed › ◌ completed'],
  ['paused', 'paused', 'reviewing', 2, 2, '✓ planning › ✓ working › ⊘ reviewing › ◌ reviewed › ◌ completed'],
]

test('an open current cycle card draws every step at full width and the compact line when narrow', () => {
  const compact: Record<string, string> = {
    planning: '▸ planning ◌ ◌ ◌ ◌', working: '✓ ▸ working ◌ ◌ ◌', reviewing: '✓ ✓ ▸ reviewing ◌ ◌', reviewed: '✓ ✓ ✓ ✓ reviewed ◌', paused: '✓ ✓ ⊘ reviewing ◌ ◌',
  }
  for (const [name, status, step, done, total, full] of OPEN) {
    const c = current(status, step, done, total)
    assert.ok(cardOf(c, 120).includes(full), `${name} at 120: ${cardOf(c, 120)}`)
    assert.ok(cardOf(c, 60).includes(compact[name]!), `${name} at 60: ${cardOf(c, 60)}`)
    // A current record draws its task count with no progress bar, as the shared pane does.
    if (total > 0) assert.ok(cardOf(c, 120).includes(`${done}/${total} tasks`), name)
    for (const absent of ['▮', '▯', 'pilot', 'pass ']) assert.ok(!cardOf(c, 120).includes(absent), `${name}: ${absent}`)
  }
})

test('the OMP band states a current cycle status once and shows its steps', () => {
  const want: Record<string, string> = {
    planning: 'CYC-0194 ▸ planning ◌ ◌ ◌ ◌ (0/0)',
    working: 'CYC-0194 ✓ ▸ working ◌ ◌ ◌ (0/2)',
    reviewing: 'CYC-0194 ✓ ✓ ▸ reviewing ◌ ◌ (2/2)',
    reviewed: 'CYC-0194 ✓ ✓ ✓ ✓ reviewed ◌ (2/2)',
    paused: 'CYC-0194 ✓ ✓ ⊘ reviewing ◌ ◌ paused (2/2)  │  ! blocked: Owner decision needed',
  }
  for (const [name, status, step, done, total] of OPEN) assert.equal(bandOf(current(status, step, done, total)), want[name], name)
  // The owner's example, CYC-0193 completed with one task of one, and an abandoned cycle.
  assert.equal(bandOf(current('completed', 'completed', 1, 1, { id: 'CYC-0193' })), 'CYC-0193 ✓ ✓ ✓ ✓ ✓ completed (1/1)')
  assert.equal(bandOf(current('abandoned', 'working', 1, 2)), 'CYC-0194 ✓ ✗ working ◌ ◌ ◌ abandoned (1/2)')
})

test('with no open cycle the OMP card names the latest current cycle by its own status', () => {
  assert.match(cardOf(current('abandoned', 'working', 1, 2), 120), /last abandoned: CYC-0194/)
  assert.match(cardOf(current('completed', 'completed', 1, 1), 120), /last completed: CYC-0194/)
})

test('a historical cycle keeps its OMP band and card', () => {
  const legacy = {
    ...current('active', 'build', 0, 1), schema_version: 3, type: 'dev', phase: 'build', pass: 1, pass_limit: 2,
    phases: ['plan', 'build', 'test', 'review', 'reflect'], tasks: [{ id: 'a', phase: 'build', description: 'Work', status: 'active' }], basis: 'recorded',
  }
  assert.equal(bandOf(legacy), '▸ CYC-0194 dev · build (0/1)  │  ▸ Work')
  assert.match(cardOf(legacy, 120), /\[dev · ↻ pass 1\/2\]/)
  assert.match(cardOf(legacy, 120), /✓ plan › ▸ build › ◌ test › ◌ review › ◌ reflect/)
  assert.match(cardOf(legacy, 120), /▯/)
})
