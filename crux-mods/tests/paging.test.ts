// The cycle pane's four parts: the slot for open cycles, the queue card, the latest closed cycle as a
// panel, and the paged `cycles:` list of the other closed cycles.
// The drawing tests call pane() directly. The register-level tests mount the Pane and press its buttons.
import {test, expect} from 'claude-code/testing'
import {parseReader} from '../hooks/lib/view.ts'
import {HARNESS, agents} from '../hooks/lib/claude.ts'
import {OLDER_PAGE_SIZE, olderPages, pane, type Block, type Line} from '../hooks/lib/draw.ts'
import {install, texts, PANE} from './fixtures/world.ts'

const cycleRow = (n: number, status = 'completed', extra: Record<string, unknown> = {}) => ({
  id: `CYC-${String(n).padStart(4, '0')}`, title: `Cycle title ${n}`, type: 'iterate', status, phase: 'build', pass: 1, pass_limit: 2,
  phases: ['plan', 'build', 'test', 'review', 'reflect'],
  tasks: [
    {id: 'a', phase: 'plan', description: 'Plan it', status: 'done'},
    {id: 'b', phase: 'build', description: `Current work ${n}`, status: status === 'active' ? 'active' : 'done'},
  ],
  returns: [], waits: [], blocker: null, reflection: null, modified_s: 1780000000,
  started_s: 1779999000, ended_s: status === 'active' || status === 'paused' ? null : 1779999900, paused_s: 0,
  open_started_s: status === 'active' || status === 'paused' ? 1779999500 : null, basis: 'recorded',
  phase_times: [{phase: 'plan', active_s: 500, paused_s: 0}], ...extra,
})
const qItem = (n: number, state: string, extra: Record<string, unknown> = {}) => ({
  id: `Q-${String(n).padStart(4, '0')}`, title: `Queue title ${n}`, state, suggested_type: 'iterate', cycle: null, cycle_status: null, ...extra,
})
const doc = (cycles: unknown[], queue?: unknown) => ({
  format: 'crux.cycle-progress', format_version: 2, ok: true, docs_dir: 'bionic', now_s: 1780000000, cycles,
  ...(queue === undefined ? {} : {queue}),
})
const parsed = (d: unknown) => {
  const p = parseReader(JSON.stringify(d))
  expect(p.ok).toBe(true)
  return p
}
const draw = (d: unknown, page?: number, width = 100) => pane(parsed(d), agents([]), width, 'docked', HARNESS, page)
const plain = (l: Line) => l.map(s => s.text).join('')
const flat = (b: Block): Line[] => (b.kind === 'line' ? [b.line] : b.children.flatMap(flat))
const rows = (b: Block): string[] => flat(b).map(plain)
const top = (b: Block): Block[] => (b.kind === 'box' ? b.children : [])
// The text of one top-level block.
const blockText = (b: Block): string[] => rows(b)

// --- the slot ----------------------------------------------------------------------------------

test('an active cycle draws first in the slot with type, phase, loop and limit, task count and current task', () => {
  const b = draw(doc([cycleRow(5, 'active'), cycleRow(4)]))
  const first = top(b)[0]!
  expect(first.kind).toBe('box')
  const text = blockText(first).join('\n')
  expect(text).toContain('CYC-0005')
  expect(text).toContain('iterate')
  expect(text).toContain('loop 1 of 2')
  expect(text).toContain('build: Current work 5')
  expect(text).toContain('1/2 tasks')
  // The latest closed cycle is a panel after the slot, and with one closed cycle no `cycles:` heading draws.
  const next = top(b)[1]!
  expect(next.kind).toBe('box')
  expect(blockText(next).join('\n')).toContain('CYC-0004')
  expect(rows(b)).not.toContain('cycles:')
})

test('a paused cycle is open work and draws in the slot', () => {
  const b = draw(doc([cycleRow(5, 'paused'), cycleRow(4)]))
  expect(top(b)[0]!.kind).toBe('box')
  expect(blockText(top(b)[0]!).join('\n')).toContain('CYC-0005')
})

