// The cycle panel in crux-opencode: the slot, the queue card, the latest closed cycle as a panel and
// the capped `cycles:` list. The host cannot turn pages, so the list stops at three rows with a
// `+N more` line and no page footer.
import { test, expect } from 'claude-code/testing'
import { panelNode, readView } from '../lib/render.ts'
import type { PlainNode, PlainSpan } from '../lib/render.ts'
import { jsonText } from './fixtures/plain.ts'

const WIDTHS: Array<number | undefined> = [30, 40, 60, 86, 110, 120, undefined]
const PHASES = ['plan', 'build', 'test', 'review', 'reflect']

const cycleRow = (n: number, status = 'completed') => ({
  id: `CYC-${String(n).padStart(4, '0')}`, title: `Cycle title ${n}`, type: 'iterate', status, phase: 'build', pass: 1, pass_limit: 2,
  phases: PHASES,
  tasks: [
    { id: 'a', phase: 'plan', description: 'Plan it', status: 'done' },
    { id: 'b', phase: 'build', description: `Current work ${n}`, status: status === 'active' ? 'active' : 'done' },
  ],
  returns: [], waits: [], blocker: null, reflection: null, modified_s: 1780000000,
  started_s: 1779999000, ended_s: status === 'active' || status === 'paused' ? null : 1779999900, paused_s: 0,
  open_started_s: status === 'active' || status === 'paused' ? 1779999500 : null, basis: 'recorded',
  phase_times: [{ phase: 'plan', active_s: 500, paused_s: 0 }],
})
const qItem = (n: number, state: string) => ({
  id: `Q-${String(n).padStart(4, '0')}`, title: `Queue title ${n}`, state, suggested_type: 'iterate', cycle: null, cycle_status: null,
})
const doc = (cycles: unknown[], queue?: unknown) => ({
  format: 'crux.cycle-progress', format_version: 2, ok: true, docs_dir: 'bionic', now_s: 1780000000, cycles,
  ...(queue === undefined ? {} : { queue }),
})
const parsedOf = (d: unknown) => {
  const p = readView(true, () => ({ ok: true, stdout: jsonText(d) }))
  expect(p !== null && p.ok).toBe(true)
  return p
}
const rowsOf = (n: PlainNode | null): PlainSpan[][] => {
  if (n === null || n.kind === 'spacer') return []
  return n.kind === 'text' ? [n.spans] : n.children.flatMap(rowsOf)
}
const plain = (r: PlainSpan[]) => r.map(s => s.text).join('')
const textOf = (d: unknown, width: number | undefined): string[] => rowsOf(panelNode(parsedOf(d), 'crux-dashboard', width)).map(plain)
const closed = (n: number) => Array.from({ length: n }, (_, i) => cycleRow(n - i))

const FULL = doc([cycleRow(9, 'active'), ...closed(6)], { ok: true, items: [qItem(1, 'pending'), qItem(2, 'held')], authorization: null })

for (const w of WIDTHS) {
  test(`width ${w ?? 'none'}: the expanded cycle follows the queue, then cycles: heads three rows, +N more and no page footer`, () => {
    const lines = textOf(FULL, w)
    // Six closed cycles: CYC-0006 is the panel, 0005 to 0003 are rows, and two are left.
    expect(lines.some(l => l.includes('+2 more'))).toBe(true)
    expect(lines.some(l => l.includes('page'))).toBe(false)
    expect(lines.some(l => l.includes('older'))).toBe(false)
    const queue = lines.findIndex(l => l.startsWith('Queue'))
    const panelAt = lines.findIndex(l => l.startsWith('CYC-0006'))
    const heading = lines.findIndex(l => l.trim() === 'cycles:')
    expect(queue).toBeGreaterThan(-1)
    expect(panelAt).toBeGreaterThan(queue)
    expect(heading).toBeGreaterThan(panelAt)
    // Rows cut at a narrow width may lose the status word, so count the ids after the heading.
    expect(lines.slice(heading + 1).filter(l => /CYC-000[1-5]/.test(l)).length).toBe(3)
  })

  test(`width ${w ?? 'none'}: no row is wider than the width`, () => {
    if (w === undefined) return
    for (const l of textOf(FULL, w)) expect(l.length).toBeLessThanOrEqual(w)
  })

  test(`width ${w ?? 'none'}: the slot draws first for an active cycle`, () => {
    const lines = textOf(FULL, w)
    const first = lines.findIndex(l => l.includes('CYC-0009'))
    expect(first >= 0).toBe(true)
    expect(lines.findIndex(l => l.includes('CYC-0006')) > first).toBe(true)
  })
}

test('with no open cycle the latest closed cycle is the panel and the other draws as one row', () => {
  const lines = textOf(doc(closed(2)), 100)
  expect(lines.filter(l => l.includes('loop 1 of 2')).length).toBe(1)
  expect(lines.findIndex(l => l.trim() === 'cycles:')).toBeGreaterThan(lines.findIndex(l => l.startsWith('CYC-0002')))
  expect(lines.filter(l => /^\S? ?CYC-0001/.test(l)).length).toBe(1)
})

test('exactly one closed cycle draws the panel alone, with no cycles: heading', () => {
  const lines = textOf(doc(closed(1)), 100)
  expect(lines.some(l => l.startsWith('CYC-0001'))).toBe(true)
  expect(lines.some(l => l.includes('cycles:'))).toBe(false)
})

test('four or fewer closed cycles draw no +N more line, and five draw +1 more', () => {
  for (const n of [1, 2, 3, 4]) expect(textOf(doc(closed(n)), 100).some(l => l.includes('more') || l.includes('older'))).toBe(false)
  expect(textOf(doc(closed(5)), 100).some(l => l.includes('+1 more'))).toBe(true)
})

test('the queue card: absent, empty, short, overflowing and unreadable', () => {
  const cycles = [cycleRow(9, 'active')]
  const text = (q: unknown) => textOf(doc(cycles, q), 100).join('\n')
  expect(text(undefined)).not.toContain('Queue title')
  expect(text(null)).not.toContain('Queue title')
  expect(text({ ok: true, items: [], authorization: null })).not.toContain('Queue title')
  expect(text({ ok: true, items: [qItem(1, 'pending'), qItem(2, 'held')], authorization: null })).toContain('Queue title 2')
  const many = Array.from({ length: 8 }, (_, i) => qItem(i + 1, 'pending'))
  const over = text({ ok: true, items: many, authorization: null })
  expect(over).toContain('Queue title 5')
  expect(over).not.toContain('Queue title 6')
  expect(over).toContain('+3 more')
  expect(text({ ok: false, error: 'broken' })).toContain('Queue unavailable')
})
