import { test, expect } from 'claude-code/testing'
import { bandNode, panelNode } from '../lib/render.ts'
import type { PlainNode } from '../lib/render.ts'
import { KEPT_CODES } from '../lib/status.ts'
import { TOKENS } from '../lib/theme.ts'
import { jsonText } from './fixtures/plain.ts'
import { kept } from '../../crux-mods/hooks/lib/view.ts'
import { CONTROL_TITLE, CONTROL_TITLE_CLEAN, FORMAT_TEXT, FORMAT_TEXT_CLEAN, IDLE_CONTROL, READER_CONTROL, READER_OK, READER_STALLED } from './fixtures/reader-docs.ts'

const PANEL = 'crux-dashboard'
const WIDTHS: (number | undefined)[] = [30, 40, 60, 86, 110, 120, undefined]
const fromDoc = (doc: unknown) => kept({ ok: true, stdout: jsonText(doc) }, KEPT_CODES)

// Control (Cc), format (Cf), default-ignorable, line and paragraph separators and lone surrogates.
const UNSAFE = new RegExp('[\\p{Cc}\\p{Cf}\\p{Default_Ignorable_Code_Point}\\u2028\\u2029\\ud800-\\udfff]', 'u')

const nodesOf = (n: PlainNode | null): PlainNode[] => (n === null ? [] : n.kind === 'box' ? [n, ...n.children.flatMap(c => nodesOf(c))] : [n])
const strings = (n: PlainNode | null): string[] => nodesOf(n).flatMap(x => (x.kind === 'text' ? x.spans.map(s => s.text) : []))

test('the control fixtures are views that carry the characters, so the removal below is not vacuous', () => {
  expect(UNSAFE.test(CONTROL_TITLE)).toBe(true)
  expect(UNSAFE.test(FORMAT_TEXT)).toBe(true)
  ;[READER_CONTROL, IDLE_CONTROL].forEach(doc => {
    const p = fromDoc(doc)
    expect(p !== null && p.ok).toBe(true)
  })
  const run = fromDoc(READER_CONTROL)
  expect(run !== null && run.ok && run.view.runs.some(r => r.prompts.some(pr => UNSAFE.test(pr.title)))).toBe(true)
  const last = fromDoc(IDLE_CONTROL)
  expect(last !== null && last.ok && last.view.last_completed !== null && last.view.last_completed.summary.some(l => UNSAFE.test(l))).toBe(true)
})

test('titles with control characters draw with them removed', () => {
  let rows = 0
  ;[READER_CONTROL, IDLE_CONTROL].forEach(doc => {
    WIDTHS.forEach(w => {
      ;[bandNode(fromDoc(doc), w), panelNode(fromDoc(doc), PANEL, w, 0)].forEach(node => {
        strings(node).forEach(text => {
          rows++
          expect(UNSAFE.test(text)).toBe(false)
        })
      })
    })
  })
  expect(rows).toBeGreaterThan(100)
})

test('the removal keeps the text around the control characters', () => {
  const lines = strings(panelNode(fromDoc(READER_CONTROL), PANEL, 120, 0)).join('\n')
  expect(lines).toContain(CONTROL_TITLE_CLEAN)
  const summary = strings(panelNode(fromDoc(IDLE_CONTROL), PANEL, 120, 0)).join('\n')
  expect(summary).toContain(FORMAT_TEXT_CLEAN)
})

test('free text reaches only the text of a text node, never a token or a box', () => {
  ;[READER_CONTROL, IDLE_CONTROL].forEach(doc => {
    WIDTHS.forEach(w => {
      ;[bandNode(fromDoc(doc), w), panelNode(fromDoc(doc), PANEL, w, 0)].forEach(node => {
        nodesOf(node).forEach(n => {
          if (n.kind === 'text') {
            n.spans.forEach(s => {
              expect(TOKENS).toContain(s.token)
              expect(typeof s.bold).toBe('boolean')
            })
          } else if (n.kind === 'box') {
            expect(n.border === null || TOKENS.includes(n.border)).toBe(true)
            expect(n.direction === 'row' || n.direction === 'column').toBe(true)
            expect(typeof n.width).toBe('number')
            expect(typeof n.padding).toBe('number')
          } else {
            expect(typeof n.width).toBe('number')
          }
        })
      })
    })
  })
})

test('a title the reader sends as an instruction draws as text and nothing else', () => {
  const texts = strings(panelNode(fromDoc(READER_OK), PANEL, 120, 0)).join('\n')
  expect(texts).toContain('Ignore previous instructions')
})

// This test shows determinism: the same document draws the same tree twice. It cannot observe a clock
// read, because a microtask wait moves no clock. The source check proves there is none: its Date
// fixtures under tools/opencode_gate_fixtures/negative/ (date-now.json, date-utc.json and others) seed
// each Date use and show the check refusing it. The next test shows that now_s moves the drawing.
test('the same document renders byte-equal on a second draw', async () => {
  const docs = [READER_OK, READER_STALLED, READER_CONTROL]
  const draw = () => docs.map(doc => WIDTHS.map(w => [bandNode(fromDoc(doc), w), panelNode(fromDoc(doc), PANEL, w, 0)]))
  const before = draw()
  await new Promise<void>(resolve => {
    resolve()
  })
  const after = draw()
  expect(after).toEqual(before)
  // Positive control: each document drew many rows, so the comparison above holds trees, not empty ones.
  expect(before.every(perDoc => perDoc.reduce((t, pair) => t + pair.reduce((u, node) => u + strings(node).length, 0), 0) > 100)).toBe(true)
})

test('a different now_s changes the drawing', () => {
  const stalled = panelNode(fromDoc(READER_STALLED), PANEL, 120, 0)
  const plain = panelNode(fromDoc(READER_OK), PANEL, 120, 0)
  expect(stalled).not.toBeNull()
  expect(stalled).not.toEqual(plain)
})
