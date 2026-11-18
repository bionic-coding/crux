// Reader format 5 in crux-omp: the extension reads the document strictly through the shared core and
// its cycle cards draw the open attempts, the classification count, owner exception and revision.
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { blockLines, panelLines, readView } from '../lib/render.ts'
import { buildOmpCyclesPane } from '../lib/live.ts'
import type { LiveRuntimeSnapshot } from '../lib/live.ts'
import { STATE_GLYPHS } from '../../crux-mods/hooks/lib/draw.ts'
import { parseReader } from '../../crux-mods/hooks/lib/view.ts'
import { jsonText } from './fixtures/plain.ts'

const row = (status: string, over: Record<string, unknown> = {}) => ({
  id: 'CYC-0007', schema_version: 3, revision: 4, assignments: [], classification_count: 0, exception: null,
  title: 'A cycle', type: 'dev', status, phase: 'build', pass: 1, pass_limit: 2,
  phases: ['plan', 'build', 'test', 'review', 'reflect'],
  tasks: [{ id: 'a', phase: 'build', description: 'Work', status: status === 'active' ? 'active' : 'done' }],
  returns: [], waits: [], blocker: null, reflection: null, modified_s: 1780000000, started_s: 1779999000,
  ended_s: status === 'active' || status === 'paused' ? null : 1779999900, paused_s: 0,
  open_started_s: status === 'active' || status === 'paused' ? 1779999500 : null, basis: 'recorded',
  phase_times: [{ phase: 'build', active_s: 500, paused_s: 0 }], ...over,
})
const doc = (cycles: unknown[], over: Record<string, unknown> = {}) => ({
  format: 'crux.cycle-progress', format_version: 5, ok: true, docs_dir: 'bionic', now_s: 1780000000, cycles, ...over,
})
const attempt = (over: Record<string, unknown> = {}) => ({
  id: 'build-x', task: 'build-x', role: 'developer', host: 'omp', attempt: 1, state: 'running', observation: 'running-bound', liveness: 'unknown', unresolved: false, ...over,
})
const reserved = (over: Record<string, unknown> = {}) =>
  attempt({ id: 'lead', task: null, host: null, role: 'dev-lead', state: 'reserved', observation: 'reserved-unbound', unresolved: true, ...over })

const readOf = (d: unknown) => readView(() => ({ ok: true, stdout: jsonText(d) }))
const textOf = (d: unknown): string => {
  const p = readOf(d)
  assert.ok(p !== null && p.ok, 'the document did not read as a view')
  const lines = panelLines(p, 120)
  assert.ok(lines !== null)
  return lines.join('\n')
}

test('formats 2 and 4 are a format mismatch and format 5 reads', () => {
  assert.deepEqual(parseReader(jsonText(doc([row('active')], { format_version: 2 }))), { ok: false, code: 'reader-format-mismatch' })
  assert.equal(readOf(doc([row('active')], { format_version: 2 }))?.ok, false)
  assert.deepEqual(parseReader(jsonText(doc([row('active')], { format_version: 4 }))), { ok: false, code: 'reader-format-mismatch' })
  assert.equal(readOf(doc([row('active')]))?.ok, true)
})

test('each new key is read strictly', () => {
  const bad: Record<string, unknown>[] = [
    { assignments: [attempt({ liveness: 'stalled' })] },
    { assignments: [attempt({ state: 'lost' })] },
    { assignments: [attempt({ unresolved: 1 })] },
    { classifications: [] },
    { classification_count: -1 },
    { classification_count: 2.5 },
    { exception: 7 },
    { revision: 1.5 },
    { schema_version: 0 },
  ]
  for (const over of bad) assert.equal(readOf(doc([row('active', over)]))?.ok, false, JSON.stringify(over))
})

