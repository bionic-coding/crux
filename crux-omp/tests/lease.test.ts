import { test } from 'node:test'
import assert from 'node:assert/strict'
import { acquire, leaseFree, release } from '../lib/lease.ts'
import { makeFake } from './fixtures/fake.ts'

test('a free lease is acquired and written held', () => {
  const fake = makeFake()
  assert.equal(leaseFree(fake.host), true)
  assert.equal(acquire(fake.host), 'acquired')
  assert.equal(fake.mem.running, true)
})

test('a held lease is busy and is not written', () => {
  const fake = makeFake()
  fake.mem.running = true
  assert.equal(leaseFree(fake.host), false)
  assert.equal(acquire(fake.host), 'busy')
  assert.equal(fake.mem.running, true)
})

test('an unreadable lease is never free', () => {
  const fake = makeFake()
  fake.lease.readDefault = 'unknown'
  assert.equal(leaseFree(fake.host), false)
  assert.equal(acquire(fake.host), 'busy')
})

test('a write that lies fails the acquisition and writes false', () => {
  const fake = makeFake()
  fake.lease.writes.push('lie')
  assert.equal(acquire(fake.host), 'failed')
  assert.equal(fake.mem.running, false)
})

test('a write that changed the value before failing is undone', () => {
  const fake = makeFake()
  fake.lease.writes.push('throw-after-change')
  assert.equal(acquire(fake.host), 'failed')
  assert.equal(fake.mem.running, false)
})

test('a write that throws leaves the lease free and fails', () => {
  const fake = makeFake()
  fake.lease.writes.push('throw')
  assert.equal(acquire(fake.host), 'failed')
  assert.equal(fake.mem.running, false)
})

test('release writes false', () => {
  const fake = makeFake()
  fake.mem.running = true
  release(fake.host)
  assert.equal(fake.mem.running, false)
})
