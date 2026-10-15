import { test, expect } from 'claude-code/testing'
import * as draw from '../hooks/lib/draw.ts'
import {
  AGENT_GLYPHS, BAR_OFF, BAR_ON, DECISION_GLYPHS, GATE_WORDS, GROUP_SEP, KINDS, NO_SEATS, SEAT_CELLS, STATE_GLYPHS, THEME_KEYS, UNKNOWN, UNTAGGED,
  agentGlyph, agentLines, bar, compactStrip, councilGrid, decisionGlyph, drawn, fitLine, gateStrip, gateWord, groupsOf, kindOf, labelledStrip,
  legendLine, lineCells, seatCell, stateGlyph, statusLine, stripLine, window,
} from '../hooks/lib/draw.ts'
import type { Line } from '../hooks/lib/draw.ts'
import * as width from '../hooks/lib/width.ts'
import { cells } from '../hooks/lib/width.ts'
import { DECISIONS, GATE_CLASSES, STATES, agents, parseReader } from '../hooks/lib/view.ts'
import type { Gate, RunView } from '../hooks/lib/view.ts'
import { AMBIGUOUS } from './fixtures/eaw-ambiguous.ts'
import { CLOCK_READ, withoutClock } from './fixtures/no-clock.ts'
import { EDGE_COUNCILS, READER_COUNCILS, READER_OK, READER_TEN, RUN, clone } from './fixtures/reader-output.ts'

const textOf = (l: Line) => l.map(s => s.text).join('')
const runOf = (doc: unknown, i = 0): RunView => {
  const p = parseReader(JSON.stringify(doc))
  if (!p.ok) throw new Error(`fixture is ${p.code}`)
  return p.view.runs[i]!
}

// --- the closed maps -------------------------------------------------------------------------

test('every prompt and gate state draws its glyph, and any other value the unknown cell', () => {
  expect(STATES.map(s => stateGlyph(s))).toEqual(['\u{2713}', '\u{2298}', '\u{2717}', '\u{25B8}', '\u{25CC}'])
  for (const other of ['passed', 'toString', 'constructor', '__proto__', '']) expect([other, stateGlyph(other)]).toEqual([other, '?'])
  expect(UNKNOWN).toBe('?')
})

test('every seat decision draws its glyph, a null decision a dash, and any other value the unknown cell', () => {
  expect(DECISIONS.map(d => decisionGlyph(d))).toEqual(['\u{2713}', '~', '\u{2717}', '\u{2297}', '\u{2B26}', '\u{2296}'])
  expect(decisionGlyph(null)).toBe('-')
  for (const other of ['ship it', 'AUTO_EXECUTE', 'hasOwnProperty', '__proto__']) expect([other, decisionGlyph(other)]).toEqual([other, '?'])
})

test('every agent status draws its glyph, and any other status the unknown cell', () => {
  expect(['running', 'completed', 'failed'].map(agentGlyph)).toEqual(['\u{25B8}', '\u{2713}', '\u{2717}'])
  for (const other of ['queued', 'unknown', 'valueOf']) expect([other, agentGlyph(other)]).toEqual([other, '?'])
})

test('every gate class draws its word, and any other class the unknown cell', () => {
  expect(GATE_CLASSES.map(gateWord)).toEqual(['council', 'module-close', 'review'])
  expect([gateWord('internal-review'), gateWord('toString')]).toEqual(['?', '?'])
})

test('a module tag draws its kind by its prefix: a word and a theme key; no tag is untagged; any other prefix is unknown', () => {
  expect(['adr-1', 'implementation-2', 'dev-3', 'review-4', 'verify-5'].map(kindOf)).toEqual([
    { word: 'adr', color: 'merged' }, { word: 'implementation', color: 'permission' }, { word: 'dev', color: 'claude' },
    { word: 'review', color: 'suggestion' }, { word: 'verify', color: 'success' },
  ])
  expect(kindOf(null)).toEqual({ word: 'untagged', color: 'inactive' })
  for (const other of ['zzz-1', 'constructor-1', '__proto__-1', 'Adr 1', 'adr', 'adr-1\u{200B}']) expect([other, kindOf(other)]).toEqual([other, { word: '?', color: 'text' }])
})

