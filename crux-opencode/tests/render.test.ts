import { test, expect } from 'claude-code/testing'
import { bandNode, panelNode, readView } from '../lib/render.ts'
import type { PlainNode } from '../lib/render.ts'
import { DRAW_ONLY, INVALID, KEPT_CODES, UNSUPPORTED, UNSUPPORTED_WORDS } from '../lib/status.ts'
import { DEFAULT_WIDTH, cells } from '../../crux-mods/hooks/lib/width.ts'
import { PANEL_FRAME } from '../../crux-mods/hooks/lib/draw.ts'
import { kept, parseReader } from '../../crux-mods/hooks/lib/view.ts'
import type { Parsed, RunView } from '../../crux-mods/hooks/lib/view.ts'
import { frameCost, widthOf } from './fixtures/fake.ts'
import { jsonText } from './fixtures/plain.ts'
import { ALL_DOCS, READER_EMPTY, READER_OK } from './fixtures/reader-docs.ts'

const WIDTHS: (number | undefined)[] = [30, 40, 60, 86, 110, 120, undefined]
const PANEL = 'crux-dashboard'

const fromDoc = (doc: unknown): Parsed | null => kept({ ok: true, stdout: jsonText(doc) }, KEPT_CODES)

// Every result a view can hold: each reader document that holds a run, each kept status code, the
// unsupported status and no result.
const CASES: [string, Parsed | null][] = [
  ...ALL_DOCS.map((doc, i): [string, Parsed | null] => [`document ${i}`, fromDoc(doc)]),
  ...KEPT_CODES.map((code): [string, Parsed | null] => [`status ${code}`, { ok: false, code }]),
  ['unsupported', UNSUPPORTED],
  ['no result', null],
]

// --- the frame model (tests/fixtures/fake.ts): what a row and a frame cost -----------------------

type Tally = { rows: number; frames: number; widest: number }

// Checks every row against the cells left inside every enclosing frame. A row box's children,
// its spacers included, sum to no more than the inside of the box.
function check(n: PlainNode, avail: number, tally: Tally): void {
  const own = widthOf(n)
  expect(own).toBeLessThanOrEqual(avail)
  if (n.kind === 'text') {
    tally.rows++
    tally.widest = Math.max(tally.widest, own)
    return
  }
  if (n.kind === 'spacer') return
  const cost = frameCost(n)
  if (cost > 0) tally.frames++
  const inner = n.width - cost
  if (n.direction === 'row') {
    expect(n.children.reduce((t, c) => t + widthOf(c), 0)).toBeLessThanOrEqual(inner)
  }
  n.children.forEach(c => check(c, inner, tally))
}

const budget = (w: number | undefined): number => (w === undefined ? DEFAULT_WIDTH : w)

test('every reader fixture in the list is a view, and the empty reader document is the no-active-run status, not a view', () => {
  ALL_DOCS.forEach(doc => {
    const p = fromDoc(doc)
    expect(p !== null && p.ok).toBe(true)
  })
  expect(parseReader(jsonText(READER_EMPTY))).toEqual({ ok: false, code: 'no-active-run' })
})

test('a drawing with no width reported is as wide as the default, 40 cells', () => {
  expect(DEFAULT_WIDTH).toBe(40)
})

test('the frame model costs what the core charges a bordered panel', () => {
  const p = fromDoc(READER_OK)
  const node = panelNode(p, PANEL, 60, 0)
  expect(node).not.toBeNull()
  const framed: PlainNode[] = []
  const walk = (n: PlainNode) => {
    if (n.kind !== 'box') return
    if (n.border !== null) framed.push(n)
    n.children.forEach(walk)
  }
  if (node !== null) walk(node)
  expect(framed.length).toBeGreaterThan(0)
  framed.forEach(f => expect(frameCost(f)).toBe(PANEL_FRAME))
  expect(PANEL_FRAME).toBe(4)
})

test('the band fits the reported width at every width, over every reader result', () => {
  const tally: Tally = { rows: 0, frames: 0, widest: 0 }
  let drawn = 0
  CASES.forEach(([, p]) => {
    WIDTHS.forEach(w => {
      const node = bandNode(p, w)
      if (node === null) return
      drawn++
      check(node, budget(w), tally)
    })
  })
  expect(drawn).toBeGreaterThan(200)
  expect(tally.rows).toBeGreaterThan(200)
})

test('the panel fits the reported width at every width, over every reader result', () => {
  const tally: Tally = { rows: 0, frames: 0, widest: 0 }
  let drawn = 0
  CASES.forEach(([, p]) => {
    WIDTHS.forEach(w => {
      const node = panelNode(p, PANEL, w, 0)
      if (node === null) return
      drawn++
      check(node, budget(w), tally)
    })
  })
  expect(drawn).toBeGreaterThan(200)
  expect(tally.rows).toBeGreaterThan(3000)
  expect(tally.frames).toBeGreaterThan(300)
})

