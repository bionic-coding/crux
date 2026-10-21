// A fake Host built from plain values. Its file and environment functions log every path and
// name they are asked for. Its lease read and write can succeed, fail or misreport, one call at
// a time. Its timers are a manual clock the test advances. Its start returns a process the test
// drives event by event, in any order. The UI writes are captured, not drawn.
import type { Host, KeptEnvelope, ReaderHandle, ReaderSink } from '../../lib/host.ts'

// --- the manual clock -----------------------------------------------------------

type Timer = { due: number; every: number | undefined; fn: () => void; live: boolean; seq: number }

export type Clock = {
  after: (ms: number, fn: () => void) => () => void
  every: (ms: number, fn: () => void) => () => void
  live: () => number
  advance: (ms: number) => void
}

export function makeClock(): Clock {
  let now = 0
  let seq = 0
  const timers: Timer[] = []
  const add = (ms: number, fn: () => void, every: number | undefined) => {
    seq += 1
    const t: Timer = { due: now + ms, every, fn, live: true, seq }
    timers.push(t)
    return () => {
      t.live = false
    }
  }
  const dueBy = (limit: number) => timers.filter(t => t.live && t.due <= limit).sort((a, b) => a.due - b.due || a.seq - b.seq)
  const fire = (t: Timer) => {
    if (!t.live) return
    if (t.every === undefined) t.live = false
    else t.due += t.every
    t.fn()
  }
  return {
    after: (ms, fn) => add(ms, fn, undefined),
    every: (ms, fn) => add(ms, fn, ms),
    live: () => timers.filter(t => t.live).length,
    advance: ms => {
      const end = now + ms
      for (;;) {
        const next = dueBy(end)[0]
        if (next === undefined) break
        if (next.due > now) now = next.due
        fire(next)
      }
      now = end
    },
  }
}

// --- the memory value -----------------------------------------------------------

export type Memory = { running: boolean; current: KeptEnvelope | null; writes: (KeptEnvelope | null)[] }

export const makeMemory = (): Memory => ({ running: false, current: null, writes: [] })

// --- faults on the lease ----------------------------------------------------------

export type ReadFault = 'ok' | 'throw' | 'held' | 'free' | 'unknown'
export type WriteFault = 'ok' | 'throw' | 'throw-after-change' | 'lie'

export type LeaseFaults = { reads: ReadFault[]; writes: WriteFault[]; readDefault: ReadFault; writeDefault: WriteFault }

// --- the process ----------------------------------------------------------------

export type Proc = {
  argv: string[]
  cwd: string
  sink: ReaderSink
  terms: number
  hards: number
  exited: boolean
  closed: boolean
  spawn: () => void
  exit: () => void
  out: (data: number[] | string) => void
  err: (data: number[] | string) => void
  fail: () => void
  close: (code?: number) => void
  finish: (stdout: string, code?: number) => void
}

const bytesOf = (data: number[] | string): number[] =>
  typeof data === 'string' ? Array.from(data, c => c.charCodeAt(0)) : data

// --- the world the plan reads -----------------------------------------------------

export type World = {
  directory?: string | undefined
  cloneDir?: string | undefined
  env?: Record<string, string>
  files?: string[]
  dirs?: string[]
  reals?: Record<string, string>
  texts?: Record<string, string>
}

export const CLONE = '/clone'
export const PROJECT = '/proj'
export const HOME = '/home/u'
export const UV = '/opt/homebrew/bin/uv'
export const SCRIPT = `${CLONE}/crux/scripts/visualize-run-progress.py`
export const PLUGIN_JSON = `${CLONE}/crux/plugin.json`
export const MODS_JSON = `${CLONE}/crux-mods/.claude-plugin/plugin.json`

// A machine on which every plan step passes.
export function okWorld(): World {
  return {
    directory: PROJECT,
    cloneDir: CLONE,
    env: { HOME },
    files: [SCRIPT, UV, PLUGIN_JSON, MODS_JSON],
    dirs: [PROJECT, `${CLONE}/crux`, HOME, '/usr/bin', '/bin'],
    reals: {},
    texts: { [PLUGIN_JSON]: '{"version":"3.31.1"}', [MODS_JSON]: '{"version":"3.31.1"}' },
  }
}

