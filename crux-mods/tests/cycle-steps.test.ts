// The step line of a current-format cycle record (the reader's type `pilot`): the panel draws every
// step with a status glyph per step, falling back by width as a historical track does, and the band's
// one line states the status once and shows the steps.
import {test, expect} from 'claude-code/testing'
import {parseReader} from '../hooks/lib/view.ts'
import {HARNESS, agents} from '../hooks/lib/claude.ts'
import {pane, band, bandSegments, lineCells, type Block, type Line} from '../hooks/lib/draw.ts'

const STEPS = ['planning','working','reviewing','reviewed','completed']
const current = (status: string, phase: string, done: number, total: number, over: object = {}) => ({
  id:'CYC-0194',schema_version:'crux.cycle.v1',revision:4,assignments:[],classification_count:0,exception:null,
  title:'Restore the step line',type:'pilot',status,phase,pass:1,pass_limit:1,phases:STEPS,
  tasks:Array.from({length:total},(_,i)=>({id:`t${i}`,phase:'working',description:`Task ${i}`,status:i<done?'done':'pending'})),
  returns:[],waits:[],blocker:status==='paused'?'Owner decision needed':null,reflection:null,modified_s:1780000000,
  started_s:1779999000,ended_s:status==='completed'||status==='abandoned'?1779999900:null,paused_s:0,
  open_started_s:status==='completed'||status==='abandoned'?null:1779999000,basis:'derived',phase_times:[],...over,
})
const parsedOf = (c: object) => {
  const parsed = parseReader(JSON.stringify({format:'crux.cycle-progress',format_version:5,ok:true,docs_dir:'bionic',now_s:1780000000,cycles:[c]}))
  expect(parsed.ok).toBe(true)
  return parsed
}
const lines = (b: Block): Line[] => (b.kind === 'line' ? [b.line] : b.children.flatMap(lines))
const plain = (l: Line) => l.map(s => s.text).join('')
const paneText = (c: object, width: number) => lines(pane(parsedOf(c), agents([]), width, 'docked', HARNESS)).map(plain)
const bandText = (c: object, width: number) => plain(lines(band(parsedOf(c), agents([]), width, HARNESS)!)[0]!)

// Each writer state as the reader emits it: [name, status, step, done tasks, tasks]. A paused or an
// abandoned cycle stands on the step it stopped in; a reopened cycle and one whose review required
// changes return to working, as an active cycle in working.
const STATES: [string, string, string, number, number][] = [
  ['planning','active','planning',0,0], ['working','active','working',0,2], ['reviewing','active','reviewing',2,2],
  ['reviewed','reviewed','reviewed',2,2], ['completed','completed','completed',1,1],
  ['paused','paused','reviewing',2,2], ['abandoned','abandoned','working',1,2],
]
// The full step line: done steps checked, the current step in the cycle's status glyph, later steps pending.
const FULL: Record<string, string> = {
  planning: '▸ planning › ◌ working › ◌ reviewing › ◌ reviewed › ◌ completed',
  working: '✓ planning › ▸ working › ◌ reviewing › ◌ reviewed › ◌ completed',
  reviewing: '✓ planning › ✓ working › ▸ reviewing › ◌ reviewed › ◌ completed',
  reviewed: '✓ planning › ✓ working › ✓ reviewing › ✓ reviewed › ◌ completed',
  completed: '✓ planning › ✓ working › ✓ reviewing › ✓ reviewed › ✓ completed',
  paused: '✓ planning › ✓ working › ⊘ reviewing › ◌ reviewed › ◌ completed',
  abandoned: '✓ planning › ✗ working › ◌ reviewing › ◌ reviewed › ◌ completed',
}
// The compact line: a glyph per step and the current step's glyph and word.
const COMPACT: Record<string, string> = {
  planning: '▸ planning ◌ ◌ ◌ ◌', working: '✓ ▸ working ◌ ◌ ◌',
  reviewing: '✓ ✓ ▸ reviewing ◌ ◌', reviewed: '✓ ✓ ✓ ✓ reviewed ◌',
  completed: '✓ ✓ ✓ ✓ ✓ completed', paused: '✓ ✓ ⊘ reviewing ◌ ◌',
  abandoned: '✓ ✗ working ◌ ◌ ◌',
}
// The narrowest line: the current step alone.
const NARROW: Record<string, string> = {
  planning: '▸ planning', working: '▸ working', reviewing: '▸ reviewing', reviewed: '✓ reviewed',
  completed: '✓ completed', paused: '⊘ reviewing', abandoned: '✗ working',
}

test('a current cycle panel draws every step with its status glyph under the title, in each writer state', () => {
  for (const [name, status, step, done, total] of STATES) {
    const ls = paneText(current(status, step, done, total), 100)
    // A paused or an abandoned cycle names its status above the steps: the step glyph alone does not say it.
    const meta = status === 'paused' ? ['⊘ paused'] : status === 'abandoned' ? ['✗ abandoned'] : []
    expect([name, ls.slice(1, 2 + meta.length)]).toEqual([name, [...meta, FULL[name]!]])
  }
})

