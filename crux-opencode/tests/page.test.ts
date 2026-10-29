// turnPage: the page-turn commands' one effect. It returns exactly true when it took the key and
// exactly false when it declined, and the host passes a declined key to the prompt.
import { test, expect } from 'claude-code/testing'
import { turnPage } from '../lib/page.ts'
import { INVALID, UNSUPPORTED } from '../lib/status.ts'
import { makeFake } from './fixtures/fake.ts'
import type { Fake } from './fixtures/fake.ts'
import { closed, doc, parsedOf, withPages } from './fixtures/cycles.ts'
import type { Parsed } from '../../crux-mods/hooks/lib/view.ts'

const ONE = withPages(1)
const TWO = withPages(2)
// Three pages give a middle page and the bounds on both sides of it. The reader accepts up to 60
// cycles, so one read view holds them.
const THREE: Parsed = withPages(3)

// A fake whose panel is open and focused: the one state in which a page key is taken.
const rig = (): Fake => {
  const fake = makeFake()
  fake.opens.open = true
  fake.pager.focused = true
  return fake
}

test('n and p step the page while the panel is open and focused, and return true', () => {
  const fake = rig()
  expect(turnPage(fake.host, THREE, 1)).toBe(true)
  expect(fake.pager.page).toBe(1)
  expect(turnPage(fake.host, THREE, 1)).toBe(true)
  expect(fake.pager.page).toBe(2)
  expect(turnPage(fake.host, THREE, -1)).toBe(true)
  expect(fake.pager.page).toBe(1)
  expect(fake.pager.writes).toEqual([1, 2, 1])
})

test('n on the last page and p on the first page stay put and still take the key', () => {
  const fake = rig()
  expect(turnPage(fake.host, TWO, -1)).toBe(true)
  expect(fake.pager.page).toBe(0)
  fake.pager.page = 1
  expect(turnPage(fake.host, TWO, 1)).toBe(true)
  expect(fake.pager.page).toBe(1)
})

test('a stored index past the last page is bounded on the press, so p moves back at once', () => {
  const fake = rig()
  fake.pager.page = 99
  expect(turnPage(fake.host, THREE, -1)).toBe(true)
  expect(fake.pager.page).toBe(1)
  fake.pager.page = 99
  expect(turnPage(fake.host, THREE, 1)).toBe(true)
  expect(fake.pager.page).toBe(2)
})

test('a stored index below zero, not a number, or not whole is bounded on the press', () => {
  const fake = rig()
  const hostWith = (stored: unknown) => ({ ...fake.host, pageRead: () => stored as number })
  expect(turnPage(hostWith(-5), THREE, 1)).toBe(true)
  expect(fake.pager.page).toBe(1)
  expect(turnPage(hostWith(0 / 0), THREE, 1)).toBe(true)
  expect(fake.pager.page).toBe(1)
  expect(turnPage(hostWith('2'), THREE, 1)).toBe(true)
  expect(fake.pager.page).toBe(1)
  expect(turnPage(hostWith(1.9), THREE, 1)).toBe(true)
  expect(fake.pager.page).toBe(2)
  // Infinity is not a page: it bounds to the first page, so p stays there.
  expect(turnPage(hostWith(1 / 0), THREE, -1)).toBe(true)
  expect(fake.pager.page).toBe(0)
})

test('a closed panel declines and writes nothing, even while the focus reader still says focused', () => {
  const fake = rig()
  fake.opens.open = false
  expect(turnPage(fake.host, THREE, 1)).toBe(false)
  expect(turnPage(fake.host, THREE, -1)).toBe(false)
  expect(fake.pager.writes).toEqual([])
})

test('an open panel that is not focused declines and writes nothing', () => {
  const fake = rig()
  fake.pager.focused = false
  expect(turnPage(fake.host, THREE, 1)).toBe(false)
  expect(fake.pager.writes).toEqual([])
})

test('a focus reader that throws reads as unfocused, so the key declines', () => {
  const fake = rig()
  fake.pager.focusThrows = true
  expect(turnPage(fake.host, THREE, 1)).toBe(false)
  expect(fake.pager.writes).toEqual([])
})

test('a panelOpen or panelFocused that throws declines with false', () => {
  const fake = rig()
  const open = {
    ...fake.host,
    panelOpen: () => {
      throw new Error('panelOpen')
    },
  }
  const focus = {
    ...fake.host,
    panelFocused: () => {
      throw new Error('panelFocused')
    },
  }
  expect(turnPage(open, THREE, 1)).toBe(false)
  expect(turnPage(focus, THREE, 1)).toBe(false)
  expect(fake.pager.writes).toEqual([])
})

test('one page or none declines, so the key reaches the prompt', () => {
  const fake = rig()
  expect(turnPage(fake.host, ONE, 1)).toBe(false)
  expect(turnPage(fake.host, parsedOf(doc(closed(1))), 1)).toBe(false)
  expect(turnPage(fake.host, parsedOf(doc([])), 1)).toBe(false)
  expect(fake.pager.writes).toEqual([])
})

test('no view, an unsupported view and an invalid view decline', () => {
  const fake = rig()
  expect(turnPage(fake.host, null, 1)).toBe(false)
  expect(turnPage(fake.host, UNSUPPORTED, 1)).toBe(false)
  expect(turnPage(fake.host, INVALID, 1)).toBe(false)
  expect(turnPage(fake.host, { ok: false, code: 'no-active-run' }, -1)).toBe(false)
  expect(fake.pager.writes).toEqual([])
})

test('a refused write declines with false and leaves the page', () => {
  const fake = rig()
  fake.pager.writeFails = true
  expect(turnPage(fake.host, THREE, 1)).toBe(false)
  expect(fake.pager.page).toBe(0)
})

test('a pageRead or pageWrite that throws declines with false and does not throw', () => {
  const fake = rig()
  const read = {
    ...fake.host,
    pageRead: () => {
      throw new Error('pageRead')
    },
  }
  const write = {
    ...fake.host,
    pageWrite: () => {
      throw new Error('pageWrite')
    },
  }
  expect(turnPage(read, THREE, 1)).toBe(false)
  expect(turnPage(write, THREE, 1)).toBe(false)
})

test('a pageWrite that answers anything but true declines with false', () => {
  const fake = rig()
  const host = { ...fake.host, pageWrite: () => undefined as unknown as boolean }
  expect(turnPage(host, THREE, 1)).toBe(false)
})
