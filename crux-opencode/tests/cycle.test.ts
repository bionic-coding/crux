import { test, expect } from 'claude-code/testing'
import { bandNode, panelNode, readView } from '../lib/render.ts'
import type { PlainNode, PlainSpan } from '../lib/render.ts'
import { tokenOfKey } from '../lib/theme.ts'
import { jsonText } from './fixtures/plain.ts'

// The phase sequence of each cycle type. It is written here and not read from the parser, which
// keeps it private. The parser rejects a document whose phases differ from its own sequence, so a
// change there fails the drawing tests below instead of drifting silently.
const SEQUENCES: Record<string, string[]> = {
  dev: ['plan', 'build', 'test', 'review', 'reflect'],
  iterate: ['plan', 'build', 'test', 'review', 'reflect'],
  refactor: ['plan', 'build', 'test', 'review', 'reflect'],
  'quick-fix': ['build', 'test', 'review', 'reflect'],
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
    format: 'crux.cycle-progress', format_version: 1, ok: true, docs_dir: 'bionic', now_s: 1780000000,
    cycles: [{
      id: 'CYC-0001', title: 'Update the dashboard', type, status: 'active', phase: phases[0], pass: 1, pass_limit: 2,
      phases, tasks: tasksOf(phases), returns: [], waits: [], blocker: null, reflection: null, modified_s: 1780000000, ...over,
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
  expect(plain(meta)).toContain('iterate ↻ loop 1 ▸ active')
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