test('an open cycle card draws open attempts with unknown liveness and the unresolved mark', () => {
  const text = textOf(doc([row('active', { assignments: [attempt(), reserved()] })]))
  assert.match(text, /build-x developer attempt 1 running on omp \(running-bound, liveness unknown\)/)
  assert.match(text, /lead dev-lead attempt 1 reserved \(reserved-unbound, liveness unknown\)/)
  assert.match(text, /Unresolved dispatch: lead/)
  assert.doesNotMatch(text, /Unresolved dispatch: build-x/)
  assert.match(text, /revision 4/)
})

test('a paused cycle draws its open attempts', () => {
  assert.match(textOf(doc([row('paused', { assignments: [attempt()] })])), /build-x developer attempt 1 running/)
})

test('a closed cycle with open attempts draws none of them', () => {
  const text = textOf(doc([row('completed', { assignments: [attempt({ id: 'left-over' })] })]))
  assert.doesNotMatch(text, /left-over/)
  assert.match(text, /revision 4/)
})

test('the classification count and the owner exception draw only when present', () => {
  const text = textOf(doc([row('active', { classification_count: 1, exception: 'Owner approved' })]))
  assert.match(text, /Classifications: 1/)
  assert.match(text, /Owner exception: Owner approved/)
  const bare = textOf(doc([row('active', { revision: null, schema_version: 2 })]))
  for (const absent of [/Classification/, /Owner exception/, /revision/, /attempt/]) assert.doesNotMatch(bare, absent)
})

test('25 classifications draw as one count line and no detail', () => {
  const text = textOf(doc([row('active', { classification_count: 25 })]))
  assert.equal(text.split('\n').filter(l => l.includes('Classification')).length, 1)
  assert.match(text, /Classifications: 25/)
  for (const detail of [/work-sizing/, /fell back/, /cost/, /provider/]) assert.doesNotMatch(text, detail)
})

