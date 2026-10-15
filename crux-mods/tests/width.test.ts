import { test, expect } from 'claude-code/testing'
import { DEFAULT_WIDTH, ELLIPSIS, MAX_WIDTH, cells, fit, head, wrap, drawingWidth } from '../hooks/lib/width.ts'
import { AMBIGUOUS } from './fixtures/eaw-ambiguous.ts'

// Every expected value below is written by hand from Unicode 17.0.0's EastAsianWidth.txt: W and F
// count two cells, everything else one. Each pair pins both sides of a boundary of the table.
const PINS: [number, number][] = [
  [0x10ff, 1], [0x1100, 2], // Hangul Jamo starts
  [0x115f, 2], [0x1160, 1], // the leading-consonant fillers end
  [0x2e7f, 1], [0x2e80, 2], // CJK Radicals Supplement starts
  [0x303e, 2], [0x303f, 1], // CJK Symbols and Punctuation ends at U+303E
  [0x4dbf, 2], [0x4dc0, 2], // Extension A and the Yijing hexagrams: one run of W
  [0xa48c, 2], [0xa48d, 1], // Yi Syllables end
  [0xa490, 2], [0xa4c6, 2], [0xa4c7, 1], // Yi Radicals
  [0xa4cf, 1], [0xa4d0, 1], // Lisu: neither side is wide
  [0xd7a3, 2], [0xd7a4, 1], // Hangul Syllables end
  [0xfaff, 2], [0xfb00, 1], // CJK Compatibility Ideographs end
  [0xff00, 1], [0xff01, 2], // the fullwidth forms start
  [0xff60, 2], [0xff61, 1], // the fullwidth forms end, the halfwidth forms start
  [0xffe6, 2], [0xffe7, 1], // the fullwidth signs end
  [0x1f64f, 2], [0x1f650, 1], // Emoticons end
  [0x20000, 2], [0x2a6e0, 2], [0x2fffd, 2], [0x2fffe, 1], // plane 2, an unassigned code point included
  [0x30000, 2], [0x3fffd, 2], [0x3fffe, 1], // plane 3
  [0x0041, 1], [0x00e9, 1], [0x0301, 1], [0x2026, 1], [0x25d0, 1], [0x2713, 1], [0x4e2d, 2],
]

for (const [cp, want] of PINS) {
  test(`U+${cp.toString(16).toUpperCase().padStart(4, '0')} counts ${want} cell${want === 1 ? '' : 's'}`, () => {
    expect(cells(String.fromCodePoint(cp))).toBe(want)
  })
}

test('cells adds the cells of each code point', () => {
  expect(cells('')).toBe(0)
  expect(cells('abc')).toBe(3)
  expect(cells('\u{65E5}\u{672C}\u{8A9E}')).toBe(6)
  expect(cells('\u{FF21}b')).toBe(3)
  expect(cells('a\u{1F600}b')).toBe(4)
  expect(cells('\u{20000}x')).toBe(3)
  // A combining mark counts one cell: an over-count, never an under-count.
  expect(cells('e\u{301}')).toBe(2)
  // A lone surrogate counts one.
  expect(cells('a\ud800')).toBe(2)
})

test('every Ambiguous code point of Unicode 17.0.0 counts one cell', () => {
  const wide: string[] = []
  let n = 0
  for (const [lo, hi] of AMBIGUOUS) {
    for (let cp = lo; cp <= hi; cp++) {
      n++
      if (cells(String.fromCodePoint(cp)) !== 1) wide.push(cp.toString(16))
    }
  }
  expect(AMBIGUOUS.length).toBe(179)
  expect(n).toBeGreaterThan(130000)
  expect(wide).toEqual([])
})

test('fit keeps text that fits and cuts longer text with an ellipsis', () => {
  expect(ELLIPSIS).toBe('\u{2026}')
  expect(fit('abcdef', 6)).toBe('abcdef')
  expect(fit('abcdef', 5)).toBe('abcd\u{2026}')
  expect(fit('abcdef', 1)).toBe('\u{2026}')
  expect(fit('abcdef', 0)).toBe('')
  expect(fit('', 3)).toBe('')
  // A two-cell character is never split: the head stops short of it.
  expect(fit('\u{65E5}\u{672C}\u{8A9E}', 6)).toBe('\u{65E5}\u{672C}\u{8A9E}')
  expect(fit('\u{65E5}\u{672C}\u{8A9E}', 5)).toBe('\u{65E5}\u{672C}\u{2026}')
  expect(fit('\u{65E5}\u{672C}\u{8A9E}', 4)).toBe('\u{65E5}\u{2026}')
  expect(fit('\u{65E5}\u{672C}\u{8A9E}', 2)).toBe('\u{2026}')
  expect(fit('a\u{1F600}b', 3)).toBe('a\u{2026}')
})

test('fit stays within n for every n from 1 to 12 on mixed text, and keeps a head of the text', () => {
  const mixed = 'a\u{65E5}b\u{1F600}c\u{FF21}d\u{20000}e\u{301}f'
  for (let n = 1; n <= 12; n++) {
    const out = fit(mixed, n)
    expect([n, cells(out) <= n]).toEqual([n, true])
    const body = out.endsWith('\u{2026}') ? out.slice(0, -1) : out
    expect([n, mixed.startsWith(body)]).toEqual([n, true])
  }
  // Positive control: the text takes 15 cells (four of its eleven code points take two), so every n above cut it.
  expect(cells(mixed)).toBe(15)
})

test('head keeps the longest prefix of at most n cells', () => {
  expect(head('ab\u{65E5}c', 3)).toBe('ab')
  expect(head('ab\u{65E5}c', 4)).toBe('ab\u{65E5}')
  expect(head('ab\u{65E5}c', 0)).toBe('')
})

test('wrap cuts text into chunks of at most n cells and never splits a two-cell character', () => {
  expect(wrap('ab\u{65E5}\u{672C}c', 3)).toEqual(['ab', '\u{65E5}', '\u{672C}c'])
  expect(wrap('abcdefg', 3)).toEqual(['abc', 'def', 'g'])
  expect(wrap('abc', 3)).toEqual(['abc'])
  expect(wrap('', 3)).toEqual([''])
  // A character wider than n draws as an ellipsis.
  expect(wrap('a\u{65E5}b', 1)).toEqual(['a', '\u{2026}', 'b'])
  const long = 'x'.repeat(7) + '\u{1F600}'.repeat(5)
  const chunks = wrap(long, 4)
  expect(chunks.every(c => cells(c) <= 4)).toBe(true)
  expect(chunks.join('')).toBe(long)
})

test('the drawing width is the reported width, or 40 when none is reported, and at most 400', () => {
  expect([DEFAULT_WIDTH, MAX_WIDTH]).toEqual([40, 400])
  const cases: [unknown, number][] = [
    [30, 30], [86.7, 86], [1, 1], [1.9, 1], [0, 40], [0.5, 40], [-1, 40], [NaN, 40], [Infinity, 40], [-Infinity, 40],
    [undefined, 40], [null, 40], ['80', 40], [10000, 400], [400, 400], [401, 400],
  ]
  for (const [cols, want] of cases) expect([String(cols), drawingWidth(cols)]).toEqual([String(cols), want])
})
