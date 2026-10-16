// The time axis in the pane: one lane per prompt on the run's shared axis, the run's times rows, the
// prompt rows whose title gives way before their duration, and the pane's size budget.
//
// Expected lanes, rows and sizes are literals, hand arithmetic from a fixture's parameters, or the
// rule as this file writes it out apart from the production code. Every size is counted on the drawn
// tree by this file's own counter, drawnSize, never by draw.ts's blockSize. Width is measured by
// fixtures/measure.ts, which shares no code with the hooks' width code. Non-ASCII is written as brace
// escapes.
//
// The source scans at the end read the source of each function draw.ts and view.ts export, because
// the kit gives a test no file read. A module-level alias of a clock, or an unexported helper such as
// draw.ts's budgeted or packed, is seen only by the review grep over the two whole files.
import { test, expect } from 'claude-code/testing'
import * as draw from '../hooks/lib/draw.ts'
import * as view from '../hooks/lib/view.ts'
import { parseReader } from '../hooks/lib/view.ts'
import { HARNESS, agents } from '../hooks/lib/claude.ts'
import type { Parsed } from '../hooks/lib/view.ts'
import { AMBIGUOUS } from './fixtures/eaw-ambiguous.ts'
import { HOSTILE_TITLE, IDLE_LATEST, NOW_S, READER_NO_PROMPTS, READER_OK, RUN, clone, readerAt } from './fixtures/reader-output.ts'
import { PANE, BAND, install } from './fixtures/world.ts'
import type { Opts } from './fixtures/world.ts'
import { layout, overflows, widest } from './fixtures/measure.ts'
import { withoutClock } from './fixtures/no-clock.ts'
import { READER_ZERO_AT_END, SEAT_SHAPE, nodeHeavyDoc, range, readerOf, seatDoc, targetAbandoned, targetCompleted, withoutAnyClock } from './fixtures/axis.ts'

const ok = (doc: unknown) => ({ exitCode: 0, stdout: JSON.stringify(doc) })
const P = (doc: unknown): Parsed => parseReader(JSON.stringify(doc))
const WIDTHS: (number | undefined)[] = [30, 40, 60, 86, 110, 120, undefined]
const dw = (w: number | undefined) => w ?? 40

// The lane glyphs, written here by hand: the fill, the track, and the end cell, which is the
// prompt's state glyph.
const FILL = '\u{25AC}'
const TRACK = '.'
const END: Record<string, string> = { done: '\u{2713}', blocked: '\u{2717}', running: '\u{25B8}', pending: '\u{25CC}', skipped: '\u{2298}' }
const NO_START = 'no start'
const WORD = 'lanes withheld'
const LANE = new RegExp('^p(\\d+) +([\\u{25AC}.\\u{2713}\\u{2717}\\u{25B8}\\u{25CC}\\u{2298}?]+|no start)$', 'u')

async function load($: any, on: any, o: Opts) {
  install(on, o)
  await $.command.run({ command: 'crux-dashboard' } as any)
}
const withWidth = (base: Record<string, unknown>, w: number | undefined) => {
  const { bodyColumns: _, ...rest } = base
  return w === undefined ? rest : { ...rest, bodyColumns: w }
}
async function drawPane($: any, w: number | undefined, placement: 'inline' | 'dock') {
  const ui = await $.ui.mount({ plugin: 'crux-mods', surface: 'terminal', component: 'Pane', requestId: 'crux-dashboard', props: { ...withWidth(PANE, w), placement } })
  const tree = await ui.drawn()
  await ui.unmount()
  return tree
}
async function drawBand($: any, w: number | undefined) {
  const ui = await $.ui.mount({ plugin: 'crux-mods', surface: 'terminal', component: 'AbovePrompt', props: withWidth(BAND, w) })
  const tree = await ui.drawn()
  await ui.unmount()
  return tree
}

type Lane = { n: number; body: string; text: string; inner: number }
function lanesOf(tree: unknown, w: number): Lane[] {
  const out: Lane[] = []
  for (const l of layout(tree, w).lines) {
    const m = LANE.exec(l.text)
    if (m !== null) out.push({ n: Number(m[1]), body: m[2]!, text: l.text, inner: l.limit - l.left })
  }
  return out
}
function fits(tree: unknown, w: number, label: string) {
  const l = layout(tree, w)
  expect([label, overflows(l)]).toEqual([label, []])
  expect([label, widest(l) <= w]).toEqual([label, true])
  expect([label, [...new Set(l.types)].filter(t => t !== 'Box' && t !== 'Text')]).toEqual([label, []])
}

// The span-to-cells rule, written out here apart from view.ts's laneCells: the start floored, the
// end ceiled, one cell at least, the product before the division.
function expected(L: number, A: number, B: number, s: number, e: number, state: string): string {
  const T = B - A
  let lo = T === 0 ? 0 : Math.floor(((Math.max(s, A) - A) * L) / T)
  let hi = T === 0 ? 1 : Math.ceil(((Math.min(e, B) - A) * L) / T)
  lo = Math.min(lo, L - 1)
  hi = Math.min(L, Math.max(hi, lo + 1))
  return TRACK.repeat(lo) + FILL.repeat(hi - lo - 1) + END[state] + TRACK.repeat(L - hi)
}

// --- the lanes ------------------------------------------------------------------------------------

test('an in-progress run draws one lane per prompt on one shared axis at every width, each row inside the width', async ($, on) => {
  await load($, on, { reader: ok(READER_OK), agents: [] })
  for (const w of WIDTHS) {
    const tree = await drawPane($, w, 'dock')
    fits(tree, dw(w), `dock ${w}`)
    const lanes = lanesOf(tree, dw(w))
    expect([w, lanes.map(l => l.n)]).toEqual([w, [1, 2, 3, 4]])
    const L = lanes[0]!.inner - 3
    expect([w, L >= 10]).toEqual([w, true])
    const A = RUN.started_s, B = NOW_S
    const [p1, p2, p3] = RUN.prompts
    expect([w, lanes.map(l => l.body)]).toEqual([w, [
      expected(L, A, B, p1!.started_s!, p1!.completed_s!, 'done'),
      expected(L, A, B, p2!.started_s!, B, 'blocked'),
      expected(L, A, B, p3!.started_s!, B, 'running'),
      NO_START,
    ]])
  }
})

test('lanes pinned by hand at 30 columns: the running prompt runs to now_s at the right edge', async ($, on) => {
  await load($, on, { reader: ok(READER_OK), agents: [] })
  const lanes = lanesOf(await drawPane($, 30, 'dock'), 30)
  expect(lanes.map(l => l.text)).toEqual([
    'p1 ' + FILL.repeat(6) + '\u{2713}' + TRACK.repeat(20),
    'p2 ' + TRACK.repeat(7) + FILL.repeat(19) + '\u{2717}',
    'p3 ' + TRACK.repeat(24) + FILL.repeat(2) + '\u{25B8}',
    'p4 no start',
  ])
})

test('the running span follows now_s and nothing else', async ($, on) => {
  await load($, on, { reader: ok(readerAt(NOW_S + 7839)), agents: [] })
  const lanes = lanesOf(await drawPane($, 30, 'dock'), 30)
  const L = 27, A = RUN.started_s, B = NOW_S + 7839
  expect(lanes.find(l => l.n === 3)?.body).toBe(expected(L, A, B, RUN.prompts[2]!.started_s!, B, 'running'))
  expect(lanes.find(l => l.n === 1)?.body).toBe(expected(L, A, B, RUN.prompts[0]!.started_s!, RUN.prompts[0]!.completed_s!, 'done'))
})

for (const [label, doc] of [['now', IDLE_LATEST], ['no clock', { ...IDLE_LATEST, now_s: null }]] as const) {
  test(`the last-run panel draws lanes from last_completed on an axis from start to completion (${label})`, async ($, on) => {
    await load($, on, { reader: ok(doc), agents: [] })
    const lanes = lanesOf(await drawPane($, 30, 'dock'), 30)
    expect(lanes.map(l => l.text)).toEqual([
      'p1 ' + FILL.repeat(5) + '\u{2713}' + TRACK.repeat(21),
      'p2 ' + TRACK.repeat(5) + FILL.repeat(15) + '\u{2713}' + TRACK.repeat(6),
      'p3 no start',
      'p4 ' + TRACK.repeat(20) + FILL.repeat(6) + '\u{2713}',
    ])
  })
}

// Paired with the first lane test, which draws the lanes for the same run with now_s set.
test('now_s null omits the in-progress axis and keeps the completed prompt duration', async ($, on) => {
  await load($, on, { reader: ok(readerAt(null)), agents: [] })
  const tree = await drawPane($, 400, 'dock')
  expect(lanesOf(tree, 400)).toEqual([])
  expect(layout(tree, 400).lines.map(l => l.text)).toContain(`p1  done  adr-1  ${HOSTILE_TITLE}  33m`)
})

test('a prompt with no start time draws no segment and says so in a word', async ($, on) => {
  const doc = clone(READER_OK)
  doc.runs[0].prompts[0].started_s = null
  await load($, on, { reader: ok(doc), agents: [] })
  const lanes = lanesOf(await drawPane($, 60, 'dock'), 60)
  expect(lanes.filter(l => l.body === NO_START).map(l => l.n)).toEqual([1, 4])
})

