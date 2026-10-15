// A request such as "show the run" opens the run dashboard pane while the prompt passes on
// unchanged. The behaviour tests submit through the engine's `$.prompt.submit`, so the hook under
// test runs as a session runs it, above a test hook that stands for the engine. The pins, the direct
// tests of the phrase module, the direct calls of `register` and its handler, and case 8 call the
// module or read the manifest directly.
import { test, expect } from 'claude-code/testing'
import { capabilities } from '../hooks/capabilities.ts'
import { LAUNCH_CODES } from '../hooks/lib/launch.ts'
import { MAX_PROMPT_UNITS, PHRASES, asksForTheRun, matchesPhrase } from '../hooks/lib/phrases.ts'
import { register } from '../hooks/register.tsx'
import { READER_OK } from './fixtures/reader-output.ts'
import { BAND, PANE, install, texts } from './fixtures/world.ts'
import type { Opts } from './fixtures/world.ts'

const SIX = ['show the run', 'show run progress', 'visualize run progress', 'run status', 'promptbook status', 'cycle status']
const PANE_OPEN = { id: 'crux-dashboard', title: 'Dashboard' }
const CANARY = 'CANARY-7f3a9c1e'
const okReader = (extra: Record<string, unknown> = {}) => ({ exitCode: 0, stdout: JSON.stringify(READER_OK), ...extra })

// The 16 origin kinds Claude Code 2.1.296 and 2.1.299 declare, an unknown kind, an origin with no
// kind and no origin: 19 rows. These 12 kinds carry no field beside the kind; `channel` carries a
// server and `plugin` a name.
const KINDS_WITH_NO_FIELD = [
  'sdk', 'task-notification', 'scheduled-trigger', 'peer', 'peer-send-message', 'projects-relay', 'coordinator',
  'observer', 'observer-activity', 'auto-continuation', 'unclassified', 'slack-ping',
]
const ORIGINS: [string, Record<string, unknown> | undefined][] = [
  ['composer', { kind: 'composer' }],
  ['bridge', { kind: 'bridge' }],
  ...KINDS_WITH_NO_FIELD.map((k): [string, Record<string, unknown>] => [k, { kind: k }]),
  ['channel', { kind: 'channel', server: 'a-server' }],
  ['plugin', { kind: 'plugin', name: 'a-plugin' }],
  ['an unknown kind', { kind: 'a-kind-from-a-later-release' }],
  ['an origin with no kind', {}],
  ['no origin', undefined],
]
const ORIGIN_ROWS = 19
const typed = (kind: string) => kind === 'composer' || kind === 'bridge'

// A hook beneath the plugin: it records each event it receives and answers a distinct text.
function beneath(on: any) {
  const seen: any[] = []
  on('prompt.submit', (_$: any, e: any) => {
    seen.push(e)
    return { text: `beneath answer ${seen.length}` } as any
  })
  return seen
}

type Call = { event: string; input: any }

// The recording registrar. Each hook registered through it records its event and input before the
// hook runs. A test's own hook can stand in for the one `install` registers on an event, because the
// kit refuses a second hook on one event.
function recording(on: any, calls: Call[], standIn: Record<string, any> = {}) {
  return (event: string, ...rest: any[]) => {
    const hook = rest[rest.length - 1]
    const use = standIn[event] ?? hook
    return on(event, ...rest.slice(0, -1), async ($: any, e: any, next: any) => {
      calls.push({ event, input: e })
      return use($, e, next)
    })
  }
}

// Registers pass-through hooks on state.get, state.set, ui.invalidate and ui.resolve, so the
// recording registrar records each of those calls, which the kit answers beneath. The element tables
// that ui.resolve looks up are fetched when the plugins load, once per surface and component. A
// ui.resolve input names the surface and the component, never the props.
function watchKitCalls(on: any) {
  for (const event of ['state.get', 'state.set', 'ui.invalidate', 'ui.resolve']) on(event, ($: any, e: any, next: any) => next(e))
}

// The world, the recorded calls and the beneath hook for one test.
function setup($: any, on: any, o: Opts = {}, standIn: Record<string, any> = {}) {
  const seen = beneath(on)
  const calls: Call[] = []
  const rec = recording(on, calls, standIn)
  watchKitCalls(rec)
  const w = install(rec, o)
  return { w, calls, seen }
}
const opensOf = (calls: Call[]) => calls.filter(c => c.event === 'ui.open')

// Submits one prompt and says what the beneath hook saw and how many opens were requested.
async function submit($: any, calls: Call[], seen: any[], input: Record<string, unknown>) {
  const opened = opensOf(calls).length
  const before = seen.length
  const result = await $.prompt.submit(input as any)
  return { result, opened: opensOf(calls).length - opened, seen: seen.slice(before) }
}

