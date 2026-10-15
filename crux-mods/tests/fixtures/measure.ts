// A test-side reading of a drawn tree, written independently of hooks/lib/width.ts and
// hooks/lib/draw.ts. It places each Box and each line of Text the way the terminal lays them out
// (a Box's width prop, its round border and its padding, a row's columns and its gap) and counts
// each line's cells with a coarse hand-written list of wide blocks. Every wide character the
// fixtures draw lies in the list, and no narrow one does.

const COARSE_WIDE: [number, number][] = [
  [0x1100, 0x115f], [0x2e80, 0x303e], [0x3041, 0x33ff], [0x3400, 0x4dbf], [0x4e00, 0x9fff], [0xa000, 0xa4cf], [0xac00, 0xd7a3],
  [0xf900, 0xfaff], [0xfe30, 0xfe4f], [0xff01, 0xff60], [0xffe0, 0xffe6], [0x1f300, 0x1f320], [0x1f600, 0x1f64f], [0x1f680, 0x1f6c5],
  [0x20000, 0x2fffd], [0x30000, 0x3fffd],
]

export function coarseCells(s: string): number {
  let n = 0
  for (const ch of s) {
    const cp = ch.codePointAt(0)!
    n += COARSE_WIDE.some(([lo, hi]) => cp >= lo && cp <= hi) ? 2 : 1
  }
  return n
}

type Node = { type?: unknown; props?: Record<string, unknown>; children?: unknown }

const kids = (n: Node): unknown[] => (Array.isArray(n.children) ? (n.children as unknown[]).flat(Infinity) : n.children === undefined || n.children === null ? [] : [n.children])
const isNode = (v: unknown): v is Node => v !== null && typeof v === 'object' && !Array.isArray(v)

// One drawn line: its text, where it starts and ends, the right edge of the box that holds it, and
// its style when one span draws it all.
export type Placed = { text: string; left: number; right: number; limit: number; spans: number; bold: boolean; dim: boolean; color: string | undefined }
export type PlacedBox = { left: number; right: number; limit: number; border: boolean; direction: string; boxes: number }
export type Layout = { lines: Placed[]; boxes: PlacedBox[]; types: string[]; colors: string[]; rows: number }

// Every string inside a Text, in order, nested Texts included.
function textOf(n: Node): string {
  return kids(n).map(k => (typeof k === 'string' ? k : isNode(k) ? textOf(k) : '')).join('')
}

// The spans of a line: the nested Texts, or the line itself when it holds only strings.
function spansOf(n: Node): Node[] {
  const nested = kids(n).filter(isNode)
  return nested.length > 0 ? nested : [n]
}

export function layout(tree: unknown, width: number): Layout {
  const out: Layout = { lines: [], boxes: [], types: [], colors: [], rows: 0 }
  // Returns the rows the node takes.
  const walk = (v: unknown, left: number, limit: number): number => {
    if (!isNode(v)) return 0
    const p = v.props ?? {}
    out.types.push(String(v.type))
    for (const key of ['color', 'borderColor']) if (p[key] !== undefined) out.colors.push(String(p[key]))
    if (v.type === 'Text') {
      for (const k of kids(v)) if (isNode(k)) walk(k, left, limit)
      return 0
    }
    if (v.type !== 'Box') return 0
    const w = typeof p.width === 'number' ? p.width : limit - left
    const right = left + w
    const border = p.borderStyle !== undefined
    const pad = typeof p.paddingX === 'number' ? p.paddingX : 0
    const direction = p.flexDirection === 'column' ? 'column' : 'row'
    out.boxes.push({ left, right, limit, border, direction, boxes: kids(v).filter(k => isNode(k) && k.type === 'Box').length })
    const inLeft = left + (border ? 1 : 0) + pad
    const inRight = right - (border ? 1 : 0) - pad
    let rows = 0
    let x = inLeft
    const gap = typeof p.columnGap === 'number' ? p.columnGap : 0
    for (const k of kids(v)) {
      if (!isNode(k)) continue
      if (k.type === 'Text') {
        const text = textOf(k)
        const spans = spansOf(k)
        const one = spans.length === 1 ? spans[0]!.props ?? {} : {}
        out.lines.push({
          text, left: inLeft, right: inLeft + coarseCells(text), limit: inRight, spans: spans.length,
          bold: one.bold === true, dim: one.dimColor === true, color: typeof one.color === 'string' ? one.color : undefined,
        })
        for (const s of kids(k)) if (isNode(s)) walk(s, inLeft, inRight)
        out.types.push('Text')
        for (const key of ['color', 'borderColor']) if (k.props?.[key] !== undefined) out.colors.push(String(k.props[key]))
        if (direction === 'column') rows += 1
        else rows = Math.max(rows, 1)
        continue
      }
      if (direction === 'row') {
        const kw = typeof k.props?.width === 'number' ? (k.props.width as number) : 0
        rows = Math.max(rows, walk(k, x, x + kw))
        x += kw + gap
      } else {
        rows += walk(k, inLeft, inRight)
      }
    }
    return rows + (border ? 2 : 0)
  }
  out.rows = walk(tree, 0, width)
  return out
}

// The widest right edge of any line or box in a drawn tree.
export const widest = (l: Layout): number => Math.max(0, ...l.lines.map(x => x.right), ...l.boxes.map(b => b.right))

// Every line or box that passes the edge of the box holding it.
export const overflows = (l: Layout): string[] => [
  ...l.lines.filter(x => x.right > x.limit).map(x => `line ${JSON.stringify(x.text)} ends at ${x.right} past ${x.limit}`),
  ...l.boxes.filter(b => b.right > b.limit).map(b => `box ends at ${b.right} past ${b.limit}`),
]

// Each drawn line's text and, when one span draws it, that span's style: the rows a reader sees.
export type Row = { text: string; bold: boolean; dim: boolean; color: string | undefined }
export const rowsOf = (tree: unknown, width = 400): Row[] => layout(tree, width).lines.map(({ text, bold, dim, color }) => ({ text, bold, dim, color }))

// True when the tree lays two Boxes side by side: a row Box holding two or more Boxes.
export const twoColumns = (l: Layout): boolean => l.boxes.some(b => b.direction === 'row' && b.boxes >= 2)
