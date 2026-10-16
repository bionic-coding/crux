// The plain node tree the band and the panel draw, and the functions that make it. A node holds
// widths, a direction, theme-token names and text: no colour value, no host element. The boundary
// file turns a node into elements and a token name into a colour at draw time.
//
// Three fixed forms below are matched token for token by the source check: readView, bandNode and
// panelNode. Each contains every exception the render path can throw, so a throw on one run changes
// no later run (the host runs the same computation again on every reactive change).
import { band, pane, statusLine } from '../../crux-mods/hooks/lib/draw.ts'
import type { Block } from '../../crux-mods/hooks/lib/draw.ts'
import { kept } from '../../crux-mods/hooks/lib/view.ts'
import type { Parsed } from '../../crux-mods/hooks/lib/view.ts'
import { drawingWidth } from '../../crux-mods/hooks/lib/width.ts'
import { BAND_PREFIX, HARNESS, INVALID, KEPT_CODES, UNAVAILABLE_AGENTS, UNSUPPORTED, UNSUPPORTED_CODE, UNSUPPORTED_WORDS } from './status.ts'
import { FRAME_TOKEN, spanToken } from './theme.ts'

// One run of text: its text, the theme-token name it draws in, and whether it is bold.
export type PlainSpan = { text: string; token: string; bold: boolean }

// A box with a width in cells, a direction, the token of its border (null for no border), the
// padding in cells on each side, and its children. A bordered box costs its border cell and its
// padding on both sides. A text node is one line of spans. A spacer is the gap between two
// children of a row.
export type PlainNode =
  | { kind: 'box'; width: number; direction: 'row' | 'column'; border: string | null; padding: number; children: PlainNode[] }
  | { kind: 'text'; spans: PlainSpan[] }
  | { kind: 'spacer'; width: number }

function nodeOf(b: Block): PlainNode {
  if (b.kind === 'line') return { kind: 'text', spans: b.line.map(s => ({ text: s.text, token: spanToken(s), bold: s.bold === true })) }
  const row = b.direction === 'row'
  const children = b.children.flatMap((c, i): PlainNode[] =>
    row && i > 0 && b.gap > 0 ? [{ kind: 'spacer', width: b.gap }, nodeOf(c)] : [nodeOf(c)],
  )
  return { kind: 'box', width: b.width, direction: b.direction, border: b.border === null ? null : FRAME_TOKEN, padding: b.border === null ? 0 : 1, children }
}

// The one line of an unsupported version, with no frame, at the region's width: the prefix and the
// words when both fit, else the words alone, else the words cut to the width.
function unsupportedBlock(width: unknown, style: { color?: 'error'; dim?: boolean }): Block {
  const w = drawingWidth(width)
  return { kind: 'box', direction: 'column', width: w, border: null, gap: 0, children: [{ kind: 'line', line: statusLine(BAND_PREFIX, UNSUPPORTED_WORDS, w, style) }] }
}

const isUnsupported = (p: Parsed): boolean => !p.ok && p.code === UNSUPPORTED_CODE

function drawBand(parsed: Parsed | null, width: unknown): PlainNode | null {
  if (parsed === null) return null
  if (isUnsupported(parsed)) return nodeOf(unsupportedBlock(width, { dim: true }))
  const block = band(parsed, UNAVAILABLE_AGENTS, width, HARNESS)
  return block === null ? null : nodeOf(block)
}

function drawPanel(parsed: Parsed | null, width: unknown): PlainNode | null {
  if (parsed === null) return null
  if (isUnsupported(parsed)) return nodeOf(unsupportedBlock(width, { color: 'error' }))
  return nodeOf(pane(parsed, UNAVAILABLE_AGENTS, width, 'docked', HARNESS))
}

export function readView(supported: boolean, read: () => unknown): Parsed | null {
  if (!supported) {
    return UNSUPPORTED
  }
  try {
    return kept(read(), KEPT_CODES)
  } catch {
    return INVALID
  }
}

export function bandNode(parsed: Parsed | null, width: unknown): PlainNode | null {
  try {
    return drawBand(parsed, width)
  } catch {
    try {
      return drawBand(INVALID, width)
    } catch {
      return null
    }
  }
}

export function panelNode(parsed: Parsed | null, name: unknown, width: unknown): PlainNode | null {
  if (name !== 'crux-dashboard') {
    return null
  }
  try {
    return drawPanel(parsed, width)
  } catch {
    try {
      return drawPanel(INVALID, width)
    } catch {
      return null
    }
  }
}
