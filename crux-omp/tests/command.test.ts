import { test } from 'node:test'
import assert from 'node:assert/strict'
import { pageDelta, runCommand } from '../lib/command.ts'
import type { Scheduler } from '../lib/refresh.ts'
import { makeFake } from './fixtures/fake.ts'

function rig() {
  const fake = makeFake()
  const order: string[] = []
  const scheduler: Scheduler = {
    start: () => order.push('start'),
    stop: () => order.push('stop'),
    request: reason => order.push('request:' + reason),
  }
  return { fake, order, scheduler }
}

test('the command requests a refresh and then opens the panel', () => {
  const { fake, order, scheduler } = rig()
  runCommand(fake.host, scheduler)
  assert.deepEqual(order, ['request:command'])
  assert.equal(fake.opens.count, 1)
  assert.equal(fake.opens.open, true)
  assert.deepEqual(fake.toasts, [])
})

test('a panel that does not open toasts panel-unavailable', () => {
  const { fake, scheduler } = rig()
  fake.opens.result = false
  runCommand(fake.host, scheduler)
  assert.deepEqual(fake.toasts, ['panel-unavailable'])
})

test('the command closes an open panel and does nothing else', () => {
  const { fake, order, scheduler } = rig()
  fake.opens.open = true
  runCommand(fake.host, scheduler)
  assert.deepEqual(order, [])
  assert.equal(fake.opens.closes, 1)
  assert.equal(fake.opens.open, false)
})

test('the command toggles: open, close, open again', () => {
  const { fake, scheduler } = rig()
  runCommand(fake.host, scheduler)
  runCommand(fake.host, scheduler)
  runCommand(fake.host, scheduler)
  assert.equal(fake.opens.count, 2)
  assert.equal(fake.opens.closes, 1)
  assert.equal(fake.opens.open, true)
})

test('a scheduler that throws still opens the panel', () => {
  const { fake } = rig()
  const scheduler: Scheduler = {
    start: () => {},
    stop: () => {},
    request: () => {
      throw new Error('request')
    },
  }
  runCommand(fake.host, scheduler)
  assert.equal(fake.opens.open, true)
})

test('a host whose panel calls throw is caught', () => {
  const { fake } = rig()
  const host = {
    ...fake.host,
    panelOpen: () => {
      throw new Error('panelOpen')
    },
    openPanel: () => {
      throw new Error('openPanel')
    },
  }
  const scheduler: Scheduler = { start: () => {}, stop: () => {}, request: () => {} }
  assert.doesNotThrow(() => runCommand(host, scheduler))
})

test('pageDelta reads the next and prev arguments and nothing else', () => {
  assert.equal(pageDelta('next'), 1)
  assert.equal(pageDelta('  Prev '), -1)
  assert.equal(pageDelta(''), null)
  assert.equal(pageDelta('toggle'), null)
  assert.equal(pageDelta(undefined as never), null)
})
