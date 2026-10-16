import { test, expect } from 'claude-code/testing'
import { capabilities } from '../capabilities.ts'
import { TIMEOUT_MS, createScheduler } from '../lib/refresh.ts'
import type { Reason } from '../lib/refresh.ts'
import { READ_CAP } from '../lib/reader.ts'
import { KEPT_CODES } from '../lib/status.ts'
import { READER_ERROR_CODES, kept, parseReader } from '../../crux-mods/hooks/lib/view.ts'
import { HOME, makeFake, okWorld } from './fixtures/fake.ts'
import type { Fake, Proc, Shared, World } from './fixtures/fake.ts'
import { jsonText } from './fixtures/plain.ts'
import { NO_RUN_DOC, OTHER_FORMAT_DOC, VIEW_STDOUT, readerErrorDoc } from './fixtures/sched-docs.ts'

const TIME_LIMIT = jsonText(readerErrorDoc('time-limit'))
const blank = (n: number) => Array.from({ length: n }, () => 0x20)

// refresh.ts does not import the manifest, so this pin keeps its timeout equal to the launch block's.
test('the reader timeout equals the manifest launch timeout', () => {
  expect(TIMEOUT_MS).toBe(capabilities.launch.timeout_ms)
})

function mk(world: World = okWorld(), shared: Shared = {}) {
  const fake = makeFake(world, shared)
  const sched = createScheduler(fake.host)
  return { fake, sched }
}

// A scheduler started at time 0 on a free lease, advanced to the moment its first reader starts.
function running() {
  const r = mk()
  r.sched.start()
  r.fake.clock.advance(4100)
  return r
}

const proc = (fake: Fake, i = 0): Proc => {
  const p = fake.procs[i]
  if (p === undefined) throw new Error('no process ' + i)
  return p
}

// --- start and the hold -----------------------------------------------------------

test('the first reader starts when the hold has run out, not before', () => {
  const { fake, sched } = mk()
  sched.start()
  fake.clock.advance(4099)
  expect(fake.started()).toBe(0)
  fake.clock.advance(1)
  expect(fake.started()).toBe(1)
  expect(fake.mem.running).toBe(true)
})

test('start polls the lease every 250 ms, the first poll at 0 ms', () => {
  const { fake, sched } = mk()
  fake.mem.running = true
  sched.start()
  expect(fake.asked('leaseRead:').length).toBe(0)
  fake.clock.advance(0)
  expect(fake.asked('leaseRead:').length).toBe(1)
  fake.clock.advance(249)
  expect(fake.asked('leaseRead:').length).toBe(1)
  fake.clock.advance(1)
  expect(fake.asked('leaseRead:').length).toBe(2)
  fake.clock.advance(1000)
  expect(fake.asked('leaseRead:').length).toBe(6)
})

test('a held lease keeps the scheduler in the hold until it reads free and 2100 ms pass', () => {
  const { fake, sched } = mk()
  fake.mem.running = true
  sched.start()
  fake.clock.advance(3000)
  fake.mem.running = false
  // The next poll is at 3250 and reads free; the free cool-down ends at 5350.
  fake.clock.advance(2349)
  expect(fake.started()).toBe(0)
  fake.clock.advance(1)
  expect(fake.started()).toBe(1)
})

test('an unreadable lease never counts as free', () => {
  const { fake, sched } = mk()
  fake.lease.readDefault = 'unknown'
  sched.start()
  fake.clock.advance(60000)
  expect(fake.started()).toBe(0)
  fake.lease.readDefault = 'ok'
  fake.clock.advance(250 + 2100)
  expect(fake.started()).toBe(1)
})

test('the first drain is explicit: no request is needed', () => {
  const { fake, sched } = mk()
  sched.start()
  fake.clock.advance(4100)
  expect(fake.started()).toBe(1)
})

test('requests before start and after stop do nothing', () => {
  const before = mk()
  before.sched.request('command')
  before.sched.request('panel')
  before.fake.clock.advance(60000)
  expect(before.fake.started()).toBe(0)
  expect(before.fake.clock.live()).toBe(0)

  const after = running()
  after.sched.stop()
  after.fake.clock.advance(1)
  const live = after.fake.clock.live()
  after.sched.request('command')
  after.sched.request('tick')
  expect(after.fake.clock.live()).toBe(live)
})