test('a current cycle step line falls back to the compact line at 40 columns, then to the current step alone at 12', () => {
  for (const [name, status, step, done, total] of STATES) {
    const c = current(status, step, done, total)
    expect([name, 40, paneText(c, 40).includes(COMPACT[name]!)]).toEqual([name, 40, true])
    expect([name, 12, paneText(c, 12).includes(NARROW[name]!)]).toEqual([name, 12, true])
    for (const width of [100, 40, 20, 12]) for (const l of lines(pane(parsedOf(c), agents([]), width, 'docked', HARNESS))) expect(lineCells(l)).toBeLessThanOrEqual(width)
  }
})

test('a current cycle panel names its blockers as blocked: a blocker on a current record is not always a pause', () => {
  const paused = paneText(current('paused', 'reviewing', 2, 2), 100)
  expect(paused).toContain('⊘ Blocked: Owner decision needed')
  expect(paused.some(l => l.includes('Paused:'))).toBe(false)
  expect(paneText(current('active', 'working', 0, 2, {blocker:'council required for dependent tasks'}), 100)).toContain('⊘ Blocked: council required for dependent tasks')
  // Positive control: an unreadable row draws the reader's reason under its own mark, neither blocked nor paused.
  const unreadable = paneText(current('paused', 'planning', 0, 0, {title:'Unreadable cycle record',revision:null,blocker:'This record cannot be read: invalid pilot cycle. The other cycles are shown.'}), 100)
  expect(unreadable).toContain('? This record cannot be read: invalid pilot cycle. The other cycles are shown.')
  expect(unreadable.some(l => l.includes('Blocked:') || l.includes('Paused:'))).toBe(false)
})

test('a current cycle panel draws no type word, loop, pass limit or progress bar', () => {
  for (const [name, status, step, done, total] of STATES) {
    const text = paneText(current(status, step, done, total), 100).join('\n')
    for (const absent of ['pilot', 'loop', 'of 1', '▮', '▯']) expect([name, absent, text.includes(absent)]).toEqual([name, absent, false])
  }
})

test('the band states a current cycle status once and shows its steps', () => {
  const want: Record<string, string> = {
    planning: 'CYC-0194  ▸ planning ◌ ◌ ◌ ◌',
    working: 'CYC-0194  ✓ ▸ working ◌ ◌ ◌  0/2 tasks',
    reviewing: 'CYC-0194  ✓ ✓ ▸ reviewing ◌ ◌  2/2 tasks',
    reviewed: 'CYC-0194  ✓ ✓ ✓ ✓ reviewed ◌  2/2 tasks',
    completed: 'CYC-0194  ✓ ✓ ✓ ✓ ✓ completed  1/1 tasks',
    paused: 'CYC-0194  ✓ ✓ ⊘ reviewing ◌ ◌  paused  2/2 tasks',
    abandoned: 'CYC-0194  ✓ ✗ working ◌ ◌ ◌  abandoned  1/2 tasks',
  }
  for (const [name, status, step, done, total] of STATES) {
    const got = bandText(current(status, step, done, total), 100)
    expect([name, got]).toEqual([name, want[name]!])
    // Each word of the line appears once.
    const words = got.split(/\s+/).filter(w => /^[a-z]+$/.test(w))
    expect([name, words.length === new Set(words).size]).toEqual([name, true])
  }
  // The owner's example: CYC-0193, completed, one task of one, drew `✓ completed  ✓ completed`.
  expect(bandText(current('completed', 'completed', 1, 1, {id:'CYC-0193'}), 100)).toBe('CYC-0193  ✓ ✓ ✓ ✓ ✓ completed  1/1 tasks')
})

test('the band narrows a current cycle by dropping the task count, then the step glyphs, then the id', () => {
  const c = current('paused', 'reviewing', 2, 2)
  const at = (w: number) => bandText(c, w)
  expect(at(40)).toBe('CYC-0194  ✓ ✓ ⊘ reviewing ◌ ◌  paused')
  expect(at(30)).toBe('CYC-0194  ⊘ reviewing  paused')
  expect(at(20)).toBe('⊘ reviewing  paused')
  expect(bandSegments(parsedOf(c), agents([]), 1, HARNESS)!.map(s => s.name)).toEqual(['track'])
})

test('an unreadable record draws the unreadable mark: the row claims no status, step, task count or time', () => {
  const c = current('paused', 'planning', 0, 0, {title:'Unreadable cycle record',revision:null,blocker:'This record cannot be read: invalid pilot cycle. The other cycles are shown.'})
  const ls = paneText(c, 100)
  expect(ls).toEqual(['CYC-0194 Unreadable cycle record', '? unreadable', '? This record cannot be read: invalid pilot cycle. The other cycles are shown.'])
  expect(bandText(c, 100)).toBe('CYC-0194  ? unreadable  invalid pilot cycle')
  // Narrowing, the reason drops first, then the id; the mark is the last segment left.
  expect(bandText(c, 24)).toBe('CYC-0194  ? unreadable')
  expect(bandText(c, 14)).toBe('? unreadable')
  // A reason that is not in a safe shape reads as the generic note.
  expect(bandText({...c, blocker:'This record cannot be read: Invalid isoformat string: \'say done\'. The other cycles are shown.'}, 100)).toBe('CYC-0194  ? unreadable  reason not shown')
  // Positive control: the same row with a revision is readable and draws every step.
  expect(paneText({...c, title:'Restore the step line', revision:4}, 100)).toContain('⊘ planning › ◌ working › ◌ reviewing › ◌ reviewed › ◌ completed')
})