test('the reader check stays strict: an unknown tag prefix is a valid tag that draws the unknown kind, and an unknown state is invalid', () => {
  const doc = clone(READER_OK)
  doc.runs[0].prompts[0].module_tag = 'zzz-7'
  const r = runOf(doc)
  expect(kindOf(r.prompts[0]!.module_tag).word).toBe('?')
  expect(labelledStrip(r, 200)!.map(s => s.text)).toContain('?')
  const bad = clone(READER_OK)
  bad.runs[0].prompts[0].state = 'passed'
  expect(parseReader(JSON.stringify(bad))).toEqual({ ok: false, code: 'reader-output-invalid' })
})

test('each map is one-to-one, and the four special grid cells differ from each other, from every decision glyph and from the unknown cell', () => {
  const distinct = (xs: string[]) => new Set(xs).size === xs.length
  expect(distinct(Object.values(STATE_GLYPHS))).toBe(true)
  expect(distinct(Object.values(DECISION_GLYPHS))).toBe(true)
  expect(distinct(Object.values(AGENT_GLYPHS))).toBe(true)
  expect(distinct(Object.values(GATE_WORDS))).toBe(true)
  const kinds = [...Object.values(KINDS), UNTAGGED, draw.UNKNOWN_KIND]
  expect(distinct(kinds.map(k => k.word))).toBe(true)
  expect(distinct(kinds.map(k => k.color))).toBe(true)
  const special = Object.values(SEAT_CELLS)
  expect(distinct([...special, ...Object.values(DECISION_GLYPHS), UNKNOWN])).toBe(true)
  expect(special).toEqual(['-', '!', '.', '\u{2205}'])
})

// Every glyph a closed map draws, with the constants of the mod drawn as glyphs.
const GLYPHS = [
  ...Object.values(STATE_GLYPHS), ...Object.values(DECISION_GLYPHS), ...Object.values(SEAT_CELLS), ...Object.values(AGENT_GLYPHS),
  BAR_ON, BAR_OFF, GROUP_SEP, UNKNOWN,
]

test('every glyph takes one cell, is not East Asian Ambiguous, and is no emoji', () => {
  const inAmbiguous = (cp: number) => AMBIGUOUS.some(([lo, hi]) => cp >= lo && cp <= hi)
  const emoji = [new RegExp('\\p{Emoji}', 'u'), new RegExp('\\p{Emoji_Presentation}', 'u'), new RegExp('\\p{Extended_Pictographic}', 'u')]
  for (const g of GLYPHS) {
    const cps = Array.from(g)
    expect([g, cps.length, cells(g)]).toEqual([g, 1, 1])
    expect([g, inAmbiguous(g.codePointAt(0)!)]).toEqual([g, false])
    expect([g, emoji.map(re => re.test(g))]).toEqual([g, [false, false, false]])
  }
  // Positive controls: the warning sign is an emoji, and the black circle is Ambiguous.
  expect(emoji[0]!.test('\u{26A0}')).toBe(true)
  expect(inAmbiguous(0x25cf)).toBe(true)
})

test('every theme key a builder uses is in the closed list', () => {
  const r = runOf(READER_COUNCILS)
  const lines: Line[] = [
    legendLine([r], 400), labelledStrip(r, 400)!, compactStrip(r, 400), stripLine(r, 400), bar(50, 20), ...councilGrid(r.councils, 400),
    gateStrip(r.gates, 400), ...agentLines(agents([{ status: 'running', type: 't', description: 'd' }, { status: 'odd', type: 't', description: 'd' }]), 400),
    statusLine('Dashboard unavailable: ', 'reader-failed', 400),
  ]
  const keys = new Set(lines.flat().map(s => s.color).filter(c => c !== undefined))
  expect([...keys].every(k => (THEME_KEYS as readonly string[]).includes(k!))).toBe(true)
  // Positive control: the lines do draw colours.
  expect(keys.size).toBeGreaterThan(2)
})

