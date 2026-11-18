// Reader format 5 in crux-opencode: the dashboard reads the same document the Claude Code mod reads,
// strictly, and draws the open attempts, the classification count, owner exception and revision through the
// shared core.
import { test, expect } from 'claude-code/testing'
import { bandNode, panelNode, readView } from '../lib/render.ts'
import { parseReader } from '../../crux-mods/hooks/lib/view.ts'
import { cycleRow, doc, plain, rowsOf } from './fixtures/cycles.ts'
import { jsonText } from './fixtures/plain.ts'

const attempt = (over: Record<string, unknown> = {}) => ({
  id: 'build-x', task: 'build-x', role: 'developer', host: 'opencode', attempt: 1, state: 'running', observation: 'running-bound', liveness: 'unknown', unresolved: false, ...over,
})
const reserved = (over: Record<string, unknown> = {}) =>
  attempt({ id: 'lead', task: null, host: null, role: 'dev-lead', state: 'reserved', observation: 'reserved-unbound', unresolved: true, ...over })
const v3Row = (status: string, over: Record<string, unknown> = {}) => ({ ...cycleRow(7, status), schema_version: 3, revision: 4, ...over })

const readOf = (d: unknown) => readView(true, () => ({ ok: true, stdout: jsonText(d) }))
const linesOf = (d: unknown): string[] => {
  const p = readOf(d)
  if (p === null || !p.ok) throw new Error('the document did not read as a view')
  return rowsOf(panelNode(p, 'crux-dashboard', 100, 0)).map(plain)
}

test('formats 2 and 4 read as a format mismatch and format 5 reads', () => {
  // The core names the mismatch; the kept envelope shows any refused document as reader-output-invalid.
  expect(parseReader(jsonText({ ...doc([cycleRow(1)]), format_version: 2 }))).toEqual({ ok: false, code: 'reader-format-mismatch' })
  expect(readOf({ ...doc([cycleRow(1)]), format_version: 2 })?.ok).toBe(false)
  expect(parseReader(jsonText({ ...doc([cycleRow(1)]), format_version: 4 }))).toEqual({ ok: false, code: 'reader-format-mismatch' })
  expect(readOf(doc([cycleRow(1)]))?.ok).toBe(true)
})

test('each new key is read strictly', () => {
  const bad: Record<string, unknown>[] = [
    { assignments: [attempt({ liveness: 'running' })] },
    { assignments: [attempt({ state: 'finished' })] },
    { assignments: [attempt({ observation: 'delivered' })] },
    { assignments: [attempt({ extra: 1 })] },
    { classifications: [] },
    { classification_count: -1 },
    { classification_count: '1' },
    { exception: 'x'.repeat(301) },
    { revision: -1 },
    { schema_version: 4 },
  ]
  for (const over of bad) expect([over, readOf(doc([{ ...cycleRow(1), ...over }]))]).toEqual([over, { ok: false, code: 'reader-output-invalid' }])
})

test('an open cycle draws its open attempts with unknown liveness and an unresolved mark', () => {
  const text = linesOf(doc([v3Row('active', { assignments: [attempt(), reserved()] })])).join('\n')
  expect(text).toContain('build-x developer attempt 1 running on opencode (running-bound, liveness unknown)')
  expect(text).toContain('lead dev-lead attempt 1 reserved (reserved-unbound, liveness unknown)')
  expect(text).toContain('Unresolved dispatch: lead')
  expect(text.includes('Unresolved dispatch: build-x')).toBe(false)
  expect(text).toContain('revision 4')
})

test('a closed cycle with open attempts draws none of them', () => {
  const text = linesOf(doc([v3Row('completed', { assignments: [attempt({ id: 'left-over' })] })])).join('\n')
  expect(text.includes('left-over')).toBe(false)
  expect(text).toContain('revision 4')
})

test('the classification count and the owner exception draw only when present', () => {
  const text = linesOf(doc([v3Row('active', { classification_count: 1, exception: 'Owner approved' })])).join('\n')
  expect(text).toContain('Classifications: 1')
  expect(text).toContain('Owner exception: Owner approved')
  const bare = linesOf(doc([cycleRow(1, 'active')])).join('\n')
  for (const absent of ['Classification', 'Owner exception', 'revision', 'attempt']) expect(bare.includes(absent)).toBe(false)
})

