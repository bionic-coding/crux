// The dashboard's drawing: closed maps from reader values to glyphs, words and theme keys, and the
// pure builders that turn a checked reader view into lines of styled spans. Nothing here calls `$`
// or reads a clock, and nothing here computes with a time: every time a line shows, and every lane
// cell, comes from view.ts's time functions, which compute from the reader's now_s and the reader's
// own times. The hooks module turns a block into Box and Text elements and draws nothing else.
//
// Three kinds of drawn value. A glyph, a word or a theme key comes from a reader value or an
// agent-list field through a closed map below, or is a constant of the mod; a value a map does not
// recognise draws as the visible unknown cell `?`. A number is computed from the inputs. Every other
// value is free text, and it reaches a line only through drawn(): the removal of view.ts's
// safeText, then a cut to a display width.
import type { Agents, Council, Escalation, Gate, Parsed, Prompt, ReaderView, RunView, Time } from './view.ts'
import {
  COUNCIL_KINDS, ESCALATION_NOTE, MAX_SHOWN_RUNS, QUIET, ROUTE_ACTIONS, RUN_STATUS, STATES, bandRun, counted, currentEscalation,
  currentPrompt, escalationText, laneCells, lastRunAge, openElapsed, promptBounds, promptSpan, runAxis, runTimes, safeText, stallIdle,
} from './view.ts'
import { ELLIPSIS, MAX_WIDTH, cells, drawingWidth, fit, head, wrap } from './width.ts'

// --- theme keys, spans and lines ----------------------------------------------------------

// The theme keys the dashboard draws with: the keys Flightdeck v0.4.0 draws, plus `error`. A
// colour is always one of these, never a literal value, and every distinction a colour draws is
// also drawn by a glyph or a word.
export const THEME_KEYS = ['claude', 'suggestion', 'success', 'permission', 'merged', 'warning', 'error', 'inactive', 'subtle', 'text'] as const
export type ThemeKey = (typeof THEME_KEYS)[number]

// One run of text in one style. A line is a list of spans, drawn as one Text holding a Text per span.
export type Span = { text: string; color?: ThemeKey; bold?: boolean; dim?: boolean }
export type Line = Span[]

const span = (text: string, style: Omit<Span, 'text'> = {}): Span => ({ text, ...style })

// The cells a line takes.
export const lineCells = (line: Line): number => line.reduce((n, s) => n + cells(s.text), 0)

// The line whole when it takes at most n cells, else its longest head of at most n-1 cells and an
// ellipsis in the style of the span it cuts. Every line the dashboard draws passes through this.
export function fitLine(line: Line, n: number): Line {
  if (lineCells(line) <= n) return line
  if (n < 1) return []
  const out: Line = []
  let left = n - 1
  for (const s of line) {
    const w = cells(s.text)
    if (w <= left) {
      out.push(s)
      left -= w
      continue
    }
    out.push({ ...s, text: head(s.text, left) + ELLIPSIS })
    return out
  }
  return out
}

// The line with each run of adjacent spans in one style made one span. A drawn line holds a Text per
// span, so this keeps a drawing's element count near its line count.
export function merged(line: Line): Line {
  const out: Line = []
  for (const s of line) {
    if (s.text === '' && line.length > 1) continue
    const last = out[out.length - 1]
    if (last !== undefined && last.color === s.color && last.bold === s.bold && last.dim === s.dim) out[out.length - 1] = { ...last, text: last.text + s.text }
    else out.push(s)
  }
  return out
}

// Spans joined with a gap of plain spaces between non-empty parts.
export function joined(parts: Line[], gap = '  '): Line {
  const out: Line = []
  for (const p of parts) {
    if (p.length === 0) continue
    if (out.length > 0) out.push(span(gap))
    out.push(...p)
  }
  return out
}

// --- free text ------------------------------------------------------------------------------

// The one entry point for free text: the removal first, then the cut to n cells with an ellipsis.
export const drawn = (s: string, n: number = MAX_WIDTH): string => fit(safeText(s), n)

// --- closed maps ----------------------------------------------------------------------------

// A map lookup that never reaches a key inherited from Object.prototype.
function own<T>(map: Readonly<Record<string, T>>, key: string): T | undefined {
  return Object.prototype.hasOwnProperty.call(map, key) ? map[key] : undefined
}

export const UNKNOWN = '?'

// A prompt's or a gate's state. Every glyph in this file is East Asian Narrow or Neutral and none is
// an emoji, so each takes one cell on every terminal the tests describe.
export const STATE_GLYPHS: Readonly<Record<string, string>> = {
  done: '\u{2713}', // check mark
  blocked: '\u{2717}', // ballot x
  running: '\u{25B8}', // black right-pointing small triangle
  pending: '\u{25CC}', // dotted circle
  skipped: '\u{2298}', // circled division slash
}

// A seat's decision in a council record.
export const DECISION_GLYPHS: Readonly<Record<string, string>> = {
  APPROVE: '\u{2713}',
  APPROVE_WITH_NITS: '~',
  REQUEST_CHANGES: '\u{2717}',
  REJECT: '\u{2297}', // circled times
  ARCHITECTURAL: '\u{2B26}', // white medium diamond
  DEFER_TO_HUMAN: '\u{2296}', // circled minus
}
// The words the legend gives each decision glyph.
export const DECISION_WORDS: Readonly<Record<string, string>> = {
  APPROVE: 'approve', APPROVE_WITH_NITS: 'nits', REQUEST_CHANGES: 'changes', REJECT: 'reject', ARCHITECTURAL: 'architectural', DEFER_TO_HUMAN: 'defer',
}

// The grid's cells that are not a decision: a seat with no decision, an errored seat, a role the
// record does not seat, and every cell of a council that could not run.
export const SEAT_CELLS = { none: '-', errored: '!', absent: '.', notRun: '\u{2205}' } as const

// An agent's status in the engine's agent list.
export const AGENT_GLYPHS: Readonly<Record<string, string>> = { running: '\u{25B8}', completed: '\u{2713}', failed: '\u{2717}' }

// The progress bar's filled and empty cells, and the strip's group separator.
export const BAR_ON = '\u{25AE}' // black vertical rectangle
export const BAR_OFF = '\u{25AF}' // white vertical rectangle
export const GROUP_SEP = '|'