test('a zero-length span draws one cell, its state glyph', async ($, on) => {
  const doc = clone(READER_OK)
  doc.runs[0].prompts[0].completed_s = doc.runs[0].prompts[0].started_s
  await load($, on, { reader: ok(doc), agents: [] })
  const lanes = lanesOf(await drawPane($, 30, 'dock'), 30)
  expect(lanes.find(l => l.n === 1)?.body).toBe('\u{2713}' + TRACK.repeat(26))
})

test('the threshold: lanes of 10 cells draw at 13 columns, and at 12 no lane draws', async ($, on) => {
  await load($, on, { reader: ok(READER_OK), agents: [] })
  const at = await drawPane($, 13, 'dock')
  expect(lanesOf(at, 13).map(l => l.body.length === 10 || l.body === NO_START)).toEqual([true, true, true, true])
  const below = await drawPane($, 12, 'dock')
  expect(lanesOf(below, 12)).toEqual([])
})

test('the two-column layout draws the lanes in the left run panel', async ($, on) => {
  await load($, on, { reader: ok(READER_OK), agents: [] })
  for (const w of [110, 120]) {
    const tree: any = await drawPane($, w, 'dock')
    const row = tree.children.flat(Infinity).find((c: any) => c?.props?.flexDirection === 'row')
    const [left, right] = row.children.flat(Infinity).filter((c: any) => c?.type === 'Box')
    const col = Math.floor((w - 2) / 2)
    expect([w, lanesOf(left, col).length, lanesOf(right, col).length]).toEqual([w, 4, 0])
  }
})

for (const [label, doc] of [['live', READER_OK], ['last run', IDLE_LATEST]] as const) {
  test(`the inline mini layout draws no lane and at most 8 rows at every width (${label})`, async ($, on) => {
    await load($, on, { reader: ok(doc), agents: [] })
    for (const w of [...WIDTHS, 1, 5, 13, 29]) {
      const tree = await drawPane($, w, 'inline')
      fits(tree, dw(w), `inline ${w}`)
      expect([w, lanesOf(tree, dw(w)), layout(tree, dw(w)).rows <= 8]).toEqual([w, [], true])
    }
  })
}

test('the band draws no lane', async ($, on) => {
  await load($, on, { reader: ok(READER_OK), agents: [] })
  for (const w of WIDTHS) expect([w, lanesOf(await drawBand($, w), dw(w))]).toEqual([w, []])
})

test('the pane draws with every clock read throwing', () => {
  expect(() => withoutClock(() => {
    for (const doc of [READER_OK, readerAt(null), IDLE_LATEST]) for (const w of [...WIDTHS, 12, 13]) {
      draw.pane(P(doc), agents([]), w, 'docked', HARNESS)
      draw.pane(P(doc), agents([]), w, 'mini', HARNESS)
    }
  })).not.toThrow()
})

test('the lane glyphs are one cell, not Ambiguous, and no emoji', () => {
  const inAmbiguous = (cp: number) => AMBIGUOUS.some(([lo, hi]) => cp >= lo && cp <= hi)
  const emoji = [new RegExp('\\p{Emoji}', 'u'), new RegExp('\\p{Emoji_Presentation}', 'u'), new RegExp('\\p{Extended_Pictographic}', 'u')]
  for (const g of [FILL, TRACK]) {
    expect([g, Array.from(g).length, inAmbiguous(g.codePointAt(0)!), emoji.map(re => re.test(g))]).toEqual([g, 1, false, [false, false, false]])
  }
  // Positive controls: the box-drawing line and the middle dot are Ambiguous; the black small square is an emoji.
  expect([inAmbiguous(0x2500), inAmbiguous(0xb7), emoji[0]!.test('\u{25AA}')]).toEqual([true, true, true])
})

// --- the times rows, the prompt rows and the status rule ------------------------------------------
// Expected rows are literals from an oracle written apart from the production code.

const AGENT = { id: 'a1', description: 'Plan the thing', type: 'developer', status: 'running' }
const NAMED: [string, number | undefined][] = [['30', 30], ['40', 40], ['60', 60], ['86', 86], ['110', 110], ['120', 120], ['none', undefined]]
const TIMES = /^(started|completed|elapsed|took) /
const PROMPT_ROW = new RegExp('^(\\u{25B8} )?p\\d+  (done|blocked|running|pending|skipped|\\?)(  |$)', 'u')
const ELL = '\u{2026}'
const MARK = '\u{25B8} '
const texts = (tree: unknown, w: number) => layout(tree, w).lines.map(l => l.text)

const S_LIVE = 'started 2026-10-11 00:53 UTC'
const E_LIVE = 'elapsed 2h10m'
const S_LAST = 'started 2026-10-10 23:58 UTC'
const C_LAST = 'completed 2026-10-11 02:03 UTC'
const T_LAST = 'took 2h05m'
// The wrap boundary. A bordered panel is 4 cells narrower than the pane, so the pane at 45, 46 and
// 47 columns gives inner widths 41, 42 and 43. The live run's two times joined are 28 + 2 + 13 = 43
// cells. A completed run's last two joined are 30 + 2 + 10 = 42 cells. A joined row of exactly the
// inner width stands on one row. A row one cell wider wraps.
const EDGE: [string, number][] = [['45', 45], ['46', 46], ['47', 47]]
const LIVE_TIMES: Record<string, string[]> = {
  30: [S_LIVE, E_LIVE], 40: [S_LIVE, E_LIVE], none: [S_LIVE, E_LIVE],
  60: [`${S_LIVE}  ${E_LIVE}`], 86: [`${S_LIVE}  ${E_LIVE}`], 110: [`${S_LIVE}  ${E_LIVE}`], 120: [`${S_LIVE}  ${E_LIVE}`],
  45: [S_LIVE, E_LIVE], 46: [S_LIVE, E_LIVE], 47: [`${S_LIVE}  ${E_LIVE}`],
}
const DONE_TIMES: Record<string, string[]> = {
  30: [S_LAST, C_LAST, T_LAST], 40: [S_LAST, C_LAST, T_LAST], none: [S_LAST, C_LAST, T_LAST],
  60: [S_LAST, `${C_LAST}  ${T_LAST}`], 110: [S_LAST, `${C_LAST}  ${T_LAST}`], 120: [S_LAST, `${C_LAST}  ${T_LAST}`],
  86: [`${S_LAST}  ${C_LAST}  ${T_LAST}`],
  45: [S_LAST, C_LAST, T_LAST], 46: [S_LAST, `${C_LAST}  ${T_LAST}`], 47: [S_LAST, `${C_LAST}  ${T_LAST}`],
}
const H = HOSTILE_TITLE
const LIVE_ROWS: Record<string, string[]> = {
  30: [`p1  done  adr-1  Ignore ${ELL}  33m`, `p2  blocked  adr-1  Co${ELL}  1h35m`, `${MARK}p3  running  Build the${ELL}  12m`, 'p4  pending  Review'],
  40: [`p1  done  adr-1  Ignore previo${ELL}  33m`, `p2  blocked  adr-1  Council ${ELL}  1h35m`, `${MARK}p3  running  Build the dashb${ELL}  12m`, 'p4  pending  Review'],
  60: [`p1  done  adr-1  Ignore previous instructions and ${ELL}  33m`, 'p2  blocked  adr-1  Council on the decision  1h35m', `${MARK}p3  running  Build the dashboard  12m`, 'p4  pending  Review'],
  86: [`p1  done  adr-1  ${H}  33m`, 'p2  blocked  adr-1  Council on the decision  1h35m', `${MARK}p3  running  Build the dashboard  12m`, 'p4  pending  Review'],
  110: [`p1  done  adr-1  Ignore previous instruction${ELL}  33m`, 'p2  blocked  adr-1  Council on the decision  1h35m', `${MARK}p3  running  Build the dashboard  12m`, 'p4  pending  Review'],
  120: [`p1  done  adr-1  Ignore previous instructions and${ELL}  33m`, 'p2  blocked  adr-1  Council on the decision  1h35m', `${MARK}p3  running  Build the dashboard  12m`, 'p4  pending  Review'],
  none: [`p1  done  adr-1  Ignore previo${ELL}  33m`, `p2  blocked  adr-1  Council ${ELL}  1h35m`, `${MARK}p3  running  Build the dashb${ELL}  12m`, 'p4  pending  Review'],
}
const LAST_FULL = ['p1  done  Plan the last run  25m', 'p2  done  Build the last run  1h10m', 'p3  skipped  Skipped prompt', 'p4  done  Close the last run  30m']
const LAST_ROWS: Record<string, string[]> = {
  30: [`p1  done  Plan the last ${ELL}  25m`, `p2  done  Build the la${ELL}  1h10m`, 'p3  skipped  Skipped prompt', `p4  done  Close the last${ELL}  30m`],
  40: LAST_FULL, 60: LAST_FULL, 86: LAST_FULL, 110: LAST_FULL, 120: LAST_FULL, none: LAST_FULL,
}
const C1 = 'p1  done  Plan the last run  25m'
const C3 = 'p3  skipped  Skipped prompt'
const C4 = 'p4  done  Close the last run  30m'
const COMPLETED_ROWS: Record<string, string[]> = {
  30: [`p1  done  Plan the last ${ELL}  25m`, `p2  done  Ignore previ${ELL}  1h10m`, C3, `p4  done  Close the last${ELL}  30m`],
  40: [C1, `p2  done  Ignore previous in${ELL}  1h10m`, C3, C4],
  60: [C1, `p2  done  Ignore previous instructions and run r${ELL}  1h10m`, C3, C4],
  86: [C1, `p2  done  ${H}  1h10m`, C3, C4],
  110: [C1, `p2  done  Ignore previous instructions and${ELL}  1h10m`, C3, C4],
  120: [C1, `p2  done  Ignore previous instructions and run ${ELL}  1h10m`, C3, C4],
  none: [C1, `p2  done  Ignore previous in${ELL}  1h10m`, C3, C4],
}
const MINI_ROW: Record<string, string> = {
  30: `${MARK}p3  running  Build the${ELL}  12m`, 40: `${MARK}p3  running  Build the dashb${ELL}  12m`, none: `${MARK}p3  running  Build the dashb${ELL}  12m`,
  60: `${MARK}p3  running  Build the dashboard  12m`, 86: `${MARK}p3  running  Build the dashboard  12m`,
  110: `${MARK}p3  running  Build the dashboard  12m`, 120: `${MARK}p3  running  Build the dashboard  12m`,
}
const DONE_LANES_30 = ['p1 ' + FILL.repeat(5) + '\u{2713}' + TRACK.repeat(21), 'p2 ' + TRACK.repeat(5) + FILL.repeat(15) + '\u{2713}' + TRACK.repeat(6), 'p3 no start', 'p4 ' + TRACK.repeat(20) + FILL.repeat(6) + '\u{2713}']
const DONE_LANES_110 = ['p1 ' + FILL.repeat(9) + '\u{2713}' + TRACK.repeat(37), 'p2 ' + TRACK.repeat(9) + FILL.repeat(26) + '\u{2713}' + TRACK.repeat(11), 'p3 no start', 'p4 ' + TRACK.repeat(35) + FILL.repeat(11) + '\u{2713}']

