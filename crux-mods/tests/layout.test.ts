// The band and the pane at every width the dashboard's width rule names, with no width reported,
// and below 30 columns; in each layout that applies; with each section empty; and with each status.
// Every drawn tree is read by fixtures/measure.ts, which does not share the hooks' width code.
import { test, expect } from 'claude-code/testing'
import * as draw from '../hooks/lib/draw.ts'
import { THEME_KEYS } from '../hooks/lib/draw.ts'
import type { Block } from '../hooks/lib/draw.ts'
import * as width from '../hooks/lib/width.ts'
import { LAUNCH_CODES } from '../hooks/lib/launch.ts'
import { READER_ERROR_CODES, VIEW_CODES, agents, answer, parseReader } from '../hooks/lib/view.ts'
import type { Parsed } from '../hooks/lib/view.ts'
import {
  HOSTILE_TITLE, IDLE_LATEST, IDLE_LATEST_DATED, IDLE_NO_SUMMARY, IDLE_RUN_IN_PROGRESS, IDLE_UNDETERMINED, IDLE_WIDE, READER_AT_CAP,
  READER_COUNCILS, READER_EMPTY, READER_ESCALATED, READER_NO_COUNCILS, READER_NO_GATES, READER_NO_PROMPTS, READER_OK, READER_PATCH, READER_SIX,
  READER_STALLED, READER_STALLED_ESCALATED, READER_TEN, READER_TWO, READER_WIDE, WIDE_TEXT, clone, idleDoc, readerAt, readerError,
} from './fixtures/reader-output.ts'
import { STATUS_CODES, STATUS_MACHINES } from './fixtures/statuses.ts'
import { BAND, PANE, install } from './fixtures/world.ts'
import type { Opts } from './fixtures/world.ts'
import { layout, overflows, rowsOf, twoColumns, widest } from './fixtures/measure.ts'
import type { Layout } from './fixtures/measure.ts'
import { CLOCK_READ, withoutClock } from './fixtures/no-clock.ts'

const ok = (doc: unknown) => ({ exitCode: 0, stdout: JSON.stringify(doc) })
// The two notes, written here independently of view.ts.
const STALL_NOTE = "This session's agent list cannot see subagents in another Claude Code session, work in Codex or OpenCode, main-thread work or a background command; each can run for a long time without changing the run file."
const ESCALATION_NOTE = 'Read from council records in the working tree. Whether each record counts, and whether the gate stops, is decided by the gate check, which reads committed history.'
const P = (doc: unknown): Parsed => parseReader(JSON.stringify(doc))
const RUNNING = { id: 'a1', description: 'Plan the thing', type: 'developer', status: 'running' }
const DONE = { id: 'a2', description: 'Done thing', type: 'reviewer', status: 'completed' }

// The widths the width rule names, no width reported, and widths below 30 columns.
const WIDTHS: (number | undefined)[] = [30, 40, 60, 86, 110, 120, undefined]
const SMALL = [1, 2, 5, 10, 29]
const drawingWidth = (w: number | undefined) => w ?? 40

async function load($: any, on: any, o: Opts = {}) {
  install(on, { reader: ok(READER_OK), ...o })
  await $.command.run({ command: 'crux-dashboard' } as any)
}
const withWidth = (base: Record<string, unknown>, w: number | undefined) => {
  const { bodyColumns: _, ...rest } = base
  return w === undefined ? rest : { ...rest, bodyColumns: w }
}
async function drawPane($: any, w: number | undefined, placement: 'inline' | 'dock', surface = 'terminal') {
  const ui = await $.ui.mount({ plugin: 'crux-mods', surface, component: 'Pane', requestId: 'crux-dashboard', props: { ...withWidth(PANE, w), placement } })
  const tree = await ui.drawn()
  await ui.unmount()
  return tree
}
async function drawBand($: any, w: number | undefined, surface = 'terminal') {
  const ui = await $.ui.mount({ plugin: 'crux-mods', surface, component: 'AbovePrompt', props: withWidth(BAND, w) })
  const tree = await ui.drawn()
  await ui.unmount()
  return tree
}

// A block from the pure builders as the element tree the hooks module draws from it.
function asTree(b: Block | null): unknown {
  if (b === null) return { type: 'Box', props: {}, children: [] }
  if (b.kind === 'line') return { type: 'Text', props: { wrap: 'truncate' }, children: b.line.map(s => ({ type: 'Text', props: draw.styleOf(s), children: [s.text] })) }
  const props: Record<string, unknown> = { flexDirection: b.direction, width: b.width }
  if (b.border !== null) Object.assign(props, { borderStyle: 'round', borderColor: b.border, paddingX: 1 })
  if (b.direction === 'row') props.columnGap = b.gap
  return { type: 'Box', props, children: b.children.map(asTree) }
}
const texts = (tree: unknown) => rowsOf(tree).map(r => r.text)

// What every drawing must hold at width w.
function check(tree: unknown, w: number, kind: 'band' | 'inline' | 'dock', label: string): Layout {
  const l = layout(tree, w)
  expect([label, overflows(l)]).toEqual([label, []])
  expect([label, widest(l) <= w]).toEqual([label, true])
  expect([label, [...new Set(l.types)].filter(t => t !== 'Box' && t !== 'Text')]).toEqual([label, []])
  expect([label, l.colors.filter(c => !(THEME_KEYS as readonly string[]).includes(c))]).toEqual([label, []])
  const bordered = l.boxes.some(b => b.border)
  if (w < 40 || kind === 'band') expect([label, 'border', bordered]).toEqual([label, 'border', false])
  if (kind === 'inline') expect([label, 'rows', l.rows <= 8]).toEqual([label, 'rows', true])
  if (kind === 'band') expect([label, 'lines', l.lines.length <= 1]).toEqual([label, 'lines', true])
  if (kind !== 'dock' || w < 110) expect([label, 'columns', twoColumns(l)]).toEqual([label, 'columns', false])
  return l
}