const composer = (text: string, more: Record<string, unknown> = {}) => ({ text, wait: false, origin: { kind: 'composer' }, ...more })
// A text as a failure label, JSON-quoted so its whitespace and control characters show.
const shown = (s: string) => JSON.stringify(s)
// The reader's run time on the mocked clock, and a wait long enough for that run to finish.
const READER_DELAY_MS = 2000
const PAST_THE_READER_MS = 2500

// --- the pins ----------------------------------------------------------------------------------

test('the phrase set is the six phrases in order', () => {
  expect([...PHRASES]).toEqual(SIX)
})

test('the bound is 38', () => {
  expect(MAX_PROMPT_UNITS).toBe(38)
  expect(MAX_PROMPT_UNITS).toBe(Math.max(...PHRASES.map(p => p.length)) + 16)
})

test('matchesPhrase and asksForTheRun give the expected booleans', () => {
  expect(matchesPhrase('show the run')).toBe(true)
  expect(matchesPhrase('  SHOW   the RUN!')).toBe(true)
  expect(matchesPhrase('show the run please')).toBe(false)
  expect(asksForTheRun({ text: 'show the run', origin: { kind: 'composer' } })).toBe(true)
  expect(asksForTheRun({ text: 'show the run', origin: { kind: 'sdk' } })).toBe(false)
})

// The inputs the kit may refuse or stamp are held by direct calls: an attachments value that is not
// an array, a text that is not a string, an origin with no kind and no origin. Each row also has a
// control that is true, so a false is the input's and not the helper's.
test('asksForTheRun refuses the inputs a typed prompt cannot carry', () => {
  const ok = { text: 'show the run', origin: { kind: 'composer' } }
  expect(asksForTheRun(ok)).toBe(true)
  expect(asksForTheRun({ ...ok, attachments: [] })).toBe(true)
  expect(asksForTheRun({ ...ok, attachments: 'x' })).toBe(false)
  expect(asksForTheRun({ ...ok, attachments: {} })).toBe(false)
  expect(asksForTheRun({ ...ok, attachments: null })).toBe(false)
  expect(asksForTheRun({ ...ok, attachments: [{ type: 'image' }] })).toBe(false)
  expect(asksForTheRun({ ...ok, text: 42 })).toBe(false)
  expect(asksForTheRun({ ...ok, text: undefined })).toBe(false)
  expect(asksForTheRun({ ...ok, text: ['show the run'] })).toBe(false)
  expect(asksForTheRun({ text: 'show the run', origin: {} })).toBe(false)
  expect(asksForTheRun({ text: 'show the run', origin: { kind: 7 } })).toBe(false)
  expect(asksForTheRun({ text: 'show the run' })).toBe(false)
  expect(asksForTheRun({ text: 'show the run', origin: { kind: 'bridge' } })).toBe(true)
})

// One closing mark is dropped, after a first trim and before a second. A doubled mark is a near miss.
test('matchesPhrase drops one closing mark, between two trims', () => {
  for (const text of ['show the run?', 'show the run? ', 'show the run! ', 'show the run.\n', 'show the run ?']) {
    expect([shown(text), matchesPhrase(text)]).toEqual([shown(text), true])
  }
  for (const text of ['show the run?!', 'show the run..', 'show the run!?', 'show the run. .']) {
    expect([shown(text), matchesPhrase(text)]).toEqual([shown(text), false])
  }
})

// The whitespace the match trims and collapses is exactly six ASCII characters: space, tab, line
// feed, vertical tab, form feed and carriage return.
test('matchesPhrase trims and collapses exactly the six ASCII whitespace characters', () => {
  for (const c of [' ', '\t', '\n', '\v', '\f', '\r']) {
    const text = `${c}show${c}the${c}${c}run${c}`
    expect([shown(text), matchesPhrase(text)]).toEqual([shown(text), true])
  }
  // Other ASCII control characters are not whitespace, inside the text or at its end.
  for (const c of ['\u0007', '\u0008', '\u001c', '\u001f']) {
    for (const text of [`show${c}the run`, `show the run${c}`]) {
      expect([shown(text), matchesPhrase(text)]).toEqual([shown(text), false])
    }
  }
})

// A field whose getter throws, so a test sees whether the field was read.
function trap(input: Record<string, unknown>, field: string) {
  Object.defineProperty(input, field, { enumerable: true, get() { throw new Error(`read: ${field}`) } })
  return input as any
}