test('start acts only once, and not after stop', () => {
  const { fake, sched } = mk()
  sched.start()
  const live = fake.clock.live()
  sched.start()
  expect(fake.clock.live()).toBe(live)
  const stopped = mk()
  stopped.sched.stop()
  stopped.sched.start()
  stopped.fake.clock.advance(60000)
  expect(stopped.fake.clock.live()).toBe(0)
  expect(stopped.fake.started()).toBe(0)
})

test('a scheduler that was never started holds no timer', () => {
  const { fake, sched } = mk()
  const reasons: Reason[] = ['tick', 'panel', 'command', 'event']
  for (const r of reasons) sched.request(r)
  fake.clock.advance(60000)
  expect(fake.clock.live()).toBe(0)
  expect(fake.log).toEqual([])
})

// --- one reader at a time ---------------------------------------------------------

test('requests during a run coalesce into one run after the cool-down', () => {
  const { fake, sched } = running()
  const reasons: Reason[] = ['panel', 'command', 'event', 'tick', 'command', 'panel']
  for (const r of reasons) sched.request(r)
  fake.clock.advance(100)
  expect(fake.procs.length).toBe(1)
  proc(fake).finish(VIEW_STDOUT)
  // The run closed at 4200; the cool-down ends at 6300.
  fake.clock.advance(2099)
  expect(fake.procs.length).toBe(1)
  fake.clock.advance(1)
  expect(fake.procs.length).toBe(2)
  fake.clock.advance(100)
  proc(fake, 1).finish(VIEW_STDOUT)
  fake.clock.advance(3000)
  // The flags were cleared by the second run's start: no third run before the next tick.
  expect(fake.procs.length).toBe(2)
})

test('the interval asks for a run every 10 s', () => {
  const { fake } = running()
  proc(fake).finish(VIEW_STDOUT)
  fake.clock.advance(5899)
  expect(fake.procs.length).toBe(1)
  fake.clock.advance(1)
  expect(fake.procs.length).toBe(2)
  proc(fake, 1).finish(VIEW_STDOUT)
  fake.clock.advance(9999)
  expect(fake.procs.length).toBe(2)
  fake.clock.advance(1)
  expect(fake.procs.length).toBe(3)
})

test('the floor is measured from close, not from exit', () => {
  const { fake, sched } = running()
  const p = proc(fake)
  fake.clock.advance(1000)
  p.spawn()
  p.out(VIEW_STDOUT)
  p.exit()
  fake.clock.advance(2900)
  // The process exited at 5100 and closes at 8000.
  p.close(0)
  sched.request('command')
  // The interval fired at 10000 during the cool-down, which ends at 10100.
  fake.clock.advance(2099)
  expect(fake.procs.length).toBe(1)
  fake.clock.advance(1)
  expect(fake.procs.length).toBe(2)
})

test('a request in a cool-down starts nothing until the cool-down ends', () => {
  const { fake, sched } = running()
  proc(fake).finish(VIEW_STDOUT)
  fake.clock.advance(1)
  sched.request('command')
  fake.clock.advance(2098)
  expect(fake.procs.length).toBe(1)
  fake.clock.advance(1)
  expect(fake.procs.length).toBe(2)
})

test('a request in idle starts a run on a 0 ms timer', () => {
  const { fake, sched } = running()
  proc(fake).finish(VIEW_STDOUT)
  fake.clock.advance(2100)
  expect(fake.procs.length).toBe(1)
  sched.request('panel')
  expect(fake.procs.length).toBe(1)
  fake.clock.advance(0)
  expect(fake.procs.length).toBe(2)
})

test('the event reason starts a run from a handler that takes no parameter', () => {
  const { fake, sched } = running()
  proc(fake).finish(VIEW_STDOUT)
  fake.clock.advance(2100)
  const onEvent = () => {
    sched.request('event')
  }
  onEvent()
  fake.clock.advance(0)
  expect(fake.procs.length).toBe(2)
})

test('a request reads no host value', () => {
  const { fake, sched } = running()
  const before = fake.log.length
  const reasons: Reason[] = ['tick', 'panel', 'command', 'event']
  for (const r of reasons) sched.request(r)
  expect(fake.log.length).toBe(before)
})

test('at most one process is alive across many requests', () => {
  const { fake, sched } = mk()
  sched.start()
  let max = 0
  for (let i = 0; i < 400; i++) {
    fake.clock.advance(100)
    sched.request('panel')
    sched.request('tick')
    max = Math.max(max, fake.alive())
    const p = fake.procs[fake.procs.length - 1]
    if (p !== undefined && !p.closed && i % 7 === 0) p.finish(VIEW_STDOUT)
  }
  expect(fake.procs.length).toBeGreaterThan(3)
  expect(max).toBe(1)
})

