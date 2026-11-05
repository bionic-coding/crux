// Reader format 5 in crux-opencode: the dashboard reads the same document the Claude Code mod reads,
// strictly, and draws the open attempts, the classification count, owner exception and revision through the
// shared core.
import { test, expect } from 'claude-code/testing'
import { panelNode, readView } from '../lib/render.ts'
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