// A module kind: the word that names it and the theme key it is drawn in. The key comes from the
// module tag's prefix, the promptbook schema's closed set.
export type Kind = { word: string; color: ThemeKey }
export const KINDS: Readonly<Record<string, Kind>> = {
  adr: { word: 'adr', color: 'merged' },
  implementation: { word: 'implementation', color: 'permission' },
  dev: { word: 'dev', color: 'claude' },
  review: { word: 'review', color: 'suggestion' },
  verify: { word: 'verify', color: 'success' },
}
// A prompt with no module tag, such as every prompt of a patch book.
export const UNTAGGED: Kind = { word: 'untagged', color: 'inactive' }
export const UNKNOWN_KIND: Kind = { word: UNKNOWN, color: 'text' }

// A gate's class, as the word the gate strip draws.
export const GATE_WORDS: Readonly<Record<string, string>> = { council: 'council', 'module-close': 'module-close', 'independent-review': 'review' }

export const stateGlyph = (state: string): string => own(STATE_GLYPHS, state) ?? UNKNOWN
export const decisionGlyph = (d: string | null): string => (d === null ? SEAT_CELLS.none : own(DECISION_GLYPHS, d) ?? UNKNOWN)
export const agentGlyph = (status: string): string => own(AGENT_GLYPHS, status) ?? UNKNOWN
export const gateWord = (cls: string): string => own(GATE_WORDS, cls) ?? UNKNOWN
// A closed-set token drawn as itself when it is a member, else the unknown cell.
const member = (v: string | null, set: readonly string[]): string => (v === null ? 'none' : set.includes(v) ? v : UNKNOWN)

const TAG_PREFIX = /^([a-z]+)-\d+$/
export function kindOf(tag: string | null): Kind {
  if (tag === null) return UNTAGGED
  const m = TAG_PREFIX.exec(tag)
  return (m !== null && m[1] !== undefined ? own(KINDS, m[1]) : undefined) ?? UNKNOWN_KIND
}

// The error key marks a blocked or refused cell; the glyph already says so.
const BAD_GLYPHS: readonly string[] = ['\u{2717}', '\u{2297}']
const glyphSpan = (g: string): Span => (BAD_GLYPHS.includes(g) ? span(g, { color: 'error' }) : g === UNKNOWN ? span(g, { color: 'warning' }) : span(g))

// --- the legend ------------------------------------------------------------------------------

// One line naming the module kinds and the state glyphs. Its entries, in priority order: the state
// glyphs the runs use, the kinds the runs use, the decision glyphs their councils use that no state
// shares, then the state glyphs they do not use. A legend that does not fit drops whole entries
// from its tail.
export function legendLine(runs: RunView[], n: number): Line {
  const used = new Set(runs.flatMap(r => r.prompts.map(p => p.state as string)))
  const kinds: Kind[] = []
  for (const r of runs) for (const p of r.prompts) {
    const k = kindOf(p.module_tag)
    if (!kinds.some(x => x.word === k.word)) kinds.push(k)
  }
  const decisions: string[] = []
  for (const r of runs) for (const c of r.councils) for (const s of c.seats) {
    const g = s.decision === null ? undefined : own(DECISION_GLYPHS, s.decision)
    if (g !== undefined && !Object.values(STATE_GLYPHS).includes(g) && !decisions.includes(s.decision!)) decisions.push(s.decision!)
  }
  const entries: Line[] = [
    ...STATES.filter(s => used.has(s)).map(s => [glyphSpan(stateGlyph(s)), span(` ${s}`, { dim: true })]),
    ...kinds.map(k => [span(k.word, { color: k.color })]),
    ...decisions.map(d => [glyphSpan(decisionGlyph(d)), span(` ${own(DECISION_WORDS, d)}`, { dim: true })]),
    ...STATES.filter(s => !used.has(s)).map(s => [glyphSpan(stateGlyph(s)), span(` ${s}`, { dim: true })]),
  ]
  const kept: Line[] = []
  for (const e of entries) {
    if (lineCells(joined([...kept, e])) > n) break
    kept.push(e)
  }
  return joined(kept)
}

// --- the prompt strip -------------------------------------------------------------------------

// Consecutive prompts with the same module tag form one group.
export type Group = { kind: Kind; from: number; to: number }
export function groupsOf(prompts: Prompt[]): Group[] {
  const out: Group[] = []
  prompts.forEach((p, i) => {
    const last = out[out.length - 1]
    if (last !== undefined && prompts[last.from]!.module_tag === p.module_tag) last.to = i
    else out.push({ kind: kindOf(p.module_tag), from: i, to: i })
  })
  return out
}

// The cell a strip keeps first: the current prompt, else the last prompt that is not pending, else
// the first.
export function stripAnchor(r: RunView): number {
  const cur = currentPrompt(r)
  if (cur !== undefined) return r.prompts.indexOf(cur)
  for (let i = r.prompts.length - 1; i >= 0; i--) if (r.prompts[i]!.state !== 'pending') return i
  return 0
}

// The k cells nearest the anchor, as a half-open range of indexes. A tie keeps the earlier cell.
export function window(total: number, anchor: number, k: number): [number, number] {
  const kk = Math.max(0, Math.min(k, total))
  const lo = Math.max(0, Math.min(anchor - Math.ceil((kk - 1) / 2), total - kk))
  return [lo, lo + kk]
}

// The cells of one window of a strip, with a separator where a group ends inside it.
function stripCells(prompts: Prompt[], lo: number, hi: number): Line {
  const out: Line = []
  for (let i = lo; i < hi; i++) {
    if (i > lo && prompts[i]!.module_tag !== prompts[i - 1]!.module_tag) out.push(span(GROUP_SEP, { dim: true }))
    out.push(glyphSpan(stateGlyph(prompts[i]!.state)))
  }
  return out
}

// A glyph row cut to n cells: the k cells nearest the anchor for the largest k that fits, then `+N`
// for the N cells it leaves out, or an ellipsis when `+N` does not fit. `sep` goes before the count.
// Empty when no cell fits.
function fitCells(total: number, anchor: number, n: number, cellsOf: (lo: number, hi: number) => Line, sep = ''): Line {
  for (const mark of ['count', 'ellipsis'] as const) {
    for (let k = total; k >= 1; k--) {
      const [lo, hi] = window(total, anchor, k)
      const rest = total - k
      const tail = rest === 0 ? [] : [span(sep + (mark === 'count' ? `+${rest}` : ELLIPSIS), { dim: true })]
      const line = [...cellsOf(lo, hi), ...tail]
      if (lineCells(line) <= n) return line
    }
  }
  return []
}

// The strip with no words: a cell per prompt and a separator between groups, cut to n cells.
export function compactStrip(r: RunView, n: number): Line {
  return fitCells(r.prompts.length, stripAnchor(r), n, (lo, hi) => stripCells(r.prompts, lo, hi))
}