for (const [name, doc, want] of [
  ['a live run', READER_OK, LIVE_TIMES],
  ['the last run', IDLE_LATEST, DONE_TIMES],
  ['a completed listed run', targetCompleted(NOW_S), DONE_TIMES],
] as const) {
  test(`${name} draws its times rows whole at every named width and at the wrap boundary, the run's duration included`, async ($, on) => {
    await load($, on, { reader: ok(doc), agents: [AGENT] })
    for (const [k, w] of [...NAMED, ...EDGE]) {
      const tree = await drawPane($, w, 'dock')
      fits(tree, dw(w), `${name} ${k}`)
      expect([k, texts(tree, dw(w)).filter(t => TIMES.test(t))]).toEqual([k, want[k]])
    }
  })
}

for (const [name, doc, want] of [
  ['a live run', READER_OK, LIVE_ROWS],
  ['the last run', IDLE_LATEST, LAST_ROWS],
  ['a completed listed run', targetCompleted(NOW_S), COMPLETED_ROWS],
] as const) {
  test(`${name} keeps every prompt duration whole at every named width; the title gives way first`, async ($, on) => {
    await load($, on, { reader: ok(doc), agents: [AGENT] })
    for (const [k, w] of NAMED) {
      expect([k, texts(await drawPane($, w, 'dock'), dw(w)).filter(t => PROMPT_ROW.test(t))]).toEqual([k, want[k]])
    }
  })
}

for (const [label, now] of [['now_s after completion', NOW_S], ['now_s 30 days later', NOW_S + 30 * 86400], ['now_s null', null]] as const) {
  test(`a completed listed run (${label}) draws its axis, its duration and its prompt durations from recorded times only`, async ($, on) => {
    await load($, on, { reader: ok(targetCompleted(now)), agents: [AGENT] })
    const at30 = await drawPane($, 30, 'dock')
    expect(texts(at30, 30).filter(t => TIMES.test(t))).toEqual(DONE_TIMES[30])
    expect(lanesOf(at30, 30).map(l => l.text)).toEqual(DONE_LANES_30)
    expect(texts(at30, 30).filter(t => PROMPT_ROW.test(t))).toEqual(COMPLETED_ROWS[30])
    const at110 = await drawPane($, 110, 'dock')
    expect(lanesOf(at110, 110).map(l => l.text)).toEqual(DONE_LANES_110)
    expect(texts(at110, 110).some(t => t.includes('elapsed'))).toBe(false)
  })
}

for (const [label, now] of [['now_s set', NOW_S], ['now_s null', null]] as const) {
  test(`an abandoned listed run (${label}) draws recorded times only: its running prompt has no duration and an empty track`, async ($, on) => {
    await load($, on, { reader: ok(targetAbandoned(now)), agents: [] })
    const tree = await drawPane($, 60, 'dock')
    const t = texts(tree, 60)
    expect(t.filter(x => TIMES.test(x))).toEqual([S_LAST, `${C_LAST}  ${T_LAST}`])
    expect(t.filter(x => PROMPT_ROW.test(x))).toEqual(['p1  done  Plan the last run  25m', 'p2  running  Build the last run', 'p3  pending  Third', 'p4  pending  Fourth'])
    expect(lanesOf(tree, 60).map(l => l.text)).toEqual(['p1 ' + FILL.repeat(10) + '\u{2713}' + TRACK.repeat(42), 'p2 ' + TRACK.repeat(53), 'p3 no start', 'p4 no start'])
  })
}

test('the mini layout keeps the current prompt\'s elapsed time whole at every named width', async ($, on) => {
  await load($, on, { reader: ok(READER_OK), agents: [] })
  for (const [k, w] of NAMED) {
    const tree = await drawPane($, w, 'inline')
    fits(tree, dw(w), `inline ${k}`)
    expect([k, texts(tree, dw(w)).filter(t => t.startsWith(`${MARK}p3  `))]).toEqual([k, [MINI_ROW[k]]])
  }
})

test('below 30 columns each prompt row keeps its duration down to the width its fixed fields take (18 here)', async ($, on) => {
  await load($, on, { reader: ok(READER_OK), agents: [] })
  for (let w = 18; w <= 29; w++) {
    const rows = texts(await drawPane($, w, 'dock'), w).filter(t => PROMPT_ROW.test(t))
    expect([w, rows.length, rows[0]!.endsWith('  33m'), rows[1]!.endsWith('  1h35m'), rows[2]!.endsWith('  12m')]).toEqual([w, 4, true, true, true])
  }
})

test('the widest fixed fields the view admits keep their duration at 30 columns', async ($, on) => {
  const doc = clone(READER_OK)
  const r = doc.runs[0]
  r.started_s = 0
  r.current_prompt = 10000
  r.prompts = [{ n: 10000, state: 'running', module_tag: 'implementation-12', title: H, started_s: 0, completed_s: null }]
  doc.now_s = 4102444800
  await load($, on, { reader: ok(doc), agents: [] })
  const tree = await drawPane($, 30, 'dock')
  fits(tree, 30, 'widest fixed fields')
  expect(texts(tree, 30).filter(t => PROMPT_ROW.test(t))).toEqual([`${MARK}p10000  running  1139568h00m`])
  expect(texts(tree, 30).filter(t => TIMES.test(t))).toEqual(['started 1970-01-01 00:00 UTC', 'elapsed 1139568h00m'])
})

test('a zero-length span at the axis end takes the last cell', async ($, on) => {
  await load($, on, { reader: ok(READER_ZERO_AT_END), agents: [] })
  expect(lanesOf(await drawPane($, 30, 'dock'), 30).map(l => l.text)).toEqual([
    'p1 ' + FILL.repeat(6) + '\u{2713}' + TRACK.repeat(20), 'p2 ' + TRACK.repeat(7) + FILL.repeat(19) + '\u{2717}', 'p3 ' + TRACK.repeat(26) + '\u{25B8}', 'p4 no start',
  ])
})

test('a live run read in the very second it started keeps its lanes: the axis has zero length, and its end is not before its start', async ($, on) => {
  await load($, on, { reader: ok(readerAt(RUN.started_s)), agents: [] })
  const tree = await drawPane($, 30, 'dock')
  expect(lanesOf(tree, 30).map(l => l.text)).toEqual(['p1 \u{2713}' + TRACK.repeat(26), 'p2 ' + TRACK.repeat(27), 'p3 ' + TRACK.repeat(27), 'p4 no start'])
  expect(texts(tree, 30).filter(t => TIMES.test(t))).toEqual([S_LIVE, 'elapsed 0m'])
})

test('a run in progress whose file carries a completion time still runs to now_s: elapsed time and an axis to now_s, never completed or took', async ($, on) => {
  const doc = clone(READER_OK)
  doc.runs[0].completed_s = RUN.started_s + 600
  await load($, on, { reader: ok(doc), agents: [] })
  const tree = await drawPane($, 30, 'dock')
  expect(texts(tree, 30).filter(t => TIMES.test(t))).toEqual([S_LIVE, E_LIVE])
  expect(lanesOf(tree, 30).map(l => l.text)).toEqual(['p1 ' + FILL.repeat(6) + '\u{2713}' + TRACK.repeat(20), 'p2 ' + TRACK.repeat(7) + FILL.repeat(19) + '\u{2717}', 'p3 ' + TRACK.repeat(24) + FILL.repeat(2) + '\u{25B8}', 'p4 no start'])
})

