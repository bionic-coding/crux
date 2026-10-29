// The cycle panel in crux-opencode: the slot, the queue card, the latest closed cycle as a panel and
// the paged `cycles:` list. The host turns the pages with n and p, so the list draws one page, a
// `page X/Y` footer and, with more than one page, a hint that names the keys.
import { test, expect } from 'claude-code/testing'
import { panelNode } from '../lib/render.ts'
import { HARNESS } from '../lib/status.ts'
import { OLDER_PAGE_SIZE, olderPages } from '../../crux-mods/hooks/lib/draw.ts'
import { closed, cycleRow, doc, parsedOf, plain, qItem, rowsOf } from './fixtures/cycles.ts'

const WIDTHS: Array<number | undefined> = [30, 40, 60, 86, 110, 120, undefined]
const HINT = 'p previous · n next'

const textOf = (d: unknown, width: number | undefined, page = 0): string[] =>
  rowsOf(panelNode(parsedOf(d), 'crux-dashboard', width, page)).map(plain)

// Two pages, the last one holding a single row: the latest closed cycle, one full page and one row.
// Two pages keep the fixture small; the reader accepts up to 60 cycles, so a view can hold six.
const CLOSED = 1 + OLDER_PAGE_SIZE + 1
const PAGES = 2
const LATEST = closed(CLOSED)[0]!.id
const FULL = doc([cycleRow(99, 'active'), ...closed(CLOSED)], { ok: true, items: [qItem(1, 'pending'), qItem(2, 'held')], authorization: null })

// The ids of the list rows on a page: the closed cycles after the first, newest first.
const idsOnPage = (page: number): string[] => {
  const rest = closed(CLOSED).slice(1).map(c => c.id)
  return rest.slice(page * OLDER_PAGE_SIZE, (page + 1) * OLDER_PAGE_SIZE)
}
// The list rows a drawing holds, as the ids it names after the `cycles:` heading.
const listIds = (lines: string[]): string[] => {
  const heading = lines.findIndex(l => l.trim() === 'cycles:')
  return lines.slice(heading + 1).flatMap(l => l.match(/CYC-\d{4}/)?.[0] ?? [])
}

test('the fixture holds the pages it claims, derived from the core page size', () => {
  expect(olderPages(parsedOf(FULL))).toBe(PAGES)
  expect(Object.keys(HARNESS)).toEqual(['bandPrefix', 'stallNote'])
})

for (const w of WIDTHS) {
  test(`width ${w ?? 'none'}: the expanded cycle follows the queue, then cycles: heads one page of rows and the footer`, () => {
    const lines = textOf(FULL, w, 0)
    const queue = lines.findIndex(l => l.startsWith('Queue'))
    const panelAt = lines.findIndex(l => l.startsWith(LATEST))
    const heading = lines.findIndex(l => l.trim() === 'cycles:')
    expect(queue).toBeGreaterThan(-1)
    expect(panelAt).toBeGreaterThan(queue)
    expect(heading).toBeGreaterThan(panelAt)
    expect(listIds(lines)).toEqual(idsOnPage(0))
    expect(lines.some(l => l.includes(`page 1/${PAGES}`))).toBe(true)
    expect(lines.some(l => l.includes('more'))).toBe(false)
    expect(lines.some(l => l.includes('older'))).toBe(false)
  })

  test(`width ${w ?? 'none'}: no row, the hint included, is wider than the width`, () => {
    if (w === undefined) return
    for (const page of [0, 1, PAGES - 1]) for (const l of textOf(FULL, w, page)) expect(l.length).toBeLessThanOrEqual(w)
  })

  test(`width ${w ?? 'none'}: the hint is the last line after the page footer`, () => {
    const lines = textOf(FULL, w, 0)
    const footer = lines.findIndex(l => l.includes(`page 1/${PAGES}`))
    expect(footer).toBeGreaterThan(-1)
    expect(lines.length - 1).toBe(footer + 1)
    expect(lines[lines.length - 1]!.trim()).toBe(HINT)
  })

  test(`width ${w ?? 'none'}: the slot draws first for an active cycle`, () => {
    const lines = textOf(FULL, w)
    const first = lines.findIndex(l => l.includes('CYC-0099'))
    expect(first >= 0).toBe(true)
    expect(lines.findIndex(l => l.includes(LATEST)) > first).toBe(true)
  })
}

