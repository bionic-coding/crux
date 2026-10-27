import { test, expect } from 'claude-code/testing'
import { bandNode, panelNode, readView } from '../lib/render.ts'
import type { PlainNode, PlainSpan } from '../lib/render.ts'
import { tokenOfKey } from '../lib/theme.ts'
import { cycleTimeText } from '../../crux-mods/hooks/lib/view.ts'
import { jsonText } from './fixtures/plain.ts'

// The phase sequence of each cycle type. It is written here and not read from the parser, which
// keeps it private. The parser rejects a document whose phases differ from its own sequence, so a
// change there fails the drawing tests below instead of drifting silently.
const SEQUENCES: Record<string, string[]> = {
  dev: ['plan', 'build', 'test', 'review', 'reflect'],
  iterate: ['plan', 'build', 'test', 'review', 'reflect'],
  refactor: ['plan', 'build', 'test', 'review', 'reflect'],
  'quick-fix': ['build', 'test', 'review', 'reflect'],
  simplify: ['plan', 'build', 'test', 'review', 'reflect'],
  release: ['plan', 'release', 'reflect'],
}
const PROGRESS_TOKENS = ['success', 'claude', 'warning', 'error'].map(tokenOfKey)

// The phase-key map as it stood when review drew in `subtle`, which resolves to the same token as
// reflect's `inactive`.
const OLD_KEYS: Record<string, string> = { plan: 'merged', build: 'suggestion', test: 'permission', review: 'subtle', release: 'text', reflect: 'inactive' }

const tasksOf = (phases: string[]) => phases.map(p => ({ id: `t-${p}`, phase: p, description: `Work in ${p}`, status: 'pending' }))
const docOf = (type: string, over: Record<string, unknown> = {}) => {
  const phases = SEQUENCES[type]!
  return {
    format: 'crux.cycle-progress', format_version: 2, ok: true, docs_dir: 'bionic', now_s: 1780000000,
    cycles: [{
      id: 'CYC-0001', title: 'Update the dashboard', type, status: 'active', phase: phases[0], pass: 1, pass_limit: 2,
      phases, tasks: tasksOf(phases), returns: [], waits: [], blocker: null, reflection: null, modified_s: 1780000000,
      started_s: 1779999000, ended_s: null, paused_s: 0, open_started_s: 1779999000, basis: 'recorded',
      phase_times: [{ phase: phases[0], active_s: 1000, paused_s: 0 }], ...over,
    }],
  }
}
const parsedOf = (doc: unknown) => {
  const p = readView(true, () => ({ ok: true, stdout: jsonText(doc) }))
  expect(p !== null && p.ok).toBe(true)
  return p
}

const rowsOf = (n: PlainNode | null): PlainSpan[][] => {
  if (n === null || n.kind === 'spacer') return []
  return n.kind === 'text' ? [n.spans] : n.children.flatMap(rowsOf)
}
const plain = (r: PlainSpan[]) => r.map(s => s.text).join('')
const find = (rs: PlainSpan[][], text: string) => rs.find(r => plain(r).includes(text))
const spanOf = (r: PlainSpan[] | undefined, text: string) => r!.find(s => s.text === text)

// The phases whose token another phase of the same type shares.
function collisions(tokens: Record<string, string>, phases: string[]): string[] {
  return phases.filter((p, i) => phases.some((q, j) => j !== i && tokens[q] === tokens[p]))
}

// The token each phase word draws in, read from the task rows of a drawn panel.
function drawnTokens(type: string): Record<string, string> {
  const rows = rowsOf(panelNode(parsedOf(docOf(type)), 'crux-dashboard', 100))
  const out: Record<string, string> = {}
  for (const phase of SEQUENCES[type]!) {
    const row = find(rows, `: Work in ${phase}`)
    out[phase] = spanOf(row, phase)!.token
  }
  return out
}