// The order is the privacy property: the text of a prompt the user did not type, or of one with an
// attachment, is never read. The result alone cannot show it, so the getters do.
test('asksForTheRun reads the origin, then the attachments, then the text', () => {
  // A prompt of another origin is refused before its attachments or its text are read.
  expect(asksForTheRun(trap(trap({ origin: { kind: 'sdk' } }, 'attachments'), 'text'))).toBe(false)
  // A typed prompt with an attachment is refused before its text is read.
  expect(asksForTheRun(trap({ origin: { kind: 'composer' }, attachments: [{ type: 'image' }] }, 'text'))).toBe(false)
  // The controls: each trap fires once its field is reached.
  expect(() => asksForTheRun(trap({ origin: { kind: 'composer' } }, 'text'))).toThrow('read: text')
  expect(() => asksForTheRun(trap({ origin: { kind: 'bridge' } }, 'attachments'))).toThrow('read: attachments')
  expect(asksForTheRun({ origin: { kind: 'composer' }, attachments: [], text: 'show the run' })).toBe(true)
  // Nothing else is read: a matching typed prompt with traps on its context and wait still matches.
  const others = trap(trap({ origin: { kind: 'composer' }, attachments: [], text: 'show the run' }, 'context'), 'wait')
  expect(() => asksForTheRun(others)).not.toThrow()
  expect(asksForTheRun(others)).toBe(true)
})

// --- case 1 ------------------------------------------------------------------------------------

test('case 1: the hooks beneath get the submitted event once and the answer comes back', async ($, on) => {
  const { calls, seen } = setup($, on)
  let n = 0
  for (const [name, origin] of ORIGINS) {
    for (const text of ['show the run', 'what is in this file']) {
      n++
      const input = { text, wait: false, ...(origin === undefined ? {} : { origin }) }
      const r = await submit($, calls, seen, input)
      const label = `${name} / ${text}`
      expect([label, r.seen.length]).toEqual([label, 1])
      expect([label, r.seen[0]]).toEqual([label, input])
      expect([label, (r.result as any).text]).toEqual([label, `beneath answer ${n}`])
      // The control: a typed phrase opens the pane, and nothing else does.
      expect([label, r.opened]).toEqual([label, text === 'show the run' && origin !== undefined && typed(String(origin.kind)) ? 1 : 0])
    }
  }
  expect(ORIGINS.length).toBe(ORIGIN_ROWS)
  // Each origin row with a phrase and a non-phrase. This is not the length bound.
  expect(n).toBe(ORIGIN_ROWS * 2)
})

// --- case 2 ------------------------------------------------------------------------------------

// Spellings of one phrase that the hook treats as the phrase. Each is at most 38 code units.
function variants(p: string): [string, Record<string, unknown>][] {
  const mixed = [...p].map((c, i) => (i % 2 === 0 ? c.toUpperCase() : c)).join('')
  return [
    [p.toUpperCase(), {}],
    [mixed, {}],
    [p.replace(/ /g, '   '), {}],
    ['  ' + p + '  ', {}],
    ['\t' + p.replace(' ', '\t') + '\n', {}],
    [p.replace(' ', '\n') + '\r\n', {}],
    [p + '.', {}],
    [p + '?', {}],
    [p + '!', {}],
    [p + ' !', {}],
    [p + '? ', {}],
    [p + '! ', {}],
    [p + '.\n', {}],
    [p, { attachments: [] }],
    [p.padEnd(38), {}],
    [p.padStart(38), {}],
  ]
}

test('case 2: each phrase and each ASCII variant within the bound opens the pane', async ($, on) => {
  const { calls, seen } = setup($, on)
  let n = 0
  for (const p of SIX) {
    for (const [text, more] of [[p, {}] as [string, Record<string, unknown>], ...variants(p)]) {
      n++
      expect(text.length <= 38).toBe(true)
      const input = composer(text, more)
      const r = await submit($, calls, seen, input)
      expect([shown(text), r.opened, r.seen.length, r.seen[0]]).toEqual([shown(text), 1, 1, input])
    }
  }
  // Each phrase with the phrase itself and its 16 variants.
  expect(n).toBe(SIX.length * 17)
  // One variant through the bridge also opens the pane.
  const bridged = { text: 'RUN STATUS?', wait: false, origin: { kind: 'bridge' } }
  const b = await submit($, calls, seen, bridged)
  expect([b.opened, b.seen.length, b.seen[0]]).toEqual([1, 1, bridged])
})

// --- case 3 ------------------------------------------------------------------------------------