// --- every fixture, every width, every layout ------------------------------------------------

const FIXTURES: [string, Opts][] = [
  ['a live run with agents', { reader: ok(READER_OK), agents: [RUNNING, DONE] }],
  ['a stalled run', { reader: ok(READER_STALLED) }],
  ['a stalled and escalated run', { reader: ok(READER_STALLED_ESCALATED) }],
  ['two runs', { reader: ok(READER_TWO) }],
  ['six runs', { reader: ok(READER_SIX) }],
  ['a patch book with no module tags', { reader: ok(READER_PATCH) }],
  ['councils at every edge of the grid', { reader: ok(READER_COUNCILS) }],
  ['ten prompts in three modules', { reader: ok(READER_TEN) }],
  ['wide text', { reader: ok(READER_WIDE), agents: [{ ...RUNNING, description: WIDE_TEXT.repeat(3) }] }],
  ['a run read with no clock', { reader: ok(readerAt(null)) }],
  ['the last run', { reader: ok(IDLE_LATEST) }],
  ['the last dated run', { reader: ok(IDLE_LATEST_DATED) }],
  ['an undetermined last run', { reader: ok(IDLE_UNDETERMINED) }],
  ['a run in progress the reader refused', { reader: ok(IDLE_RUN_IN_PROGRESS) }],
  ['target mode with no listed run', { reader: ok(idleDoc('not-requested')) }],
  ['a last run with a wide summary', { reader: ok(IDLE_WIDE) }],
  ['a last run with the summary at its caps', { reader: ok(READER_AT_CAP) }],
  ['no councils', { reader: ok(READER_NO_COUNCILS) }],
  ['no gates', { reader: ok(READER_NO_GATES) }],
  ['no prompts', { reader: ok(READER_NO_PROMPTS) }],
  ['no summary', { reader: ok(IDLE_NO_SUMMARY) }],
  ['no agents', { reader: ok(READER_OK), agents: [] }],
  ['an agent list that cannot be read', { reader: ok(READER_OK), agents: 'throw' }],
]

for (const [name, o] of FIXTURES) {
  test(`${name}: the band and both pane layouts fit every width and draw only Box and Text in theme keys`, async ($, on) => {
    await load($, on, o)
    for (const w of [...WIDTHS, ...SMALL]) {
      const n = drawingWidth(w)
      check(await drawBand($, w), n, 'band', `${name} band ${w}`)
      check(await drawPane($, w, 'inline'), n, 'inline', `${name} inline ${w}`)
      check(await drawPane($, w, 'dock'), n, 'dock', `${name} dock ${w}`)
    }
  })
}

test('the pane draws on every surface and the band on the two that raise it, each within its width', async ($, on) => {
  await load($, on, { agents: [RUNNING] })
  for (const surface of ['terminal', 'desktop', 'vscode', 'mobile'] as const) {
    for (const placement of ['inline', 'dock'] as const) {
      const tree = await drawPane($, 60, placement, surface)
      check(tree, 60, placement, `${surface} ${placement}`)
      expect(texts(tree).join('\n')).toContain('PB-0149 RUN-001')
    }
  }
  for (const surface of ['terminal', 'desktop'] as const) expect(texts(await drawBand($, 60, surface)).join('')).toContain('PB-0149 RUN-001')
})

// --- the docked pane --------------------------------------------------------------------------

test('the docked pane draws bordered panels from 40 columns and drops them below', async ($, on) => {
  await load($, on, { agents: [RUNNING] })
  for (const w of [40, 60, 86, 109, 110, 120, undefined]) {
    const l = layout(await drawPane($, w, 'dock'), drawingWidth(w))
    expect([w, l.boxes.filter(b => b.border).length]).toEqual([w, 4])
  }
  for (const w of [39, 30, 10]) expect([w, layout(await drawPane($, w, 'dock'), w).boxes.some(b => b.border)]).toEqual([w, false])
})

test('the docked pane draws two columns from 110 columns: the run on the left, its councils, gates and agents on the right', async ($, on) => {
  await load($, on, { agents: [RUNNING] })
  for (const w of [30, 86, 109]) expect([w, twoColumns(layout(await drawPane($, w, 'dock'), w))]).toEqual([w, false])
  for (const w of [110, 120]) {
    const tree: any = await drawPane($, w, 'dock')
    expect([w, twoColumns(layout(tree, w))]).toEqual([w, true])
    const row = tree.children.flat(Infinity).find((c: any) => c?.props?.flexDirection === 'row')
    const [left, right] = row.children.flat(Infinity).filter((c: any) => c?.type === 'Box')
    expect(texts(left).join('\n')).toContain('PB-0149 RUN-001  in_progress  prompt 3 of 4  25%')
    expect(texts(left).join('\n')).toContain('reader 3.27.4  refused run files 0')
    expect(texts(right).filter(t => ['Councils', 'Gates', 'Agents'].includes(t))).toEqual(['Councils', 'Gates', 'Agents'])
  }
})

