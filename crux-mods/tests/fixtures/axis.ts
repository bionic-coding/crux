// Reader documents for the time axis, and a clock guard wider than no-clock.ts's withoutClock. A new
// file, so no existing fixture changes. Every time is whole epoch seconds from reader-output.ts.
import { CONVERGED, HOSTILE_TITLE, NOW_S, READER_OK, RUN, lastRunAged } from './reader-output.ts'

// --- runs whose status is not in progress, listed in `runs` ------------------------------------

// A completed run listed in `runs`, as a target-mode document gives it: its second prompt carries
// the long title, so its row is cut at most widths.
const COMPLETED = (() => {
  const r = lastRunAged(3600, [])
  return { ...r, prompts: r.prompts.map(p => (p.n === 2 ? { ...p, title: HOSTILE_TITLE } : p)) }
})()
export const targetCompleted = (now_s: number | null) => ({
  ...READER_OK, now_s, runs: [COMPLETED], last_completed: null as unknown, last_completed_status: 'not-requested',
})

// An abandoned run listed in `runs`: abandonment sets its completion time and clears its current
// prompt, and leaves the prompt that was running as running.
const ABANDONED = (() => {
  const r = lastRunAged(3600, [])
  const S = r.started_s
  return {
    ...r,
    status: 'abandoned',
    progress: { total: 4, terminal: 1, done: 1, pct: 25, counts: { done: 1, skipped: 0, blocked: 0, running: 1, pending: 2 } },
    prompts: [
      { n: 1, state: 'done', module_tag: null, title: 'Plan the last run', started_s: S, completed_s: S + 1500 },
      { n: 2, state: 'running', module_tag: null, title: 'Build the last run', started_s: S + 1500, completed_s: null },
      { n: 3, state: 'pending', module_tag: null, title: 'Third', started_s: null, completed_s: null },
      { n: 4, state: 'pending', module_tag: null, title: 'Fourth', started_s: null, completed_s: null },
    ],
  }
})()
export const targetAbandoned = (now_s: number | null) => ({
  ...READER_OK, now_s, runs: [ABANDONED], last_completed: null as unknown, last_completed_status: 'not-requested',
})

// --- live runs ------------------------------------------------------------------------------------

// The live run with its running prompt started in the very second of now_s.
export const READER_ZERO_AT_END = {
  ...READER_OK,
  runs: [{ ...RUN, prompts: RUN.prompts.map(p => (p.n === 3 ? { ...p, started_s: NOW_S } : p)) }],
}

// A live run whose prompts carry the numbers given, each done in its own minute.
export function runOf(ns: number[]) {
  return {
    ...RUN,
    current_prompt: null,
    progress: { total: ns.length, terminal: ns.length, done: ns.length, pct: 100, counts: { done: ns.length, skipped: 0, blocked: 0, running: 0, pending: 0 } },
    prompts: ns.map((n, i) => ({ n, state: 'done', module_tag: null, title: `Prompt ${n}`, started_s: RUN.started_s + i * 60, completed_s: RUN.started_s + i * 60 + 60 })),
    councils: [] as unknown[],
    gates: [] as unknown[],
  }
}
export const range = (k: number) => Array.from({ length: k }, (_, i) => i + 1)
export const readerOf = (ns: number[], runs = 1) => ({
  ...READER_OK,
  runs: Array.from({ length: runs }, (_, i) => ({ ...runOf(ns), run_id: `RUN-00${i + 1}`, run_path: `promptbooks/runs/PB-0149-x/run-RUN-00${i + 1}.yaml`, modified_s: RUN.modified_s - i })),
})

// --- the pane's budget ----------------------------------------------------------------------------

// An ASCII title of exactly len characters that names its prompt.
export const titleOf = (n: number, len: number) => `Implement and test prompt ${n} of the time axis `.padEnd(len, 'abcdefghij').slice(0, len)

// An in-progress run of k prompts with titles of len characters, each prompt done in its own minute
// from the run's start and the last one running: no council, no gate.
export function seatRun(i: number, k: number, len: number | ((n: number) => number)) {
  const A = RUN.started_s
  const lenOf = typeof len === 'number' ? () => len : len
  const prompts = Array.from({ length: k }, (_, j) => {
    const n = j + 1
    const last = n === k
    return { n, state: last ? 'running' : 'done', module_tag: null, title: titleOf(n, lenOf(n)), started_s: A + j * 60, completed_s: last ? null : A + j * 60 + 60 }
  })
  return {
    ...RUN, run_id: `RUN-00${i + 1}`, run_path: `promptbooks/runs/PB-0149-x/run-RUN-00${i + 1}.yaml`, modified_s: RUN.modified_s - i,
    current_prompt: k, status: 'in_progress',
    progress: { total: k, terminal: k - 1, done: k - 1, pct: Math.floor(((k - 1) * 100) / k), counts: { done: k - 1, skipped: 0, blocked: 0, running: 1, pending: 0 } },
    prompts, councils: [] as unknown[], gates: [] as unknown[], councils_skipped: 0,
  }
}
// One shown run per entry of ks, each with titles of len characters.
export const seatDoc = (ks: number[], len: number | ((run: number, n: number) => number)) => ({
  ...READER_OK, now_s: NOW_S,
  runs: ks.map((k, i) => seatRun(i, k, typeof len === 'number' ? len : (n: number) => len(i, n))),
})
// Five shown in-progress runs of 100 prompts with titles of 100 characters: the shape whose lanes
// would pass the kit's text limit if every run drew them.
export const SEAT_SHAPE = seatDoc([100, 100, 100, 100, 100], 100)