test('with every cycle completed or abandoned no slot block is drawn', () => {
  const b = draw(doc([cycleRow(5), cycleRow(4, 'abandoned')]))
  // The latest closed cycle is the one panel, then the `cycles:` heading and one compact row: no placeholder.
  expect(top(b).map(c => c.kind)).toEqual(['box', 'line', 'line'])
  expect(rows(b)[0]).toContain('CYC-0005')
  expect(rows(b)).toContain('cycles:')
  const queued = draw(doc([cycleRow(5)], {ok: true, items: [qItem(1, 'pending')], authorization: null}))
  expect(top(queued).map(c => c.kind)).toEqual(['box', 'box'])
  expect(blockText(top(queued)[0]!)[0]).toContain('Queue')
  expect(blockText(top(queued)[1]!)[0]).toContain('CYC-0005')
})

test('at most two open cycles draw, and a +N open line counts the rest', () => {
  const two = draw(doc([cycleRow(9, 'active'), cycleRow(8, 'paused')]))
  expect(top(two).filter(c => c.kind === 'box').length).toBe(2)
  expect(rows(two).some(r => r.includes('open'))).toBe(false)
  const four = draw(doc([cycleRow(9, 'active'), cycleRow(8, 'paused'), cycleRow(7, 'paused'), cycleRow(6, 'paused')]))
  expect(top(four).filter(c => c.kind === 'box').length).toBe(2)
  expect(rows(four)).toContain('+2 open')
})

// --- the queue card ----------------------------------------------------------------------------

const queueRows = (b: Block): string[] => {
  const card = top(b).find(c => c.kind === 'box' && blockText(c)[0]!.startsWith('Queue'))
  return card === undefined ? [] : blockText(card)
}

test('a null queue and an empty queue draw no card', () => {
  expect(queueRows(draw(doc([cycleRow(1)])))).toEqual([])
  expect(queueRows(draw(doc([cycleRow(1)], null)))).toEqual([])
  expect(queueRows(draw(doc([cycleRow(1)], {ok: true, items: [], authorization: null})))).toEqual([])
  // Only a running started item: nothing upcoming and nothing finished.
  const running = qItem(1, 'started', {cycle: 'CYC-0001', cycle_status: 'active'})
  expect(queueRows(draw(doc([cycleRow(1, 'active')], {ok: true, items: [running], authorization: null})))).toEqual([])
})

test('a queue that could not be read draws one warning line and no error text', () => {
  const b = draw(doc([cycleRow(1)], {ok: false, error: 'bad queue file'}))
  const warn = top(b).find(c => c.kind === 'line' && plain((c as any).line).startsWith('Queue unavailable'))
  expect(warn).toBeDefined()
  expect(rows(b).join('\n')).not.toContain('bad queue file')
  expect(((warn as any).line as Line).some(s => s.color === 'warning')).toBe(true)
})

test('a short queue draws the header, the upcoming rows and the finished rows', () => {
  const items = [
    qItem(1, 'started', {cycle: 'CYC-0001', cycle_status: 'completed'}),
    qItem(2, 'pending'), qItem(3, 'held'),
  ]
  const r = queueRows(draw(doc([cycleRow(1)], {ok: true, items, authorization: {kind: 'next-n', remaining: ['Q-0002', 'Q-0003']}})))
  expect(r[0]).toBe('Queue  2 queued  authorized: next-n, remaining Q-0002 Q-0003')
  expect(r[1]).toContain('Q-0002')
  expect(r[1]).toContain('Queue title 2')
  expect(r[1]).toContain('pending')
  expect(r[2]).toContain('Q-0003')
  expect(r[2]).toContain('held')
  expect(r[3]).toContain('Q-0001')
  expect(r[3]).toContain('CYC-0001')
  expect(r[3]).toContain('completed')
  expect(r.length).toBe(4)
  expect(r.join('\n')).not.toContain('more')
})