// Cyrillic a, e and o, which look like the Latin letters.
const CYRILLIC: Record<string, string> = { a: '\u0430', e: '\u0435', o: '\u043e' }
function nearMisses(p: string): [string, string, Record<string, unknown>][] {
  const at = [...p].findIndex(c => c in CYRILLIC)
  const lookalike = p.slice(0, at) + CYRILLIC[p[at]!]! + p.slice(at + 1)
  return [
    ['inside a longer prompt', `please ${p} now`, {}],
    ['negated', `don't ${p}`, {}],
    ['one Cyrillic letter', lookalike, {}],
    ['a leading U+00A0', '\u00a0' + p, {}],
    ['padded to 39', p.padEnd(39), {}],
    ['one attachment', p, { attachments: [{ type: 'image' }] }],
    ['two closing marks', p + '?!', {}],
    ['two full stops', p + '..', {}],
  ]
}

test('case 3: each near miss opens nothing', async ($, on) => {
  const { calls, seen } = setup($, on)
  let misses = 0
  for (const p of SIX) {
    for (const [name, text, more] of nearMisses(p)) {
      misses++
      const label = `${p}: ${name}`
      const input = composer(text, more)
      const miss = await submit($, calls, seen, input)
      expect([label, miss.opened]).toEqual([label, 0])
      expect([label, miss.seen.length, miss.seen[0]]).toEqual([label, 1, input])
      // The control: the unmodified phrase opens in the same iteration.
      const hit = await submit($, calls, seen, composer(p))
      expect([label, hit.opened]).toEqual([label, 1])
    }
    // The pair at the bound: 38 code units open, 39 do not.
    const at38 = await submit($, calls, seen, composer(p.padEnd(38)))
    const at39 = await submit($, calls, seen, composer(p.padEnd(39)))
    expect([p, at38.opened, at39.opened]).toEqual([p, 1, 0])
  }
  // Each phrase with its 8 near misses.
  expect(misses).toBe(SIX.length * 8)
})

// --- case 4 ------------------------------------------------------------------------------------

test('case 4: a matching prompt opens nothing for any other origin', async ($, on) => {
  const { calls, seen } = setup($, on)
  let others = 0
  for (const [name, origin] of ORIGINS) {
    const input = { text: 'show the run', wait: false, ...(origin === undefined ? {} : { origin }) }
    const r = await submit($, calls, seen, input)
    if (origin !== undefined && typed(String(origin.kind))) {
      // The control: the typed origins open with the same text.
      expect([name, r.opened]).toEqual([name, 1])
    } else {
      others++
      expect([name, r.opened]).toEqual([name, 0])
      expect([name, r.seen.length, r.seen[0]]).toEqual([name, 1, input])
    }
  }
  // Every origin row but composer and bridge.
  expect(others).toBe(ORIGIN_ROWS - 2)
})

// --- case 5 ------------------------------------------------------------------------------------

test('case 5: the open and the launch are constants, and repeated matches join one launch', async ($, on) => {
  const { w, calls, seen } = setup($, on, { reader: okReader({ delayMs: READER_DELAY_MS }) })
  // Every open, across every phrase and variant, is one constant.
  let n = 0
  for (const p of SIX) {
    for (const [text, more] of [[p, {}] as [string, Record<string, unknown>], ...variants(p)]) {
      n++
      await submit($, calls, seen, composer(text, more))
    }
  }
  const opens = opensOf(calls)
  expect(opens.length).toBe(n)
  for (const o of opens) expect(o.input).toEqual(PANE_OPEN)
  // The timers those prompts set fire together, and the launches join: one reader run in all.
  await w.clock.settle()
  expect(w.runs.length).toBe(1)
  await w.clock.advance(PAST_THE_READER_MS)
  expect(w.runs.length).toBe(1)
  // Later matches, and /crux-dashboard, start launches with the same argv and init.
  await submit($, calls, seen, composer('RUN STATUS'))
  await w.clock.settle()
  await w.clock.advance(PAST_THE_READER_MS)
  const answered = $.command.run({ command: 'crux-dashboard' } as any)
  await w.clock.advance(PAST_THE_READER_MS)
  await answered
  expect(w.runs.length).toBe(3)
  for (const r of w.runs) {
    expect(r.argv).toEqual(w.runs[0]!.argv)
    expect(r.init).toEqual(w.runs[0]!.init)
    // 'status' ends three of the phrases: no word of a matched prompt reaches the launch.
    expect(JSON.stringify(r)).not.toContain('status')
  }
  // The control: the open count equals the match count, so the single launch is a join, not a miss.
  expect(opensOf(calls).length).toBe(n + 2)
})

// --- case 6 ------------------------------------------------------------------------------------

test('case 6: a denied open lets the prompt through', async ($, on) => {
  const { calls, seen } = setup($, on, {}, { 'ui.open': () => ({ deny: 'no surface' }) })
  const input = composer('show the run')
  const r = await submit($, calls, seen, input)
  expect([r.opened, r.seen.length, r.seen[0]]).toEqual([1, 1, input])
  expect((r.result as any).text).toBe('beneath answer 1')
})