// The strip with each group labelled by its kind word, in the kind's colour, or null when it does
// not fit n cells. A cell takes no kind colour: the word beside it carries the kind.
export function labelledStrip(r: RunView, n: number): Line | null {
  const parts = groupsOf(r.prompts).map(g => [span(g.kind.word, { color: g.kind.color }), span(' '), ...stripCells(r.prompts, g.from, g.to + 1)])
  const line = joined(parts)
  return lineCells(line) <= n ? line : null
}

// The kind of the current prompt's group, or undefined without a current prompt.
export const currentKind = (r: RunView): Kind | undefined => {
  const cur = currentPrompt(r)
  return cur === undefined ? undefined : kindOf(cur.module_tag)
}

// The pane's strip line: labelled when it fits; else the current group's word and the compact strip.
export function stripLine(r: RunView, n: number): Line {
  if (r.prompts.length === 0) return []
  const labelled = labelledStrip(r, n)
  if (labelled !== null) return labelled
  const k = currentKind(r)
  if (k !== undefined) {
    const word = [span(k.word, { color: k.color })]
    const rest = compactStrip(r, n - lineCells(word) - 1)
    if (rest.length > 0) return [...word, span(' '), ...rest]
  }
  return compactStrip(r, n)
}

// --- the progress bar -------------------------------------------------------------------------

export const BAR_WIDTH = 20
// The share of terminal prompts as filled cells out of `width`, from the reader's percentage.
export function bar(pct: number, width: number): Line {
  const w = Math.max(0, Math.min(width, BAR_WIDTH))
  const on = Math.max(0, Math.min(w, Math.round((pct * w) / 100)))
  return w === 0 ? [] : [span(BAR_ON.repeat(on)), span(BAR_OFF.repeat(w - on), { dim: true })]
}

// --- the council grid ---------------------------------------------------------------------------

const pad = (s: string, n: number) => s + ' '.repeat(Math.max(0, n - cells(s)))

// The cell a seat role takes in one council record.
export function seatCell(c: Council, role: string): string {
  if (c.outcome === 'could-not-run') return SEAT_CELLS.notRun
  const s = c.seats.find(x => x.role === role)
  if (s === undefined) return SEAT_CELLS.absent
  if (s.errored) return SEAT_CELLS.errored
  return decisionGlyph(s.decision)
}

const recordLabel = (c: Council) => `p${c.prompt}r${c.round}`
// The label of the one row a grid draws when no record seats anyone.
export const NO_SEATS = 'seats'

// One row per seat role and one column per council record, the newest last: a header line naming
// each record, a line per role, and a footer for the newest record with its aggregate and whether
// it converged. A grid that does not fit keeps the newest records and counts the rest as `+N`.
export function councilGrid(councils: Council[], n: number): Line[] {
  if (councils.length === 0) return []
  const roles: string[] = []
  for (const c of councils) for (const s of c.seats) if (!roles.includes(s.role)) roles.push(s.role)
  // Records that seat no one, such as councils that could not run, still draw one row of cells.
  if (roles.length === 0) roles.push(NO_SEATS)
  const labelWidth = Math.min(Math.max(0, ...roles.map(r => cells(drawn(r)))), Math.max(4, Math.floor(n / 3)))
  // How many of the newest records fit beside the label column and a `+N` count.
  let shown = councils.length
  const widthOf = (k: number) => {
    const cols = councils.slice(councils.length - k)
    const rest = councils.length - k
    return labelWidth + cols.reduce((w, c) => w + 1 + cells(recordLabel(c)), 0) + (rest > 0 ? 1 + cells(`+${rest}`) : 0)
  }
  while (shown > 1 && widthOf(shown) > n) shown--
  const cols = councils.slice(councils.length - shown)
  const rest = councils.length - shown
  const lines: Line[] = []
  const header: Line = [span(pad('', labelWidth))]
  for (const c of cols) header.push(span(' ' + recordLabel(c), { dim: true }))
  if (rest > 0) header.push(span(` +${rest}`, { dim: true }))
  lines.push(header)
  for (const role of roles) {
    const line: Line = [span(pad(drawn(role, labelWidth), labelWidth))]
    for (const c of cols) {
      line.push(span(' '))
      line.push(glyphSpan(seatCell(c, role)))
      line.push(span(' '.repeat(cells(recordLabel(c)) - 1)))
    }
    lines.push(line)
  }
  const last = councils[councils.length - 1]!
  const notes = [
    `p${last.prompt} r${last.round}`, member(last.kind, COUNCIL_KINDS),
    last.outcome === 'could-not-run' ? 'could not run' : last.quorum_met ? '' : 'quorum not met',
    last.degraded ? 'degraded' : '', member(last.aggregate, ROUTE_ACTIONS), last.converged ? 'converged' : 'not converged',
  ].filter(s => s !== '')
  lines.push([span(notes.join('  '), { dim: true })])
  return lines.map(l => fitLine(l, n))
}

// --- the gate strip -----------------------------------------------------------------------------

const gateEntry = (g: Gate): Line => [glyphSpan(stateGlyph(g.state)), span(` p${g.n} ${gateWord(g.gate_class)}`)]

// The gate that anchors the strip: the last one that is not pending, else the first.
export function gateAnchor(gates: Gate[]): number {
  for (let i = gates.length - 1; i >= 0; i--) if (gates[i]!.state !== 'pending') return i
  return 0
}

// Each gate as its state glyph, its prompt and its class word, cut to n cells around the anchor.
export function gateStrip(gates: Gate[], n: number): Line {
  if (gates.length === 0) return []
  return fitCells(gates.length, gateAnchor(gates), n, (lo, hi) => joined(gates.slice(lo, hi).map(gateEntry)), '  ')
}

// --- agents and statuses ------------------------------------------------------------------------

// A line per agent the engine lists, or one line when the list cannot be read. A readable list with
// no agent has no line, so its panel takes no room.
export function agentLines(ag: Agents, n: number): Line[] {
  if (!ag.available) return [[span('agents unavailable', { dim: true })]]
  return ag.shown.map(a => fitLine(joined([[glyphSpan(agentGlyph(a.status))], [span(drawn(a.type, n))], [span(drawn(a.description, n))]].filter(p => p[0]!.text !== '')), n))
}

// A status: its prefix and its code when both fit, else the code alone, else the code cut to n cells.
export function statusLine(prefix: string, code: string, n: number, style: Omit<Span, 'text'> = { color: 'error' }): Line {
  const c = drawn(code)
  const whole = prefix + c
  if (cells(whole) <= n) return [span(whole, style)]
  return [span(fit(c, n), style)]
}

// --- wrapped text ---------------------------------------------------------------------------------

