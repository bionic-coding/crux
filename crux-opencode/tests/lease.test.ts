import { test, expect } from 'claude-code/testing'
import { acquire, leaseFree, release } from '../lib/lease.ts'
import { makeFake } from './fixtures/fake.ts'

const writes = (log: string[]) => log.filter(e => e.startsWith('leaseWrite:'))
const reads = (log: string[]) => log.filter(e => e.startsWith('leaseRead:'))

test('leaseFree is true only when the lease reads free', () => {
  const fake = makeFake()
  expect(leaseFree(fake.host)).toBe(true)
  fake.mem.running = true
  expect(leaseFree(fake.host)).toBe(false)
})

test('an unreadable lease is never free', () => {
  const fake = makeFake()
  fake.lease.readDefault = 'throw'
  expect(leaseFree(fake.host)).toBe(false)
  fake.lease.readDefault = 'unknown'
  expect(leaseFree(fake.host)).toBe(false)
  fake.lease.readDefault = 'free'
  expect(leaseFree(fake.host)).toBe(true)
})

test('a free lease is acquired with one write and a confirming read', () => {
  const fake = makeFake()
  expect(acquire(fake.host)).toBe('acquired')
  expect(fake.mem.running).toBe(true)
  expect(writes(fake.log)).toEqual(['leaseWrite:true:ok'])
  expect(reads(fake.log)).toEqual(['leaseRead:free', 'leaseRead:held'])
})

test('a held lease is busy and nothing is written', () => {
  const fake = makeFake()
  fake.mem.running = true
  expect(acquire(fake.host)).toBe('busy')
  expect(writes(fake.log)).toEqual([])
  expect(fake.mem.running).toBe(true)
})

test('an unknown lease is busy and nothing is written', () => {
  const fake = makeFake()
  fake.lease.reads.push('unknown')
  expect(acquire(fake.host)).toBe('busy')
  expect(writes(fake.log)).toEqual([])
  // A throwing first read reads as unknown.
  const thrown = makeFake()
  thrown.lease.reads.push('throw')
  expect(acquire(thrown.host)).toBe('busy')
  expect(writes(thrown.log)).toEqual([])
  // Positive control: the same fakes acquire once the read is clean.
  expect(acquire(thrown.host)).toBe('acquired')
})

test('a write that throws is failed, with a false write-back', () => {
  const fake = makeFake()
  fake.lease.writes.push('throw')
  expect(acquire(fake.host)).toBe('failed')
  expect(writes(fake.log)).toEqual(['leaseWrite:true:throw', 'leaseWrite:false:ok'])
  expect(fake.mem.running).toBe(false)
})

test('a write that changed the value before it threw is written back', () => {
  const fake = makeFake()
  fake.lease.writes.push('throw-after-change')
  expect(acquire(fake.host)).toBe('failed')
  expect(fake.mem.running).toBe(false)
  expect(writes(fake.log)[writes(fake.log).length - 1]).toBe('leaseWrite:false:ok')
})

test('a successful write followed by a read that throws is failed, with a false write-back', () => {
  const fake = makeFake()
  fake.lease.reads.push('ok', 'throw')
  expect(acquire(fake.host)).toBe('failed')
  expect(writes(fake.log)).toEqual(['leaseWrite:true:ok', 'leaseWrite:false:ok'])
  expect(fake.mem.running).toBe(false)
})

test('a write that throws is failed, and false is written back without a second read', () => {
  const fake = makeFake()
  fake.lease.writes.push('throw')
  fake.lease.reads.push('ok')
  expect(acquire(fake.host)).toBe('failed')
  expect(fake.mem.running).toBe(false)
  expect(writes(fake.log)[writes(fake.log).length - 1]).toBe('leaseWrite:false:ok')
  expect(reads(fake.log)).toEqual(['leaseRead:free'])
})

test('a write that reports success but leaves the value false is failed', () => {
  const fake = makeFake()
  fake.lease.writes.push('lie')
  expect(acquire(fake.host)).toBe('failed')
  expect(fake.mem.running).toBe(false)
  expect(writes(fake.log)).toEqual(['leaseWrite:true:lie', 'leaseWrite:false:ok'])
})

test('a write-back that also fails still gives failed', () => {
  const fake = makeFake()
  fake.lease.writes.push('throw-after-change', 'throw')
  expect(acquire(fake.host)).toBe('failed')
  expect(writes(fake.log)).toEqual(['leaseWrite:true:throw-after-change', 'leaseWrite:false:throw'])
  // The value the failed write changed stays: it reads held.
  expect(fake.mem.running).toBe(true)
})

test('a read that misreports held after the write is not acquired when the write failed', () => {
  const fake = makeFake()
  fake.lease.writes.push('throw')
  fake.lease.reads.push('ok', 'held')
  expect(acquire(fake.host)).toBe('failed')
})

test('only a successful write followed by a read of held is acquired', () => {
  const fake = makeFake()
  fake.lease.reads.push('ok', 'unknown')
  expect(acquire(fake.host)).toBe('failed')
  const held = makeFake()
  held.lease.reads.push('ok', 'held')
  expect(acquire(held.host)).toBe('acquired')
})

test('two calls with no release between give acquired, then busy', () => {
  const fake = makeFake()
  expect(acquire(fake.host)).toBe('acquired')
  expect(acquire(fake.host)).toBe('busy')
  expect(writes(fake.log)).toEqual(['leaseWrite:true:ok'])
})

test('release writes false and a later acquire succeeds', () => {
  const fake = makeFake()
  expect(acquire(fake.host)).toBe('acquired')
  release(fake.host)
  expect(fake.mem.running).toBe(false)
  expect(writes(fake.log)[1]).toBe('leaseWrite:false:ok')
  expect(acquire(fake.host)).toBe('acquired')
})

test('release over a failing write leaves the lease held', () => {
  const fake = makeFake()
  acquire(fake.host)
  fake.lease.writes.push('throw')
  release(fake.host)
  expect(fake.mem.running).toBe(true)
  expect(acquire(fake.host)).toBe('busy')
})

test('two hosts that share memory cannot both acquire', () => {
  const first = makeFake()
  const second = makeFake(undefined, { clock: first.clock, mem: first.mem })
  expect(acquire(first.host)).toBe('acquired')
  expect(acquire(second.host)).toBe('busy')
  release(first.host)
  expect(acquire(second.host)).toBe('acquired')
  expect(acquire(first.host)).toBe('busy')
})