test('the docked pane draws the legend, the run panel with its strip and bar, the council grid, the gate strip and the agent rows', async ($, on) => {
  await load($, on, { agents: [RUNNING] })
  const rows = texts(await drawPane($, 100, 'dock'))
  expect(rows).toEqual([
    '\u{2713} done  \u{2717} blocked  \u{25B8} running  \u{25CC} pending  adr  untagged  \u{2298} skipped',
    'PB-0149 RUN-001  in_progress  prompt 3 of 4  25%',
    'adr \u{2713}\u{2717}  untagged \u{25B8}\u{25CC}',
    '\u{25AE}'.repeat(5) + '\u{25AF}'.repeat(15),
    'started 2026-10-11 00:53 UTC  elapsed 2h10m',
    'p1 ' + '\u{25AC}'.repeat(23) + '\u{2713}' + '.'.repeat(69),
    'p2 ' + '.'.repeat(24) + '\u{25AC}'.repeat(68) + '\u{2717}',
    'p3 ' + '.'.repeat(84) + '\u{25AC}'.repeat(8) + '\u{25B8}',
    'p4 no start',
    'done 1  skipped 0  blocked 1  running 1  pending 1',
    `p1  done  adr-1  ${HOSTILE_TITLE}  33m`,
    'p2  blocked  adr-1  Council on the decision  1h35m',
    '\u{25B8} p3  running  Build the dashboard  12m',
    'p4  pending  Review',
    'refused council files 2',
    'Councils',
    '           p2r1 p2r2',
    'openai_top \u{2717}    \u{2713}   ',
    'google_top \u{2713}    .   ',
    'p2 r2  adr  AUTO_EXECUTE  converged',
    'Gates',
    '\u{2717} p2 council  \u{25CC} p4 review',
    'Agents',
    '\u{25B8}  developer  Plan the thing',
    'reader 3.27.4  refused run files 0',
  ])
})

for (const [label, o, want] of [
  ['no councils', { reader: ok(READER_NO_COUNCILS), agents: [RUNNING] }, ['Gates', 'Agents']],
  ['no gates', { reader: ok(READER_NO_GATES), agents: [RUNNING] }, ['Councils', 'Agents']],
  ['no agents', { reader: ok(READER_OK), agents: [] }, ['Councils', 'Gates']],
  ['no summary', { reader: ok(IDLE_NO_SUMMARY) }, []],
  ['a summary', { reader: ok(IDLE_LATEST) }, ['Summary']],
  ['agents unavailable', { reader: ok(READER_OK), agents: 'throw' }, ['Councils', 'Gates', 'Agents']],
] as [string, Opts, string[]][]) {
  test(`the docked pane with ${label} draws exactly the sections that have something to show`, async ($, on) => {
    await load($, on, o)
    const rows = texts(await drawPane($, 100, 'dock'))
    expect(rows.filter(t => ['Councils', 'Gates', 'Agents', 'Summary'].includes(t))).toEqual(want)
    // The none row of a readable but empty agent list is gone; agents unavailable stays.
    expect(rows.includes('none')).toBe(false)
    expect(rows.includes('agents unavailable')).toBe(label === 'agents unavailable')
  })
}

test('a run with no prompts draws no strip, no bar and no prompt row, and still draws its counts', async ($, on) => {
  await load($, on, { reader: ok(READER_NO_PROMPTS) })
  const rows = texts(await drawPane($, 100, 'dock'))
  expect(rows).toContain('PB-0149 RUN-001  in_progress  prompt none of 0  0%')
  expect(rows).toContain('done 0  skipped 0  blocked 0  running 0  pending 0')
  expect(rows.some(t => t.includes('\u{25AE}') || t.includes('\u{25AF}') || /^p\d/.test(t))).toBe(false)
})

test('six runs draw five run panels and count the sixth', async ($, on) => {
  await load($, on, { reader: ok(READER_SIX) })
  const rows = texts(await drawPane($, 100, 'dock'))
  expect(rows.filter(t => /^PB-0149 RUN-00\d  in_progress/.test(t)).length).toBe(5)
  expect(rows).toContain('+1 more run')
  // With several runs each councils and gates panel names its run.
  expect(rows).toContain('Councils PB-0149 RUN-001')
  expect(rows).toContain('Gates PB-0149 RUN-005')
})

// --- every row PB-0152 added stays in the full layout ------------------------------------------

test('the full layout keeps every live-run row: times, counts, the stall and its note, each escalation and its note, every prompt, refused files and the reader', async ($, on) => {
  await load($, on, { reader: ok(READER_STALLED_ESCALATED), agents: [] })
  const rows = rowsOf(await drawPane($, 400, 'dock'))
  const t = rows.map(r => r.text)
  for (const row of [
    'PB-0149 RUN-001  in_progress  prompt 3 of 4  25%', 'started 2026-10-11 00:53 UTC  elapsed 2h30m', 'done 1  skipped 0  blocked 1  running 1  pending 1',
    'run file unchanged 25m, no subagent running in this session',
    'escalation p2: records r1-r4 show quorum met, none converged; a counted round past 3 needs an owner exception',
    'escalation p3: records r1-r3 show quorum met, none converged; a counted round past 3 needs an owner exception',
    `p1  done  adr-1  ${HOSTILE_TITLE}  33m`, 'p2  blocked  adr-1  Council on the decision  1h55m', '\u{25B8} p3  running  Build the dashboard  32m', 'p4  pending  Review',
    'refused council files 2', 'reader 3.27.4  refused run files 0',
  ]) expect([row, t.includes(row)]).toEqual([row, true])
  const noteAt = t.indexOf('run file unchanged 25m, no subagent running in this session') + 1
  expect(t.slice(noteAt, noteAt + 2).join(' ')).toBe(STALL_NOTE)
  expect(rows[noteAt]!.dim).toBe(true)
  expect(t[t.indexOf('escalation p3: records r1-r3 show quorum met, none converged; a counted round past 3 needs an owner exception') + 1]).toBe(ESCALATION_NOTE)
  expect(rows.find(r => r.text.startsWith('run file unchanged'))!.color).toBe('error')
  expect(rows.filter(r => r.text.startsWith('escalation p')).map(r => r.color)).toEqual(['error', 'error'])
})