test('case 6: the open the world cannot place throws, and the prompt goes through', async ($, on) => {
  const { calls, seen } = setup($, on, { open: 'throw' })
  const input = composer('show the run')
  const r = await submit($, calls, seen, input)
  expect([r.opened, r.seen.length, r.seen[0]]).toEqual([1, 1, input])
  expect((r.result as any).text).toBe('beneath answer 1')
})

test('case 6: an open that never settles lets the prompt through', async ($, on) => {
  const { calls, seen } = setup($, on, {}, { 'ui.open': () => new Promise(() => {}) })
  const input = composer('show the run')
  const r = await submit($, calls, seen, input)
  expect([r.opened, r.seen.length, r.seen[0]]).toEqual([1, 1, input])
  expect((r.result as any).text).toBe('beneath answer 1')
})

test('case 6: a deferred open is requested, then the beneath hook is called, then the open settles', async ($, on) => {
  const order: string[] = []
  let release: () => void = () => {}
  const gate = new Promise<void>(resolve => { release = resolve })
  on('prompt.submit', (_$: any, e: any) => {
    order.push('beneath hook called')
    release()
    return { text: 'beneath answer' } as any
  })
  const calls: Call[] = []
  const rec = recording(on, calls, {
    'ui.open': async () => {
      order.push('open requested')
      await gate
      order.push('open settled')
      return { value: { isPlaced: true } }
    },
  })
  watchKitCalls(rec)
  const w = install(rec, {})
  const r = await $.prompt.submit(composer('show the run') as any)
  expect((r as any).text).toBe('beneath answer')
  await w.clock.settle()
  // The release is the control: the deferred promise does settle, after the beneath hook ran.
  expect(order).toEqual(['open requested', 'beneath hook called', 'open settled'])
})

// --- case 7 ------------------------------------------------------------------------------------

const MATCHING = '  SHOW   the RUN!'
const NON_MATCHING = `show the run ${CANARY}`

// Every place a value can go: the recorded inputs of every call the plugin makes, the state writes,
// the launch arguments and environment, what the band and the pane draw and the command's answer.
type Sinks = Record<string, string>
function sinksOf(calls: Call[], drawn: { band: string[]; pane: string[]; answer: string }): Sinks {
  const pick = (event: string) => calls.filter(c => c.event === event).map(c => c.input)
  return {
    'recorded inputs': JSON.stringify(calls.filter(c => c.event !== 'prompt.submit').map(c => c.input)),
    'ui.open': JSON.stringify(pick('ui.open')),
    'state.set': JSON.stringify(pick('state.set')),
    'process.run': JSON.stringify(pick('process.run')),
    band: drawn.band.join('\n'),
    pane: drawn.pane.join('\n'),
    answer: drawn.answer,
  }
}
// The search ignores case, and the needles hold the matching prompt in two forms. The hook folds a
// prompt to lower case and collapses its whitespace to match it. Ignoring case finds a leak of the
// text as typed or folded to lower case, and the needle 'show the run' finds a leak of the
// normalized match.
const findIn = (sinks: Sinks, needles: string[]) =>
  Object.entries(sinks).flatMap(([name, text]) =>
    needles.filter(n => text.toLowerCase().includes(n.toLowerCase())).map(n => `${name}: ${n}`))
const NEEDLES = [CANARY, MATCHING, '  SHOW   ', 'SHOW   the', 'show the run']

const bandTexts = async ($: any) =>
  texts(await (await $.ui.mount({ plugin: 'crux-mods', surface: 'terminal', component: 'AbovePrompt', props: BAND })).drawn())
const paneTexts = async ($: any) =>
  texts(await (await $.ui.mount({ plugin: 'crux-mods', surface: 'terminal', component: 'Pane', requestId: 'crux-dashboard', props: PANE })).drawn())

// Raises session start, submits the matching and the non-matching prompt, lets the 0 ms refresh
// finish, runs /crux-dashboard and draws the band and the pane.
async function canaryRun($: any, on: any, standIn: Record<string, any> = {}) {
  const { w, calls, seen } = setup($, on, { reader: okReader() }, standIn)
  await $.session.start({ cwd: '/proj' } as any)
  await w.clock.settle()
  const matching = composer(MATCHING, { context: [CANARY] })
  const nonMatching = composer(NON_MATCHING)
  const a = await submit($, calls, seen, matching)
  const b = await submit($, calls, seen, nonMatching)
  await w.clock.settle()
  const answer = String(((await $.command.run({ command: 'crux-dashboard' } as any)) as any).text)
  const band = await bandTexts($)
  const pane = await paneTexts($)
  return { w, calls, seen, a, b, matching, nonMatching, drawn: { band, pane, answer } }
}