// --- spans and free text ----------------------------------------------------------------------

test('fitLine keeps a line that fits and cuts a longer one with an ellipsis in the cut span\'s style', () => {
  const line: Line = [{ text: 'abc' }, { text: 'def', color: 'error' }]
  expect(fitLine(line, 6)).toEqual(line)
  expect(fitLine(line, 5)).toEqual([{ text: 'abc' }, { text: 'd\u{2026}', color: 'error' }])
  expect(fitLine(line, 3)).toEqual([{ text: 'ab\u{2026}' }])
  expect(fitLine(line, 1)).toEqual([{ text: '\u{2026}' }])
  expect(fitLine(line, 0)).toEqual([])
  expect(lineCells([{ text: '\u{65E5}\u{672C}' }, { text: 'a' }])).toBe(5)
})

test('drawn removes before it cuts, so a removed character takes no room', () => {
  expect(drawn('ab\u{200B}cd\u{202E}ef', 6)).toBe('abcdef')
  expect(drawn('ab\u{200B}cd\u{202E}efg', 6)).toBe('abcde\u{2026}')
  expect(drawn('\u{E0041}\u{E0042}', 3)).toBe('')
})

// --- the prompt strip ---------------------------------------------------------------------------

test('the strip groups consecutive prompts by module and labels each group with its kind word', () => {
  const r = runOf(READER_OK)
  expect(groupsOf(r.prompts).map(g => [g.kind.word, g.from, g.to])).toEqual([['adr', 0, 1], ['untagged', 2, 3]])
  expect(textOf(labelledStrip(r, 200)!)).toBe('adr \u{2713}\u{2717}  untagged \u{25B8}\u{25CC}')
  expect(textOf(compactStrip(r, 200))).toBe('\u{2713}\u{2717}|\u{25B8}\u{25CC}')
  // The kind word carries the kind's colour; no cell does, and a blocked cell is in the error key.
  const labelled = labelledStrip(r, 200)!
  expect(labelled.filter(s => s.text === 'adr' || s.text === 'untagged').map(s => s.color)).toEqual(['merged', 'inactive'])
  expect(labelled.filter(s => s.text === '\u{2717}').map(s => s.color)).toEqual(['error'])
  expect(labelled.filter(s => ['\u{2713}', '\u{25B8}', '\u{25CC}'].includes(s.text)).map(s => s.color)).toEqual([undefined, undefined, undefined])
})

test('a patch book with no module tags is one untagged group', () => {
  const doc = clone(READER_OK)
  for (const p of doc.runs[0].prompts) p.module_tag = null
  expect(textOf(labelledStrip(runOf(doc), 200)!)).toBe('untagged \u{2713}\u{2717}\u{25B8}\u{25CC}')
})

test('a strip that does not fit keeps the cells nearest the current prompt and counts the rest exactly', () => {
  const r = runOf(READER_TEN)
  // Ten cells and two separators.
  expect(textOf(compactStrip(r, 12))).toBe('\u{2713}\u{2713}\u{2717}|\u{2713}\u{25B8}\u{25CC}|\u{25CC}\u{25CC}\u{25CC}\u{25CC}')
  expect(window(10, 4, 3)).toEqual([3, 6])
  expect(window(10, 4, 4)).toEqual([2, 6])
  expect(window(10, 0, 3)).toEqual([0, 3])
  expect(window(10, 9, 3)).toEqual([7, 10])
  expect(textOf(compactStrip(r, 6))).toBe('\u{2713}\u{25B8}\u{25CC}+7')
  expect(textOf(compactStrip(r, 7))).toBe('\u{2717}|\u{2713}\u{25B8}\u{25CC}+6')
  expect(textOf(compactStrip(r, 3))).toBe('\u{25B8}+9')
  // Where the count no longer fits, an ellipsis stands for the rest.
  expect(textOf(compactStrip(r, 2))).toBe('\u{25B8}\u{2026}')
  expect(compactStrip(r, 1)).toEqual([])
  for (let n = 1; n <= 14; n++) expect([n, lineCells(compactStrip(r, n)) <= n]).toEqual([n, true])
})