// --- killing ----------------------------------------------------------------------

test('a reader that outlives its timeout is terminated, then killed after the grace', () => {
  const { fake } = running()
  const p = proc(fake)
  p.spawn()
  fake.clock.advance(9999)
  expect(p.terms).toBe(0)
  fake.clock.advance(1)
  expect(p.terms).toBe(1)
  expect(p.hards).toBe(0)
  fake.clock.advance(1999)
  expect(p.hards).toBe(0)
  fake.clock.advance(1)
  expect(p.hards).toBe(1)
  // A signal kill closes with no exit code.
  p.exit()
  p.close(undefined)
  expect(fake.mem.current).toEqual({ ok: false, code: 'reader-timeout' })
  expect(fake.mem.running).toBe(false)
  expect(p.signalsAfterExit).toBe(0)
})

test('a request while the reader is stopping starts nothing until its close', () => {
  const { fake, sched } = running()
  const p = proc(fake)
  p.spawn()
  fake.clock.advance(10000)
  expect(p.terms).toBe(1)
  sched.request('command')
  fake.clock.advance(30000)
  expect(fake.procs.length).toBe(1)
  p.exit()
  p.close(undefined)
  fake.clock.advance(2099)
  expect(fake.procs.length).toBe(1)
  fake.clock.advance(1)
  expect(fake.procs.length).toBe(2)
})

test('a reader that exits before the grace timer is not killed', () => {
  const { fake } = running()
  const p = proc(fake)
  p.spawn()
  fake.clock.advance(10000)
  expect(p.terms).toBe(1)
  fake.clock.advance(500)
  p.exit()
  fake.clock.advance(5000)
  expect(p.hards).toBe(0)
  expect(p.signalsAfterExit).toBe(0)
  expect(fake.mem.writes.length).toBe(0)
  p.close(undefined)
  expect(fake.mem.current).toEqual({ ok: false, code: 'reader-timeout' })
})

test('a timeout after exit sends no signal and the result is the timeout', () => {
  const { fake } = running()
  const p = proc(fake)
  p.spawn()
  p.out(VIEW_STDOUT)
  p.exit()
  fake.clock.advance(10000)
  expect(p.terms).toBe(0)
  expect(p.hards).toBe(0)
  expect(fake.mem.writes.length).toBe(0)
  p.close(0)
  expect(fake.mem.current).toEqual({ ok: false, code: 'reader-timeout' })
})

test('a close delayed past the grace timer blocks any new start and sends no signal after exit', () => {
  const { fake, sched } = running()
  const p = proc(fake)
  p.spawn()
  fake.clock.advance(10000)
  fake.clock.advance(2000)
  expect(p.hards).toBe(1)
  p.exit()
  for (let i = 0; i < 10; i++) {
    sched.request('command')
    fake.clock.advance(10000)
  }
  expect(fake.procs.length).toBe(1)
  expect(p.signalsAfterExit).toBe(0)
  expect(p.terms).toBe(1)
  expect(p.hards).toBe(1)
  expect(fake.mem.running).toBe(true)
  p.close(undefined)
  expect(fake.mem.running).toBe(false)
  fake.clock.advance(2100)
  expect(fake.procs.length).toBe(2)
})

test('a refused byte terminates the reader at once and settles as reader-output-invalid', () => {
  const { fake, sched } = running()
  const p = proc(fake)
  p.spawn()
  p.out([0x7b, 0xe9])
  expect(p.terms).toBe(1)
  sched.request('command')
  fake.clock.advance(1999)
  expect(p.hards).toBe(0)
  fake.clock.advance(1)
  expect(p.hards).toBe(1)
  p.exit()
  p.close(undefined)
  expect(fake.mem.current).toEqual({ ok: false, code: 'reader-output-invalid' })
})

test('output past the cap terminates the reader', () => {
  const { fake } = running()
  const p = proc(fake)
  p.spawn()
  for (let i = 0; i < 17; i++) p.out(blank(65536))
  expect(READ_CAP).toBe(1048576)
  expect(p.terms).toBe(1)
  p.exit()
  p.close(undefined)
  expect(fake.mem.current).toEqual({ ok: false, code: 'reader-output-invalid' })
})

test('a reader that ends on its own is not terminated', () => {
  const { fake } = running()
  const p = proc(fake)
  p.finish(VIEW_STDOUT)
  fake.clock.advance(30000)
  expect(p.terms).toBe(0)
  expect(p.hards).toBe(0)
})

