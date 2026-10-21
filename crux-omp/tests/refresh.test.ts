import { test } from 'node:test'
import assert from 'node:assert/strict'
import { capabilities } from '../capabilities.ts'
import { GRACE_MS, HOLD_MS, INTERVAL_MS, TIMEOUT_MS, createScheduler } from '../lib/refresh.ts'
import type { Reason } from '../lib/refresh.ts'
import { makeFake } from './fixtures/fake.ts'
import type { Fake, Proc } from './fixtures/fake.ts'
import { VIEW_STDOUT } from './fixtures/docs.ts'

const mk = () => {
  const fake = makeFake()
  return { fake, sched: createScheduler(fake.host) }
}

// A scheduler started at time 0 on a free lease, advanced to the moment its first reader starts.
const running = () => {
  const r = mk()
  r.sched.start()
  r.fake.clock.advance(HOLD_MS)
  return r
}

const proc = (fake: Fake, i = 0): Proc => {
  const p = fake.procs[i]
  if (p === undefined) throw new Error('no process ' + i)
  return p
}

test('the reader timeout equals the manifest launch timeout', () => {
  assert.equal(TIMEOUT_MS, capabilities.launch.timeout_ms)
})

test('the periodic interval is 15 seconds', () => {
  assert.equal(INTERVAL_MS, 15000)
})

test('the first reader starts when the hold has run out, not before', () => {
  const { fake, sched } = mk()
  sched.start()
  fake.clock.advance(HOLD_MS - 1)
  assert.equal(fake.started(), 0)
  fake.clock.advance(1)
  assert.equal(fake.started(), 1)
  assert.equal(fake.mem.running, true)
})

test('requests before start and after stop do nothing', () => {
  const before = mk()
  for (const r of ['tick', 'panel', 'command', 'event'] as Reason[]) before.sched.request(r)
  before.fake.clock.advance(60000)
  assert.equal(before.fake.started(), 0)
  assert.equal(before.fake.clock.live(), 0)

  const after = running()
  after.sched.stop()
  const live = after.fake.clock.live()
  after.sched.request('command')
  assert.equal(after.fake.clock.live(), live)
})

test('a finished run writes the kept stdout and releases the lease', () => {
  const { fake } = running()
  proc(fake).finish(VIEW_STDOUT)
  assert.deepEqual(fake.mem.writes, [{ ok: true, stdout: VIEW_STDOUT }])
  assert.equal(fake.mem.running, false)
})

test('a finished run with no JSON writes reader-failed', () => {
  const { fake } = running()
  proc(fake).finish('not json', 1)
  assert.deepEqual(fake.mem.writes, [{ ok: false, code: 'reader-failed' }])
})

test('requests during a run coalesce into one run after the cool-down', () => {
  const { fake, sched } = running()
  sched.request('panel')
  sched.request('command')
  sched.request('event')
  proc(fake).finish(VIEW_STDOUT)
  fake.clock.advance(2100)
  assert.equal(fake.started(), 2)
})

test('a reader that does not close in time is sent term, then the hard kill after the grace', () => {
  const { fake } = running()
  fake.clock.advance(TIMEOUT_MS - 1)
  assert.equal(proc(fake).terms, 0)
  fake.clock.advance(1)
  assert.equal(proc(fake).terms, 1)
  fake.clock.advance(GRACE_MS - 1)
  assert.equal(proc(fake).hards, 0)
  fake.clock.advance(1)
  assert.equal(proc(fake).hards, 1)
})

test('stop kills the running reader and clears every timer', () => {
  const { fake, sched } = running()
  sched.stop()
  assert.equal(proc(fake).terms, 1)
  // The grace timer remains so a process that ignores term still receives the hard kill.
  assert.equal(fake.clock.live(), 1)
})

test('a scheduler that was never started holds no timer', () => {
  const { fake, sched } = mk()
  sched.stop()
  sched.start()
  fake.clock.advance(60000)
  assert.equal(fake.started(), 0)
})

test('a slow code backs off the periodic tick', () => {
  const { fake, sched } = running()
  proc(fake).finish('', 0)
  sched.request('command')
  fake.clock.advance(2100)
  assert.equal(fake.started(), 2)
  // The second run times out and the scheduler backs off: ticks are dropped, not queued.
  fake.clock.advance(TIMEOUT_MS)
  proc(fake, 1).close(0)
  fake.clock.advance(2100 + INTERVAL_MS)
  assert.equal(fake.started(), 2)
  // An explicit request still starts a run under back-off.
  sched.request('command')
  fake.clock.advance(0)
  assert.equal(fake.started(), 3)
})