test('the panel draws the cycle title, status, loop, track and phase-labelled strip', () => {
  const doc = docOf('iterate', {
    phase: 'build',
    tasks: [
      { id: 'a', phase: 'plan', description: 'Plan it', status: 'done' },
      { id: 'b', phase: 'build', description: 'Write code', status: 'active' },
      { id: 'c', phase: 'test', description: 'Run tests', status: 'blocked' },
      { id: 'd', phase: 'review', description: 'Review it', status: 'pending' },
    ],
  })
  const rows = rowsOf(panelNode(parsedOf(doc), 'crux-dashboard', 100))
  const title = find(rows, 'CYC-0001')!
  expect(plain(title)).toContain('CYC-0001 Update the dashboard')
  expect(title.every(s => s.bold)).toBe(true)

  const meta = find(rows, 'loop 1')!
  // The open cycle's slot names the loop limit when the line has room for it.
  expect(plain(meta)).toContain('iterate ↻ loop 1 of 2 ▸ active')
  // The drawing merges the loop icon and its words into one span of one style.
  const loop = meta.find(s => s.text.includes('↻ loop 1'))!
  expect(loop.token).toBe('text.base')
  expect(loop.bold).toBe(false)
  expect(spanOf(meta, 'active')).toEqual({ text: 'active', token: 'syntax.function', bold: true })
  expect(spanOf(meta, '▸')).toEqual({ text: '▸', token: 'syntax.function', bold: true })

  const track = find(rows, '›')!
  expect(plain(track)).toBe('✓ plan › ▸ build › ◌ test › ◌ review › ◌ reflect')
  expect(spanOf(track, 'build')).toEqual({ text: 'build', token: 'syntax.function', bold: true })
  expect(spanOf(track, 'plan')).toEqual({ text: 'plan', token: 'text.feedback.success.base', bold: false })
  expect(spanOf(track, 'test')).toEqual({ text: 'test', token: 'text.muted', bold: false })
  expect(track.find(s => s.text.includes('›'))!.token).toBe('text.base')

  const strip = find(rows, 'plan ✓ build ▸')!
  expect(plain(strip)).toBe('plan ✓ build ▸ test ✗ review ◌')
  expect(spanOf(strip, '✓')!.token).toBe('text.feedback.success.base')
  expect(spanOf(strip, '▸')).toEqual({ text: '▸', token: 'syntax.function', bold: true })
  expect(spanOf(strip, '✗')!.token).toBe('text.feedback.error.base')
  expect(spanOf(strip, '◌')!.token).toBe('text.muted')
  expect(spanOf(strip, 'plan')!.token).toBe('syntax.keyword')

  const active = find(rows, ': Write code')!
  expect(spanOf(active, 'Write code')!.bold).toBe(true)
  expect(spanOf(active, 'build')!.token).toBe('text.feedback.info.base')
  const blocked = find(rows, ': Run tests')!
  expect(spanOf(blocked, 'Run tests')).toEqual({ text: 'Run tests', token: 'text.feedback.error.base', bold: false })
  // Positive control: the done task draws no bold, so the bold above comes from the active state.
  expect(find(rows, ': Plan it')!.find(s => s.text.includes('Plan it'))!.bold).toBe(false)
})

test('a status word and a glyph accompany every status colour', () => {
  // An open cycle and the latest closed cycle both draw as a panel with a meta row.
  const draw = (status: string) => find(rowsOf(panelNode(parsedOf(docOf('dev', { status })), 'crux-dashboard', 100)), 'loop 1')!
  const want: [string, string, string][] = [
    ['active', '▸', 'syntax.function'], ['completed', '✓', 'text.feedback.success.base'],
    ['paused', '⊘', 'text.feedback.warning.base'], ['abandoned', '✗', 'text.feedback.error.base'],
  ]
  for (const [word, glyph, token] of want) {
    const row = draw(word)
    expect(spanOf(row, word)!.token).toBe(token)
    expect(spanOf(row, glyph)!.token).toBe(token)
  }
})