test('a timeout is cancelled when the run ends', () => {
  const { fake } = running()
  proc(fake).finish(VIEW_STDOUT)
  const delays = fake.clock.delays()
  // Only the cool-down and the interval are pending: no 10 s timeout, no grace.
  expect(delays.includes(2100)).toBe(true)
  expect(delays.filter(d => d > 6000 && d < 10000).length).toBe(0)
  expect(fake.clock.live()).toBe(2)
})

// --- settling and back-off --------------------------------------------------------

const settled = (stdout: string, exit = 0) => {
  const r = running()
  proc(r.fake).finish(stdout, exit)
  return r
}

test('a view is kept as the reader stdout', () => {
  const { fake } = settled(VIEW_STDOUT)
  expect(parseReader(VIEW_STDOUT).ok).toBe(true)
  expect(fake.mem.current).toEqual({ ok: true, stdout: VIEW_STDOUT })
  expect(fake.mem.writes.length).toBe(1)
  expect(kept(fake.mem.current, KEPT_CODES)).toEqual(parseReader(VIEW_STDOUT))
})

test('reader error documents read back through the kept set', () => {
  for (const code of READER_ERROR_CODES) {
    const { fake } = settled(jsonText(readerErrorDoc(code)), 1)
    expect(fake.mem.current).toEqual({ ok: false, code: 'reader-failed:' + code })
    expect(kept(fake.mem.current, KEPT_CODES)).toEqual({ ok: false, code: 'reader-failed:' + code })
  }
})

test('a format mismatch and no-active-run read back through the kept set', () => {
  const mismatch = settled(jsonText(OTHER_FORMAT_DOC))
  expect(mismatch.fake.mem.current).toEqual({ ok: false, code: 'reader-format-mismatch' })
  expect(kept(mismatch.fake.mem.current, KEPT_CODES)).toEqual({ ok: false, code: 'reader-format-mismatch' })
  const none = settled(jsonText(NO_RUN_DOC))
  expect(none.fake.mem.current).toEqual({ ok: false, code: 'no-active-run' })
  expect(kept(none.fake.mem.current, KEPT_CODES)).toEqual({ ok: false, code: 'no-active-run' })
})

test('output that is not a document is reader-output-invalid', () => {
  const { fake } = settled('{"format":')
  expect(fake.mem.current).toEqual({ ok: false, code: 'reader-output-invalid' })
})

test('the core classifies the finished process before the document is read', () => {
  expect(settled('', 152).fake.mem.current).toEqual({ ok: false, code: 'reader-cpu-limit' })
  expect(settled('', 1).fake.mem.current).toEqual({ ok: false, code: 'reader-failed' })
  expect(settled('plain text', 0).fake.mem.current).toEqual({ ok: false, code: 'reader-failed' })
})

test('a run releases the lease after it writes the kept value', () => {
  const { fake } = running()
  expect(fake.mem.running).toBe(true)
  proc(fake).finish(VIEW_STDOUT)
  expect(fake.mem.running).toBe(false)
  const order = fake.log.filter(e => e === 'writeKept' || e === 'leaseWrite:false:ok')
  expect(order).toEqual(['writeKept', 'leaseWrite:false:ok'])
})

test('a time-limit result backs off: a tick starts nothing, an explicit request runs', () => {
  const { fake, sched } = settled(TIME_LIMIT, 1)
  expect(fake.mem.current).toEqual({ ok: false, code: 'reader-failed:time-limit' })
  // The ticks at 10000 and 20000 and 30000 are dropped.
  fake.clock.advance(40000)
  expect(fake.procs.length).toBe(1)
  sched.request('command')
  fake.clock.advance(0)
  expect(fake.procs.length).toBe(2)
  // A result that is not slow ends the back-off.
  proc(fake, 1).finish(VIEW_STDOUT)
  fake.clock.advance(10000)
  expect(fake.procs.length).toBe(3)
})

test('an explicit request that is slow again keeps the back-off', () => {
  const { fake, sched } = settled(TIME_LIMIT, 1)
  fake.clock.advance(12000)
  sched.request('panel')
  fake.clock.advance(0)
  expect(fake.procs.length).toBe(2)
  proc(fake, 1).finish(TIME_LIMIT, 1)
  fake.clock.advance(60000)
  expect(fake.procs.length).toBe(2)
})