// Text wrapped at spaces into lines of at most n cells. A word wider than n is cut into chunks.
export function wrapWords(s: string, n: number): string[] {
  const out: string[] = []
  let cur = ''
  for (const word of s.split(' ')) {
    const next = cur === '' ? word : `${cur} ${word}`
    if (cells(next) <= n) {
      cur = next
      continue
    }
    if (cur !== '') out.push(cur)
    const chunks = cells(word) <= n ? [word] : wrap(word, n)
    out.push(...chunks.slice(0, -1))
    cur = chunks[chunks.length - 1] ?? ''
  }
  if (cur !== '' || out.length === 0) out.push(cur)
  return out
}

// --- the time axis ----------------------------------------------------------------------------------

export const LANE_FILL = '\u{25AC}' // black rectangle
export const LANE_TRACK = '.'
export const NO_START = 'no start'
// A lane draws with at least LANE_MIN cells and grows with the width to LANE_MAX cells.
export const LANE_MIN = 10
export const LANE_MAX = 120
// A run of more prompts than this draws the withheld word in place of its lanes.
export const MAX_LANES = 100
// The word a run panel draws where its lanes would be when it withholds them.
export const LANES_WITHHELD = 'lanes withheld'

// What a run panel draws on the time axis: its lanes, or the withheld word in their place. In phase1
// mode, past the pane's budget, a panel draws its rows as the pane drew them before the time axis:
// no lane output, the times on one row, and each prompt row cut at its tail.
export type LaneMode = 'draw' | 'withhold' | 'phase1'

// A run's lane rows: one per prompt on the run's axis. None in phase1 mode, without an axis, or below
// LANE_MIN lane cells, where the text durations stand alone, so a run with no lane output draws no
// word in any mode. The withheld word for a run of more than MAX_LANES prompts, or in withhold mode.
export function laneLines(r: RunView, now: Time, n: number, mode: LaneMode = 'draw'): Line[] {
  if (mode === 'phase1') return []
  const axis = runAxis(r, now)
  if (axis === null || r.prompts.length === 0) return []
  const labelW = Math.max(...r.prompts.map(p => cells(`p${p.n}`)))
  const L = Math.min(n - labelW - 1, LANE_MAX)
  if (L < LANE_MIN) return []
  if (mode === 'withhold' || r.prompts.length > MAX_LANES) return [[span(LANES_WITHHELD, { dim: true })]]
  return r.prompts.map(pr => {
    const label = span(pad(`p${pr.n}`, labelW) + ' ')
    if (pr.started_s === null) return [label, span(NO_START, { dim: true })]
    const b = promptBounds(pr, r, now)
    const c = b === null ? null : laneCells(axis, b, L)
    if (c === null) return [label, span(LANE_TRACK.repeat(L), { dim: true })]
    const [lo, hi] = c
    return [label, span(LANE_TRACK.repeat(lo), { dim: true }), span(LANE_FILL.repeat(hi - lo - 1)), glyphSpan(stateGlyph(pr.state)), span(LANE_TRACK.repeat(L - hi), { dim: true })]
  })
}

// --- the run's rows -------------------------------------------------------------------------------

// The marker of the prompt a live run is on: a glyph, never the colour alone.
export const CURRENT_MARK = '\u{25B8} '

// A run's book id and run id: free text, though the reader checks both against a pattern.
const ids = (r: RunView) => `${drawn(r.book_id)} ${drawn(r.run_id)}`
const position = (r: RunView) => (r.current_prompt === null ? `prompt none of ${r.total}` : `p${r.current_prompt}/${r.total}`)

function headerLine(r: RunView): Line {
  return [span(`${ids(r)}  ${member(r.status, RUN_STATUS)}  prompt ${r.current_prompt === null ? 'none' : r.current_prompt} of ${r.total}  ${r.pct}%`, { bold: true })]
}

// A prompt row ends with its duration, or in a run in progress with its elapsed time by the open
// rule. The prompt a live run is on is bold and marked; a blocked one is in the error key, and says
// blocked. A row wider than n keeps its duration whole: the tag and the title give way first, the
// title before the tag.
function promptLine(pr: Prompt, r: RunView, now: Time, live: boolean, n: number): Line {
  const took = promptSpan(pr, r, now)
  const head = `${live && r.current_prompt === pr.n ? CURRENT_MARK : ''}p${pr.n}  ${member(pr.state, STATES)}`
  const body = `${pr.module_tag === null ? '' : drawn(pr.module_tag) + '  '}${drawn(pr.title)}`
  const tail = took === null ? '' : `  ${took}`
  const room = n - cells(head) - 2 - cells(tail)
  const text = took === null || room >= cells(body) ? `${head}  ${body}${tail}` : room >= 1 ? `${head}  ${fit(body, room)}${tail}` : `${head}${tail}`
  const blocked = pr.state === 'blocked'
  if (live && r.current_prompt === pr.n) return [span(text, blocked ? { bold: true, color: 'error' } : { bold: true })]
  return [span(text, blocked ? { color: 'error' } : {})]
}

// Parts joined by two spaces into rows of at most n cells, each part whole on one row.
function packed(parts: string[], n: number): string[] {
  const rows: string[] = []
  for (const p of parts) {
    const joinedRow = rows.length === 0 ? null : `${rows[rows.length - 1]}  ${p}`
    if (joinedRow !== null && cells(joinedRow) <= n) rows[rows.length - 1] = joinedRow
    else rows.push(p)
  }
  return rows
}

const dimLines = (texts: string[]): Line[] => texts.map(t => [span(t, { dim: true })])

const stallFull = (idle: string) => `run file unchanged ${idle}, no subagent running in this session`
const stallShort = (idle: string) => `stalled ${idle}`
const escalationShort = (e: Escalation) => `escalation p${e.prompt} r${e.round}`

// One run's rows inside its panel, n cells wide: the header, the grouped strip, the bar, the times
// rows, the lanes or the withheld word, the counts, the stall and the escalations with their notes,
// every prompt, and the refused files. In phase1 mode the times stand on one row and each prompt row
// is cut at its tail, with no lane output.
export function runLines(r: RunView, v: ReaderView, ag: Agents, live: boolean, n: number, harness: Harness, lanes: LaneMode = 'draw'): Line[] {
  const room = lanes === 'phase1' ? Infinity : n
  const lines: Line[] = [headerLine(r)]
  const strip = stripLine(r, n)
  if (strip.length > 0) lines.push(strip)
  if (r.total > 0) lines.push(bar(r.pct, n))
  for (const t of packed(runTimes(r, v.now_s), room)) lines.push([span(t, { dim: true })])
  lines.push(...laneLines(r, v.now_s, n, lanes))
  lines.push([span(`done ${r.counts.done}  skipped ${r.counts.skipped}  blocked ${r.counts.blocked}  running ${r.counts.running}  pending ${r.counts.pending}`, { dim: true })])
  const idle = live ? stallIdle(r, v.now_s, ag) : null
  if (idle !== null) {
    lines.push([span(stallFull(idle), { color: 'error' })])
    lines.push(...dimLines(wrapWords(harness.stallNote, n)))
  }
  if (live) {
    for (const e of r.escalations) lines.push([span(escalationText(e), { color: 'error' })])
    if (r.escalations.length > 0) lines.push(...dimLines(wrapWords(ESCALATION_NOTE, n)))
  }
  for (const pr of r.prompts) lines.push(promptLine(pr, r, v.now_s, live, room))
  lines.push([span(`refused council files ${r.councils_skipped}`, { dim: true })])
  return lines
}