test('a queue with no authorization says so', () => {
  const r = queueRows(draw(doc([cycleRow(1)], {ok: true, items: [qItem(1, 'starting')], authorization: null})))
  expect(r[0]).toBe('Queue  1 queued  not authorized')
  expect(r[1]).toContain('starting')
})

test('an overflowing queue is bounded at nine rows with a +N more line', () => {
  const items = [
    ...Array.from({length: 4}, (_, i) => qItem(i + 1, 'started', {cycle: `CYC-${String(i + 1).padStart(4, '0')}`, cycle_status: i % 2 === 0 ? 'completed' : 'abandoned'})),
    ...Array.from({length: 8}, (_, i) => qItem(i + 5, 'pending')),
  ]
  const r = queueRows(draw(doc([cycleRow(1)], {ok: true, items, authorization: null})))
  expect(r.length).toBe(9)
  expect(r[0]).toContain('8 queued')
  // Five upcoming in queue order, then the last two finished in queue order.
  expect(r.slice(1, 6).map(x => x.match(/Q-\d+/)![0])).toEqual(['Q-0005', 'Q-0006', 'Q-0007', 'Q-0008', 'Q-0009'])
  expect(r.slice(6, 8).map(x => x.match(/Q-\d+/)![0])).toEqual(['Q-0003', 'Q-0004'])
  expect(r[7]).toContain('abandoned')
  // 3 upcoming are left out. The 2 finished items hidden above them are not counted.
  expect(r[8]).toBe('+3 more')
})

test('hidden finished items never draw a +N more line', () => {
  const items = [
    ...Array.from({length: 13}, (_, i) => qItem(i + 1, 'started', {cycle: `CYC-${String(i + 1).padStart(4, '0')}`, cycle_status: 'completed'})),
    ...Array.from({length: 4}, (_, i) => qItem(i + 14, 'pending')),
  ]
  const r = queueRows(draw(doc([cycleRow(1)], {ok: true, items, authorization: null})))
  expect(r.length).toBe(7)
  expect(r.some(x => x.includes('more'))).toBe(false)
})

test('an open cycle past the slot is counted in +N open and never listed as a closed row', () => {
  const open = [9, 8, 7, 6].map((n, i) => cycleRow(n, i === 0 ? 'active' : 'paused'))
  const d = doc([...open, cycleRow(3), cycleRow(2), cycleRow(1)])
  expect(olderPages(parsed(d))).toBe(1)
  const b = draw(d)
  expect(rows(b)).toContain('+2 open')
  // The latest closed cycle is the panel; the other two are rows.
  const listed = listRows(b).filter(r => r.includes('CYC-'))
  expect(listed.length).toBe(2)
  expect(listed.some(r => r.includes('CYC-0007') || r.includes('CYC-0006'))).toBe(false)
  expect(top(b).filter(c => c.kind === 'box').map(c => blockText(c)[0]!.slice(0, 8))).toEqual(['CYC-0009', 'CYC-0008', 'CYC-0003'])
  // Only open cycles past the slot: no closed cycles and no pages.
  expect(olderPages(parsed(doc(open)))).toBe(0)
})

test('a queue title is drawn through the sanitiser and rows fit a narrow width', () => {
  const hostile = qItem(1, 'pending', {title: 'Run this\u001b[2J‮ now ' + 'x'.repeat(200)})
  const b = draw(doc([cycleRow(1)], {ok: true, items: [hostile], authorization: null}), 0, 40)
  const joined = JSON.stringify(b)
  expect(joined.includes('\\u001b')).toBe(false)
  expect(joined.includes('‮')).toBe(false)
})

// --- the latest closed cycle and the paged `cycles:` list -----------------------------------------------------------------------

const many = (k: number, open = false) => [...(open ? [cycleRow(k + 1, 'active')] : []), ...Array.from({length: k}, (_, i) => cycleRow(k - i))]
const listRows = (b: Block) => top(b).filter(c => c.kind === 'line').map(c => plain((c as any).line))
// The ids CYC-hi down to CYC-lo, newest first, as the list draws them.
const ids = (hi: number, lo: number) => Array.from({length: hi - lo + 1}, (_, i) => `CYC-${String(hi - i).padStart(4, '0')}`)