test('a cpu-limit and a reader-timeout result back off, and a plain failure does not', () => {
  const cpu = settled('', 152)
  cpu.fake.clock.advance(60000)
  expect(cpu.fake.procs.length).toBe(1)
  const failed = settled('', 1)
  failed.fake.clock.advance(10000)
  expect(failed.fake.procs.length).toBe(2)
})

test('a run that timed out starts no run by itself after it closes, and a request starts one', () => {
  const { fake, sched } = running()
  const p = proc(fake)
  p.spawn()
  // The interval fires at 10000, inside the run, and sets the tick flag.
  fake.clock.advance(10000)
  expect(p.terms).toBe(1)
  p.exit()
  p.close(undefined)
  fake.clock.advance(60000)
  expect(fake.procs.length).toBe(1)
  sched.request('command')
  fake.clock.advance(0)
  expect(fake.procs.length).toBe(2)
})

test('a tick that arrives during a run starts one more run after it', () => {
  const { fake } = running()
  // The tick at 10000 lands inside the run, which closes at 11000.
  fake.clock.advance(5900)
  proc(fake).finish(VIEW_STDOUT)
  fake.clock.advance(2100)
  expect(fake.procs.length).toBe(2)
})

test('a plan refusal settles with its code, takes no lease, and clears the back-off', () => {
  const env: Record<string, string> = { HOME }
  const { fake, sched } = mk({ ...okWorld(), env })
  sched.start()
  fake.clock.advance(4100)
  proc(fake).finish(TIME_LIMIT, 1)
  // Backed off: the tick at 10000 is dropped.
  fake.clock.advance(10000)
  expect(fake.procs.length).toBe(1)
  delete env.HOME
  const leaseOps = fake.asked('leaseWrite:').length
  sched.request('command')
  fake.clock.advance(0)
  expect(fake.mem.current).toEqual({ ok: false, code: 'home-invalid' })
  expect(fake.procs.length).toBe(1)
  expect(fake.asked('leaseWrite:').length).toBe(leaseOps)
  expect(fake.mem.running).toBe(false)
  // The back-off is gone: the interval at 20000 asks again, and a clean plan starts a reader.
  env.HOME = HOME
  fake.clock.advance(10000)
  expect(fake.procs.length).toBe(2)
})

test('the interval keeps asking while the plan refuses', () => {
  const env: Record<string, string> = {}
  const { fake, sched } = mk({ ...okWorld(), env })
  sched.start()
  fake.clock.advance(4100)
  expect(fake.mem.current).toEqual({ ok: false, code: 'home-invalid' })
  expect(fake.started()).toBe(0)
  const writes = fake.mem.writes.length
  fake.clock.advance(10000)
  expect(fake.mem.writes.length).toBe(writes + 1)
  expect(fake.mem.running).toBe(false)
})

// --- the lease ---------------------------------------------------------------------

test('a start that returns undefined settles as reader-cannot-start and releases', () => {
  const { fake, sched } = mk()
  fake.startMode.value = 'undefined'
  sched.start()
  fake.clock.advance(4100)
  expect(fake.started()).toBe(1)
  expect(fake.mem.current).toEqual({ ok: false, code: 'reader-cannot-start' })
  expect(fake.mem.running).toBe(false)
  // The scheduler recovers: the next tick starts again.
  fake.startMode.value = 'handle'
  fake.clock.advance(10000)
  expect(fake.procs.length).toBe(1)
})

test('a start that returns untracked settles as reader-cannot-start and keeps the lease', () => {
  const { fake, sched } = mk()
  fake.startMode.value = 'untracked'
  sched.start()
  fake.clock.advance(4100)
  expect(fake.mem.current).toEqual({ ok: false, code: 'reader-cannot-start' })
  expect(fake.mem.running).toBe(true)
  fake.startMode.value = 'handle'
  const releases = fake.asked('leaseWrite:false').length
  sched.request('command')
  fake.clock.advance(120000)
  expect(fake.started()).toBe(1)
  expect(fake.procs.length).toBe(0)
  expect(fake.asked('leaseWrite:false').length).toBe(releases)
  expect(fake.mem.running).toBe(true)
})

test('a failed acquire starts nothing and settles as reader-cannot-start', () => {
  const { fake, sched } = mk()
  sched.start()
  fake.clock.advance(4099)
  // Read free, then the write throws.
  fake.lease.writes.push('throw')
  fake.clock.advance(1)
  expect(fake.started()).toBe(0)
  expect(fake.mem.current).toEqual({ ok: false, code: 'reader-cannot-start' })
  expect(fake.mem.running).toBe(false)
  // Positive control: the lease works afterwards, and the next tick starts a reader.
  fake.clock.advance(10000)
  expect(fake.started()).toBe(1)
})