test('the full layout keeps every last-run row: the title, its times, counts, prompts, the summary and the reader', async ($, on) => {
  await load($, on, { reader: ok(idleDoc('latest', { summary: ['Shipped the run dashboard.', '', 'Second paragraph after an empty line.'], truncated: true })) })
  const t = texts(await drawPane($, 100, 'dock'))
  const from = t.indexOf('Last run')
  expect(t.slice(from)).toEqual([
    'Last run', 'PB-0150 RUN-002  completed  prompt none of 4  100%', 'untagged \u{2713}\u{2713}\u{2298}\u{2713}', '\u{25AE}'.repeat(20),
    'started 2026-10-10 23:58 UTC  completed 2026-10-11 02:03 UTC  took 2h05m',
    'p1 ' + '\u{25AC}'.repeat(18) + '\u{2713}' + '.'.repeat(74), 'p2 ' + '.'.repeat(18) + '\u{25AC}'.repeat(52) + '\u{2713}' + '.'.repeat(22), 'p3 no start', 'p4 ' + '.'.repeat(70) + '\u{25AC}'.repeat(22) + '\u{2713}',
    'done 3  skipped 1  blocked 0  running 0  pending 0',
    'p1  done  Plan the last run  25m', 'p2  done  Build the last run  1h10m', 'p3  skipped  Skipped prompt', 'p4  done  Close the last run  30m',
    'refused council files 0', 'Summary', 'Shipped the run dashboard.', '', 'Second paragraph after an empty line.', 'summary truncated',
    'reader 3.27.4  refused run files 0',
  ])
})

test('the full layout keeps the undetermined and run-in-progress rows, wrapped at the width', async ($, on) => {
  await load($, on, { reader: ok(IDLE_UNDETERMINED) })
  const t = texts(await drawPane($, 60, 'dock'))
  expect(t.slice(0, 3).join(' ')).toBe('Last run not shown: 3 run entries unresolved, 2 completed runs undated; a run in progress or a newer completed run cannot be ruled out.')
  expect(t[t.length - 1]).toBe('reader 3.27.4  refused run files 0')
})

// --- the mini layout --------------------------------------------------------------------------

test('the inline pane draws at most 8 rows in the order run, legend, gates, councils, agents, and names what it cut', async ($, on) => {
  await load($, on, { agents: [RUNNING, DONE] })
  const tree = await drawPane($, 60, 'inline')
  const l = layout(tree, 60)
  expect(l.rows).toBe(8)
  expect(texts(tree)).toEqual([
    'PB-0149 RUN-001  p3/4  25%',
    'adr \u{2713}\u{2717}  untagged \u{25B8}\u{25CC}',
    '\u{25B8} p3  running  Build the dashboard  12m',
    '\u{2713} done  \u{2717} blocked  \u{25B8} running  \u{25CC} pending  adr  untagged',
    '\u{2717} p2 council  \u{25CC} p4 review',
    '+2 more: councils, agents',
  ])
  // The run section is bordered from 40 columns: 3 rows and the border's 2.
  expect(l.boxes.filter(b => b.border).length).toBe(1)
})

test('the inline pane keeps the stall and the escalation ahead of the strip and the prompt', async ($, on) => {
  await load($, on, { reader: ok(READER_STALLED_ESCALATED), agents: [] })
  const at60 = await drawPane($, 60, 'inline')
  expect(layout(at60, 60).rows).toBe(8)
  expect(texts(at60)).toEqual([
    'PB-0149 RUN-001  p3/4  25%', 'stalled 25m', 'escalation p3 r3 +1', 'adr \u{2713}\u{2717}  untagged \u{25B8}\u{25CC}',
    '\u{25B8} p3  running  Build the dashboard  32m', '+3 more: legend, gates, councils',
  ])
  const at30 = await drawPane($, 30, 'inline')
  expect(layout(at30, 30).rows).toBe(8)
  const t = texts(at30)
  expect(t.slice(0, 3)).toEqual(['PB-0149 RUN-001  p3/4  25%', 'stalled 25m', 'escalation p3 r3 +1'])
})

test('an inline pane that fits draws every section and no +N more row', async ($, on) => {
  await load($, on, { agents: [] })
  const tree = await drawPane($, 30, 'inline')
  const t = texts(tree)
  expect(t.some(x => x.startsWith('+'))).toBe(false)
  expect(t[t.length - 1]!.startsWith('council p2 r2 ')).toBe(true)
  expect(layout(tree, 30).rows).toBeLessThanOrEqual(8)
})

test('the inline pane for the last run names its summary, which it does not draw', async ($, on) => {
  await load($, on, { reader: ok(IDLE_LATEST) })
  const t = texts(await drawPane($, 60, 'inline'))
  expect(t[0]).toBe('Last run: PB-0150 RUN-002  3/4 done')
  expect(t[t.length - 1]).toBe('+1 more: summary')
})