test('the page size is ten and olderPages counts the closed cycles after the latest one', () => {
  expect(OLDER_PAGE_SIZE).toBe(10)
  expect(olderPages(parsed(doc([])))).toBe(0)
  expect(olderPages(parsed(doc(many(1))))).toBe(0)
  expect(olderPages(parsed(doc(many(2))))).toBe(1)
  expect(olderPages(parsed(doc(many(11, true))))).toBe(1)
  expect(olderPages(parsed(doc(many(12, true))))).toBe(2)
  expect(olderPages(parsed(doc(many(20))))).toBe(2)
  // The reader accepts at most 60 cycles: 59 list rows after the latest closed one, six pages.
  expect(olderPages(parsed(doc(many(60))))).toBe(6)
  expect(olderPages({ok: false, code: 'reader-failed'})).toBe(0)
})

test('page 0 shows the latest closed cycle as a panel, then `cycles:` and the next ten as rows with a footer', () => {
  const b = draw(doc(many(14, true)), 0)
  const panelText = blockText(top(b).filter(c => c.kind === 'box').pop()!).join('\n')
  expect(panelText).toContain('CYC-0014')
  expect(panelText).toContain('Cycle title 14')
  expect(panelText).toContain('completed')
  const r = listRows(b)
  expect(r.length).toBe(12)
  expect(r[0]).toBe('cycles:')
  expect(r[1]).toContain('CYC-0013')
  expect(r[1]).toContain('iterate')
  expect(r[1]).toContain('completed')
  expect(r[1]).toContain('2/2')
  expect(r[1]).toContain('Cycle title 13')
  expect(r[10]).toContain('CYC-0004')
  expect(r[11]).toBe('page 1/2')
})

test('the first, a middle and the last page show their own cycles', () => {
  // 20 cycles: the latest closed is CYC-0019, then 18 rows over two pages.
  const first = listRows(draw(doc(many(19, true)), 0))
  expect(first.map(x => x.match(/CYC-\d+/)?.[0])).toEqual([undefined, ...ids(18, 9), undefined])
  expect(first[11]).toBe('page 1/2')
  const full = listRows(draw(doc(many(19, true)), 1))
  expect(full.map(x => x.match(/CYC-\d+/)?.[0])).toEqual([undefined, ...ids(8, 1), undefined])
  expect(full[9]).toBe('page 2/2')
  // 26 cycles: the latest closed is CYC-0025, then 24 rows over three pages, so page 2 is a middle page.
  const mid = listRows(draw(doc(many(25, true)), 1))
  expect(mid.map(x => x.match(/CYC-\d+/)?.[0])).toEqual([undefined, ...ids(14, 5), undefined])
  expect(mid[11]).toBe('page 2/3')
  const last = listRows(draw(doc(many(14, true)), 1))
  expect(last.map(x => x.match(/CYC-\d+/)?.[0])).toEqual([undefined, ...ids(3, 1), undefined])
  expect(last[4]).toBe('page 2/2')
})

test('the reader accepts 60 cycles whole and refuses 61, and the 60 page over six pages of ten', () => {
  const sixty = parseReader(JSON.stringify(doc(many(60))))
  if (!sixty.ok) throw new Error('60 cycles did not read as a view')
  expect(sixty.view.cycles!.length).toBe(60)
  expect(olderPages(sixty)).toBe(6)
  const last = listRows(draw(doc(many(60)), 5))
  expect(last.map(x => x.match(/CYC-\d+/)?.[0])).toEqual([undefined, ...ids(9, 1), undefined])
  expect(last[10]).toBe('page 6/6')
  // The producer sends at most 60, so a 61-cycle document is not reader output.
  expect(parseReader(JSON.stringify(doc(many(61))))).toEqual({ok: false, code: 'reader-output-invalid'})
})

