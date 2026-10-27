import { test, expect } from 'claude-code/testing'
import { FRAME_TOKEN, TEXT_BASE, TEXT_MUTED, TOKENS, TOKEN_TABLE, spanToken, tokenOfKey } from '../lib/theme.ts'
import { bandNode, panelNode } from '../lib/render.ts'
import type { PlainNode } from '../lib/render.ts'
import { KEPT_CODES } from '../lib/status.ts'
import { THEME_KEYS, PANEL_BORDER, band, pane } from '../../crux-mods/hooks/lib/draw.ts'
import type { Block } from '../../crux-mods/hooks/lib/draw.ts'
import { kept } from '../../crux-mods/hooks/lib/view.ts'
import { HARNESS, UNAVAILABLE_AGENTS } from '../lib/status.ts'
import { jsonText } from './fixtures/plain.ts'
import { ALL_DOCS, READER_CONTROL, READER_EMPTY } from './fixtures/reader-docs.ts'

// The map, written out here apart from theme.ts.
const MAP: [string, string][] = [
  ['merged', 'syntax.keyword'],
  ['permission', 'syntax.type'],
  ['claude', 'syntax.function'],
  ['suggestion', 'text.feedback.info.base'],
  ['success', 'text.feedback.success.base'],
  ['inactive', 'text.muted'],
  ['text', 'text.base'],
  ['error', 'text.feedback.error.base'],
  ['warning', 'text.feedback.warning.base'],
  ['subtle', 'text.muted'],
]

const docParsed = (doc: unknown) => kept({ ok: true, stdout: jsonText(doc) }, KEPT_CODES)

test('each of the ten core keys maps to exactly one token, as the table says', () => {
  expect(THEME_KEYS.length).toBe(10)
  expect(TOKEN_TABLE.length).toBe(10)
  MAP.forEach(([key, token]) => expect(tokenOfKey(key)).toBe(token))
  THEME_KEYS.forEach(key => {
    expect(TOKEN_TABLE.filter(row => row[0] === key).length).toBe(1)
    expect(MAP.filter(row => row[0] === key).length).toBe(1)
  })
})

test('the tokens the module can produce are the nine the table and the two defaults name', () => {
  const want = [...new Set(MAP.map(row => row[1]))]
  expect(want.length).toBe(9)
  expect([...TOKENS].sort()).toEqual([...want].sort())
  expect(TEXT_BASE).toBe('text.base')
  expect(TEXT_MUTED).toBe('text.muted')
})

test('a span with no colour draws in text.base, and a dim-only span in text.muted', () => {
  expect(spanToken({ text: 'x' })).toBe('text.base')
  expect(spanToken({ text: 'x', bold: true })).toBe('text.base')
  expect(spanToken({ text: 'x', dim: true })).toBe('text.muted')
  expect(spanToken({ text: 'x', bold: true, dim: true })).toBe('text.muted')
})

test('a colour wins over dim, and a coloured span takes its key token', () => {
  expect(spanToken({ text: 'x', color: 'error', dim: true })).toBe('text.feedback.error.base')
  expect(spanToken({ text: 'x', color: 'merged', dim: true, bold: true })).toBe('syntax.keyword')
  MAP.forEach(([key, token]) => {
    const colour = THEME_KEYS.find(k => k === key)
    expect(colour).toBeDefined()
    if (colour !== undefined) expect(spanToken({ text: 'x', color: colour })).toBe(token)
  })
})

test('the frame draws through the same map', () => {
  expect(PANEL_BORDER).toBe('subtle')
  expect(FRAME_TOKEN).toBe('text.muted')
  expect(FRAME_TOKEN).toBe(tokenOfKey(PANEL_BORDER))
})

test('a key the table does not name draws in text.base', () => {
  expect(tokenOfKey('not-a-key')).toBe('text.base')
  expect(tokenOfKey('')).toBe('text.base')
})

const blocksOf = (b: Block | null): Block[] => (b === null ? [] : b.kind === 'line' ? [b] : [b, ...b.children.flatMap(c => blocksOf(c))])

const nodesOf = (n: PlainNode | null): PlainNode[] => (n === null ? [] : n.kind === 'box' ? [n, ...n.children.flatMap(c => nodesOf(c))] : [n])

test('every span of every drawn node carries a token the module produces', () => {
  const parsed = [...ALL_DOCS, READER_EMPTY, READER_CONTROL].map(doc => docParsed(doc))
  let spans = 0
  let boxes = 0
  parsed.forEach(p => {
    ;[30, 40, 60, 86, 110, 120, undefined].forEach(w => {
      ;[bandNode(p, w), panelNode(p, 'crux-dashboard', w, 0)].forEach(node => {
        nodesOf(node).forEach(n => {
          if (n.kind === 'text') {
            n.spans.forEach(s => {
              spans++
              expect(TOKENS).toContain(s.token)
            })
          } else if (n.kind === 'box' && n.border !== null) {
            boxes++
            expect(n.border).toBe(FRAME_TOKEN)
          }
        })
      })
    })
  })
  expect(spans).toBeGreaterThan(1000)
  expect(boxes).toBeGreaterThan(50)
})

test('every coloured span the core draws carries non-blank text', () => {
  let coloured = 0
  ;[...ALL_DOCS, READER_EMPTY].forEach(doc => {
    const p = docParsed(doc)
    if (p === null) return
    ;[30, 40, 60, 86, 110, 120, undefined].forEach(w => {
      ;[band(p, UNAVAILABLE_AGENTS, w, HARNESS), pane(p, UNAVAILABLE_AGENTS, w, 'docked', HARNESS)].forEach(block => {
        blocksOf(block).forEach(b => {
          if (b.kind !== 'line') return
          b.line.forEach(s => {
            if (s.color === undefined) return
            coloured++
            expect(s.text.trim()).not.toBe('')
          })
        })
      })
    })
  })
  expect(coloured).toBeGreaterThan(100)
})