// --- the band ---------------------------------------------------------------------------------

const segments = (doc: unknown, list: unknown, w: number) => draw.bandSegments(P(doc), agents(list), w)?.map(s => s.name)

test('the band keeps the stall and the escalation ahead of the ids and the strip at 30 and 40 columns', async ($, on) => {
  await load($, on, { reader: ok(READER_STALLED_ESCALATED), agents: [] })
  expect(texts(await drawBand($, 30))).toEqual(['escalation p3 r3  stalled 25m'])
  expect(texts(await drawBand($, 40))).toEqual(['p3/4  25%  escalation p3 r3  stalled 25m'])
  expect(texts(await drawBand($, 60))).toEqual(['PB-0149 RUN-001  p3/4  25%  escalation p3 r3  stalled 25m'])
})

test('the band at 30 columns differs from the band at 120, and each fits', async ($, on) => {
  await load($, on, { agents: [RUNNING] })
  const narrow = texts(await drawBand($, 30))
  const wide = texts(await drawBand($, 120))
  expect(narrow).toEqual(['PB-0149 RUN-001  p3/4  25%'])
  expect(wide).toEqual(['PB-0149 RUN-001  \u{2713}\u{2717}|\u{25B8}\u{25CC}  untagged  p3/4  25%  12m  Build the dashboard  council p2 r2 AUTO_EXECUTE  gate p2 blocked'])
})

test('the band draws the full stall and escalation sentences when they fit', () => {
  const t = draw.bandSegments(P(READER_STALLED_ESCALATED), agents([]), 400)!
  expect(t.map(s => s.line.map(x => x.text).join(''))).toContain('run file unchanged 25m, no subagent running in this session')
  expect(t.map(s => s.line.map(x => x.text).join(''))).toContain('escalation p3: records r1-r3 show quorum met, none converged; a counted round past 3 needs an owner exception')
})

// The segments in the order the band keeps them, most important first.
const KEEP_ORDER = ['stall', 'escalation', 'position', 'percent', 'ids', 'strip', 'kind', 'elapsed', 'title', 'council', 'gate', 'agents', 'runs']

test('as the band narrows it drops segments from the least important up, never skipping one', () => {
  const docs: [unknown, unknown][] = [[READER_OK, [RUNNING]], [READER_TWO, [RUNNING]], [READER_STALLED_ESCALATED, []], [READER_TEN, []]]
  for (const [doc, list] of docs) {
    const all = segments(doc, list, 400)!
    for (let w = 1; w <= 200; w++) {
      const kept = segments(doc, list, w)!
      const ranks = all.map(n => KEEP_ORDER.indexOf(n)).sort((a, b) => a - b)
      const want = ranks.slice(0, kept.length).map(i => KEEP_ORDER[i])
      expect([w, [...kept].sort()]).toEqual([w, [...want].sort()])
    }
  }
})

test('the band draws the strip with the current module kind as a word; no strip cell takes a kind colour', () => {
  const segs = draw.bandSegments(P(READER_OK), agents([]), 400)!
  const strip = segs.find(s => s.name === 'strip')!
  const kind = segs.find(s => s.name === 'kind')!
  expect(strip.line.map(s => s.text).join('')).toBe('\u{2713}\u{2717}|\u{25B8}\u{25CC}')
  expect(strip.line.map(s => s.color).filter(c => c !== undefined)).toEqual(['error'])
  expect(kind.line).toEqual([{ text: 'untagged', color: 'inactive' }])
  // A module that is not current draws no kind word in the band.
  expect(segs.some(s => s.line.some(x => x.text === 'adr'))).toBe(false)
})

test('a strip too wide for the band keeps the cells nearest the current prompt and counts the rest', () => {
  const segs = draw.bandSegments(P(READER_TEN), agents([]), 34)!
  expect(segs.map(s => s.name)).toEqual(['ids', 'strip', 'position', 'percent'])
  // The strip shrinks to the three cells nearest the fifth prompt and counts the other seven.
  expect(segs[1]!.line.map(s => s.text).join('')).toBe('\u{2713}\u{25B8}\u{25CC}+7')
})

test('below the width of its smallest segment the band still draws its most important segment, cut with an ellipsis', () => {
  const line = (doc: unknown, list: unknown, w: number) => texts(asTree(draw.band(P(doc), agents(list), w)))
  expect(line(READER_STALLED_ESCALATED, [], 5)).toEqual(['stal\u{2026}'])
  expect(line(READER_OK, [], 3)).toEqual(['p3\u{2026}'])
  expect(line(READER_OK, [], 1)).toEqual(['\u{2026}'])
})

test('a drawn line holds one Text per run of spans in one style, so a grid row is three Texts, not seven', async ($, on) => {
  expect(draw.merged([{ text: 'a' }, { text: 'b' }, { text: '' }, { text: 'c', color: 'error' }, { text: 'd', color: 'error' }, { text: 'e', dim: true }])).toEqual([
    { text: 'ab' }, { text: 'cd', color: 'error' }, { text: 'e', dim: true },
  ])
  // An empty line keeps its one empty span, so it still draws a row.
  expect(draw.merged([{ text: '' }])).toEqual([{ text: '' }])
  await load($, on)
  const tree: any = await drawPane($, 100, 'dock')
  const lines: any[] = []
  const walk = (n: any) => {
    if (Array.isArray(n)) return n.forEach(walk)
    if (n === null || typeof n !== 'object') return
    if (n.type === 'Text') return lines.push(n)
    walk(n.children)
  }
  walk(tree)
  const row = lines.find(l => rowsOf({ type: 'Box', props: {}, children: [l] })[0]?.text.startsWith('openai_top'))
  const spans = row.children.flat(Infinity).filter((c: any) => c?.type === 'Text')
  expect(spans.map((c: any) => [[c.children].flat(Infinity).join(''), c.props?.color])).toEqual([['openai_top ', undefined], ['\u{2717}', 'error'], ['    \u{2713}   ', undefined]])
})