test('a busy acquire restores the flags, writes nothing and starts nothing', () => {
  const { fake, sched } = running()
  proc(fake).finish(VIEW_STDOUT)
  fake.clock.advance(2100)
  // Another setup holds the lease.
  fake.mem.running = true
  const writes = fake.mem.writes.length
  sched.request('command')
  fake.clock.advance(0)
  expect(fake.procs.length).toBe(1)
  expect(fake.mem.writes.length).toBe(writes)
  fake.clock.advance(2100 * 3)
  expect(fake.procs.length).toBe(1)
  expect(fake.mem.writes.length).toBe(writes)
  // The request was kept: once the lease frees, the next drain runs without a new request.
  fake.mem.running = false
  fake.clock.advance(2100)
  expect(fake.procs.length).toBe(2)
})

test('a busy acquire restores a tick as well', () => {
  const { fake } = running()
  proc(fake).finish(VIEW_STDOUT)
  fake.clock.advance(2100)
  fake.mem.running = true
  // The tick at 10000 is busy.
  fake.clock.advance(5800)
  expect(fake.procs.length).toBe(1)
  fake.mem.running = false
  fake.clock.advance(2100)
  expect(fake.procs.length).toBe(2)
})

// --- exceptions --------------------------------------------------------------------

test('a throwing kept write still releases the lease and cools down', () => {
  const { fake } = running()
  fake.keptThrows.value = true
  proc(fake).finish(VIEW_STDOUT)
  expect(fake.mem.running).toBe(false)
  fake.keptThrows.value = false
  fake.clock.advance(5900)
  expect(fake.procs.length).toBe(2)
})

test('a throwing kept write on a plan refusal does not stop the scheduler', () => {
  const env: Record<string, string> = {}
  const { fake, sched } = mk({ ...okWorld(), env })
  fake.keptThrows.value = true
  sched.start()
  fake.clock.advance(4100)
  env.HOME = HOME
  fake.keptThrows.value = false
  fake.clock.advance(10000)
  expect(fake.procs.length).toBe(1)
})

// --- stop --------------------------------------------------------------------------

test('stop clears every timer and both flags', () => {
  const { fake, sched } = mk()
  sched.start()
  fake.clock.advance(1000)
  expect(fake.clock.live()).toBeGreaterThan(0)
  sched.stop()
  expect(fake.clock.live()).toBe(0)
  fake.clock.advance(120000)
  expect(fake.started()).toBe(0)
})

test('stop in idle and in cooling clears the timers', () => {
  const { fake, sched } = running()
  proc(fake).finish(VIEW_STDOUT)
  sched.stop()
  expect(fake.clock.live()).toBe(0)
  const idle = running()
  proc(idle.fake).finish(VIEW_STDOUT)
  idle.fake.clock.advance(2100)
  idle.sched.stop()
  expect(idle.fake.clock.live()).toBe(0)
})

test('stop terminates a running reader and starts the grace timer', () => {
  const { fake, sched } = running()
  const p = proc(fake)
  p.spawn()
  sched.stop()
  expect(p.terms).toBe(1)
  // Only the grace timer remains.
  expect(fake.clock.delays()).toEqual([2000])
  fake.clock.advance(2000)
  expect(p.hards).toBe(1)
})

test('stop acts once', () => {
  const { fake, sched } = running()
  const p = proc(fake)
  p.spawn()
  sched.stop()
  sched.stop()
  expect(p.terms).toBe(1)
  fake.clock.advance(2000)
  expect(p.hards).toBe(1)
})

test('stop after exit sends no signal', () => {
  const { fake, sched } = running()
  const p = proc(fake)
  p.spawn()
  p.exit()
  sched.stop()
  fake.clock.advance(5000)
  expect(p.terms).toBe(0)
  expect(p.hards).toBe(0)
  expect(p.signalsAfterExit).toBe(0)
})

test('a run that ends after stop writes no kept value and releases the lease', () => {
  const { fake, sched } = running()
  const p = proc(fake)
  p.spawn()
  sched.stop()
  p.out(VIEW_STDOUT)
  p.exit()
  expect(fake.mem.running).toBe(true)
  p.close(0)
  expect(fake.mem.writes.length).toBe(0)
  expect(fake.mem.running).toBe(false)
  // The grace timer is cancelled by the end.
  expect(fake.clock.live()).toBe(0)
  fake.clock.advance(60000)
  expect(fake.procs.length).toBe(1)
})

