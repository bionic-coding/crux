// The band and the panel as plain lines of text, and the functions that make them. OMP's widget
// surface takes string[], so the drawing is the core's Block tree flattened to rows: no element,
// no colour value and no host call reaches this module.
//
// bandLines and panelLines each contain every exception the render path can throw, so a throw on
// one run changes no later run.
import { band, pane } from '../../crux-mods/hooks/lib/draw.ts'
import type { Block, Span, ThemeKey } from '../../crux-mods/hooks/lib/draw.ts'
import { kept } from '../../crux-mods/hooks/lib/view.ts'
import type { Parsed } from '../../crux-mods/hooks/lib/view.ts'
import { cells, drawingWidth } from '../../crux-mods/hooks/lib/width.ts'
import { buildOmpBandLine, buildOmpCyclesPane } from './live.ts'
import type { LiveRuntimeSnapshot } from './live.ts'
import { HARNESS, INVALID, KEPT_CODES, UNAVAILABLE_AGENTS } from './status.ts'

export type OmpStyler = {
  fg?: (color: string, text: string) => string
  bold?: (text: string) => string
  dim?: (text: string) => string
}

const OMP_COLOR_MAP: Readonly<Record<ThemeKey, string>> = {
  claude: 'accent',
  suggestion: 'accent',
  success: 'success',
  permission: 'accent',
  merged: 'accent',
  warning: 'warning',
  error: 'error',
  inactive: 'muted',
  subtle: 'dim',
  text: 'text',
}

const BORDER = { topLeft: '\u{256D}', topRight: '\u{256E}', bottomLeft: '\u{2570}', bottomRight: '\u{256F}', horizontal: '\u{2500}', vertical: '\u{2502}' }

function styleSpan(span: Span, styler?: OmpStyler): string {
  let out = span.text
  if (out === '' || styler === undefined) return out
  if (span.color !== undefined && typeof styler.fg === 'function') {
    const token = OMP_COLOR_MAP[span.color] ?? 'text'
    if (token !== 'text') {
      try {
        out = styler.fg(token, out)
      } catch {}
    }
  } else if (span.dim === true && typeof styler.dim === 'function') {
    try {
      out = styler.dim(out)
    } catch {}
  }
  if (span.bold === true && typeof styler.bold === 'function') {
    try {
      out = styler.bold(out)
    } catch {}
  }
  return out
}

function borderPaint(text: string, borderColor: ThemeKey | null, styler?: OmpStyler): string {
  if (styler === undefined || borderColor === null || typeof styler.fg !== 'function') return text
  const token = OMP_COLOR_MAP[borderColor] ?? 'dim'
  try {
    return styler.fg(token, text)
  } catch {
    return text
  }
}

// A block as rows of text. A borderless column stacks its children. A bordered column draws a
// rounded frame with one cell of padding on each side. A row pads each child to its width and
// joins the rows with the gap.
export function blockLines(block: Block, styler?: OmpStyler): string[] {
  if (block.kind === 'line') return [block.line.map(s => styleSpan(s, styler)).join('')]
  if (block.direction === 'row') {
    const columns = block.children.map(c => blockLines(c, styler))
    const rawColumns = block.children.map(c => blockLines(c))
    const widths = block.children.map(b => (b.kind === 'box' ? b.width : b.line.reduce((n, s) => n + cells(s.text), 0)))
    const height = columns.reduce((n, column) => Math.max(n, column.length), 0)
    const rows: string[] = []
    for (let i = 0; i < height; i++) {
      const parts = columns.map((column, c) => {
        const styled = column[i] ?? ''
        const raw = rawColumns[c]?.[i] ?? ''
        const pad = ' '.repeat(Math.max(0, widths[c]! - cells(raw)))
        return styled + pad
      })
      rows.push(parts.join(' '.repeat(block.gap)).replace(/\s+$/, ''))
    }
    return rows
  }

  if (block.border === null) {
    if (block.gap <= 0) return block.children.flatMap(c => blockLines(c, styler))
    const rows: string[] = []
    block.children.forEach((child, i) => {
      if (i > 0) for (let g = 0; g < block.gap; g++) rows.push('')
      rows.push(...blockLines(child, styler))
    })
    return rows
  }

  const innerStyled = block.children.flatMap(c => blockLines(c, styler))
  const innerRaw = block.children.flatMap(c => blockLines(c))
  const inside = Math.max(0, block.width - 4)
  const rule = BORDER.horizontal.repeat(Math.max(0, block.width - 2))
  const vBar = borderPaint(BORDER.vertical, block.border, styler)
  return [
    borderPaint(BORDER.topLeft + rule + BORDER.topRight, block.border, styler),
    ...innerStyled.map((row, idx) => {
      const rawLen = cells(innerRaw[idx] ?? '')
      const pad = ' '.repeat(Math.max(0, inside - rawLen))
      return vBar + ' ' + row + pad + ' ' + vBar
    }),
    borderPaint(BORDER.bottomLeft + rule + BORDER.bottomRight, block.border, styler),
  ]
}

export function readView(read: () => unknown): Parsed | null {
  try {
    return kept(read(), KEPT_CODES)
  } catch {
    return INVALID
  }
}

function drawBand(parsed: Parsed | null, width: unknown, live?: LiveRuntimeSnapshot, styler?: OmpStyler): string[] | null {
  if (parsed === null && live === undefined) return null
  const w = drawingWidth(width)
  if (parsed !== null && parsed.ok && parsed.view.cycles !== undefined) {
    const line = buildOmpBandLine(parsed.view.cycles, parsed.view.now_s, live, w)
    return line === null ? null : blockLines({ kind: 'line', line }, styler)
  }
  if (parsed === null && live !== undefined) {
    const line = buildOmpBandLine([], null, live, w)
    return line === null ? null : blockLines({ kind: 'line', line }, styler)
  }
  if (parsed === null) return null
  const block = band(parsed, UNAVAILABLE_AGENTS, width, HARNESS)
  return block === null ? null : blockLines(block, styler)
}

function drawPanel(parsed: Parsed | null, width: unknown, live?: LiveRuntimeSnapshot, styler?: OmpStyler, page = 0): string[] | null {
  if (parsed === null && live === undefined) return null
  const w = drawingWidth(width)
  if (parsed !== null && parsed.ok && parsed.view.cycles !== undefined) {
    return blockLines(buildOmpCyclesPane(parsed.view.cycles, parsed.view.now_s, live, w, page), styler)
  }
  if (parsed === null && live !== undefined) {
    return blockLines(buildOmpCyclesPane([], null, live, w), styler)
  }
  if (parsed === null) return null
  return blockLines(pane(parsed, UNAVAILABLE_AGENTS, width, 'docked', HARNESS), styler)
}

export function bandLines(parsed: Parsed | null, width: unknown, live?: LiveRuntimeSnapshot, styler?: OmpStyler): string[] | null {
  try {
    return drawBand(parsed, width, live, styler)
  } catch {
    try {
      return drawBand(INVALID, width, undefined, styler)
    } catch {
      return null
    }
  }
}

export function panelLines(parsed: Parsed | null, width: unknown, live?: LiveRuntimeSnapshot, styler?: OmpStyler, page = 0): string[] | null {
  try {
    return drawPanel(parsed, width, live, styler, page)
  } catch {
    try {
      return drawPanel(INVALID, width, undefined, styler)
    } catch {
      return null
    }
  }
}