test('with no current prompt the strip keeps the cells nearest the last prompt that is not pending', () => {
  const doc = clone(READER_TEN)
  doc.runs[0].current_prompt = null
  expect(textOf(compactStrip(runOf(doc), 6))).toBe('\u{2713}\u{25B8}\u{25CC}+7')
})

test('the pane strip is labelled when it fits, else the current kind word and the compact strip', () => {
  const r = runOf(READER_TEN)
  expect(textOf(stripLine(r, 60))).toBe('dev \u{2713}\u{2713}\u{2717}  review \u{2713}\u{25B8}\u{25CC}  untagged \u{25CC}\u{25CC}\u{25CC}\u{25CC}')
  expect(textOf(stripLine(r, 20))).toBe('review \u{2713}\u{2713}\u{2717}|\u{2713}\u{25B8}\u{25CC}|\u{25CC}\u{25CC}\u{25CC}\u{25CC}')
  expect(textOf(stripLine(r, 15))).toBe('review \u{2717}|\u{2713}\u{25B8}\u{25CC}+6')
  expect(textOf(stripLine(r, 5))).toBe('\u{2713}\u{25B8}\u{25CC}+7')
})

// --- the progress bar ---------------------------------------------------------------------------

test('the bar fills the reader\'s percentage of its cells', () => {
  const on = '\u25ae'
  const off = '\u25af'
  expect([BAR_ON, BAR_OFF]).toEqual([on, off])
  expect(textOf(bar(25, 20))).toBe(on.repeat(5) + off.repeat(15))
  expect(textOf(bar(0, 10))).toBe(off.repeat(10))
  expect(textOf(bar(100, 10))).toBe(on.repeat(10))
  expect(textOf(bar(40, 30))).toBe(on.repeat(8) + off.repeat(12))
  expect(bar(50, 0)).toEqual([])
})

// --- the council grid ---------------------------------------------------------------------------

test('the grid has a column per record and a row per seat, each cell under its record\'s label', () => {
  const r = runOf(READER_OK)
  const lines = councilGrid(r.councils, 60).map(textOf)
  expect(lines).toEqual([
    '           p2r1 p2r2',
    'openai_top \u{2717}    \u{2713}   ',
    'google_top \u{2713}    .   ',
    'p2 r2  adr  AUTO_EXECUTE  converged',
  ])
  // Each cell starts where its column's label starts.
  const starts = [...lines[0]!.matchAll(/p\d+r\d+/g)].map(m => m.index!)
  for (const row of lines.slice(1, 3)) for (const s of starts) expect(row[s] === ' ').toBe(false)
})

test('the grid draws a null decision, an errored seat, an absent role and a council that could not run, each distinct from the unknown cell', () => {
  const r = runOf(READER_COUNCILS)
  const [p1r1, p1r2, p1r3, p2r1] = r.councils
  expect([seatCell(p1r1!, 'openai_top'), seatCell(p1r1!, 'anthropic_top'), seatCell(p1r1!, 'google_top'), seatCell(p1r2!, 'openai_top')]).toEqual(['-', '!', '.', '\u{2205}'])
  expect([seatCell(p1r3!, 'openai_top'), seatCell(p1r3!, 'anthropic_top'), seatCell(p1r3!, 'google_top')]).toEqual(['~', '\u{2297}', '\u{2B26}'])
  expect([seatCell(p2r1!, 'openai_top'), seatCell(p2r1!, 'google_top'), seatCell(p2r1!, 'anthropic_top')]).toEqual(['\u{2296}', '\u{2713}', '\u{2717}'])
  const lines = councilGrid(r.councils, 80).map(textOf)
  expect(lines[0]).toBe('              p1r1 p1r2 p1r3 p2r1')
  expect(lines.slice(1, 4)).toEqual([
    'openai_top    -    \u{2205}    ~    \u{2296}   ',
    'anthropic_top !    \u{2205}    \u{2297}    \u{2717}   ',
    'google_top    .    \u{2205}    \u{2B26}    \u{2713}   ',
  ])
  expect(lines.join('\n').includes('?')).toBe(false)
  // A decision outside the set, which only a view built without the reader check can hold, draws the unknown cell.
  const odd = { ...p2r1!, seats: [{ role: 'openai_top', decision: 'SHIP_IT', errored: false, blocking: 0, nit: 0 }] }
  expect(seatCell(odd, 'openai_top')).toBe('?')
})