test('laneCells, the cell table: start floored, end ceiled, one cell at least, wholly-outside spans rejected first, ends inclusive', () => {
  const ax = { from: 0, to: 100 }
  const cases: [number, number, [number, number] | null][] = [
    [0, 0, [0, 1]], [100, 100, [9, 10]], [0, 100, [0, 10]], [5, 15, [0, 2]], [10, 20, [1, 2]], [11, 12, [1, 2]],
    [-50, 0, [0, 1]], [100, 150, [9, 10]], [-50, -1, null], [101, 150, null], [-50, 150, [0, 10]], [99, 100, [9, 10]],
  ]
  for (const [s, e, want] of cases) expect([s, e, view.laneCells(ax, { from: s, to: e }, 10)]).toEqual([s, e, want])
  const zero = { from: 50, to: 50 }
  for (const [s, e, want] of [[50, 50, [0, 1]], [40, 50, [0, 1]], [50, 60, [0, 1]], [40, 49, null], [51, 60, null]] as [number, number, [number, number] | null][]) {
    expect(['zero', s, e, view.laneCells(zero, { from: s, to: e }, 10)]).toEqual(['zero', s, e, want])
  }
  const wide = { from: 0, to: 4102444800 }
  expect(view.laneCells(wide, { from: 4102444799, to: 4102444800 }, 400)).toEqual([399, 400])
  expect(view.laneCells(wide, { from: 1, to: 2 }, 400)).toEqual([0, 1])
  // Quotients 9 and 18, both whole.
  expect(view.laneCells({ from: 0, to: 7500 }, { from: 2500, to: 5000 }, 27)).toEqual([9, 18])
  // End quotient 5.4, ceiled to 6.
  expect(view.laneCells({ from: 0, to: 7500 }, { from: 0, to: 1500 }, 27)).toEqual([0, 6])
  // The product comes before the division. 1 * 49 / 49 is 1 exactly; 1 / 49 * 49 is
  // 0.9999999999999999, whose floor would put the span in cell 0.
  expect(1 / 49 * 49 < 1).toBe(true)
  expect(view.laneCells({ from: 0, to: 49 }, { from: 1, to: 2 }, 49)).toEqual([1, 2])
  expect(view.laneCells({ from: 0, to: 49 }, { from: 48, to: 49 }, 49)).toEqual([48, 49])
})

for (const [label, ns, at, below] of [
  ['a widest label of 2 cells', range(9), 13, 12],
  ['a widest label of 3 cells', range(10), 14, 13],
  ['a widest label of 4 cells (100 prompts)', range(100), 15, 14],
  ['a sparse widest label of 6 cells', [1, 2, 10000], 17, 16],
] as const) {
  test(`the threshold follows the widest label: ${label} draws lanes of 10 cells at ${at} and none at ${below}`, async ($, on) => {
    await load($, on, { reader: ok(readerOf([...ns])), agents: [] })
    const lanes = lanesOf(await drawPane($, at, 'dock'), at)
    expect([lanes.length, lanes.every(l => Array.from(l.body).length === 10)]).toEqual([ns.length, true])
    expect(lanesOf(await drawPane($, below, 'dock'), below)).toEqual([])
  })
}

test('the lane cap: a run of 100 prompts draws 100 lanes', async ($, on) => {
  await load($, on, { reader: ok(readerOf(range(100))), agents: [] })
  expect(lanesOf(await drawPane($, 400, 'dock'), 400).length).toBe(100)
})

test('five shown runs of 100 prompts draw 500 lanes at 400 and 30 columns, within both kit limits', async ($, on) => {
  await load($, on, { reader: ok(readerOf(range(100), 6)), agents: [] })
  for (const [w, L] of [[400, 120], [30, 25]]) {
    const tree = await drawPane($, w, 'dock')
    const lanes = lanesOf(tree, w)
    const units = layout(tree, w).lines.reduce((n, l) => n + l.text.length, 0)
    expect([w, lanes.length, lanes.every(l => Array.from(l.body).length === L), units < 100000]).toEqual([w, 500, true, true])
  }
})

test('a lane stops growing at 120 cells: 113 cells in a one-column pane at 120 columns, 120 at 400', async ($, on) => {
  await load($, on, { reader: ok(IDLE_LATEST), agents: [] })
  for (const [w, L] of [[120, 113], [400, 120]]) {
    const lanes = lanesOf(await drawPane($, w, 'dock'), w).filter(l => l.body !== NO_START)
    expect([w, lanes.length, lanes.every(l => Array.from(l.body).length === L)]).toEqual([w, 3, true])
  }
})

for (const k of [101, 500]) {
  test(`a run of ${k} prompts draws no lanes and keeps every prompt row`, async ($, on) => {
    await load($, on, { reader: ok(readerOf(range(k))), agents: [] })
    const tree = await drawPane($, 400, 'dock')
    expect([lanesOf(tree, 400).length, texts(tree, 400).filter(t => PROMPT_ROW.test(t)).length]).toEqual([0, k])
  })
}

test('five shown runs of 500 prompts still draw, with no lanes', async ($, on) => {
  await load($, on, { reader: ok(readerOf(range(500), 6)), agents: [] })
  const tree = await drawPane($, 400, 'dock')
  expect([lanesOf(tree, 400).length, texts(tree, 400).filter(t => PROMPT_ROW.test(t)).length]).toEqual([0, 2500])
})

for (const [name, doc] of [
  ['a completed listed run', targetCompleted(NOW_S)], ['a completed listed run with no clock', targetCompleted(null)],
  ['an abandoned listed run', targetAbandoned(NOW_S)], ['a zero-length span at the axis end', READER_ZERO_AT_END],
  ['a sparse widest label', readerOf([1, 2, 10000])], ['100 prompts', readerOf(range(100))],
] as const) {
  test(`${name}: the band and both pane layouts fit every width`, async ($, on) => {
    await load($, on, { reader: ok(doc), agents: [AGENT] })
    for (const w of [...WIDTHS, 1, 2, 5, 10, 12, 13, 14, 15, 16, 17, 18, 29]) {
      fits(await drawBand($, w), dw(w), `${name} band ${w}`)
      fits(await drawPane($, w, 'inline'), dw(w), `${name} inline ${w}`)
      fits(await drawPane($, w, 'dock'), dw(w), `${name} dock ${w}`)
    }
  })
}

test('the clock guard throws on Date() and on new Date without parentheses, and the pane draws the axis fixtures under it', () => {
  expect(() => withoutClock(() => { (Date as any)() })).toThrow()
  expect(() => withoutClock(() => { new (Date as any) })).toThrow()
  expect(() => withoutClock(() => { new Date(1000) })).not.toThrow()
  expect(() => withoutClock(() => {
    for (const doc of [targetCompleted(NOW_S), targetCompleted(null), targetAbandoned(NOW_S), READER_ZERO_AT_END, readerOf(range(100))]) {
      for (const w of [...WIDTHS, 12, 13, 29]) {
        draw.pane(P(doc), agents([]), w, 'docked', HARNESS)
        draw.pane(P(doc), agents([]), w, 'mini', HARNESS)
      }
    }
  })).not.toThrow()
})

// Every shape of a clock read, including Date() and new Date with no parentheses; a Date from a number passes.
const CLOCK_ANY = new RegExp('\\bDate\\s*\\.\\s*now\\b|\\bperformance\\s*\\.\\s*now\\b|\\bnew\\s+Date\\s*\\(\\s*\\)|\\bnew\\s+Date\\b(?!\\s*\\()|(?<!\\bnew\\s+)\\bDate\\s*\\(')
test('no export of draw.ts or view.ts names a clock read in any of five shapes', () => {
  for (const [s, hit] of [
    ['Date.now()', true], ['performance.now()', true], ['new Date()', true], ['new Date;', true], ['x = Date()', true], ['Date ( )', true],
    ['new Date(s * 1000)', false], ['d.getUTCDate()', false], ['utc(s)', false],
  ] as [string, boolean][]) expect([s, CLOCK_ANY.test(s)]).toEqual([s, hit])
  const sources = [...Object.values(draw), ...Object.values(view)].filter(v => typeof v === 'function').map(f => String(f))
  expect(sources.length).toBeGreaterThan(40)
  expect(sources.filter(s => CLOCK_ANY.test(s))).toEqual([])
  expect(sources.some(s => s.includes('new Date(s * 1e3)') || s.includes('new Date(s * 1000)'))).toBe(true)
})

test('a prompt with a start and no usable end draws the empty track, never a guessed segment', async ($, on) => {
  const doc = clone(READER_OK)
  doc.runs[0].prompts[3] = { ...doc.runs[0].prompts[3], state: 'pending', started_s: RUN.started_s + 10 }
  await load($, on, { reader: ok(doc), agents: [] })
  const lanes = lanesOf(await drawPane($, 30, 'dock'), 30)
  expect([lanes.length, lanes.find(l => l.n === 4)?.body]).toEqual([4, TRACK.repeat(27)])
})