// Before the band took the cycle panel's style, it drew a cycle as one plain line, `CYC-0001 ·
// quick-fix · Pass 1/1 · test · active`, and a test pinned it. This test replaces that pin on purpose.
test('the band draws a cycle in the panel style, each span in its token', () => {
  const doc = docOf('quick-fix', {
    phase: 'test', pass_limit: 1,
    tasks: [
      { id: 'a', phase: 'build', description: 'Draw it', status: 'done' },
      { id: 'b', phase: 'test', description: 'Check it', status: 'active' },
    ],
  })
  const rows = rowsOf(bandNode(parsedOf(doc), 100))
  expect(rows.length).toBe(1)
  const band = rows[0]!
  expect(plain(band)).toBe('CYC-0001  quick-fix  ↻ loop 1  ✓ ▸ test ◌ ◌  ▸ active  1/2 tasks')
  expect(spanOf(band, 'CYC-0001')).toEqual({ text: 'CYC-0001', token: 'text.base', bold: true })
  expect(spanOf(band, 'quick-fix')).toEqual({ text: 'quick-fix', token: 'syntax.type', bold: false })
  const loop = band.find(s => s.text.includes('↻ loop 1'))!
  expect([loop.token, loop.bold]).toEqual(['text.base', false])
  expect(spanOf(band, '✓')).toEqual({ text: '✓', token: 'text.feedback.success.base', bold: false })
  expect(spanOf(band, 'test')).toEqual({ text: 'test', token: 'syntax.function', bold: true })
  expect(band.filter(s => s.text === '▸').map(s => [s.token, s.bold])).toEqual([['syntax.function', true], ['syntax.function', true]])
  expect(band.filter(s => s.text === '◌').map(s => s.token)).toEqual(['text.muted', 'text.muted'])
  expect(spanOf(band, 'active')).toEqual({ text: 'active', token: 'syntax.function', bold: true })
  expect(spanOf(band, '1/2 tasks')).toEqual({ text: '1/2 tasks', token: 'text.muted', bold: false })
})

test('the band pairs each cycle status token with its glyph and word', () => {
  const want: [string, string, string, string][] = [
    ['active', 'build', '▸', 'syntax.function'], ['completed', 'reflect', '✓', 'text.feedback.success.base'],
    ['paused', 'build', '⊘', 'text.feedback.warning.base'], ['abandoned', 'build', '✗', 'text.feedback.error.base'],
  ]
  for (const [status, phase, glyph, token] of want) {
    const band = rowsOf(bandNode(parsedOf(docOf('dev', { status, phase })), 100))[0]!
    const i = band.findIndex(s => s.text === status)
    expect([status, band[i - 2]!.text, band[i - 2]!.token, band[i]!.token, band[i]!.bold]).toEqual([status, glyph, token, token, true])
  }
})

test('the band drops whole cycle segments at narrow widths and keeps the current phase', () => {
  const doc = docOf('iterate', { status: 'completed', phase: 'reflect', id: 'CYC-0003' })
  const at = (width: number) => plain(rowsOf(bandNode(parsedOf(doc), width))[0]!)
  expect(at(100)).toBe('CYC-0003  iterate  ↻ loop 1  ✓ ✓ ✓ ✓ ✓ reflect  ✓ completed  0/5 tasks')
  expect(at(60)).toBe('CYC-0003  ↻ loop 1  ✓ ✓ ✓ ✓ ✓ reflect  ✓ completed')
  expect(at(40)).toBe('CYC-0003  ✓ ✓ ✓ ✓ ✓ reflect  ✓ completed')
  expect(at(20)).toBe('CYC-0003  ✓ reflect')
  // The type word is absent at 60 columns. Positive control: the same drawing holds it at 100.
  expect(at(60).includes('iterate')).toBe(false)
  expect(at(100).includes('iterate')).toBe(true)
})

test('free text in a cycle title and a task description reaches the panel without control characters', () => {
  const doc = docOf('dev', {
    title: 'Fix\u001b[2J the\u0007 tool\u0085 \u202e now',
    tasks: [{ id: 'a', phase: 'plan', description: 'Plan\u001b]0;x\u0007 it\u009b', status: 'active' }],
  })
  const text = rowsOf(panelNode(parsedOf(doc), 'crux-dashboard', 100)).map(plain).join('\n')
  expect(text).toContain('Fix')
  expect(text).toContain('tool')
  expect(text).toContain('Plan')
  // Positive control: the same input holds the controls before drawing.
  expect(doc.cycles[0]!.title).toContain('\u001b')
  expect(/[\u0000-\u0008\u000b-\u001f\u007f-\u009f\u202e]/.test(text)).toBe(false)
})