// The most summary rows the pane draws. Claude Code's test kit (2.1.299) refuses a drawing of more
// than 20000 nodes and draws its own instead. The reader's largest summary, 32000 two-cell
// characters, wraps to 4562 rows at 15 columns, and more below; with the cap a pane one column wide
// stays near 12000 nodes. At 18 columns and wider no summary the reader admits passes 4000 rows.
// At 16 and 17 columns a summary of many short lines can. The cap says how many rows it cut.
export const MAX_SUMMARY_ROWS = 4000

// The summary of the last run: each line after the removal, wrapped by cells, never splitting a
// two-cell character. A line with nothing left draws one empty row.
function summaryLines(lines: string[], truncated: boolean, n: number): Line[] {
  if (lines.length === 0 && !truncated) return []
  const rows: Line[] = []
  for (const line of lines) {
    const safe = safeText(line)
    if (safe === '') rows.push([span('')])
    else for (const chunk of wrap(safe, n)) rows.push([span(drawn(chunk, n))])
  }
  const cut = rows.length - MAX_SUMMARY_ROWS
  const out: Line[] = [[span('Summary', { bold: true })], ...rows.slice(0, MAX_SUMMARY_ROWS)]
  if (cut > 0) out.push([span(`+${cut} more summary rows`, { dim: true })])
  if (truncated) out.push([span('summary truncated', { dim: true })])
  return out
}

const lastRunTitle = (v: ReaderView) =>
  v.last_completed_status === 'latest-dated' ? `Last dated run, ${counted(v.last_completed_undated, 'completed run', 'completed runs')} undated` : 'Last run'

// The sentence the pane draws when no run is listed and the last run cannot be shown, or null.
function idleSentence(v: ReaderView): Line | null {
  const undated = counted(v.last_completed_undated, 'completed run', 'completed runs')
  if (v.last_completed_status === 'undetermined') {
    if (v.last_completed_unresolved > 0) {
      const unresolved = counted(v.last_completed_unresolved, 'run entry', 'run entries')
      return [span(`Last run not shown: ${unresolved} unresolved, ${undated} undated; a run in progress or a newer completed run cannot be ruled out.`)]
    }
    return [span(`Last run not shown: no completed run carries a valid completion time (${v.last_completed_undated} undated).`)]
  }
  if (v.last_completed_status === 'run-in-progress') return [span('A run is in progress, but the reader refused its view.', { color: 'error' })]
  return null
}

// A one-span line wrapped at spaces, each piece keeping the span's style.
function wrapLine(line: Line, n: number): Line[] {
  const { text: _, ...style } = line[0] ?? { text: '' }
  return wrapWords(line.map(s => s.text).join(''), n).map(t => [span(t, style)])
}

// The run panel's rows when no run is listed: the last run with its summary, or the one sentence
// that says why it is not shown. Nothing in target mode with no listed run.
export function idleLines(v: ReaderView, ag: Agents, n: number, harness: Harness, lanes: LaneMode = 'draw'): Line[] {
  const r = v.last_completed
  if (r !== null) return [[span(lastRunTitle(v), { bold: true })], ...runLines(r, v, ag, false, n, harness, lanes), ...summaryLines(r.summary, r.summary_truncated, n)]
  const sentence = idleSentence(v)
  return sentence === null ? [] : wrapLine(sentence, n)
}

const readerLine = (v: ReaderView): Line => [span(`reader ${drawn(v.reader_version)}  refused run files ${v.runs_skipped}`, { dim: true })]
const moreRuns = (k: number): Line => [span(`+${k} more run${k === 1 ? '' : 's'}`, { dim: true })]

// --- blocks: what the hooks module draws ------------------------------------------------------------

// A line of spans, or a box of blocks. The hooks module draws a line as one Text holding a Text per
// span, and a box as a Box: round-bordered with one cell of padding when it names a border key.
export type Block =
  | { kind: 'line'; line: Line }
  | { kind: 'box'; direction: 'column' | 'row'; width: number; border: ThemeKey | null; gap: number; children: Block[] }

// Below this width the panels drop their borders.
export const BORDER_MIN = 40
// From this width a pane that is not inline draws two columns.
export const TWO_COLUMNS_MIN = 110
// The most rows the mini layout draws, its borders, its legend and its `+N more` row included.
export const MINI_ROWS = 8
export const COLUMN_GAP = 2
// A bordered panel's border and padding take two cells on each side.
export const PANEL_FRAME = 4
// Borders draw in one neutral key, so no border colour stands for anything.
export const PANEL_BORDER: ThemeKey = 'subtle'
// The band draws this gap between segments.
export const SEGMENT_GAP = '  '

// The values the importing package passes in: the prefix of the band's status line, which says
// which plugin drew it, and the note under a stalled run, which says what the agent list cannot see.
export type Harness = { bandPrefix: string; stallNote: string }
// The pane's two layouts: a short one for a small region, and the full one.
export type PaneLayout = 'mini' | 'docked'

const PANE_STATUS = 'Dashboard unavailable: '

const lineBlock = (line: Line, n: number): Block => ({ kind: 'line', line: merged(fitLine(line, n)) })
const columnBox = (width: number, children: Block[], border: ThemeKey | null = null): Block => ({ kind: 'box', direction: 'column', width, border, gap: 0, children })

// A panel: its lines, each fitted to the inner width, inside a border when it is bordered.
function panel(lines: Line[], width: number, bordered: boolean): Block {
  const inner = bordered ? width - PANEL_FRAME : width
  return columnBox(width, lines.map(l => lineBlock(l, inner)), bordered ? PANEL_BORDER : null)
}

// The props a span's Text draws with: a theme key, bold and dim, each only when set.
export function styleOf(s: Span): { color?: ThemeKey; bold?: true; dimColor?: true } {
  const out: { color?: ThemeKey; bold?: true; dimColor?: true } = {}
  if (s.color !== undefined) out.color = s.color
  if (s.bold === true) out.bold = true
  if (s.dim === true) out.dimColor = true
  return out
}