test('records that seat no one still draw one row of cells', () => {
  const r = runOf(READER_COUNCILS)
  const lines = councilGrid([r.councils[1]!], 60).map(textOf)
  expect(lines[1]).toBe(`${NO_SEATS} \u{2205}   `)
  expect(lines[2]).toBe('p1 r2  verify  could not run  none  not converged')
})

test('a grid that does not fit keeps the newest records and counts the rest', () => {
  const r = runOf(READER_COUNCILS)
  const lines = councilGrid(r.councils, 26).map(textOf)
  // The label column takes a third of the width, here 8 cells, and three of the four records fit.
  expect(lines[0]).toBe('         p1r2 p1r3 p2r1 +1')
  expect(lines[1]).toBe('openai_\u{2026} \u{2205}    ~    \u{2296}   ')
  expect(councilGrid(r.councils, 21).map(textOf)[0]).toBe('        p1r3 p2r1 +2')
  for (const l of councilGrid(r.councils, 26)) expect(lineCells(l)).toBeLessThanOrEqual(26)
  for (let n = 1; n <= 40; n++) for (const l of councilGrid(r.councils, n)) expect([n, lineCells(l) <= n]).toEqual([n, true])
})

// --- the gate strip -----------------------------------------------------------------------------

const gateAt = (n: number, state: string, gate_class = 'council'): Gate => ({ n, gate_class, state: state as any, evidence: [], evidence_count: 0 })

test('the gate strip draws each gate\'s glyph, prompt and class word', () => {
  const r = runOf(READER_OK)
  expect(textOf(gateStrip(r.gates, 80))).toBe('\u{2717} p2 council  \u{25CC} p4 review')
  expect(gateStrip(r.gates, 80).find(s => s.text === '\u{2717}')?.color).toBe('error')
  expect(gateStrip([], 80)).toEqual([])
})

test('a gate strip that does not fit keeps the gates nearest the last decided one and counts the rest', () => {
  const gates = [gateAt(1, 'done'), gateAt(3, 'done', 'module-close'), gateAt(5, 'blocked'), gateAt(7, 'pending'), gateAt(9, 'pending', 'independent-review')]
  expect(textOf(gateStrip(gates, 200))).toBe('\u{2713} p1 council  \u{2713} p3 module-close  \u{2717} p5 council  \u{25CC} p7 council  \u{25CC} p9 review')
  // A tie keeps the earlier gate: the module-close gate before the blocked one, not the pending one after it.
  expect(textOf(gateStrip(gates, 35))).toBe('\u{2713} p3 module-close  \u{2717} p5 council  +3')
  expect(textOf(gateStrip(gates, 34))).toBe('\u{2717} p5 council  +4')
  expect(textOf(gateStrip(gates, 16))).toBe('\u{2717} p5 council  +4')
  for (let n = 1; n <= 60; n++) expect([n, lineCells(gateStrip(gates, n)) <= n]).toEqual([n, true])
})

// --- agents and statuses ------------------------------------------------------------------------

test('agent rows draw the status glyph, the type and the description; an unreadable list draws one row; an empty list none', () => {
  const ag = agents([{ status: 'running', type: 'developer', description: 'Plan the thing' }, { status: 'queued', type: 'reviewer', description: 'Look' }])
  expect(agentLines(ag, 80).map(textOf)).toEqual(['\u{25B8}  developer  Plan the thing', '?  reviewer  Look'])
  expect(agentLines(agents(undefined), 80).map(textOf)).toEqual(['agents unavailable'])
  expect(agentLines(agents([]), 80)).toEqual([])
  for (const l of agentLines(ag, 12)) expect(lineCells(l)).toBeLessThanOrEqual(12)
})