// --- the summary's row cap ----------------------------------------------------------------------

test('the summary draws at most 4000 rows and counts the rows it cut, so a narrow pane stays under the engine\'s element limit', () => {
  const v = P(READER_AT_CAP)
  if (!v.ok) throw new Error('fixture invalid')
  const rowsAt = (n: number) => draw.idleLines(v.view, agents([]), n).map(l => l.map(x => x.text).join(''))
  // At 15 cells 31 lines of 1000 two-cell faces take 143 rows each, the boundary line 14 and the last
  // line 115: 4562 rows, 562 past the cap.
  const at15 = rowsAt(15)
  const s15 = at15.indexOf('Summary')
  expect(at15[s15 + 4001]).toBe('+562 more summary rows')
  expect(at15.length).toBe(s15 + 4002)
  // At 16 cells the summary takes 3988 rows and nothing is cut.
  const at16 = rowsAt(16)
  expect(at16.length - at16.indexOf('Summary') - 1).toBe(3988)
  expect(at16.some(t => t.endsWith('more summary rows'))).toBe(false)
})

// --- statuses ---------------------------------------------------------------------------------

test('the statuses are the launch codes, reader-failed with each reader error code, and the view codes: 31 in all', () => {
  const expected = new Set<string>([...LAUNCH_CODES, ...READER_ERROR_CODES.map(c => `reader-failed:${c}`), ...VIEW_CODES])
  expect(new Set(STATUS_CODES)).toEqual(expected)
  expect(STATUS_CODES.length).toBe(31)
})

test('every status has a mocked machine, reader-timeout included, so each one is mounted', () => {
  expect(STATUS_CODES.filter(c => STATUS_MACHINES[c] === null || STATUS_MACHINES[c] === undefined)).toEqual([])
  expect(STATUS_MACHINES['reader-timeout']).toEqual({ reader: 'timeout' })
})

const firstRow = (code: string, w: number | undefined, placement: 'inline' | 'dock') => texts(asTree(draw.pane({ ok: false, code }, agents([]), w, placement)))
const bandRow = (code: string, w: number | undefined) => texts(asTree(draw.band({ ok: false, code }, agents([]), w)))

test('at 30 columns each status draws one distinct row in the pane and the band, the two quiet statuses none in the band', () => {
  const pane30 = STATUS_CODES.map(c => firstRow(c, 30, 'dock'))
  expect(pane30.every(rows => rows.length === 1)).toBe(true)
  expect(new Set(pane30.map(r => r[0])).size).toBe(31)
  for (const c of STATUS_CODES) expect([c, firstRow(c, 30, 'inline')]).toEqual([c, firstRow(c, 30, 'dock')])
  const quiet = ['no-active-run', 'reader-failed:tree-missing']
  for (const c of quiet) expect([c, bandRow(c, 30)]).toEqual([c, []])
  const band30 = STATUS_CODES.filter(c => !quiet.includes(c)).map(c => bandRow(c, 30))
  expect(band30.every(rows => rows.length === 1)).toBe(true)
  expect(new Set(band30.map(r => r[0])).size).toBe(29)
  // Only the two codes longer than 30 cells are cut; every other code is whole.
  const cut = pane30.map(r => r[0]!).filter(t => t.endsWith('\u{2026}'))
  expect(cut).toEqual(['reader-failed:project-root-in\u{2026}', 'reader-failed:token-set-unava\u{2026}'])
})

test('a status keeps its prefix when it fits and drops the prefix before it cuts the code', () => {
  expect(firstRow('version-mismatch', 60, 'dock')).toEqual(['Dashboard unavailable: version-mismatch'])
  expect(firstRow('version-mismatch', 30, 'dock')).toEqual(['version-mismatch'])
  expect(bandRow('version-mismatch', 60)).toEqual(['crux-mods dashboard: version-mismatch'])
  expect(bandRow('version-mismatch', 30)).toEqual(['version-mismatch'])
  expect(firstRow('reader-failed:token-set-unavailable', 40, 'dock')).toEqual(['reader-failed:token-set-unavailable'])
})

test('reader-timeout draws through the builders with its prefix from 37 cells and its fitted code below', () => {
  for (const w of [...WIDTHS, ...SMALL]) {
    const n = drawingWidth(w)
    for (const placement of ['inline', 'dock'] as const) {
      const tree = asTree(draw.pane({ ok: false, code: 'reader-timeout' }, agents([]), w, placement))
      check(tree, n, placement, `reader-timeout ${placement} ${w}`)
      expect([w, texts(tree)]).toEqual([w, [n >= 37 ? 'Dashboard unavailable: reader-timeout' : width.fit('reader-timeout', n)]])
    }
    check(asTree(draw.band({ ok: false, code: 'reader-timeout' }, agents([]), w)), n, 'band', `reader-timeout band ${w}`)
  }
})