test('a stopped scheduler ignores a settled run: no cool-down, no new start', () => {
  const { fake, sched } = running()
  const p = proc(fake)
  sched.stop()
  p.finish(VIEW_STDOUT)
  sched.request('command')
  fake.clock.advance(120000)
  expect(fake.procs.length).toBe(1)
})

// --- host facts --------------------------------------------------------------------

test('a missing executable ends on the error and the close after it is ignored', () => {
  const { fake } = running()
  const p = proc(fake)
  p.fail()
  expect(fake.mem.current).toEqual({ ok: false, code: 'reader-cannot-start' })
  expect(fake.mem.running).toBe(false)
  const writes = fake.mem.writes.length
  p.close(-2)
  expect(fake.mem.writes.length).toBe(writes)
  expect(fake.mem.writes.length).toBe(1)
  // No process exists to signal.
  expect(p.terms).toBe(0)
  expect(p.hards).toBe(0)
})

test('an error after spawn ends nothing: the close settles the run', () => {
  const { fake } = running()
  const p = proc(fake)
  p.spawn()
  p.fail()
  expect(fake.mem.writes.length).toBe(0)
  expect(fake.mem.running).toBe(true)
  p.out(VIEW_STDOUT)
  p.exit()
  p.close(0)
  expect(fake.mem.current).toEqual({ ok: true, stdout: VIEW_STDOUT })
})

test('a signal-killed process closes with no code and ends the run', () => {
  const { fake } = running()
  const p = proc(fake)
  p.spawn()
  p.exit()
  p.close(undefined)
  expect(fake.mem.current).toEqual({ ok: false, code: 'reader-failed' })
  expect(fake.mem.running).toBe(false)
})

test('a normal run delivers spawn, output, exit and close in order', () => {
  const { fake } = running()
  proc(fake).finish(VIEW_STDOUT)
  expect(fake.mem.current).toEqual({ ok: true, stdout: VIEW_STDOUT })
  expect(fake.mem.running).toBe(false)
})

test('output delivered before spawn and a close without exit still settle', () => {
  const { fake } = running()
  const p = proc(fake)
  p.out(VIEW_STDOUT)
  p.spawn()
  p.close(0)
  expect(fake.mem.current).toEqual({ ok: true, stdout: VIEW_STDOUT })
})

// --- reload ------------------------------------------------------------------------

// A second setup on the same clock and the same memory, as after a reload.
function reload(old: ReturnType<typeof mk>) {
  return mk(okWorld(), { clock: old.fake.clock, mem: old.fake.mem })
}

test('an old reader in flight at cleanup blocks the new start until its close and 2100 ms', () => {
  const old = running()
  const p = proc(old.fake)
  p.spawn()
  old.sched.stop()
  expect(p.terms).toBe(1)
  const next = reload(old)
  next.sched.start()
  // The old reader's close is long delayed: nothing starts, hold or no hold.
  old.fake.clock.advance(60000)
  expect(next.fake.started()).toBe(0)
  expect(p.hards).toBe(1)
  expect(old.fake.mem.running).toBe(true)
  p.exit()
  p.close(undefined)
  // The old setup writes no kept value and releases the lease.
  expect(old.fake.mem.writes.length).toBe(0)
  expect(old.fake.mem.running).toBe(false)
  // The next poll is within 250 ms and the free cool-down is 2100 ms.
  old.fake.clock.advance(2099)
  expect(next.fake.started()).toBe(0)
  old.fake.clock.advance(251)
  expect(next.fake.started()).toBe(1)
  expect(old.fake.started()).toBe(1)
})

test('the old grace timer and the new hold firing back to back start nothing', () => {
  const old = running()
  const p = proc(old.fake)
  p.spawn()
  old.fake.clock.advance(100)
  old.sched.stop()
  const next = reload(old)
  next.sched.start()
  // The event loop stalls; every timer comes due at once.
  old.fake.clock.stall(20000)
  old.fake.clock.flush('due')
  expect(p.hards).toBe(1)
  expect(next.fake.started()).toBe(0)
  expect(old.fake.alive()).toBe(1)
  old.fake.clock.stall(20000)
  old.fake.clock.flush('reverse')
  expect(next.fake.started()).toBe(0)
  expect(old.fake.alive() + next.fake.alive()).toBe(1)
})