test('a status keeps its code and drops its prefix first, then cuts the code', () => {
  expect(textOf(statusLine('Dashboard unavailable: ', 'version-mismatch', 60))).toBe('Dashboard unavailable: version-mismatch')
  expect(textOf(statusLine('Dashboard unavailable: ', 'version-mismatch', 30))).toBe('version-mismatch')
  expect(textOf(statusLine('Dashboard unavailable: ', 'reader-failed:token-set-unavailable', 30))).toBe('reader-failed:token-set-unava\u{2026}')
  expect(statusLine('Dashboard unavailable: ', 'version-mismatch', 60)[0]!.color).toBe('error')
})

// --- free text from a view built without the reader check ------------------------------------------

test('a removal-class character in a role or an agent field never draws, and each value is fitted', () => {
  const r = runOf(READER_OK)
  const council = { ...r.councils[0]!, seats: [{ role: 'open\u{200B}ai\u{202E}', decision: 'APPROVE', errored: false, blocking: 0, nit: 0 }] }
  const ag = agents([{ status: 'run\u{200B}ning', type: 'dev\u{2066}eloper', description: 'Plan\u{E0041} the\u{AD} thing\u{2028}' }])
  const lines = [...councilGrid([council], 60), ...agentLines(ag, 60)].map(textOf)
  expect(lines.join('\n')).toContain('openai')
  expect(lines.join('\n')).toContain('developer  Plan the thing')
  const unsafe = new RegExp('[\\p{Cc}\\p{Cf}\\p{Default_Ignorable_Code_Point}\\u2028\\u2029]', 'u')
  expect(lines.filter(l => unsafe.test(l))).toEqual([])
  // The removal ran before the glyph map: the status names a known glyph once its zero-width space is gone.
  expect(lines.some(l => l.startsWith('\u{25B8}'))).toBe(true)
  for (const l of [...councilGrid([council], 9), ...agentLines(ag, 9)]) expect(lineCells(l)).toBeLessThanOrEqual(9)
})

// --- no clock -------------------------------------------------------------------------------------

function builderMatrix() {
  for (const doc of [READER_OK, READER_TEN, READER_COUNCILS]) {
    const r = runOf(doc)
    for (const n of [1, 5, 30, 40, 60, 86, 110, 120]) {
      legendLine([r], n); labelledStrip(r, n); compactStrip(r, n); stripLine(r, n); bar(r.pct, n); councilGrid(r.councils, n); gateStrip(r.gates, n)
      agentLines(agents([{ status: 'running', type: 'developer', description: 'Plan' }]), n); statusLine('Dashboard unavailable: ', 'reader-failed', n)
      fitLine([{ text: 'abc' }], n); drawn('a\u{200B}b', n)
    }
  }
}

test('no builder reads a clock: each runs with every clock read throwing, and no export\'s source names one', () => {
  // Positive control: the guard does throw on a clock read.
  expect(() => withoutClock(() => { Date.now() })).toThrow()
  expect(() => withoutClock(() => new Date())).toThrow()
  expect(() => withoutClock(() => { performance.now() })).toThrow()
  expect(() => withoutClock(() => builderMatrix())).not.toThrow()
  // A date made from seconds still works under the guard, as view.ts's utc makes one.
  expect(() => withoutClock(() => new Date(1000))).not.toThrow()
  expect(Date.now()).toBeGreaterThan(0)
  const sources = [...Object.values(draw), ...Object.values(width)].filter(v => typeof v === 'function').map(f => String(f))
  expect(sources.length).toBeGreaterThan(20)
  expect(sources.filter(s => CLOCK_READ.test(s))).toEqual([])
  // Positive control: the scan finds a seeded read.
  expect(CLOCK_READ.test(String(() => Date.now()))).toBe(true)
})