// --- the pane's budget ----------------------------------------------------------------------------
// Expected rows are literals or follow the rule as this file writes it out. Every size is hand
// arithmetic from the fixture's parameters, checked against this file's own count of the drawn tree.

const BUDGET_UNITS = 90000
const BUDGET_NODES = 18000
// The drawn tree's size as the kit counts it: every element and every string a node, and the text
// as the strings' UTF-16 code units.
function drawnSize(n: unknown): { units: number; nodes: number } {
  if (typeof n === 'string') return { units: n.length, nodes: 1 }
  if (Array.isArray(n)) return n.map(drawnSize).reduce((a, b) => ({ units: a.units + b.units, nodes: a.nodes + b.nodes }), { units: 0, nodes: 0 })
  if (n === null || typeof n !== 'object') return { units: 0, nodes: 0 }
  const k = drawnSize((n as any).children)
  return { units: k.units, nodes: k.nodes + 1 }
}
// The strings of each drawn line: a Text that holds a Text per span, each holding its string.
function lineStrings(tree: unknown): string[][] {
  const out: string[][] = []
  const walk = (n: unknown) => {
    if (Array.isArray(n)) return n.forEach(walk)
    if (n === null || typeof n !== 'object') return
    const o = n as { type?: unknown; children?: unknown }
    const kids = [o.children].flat(Infinity).filter(k => k !== undefined && k !== null)
    if (o.type === 'Text' && kids.length > 0 && kids.every(k => typeof k === 'object' && (k as any).type === 'Text')) {
      out.push(kids.flatMap(k => [(k as any).children].flat(Infinity).filter((s: unknown) => typeof s === 'string')))
      return
    }
    walk(o.children)
  }
  walk(tree)
  return out
}
// The pane's lines cut into run panels: each panel starts at its run's header row.
function panels(tree: unknown, w: number): string[][] {
  const out: string[][] = []
  for (const t of texts(tree, w)) {
    if (/^PB-0149 RUN-00\d  /.test(t)) out.push([])
    out[out.length - 1]?.push(t)
  }
  return out
}
const SEAT_A = RUN.started_s
const DUR = /  (\d+m|\d+h\d\dm)$/
const LIVE_TIMES_ROW = `${S_LIVE}  ${E_LIVE}`
// Lane rows of a run of k prompts from seatRun at L cells: each prompt done in its own minute from the
// run's start, the last one running to now_s.
function seatLanes(k: number, L: number, now: number): string[] {
  const labelW = `p${k}`.length
  return Array.from({ length: k }, (_, j) => {
    const n = j + 1
    const s = SEAT_A + j * 60
    const last = n === k
    return `p${n}`.padEnd(labelW) + ' ' + expected(L, SEAT_A, now, s, last ? now : s + 60, last ? 'running' : 'done')
  })
}

// The sizes below follow the drawing's structure. The pane is a column Box (1 node) holding the
// legend line, the run panels and the reader line. A line is its Text, a Text per span and each
// span's string: 1 + 2 * spans nodes. A panel is its Box and its lines. At 400 columns a bordered
// panel is 396 cells wide inside, and a lane of p100 takes 5 cells of label and 120 cells.
//
// The legend of a seat-shape pane: ✓ done, ▸ running, untagged, ⊘ skipped, ✗ blocked, ◌ pending, 60
// code units in 13 spans after merging: 27 nodes. The reader line: 34 code units, 3 nodes.
//
// A seat-shape run panel of k prompts, all done in a minute each but the last, which runs:
//   header  `PB-0149 RUN-00i  in_progress  prompt k of k  P%`         1 span
//   strip   `untagged` and ` ` with k state glyphs, 9 + k code units    2 spans
//   bar     20 cells; 1 span at 99%, 2 spans at 66%
//   times   `started 2026-10-11 00:53 UTC  elapsed 2h10m`, 43         1 span
//   counts  `done k-1  skipped 0  blocked 0  running 1  pending 0`      1 span
//   prompts k rows of 1 span: `p<n>  done  <title>  1m`, the last `▸ p<k>  running  <title>  31m`
//   refused `refused council files 0`, 23                             1 span
// With a 1-span bar that is 1 + 3 + 5 + 3 + 3 + 3 + 3k + 3 = 21 + 3k nodes before any lane or word.
//
// The lanes of a seat-shape run of 100 prompts at 120 cells: the axis is 7839 s, so p1 [0, 60] and
// p2 [60, 120] both start in cell 0 and merge their label, fill and end glyph into one span: 2
// spans. p100 ends at cell 120 and drops its empty trailing track: 3 spans. The other 97 lanes draw
// label, track, fill with its glyph, and track: 4 spans. So 100 lines and 2 * (2 + 2 + 3 + 97 * 4) =
// 790 more nodes: 890 nodes, and 100 * 125 = 12500 code units. The word is 1 span: 3 nodes, 14
// code units.
const SEAT_LANE_NODES = 100 + 2 * (2 + 2 + 3 + 97 * 4)
// A seat-shape panel's code units at 400 columns, before any lane or word, for k prompts with titles
// of len characters. The last prompt starts 60 * (k - 1) s after the run, and its elapsed time to
// now_s, 7839 s after the run's start, is `last`: 31m for 100 prompts, 30m for 101, 2h08m for 3.
const seatPanel = (k: number, len: number, last: string) => {
  const header = `PB-0149 RUN-001  in_progress  prompt ${k} of ${k}  ${Math.floor(((k - 1) * 100) / k)}%`.length
  const counts = `done ${k - 1}  skipped 0  blocked 0  running 1  pending 0`.length
  let rows = 0
  for (let n = 1; n < k; n++) rows += `p${n}  done  `.length + len + '  1m'.length
  rows += `${MARK}p${k}  running  `.length + len + `  ${last}`.length
  return header + 'untagged '.length + k + 20 + LIVE_TIMES_ROW.length + counts + rows + 'refused council files 0'.length
}

test('the council\'s shape draws whole: the reader row last and every prompt row with its duration', async ($, on) => {
  await load($, on, { reader: ok(SEAT_SHAPE), agents: [] })
  const tree = await drawPane($, 400, 'dock')
  const lines = texts(tree, 400)
  const rows = lines.filter(t => PROMPT_ROW.test(t))
  expect([lines[lines.length - 1], rows.length, rows.every(t => DUR.test(t))]).toEqual(['reader 3.27.4  refused run files 0', 500, true])
  expect(rows.filter(t => t.startsWith(MARK)).map(t => t.slice(-5))).toEqual(['  31m', '  31m', '  31m', '  31m', '  31m'])
  const size = drawnSize(tree)
  expect([size.units <= BUDGET_UNITS, size.nodes <= BUDGET_NODES]).toEqual([true, true])
})

test('in the council\'s shape the budget admits the first two runs\' lanes and withholds the rest with the word, durations kept', async ($, on) => {
  await load($, on, { reader: ok(SEAT_SHAPE), agents: [] })
  const tree = await drawPane($, 400, 'dock')
  const ps = panels(tree, 400)
  expect(ps.length).toBe(5)
  const want = seatLanes(100, 120, NOW_S)
  for (const [i, p] of ps.entries()) {
    const lanes = p.filter(t => LANE.test(t))
    const at = p.indexOf(LIVE_TIMES_ROW)
    if (i < 2) expect([i, lanes, p.includes(WORD)]).toEqual([i, want, false])
    else expect([i, lanes.length, p[at + 1]]).toEqual([i, 0, WORD])
    // Durations stay whole in every panel, lanes or not.
    expect([i, at > 0, p.filter(t => PROMPT_ROW.test(t)).every(t => DUR.test(t))]).toEqual([i, true, true])
  }
  // Without lanes the pane is 59074 code units: five panels of 52 + 109 + 20 + 43 + 51 + 11498 + 23
  // = 11796, where 11498 is 9 rows of 114, 90 of 115 and the last of 122, then the legend's 60 and
  // the reader's 34. Its nodes are 1 + 27 + 5 * (21 + 300) + 3 = 1636. Two runs' lanes and three
  // words make 59074 + 2 * 12500 + 3 * 14 = 84116 code units and 1636 + 2 * 890 + 3 * 3 = 3425 nodes.
  expect([seatPanel(100, 100, '31m'), 5 * seatPanel(100, 100, '31m') + 60 + 34, SEAT_LANE_NODES]).toEqual([11796, 59074, 890])
  expect(drawnSize(tree)).toEqual({ units: 59074 + 2 * 12500 + 3 * WORD.length, nodes: 1636 + 2 * SEAT_LANE_NODES + 3 * 3 })
  expect(drawnSize(tree)).toEqual({ units: 84116, nodes: 3425 })
  // A third run's lanes would add 12500 less the word's 14, and pass the budget.
  expect(84116 + 12500 - 14 > BUDGET_UNITS).toBe(true)
})