test('each page draws its own rows, the last one short, and the footer counts the page', () => {
  for (let page = 0; page < PAGES; page++) {
    const lines = textOf(FULL, 100, page)
    expect(listIds(lines)).toEqual(idsOnPage(page))
    expect(lines.some(l => l.includes(`page ${page + 1}/${PAGES}`))).toBe(true)
  }
  expect(idsOnPage(PAGES - 1).length).toBe(1)
})

test('the pages do not repeat a row', () => {
  const all = [0, 1].flatMap(page => listIds(textOf(FULL, 100, page)))
  expect(all.length).toBe(CLOSED - 1)
  expect(new Set(all).size).toBe(CLOSED - 1)
})

test('a page past the last, or below the first, or not a number draws the nearest page', () => {
  expect(textOf(FULL, 100, 99)).toEqual(textOf(FULL, 100, PAGES - 1))
  expect(textOf(FULL, 100, -3)).toEqual(textOf(FULL, 100, 0))
  expect(textOf(FULL, 100, 0 / 0)).toEqual(textOf(FULL, 100, 0))
})

test('a list that shrinks below the stored page draws its last page', () => {
  const shrunk = doc([...closed(1 + OLDER_PAGE_SIZE + 1)])
  const lines = textOf(shrunk, 100, 2)
  expect(lines.some(l => l.includes('page 2/2'))).toBe(true)
})

test('the hint appears with more than one page and not with one or none', () => {
  const hinted = (n: number) => textOf(doc(closed(n)), 100).some(l => l.includes(HINT))
  expect(hinted(1 + OLDER_PAGE_SIZE + 1)).toBe(true)
  expect(hinted(1 + OLDER_PAGE_SIZE)).toBe(false)
  expect(hinted(2)).toBe(false)
  expect(hinted(1)).toBe(false)
  expect(hinted(0)).toBe(false)
})

test('one page draws its rows and no footer; one more row draws a second page', () => {
  const one = textOf(doc(closed(1 + OLDER_PAGE_SIZE)), 100)
  expect(one.some(l => l.includes('page'))).toBe(false)
  expect(listIds(one).length).toBe(OLDER_PAGE_SIZE)
  const two = textOf(doc(closed(2 + OLDER_PAGE_SIZE)), 100)
  expect(two.some(l => l.includes(`page 1/2`))).toBe(true)
})

test('with no open cycle the latest closed cycle is the panel and the other draws as one row', () => {
  const lines = textOf(doc(closed(2)), 100)
  expect(lines.filter(l => l.includes('loop 1 of 2')).length).toBe(1)
  expect(lines.findIndex(l => l.trim() === 'cycles:')).toBeGreaterThan(lines.findIndex(l => l.startsWith('CYC-0002')))
  expect(lines.filter(l => /^\S? ?CYC-0001/.test(l)).length).toBe(1)
})

test('exactly one closed cycle draws the panel alone, with no cycles: heading', () => {
  const lines = textOf(doc(closed(1)), 100)
  expect(lines.some(l => l.startsWith('CYC-0001'))).toBe(true)
  expect(lines.some(l => l.includes('cycles:'))).toBe(false)
})

test('the queue card: absent, empty, short, overflowing and unreadable', () => {
  const cycles = [cycleRow(9, 'active')]
  const text = (q: unknown) => textOf(doc(cycles, q), 100).join('\n')
  expect(text(undefined)).not.toContain('Queue title')
  expect(text(null)).not.toContain('Queue title')
  expect(text({ ok: true, items: [], authorization: null })).not.toContain('Queue title')
  expect(text({ ok: true, items: [qItem(1, 'pending'), qItem(2, 'held')], authorization: null })).toContain('Queue title 2')
  const many = Array.from({ length: 8 }, (_, i) => qItem(i + 1, 'pending'))
  const over = text({ ok: true, items: many, authorization: null })
  expect(over).toContain('Queue title 5')
  expect(over).not.toContain('Queue title 6')
  expect(over).toContain('+3 more')
  expect(text({ ok: false, error: 'broken' })).toContain('Queue unavailable')
})