test('every phase word of every cycle type draws in a distinct token that is no progress token', () => {
  for (const type of Object.keys(SEQUENCES)) {
    const phases = SEQUENCES[type]!
    const tokens = drawnTokens(type)
    expect(collisions(tokens, phases)).toEqual([])
    for (const p of phases) expect(PROGRESS_TOKENS.includes(tokens[p]!)).toBe(false)
  }
  // The tokens the decision names.
  expect(drawnTokens('dev')).toEqual({ plan: 'syntax.keyword', build: 'text.feedback.info.base', test: 'syntax.type', review: 'text.base', reflect: 'text.muted' })
  expect(drawnTokens('quick-fix')).toEqual({ build: 'text.feedback.info.base', test: 'syntax.type', review: 'text.base', reflect: 'text.muted' })
  expect(drawnTokens('release')).toEqual({ plan: 'syntax.keyword', release: 'text.base', reflect: 'text.muted' })
})

test('positive control: the old review key collides with reflect, and the check sees it', () => {
  const phases = SEQUENCES.dev!
  const old: Record<string, string> = {}
  const fixed: Record<string, string> = {}
  for (const p of phases) {
    old[p] = tokenOfKey(OLD_KEYS[p]!)
    fixed[p] = tokenOfKey(p === 'review' ? 'text' : OLD_KEYS[p]!)
  }
  expect(collisions(old, phases)).toEqual(['review', 'reflect'])
  expect(collisions(fixed, phases)).toEqual([])
})

// --- elapsed time -------------------------------------------------------------------------------

const START = 1779990000
const timed = (type: string, now_s: number, over: Record<string, unknown> = {}) => {
  const d = docOf(type, { started_s: START, open_started_s: START, ...over })
  d.now_s = now_s
  return d
}
const timeRow = (doc: unknown): string | undefined => {
  const row = rowsOf(panelNode(parsedOf(doc), 'crux-dashboard', 100)).find(r => plain(r).startsWith('elapsed'))
  return row === undefined ? undefined : plain(row)
}

test('elapsed time advances with now_s for an open cycle of every type', () => {
  for (const type of Object.keys(SEQUENCES)) {
    expect(timeRow(timed(type, START + 600))).toBe('elapsed 10m')
    expect(timeRow(timed(type, START + 4000))).toBe('elapsed 1h06m')
  }
})

test('paused time shows when non-zero, with the basis when derived', () => {
  for (const type of Object.keys(SEQUENCES)) {
    expect(timeRow(timed(type, START + 4000, { paused_s: 900, status: 'paused' }))).toBe('elapsed 1h06m paused 15m')
    expect(timeRow(timed(type, START + 4000, { paused_s: 900, basis: 'derived' }))).toBe('elapsed 1h06m paused 15m (derived)')
    expect(timeRow(timed(type, START + 4000, { paused_s: 20 }))).toBe('elapsed 1h06m paused <1m')
  }
})

test('a closed cycle keeps its elapsed time at any now_s', () => {
  for (const type of Object.keys(SEQUENCES)) {
    const closed = { status: 'abandoned', ended_s: START + 1800, paused_s: 300, open_started_s: null }
    // The time text is read from the view, not from the drawn panel.
    const timeAt = (now: number) => {
      const p = parsedOf(timed(type, now, closed))
      return p !== null && p.ok ? cycleTimeText(p.view.cycles![0]!, p.view.now_s) : undefined
    }
    expect(timeAt(START + 2000)).toBe('elapsed 30m paused 5m')
    expect(timeAt(START + 90000)).toBe('elapsed 30m paused 5m')
  }
})

// The panel's no-clock property is held where the view core lives: crux-mods/tests/cycle-dashboard.test.ts
// runs the cycle drawing with every clock read throwing. This gate forbids a Date or globalThis in a test.