// Run 1 of 100 prompts can draw lanes; runs 2 to 5, of 101 prompts, draw the word whatever the budget.
// Titles of 135 or 136 characters bring the drawing with run 1's lanes to 90000 code units exactly.
const textEdge = (m: number) => seatDoc([100, 101, 101, 101, 101], (run, n) => 135 + (run === 1 || run === 2 ? 1 : run === 3 && n <= m ? 1 : 0))
test('the text budget\'s edge, under: 90000 code units with run 1\'s lanes draws them', async ($, on) => {
  await load($, on, { reader: ok(textEdge(56)), agents: [] })
  const tree = await drawPane($, 400, 'dock')
  const ps = panels(tree, 400)
  expect([ps[0]!.filter(t => LANE.test(t)).length, ps[0]!.includes(WORD), ps.slice(1).map(p => p.includes(WORD))]).toEqual([100, false, [true, true, true, true]])
  // Code units: run 1's panel with titles of 135 and its lanes, runs 2 and 3 with titles of 136,
  // run 4 with 56 titles of 136 and 45 of 135, run 5 with titles of 135, each with its word, then the
  // legend and the reader. Nodes: run 1 is 21 + 300 + 890; runs 2 to 5 are 21 + 303 + 3 each.
  const units = seatPanel(100, 135, '31m') + 12500 + 2 * seatPanel(101, 136, '30m') + seatPanel(101, 135, '30m') + 56 + seatPanel(101, 135, '30m') + 4 * 14 + 60 + 34
  expect(units).toBe(90000)
  expect(drawnSize(tree)).toEqual({ units, nodes: 1 + 27 + (21 + 300 + SEAT_LANE_NODES) + 4 * (21 + 303 + 3) + 3 })
})

test('the text budget\'s edge, over: one code unit more withholds run 1\'s lanes with the word', async ($, on) => {
  await load($, on, { reader: ok(textEdge(57)), agents: [] })
  const tree = await drawPane($, 400, 'dock')
  const ps = panels(tree, 400)
  const lines = texts(tree, 400)
  // Run 1's lanes would add 100 lanes of p100, a space and 120 cells, less the word's 14: 90001.
  const units = drawnSize(tree).units
  expect([units, units + 100 * 125 - 14, ps[0]!.filter(t => LANE.test(t)).length, ps.map(p => p.includes(WORD)), lines[lines.length - 1]]).toEqual([77515, 90001, 0, [true, true, true, true, true], 'reader 3.27.4  refused run files 0'])
})

// The last run of 100 prompts at 15 columns: lanes of p100, a space and 10 cells, each of four spans
// (label, track, fill and glyph, track), so 9 nodes and 15 code units a lane. The word is one span.
test('the node budget\'s edge, under: 18000 nodes with lanes draws them, at about half the text budget', async ($, on) => {
  await load($, on, { reader: ok(nodeHeavyDoc(1581)), agents: [] })
  const tree = await drawPane($, 15, 'dock')
  const s = drawnSize(tree)
  expect([s.nodes, s.units < BUDGET_UNITS / 1.5, texts(tree, 15).filter(t => LANE.test(t)).length, texts(tree, 15).includes(WORD)]).toEqual([18000, true, 100, false])
})

test('the node budget\'s edge, over: three nodes more withhold the lanes with the word; the text did not drive it', async ($, on) => {
  await load($, on, { reader: ok(nodeHeavyDoc(1582)), agents: [] })
  const tree = await drawPane($, 15, 'dock')
  const s = drawnSize(tree)
  expect([s.nodes + 100 * 9 - 3, s.nodes <= BUDGET_NODES, s.units + 100 * 15 - 14 < BUDGET_UNITS / 1.5, texts(tree, 15).filter(t => LANE.test(t)).length, texts(tree, 15).includes(WORD)]).toEqual([18003, true, true, 0, true])
})

test('lanes are withheld whole runs at a time from the bottom run panel shown upward: a small fourth run waits behind a third that does not fit', async ($, on) => {
  await load($, on, { reader: ok(seatDoc([100, 100, 100, 3, 100], 150)), agents: [] })
  const tree = await drawPane($, 400, 'dock')
  const ps = panels(tree, 400)
  expect(ps.map(p => [p.filter(t => LANE.test(t)).length, p.includes(WORD)])).toEqual([[100, false], [0, true], [0, true], [0, true], [0, true]])
  // Code units: four panels of 100 prompts with titles of 150, run 1's lanes, a panel of 3 prompts
  // and four words, then the legend and the reader. Nodes: run 1 is 21 + 300 + 890; runs 2, 3 and 5
  // are 21 + 300 + 3; run 4's bar at 66% is 2 spans, so it is 21 + 2 + 9 + 3.
  const units = 4 * seatPanel(100, 150, '31m') + 12500 + seatPanel(3, 150, '2h08m') + 4 * 14 + 60 + 34
  expect(units).toBe(80530)
  expect(drawnSize(tree)).toEqual({ units, nodes: 1 + 27 + (21 + 300 + SEAT_LANE_NODES) + 3 * (21 + 300 + 3) + (21 + 2 + 9 + 3) + 3 })
  // The fourth run's three lanes alone would fit: 3 lanes of p3, a space and 120 cells, less the word.
  expect([units + 3 * 123 - 14 <= BUDGET_UNITS, units + 100 * 125 - 14 > BUDGET_UNITS]).toEqual([true, true])
})

test('a pane whose rows already pass the budget draws no lane output, the word included, and still draws whole', async ($, on) => {
  await load($, on, { reader: ok(seatDoc([100, 100, 100, 100, 100], 172)), agents: [] })
  const tree = await drawPane($, 400, 'dock')
  const lines = texts(tree, 400)
  expect([lines.filter(t => LANE.test(t)).length, lines.includes(WORD), lines[lines.length - 1]]).toEqual([0, false, 'reader 3.27.4  refused run files 0'])
  expect(lines.filter(t => PROMPT_ROW.test(t)).every(t => DUR.test(t))).toBe(true)
  // Each run draws its times on one row, as before the time axis.
  expect(panels(tree, 400).map(p => p.filter(t => TIMES.test(t)))).toEqual(Array(5).fill([LIVE_TIMES_ROW]))
  // The council's shape with 72 more title characters on each of its 500 prompt rows, and its nodes.
  expect(drawnSize(tree)).toEqual({ units: 59074 + 500 * 72, nodes: 1636 })
  expect(59074 + 500 * 72).toBe(95074)
})

// Five runs of k prompts with titles of 100 characters at 60 columns, where every prompt row is cut.
// 310 prompts a run keep the drawing with the words within the budget; 320 do not.
test('within the budget a cut prompt row keeps its duration, and each run of more than 100 prompts draws the word', async ($, on) => {
  await load($, on, { reader: ok(seatDoc([310, 310, 310, 310, 310], 100)), agents: [] })
  const tree = await drawPane($, 60, 'dock')
  const lines = texts(tree, 60)
  expect([lines.find(t => t.startsWith('p1  ')), lines.filter(t => t === WORD).length]).toEqual([`p1  done  Implement and test prompt 1 of the time a${ELL}  1m`, 5])
  // A bordered panel is 56 cells wide inside. Each panel: the header `... prompt 310 of 310  99%`,
  // 52; the strip, `untagged`, a space, the 43 cells nearest the running prompt and `+267`, 56; the
  // bar, 20; the times, 43; the word, 14; the counts, 52; 310 prompt rows of 56, the done rows cut in
  // their titles and the running row, which has no elapsed time, cut at its tail; refused files, 23.
  // Then the legend's 60 and the reader's 34.
  expect(drawnSize(tree).units).toBe(5 * (52 + 56 + 20 + 43 + 14 + 52 + 310 * 56 + 23) + 60 + 34)
  expect(5 * (52 + 56 + 20 + 43 + 14 + 52 + 310 * 56 + 23) + 60 + 34).toBe(88194)
})

test('past the budget the pane draws the rows it drew before the time axis: each prompt row cut at its tail, no word, no lane, and the reader row last', async ($, on) => {
  await load($, on, { reader: ok(seatDoc([320, 320, 320, 320, 320], 100)), agents: [] })
  const tree = await drawPane($, 60, 'dock')
  const lines = texts(tree, 60)
  expect([lines.find(t => t.startsWith('p1  ')), lines.includes(WORD), lines.filter(t => LANE.test(t)).length, lines[lines.length - 1]]).toEqual([`p1  done  Implement and test prompt 1 of the time axis ${ELL}`, false, 0, 'reader 3.27.4  refused run files 0'])
  // Each panel as in the test above with 320 prompts, `+277` after the strip's 43 cells, no word, and
  // every prompt row cut at its tail to 56 cells. Nodes: the panel's Box; the header, the bar, the
  // times, the counts, the refused files and each prompt row of 1 span; the strip of 3 spans.
  expect(drawnSize(tree)).toEqual({
    units: 5 * (52 + 56 + 20 + 43 + 52 + 320 * 56 + 23) + 60 + 34,
    nodes: 1 + 27 + 5 * (1 + 3 + 7 + 3 + 3 + 3 + 320 * 3 + 3) + 3,
  })
  expect([5 * (52 + 56 + 20 + 43 + 52 + 320 * 56 + 23) + 60 + 34 > BUDGET_UNITS, 1 + 27 + 5 * (1 + 3 + 7 + 3 + 3 + 3 + 320 * 3 + 3) + 3]).toEqual([true, 4946])
})