test('25 classifications draw as one count line and no detail', () => {
  const lines = linesOf(doc([v3Row('active', { classification_count: 25 })]))
  const counted = lines.filter(l => l.includes('Classification'))
  expect(counted.length).toBe(1)
  expect(counted[0]).toContain('Classifications: 25')
  for (const detail of ['work-sizing', 'fell back', 'cost', 'provider']) expect(lines.join('\n').includes(detail)).toBe(false)
})

test('a shortcut cycle reads and draws as closed work, with its queue item as finished', () => {
  const queue = {
    ok: true, authorization: null,
    items: [{ id: 'Q-0001', title: 'Short item', state: 'started', suggested_type: 'iterate', cycle: 'CYC-0007', cycle_status: 'shortcut' }],
  }
  const text = linesOf(doc([v3Row('shortcut', { phase: 'reflect' })], queue)).join('\n')
  expect(text).toContain('\u2713 shortcut')
  expect(text).toContain('\u2713 Q-0001 CYC-0007 shortcut')
  // Positive control: the same row as an active cycle draws no closed row.
  expect(linesOf(doc([v3Row('active')])).join('\n').includes('shortcut')).toBe(false)
})

// The row cycle.py status --json prints for a crux.cycle.v1 record of kind release: a pilot row whose fixed
// beta step list is its task list.
const betaSteps = [
  ['prep', 'Prepare the release: bump the versions'],
  ['prepare', 'Bind this cycle to the beta target'],
  ['verify', 'Run release.py verify: freeze the artifact'],
  ['beta-and-smoke', 'Publish the untagged beta'],
  ['tag', 'Tag the beta and create its release'],
  ['record', 'Copy the ledger into this cycle'],
] as const
const releaseRow = (status: string, taskStatus: string, reflection: string) => ({
  ...cycleRow(1, status), schema_version: 'crux.cycle.v1', revision: 7, type: 'pilot', title: 'Release 9.9.9',
  phase: status === 'completed' ? 'completed' : 'working', pass: 1, pass_limit: 1,
  phases: ['planning', 'working', 'reviewing', 'reviewed', 'completed'],
  tasks: betaSteps.map(([id, text]) => ({ id, phase: 'working', description: `${text} [lead-a run 0]`, status: taskStatus })),
  reflection, phase_times: [], basis: 'derived',
})

test('a crux.cycle.v1 release record reads and draws its six fixed steps and its delivery facts', () => {
  const open = linesOf(doc([releaseRow('active', 'pending', 'Delivery, recorded separately: PR: none; CI: unknown; merge: unmerged')])).join('\n')
  for (const [, text] of betaSteps) expect(open).toContain(text)
  expect(open).toContain('CYC-0001')
  expect(open).toContain('0/6')
  // A current record draws its steps and no type label or pass count.
  expect(open.includes('pilot')).toBe(false)
  expect(open).toContain('✓ planning › ▸ working › ◌ reviewing › ◌ reviewed › ◌ completed')
  expect(/pass \d/.test(open)).toBe(false)
  // The band states the status once, in the current step, and draws a glyph per step.
  const opened = readOf(doc([releaseRow('active', 'pending', 'x')]))
  expect(rowsOf(bandNode(opened, 100)).map(plain)[0]).toContain('CYC-0001  ✓ ▸ working ◌ ◌ ◌  0/6 tasks')
  const finished = readOf(doc([releaseRow('completed', 'done', 'x')]))
  expect(rowsOf(bandNode(finished, 100)).map(plain)[0]).toContain('CYC-0001  ✓ ✓ ✓ ✓ ✓ completed  6/6 tasks')
  const done = linesOf(doc([releaseRow('completed', 'done', 'Completed. Delivery, recorded separately: PR: none; CI: unknown; merge: unmerged')])).join('\n')
  expect(done).toContain('6/6')
  expect(done).toContain('Completed. Delivery, recorded separately')
  // Positive control: a string format the pilot rule does not know refuses the document.
  expect(readOf(doc([{ ...releaseRow('active', 'pending', 'x'), schema_version: 'crux.cycle.v2' }]))?.ok).toBe(false)
})