test('the panel is drawn at the reported width and holds wide rows, so the check is not vacuous', () => {
  const p = fromDoc(READER_OK)
  WIDTHS.forEach(w => {
    const tally: Tally = { rows: 0, frames: 0, widest: 0 }
    const node = panelNode(p, PANEL, w, 0)
    expect(node).not.toBeNull()
    if (node !== null) check(node, budget(w), tally)
    expect(node === null ? -1 : widthOf(node)).toBe(budget(w))
    expect(tally.widest).toBeGreaterThan(20)
  })
})

test('a panel of another name, and a panel with no name, draw nothing', () => {
  CASES.forEach(([, p]) => {
    WIDTHS.forEach(w => {
      expect(panelNode(p, 'other-panel', w, 0)).toBeNull()
      expect(panelNode(p, '', w, 0)).toBeNull()
      expect(panelNode(p, undefined, w, 0)).toBeNull()
      expect(panelNode(p, 'Crux-Dashboard', w, 0)).toBeNull()
    })
  })
  expect(panelNode(fromDoc(READER_OK), PANEL, 60, 0)).not.toBeNull()
})

test('the band with no result draws nothing, and the band and the panel are not the same drawing', () => {
  expect(bandNode(null, 60)).toBeNull()
  expect(panelNode(null, PANEL, 60, 0)).toBeNull()
  expect(bandNode(fromDoc(READER_OK), 60)).not.toEqual(panelNode(fromDoc(READER_OK), PANEL, 60, 0))
})

// --- the unsupported version ---------------------------------------------------------------------

const textOf = (n: PlainNode | null): string => {
  if (n === null) return ''
  if (n.kind === 'text') return n.spans.map(s => s.text).join('')
  if (n.kind === 'spacer') return ''
  return n.children.map(textOf).join('\n')
}

test('the unsupported version draws one unframed line with the words at every width and with none', () => {
  WIDTHS.forEach(w => {
    ;[bandNode(UNSUPPORTED, w), panelNode(UNSUPPORTED, PANEL, w, 0)].forEach(node => {
      expect(node).not.toBeNull()
      expect(textOf(node)).toContain(UNSUPPORTED_WORDS)
      expect(textOf(node).includes('\n')).toBe(false)
      if (node === null) return
      const tally: Tally = { rows: 0, frames: 0, widest: 0 }
      check(node, budget(w), tally)
      expect(tally.rows).toBe(1)
      expect(tally.frames).toBe(0)
    })
  })
  expect(UNSUPPORTED_WORDS).toBe('unsupported OpenCode version')
  expect(cells(UNSUPPORTED_WORDS)).toBe(28)
})

test('the unsupported line keeps the prefix when it fits, and drops it when it does not', () => {
  expect(textOf(bandNode(UNSUPPORTED, 110))).toBe('crux-opencode dashboard: unsupported OpenCode version')
  expect(textOf(bandNode(UNSUPPORTED, 40))).toBe('unsupported OpenCode version')
  expect(textOf(bandNode(UNSUPPORTED, 30))).toBe('unsupported OpenCode version')
  expect(textOf(bandNode(UNSUPPORTED, undefined))).toBe('unsupported OpenCode version')
})

test('a status draws with the band prefix in the band and the neutral prefix in the panel', () => {
  const status: Parsed = { ok: false, code: 'uv-not-found' }
  expect(textOf(bandNode(status, 110))).toBe('crux-opencode dashboard: uv-not-found')
  expect(textOf(panelNode(status, PANEL, 110, 0))).toBe('Dashboard unavailable: uv-not-found')
  expect(textOf(bandNode({ ok: false, code: 'no-active-run' }, 110))).toBe('')
  expect(bandNode({ ok: false, code: 'no-active-run' }, 110)).toBeNull()
})

// --- the render boundary -------------------------------------------------------------------------

const GOOD = fromDoc(READER_OK)
const goodView = GOOD !== null && GOOD.ok ? GOOD.view : undefined

// A result whose view throws an Error when the core reads its runs while it draws.
function throwingView(): Parsed {
  if (goodView === undefined) throw new Error('the fixture document is not a view')
  return {
    ok: true,
    view: {
      ...goodView,
      get runs(): RunView[] {
        throw new Error('a member read that throws')
      },
    },
  }
}

test('the throwing view really throws in the core, so the cases below are not vacuous', () => {
  const view = throwingView()
  expect(() => (view.ok ? view.view.runs : [])).toThrow()
  expect(GOOD).not.toBeNull()
  expect(bandNode(GOOD, 60)).not.toEqual(bandNode(INVALID, 60))
  expect(panelNode(GOOD, PANEL, 60, 0)).not.toEqual(panelNode(INVALID, PANEL, 60, 0))
})