// The two-column layout at 150 columns: each column is (150 - 2) / 2 = 74 cells wide. A bordered run
// panel is 70 cells wide inside. There a lane of p100 takes 4 cells of label, a space and 65 cells:
// 70 code units. At the pane's 150 columns it would take 120 cells: 125 code units. Run 1, of
// 100 prompts, is the only run with lanes. Runs 2 to 5, of 301 prompts, draw the word whatever the
// budget. One agent puts the agents panel in the right column.
test('in the two-column layout the budget measures each run\'s lanes at its panel\'s inner width: past the budget with the words, the pane draws the rows it drew before the time axis', async ($, on) => {
  const agentRow = '\u{25B8}  developer  Plan the thing'
  await load($, on, { reader: ok(seatDoc([100, 301, 301, 301, 301], 100)), agents: [AGENT] })
  const tree: any = await drawPane($, 150, 'dock')
  const row = tree.children.flat(Infinity).find((c: any) => c?.props?.flexDirection === 'row')
  const [left, right] = row.children.flat(Infinity).filter((c: any) => c?.type === 'Box')
  const leftLines = texts(left, 74)
  expect([leftLines.filter(t => /^PB-0149 RUN-00\d  /.test(t)).length, leftLines[leftLines.length - 1], texts(right, 74)]).toEqual([5, 'reader 3.27.4  refused run files 0', ['Agents', agentRow]])
  const lines = texts(tree, 150)
  const rows = lines.filter(t => PROMPT_ROW.test(t))
  // No lane and no word. Every prompt row is cut at its tail to 70 cells, and the times stand on one row.
  expect([lines.filter(t => LANE.test(t)).length, lines.includes(WORD), rows.length, rows.every(t => t.length === 70 && t.endsWith(ELL))]).toEqual([0, false, 100 + 4 * 301, true])
  expect(rows[0]).toBe(`p1  done  Implement and test prompt 1 of the time axis abcdefghijabcd${ELL}`)
  expect(panels(tree, 150).map(p => p.filter(t => TIMES.test(t)))).toEqual(Array(5).fill([LIVE_TIMES_ROW]))
  // Code units: run 1's panel of 52 + 70 + 20 + 43 + 51 + 100 * 70 + 23, its strip `untagged`, a
  // space, the 58 cells nearest the running prompt and `+42`; four panels of 52 + 70 + 20 + 43 + 52 +
  // 301 * 70 + 23, each strip with 57 cells and `+244`; the legend's 60, the reader's 34, and the
  // agents panel's `Agents` and its row. Nodes: the pane's Box, the legend, the row's Box and each
  // column's Box; each run panel's Box, the strip of 3 spans and every other row of 1; the reader;
  // the agents panel's Box and its two rows.
  const units = (52 + 70 + 20 + 43 + 51 + 100 * 70 + 23) + 4 * (52 + 70 + 20 + 43 + 52 + 301 * 70 + 23) + 60 + 34 + 'Agents'.length + agentRow.length
  expect([units, agentRow.length]).toEqual([92707, 28])
  expect(drawnSize(tree)).toEqual({
    units,
    nodes: 1 + 27 + 1 + 1 + (1 + 3 + 7 + 3 + 3 + 3 + 100 * 3 + 3) + 4 * (1 + 3 + 7 + 3 + 3 + 3 + 301 * 3 + 3) + 3 + 1 + (1 + 3 + 3),
  })
  // With each run's word the pane is 92707 + 5 * 14 = 92777 code units, past the budget, so no run
  // keeps its lanes. Run 1's lanes add 100 * 70 - 14 = 6986 code units over its word, so the pane
  // with every run's lanes is 99763. Measured at the pane's width, its lanes would add
  // 100 * 125 - 14 = 12486, and the pane with the words would seem to be 99763 - 12486 = 87277,
  // inside the budget.
  expect([units + 5 * 14, units + 5 * 14 - 14 + 100 * 70, units + 5 * 14 - 14 + 100 * 70 - (100 * 125 - 14)]).toEqual([92777, 99763, 87277])
  expect([92777 > BUDGET_UNITS, 87277 <= BUDGET_UNITS, drawnSize(tree).nodes <= BUDGET_NODES]).toEqual([true, true, true])
})

test('a run of more than 100 prompts draws the word, dim, where its lanes would be, and every prompt row', async ($, on) => {
  await load($, on, { reader: ok(readerOf(range(101))), agents: [] })
  const tree = await drawPane($, 400, 'dock')
  const lines = texts(tree, 400)
  const at = lines.indexOf(LIVE_TIMES_ROW)
  expect([lines[at + 1], lines.filter(t => LANE.test(t)).length, lines.filter(t => PROMPT_ROW.test(t)).length]).toEqual([WORD, 0, 101])
  // The word's row is one span, dim, as the guide says.
  expect(layout(tree, 400).lines.filter(l => l.text === WORD).map(l => [l.spans, l.dim])).toEqual([[1, true]])
})

test('a run of 101 prompts below the lane threshold draws neither a lane nor the word', async ($, on) => {
  await load($, on, { reader: ok(readerOf(range(101))), agents: [] })
  const lines = texts(await drawPane($, 12, 'dock'), 12)
  // A lane of p101 needs 4 + 1 + 10 cells. The withheld word, cut to 12 cells, would start `lanes`.
  expect([lines.filter(t => t.startsWith('PB-0149 RUN')).length, lines.filter(t => LANE.test(t)).length, lines.filter(t => t.startsWith('lanes')).length]).toEqual([1, 0, 0])
})

test('laneLines draws nothing in any mode for a run with no lane output: below the threshold, now_s null, now_s before the start, no prompts', () => {
  const runOf = (doc: unknown) => {
    const p = P(doc)
    if (!p.ok) throw new Error('fixture invalid')
    return { run: p.view.runs[0]!, now: p.view.now_s }
  }
  const modes: draw.LaneMode[] = ['draw', 'withhold', 'phase1']
  for (const [label, doc, n] of [
    ['101 prompts at 12 columns', readerOf(range(101)), 12],
    ['now_s null', readerAt(null), 60],
    ['now_s before the start', readerAt(RUN.started_s - 60), 60],
    ['no prompts', READER_NO_PROMPTS, 60],
  ] as const) {
    const { run, now } = runOf(doc)
    for (const mode of modes) expect([label, mode, draw.laneLines(run, now, n, mode)]).toEqual([label, mode, []])
  }
  // Positive controls: the same runs draw their lane output where they have one.
  const text = (lines: draw.Line[]) => lines.map(l => l.map(s => s.text).join(''))
  const many = runOf(readerOf(range(101)))
  const live = runOf(READER_OK)
  expect([text(draw.laneLines(many.run, many.now, 400, 'draw')), text(draw.laneLines(live.run, live.now, 60, 'withhold')), draw.laneLines(live.run, live.now, 60, 'draw').length]).toEqual([[WORD], [WORD], 4])
})

test('the budget is pure: the edge of each limit, the order of the runs, gains of zero, and no lane output when the words do not fit', () => {
  const S = (units: number, nodes: number) => ({ units, nodes })
  const admit = draw.lanesAdmitted
  // Text: the words and one run's gain of 12486 reach 90000 exactly, then 90001.
  expect([admit(S(77514, 1000), [S(12486, 897)]), admit(S(77515, 1000), [S(12486, 897)])]).toEqual([1, 0])
  // Nodes: 17103 and a gain of 897 reach 18000 exactly, then 18001, with the text far below.
  expect([admit(S(40000, 17103), [S(1486, 897)]), admit(S(40000, 17104), [S(1486, 897)])]).toEqual([1, 0])
  // Each limit on its own: text under and nodes over, then text over and nodes under.
  expect([admit(S(1000, 17999), [S(10, 2)]), admit(S(89999, 10), [S(2, 1)])]).toEqual([0, 0])
  // The first runs keep their lanes: three gains of 5000 on 80000 admit two runs.
  expect(admit(S(80000, 100), [S(5000, 10), S(5000, 10), S(5000, 10)])).toBe(2)
  // A small fourth run waits behind a third that does not fit.
  expect(admit(S(80000, 100), [S(5000, 10), S(6000, 10), S(361, 3), S(5000, 10)])).toBe(1)
  // A run with no lane output gains nothing and stands in no one's way.
  expect([admit(S(80000, 100), [S(0, 0), S(5000, 10)]), admit(S(90000, 18000), [S(0, 0)])]).toEqual([2, 1])
  // The words at the budget admit no gain; past it, no lane output at all.
  expect([admit(S(90000, 18000), [S(1, 0)]), admit(S(90001, 10), []), admit(S(10, 18001), [])]).toEqual([0, -1, -1])
  // With no gains every run keeps what it has: a pane with no lanes to admit.
  expect(admit(S(10, 10), [])).toBe(0)
})

test('blockSize counts a line as its Text, a Text per span and each string, and a box as one node and its children', () => {
  const line = (texts: string[]): draw.Block => ({ kind: 'line', line: texts.map(text => ({ text })) })
  const box = (children: draw.Block[]): draw.Block => ({ kind: 'box', direction: 'column', width: 1, border: null, gap: 0, children })
  expect(draw.blockSize(line(['ab', 'c']))).toEqual({ units: 3, nodes: 5 })
  expect(draw.blockSize(line([]))).toEqual({ units: 0, nodes: 1 })
  expect(draw.blockSize(box([line(['\u{25AC}\u{2713}']), box([line(['\u{1F600}'])])]))).toEqual({ units: 4, nodes: 8 })
})

