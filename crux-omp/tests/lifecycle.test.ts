import { test } from 'node:test'
import assert from 'node:assert/strict'
import { registerAll } from '../lib/lifecycle.ts'

test('every registration runs in order, then start', () => {
  const order: string[] = []
  const cleanup = registerAll(
    [
      () => () => order.push('undo-1'),
      () => () => order.push('undo-2'),
    ],
    () => order.push('start'),
    () => order.push('stop'),
  )
  assert.deepEqual(order, ['start'])
  cleanup()
  assert.deepEqual(order, ['start', 'stop', 'undo-2', 'undo-1'])
})

test('a registration that returns undefined releases what was acquired and starts nothing', () => {
  const order: string[] = []
  const cleanup = registerAll(
    [
      () => () => order.push('undo-1'),
      () => undefined,
      () => {
        order.push('never')
        return () => order.push('undo-3')
      },
    ],
    () => order.push('start'),
    () => order.push('stop'),
  )
  assert.deepEqual(order, ['undo-1'])
  cleanup()
  assert.deepEqual(order, ['undo-1', 'stop'])
})

test('a registration that throws is treated as a failed registration', () => {
  const order: string[] = []
  registerAll(
    [
      () => {
        throw new Error('no')
      },
    ],
    () => order.push('start'),
    () => order.push('stop'),
  )
  assert.deepEqual(order, [])
})

test('a release that throws does not stop the others', () => {
  const order: string[] = []
  const cleanup = registerAll(
    [
      () => () => {
        throw new Error('undo')
      },
      () => () => order.push('undo-2'),
    ],
    undefined,
    () => order.push('stop'),
  )
  cleanup()
  assert.deepEqual(order, ['stop', 'undo-2'])
})

test('the cleanup runs once', () => {
  let stops = 0
  const cleanup = registerAll([], undefined, () => {
    stops += 1
  })
  cleanup()
  cleanup()
  assert.equal(stops, 1)
})

test('a start that throws still leaves a working cleanup', () => {
  let stopped = 0
  const cleanup = registerAll([], () => {
    throw new Error('start')
  }, () => {
    stopped += 1
  })
  cleanup()
  assert.equal(stopped, 1)
})