for (const code of STATUS_CODES) {
  const machine = STATUS_MACHINES[code]
  test(`the status ${code} is the answer's status and the pane's first and only row, fitted at every width`, async ($, on) => {
    install(on, { reader: ok(READER_OK), ...machine })
    const r = await $.command.run({ command: 'crux-dashboard' } as any)
    expect(String(r.text).split('\n')).toContain(`dashboard status ${code}`)
    for (const w of [...WIDTHS, ...SMALL]) {
      const n = drawingWidth(w)
      for (const placement of ['inline', 'dock'] as const) {
        const tree = await drawPane($, w, placement)
        check(tree, n, placement, `${code} ${placement} ${w}`)
        expect([w, placement, texts(tree)]).toEqual([w, placement, firstRow(code, w, placement)])
      }
      const band = await drawBand($, w)
      check(band, n, 'band', `${code} band ${w}`)
      expect([w, texts(band)]).toEqual([w, bandRow(code, w)])
    }
  })
}

// --- colour is never alone ----------------------------------------------------------------------

const withoutColour = (v: unknown): unknown => {
  if (Array.isArray(v)) return v.map(withoutColour)
  if (v === null || typeof v !== 'object') return v
  const o = v as Record<string, unknown>
  const props = { ...((o.props as Record<string, unknown>) ?? {}) }
  delete props.color
  delete props.borderColor
  return { ...o, props, children: withoutColour(o.children) }
}

test('with every colour removed the drawing still tells blocked from running, one kind from another, and an escalation from none', async ($, on) => {
  await load($, on, { reader: ok(READER_ESCALATED), agents: [RUNNING] })
  const pane = withoutColour(await drawPane($, 100, 'dock'))
  expect(layout(pane, 100).colors).toEqual([])
  const rows = texts(pane)
  const strip = rows.find(t => t.startsWith('adr '))!
  expect(strip).toBe('adr \u{2713}\u{2717}  untagged \u{25B8}\u{25CC}')
  expect(rows).toContain('p2  blocked  adr-1  Council on the decision  1h35m')
  expect(rows.filter(t => t.startsWith('escalation p')).length).toBe(2)
  const band = texts(withoutColour(await drawBand($, 400)))[0]!
  expect(band).toContain('untagged')
  expect(band).toContain('\u{2717}|\u{25B8}')
  expect(band).toContain('escalation p3')
})

test('with every colour removed a run with no escalation draws no escalation text', async ($, on) => {
  await load($, on, { agents: [RUNNING] })
  const rows = [...texts(withoutColour(await drawPane($, 100, 'dock'))), ...texts(withoutColour(await drawBand($, 400)))]
  expect(rows.some(t => t.includes('escalation'))).toBe(false)
  // Positive control: the same drawing names the blocked prompt.
  expect(rows.some(t => t.includes('blocked'))).toBe(true)
})

// --- free text from a view built without the reader check ---------------------------------------

const UNSAFE = new RegExp('[\\p{Cc}\\p{Cf}\\p{Default_Ignorable_Code_Point}\\u2028\\u2029]', 'u')

test('removal-class characters in any free value never draw, and every line still fits', () => {
  const live = P(READER_STALLED_ESCALATED)
  const idle = P(idleDoc('latest', { summary: ['Ship\u{200B}ped\u{2028} it\u{E0041}', 'line\u{FE0F} two'] }))
  if (!live.ok || !idle.ok) throw new Error('fixture invalid')
  const v: any = clone(live.view)
  v.reader_version = '3.27.4\u{200B}\u{202E}'
  const r = v.runs[0]
  r.book_id = 'PB-0149\u{2066}'
  r.run_id = 'RUN-001\u{E0041}'
  r.councils[0].seats[0].role = 'openai\u{200D}_top'
  r.councils[0].record_path = 'promptbooks/\u{200B}x.json'
  r.prompts[0].module_tag = 'adr\u{AD}-1'
  r.prompts[2].title = 'Build\u{2028} the\u{FE0F} dashboard\u{34F}'
  const iv: any = clone(idle.view)
  iv.last_completed.book_id = 'PB-0150\u{200F}'
  const ag = agents([{ status: 'running', type: 'dev\u{2068}eloper', description: 'Plan\u{E0100} the\u{AD} thing\u{2029}' }])
  const all: string[] = []
  for (const view of [v, iv]) {
    for (const w of [...WIDTHS, ...SMALL]) {
      const n = drawingWidth(w)
      for (const placement of ['inline', 'dock'] as const) {
        const tree = asTree(draw.pane({ ok: true, view }, ag, w, placement))
        check(tree, n, placement, `direct ${placement} ${w}`)
        all.push(...texts(tree))
      }
      const band = asTree(draw.band({ ok: true, view }, ag, w))
      check(band, n, 'band', `direct band ${w}`)
      all.push(...texts(band))
    }
  }
  expect(all.filter(t => UNSAFE.test(t))).toEqual([])
  // Positive controls: what is left of each value is drawn.
  const text = all.join('\n')
  for (const part of ['reader 3.27.4', 'PB-0149 RUN-001', 'openai_top', 'Build the dashboard', 'adr-1', 'Shipped it', 'line two', 'developer  Plan the thing', 'PB-0150 RUN-002']) {
    expect([part, text.includes(part)]).toEqual([part, true])
  }
  // The tag with a removed character no longer names a known kind: its group draws the unknown kind.
  expect(text).toContain('? \u{2713}')
})