// --- the pane's budget ----------------------------------------------------------------------------

// The most the docked pane draws while it draws lanes. Claude Code's test kit (2.1.299) cuts a
// drawing's text past 100000 UTF-16 code units of span strings, and refuses a drawing of more than
// 20000 nodes, counting every element and every string as a node. blockSize counts a block the same
// way. Its text count agreed with the kit wherever the kit reported one: 121574 code units by both,
// and 99852 drew whole where 102352 was cut. The node limit was bracketed within 12 nodes: 19989
// drew and 20001 were refused. LANE_BUDGET sits 10% below each limit. The margin is not for the kit:
// it is for a host that counts or limits differently from the kit, which no one has observed.
//
// Lanes are optional. The pane draws a run's lanes only while the whole drawing fits LANE_BUDGET. It
// withholds them whole runs at a time, from the bottom run panel shown upward, and draws the word in
// their place: a run's lanes share one axis, and a run with some lanes drawn would misstate where its
// time went. When the drawing with every run's word still passes the budget, every run panel draws in
// phase1 mode. For every document the mod requests, that is the drawing the pane drew before the time
// axis. So a pane that drew whole before the time axis still draws whole, and a pane that was cut
// before it is cut no more.
//
// The cost is at most two draws per render. The pane renders on each refresh, after a run-file write,
// and for other reasons, such as a resize. Measured per render in the kit: 107 ms against 43 ms
// before the time axis at the reader's caps, 10.5 ms against 2.3 ms for five runs of 100 prompts, and
// 1.1 ms against 0.5 ms for five runs of 28 prompts.
export type Size = { units: number; nodes: number }
export const LANE_BUDGET: Size = { units: 90000, nodes: 18000 }

const plus = (a: Size, b: Size): Size => ({ units: a.units + b.units, nodes: a.nodes + b.nodes })
const minus = (a: Size, b: Size): Size => ({ units: a.units - b.units, nodes: a.nodes - b.nodes })
const fits = (s: Size, budget: Size): boolean => s.units <= budget.units && s.nodes <= budget.nodes

// What the hooks module draws for a block: a line is its Text, a Text per span and each span's
// string, and its text is the strings' UTF-16 code units; a box is one node and its children.
export function blockSize(b: Block): Size {
  if (b.kind === 'line') return { units: b.line.reduce((u, s) => u + s.text.length, 0), nodes: 1 + 2 * b.line.length }
  return b.children.reduce((t: Size, c) => plus(t, blockSize(c)), { units: 0, nodes: 1 })
}

// How many shown runs keep their lanes, first run first: the largest k for which the drawing with
// every run's withheld word, `words`, plus the first k runs' gains fits the budget. A run's gain is
// what its lanes add over its word, 0 for a run with no lane output. So lanes are withheld whole runs
// at a time, from the bottom run panel shown upward. -1 when `words` alone passes the budget: then
// every run panel draws in phase1 mode, with no lane output, the word included.
export function lanesAdmitted(words: Size, gains: Size[], budget: Size = LANE_BUDGET): number {
  if (!fits(words, budget)) return -1
  let k = 0
  let total = words
  gains.forEach((g, i) => {
    total = plus(total, g)
    if (fits(total, budget)) k = i + 1
  })
  return k
}

// The docked pane with the lanes the budget admits. The drawing with every shown run's lanes stands
// when it fits. Otherwise each run's gain is measured at its own panel's inner width, and the pane is
// drawn again with the lanes lanesAdmitted keeps, or in phase1 mode when it keeps none.
function budgeted(v: ReaderView, ag: Agents, w: number, harness: Harness): Block {
  const widths: number[] = []
  const all = docked(v, ag, w, harness, (i, n) => {
    widths[i] = n
    return 'draw'
  })
  const size = blockSize(all)
  if (fits(size, LANE_BUDGET)) return all
  const shown = v.runs.length > 0 ? v.runs.slice(0, MAX_SHOWN_RUNS) : v.last_completed !== null ? [v.last_completed] : []
  const rows = (lines: Line[], n: number) => lines.reduce((t: Size, l) => plus(t, blockSize(lineBlock(l, n))), { units: 0, nodes: 0 })
  const gains = shown.map((r, i) => minus(rows(laneLines(r, v.now_s, widths[i]!, 'draw'), widths[i]!), rows(laneLines(r, v.now_s, widths[i]!, 'withhold'), widths[i]!)))
  const k = lanesAdmitted(gains.reduce(minus, size), gains)
  return docked(v, ag, w, harness, i => (k < 0 ? 'phase1' : i < k ? 'draw' : 'withhold'))
}

// --- the pane ---------------------------------------------------------------------------------------

// The pane at its reported width and layout. The mini layout draws a few rows; the docked layout
// draws one column, and two from TWO_COLUMNS_MIN. A status is the first and only row.
export function pane(p: Parsed, ag: Agents, cols: unknown, layout: PaneLayout, harness: Harness): Block {
  const w = drawingWidth(cols)
  if (!p.ok) return columnBox(w, [lineBlock(statusLine(PANE_STATUS, p.code, w), w)])
  return layout === 'mini' ? mini(p.view, ag, w) : budgeted(p.view, ag, w, harness)
}