// Ordering and the approval line come from the shared view core, so the panel and the band inherit them.
// The modified times run opposite to the ids, so a time sort fails these tests.
const manyOf = (ids: [string, string][]) => {
  const doc = docOf('iterate')
  const base = doc.cycles[0]!
  doc.cycles = ids.map(([id, status], i) => ({ ...base, id, status, modified_s: 1780000000 + i * 100 }))
  return doc
}
// A compact row starts with its status glyph, so the id follows an optional glyph and a space. A panel's first line starts with the id.
const idsDrawn = (doc: unknown) => rowsOf(panelNode(parsedOf(doc), 'crux-dashboard', 100)).map(plain).flatMap(t => t.match(/^(?:\S )?((?:[A-Z][A-Z0-9]*-)?CYC-\d+)/)?.[1] ?? [])

test('the panel lists active cycles first, then the rest, each by numeric id descending', () => {
  expect(idsDrawn(manyOf([['CYC-0009', 'active'], ['CYC-0010', 'completed'], ['CYC-0013', 'active'], ['CYC-0002', 'abandoned'], ['CYC-0011', 'paused']])))
    // The third open cycle is past the two-panel slot: it is counted in `+1 open`, not listed again.
    .toEqual(['CYC-0013', 'CYC-0009', 'CYC-0010', 'CYC-0002'])
  expect(idsDrawn(manyOf([['CYC-0099', 'completed'], ['CYC-10000', 'completed'], ['CYC-0100', 'completed']]))).toEqual(['CYC-10000', 'CYC-0100', 'CYC-0099'])
  expect(idsDrawn(manyOf([['ACME-CYC-0009', 'completed'], ['CYC-0010', 'completed'], ['ACME-CYC-0013', 'active']]))).toEqual(['ACME-CYC-0013', 'CYC-0010', 'ACME-CYC-0009'])
})

test('the band shows the highest numbered active cycle', () => {
  const band = rowsOf(bandNode(parsedOf(manyOf([['CYC-0009', 'active'], ['CYC-0013', 'active'], ['CYC-0020', 'completed']])), 100))[0]!
  expect(plain(band)).toContain('CYC-0013')
})

test('the panel draws one Awaiting approval line for a wait the reader repeats', () => {
  const rows = rowsOf(panelNode(parsedOf(docOf('dev', { waits: ['release-evidence', 'release-evidence', 'release-evidence', 'plan-b'] })), 'crux-dashboard', 100))
  expect(rows.map(plain).filter(t => t.includes('Awaiting approval')).map(t => t.trim())).toEqual(['⊘ Awaiting approval: release-evidence, plan-b'])
  expect(rowsOf(panelNode(parsedOf(docOf('dev')), 'crux-dashboard', 100)).some(r => plain(r).includes('Awaiting approval'))).toBe(false)
})

test('a simplify cycle draws the plan, build, test, review, reflect band', () => {
  const doc = docOf('simplify', { phase: 'test', pass_limit: 3 })
  expect(plain(rowsOf(bandNode(parsedOf(doc), 100))[0]!)).toBe('CYC-0001  simplify  ↻ loop 1  ✓ ✓ ▸ test ◌ ◌  ▸ active  0/5 tasks')
  expect(new Set(Object.values(drawnTokens('simplify'))).size).toBe(5)
})

// A listed release cycle has the one phase release. A legacy release cycle keeps its three.
test('a listed release cycle with the one phase release is accepted and drawn', () => {
  const phases = ['release']
  const doc = docOf('release', { phases, phase: 'release', pass_limit: 1, tasks: tasksOf(phases), phase_times: [{ phase: 'release', active_s: 1000, paused_s: 0 }] })
  const parsed = parsedOf(doc)
  const rows = rowsOf(panelNode(parsed, 'crux-dashboard', 100))
  expect(find(rows, ': Work in release')).toBeDefined()
  expect(plain(rowsOf(bandNode(parsed, 100))[0]!)).toContain('CYC-0001')
  expect(rows.map(plain).some(t => /limit|pass/i.test(t))).toBe(false)
})

test('a legacy release cycle with plan, release and reflect is still drawn', () => {
  const parsed = parsedOf(docOf('release'))
  expect(find(rowsOf(panelNode(parsed, 'crux-dashboard', 100)), ': Work in release')).toBeDefined()
})