test('case 7: a canary reaches no sink', async ($, on) => {
  const r = await canaryRun($, on)
  // The prompts reached the hook beneath whole and once each, so the canary exists to be found.
  expect([r.a.seen.length, r.b.seen.length]).toEqual([1, 1])
  expect(r.a.seen[0]).toEqual(r.matching)
  expect(r.b.seen[0]).toEqual(r.nonMatching)
  expect(JSON.stringify(r.b.seen[0])).toContain(CANARY)
  // The matching prompt opened the pane and the non-matching one did not, so the hook ran on both.
  expect([r.a.opened, r.b.opened]).toEqual([1, 0])
  const sinks = sinksOf(r.calls, r.drawn)
  // Each sink holds something, so an empty sink is not read as clean. An empty list in JSON, `[]`,
  // is 2 characters.
  for (const [name, text] of Object.entries(sinks)) expect([name, text.length > 2]).toEqual([name, true])
  expect(findIn(sinks, NEEDLES)).toEqual([])
})

// A plugin that copies the prompt text into an open and a process argument. It is self-contained,
// as an inline plugin's register is, and stands above the plugin under test.
const LEAKY = {
  name: 'leaky',
  tier: 'prepend' as const,
  register(on: any) {
    on('prompt.submit', async ($: any, e: any, next: any) => {
      await $.ui.open({ id: 'leak', title: e.text })
      await $.process.run(['echo', e.text])
      return next(e)
    })
  },
}

test('case 7 control: a leaky plugin\'s canary is caught', { plugins: [LEAKY] }, async ($, on) => {
  const { calls, seen } = setup($, on, { reader: okReader() })
  await $.prompt.submit(composer(NON_MATCHING) as any)
  const sinks = sinksOf(calls, { band: [], pane: [], answer: '' })
  expect(seen.length).toBe(1)
  // The canary reaches the open title and the process argument, and the same scan reports it.
  expect(findIn(sinks, [CANARY]).sort()).toEqual([`process.run: ${CANARY}`, `recorded inputs: ${CANARY}`, `ui.open: ${CANARY}`].sort())
  // The needle for the normalized match finds the same leak, so that needle can fire.
  const phrase = 'show the run'
  expect(findIn(sinks, [phrase]).sort()).toEqual([`process.run: ${phrase}`, `recorded inputs: ${phrase}`, `ui.open: ${phrase}`].sort())
})

test('case 7 control: reader values reach the drawn text and the answer', async ($, on) => {
  const r = await canaryRun($, on)
  expect(r.drawn.band[0]).toBe('PB-0149 RUN-001')
  expect(r.drawn.pane.join('\n')).toContain('PB-0149')
  expect(r.drawn.answer).toContain('PB-0149 RUN-001')
  expect(findIn(sinksOf(r.calls, r.drawn), ['PB-0149'])).toContain('band: PB-0149')
})

test('case 7 control: reader stdout reaches the state write', async ($, on) => {
  const r = await canaryRun($, on)
  const writes = r.calls.filter(c => c.event === 'state.set')
  expect(writes.length).toBeGreaterThan(0)
  expect(JSON.stringify(writes.map(c => c.input))).toContain('PB-0149')
})

test('case 7: every declared call is recorded', async ($, on) => {
  const r = await canaryRun($, on)
  const recorded = new Set(r.calls.map(c => c.event))
  const declared = capabilities.calls.map(c => c.slice(2))
  expect(declared.length).toBe(14)
  expect(declared.filter(c => !recorded.has(c))).toEqual([])
})

// --- register and its handler, called directly ---------------------------------------------------
// The kit offers no route to make the hook's own `$` calls throw at once, so these tests call
// `register` with a stand-in `on` and call the handlers it registers with a stand-in `$`.

type Registered = { event: string; hook: any }
function registered(options: unknown): Registered[] {
  const hooks: Registered[] = []
  const on = (event: string, ...rest: any[]) => {
    hooks.push({ event, hook: rest[rest.length - 1] })
  }
  register(on as any, options as any)
  return hooks
}