test('readView: a read that throws gives the reader-output-invalid status', () => {
  let calls = 0
  const result = readView(true, () => {
    calls++
    throw new Error('a memory read that throws')
  })
  expect(result).toEqual(INVALID)
  expect(calls).toBe(1)
})

test('readView: an envelope whose property read throws while the core checks it gives the status', () => {
  const envelope = {
    ok: true,
    get stdout(): string {
      throw new Error('a property read that throws')
    },
  }
  expect(readView(true, () => envelope)).toEqual(INVALID)
  // The same envelope with a plain value reads: the throw is what made the status.
  expect(readView(true, () => ({ ok: true, stdout: jsonText(READER_OK) }))).toEqual(GOOD)
})

test('readView: an unsupported version gives the unsupported status and never calls the read', () => {
  let calls = 0
  const result = readView(false, () => {
    calls++
    return { ok: true, stdout: jsonText(READER_OK) }
  })
  expect(result).toEqual(UNSUPPORTED)
  expect(calls).toBe(0)
})

test('readView: a supported version reads through the core with the kept set', () => {
  expect(readView(true, () => null)).toBeNull()
  expect(readView(true, () => undefined)).toBeNull()
  expect(readView(true, () => ({ ok: false, code: 'uv-not-found' }))).toEqual({ ok: false, code: 'uv-not-found' })
  expect(readView(true, () => ({ ok: false, code: 'a-code-nobody-defined' }))).toEqual(INVALID)
  DRAW_ONLY.forEach(code => expect(readView(true, () => ({ ok: false, code }))).toEqual(INVALID))
  expect(readView(true, () => 'text')).toEqual(INVALID)
})

type Draw = (p: Parsed | null, w: number | undefined) => PlainNode | null
const DRAWS: [string, Draw][] = [
  ['bandNode', (p, w) => bandNode(p, w)],
  ['panelNode', (p, w) => panelNode(p, PANEL, w, 0)],
]

test('a throw during drawing gives the reader-output-invalid status node, as a first call', () => {
  DRAWS.forEach(([, draw]) => {
    WIDTHS.forEach(w => {
      const node = draw(throwingView(), w)
      expect(node).not.toBeNull()
      expect(node).toEqual(draw(INVALID, w))
      expect(textOf(node)).toContain('reader-output-invalid')
    })
  })
})

test('each call equals the same call made alone, whatever ran before it', () => {
  DRAWS.forEach(([, draw]) => {
    WIDTHS.forEach(w => {
      const aloneThrow = draw(throwingView(), w)
      const aloneClean = draw(GOOD, w)
      // clean, then throwing, then clean, then throwing twice, then clean
      expect(draw(GOOD, w)).toEqual(aloneClean)
      expect(draw(throwingView(), w)).toEqual(aloneThrow)
      expect(draw(GOOD, w)).toEqual(aloneClean)
      expect(draw(throwingView(), w)).toEqual(aloneThrow)
      expect(draw(throwingView(), w)).toEqual(aloneThrow)
      expect(draw(GOOD, w)).toEqual(aloneClean)
      expect(aloneThrow).not.toEqual(aloneClean)
    })
  })
})

test('a panel of another name draws nothing for a throwing view, on every path', () => {
  WIDTHS.forEach(w => {
    expect(panelNode(throwingView(), 'other-panel', w, 0)).toBeNull()
    expect(panelNode(throwingView(), undefined, w, 0)).toBeNull()
    expect(panelNode(GOOD, 'other-panel', w, 0)).toBeNull()
  })
})

test('a result whose status member throws draws nothing rather than throwing', () => {
  const hostile: Parsed = {
    get ok(): boolean {
      throw new Error('a flag read that throws')
    },
    code: 'x',
  }
  WIDTHS.forEach(w => {
    expect(bandNode(hostile, w)).toEqual(bandNode(INVALID, w))
    expect(panelNode(hostile, PANEL, w, 0)).toEqual(panelNode(INVALID, PANEL, w, 0))
  })
})

test('a width that is not a number draws at the default width of 40', () => {
  const hostileWidth = {
    valueOf(): number {
      throw new Error('a width read that throws')
    },
  }
  expect(bandNode(GOOD, hostileWidth)).toEqual(bandNode(GOOD, undefined))
  expect(panelNode(GOOD, PANEL, hostileWidth, 0)).toEqual(panelNode(GOOD, PANEL, undefined, 0))
  expect(bandNode(GOOD, hostileWidth)).toEqual(bandNode(GOOD, 40))
  expect(panelNode(GOOD, PANEL, hostileWidth, 0)).toEqual(panelNode(GOOD, PANEL, 40, 0))
})