test('an old close delayed past the new hold still gates the new start', () => {
  const old = running()
  const p = proc(old.fake)
  p.spawn()
  old.sched.stop()
  const next = reload(old)
  next.sched.start()
  old.fake.clock.advance(4100)
  // The new hold has run out; the old reader has not closed.
  expect(next.fake.started()).toBe(0)
  old.fake.clock.advance(4100)
  expect(next.fake.started()).toBe(0)
  p.exit()
  p.close(undefined)
  old.fake.clock.advance(2099 + 250)
  expect(next.fake.started()).toBe(1)
})

test('a lease left true starts nothing', () => {
  const next = mk()
  next.fake.mem.running = true
  next.sched.start()
  next.fake.clock.advance(120000)
  next.sched.request('command')
  next.fake.clock.advance(120000)
  expect(next.fake.started()).toBe(0)
})

test('an old write that throws is failed, then a reload: one process, by the new setup', () => {
  const old = mk()
  old.fake.lease.writes.push('throw')
  old.sched.start()
  old.fake.clock.advance(4100)
  expect(old.fake.started()).toBe(0)
  expect(old.fake.mem.running).toBe(false)
  old.sched.stop()
  const next = reload(old)
  next.sched.start()
  old.fake.clock.advance(4100)
  expect(old.fake.started()).toBe(0)
  expect(next.fake.started()).toBe(1)
})

test('an old write that changed the value before it threw is written back before a reload', () => {
  const old = mk()
  old.fake.lease.writes.push('throw-after-change')
  old.sched.start()
  old.fake.clock.advance(4100)
  expect(old.fake.mem.running).toBe(false)
  old.sched.stop()
  const next = reload(old)
  next.sched.start()
  old.fake.clock.advance(4100)
  expect(old.fake.started()).toBe(0)
  expect(next.fake.started()).toBe(1)
})

test('an old successful write followed by a throwing read is written back, and the new setup starts after the cool-down', () => {
  const old = mk()
  old.sched.start()
  old.fake.clock.advance(4099)
  old.fake.lease.reads.push('ok', 'throw')
  old.fake.clock.advance(1)
  expect(old.fake.started()).toBe(0)
  expect(old.fake.mem.running).toBe(false)
  expect(old.fake.mem.current).toEqual({ ok: false, code: 'reader-cannot-start' })
  old.sched.stop()
  const next = reload(old)
  next.sched.start()
  old.fake.clock.advance(4099)
  expect(next.fake.started()).toBe(0)
  old.fake.clock.advance(1)
  expect(next.fake.started()).toBe(1)
  expect(old.fake.started()).toBe(0)
})

test('the same with a write-back that also fails: the new setup starts nothing', () => {
  const old = mk()
  old.fake.lease.writes.push('ok', 'throw')
  old.sched.start()
  old.fake.clock.advance(4099)
  old.fake.lease.reads.push('ok', 'throw')
  old.fake.clock.advance(1)
  expect(old.fake.started()).toBe(0)
  expect(old.fake.mem.running).toBe(true)
  old.sched.stop()
  const next = reload(old)
  next.sched.start()
  old.fake.clock.advance(120000)
  expect(next.fake.started()).toBe(0)
  expect(old.fake.started()).toBe(0)
})

test('an old scheduler whose cleanup never ran beside a new one: at most one process alive at every step', () => {
  const old = mk()
  old.sched.start()
  old.fake.clock.advance(50)
  const next = reload(old)
  next.sched.start()
  const clock = old.fake.clock
  const seen: Proc[] = []
  const born: number[] = []
  let peak = 0
  for (let step = 0; step < 4000; step++) {
    clock.advance(50)
    for (const p of [...old.fake.procs, ...next.fake.procs]) {
      const at = seen.indexOf(p)
      if (at < 0) {
        seen.push(p)
        born.push(clock.now())
        p.spawn()
        p.out(VIEW_STDOUT)
      } else if (!p.closed && clock.now() - (born[at] ?? 0) >= 300) {
        p.exit()
        p.close(0)
      }
    }
    peak = Math.max(peak, old.fake.alive() + next.fake.alive())
    expect(old.fake.alive() + next.fake.alive() <= 1).toBe(true)
  }
  // Positive control: both setups started readers during the run.
  expect(peak).toBe(1)
  expect(old.fake.procs.length).toBeGreaterThan(2)
  expect(next.fake.procs.length).toBeGreaterThan(2)
})