// A stand-in `$` with the two calls the hook makes on a match. It records each call. Each row says
// whether its open answers, throws at once or rejects, and whether its timer answers or throws at
// once. A proxy records every property read on `$`, at any depth. A property the stand-in lacks
// reads as undefined, so calling any other method throws inside the hook, after its read is recorded.
type Stub = { name: string; $: any; made: string[] }
function stub(name: string, open: () => unknown, after: () => unknown): Stub {
  const made: string[] = []
  const known = {
    ui: { open: (input: unknown) => { made.push(`call ui.open ${JSON.stringify(input)}`); return open() } },
    clock: { after: (ms: number, _fire: unknown) => { made.push(`call clock.after ${ms}`); return after() } },
  }
  const watch = (target: any, path: string): any =>
    new Proxy(target, {
      get(t, key) {
        const at = path === '' ? String(key) : `${path}.${String(key)}`
        made.push(`read ${at}`)
        const v = Reflect.get(t, key)
        return typeof v === 'object' && v !== null ? watch(v, at) : v
      },
    })
  return { name, $: watch(known, ''), made }
}
const placed = () => Promise.resolve({ value: { isPlaced: true } })
const aTimer = () => ({ cancel() {} })
const STUBS = () => [
  stub('an open and a timer that answer', placed, aTimer),
  stub('an open that throws at once', () => { throw new Error('the open threw') }, aTimer),
  stub('a timer that throws at once', placed, () => { throw new Error('the timer threw') }),
  stub('an open that rejects', () => Promise.reject(new Error('the open rejected')), aTimer),
]

// No error escapes the hook, whatever its own calls do, so no prompt text can reach the engine's
// report of a skipped hook. For a matched and an unmatched canary prompt from every origin, the
// handler calls `next` once with the event it received, unchanged, and resolves to `next`'s value.
test('case 7: no error escapes the hook when its own calls fail', async () => {
  const submit = registered({ read_prompts: true }).find(h => h.event === 'prompt.submit')
  expect(submit).toBeDefined()
  const OPEN = ['read ui', 'read ui.open', `call ui.open ${JSON.stringify(PANE_OPEN)}`]
  const TIMER = ['read clock', 'read clock.after', 'call clock.after 0']
  let rows = 0
  for (const s of STUBS()) {
    for (const [name, origin] of ORIGINS) {
      for (const [text, more] of [[MATCHING, { context: [CANARY] }], [NON_MATCHING, {}]] as [string, Record<string, unknown>][]) {
        rows++
        const e = { text, wait: false, ...(origin === undefined ? {} : { origin }), ...more }
        const before = JSON.parse(JSON.stringify(e))
        const passed: unknown[] = []
        const answer = { text: 'next answer' }
        const next = async (got: unknown) => {
          passed.push(got)
          return answer
        }
        const made = s.made.length
        let escaped = false
        let result: unknown
        try {
          result = await submit!.hook(s.$, e, next)
        } catch {
          // The label never carries the error's text, which could hold the prompt.
          escaped = true
        }
        const label = `${s.name} / ${name} / ${text === MATCHING ? 'matched' : 'unmatched'}`
        expect([label, escaped]).toEqual([label, false])
        expect([label, passed.length, passed[0] === e]).toEqual([label, 1, true])
        expect([label, passed[0]]).toEqual([label, before])
        expect([label, result === answer]).toEqual([label, true])
        // The control: on a match the hook reached the call this row fails. On no other prompt did it
        // read anything on `$`, so it called nothing. An open that throws at once leaves the timer
        // unset.
        const asks = text === MATCHING && origin !== undefined && typed(String(origin.kind))
        const expected = !asks ? [] : s.name === 'an open that throws at once' ? OPEN : [...OPEN, ...TIMER]
        expect([label, s.made.slice(made)]).toEqual([label, expected])
      }
    }
  }
  // Each stand-in with every origin row and a matched and an unmatched prompt.
  expect(rows).toBe(4 * ORIGIN_ROWS * 2)
})

// --- case 8 ------------------------------------------------------------------------------------

test('case 8: the manifest\'s prompt.submit entry names ADR-0156', () => {
  const entry = (capabilities.events as readonly any[]).find(e => e.event === 'prompt.submit')
  expect(entry).toBeDefined()
  expect([entry.decision, entry.behaviour, entry.gating, entry.has_catch]).toEqual(['ADR-0156', 'observe', true, false])
})

// --- case 9 ------------------------------------------------------------------------------------

async function readsNothing($: any, on: any) {
  const r = await canaryRun($, on)
  const sinks = sinksOf(r.calls, r.drawn)
  expect([r.a.opened, r.b.opened]).toEqual([0, 0])
  expect([r.a.seen.length, r.b.seen.length]).toEqual([1, 1])
  expect(r.a.seen[0]).toEqual(r.matching)
  expect(r.b.seen[0]).toEqual(r.nonMatching)
  expect(findIn(sinks, NEEDLES)).toEqual([])
  // The dashboard still draws and answers.
  expect(r.drawn.band[0]).toBe('PB-0149 RUN-001')
  expect(r.drawn.pane.join('\n')).toContain('PB-0149')
  expect(r.drawn.answer).toContain('PB-0149 RUN-001')
  // The command is the only open, so the prompt did not open the pane.
  expect(opensOf(r.calls).length).toBe(1)
}

