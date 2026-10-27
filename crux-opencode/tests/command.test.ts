import { test, expect } from 'claude-code/testing'
import { runCommand } from '../lib/command.ts'
import { createScheduler } from '../lib/refresh.ts'
import type { Scheduler } from '../lib/refresh.ts'
import { PROJECT, makeFake, okWorld } from './fixtures/fake.ts'

// A scheduler double that logs into the same list as the fake host's panel.
function rig() {
  const fake = makeFake()
  const order: string[] = []
  const scheduler: Scheduler = {
    start: () => {},
    stop: () => {},
    request: reason => {
      order.push('request:' + reason)
    },
  }
  const host = {
    ...fake.host,
    openPanel: () => {
      order.push('openPanel')
      return fake.host.openPanel()
    },
  }
  return { fake, order, scheduler, host }
}

test('the command requests a refresh and then opens the panel', () => {
  const { fake, order, scheduler, host } = rig()
  runCommand(host, scheduler)
  expect(order).toEqual(['request:command', 'openPanel'])
  expect(fake.opens.count).toBe(1)
  expect(fake.toasts).toEqual([])
})

test('a panel that does not open toasts panel-unavailable', () => {
  const { fake, scheduler, host } = rig()
  fake.opens.result = false
  runCommand(host, scheduler)
  expect(fake.toasts).toEqual(['panel-unavailable'])
  runCommand(host, scheduler)
  expect(fake.toasts).toEqual(['panel-unavailable', 'panel-unavailable'])
})

test('a panel that opens toasts nothing', () => {
  const { fake, scheduler, host } = rig()
  fake.opens.result = true
  runCommand(host, scheduler)
  expect(fake.toasts).toEqual([])
  expect(fake.opens.count).toBe(1)
})

test('the command closes the panel when it is already open', () => {
  const { fake, order, scheduler, host } = rig()
  runCommand(host, scheduler)
  expect(fake.opens.open).toBe(true)
  runCommand(host, scheduler)
  expect(fake.opens.closes).toBe(1)
  expect(fake.opens.open).toBe(false)
  expect(fake.opens.count).toBe(1)
  expect(order).toEqual(['request:command', 'openPanel'])
  expect(fake.toasts).toEqual([])
})

test('the command toggles: open, close, open again', () => {
  const { fake, scheduler, host } = rig()
  runCommand(host, scheduler)
  runCommand(host, scheduler)
  runCommand(host, scheduler)
  expect(fake.opens.count).toBe(2)
  expect(fake.opens.closes).toBe(1)
  expect(fake.opens.open).toBe(true)
})

test('a panel state the host cannot report is treated as closed, so the command opens', () => {
  const { fake, scheduler, host } = rig()
  fake.opens.currentThrows = true
  runCommand(host, scheduler)
  expect(fake.opens.count).toBe(1)
  expect(fake.opens.closes).toBe(0)
})

test('the command catches a closePanel that throws', () => {
  const { fake, scheduler } = rig()
  const angry = {
    ...fake.host,
    panelOpen: () => true,
    closePanel: () => {
      throw new Error('closePanel')
    },
  }
  runCommand(angry, scheduler)
  expect(fake.opens.count).toBe(0)
  expect(fake.toasts).toEqual([])
})

test('the command catches a scheduler that throws and still opens the panel', () => {
  const { fake, host } = rig()
  const broken: Scheduler = {
    start: () => {},
    stop: () => {},
    request: () => {
      throw new Error('request')
    },
  }
  runCommand(host, broken)
  expect(fake.opens.count).toBe(1)
})

test('the command catches a host that throws', () => {
  const { fake, order, scheduler } = rig()
  const angry = {
    ...fake.host,
    openPanel: () => {
      throw new Error('openPanel')
    },
    toast: () => {
      throw new Error('toast')
    },
  }
  runCommand(angry, scheduler)
  expect(order).toEqual(['request:command'])
  expect(fake.toasts).toEqual([])
})

test('a scheduler that was never started, as on an unsupported version, still opens the panel', () => {
  const fake = makeFake()
  const scheduler = createScheduler(fake.host)
  runCommand(fake.host, scheduler)
  expect(fake.opens.count).toBe(1)
  expect(fake.clock.live()).toBe(0)
  expect(fake.started()).toBe(0)
  fake.opens.open = false
  fake.opens.result = false
  runCommand(fake.host, scheduler)
  expect(fake.toasts).toEqual(['panel-unavailable'])
})

test('the command asks a started scheduler for a run', () => {
  const fake = makeFake()
  const scheduler = createScheduler(fake.host)
  scheduler.start()
  fake.clock.advance(4100)
  const first = fake.procs[0]
  if (first === undefined) throw new Error('no first reader')
  first.finish('{"format":"x"}')
  fake.clock.advance(2100)
  expect(fake.procs.length).toBe(1)
  runCommand(fake.host, scheduler)
  fake.clock.advance(0)
  expect(fake.procs.length).toBe(2)
})

test('a project root that resolves late is read on the next refresh, not at setup', () => {
  const world = okWorld()
  world.directory = undefined
  const fake = makeFake(world)
  const scheduler = createScheduler(fake.host)
  scheduler.start()
  fake.clock.advance(4100)
  // The host has not yet filled its location: no reader starts, and nothing throws.
  expect(fake.started()).toBe(0)
  world.directory = PROJECT
  fake.clock.advance(60000)
  expect(fake.started()).toBe(1)
  const argv = fake.procs[0]!.argv
  expect(argv[argv.length - 1]).toBe(PROJECT)
})