// `lanes` says what each shown run's panel draws on the time axis, given the panel's inner width.
function docked(v: ReaderView, ag: Agents, w: number, harness: Harness, lanes: (i: number, n: number) => LaneMode): Block {
  const bordered = w >= BORDER_MIN
  const listed = v.runs.slice(0, MAX_SHOWN_RUNS)
  const shown = listed.length > 0 ? listed : v.last_completed !== null ? [v.last_completed] : []
  const titled = (word: string, r: RunView) => [span(shown.length > 1 ? `${word} ${ids(r)}` : word, { bold: true })]
  const inner = (width: number) => (bordered ? width - PANEL_FRAME : width)
  // The run panels, with the count of runs past the shown ones.
  const runBlocks = (width: number): Block[] => {
    const out: Block[] = []
    if (listed.length === 0) {
      const idle = idleLines(v, ag, inner(width), harness, lanes(0, inner(width)))
      if (idle.length > 0) out.push(panel(idle, width, bordered))
    }
    listed.forEach((r, i) => out.push(panel(runLines(r, v, ag, true, inner(width), harness, lanes(i, inner(width))), width, bordered)))
    if (v.runs.length > listed.length) out.push(lineBlock(moreRuns(v.runs.length - listed.length), width))
    return out
  }
  // The councils and gates of each shown run, then this session's agents. An empty one takes no room.
  const sideBlocks = (width: number): Block[] => {
    const out: Block[] = []
    for (const r of shown) {
      if (r.councils.length > 0) out.push(panel([titled('Councils', r), ...councilGrid(r.councils, inner(width))], width, bordered))
      if (r.gates.length > 0) out.push(panel([titled('Gates', r), gateStrip(r.gates, inner(width))], width, bordered))
    }
    const agentRows = agentLines(ag, inner(width))
    if (agentRows.length > 0) out.push(panel([[span('Agents', { bold: true })], ...agentRows], width, bordered))
    return out
  }
  const legend = shown.length > 0 ? legendLine(shown, w) : []
  const top: Block[] = legend.length > 0 ? [lineBlock(legend, w)] : []
  if (w >= TWO_COLUMNS_MIN) {
    const col = Math.floor((w - COLUMN_GAP) / 2)
    const right = sideBlocks(col)
    if (right.length > 0) {
      const left = [...runBlocks(col), lineBlock(readerLine(v), col)]
      return columnBox(w, [...top, { kind: 'box', direction: 'row', width: w, border: null, gap: COLUMN_GAP, children: [columnBox(col, left), columnBox(col, right)] }])
    }
  }
  return columnBox(w, [...top, ...runBlocks(w), ...sideBlocks(w), lineBlock(readerLine(v), w)])
}

// --- the mini layout ----------------------------------------------------------------------------------

type Item = { name: string; line: Line }

// The newest council record in one line: its prompt and round, a cell per seat, its aggregate.
function councilSummary(councils: Council[]): Line {
  const c = councils[councils.length - 1]!
  const seats = c.outcome === 'could-not-run' ? [SEAT_CELLS.notRun] : c.seats.map(s => seatCell(c, s.role))
  return [span(`council p${c.prompt} r${c.round} `), ...seats.map(glyphSpan), span(` ${member(c.aggregate, ROUTE_ACTIONS)}${c.converged ? ' converged' : ''}`)]
}

// The agent list in one line: how many agents show each status glyph.
function agentSummary(ag: Agents): Line | null {
  if (!ag.available) return [span('agents unavailable', { dim: true })]
  if (ag.shown.length === 0) return null
  const parts: Line[] = []
  for (const g of [...new Set([...Object.values(AGENT_GLYPHS), UNKNOWN])]) {
    const k = ag.shown.filter(a => agentGlyph(a.status) === g).length
    if (k > 0) parts.push([glyphSpan(g), span(` ${k}`)])
  }
  return [span('agents '), ...joined(parts)]
}

// At most MINI_ROWS rows. The sections fill in the order run, legend, gates, councils, agents. In the
// run section the stall and the escalation come ahead of the strip and the prompt. What does not fit
// is named, with every section that has something to show, on a last `+N more` row.
function mini(v: ReaderView, ag: Agents, w: number): Block {
  const bordered = w >= BORDER_MIN
  const inner = bordered ? w - PANEL_FRAME : w
  const runItems: Item[] = []
  const r = bandRun(v.runs)
  const last = v.last_completed
  const named: string[] = []
  if (r !== undefined) {
    runItems.push({ name: 'run', line: [span(`${ids(r)}  ${position(r)}  ${r.pct}%`, { bold: true })] })
    const idle = stallIdle(r, v.now_s, ag)
    if (idle !== null) runItems.push({ name: 'stall', line: [span(stallShort(idle), { color: 'error' })] })
    const esc = currentEscalation(r) ?? r.escalations[0]
    if (esc !== undefined) {
      const others = r.escalations.length - 1
      runItems.push({ name: 'escalation', line: [span(escalationShort(esc) + (others > 0 ? ` +${others}` : ''), { color: 'error' })] })
    }
    const strip = stripLine(r, inner)
    if (strip.length > 0) runItems.push({ name: 'strip', line: strip })
    const cur = currentPrompt(r)
    if (cur !== undefined) runItems.push({ name: 'prompt', line: promptLine(cur, r, v.now_s, true, inner) })
    if (v.runs.length > 1) runItems.push({ name: 'runs', line: moreRuns(v.runs.length - 1) })
  } else if (last !== null) {
    runItems.push({ name: 'run', line: [span(`${lastRunTitle(v)}: ${ids(last)}  ${last.counts.done}/${last.total} done`, { bold: true })] })
    if (last.summary.length > 0) named.push('summary')
  } else {
    const sentence = idleSentence(v)
    if (sentence !== null) runItems.push({ name: 'run', line: sentence })
  }
  const run = r ?? last ?? undefined
  const sections: { name: string; items: Item[]; frame: number }[] = [
    { name: 'run', items: runItems, frame: bordered && runItems.length > 0 ? 2 : 0 },
    { name: 'legend', items: run === undefined ? [] : [{ name: 'legend', line: legendLine([run], w) }], frame: 0 },
    { name: 'gates', items: run === undefined || run.gates.length === 0 ? [] : [{ name: 'gates', line: gateStrip(run.gates, w) }], frame: 0 },
    { name: 'councils', items: run === undefined || run.councils.length === 0 ? [] : [{ name: 'councils', line: councilSummary(run.councils) }], frame: 0 },
    { name: 'agents', items: (() => { const a = agentSummary(ag); return a === null ? [] : [{ name: 'agents', line: a }] })(), frame: 0 },
  ].map(sec => ({ ...sec, items: sec.items.filter(i => i.line.length > 0) }))
  const total = sections.reduce((n, sec) => n + sec.items.length + (sec.items.length > 0 ? sec.frame : 0), 0)
  const budget = total + (named.length > 0 ? 1 : 0) <= MINI_ROWS ? MINI_ROWS : MINI_ROWS - 1
  const blocks: Block[] = []
  let used = 0
  for (const sec of sections) {
    if (sec.items.length === 0) continue
    const room = budget - used - sec.frame
    const kept = sec.items.slice(0, Math.max(0, room))
    for (const i of sec.items.slice(kept.length)) named.push(i.name)
    if (kept.length === 0) continue
    used += kept.length + sec.frame
    const lines = kept.map(i => i.line)
    if (sec.name === 'run') blocks.push(panel(lines, w, bordered))
    else for (const l of lines) blocks.push(lineBlock(l, w))
  }
  if (named.length > 0) blocks.push(lineBlock([span(`+${named.length} more: ${named.join(', ')}`, { dim: true })], w))
  return columnBox(w, blocks)
}

// --- the band -----------------------------------------------------------------------------------------