test('a cycle keeps at most 20 returns and 20 approval waits', () => {
  const ret = (i: number) => ({pass: i + 1, phase: 'build', reason: `r${i}`})
  const at = (extra: Record<string, unknown>) => parseReader(JSON.stringify(doc([cycleRow(1, 'completed', extra)])))
  expect(at({returns: Array.from({length: 20}, (_, i) => ret(i)), waits: Array.from({length: 20}, (_, i) => `w${i}`)}).ok).toBe(true)
  expect(at({returns: Array.from({length: 21}, (_, i) => ret(i))})).toEqual({ok: false, code: 'reader-output-invalid'})
  expect(at({waits: Array.from({length: 21}, (_, i) => `w${i}`)})).toEqual({ok: false, code: 'reader-output-invalid'})
})

test('exactly one closed cycle draws the panel alone: no heading, no footer', () => {
  const b = draw(doc(many(1)))
  expect(top(b).map(c => c.kind)).toEqual(['box'])
  expect(listRows(b)).toEqual([])
})

test('no drawn line says older', () => {
  for (const k of [1, 2, 14]) for (const page of [0, 1]) expect(rows(draw(doc(many(k, true)), page)).some(r => r.includes('older'))).toBe(false)
})

test('a page out of range is clamped', () => {
  const d = doc(many(14, true))
  expect(listRows(draw(d, 99))).toEqual(listRows(draw(d, 2)))
  expect(listRows(draw(d, -4))).toEqual(listRows(draw(d, 0)))
  expect(listRows(draw(d, Number.NaN))).toEqual(listRows(draw(d, 0)))
  expect(listRows(draw(d, 1.7))).toEqual(listRows(draw(d, 1)))
})

test('a single page draws no footer, and the default page is the first', () => {
  const b = draw(doc(many(11)))
  expect(listRows(b).length).toBe(11)
  expect(listRows(b).some(x => x.startsWith('page'))).toBe(false)
  const d = doc(many(5))
  expect(listRows(draw(d))).toEqual(listRows(draw(d, 0)))
})

test('every closed row fits its width and the title is last', () => {
  for (const w of [100, 40, 20]) {
    const b = draw(doc(many(2)), 0, w)
    for (const l of flat(b)) expect(plain(l).length).toBeLessThanOrEqual(w)
  }
})

// --- the hooks module: the page atom and the buttons -------------------------------------------

const CYCLES_OUT = {exitCode: 0, stdout: JSON.stringify(doc(many(14, true), {ok: true, items: [qItem(1, 'pending')], authorization: null}))}
const SHORT_OUT = {exitCode: 0, stdout: JSON.stringify(doc(many(2, true)))}

// The kit keeps session state in memory, so a press writes the page atom and the Pane draws it again.
const mountPane = ($: any) => $.ui.mount({plugin: 'crux-mods', surface: 'terminal', component: 'Pane', requestId: 'crux-dashboard', props: PANE})
const shownOf = async (ui: any) => texts(await ui.drawn()).join('\n')

test('the Pane draws the first page and offers next and previous buttons past one page', async ($, on) => {
  install(on, {reader: CYCLES_OUT})
  await $.command.run({command: 'crux-dashboard'} as any)
  const ui = await mountPane($)
  const first = await shownOf(ui)
  expect(first).toContain('page 1/2')
  expect(first).toContain('CYC-0014')
  expect(await ui.find({type: 'Button', key: 'older-next'})).toBeDefined()
  expect(await ui.find({type: 'Button', key: 'older-previous'})).toBeDefined()
  expect(first).not.toContain('older')
  await ui.unmount()
})

test('pressing next steps the page and previous steps it back, clamped at both ends', async ($, on) => {
  install(on, {reader: CYCLES_OUT})
  await $.command.run({command: 'crux-dashboard'} as any)
  const ui = await mountPane($)
  await ui.press({key: 'older-previous'})
  expect(await shownOf(ui)).toContain('page 1/2')
  await ui.press({key: 'older-next'})
  expect(await shownOf(ui)).toContain('page 2/2')
  expect(await shownOf(ui)).toContain('CYC-0003')
  await ui.press({key: 'older-next'})
  await ui.press({key: 'older-next'})
  expect(await shownOf(ui)).toContain('page 2/2')
  await ui.press({key: 'older-previous'})
  expect(await shownOf(ui)).toContain('page 1/2')
  await ui.unmount()
})

