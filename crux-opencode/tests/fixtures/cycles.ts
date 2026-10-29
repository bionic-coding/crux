// A cycle-progress document with a chosen number of closed cycles, for the tests that page the
// `cycles:` list. The numbers of rows and pages come from the core's OLDER_PAGE_SIZE, never from a
// copy of it, so a change of the page size moves these fixtures with it.
import { readView } from '../../lib/render.ts'
import type { PlainNode, PlainSpan } from '../../lib/render.ts'
import { OLDER_PAGE_SIZE } from '../../../crux-mods/hooks/lib/draw.ts'
import type { Parsed } from '../../../crux-mods/hooks/lib/view.ts'
import { jsonText } from './plain.ts'

const PHASES = ['plan', 'build', 'test', 'review', 'reflect']

export const cycleRow = (n: number, status = 'completed') => ({
  id: `CYC-${String(n).padStart(4, '0')}`, title: `Cycle title ${n}`, type: 'iterate', status, phase: 'build', pass: 1, pass_limit: 2,
  phases: PHASES,
  tasks: [
    { id: 'a', phase: 'plan', description: 'Plan it', status: 'done' },
    { id: 'b', phase: 'build', description: `Current work ${n}`, status: status === 'active' ? 'active' : 'done' },
  ],
  returns: [], waits: [], blocker: null, reflection: null, modified_s: 1780000000,
  started_s: 1779999000, ended_s: status === 'active' || status === 'paused' ? null : 1779999900, paused_s: 0,
  open_started_s: status === 'active' || status === 'paused' ? 1779999500 : null, basis: 'recorded',
  phase_times: [{ phase: 'plan', active_s: 500, paused_s: 0 }],
})

export const qItem = (n: number, state: string) => ({
  id: `Q-${String(n).padStart(4, '0')}`, title: `Queue title ${n}`, state, suggested_type: 'iterate', cycle: null, cycle_status: null,
})

export const doc = (cycles: unknown[], queue?: unknown) => ({
  format: 'crux.cycle-progress', format_version: 2, ok: true, docs_dir: 'bionic', now_s: 1780000000, cycles,
  ...(queue === undefined ? {} : { queue }),
})

export const parsedOf = (d: unknown): Parsed => {
  const p = readView(true, () => ({ ok: true, stdout: jsonText(d) }))
  if (p === null || !p.ok) throw new Error('the document did not read as a view')
  return p
}

export const rowsOf = (n: PlainNode | null): PlainSpan[][] => {
  if (n === null || n.kind === 'spacer') return []
  return n.kind === 'text' ? [n.spans] : n.children.flatMap(rowsOf)
}
export const plain = (r: PlainSpan[]) => r.map(s => s.text).join('')

// n closed cycles, newest first: CYC-n is the latest (it draws as a panel), the others are list rows.
export const closed = (n: number) => Array.from({ length: n }, (_, i) => cycleRow(n - i))

// The closed cycles of a view whose `cycles:` list holds exactly `pages` pages, the last one holding
// a single row: the latest closed cycle plus (pages - 1) * OLDER_PAGE_SIZE + 1 list rows. The reader
// accepts at most 60 cycles, so a read view holds at most six pages.
export const closedForPages = (pages: number) => 1 + (pages - 1) * OLDER_PAGE_SIZE + 1
export const withPages = (pages: number): Parsed => parsedOf(doc(closed(closedForPages(pages))))