// A last run whose drawing is mostly nodes and little text: 100 prompts, each done in ten seconds
// well inside the run's axis, a summary of two-cell characters that wraps to the summary's row cap
// at narrow widths, and `roles` council roles, one row each in the council grid.
export function nodeHeavyDoc(roles: number) {
  const S = NOW_S - 3600
  const prompts = Array.from({ length: 100 }, (_, j) => ({ n: j + 1, state: 'done', module_tag: null, title: `T${j + 1}`, started_s: S + 200 + 10 * j, completed_s: S + 210 + 10 * j }))
  const councils = Array.from({ length: Math.ceil(roles / 12) }, (_, c) => ({
    ...CONVERGED,
    record_path: `promptbooks/runs/PB-0150-show-the-last-run/council/RUN-002-p${c + 1}-r1-20261010T000000000000Z.json`,
    prompt: c + 1, round: 1,
    seats: Array.from({ length: Math.min(12, roles - 12 * c) }, (_, s) => ({ role: `r${String(12 * c + s).padStart(4, '0')}`, decision: 'APPROVE', errored: false, findings: { blocking: 0, nit: 0 } })),
  }))
  const summary = Array.from({ length: 32 }, () => '\u{4E2D}'.repeat(1000))
  const last = {
    ...lastRunAged(3600, summary), started_s: S, completed_s: S + 1400, modified_s: S + 1400,
    progress: { total: 100, terminal: 100, done: 100, pct: 100, counts: { done: 100, skipped: 0, blocked: 0, running: 0, pending: 0 } },
    prompts, councils, councils_skipped: 0,
  }
  return { ...READER_OK, runs: [], last_completed: last as unknown, last_completed_status: 'latest' }
}

// --- a wider clock guard ----------------------------------------------------------------------------

// A wider clock guard than no-clock.ts's withoutClock, which stays as it is. Beside Date.now(),
// new Date() and performance.now(), it throws on Date() called as a function, on new Date with no
// argument, on Temporal.Now, on process.hrtime and process.uptime, and on an Intl date format of no
// date, which formats the current time. It cannot see a Date captured before it runs: the source
// scans cover that.
export function withoutAnyClock(run: () => void) {
  const g = globalThis as any
  const had = { Date: g.Date, performance: g.performance, Temporal: g.Temporal, Intl: g.Intl, process: g.process, hasProcess: Object.prototype.hasOwnProperty.call(g, 'process') }
  const RealDate = had.Date
  class NoClock extends RealDate {
    constructor(...args: any[]) {
      if (args.length === 0) throw new Error('clock read: new Date()')
      super(...(args as [number]))
    }
    static now(): number {
      throw new Error('clock read: Date.now()')
    }
  }
  const thrower = (what: string) => () => { throw new Error(`clock read: ${what}`) }
  const realIntl = had.Intl
  const RealDTF = realIntl.DateTimeFormat
  function NoClockDTF(...a: any[]) {
    const f = new RealDTF(...a)
    return new Proxy(f, {
      get(t, k) {
        if (k === 'format' || k === 'formatToParts') return (d?: unknown) => {
          if (d === undefined) throw new Error(`clock read: Intl ${String(k)}() of no date`)
          return (t as any)[k](d)
        }
        const v = Reflect.get(t, k)
        return typeof v === 'function' ? v.bind(t) : v
      },
    })
  }
  g.Date = NoClock
  g.performance = { now: thrower('performance.now()') }
  // The runtime freezes Temporal and Intl, so the guard puts copies in their place.
  const copy = (o: any) => {
    const out: any = {}
    for (const k of Object.getOwnPropertyNames(o ?? {})) out[k] = o[k]
    return out
  }
  const temporal = copy(had.Temporal)
  Object.defineProperty(temporal, 'Now', { get: thrower('Temporal.Now') })
  const intl = copy(realIntl)
  intl.DateTimeFormat = NoClockDTF
  g.Temporal = temporal
  g.Intl = intl
  g.process = { hrtime: Object.assign(thrower('process.hrtime()'), { bigint: thrower('process.hrtime.bigint()') }), uptime: thrower('process.uptime()') }
  try {
    run()
  } finally {
    g.Date = RealDate
    g.performance = had.performance
    g.Temporal = had.Temporal
    g.Intl = realIntl
    if (had.hasProcess) g.process = had.process
    else delete g.process
  }
}