test('blockSize counts an empty span\'s string, and a merged lane by its spans: one at cell 0, four in the middle, three at the end, the error glyph apart', () => {
  // A line of no span is its Text; a line of one empty span is its Text, the span's Text and the string.
  expect([draw.blockSize({ kind: 'line', line: [] }), draw.blockSize({ kind: 'line', line: [{ text: '' }] })]).toEqual([{ units: 0, nodes: 1 }, { units: 0, nodes: 3 }])
  // merged keeps a line's single empty span, and drops an empty span from a line of more than one.
  expect([draw.merged([{ text: '' }]), draw.merged([{ text: 'a' }, { text: '', dim: true }, { text: 'b' }])]).toEqual([[{ text: '' }], [{ text: 'ab' }]])
  const runOf = (doc: unknown) => {
    const p = P(doc)
    if (!p.ok) throw new Error('fixture invalid')
    return { run: p.view.runs[0] ?? p.view.last_completed!, now: p.view.now_s }
  }
  const lanesAt30 = (doc: unknown) => {
    const { run, now } = runOf(doc)
    return draw.laneLines(run, now, 30).map(l => draw.merged(l))
  }
  const [p1, p2, , p4] = lanesAt30(IDLE_LATEST)
  const [, b2] = lanesAt30(READER_OK)
  // The last run at 27 cells: p1 at cell 0 merges its label, fill and end glyph, then its track.
  expect(p1).toEqual([{ text: 'p1 ' + FILL.repeat(5) + END.done }, { text: TRACK.repeat(21), dim: true }])
  // p2 in the middle: label, track, fill with its glyph, track.
  expect(p2).toEqual([{ text: 'p2 ' }, { text: TRACK.repeat(5), dim: true }, { text: FILL.repeat(15) + END.done }, { text: TRACK.repeat(6), dim: true }])
  // p4 ends at cell 27: its empty trailing track is gone.
  expect(p4).toEqual([{ text: 'p4 ' }, { text: TRACK.repeat(20), dim: true }, { text: FILL.repeat(6) + END.done }])
  // The live run's blocked p2 ends at cell 27 in the error key, apart from its fill.
  expect(b2).toEqual([{ text: 'p2 ' }, { text: TRACK.repeat(7), dim: true }, { text: FILL.repeat(19) }, { text: END.blocked, color: 'error' }])
  const sizes = [p1!, p2!, p4!, b2!].map(l => draw.blockSize({ kind: 'line', line: l }))
  expect(sizes).toEqual([{ units: 30, nodes: 1 + 2 * 2 }, { units: 30, nodes: 1 + 2 * 4 }, { units: 30, nodes: 1 + 2 * 3 }, { units: 30, nodes: 1 + 2 * 4 }])
})

for (const [name, doc] of [['the live run', READER_OK], ['the last run', IDLE_LATEST], ['the council\'s shape', SEAT_SHAPE], ['a council grid', nodeHeavyDoc(30)], ['a completed listed run', targetCompleted(NOW_S)]] as const) {
  test(`blockSize counts what the drawn tree holds: ${name} at 15, 30, 120 and 400 columns`, async ($, on) => {
    await load($, on, { reader: ok(doc), agents: [AGENT] })
    for (const w of [15, 30, 120, 400]) {
      const tree = await drawPane($, w, 'dock')
      expect([w, draw.blockSize(draw.pane(P(doc), agents([AGENT]), w, 'docked', HARNESS))]).toEqual([w, drawnSize(tree)])
      // The last run's summary has an empty line, drawn as a line whose only string is empty.
      if (doc === IDLE_LATEST) expect([w, lineStrings(tree).filter(s => s.length === 1 && s[0] === '').length]).toEqual([w, 1])
    }
  })
}

test('the title gives way to its last cell: a room of 2 cells, of 1, and none, with no dangling gap; the times rows stay dim', async ($, on) => {
  const doc = clone(READER_OK)
  const r = doc.runs[0]
  r.started_s = 0
  r.current_prompt = 10000
  r.prompts = [{ n: 10000, state: 'running', module_tag: 'implementation-12', title: H, started_s: 0, completed_s: null }]
  doc.now_s = 4102444800
  await load($, on, { reader: ok(doc), agents: [] })
  const want: Record<number, string> = {
    34: `${MARK}p10000  running  i${ELL}  1139568h00m`,
    33: `${MARK}p10000  running  ${ELL}  1139568h00m`,
    32: `${MARK}p10000  running  1139568h00m`,
  }
  for (const w of [34, 33, 32]) {
    const tree = await drawPane($, w, 'dock')
    fits(tree, w, `room ${w}`)
    expect([w, texts(tree, w).filter(t => PROMPT_ROW.test(t))]).toEqual([w, [want[w]]])
    const times = layout(tree, w).lines.filter(l => TIMES.test(l.text))
    expect([w, times.map(l => [l.text, l.dim])]).toEqual([w, [['started 1970-01-01 00:00 UTC', true], ['elapsed 1139568h00m', true]]])
  }
})

// --- the clock ------------------------------------------------------------------------------------

test('the wider clock guard throws on every clock shape, lets a Date from a number through, and restores every global', () => {
  const g = globalThis as any
  const before = [g.Date, g.performance, g.Temporal, g.Intl, Object.prototype.hasOwnProperty.call(g, 'process')]
  const seeds: [string, () => unknown][] = [
    ['Date()', () => (Date as any)()], ['new Date()', () => new Date()], ['new Date', () => new (Date as any)], ['Date.now()', () => Date.now()],
    ['performance.now()', () => performance.now()], ['Temporal.Now.instant()', () => (globalThis as any).Temporal.Now.instant()],
    ['process.hrtime()', () => (globalThis as any).process.hrtime()], ['process.hrtime.bigint()', () => (globalThis as any).process.hrtime.bigint()],
    ['process.uptime()', () => (globalThis as any).process.uptime()],
    ['Intl format()', () => new Intl.DateTimeFormat('en').format()], ['Intl formatToParts()', () => (Intl.DateTimeFormat as any)('en').formatToParts()],
  ]
  for (const [name, seed] of seeds) expect([name, (() => { try { withoutAnyClock(() => { seed() }); return 'ran' } catch { return 'threw' } })()]).toEqual([name, 'threw'])
  expect(() => withoutAnyClock(() => { new Date(1000); new Intl.DateTimeFormat('en', { timeZone: 'UTC' }).format(new Date(0)) })).not.toThrow()
  expect([g.Date, g.performance, g.Temporal, g.Intl, Object.prototype.hasOwnProperty.call(g, 'process')]).toEqual(before)
})

test('the band and both pane layouts draw every axis fixture under the wider clock guard', () => {
  expect(() => withoutAnyClock(() => {
    for (const doc of [SEAT_SHAPE, textEdge(56), textEdge(57), nodeHeavyDoc(1582), seatDoc([100, 100, 100, 3, 100], 150), READER_OK, IDLE_LATEST, targetCompleted(null), targetAbandoned(NOW_S), READER_ZERO_AT_END]) {
      for (const w of [15, 30, 120, 400]) {
        draw.pane(P(doc), agents([AGENT]), w, 'docked', HARNESS)
        draw.pane(P(doc), agents([AGENT]), w, 'mini', HARNESS)
        draw.band(P(doc), agents([AGENT]), w, HARNESS)
      }
    }
  })).not.toThrow()
})

// Every shape of a clock read the suite can see in source: any call of a now(), any Date that is not
// new Date(<an argument>), new Date with no argument, and Temporal, process, performance and Intl
// in any form.
const CLOCK_SHAPES = new RegExp([
  '\\.\\s*now\\s*\\(', '(?<!\\bnew\\s+)\\bDate\\b', '\\bnew\\s+Date\\b(?!\\s*\\(\\s*[^)\\s])',
  '\\bTemporal\\b', '\\bprocess\\b', '\\bperformance\\b', '\\bIntl\\b', '\\.\\s*format(ToParts)?\\s*\\(\\s*\\)',
].join('|'))
test('no export of draw.ts or view.ts names a clock read in any shape the wider scan knows', () => {
  for (const [s, hit] of [
    ['Date.now()', true], ['performance.now()', true], ['new Date()', true], ['new Date;', true], ['x = Date()', true], ['Date ( )', true],
    ['Temporal.Now.instant()', true], ['process.hrtime()', true], ['process.uptime()', true], ['new Intl.DateTimeFormat().format()', true],
    ['f.formatToParts( )', true], ['const D = Date', true], ['D.now()', true],
    ['new Date(s * 1000)', false], ['d.getUTCDate()', false], ['utc(s)', false], ['f.format(d)', false],
  ] as [string, boolean][]) expect([s, CLOCK_SHAPES.test(s)]).toEqual([s, hit])
  const sources = [...Object.values(draw), ...Object.values(view)].filter(v => typeof v === 'function').map(f => String(f))
  expect(sources.length).toBeGreaterThan(40)
  expect(sources.filter(s => CLOCK_SHAPES.test(s)).map(s => s.slice(0, 60))).toEqual([])
  expect(sources.some(s => /new Date\(s \* (1e3|1000)\)/.test(s))).toBe(true)
})
