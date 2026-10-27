import { test, expect } from 'claude-code/testing'
import { createFocusSlot } from '../lib/focus.ts'

test('an empty slot reads false', () => {
  expect(createFocusSlot().read()).toBe(false)
})

test('a published reader is called at each read, never copied', () => {
  const slot = createFocusSlot()
  let focused = false
  let calls = 0
  slot.publish(() => {
    calls += 1
    return focused
  })
  expect(slot.read()).toBe(false)
  focused = true
  expect(slot.read()).toBe(true)
  focused = false
  expect(slot.read()).toBe(false)
  expect(calls).toBe(3)
})

test('only a reader that returns exactly true reads as focused', () => {
  const slot = createFocusSlot()
  slot.publish(() => 1 as unknown as boolean)
  expect(slot.read()).toBe(false)
  slot.publish(() => undefined as unknown as boolean)
  expect(slot.read()).toBe(false)
})

test('a reader that throws reads false', () => {
  const slot = createFocusSlot()
  slot.publish(() => {
    throw new Error('reader')
  })
  expect(slot.read()).toBe(false)
})

test('the release empties the slot', () => {
  const slot = createFocusSlot()
  const release = slot.publish(() => true)
  expect(slot.read()).toBe(true)
  release()
  expect(slot.read()).toBe(false)
})

test('a stale release after a remount leaves the newer reader in place', () => {
  const slot = createFocusSlot()
  const releaseOld = slot.publish(() => true)
  // The remount publishes before the old cleanup runs.
  const releaseNew = slot.publish(() => true)
  releaseOld()
  expect(slot.read()).toBe(true)
  releaseNew()
  expect(slot.read()).toBe(false)
})

test('a release called twice does not empty a reader published after the first call', () => {
  const slot = createFocusSlot()
  const release = slot.publish(() => true)
  release()
  slot.publish(() => true)
  release()
  expect(slot.read()).toBe(true)
})

test('clear empties the slot whatever it holds', () => {
  const slot = createFocusSlot()
  slot.publish(() => true)
  slot.clear()
  expect(slot.read()).toBe(false)
})

test('two slots from the factory are independent', () => {
  const a = createFocusSlot()
  const b = createFocusSlot()
  a.publish(() => true)
  expect(a.read()).toBe(true)
  expect(b.read()).toBe(false)
  b.publish(() => true)
  a.clear()
  expect(a.read()).toBe(false)
  expect(b.read()).toBe(true)
})