// One band segment: what it shows, its line, and how the fit treats it. `rank` orders the
// segments by what is kept first, lowest first. A segment with `at` shrinks to a form of at most
// a given width before it is dropped; one with `short` takes its short form first, at `shortRank`.
type BandItem = {
  name: string; order: number; rank: number; line: Line
  short?: Line; shortRank?: number
  at?: (budget: number) => Line; min?: number
}
export type Segment = { name: string; line: Line }

// The segments kept at width w, in draw order. Every segment starts at its full form. While the
// line is too wide, the lowest-ranked step is taken: a stall or an escalation takes its short form
// first, then segments shrink or drop from the lowest rank up. The stall and the escalation are the
// last to go, after the position, the percentage, the ids and the strip's cells. The most important
// segment left is never dropped: below its width the band cuts it with an ellipsis.
function fitSegments(items: BandItem[], w: number): Segment[] {
  const live = new Map(items.map(i => [i, i.line]))
  const total = () => [...live.values()].reduce((n, l) => n + lineCells(l), 0) + SEGMENT_GAP.length * Math.max(0, live.size - 1)
  const steps: { rank: number; item: BandItem; kind: 'short' | 'cut' }[] = []
  for (const i of items) {
    if (i.short !== undefined) steps.push({ rank: i.shortRank ?? i.rank, item: i, kind: 'short' })
    steps.push({ rank: i.rank, item: i, kind: 'cut' })
  }
  steps.sort((a, b) => b.rank - a.rank)
  for (const st of steps) {
    if (total() <= w) break
    const cur = live.get(st.item)
    if (cur === undefined) continue
    if (st.kind === 'short') {
      live.set(st.item, st.item.short!)
      continue
    }
    if (st.item.at !== undefined) {
      const budget = lineCells(cur) - (total() - w)
      if (budget >= (st.item.min ?? 1)) {
        live.set(st.item, st.item.at(budget))
        continue
      }
    }
    if (live.size > 1) live.delete(st.item)
  }
  return items.filter(i => live.has(i)).sort((a, b) => a.order - b.order).map(i => ({ name: i.name, line: live.get(i)! }))
}

// The band's segments at width w, or null when the band draws nothing. A status takes the band's
// line in place of the run; the two quiet statuses keep it empty. With no listed run the band shows
// the last run for 48 hours after it completed, or the refusal when the reader refused a run.
// The last run's progress counts every terminal prompt (done, skipped or blocked), because the run finished.
export function bandSegments(p: Parsed, ag: Agents, w: number, harness: Harness): Segment[] | null {
  if (!p.ok) return QUIET.includes(p.code) ? null : [{ name: 'status', line: statusLine(harness.bandPrefix, p.code, w, { dim: true }) }]
  const v = p.view
  const r = bandRun(v.runs)
  if (r === undefined) {
    if (v.last_completed_status === 'run-in-progress') return [{ name: 'last run', line: [span('run in progress, view refused', { dim: true })] }]
    const last = v.last_completed
    const age = lastRunAge(v)
    if (last === null || age === null) return null
    // CRUX: names the plugin, so a user who did not install it knows where the line comes from.
    const lead = v.last_completed_status === 'latest-dated' ? 'CRUX: Last dated run' : 'CRUX: Last run'
    return [{ name: 'last run', line: [span(`${lead} ${ids(last)} completed ${age.age} ago. Progress: ${last.terminal}/${last.total}.${age.took === null ? '' : ` Time: ${age.took}.`}`, { dim: true })] }]
  }
  const dim = (text: string): Line => [span(text, { dim: true })]
  const items: BandItem[] = []
  const cur = currentPrompt(r)
  items.push({ name: 'ids', order: 0, rank: 5, line: dim(ids(r)) })
  if (r.prompts.length > 0) {
    // The smallest strip is the current cell and the count of the rest.
    const rest = r.prompts.length - 1
    items.push({ name: 'strip', order: 1, rank: 6, line: compactStrip(r, MAX_WIDTH), at: b => compactStrip(r, b), min: 1 + (rest > 0 ? cells(`+${rest}`) : 0) })
  }
  const kind = currentKind(r)
  if (kind !== undefined) items.push({ name: 'kind', order: 2, rank: 7, line: [span(kind.word, { color: kind.color })] })
  items.push({ name: 'position', order: 3, rank: 3, line: dim(position(r)) })
  items.push({ name: 'percent', order: 4, rank: 4, line: dim(`${r.pct}%`) })
  const elapsed = cur === undefined ? null : openElapsed(cur, v.now_s)
  if (elapsed !== null) items.push({ name: 'elapsed', order: 5, rank: 8, line: dim(elapsed) })
  const esc = currentEscalation(r)
  if (esc !== undefined) items.push({ name: 'escalation', order: 6, rank: 2, line: [span(escalationText(esc), { color: 'error' })], short: [span(escalationShort(esc), { color: 'error' })], shortRank: 14 })
  const idle = stallIdle(r, v.now_s, ag)
  if (idle !== null) items.push({ name: 'stall', order: 7, rank: 1, line: [span(stallFull(idle), { color: 'error' })], short: [span(stallShort(idle), { color: 'error' })], shortRank: 15 })
  if (cur !== undefined) {
    const title = drawn(cur.title)
    if (title !== '') items.push({ name: 'title', order: 8, rank: 9, line: dim(title), at: b => dim(fit(title, b)), min: Math.min(8, cells(title)) })
  }
  const newest = r.councils[r.councils.length - 1]
  if (newest !== undefined) items.push({ name: 'council', order: 9, rank: 10, line: dim(`council p${newest.prompt} r${newest.round} ${member(newest.aggregate, ROUTE_ACTIONS)}`) })
  const decided = r.gates.filter(g => g.state !== 'pending')
  const gateNow = decided[decided.length - 1]
  if (gateNow !== undefined) items.push({ name: 'gate', order: 10, rank: 11, line: dim(`gate p${gateNow.n} ${member(gateNow.state, STATES)}`) })
  if (ag.running > 0) items.push({ name: 'agents', order: 11, rank: 12, line: dim(`${ag.running} agent${ag.running === 1 ? '' : 's'} running`) })
  const others = v.runs.length - 1
  if (others > 0) items.push({ name: 'runs', order: 12, rank: 13, line: dim(`+${others} more run${others === 1 ? '' : 's'}`) })
  return fitSegments(items, w)
}

// The band at its reported width: one borderless line, or null when it draws nothing.
export function band(p: Parsed, ag: Agents, cols: unknown, harness: Harness): Block | null {
  const w = drawingWidth(cols)
  const segs = bandSegments(p, ag, w, harness)
  if (segs === null || segs.length === 0) return null
  return columnBox(w, [lineBlock(joined(segs.map(s => s.line), SEGMENT_GAP), w)])
}