export type Fake = {
  host: Host
  world: World
  clock: Clock
  mem: Memory
  log: string[]
  procs: Proc[]
  toasts: string[]
  opens: { count: number; result: boolean; open: boolean; closes: number }
  startMode: { value: 'handle' | 'untracked' | 'undefined' }
  keptThrows: { value: boolean }
  lease: LeaseFaults
  started: () => number
  asked: (prefix: string) => string[]
}

export type Shared = { clock?: Clock; mem?: Memory }

export function makeFake(world: World = okWorld(), shared: Shared = {}): Fake {
  const clock = shared.clock ?? makeClock()
  const mem = shared.mem ?? makeMemory()
  const log: string[] = []
  const procs: Proc[] = []
  const toasts: string[] = []
  const opens = { count: 0, result: true, open: false, closes: 0 }
  const startMode: { value: 'handle' | 'untracked' | 'undefined' } = { value: 'handle' }
  const keptThrows = { value: false }
  const lease: LeaseFaults = { reads: [], writes: [], readDefault: 'ok', writeDefault: 'ok' }
  const files = world.files ?? []
  const dirs = world.dirs ?? []
  const reals = world.reals ?? {}
  const texts = world.texts ?? {}
  const env = world.env ?? {}
  const exists = (p: string) => files.includes(p) || dirs.includes(p)

  const host: Host = {
    directory: world.directory,
    cloneDir: world.cloneDir,
    env: name => {
      log.push('env:' + name)
      return env[name]
    },
    isFile: p => {
      log.push('isFile:' + p)
      return files.includes(p)
    },
    isDir: p => {
      log.push('isDir:' + p)
      return dirs.includes(p)
    },
    real: p => {
      log.push('real:' + p)
      return reals[p] ?? (exists(p) ? p : undefined)
    },
    read: p => {
      log.push('read:' + p)
      return texts[p]
    },
    start: (argv, cwd, sink) => {
      log.push('start')
      if (startMode.value === 'undefined') return undefined
      if (startMode.value === 'untracked') return 'untracked'
      const proc: Proc = {
        argv,
        cwd,
        sink,
        terms: 0,
        hards: 0,
        exited: false,
        closed: false,
        spawn: () => sink.spawned(),
        exit: () => {
          proc.exited = true
          sink.exited()
        },
        out: data => sink.out(bytesOf(data)),
        err: data => sink.err(bytesOf(data)),
        fail: () => sink.failed(),
        close: code => {
          proc.closed = true
          sink.closed(code)
        },
        finish: (stdout, code = 0) => {
          proc.spawn()
          proc.out(stdout)
          proc.exit()
          proc.close(code)
        },
      }
      procs.push(proc)
      const handle: ReaderHandle = {
        term: () => {
          proc.terms += 1
        },
        hard: () => {
          proc.hards += 1
        },
      }
      return handle
    },
    after: (ms, fn) => clock.after(ms, fn),
    every: (ms, fn) => clock.every(ms, fn),
    leaseRead: () => {
      const fault: ReadFault = lease.reads.shift() ?? lease.readDefault
      const value = fault === 'ok' ? (mem.running ? 'held' : 'free') : fault === 'throw' ? 'unknown' : fault
      log.push('leaseRead:' + value)
      return value
    },
    leaseWrite: b => {
      const fault: WriteFault = lease.writes.shift() ?? lease.writeDefault
      log.push('leaseWrite:' + b + ':' + fault)
      if (fault === 'throw') return false
      if (fault === 'throw-after-change') {
        mem.running = b === true
        return false
      }
      if (fault === 'lie') return true
      mem.running = b === true
      return true
    },
    writeKept: v => {
      log.push('writeKept')
      if (keptThrows.value) throw new Error('writeKept')
      mem.writes.push(v)
      mem.current = v
    },
    openPanel: () => {
      opens.count += 1
      if (opens.result === true) opens.open = true
      return opens.result
    },
    panelOpen: () => opens.open,
    closePanel: () => {
      opens.closes += 1
      opens.open = false
      return true
    },
    toast: code => {
      toasts.push(code)
    },
  }

  return {
    host,
    world,
    clock,
    mem,
    log,
    procs,
    toasts,
    opens,
    startMode,
    keptThrows,
    lease,
    started: () => log.filter(e => e === 'start').length,
    asked: prefix => log.filter(e => e.startsWith(prefix)),
  }
}