// --- no clock, and the text answer unchanged ------------------------------------------------------

test('no layout reads a clock: the band and the pane draw every fixture with every clock read throwing', () => {
  const docs = [READER_OK, READER_STALLED_ESCALATED, READER_TWO, READER_COUNCILS, IDLE_LATEST, IDLE_UNDETERMINED, idleDoc('not-requested'), READER_EMPTY]
  expect(() => withoutClock(() => {
    for (const doc of docs) {
      for (const w of [...WIDTHS, ...SMALL]) {
        draw.band(P(doc), agents([RUNNING]), w)
        draw.pane(P(doc), agents([RUNNING]), w, 'inline')
        draw.pane(P(doc), agents('x'), w, 'dock')
      }
    }
  })).not.toThrow()
  const sources = Object.values(draw).filter(f => typeof f === 'function').map(f => String(f))
  expect(sources.filter(s => CLOCK_READ.test(s))).toEqual([])
  expect(sources.some(s => s.includes('function docked') || s.includes('bandSegments'))).toBe(true)
})

// FNV-1a over UTF-16 code units: a checksum of each answer, computed at the base commit before
// this change, so a changed byte in any answer fails here.
const fnv1a = (s: string): string => {
  let h = 0x811c9dc5
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i)
    h = Math.imul(h, 0x01000193) >>> 0
  }
  return h.toString(16).padStart(8, '0')
}

// Computed at ef4f3265 by running answer() over these inputs: [name, checksum, length in code units].
const GOLDEN: [string, string, number][] = [
  ['READER_OK', '9e213754', 1548],
  ['READER_EMPTY', '796059ef', 119],
  ['READER_TWO', 'fb93221e', 2081],
  ['READER_STALLED', 'd0a6d7ae', 1548],
  ['READER_ESCALATED', '9113358a', 1582],
  ['IDLE_LATEST', '36dfa8ed', 723],
  ['IDLE_LATEST_DATED', '4db05882', 729],
  ['IDLE_UNDETERMINED', '8474fda1', 216],
  ['IDLE_RUN_IN_PROGRESS', 'abc822d1', 219],
  ['not-requested', '9bc5440a', 217],
  ['READER_AT_CAP', '36dfa8ed', 723],
  ['readerAt(null)', 'e41fbdf9', 1542],
  ['reader-failed:usage', '85cf459d', 125],
  ['reader-failed:project-root-invalid', 'f5cfd724', 140],
  ['reader-failed:config-invalid', '02d21ee6', 134],
  ['reader-failed:tree-missing', '63c7dff7', 132],
  ['reader-failed:containment', '52c8292e', 131],
  ['reader-failed:book-not-found', '4dead2da', 134],
  ['reader-failed:run-not-found', '83435c8a', 133],
  ['reader-failed:run-invalid', 'da1c4db9', 131],
  ['reader-failed:book-invalid', '22ac6e69', 132],
  ['reader-failed:token-set-unavailable', 'e1c4b9e1', 141],
  ['reader-failed:yaml-unavailable', 'ef790012', 136],
  ['reader-failed:time-limit', 'c520d865', 130],
  ['reader-failed:internal', '3c3d801b', 128],
  ['code:no-env-binary', 'e61da50a', 119],
  ['code:loader-var-set', '9d0b0a37', 120],
  ['code:config-dir-mismatch', '8d197f00', 125],
  ['code:inside-project', 'e8a0bd95', 120],
  ['code:project-root-invalid', '642cdb77', 126],
  ['code:home-invalid', 'f4255038', 118],
  ['code:uv-not-found', '0790771b', 118],
  ['code:crux-not-installed', '6c35edda', 124],
  ['code:version-mismatch', 'd3da973a', 122],
  ['code:reader-no-json-mode', '1c2f1225', 125],
  ['code:offline-unavailable', '0b3021b7', 125],
  ['code:reader-timeout', '50ccd848', 120],
  ['code:reader-cannot-start', '6c7c8423', 125],
  ['code:reader-cpu-limit', 'd7780aeb', 122],
  ['code:reader-failed', 'ed9ae4b0', 119],
  ['code:reader-output-invalid', '60d14812', 127],
  ['code:no-active-run', '796059ef', 119],
  ['code:reader-format-mismatch', '07001c21', 128],
]

test('the text answer is byte for byte the base commit\'s for 12 documents, the 13 reader failures and the 18 other codes', () => {
  const docs: Record<string, unknown> = {
    READER_OK, READER_EMPTY, READER_TWO, READER_STALLED, READER_ESCALATED, IDLE_LATEST, IDLE_LATEST_DATED, IDLE_UNDETERMINED,
    IDLE_RUN_IN_PROGRESS, 'not-requested': idleDoc('not-requested'), READER_AT_CAP, 'readerAt(null)': readerAt(null),
    ...Object.fromEntries(READER_ERROR_CODES.map(c => [`reader-failed:${c}`, readerError(c)])),
  }
  const got: [string, string, number][] = []
  for (const [name] of GOLDEN) {
    const a = name.startsWith('code:') ? answer({ ok: false, code: name.slice(5) }) : answer(P(docs[name]))
    got.push([name, fnv1a(a), a.length])
  }
  expect(GOLDEN.length).toBe(43)
  expect(got).toEqual(GOLDEN)
  // Positive control: a changed byte changes the checksum.
  expect(fnv1a(answer(P(READER_OK)) + ' ')).not.toBe(GOLDEN[0]![1])
})