test('case 9: with read_prompts off nothing is read and the dashboard still works', { options: { read_prompts: false } }, async ($, on) => {
  await readsNothing($, on)
})

test('case 9 control: the same body with read_prompts on opens the pane', { options: { read_prompts: true } }, async ($, on) => {
  const r = await canaryRun($, on)
  expect([r.a.opened, r.b.opened]).toEqual([1, 0])
  expect(opensOf(r.calls).length).toBe(2)
})

// The module's own check, called directly: `register` adds the prompt hook only when an options
// object arrives and its read_prompts is true or unset. An empty options object leaves it unset. A
// value of another type registers no prompt hook even where the kit would let it through. With no
// options object, undefined or null, no prompt hook registers. That is the privacy-safe outcome: an
// engine that passes no options gives the user no setting to turn reading off, so the hook reads
// nothing there. The other hooks register in every row, so each row shows the module ran.
test('case 9: register adds the prompt hook only for an options object whose read_prompts is true or unset', () => {
  const always = ['session.start', 'tool.call', 'ui.render', 'ui.render', 'command.run']
  const rows: [string, unknown, boolean][] = [
    ['true', { read_prompts: true }, true],
    ['an empty options object', {}, true],
    ['no options object', undefined, false],
    ['a null options object', null, false],
    ['false', { read_prompts: false }, false],
    ['the string "false"', { read_prompts: 'false' }, false],
    ['the number 0', { read_prompts: 0 }, false],
  ]
  for (const [name, options, reads] of rows) {
    const events = registered(options).map(h => h.event)
    expect([name, events]).toEqual([name, reads ? ['prompt.submit', ...always] : always])
  }
})

for (const bad of ['false', 0] as const) {
  test(`case 9: a non-boolean read_prompts stops the module from loading (${JSON.stringify(bad)})`, { options: { read_prompts: bad } }, async ($, on) => {
    const { w, calls, seen } = setup($, on, { reader: okReader() })
    let message = ''
    try {
      await $.prompt.submit(composer(NON_MATCHING) as any)
    } catch (err) {
      message = String((err as Error).message)
    }
    expect(message).toContain('must be a boolean')
    expect(message.includes(CANARY)).toBe(false)
    expect([w.opened.length, w.runs.length, opensOf(calls).length, seen.length]).toEqual([0, 0, 0, 0])
  })
}

// --- lifetime ----------------------------------------------------------------------------------
// The refresh a match starts runs from a timer of its own. It completes after the prompt's dispatch
// has finished, and after a hook above has answered without waiting for it.

async function refreshCompletes($: any, on: any, answered: string) {
  const { w, calls, seen } = setup($, on, { reader: okReader({ delayMs: READER_DELAY_MS }) })
  const sent = await submit($, calls, seen, composer('show the run'))
  expect([sent.opened, (sent.result as any).text]).toEqual([1, answered])
  // The refresh starts from a 0 ms timer of its own, never inside the prompt's dispatch: no reader
  // has started before the clock moves, and the one timer set is the 0 ms one.
  expect(w.runs.length).toBe(0)
  await w.clock.settle()
  expect(calls.filter(c => c.event === 'clock.after').map(c => c.input.ms)).toEqual([0])
  expect(w.runs.length).toBe(1)
  // /crux-dashboard while the launch is in flight joins it.
  const asked = $.command.run({ command: 'crux-dashboard' } as any)
  await w.clock.advance(PAST_THE_READER_MS)
  const text = String(((await asked) as any).text)
  const pane = (await paneTexts($)).join('\n')
  expect(w.runs.length).toBe(1)
  expect(text).toContain('status ok')
  expect(text).toContain('PB-0149 RUN-001')
  expect(pane).toContain('PB-0149')
  for (const code of ['reader-failed', ...LAUNCH_CODES]) {
    expect([code, text.includes(code), pane.includes(code)]).toEqual([code, false, false])
  }
}

test('lifetime: a refresh after a match completes', async ($, on) => {
  await refreshCompletes($, on, 'beneath answer 1')
})

// A hook above that answers at once, so the dispatch ends before the plugin's work does.
const ABANDON = {
  name: 'abandon',
  tier: 'prepend' as const,
  register(on: any) {
    on('prompt.submit', ($: any, e: any, next: any) => {
      void next(e)
      return { text: 'answered at once' }
    })
  },
}

test('lifetime: a refresh after an abandoned dispatch completes', { plugins: [ABANDON] }, async ($, on) => {
  await refreshCompletes($, on, 'answered at once')
})
