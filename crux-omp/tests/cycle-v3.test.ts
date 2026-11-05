// Reader format 5 in crux-omp: the extension reads the document strictly through the shared core and
// its cycle cards draw the open attempts, the classification count, owner exception and revision.
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { panelLines, readView } from '../lib/render.ts'
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