test('a shortcut cycle reads and draws as closed work: listed with the closed cycles, and its queue item as finished', () => {
  const queue = {
    ok: true, authorization: null,
    items: [{ id: 'Q-0001', title: 'Short item', state: 'started', suggested_type: 'iterate', cycle: 'CYC-0007', cycle_status: 'shortcut' }],
  }
  const text = textOf(doc([row('shortcut', { phase: 'reflect' })], { queue }))
  assert.match(text, /last completed: CYC-0007/)
  assert.match(text, /\u2713 CYC-0007 dev shortcut 1\/1/)
  assert.match(text, /\u2713 Q-0001 CYC-0007 shortcut/)
  assert.doesNotMatch(text, /CURRENT CYCLE: CYC-0007/)
  assert.doesNotMatch(text, /PAUSED/)
  // Positive control: an active cycle draws as the current cycle, so the absence above is the status's doing.
  assert.match(textOf(doc([row('active')])), /CURRENT CYCLE/)
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
const releaseRow = (status: string, taskStatus: string, reflection: string) =>
  row(status, {
    schema_version: 'crux.cycle.v1', revision: 7, type: 'pilot', title: 'Release 9.9.9',
    phase: status === 'completed' ? 'completed' : 'working', pass: 1, pass_limit: 1,
    phases: ['planning', 'working', 'reviewing', 'reviewed', 'completed'],
    tasks: betaSteps.map(([id, text]) => ({ id, phase: 'working', description: `${text} [lead-a run 0]`, status: taskStatus })),
    reflection, phase_times: [], basis: 'derived',
  })

test('a crux.cycle.v1 release record reads and draws its six fixed steps and its delivery facts', () => {
  const open = textOf(doc([releaseRow('active', 'pending', 'Delivery, recorded separately: PR: none; CI: unknown; merge: unmerged')]))
  // The card lists five pending tasks and counts the sixth.
  for (const [, text] of betaSteps.slice(0, 5)) assert.ok(open.includes(text), text)
  assert.match(open, /\+1 more pending tasks/)
  assert.match(open, /CURRENT CYCLE: CYC-0007 Release 9\.9\.9/)
  assert.match(open, /0\/6 tasks/)
  const done = textOf(doc([releaseRow('completed', 'done', 'Completed. Delivery, recorded separately: PR: none; CI: unknown; merge: unmerged')]))
  assert.match(done, /6\/6/)
  assert.match(done, /Completed\. Delivery, recorded separately/)
  // A current record draws its steps and no type label or pass count.
  for (const absent of [/pilot/, /pass \d/]) assert.doesNotMatch(open, absent)
  assert.match(open, /✓ planning › ▸ working › ◌ reviewing › ◌ reviewed › ◌ completed/)
  // Positive control: a historical record keeps its type and pass count in the same card.
  assert.match(textOf(doc([row('active')])), /pass \d\/\d/)
  // Positive control: a string format the pilot rule does not know refuses the document.
  assert.equal(readOf(doc([{ ...releaseRow('active', 'pending', 'x'), schema_version: 'crux.cycle.v2' }]))?.ok, false)
})

// A current-format row awaiting finish: status reviewed on its reviewed state.
const pilotRow = (id: string, status: string, phase: string) =>
  row(status, {
    id, schema_version: 'crux.cycle.v1', revision: 5, type: 'pilot', title: `Pilot ${id}`, phase, pass: 1, pass_limit: 1,
    phases: ['planning', 'working', 'reviewing', 'reviewed', 'completed'], phase_times: [], basis: 'derived',
    tasks: [{ id: 'a', phase: 'working', description: 'Work [lead run 1]', status: 'done' }],
    ended_s: status === 'completed' ? 1779999900 : null, open_started_s: status === 'completed' ? null : 1779999000,
  })

test('a reviewed cycle awaiting finish draws with the current cycles, not with the closed ones', () => {
  const text = textOf(doc([pilotRow('CYC-0008', 'reviewed', 'reviewed'), pilotRow('CYC-0006', 'completed', 'completed')]))
  assert.match(text, /CURRENT CYCLE: CYC-0008 Pilot CYC-0008/)
  assert.match(text, /reviewed/)
  assert.match(text, /CYC-0006/)
  assert.doesNotMatch(text, /PAUSED/)
  // The closed cycle stays in the closed group, and the reviewed one draws once.
  assert.equal(text.split('CYC-0008 Pilot CYC-0008').length - 1, 1)
  assert.doesNotMatch(text, /CURRENT CYCLE: CYC-0006/)
  // Positive control: the same row as completed draws with the closed cycles, so the card above is the status's doing.
  assert.doesNotMatch(textOf(doc([pilotRow('CYC-0008', 'completed', 'completed')])), /CURRENT CYCLE: CYC-0008/)
})

test('the live queue card gives a started item whose cycle is reviewed the running glyph', () => {
  const p = readOf(doc([pilotRow('CYC-0008', 'reviewed', 'reviewed'), pilotRow('CYC-0006', 'completed', 'completed')]))
  assert.ok(p !== null && p.ok && p.view.cycles !== undefined)
  const item = (id: string, cycle: string) => ({ id, title: `Item ${id}`, suggestedType: 'dev', state: 'started', dependsOn: [], cycle, holdReason: null, authorized: true })
  const live: LiveRuntimeSnapshot = {
    nowMs: 1780000000000, mainStreaming: false, activeTools: [], subagents: [], asyncJobs: [],
    queue: { items: [item('Q-0002', 'CYC-0008'), item('Q-0001', 'CYC-0006')], authKind: 'queue', remaining: [] },
  }
  const lines = blockLines(buildOmpCyclesPane(p.view.cycles, p.view.now_s, live, 120))
  const rowOf = (id: string) => lines.find(l => l.includes(` ${id} `)) ?? ''
  assert.ok(rowOf('Q-0002').includes(`${STATE_GLYPHS.running} Q-0002`), rowOf('Q-0002'))
  assert.match(rowOf('Q-0002'), /dev · reviewed/)
  // Positive control: the completed cycle's item takes the done glyph from the same card.
  assert.ok(rowOf('Q-0001').includes(`${STATE_GLYPHS.done} Q-0001`), rowOf('Q-0001'))
})