test('the buttons carry the n and p hotkeys and draw plain', async ($, on) => {
  install(on, {reader: CYCLES_OUT})
  await $.command.run({command: 'crux-dashboard'} as any)
  const ui = await mountPane($)
  const next = (await ui.find({type: 'Button', key: 'older-next'})) as any
  const previous = (await ui.find({type: 'Button', key: 'older-previous'})) as any
  expect(next.props.hotkey).toBe('n')
  expect(previous.props.hotkey).toBe('p')
  expect(next.props.plain).toBe(true)
  await ui.unmount()
})

test('one page of closed cycles draws no buttons', async ($, on) => {
  install(on, {reader: SHORT_OUT})
  await $.command.run({command: 'crux-dashboard'} as any)
  const ui = await mountPane($)
  expect(await ui.find({type: 'Button'})).toBeUndefined()
  expect(await shownOf(ui)).toContain('CYC-0002')
  expect(await shownOf(ui)).toContain('CYC-0001')
  await ui.unmount()
})

// A stored page, as a reload of the mod's code or a longer session leaves it. The hook answers the page
// key and passes every other key to the kit's own store.
function storePage(on: any, stored: unknown) {
  on('state.get', (_$: any, e: any, next: any) =>
    (e.key === 'page' ? {value: {value: stored, version: 1}} : next(e)) as any)
}

test('a stored page past the end is clamped when drawn', async ($, on) => {
  install(on, {reader: CYCLES_OUT})
  storePage(on, {shape: 'page-1', value: 9})
  await $.command.run({command: 'crux-dashboard'} as any)
  const ui = await mountPane($)
  expect(await shownOf(ui)).toContain('page 2/2')
  await ui.unmount()
})

test('a stored page in range is drawn', async ($, on) => {
  install(on, {reader: CYCLES_OUT})
  storePage(on, {shape: 'page-1', value: 1})
  await $.command.run({command: 'crux-dashboard'} as any)
  const ui = await mountPane($)
  expect(await shownOf(ui)).toContain('page 2/2')
  await ui.unmount()
})

test('a stored page under another shape tag reads as the first page', async ($, on) => {
  install(on, {reader: CYCLES_OUT})
  storePage(on, {shape: 'page-0', value: 2})
  await $.command.run({command: 'crux-dashboard'} as any)
  const ui = await mountPane($)
  expect(await shownOf(ui)).toContain('page 1/2')
  await ui.unmount()
})

// --- the default harness ----------------------------------------------------------------------

test("the default harness pages: the footer draws and no +N more line does", () => {
  const lines = rows(draw(doc([cycleRow(19, "active"), ...Array.from({length: 13}, (_, i) => cycleRow(13 - i))])))
  expect(lines.some(l => l.includes("page 1/2"))).toBe(true)
  expect(lines.some(l => l.includes("more"))).toBe(false)
})

test('a harness that cannot turn pages draws the first page and a +N more line, and no footer', () => {
  const lines = listRows(pane(parsed(doc(many(14, true))), agents([]), 100, 'docked', {...HARNESS, pages: false}))
  expect(lines.length).toBe(1 + OLDER_PAGE_SIZE + 1)
  expect(lines.map(x => x.match(/CYC-\d+/)?.[0])).toEqual([undefined, ...ids(13, 4), undefined])
  expect(lines[lines.length - 1]).toBe('+3 more')
  expect(lines.some(l => l.startsWith('page'))).toBe(false)
  const one = listRows(pane(parsed(doc(many(11))), agents([]), 100, 'docked', {...HARNESS, pages: false}))
  expect(one.length).toBe(1 + OLDER_PAGE_SIZE)
  expect(one.some(l => l.includes('more'))).toBe(false)
})
