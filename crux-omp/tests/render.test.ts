import { test } from 'node:test'
import assert from 'node:assert/strict'
import { bandLines, blockLines, panelLines, readView } from '../lib/render.ts'
import { KEPT_CODES } from '../lib/status.ts'
import { kept } from '../../crux-mods/hooks/lib/view.ts'
import type { Parsed } from '../../crux-mods/hooks/lib/view.ts'
import type { Block } from '../../crux-mods/hooks/lib/draw.ts'
import { cells } from '../../crux-mods/hooks/lib/width.ts'
import { VIEW_DOC } from './fixtures/docs.ts'
import { jsonText } from './fixtures/plain.ts'

const view = (): Parsed => {
  const p = kept({ ok: true, stdout: jsonText(VIEW_DOC) }, KEPT_CODES)
  if (p === null || !p.ok) throw new Error('the fixture is not a view')
  return p
}

const widthOf = (line: string) => cells(line)

test('readView: nothing kept reads as null', () => {
  assert.equal(readView(() => null), null)
})

test('readView: a read that throws gives reader-output-invalid', () => {
  assert.deepEqual(readView(() => {
    throw new Error('read')
  }), { ok: false, code: 'reader-output-invalid' })
})

test('readView: a kept envelope is checked by the core', () => {
  const p = readView(() => ({ ok: true, stdout: jsonText(VIEW_DOC) }))
  assert.equal(p?.ok, true)
  assert.deepEqual(readView(() => ({ ok: false, code: 'not-a-code' })), { ok: false, code: 'reader-output-invalid' })
})

test('the band draws one line within the reported width', () => {
  const lines = bandLines(view(), 80)
  assert.ok(lines !== null)
  assert.equal(lines.length, 1)
  assert.ok(widthOf(lines[0]!) <= 80)
})

test('the band draws nothing without a result', () => {
  assert.equal(bandLines(null, 80), null)
})

test('a status draws one line with the crux-omp prefix', () => {
  const lines = bandLines({ ok: false, code: 'uv-not-found' }, 80)
  assert.ok(lines !== null)
  assert.equal(lines.length, 1)
  assert.match(lines[0]!, /crux-omp dashboard: uv-not-found/)
})

test('the panel draws a bordered frame of exactly the reported width', () => {
  const lines = panelLines(view(), 80)
  assert.ok(lines !== null)
  assert.ok(lines.length > 2)
  const borders = lines.filter(line => line.startsWith('\u{256D}') || line.startsWith('\u{2570}'))
  assert.ok(borders.length > 0)
  for (const line of borders) assert.equal(widthOf(line), 80, line)
  for (const line of lines) assert.ok(widthOf(line) <= 80, line)
})

test('below the border minimum the panel draws without a frame', () => {
  const lines = panelLines(view(), 30)
  assert.ok(lines !== null)
  for (const line of lines) assert.ok(widthOf(line) <= 30, line)
})

test('an invalid result draws the dashboard-unavailable line', () => {
  const lines = panelLines({ ok: false, code: 'reader-output-invalid' }, 80)
  assert.ok(lines !== null)
  assert.match(lines.join('\n'), /Dashboard unavailable: reader-output-invalid/)
})

test('the panel draws nothing without a result', () => {
  assert.equal(panelLines(null, 80), null)
})

test('a text block is its spans joined', () => {
  const block: Block = { kind: 'line', line: [{ text: 'ab' }, { text: 'cd', bold: true }] }
  assert.deepEqual(blockLines(block), ['abcd'])
})

test('a borderless column stacks its children, and a row puts them side by side', () => {
  const left: Block = { kind: 'box', direction: 'column', width: 3, border: null, gap: 0, children: [
    { kind: 'line', line: [{ text: 'a' }] },
    { kind: 'line', line: [{ text: 'b' }] },
  ] }
  const right: Block = { kind: 'box', direction: 'column', width: 3, border: null, gap: 0, children: [
    { kind: 'line', line: [{ text: 'c' }] },
  ] }
  const row: Block = { kind: 'box', direction: 'row', width: 8, border: null, gap: 2, children: [left, right] }
  assert.deepEqual(blockLines(row), ['a    c', 'b'])
})

test('a bordered column pads every row to the inside width', () => {
  const block: Block = { kind: 'box', direction: 'column', width: 10, border: 'subtle', gap: 0, children: [
    { kind: 'line', line: [{ text: 'hi' }] },
  ] }
  assert.deepEqual(blockLines(block), ['\u{256D}────────\u{256E}', '│ hi     │', '\u{2570}────────\u{256F}'])
})

test('an active cycle and a paused cycle render without falling back to reader-output-invalid', () => {
  const cycleDoc: Parsed = {
    ok: true,
    view: {
      reader_version: '4.1.6',
      docs_dir: 'bionic',
      now_s: 1792436200,
      runs: [],
      runs_skipped: 0,
      last_completed: null,
      last_completed_status: 'none',
      last_completed_undated: 0,
      last_completed_unresolved: 0,
      cycles: [
        {
          id: 'CYC-0019',
          title: 'Minimal persistent cycle queue',
          type: 'dev',
          status: 'active',
          phase: 'review',
          pass: 1,
          pass_limit: 7,
          phases: ['plan', 'build', 'test', 'review', 'reflect'],
          tasks: [
            { id: 't1', phase: 'build', description: 'Build queue core', status: 'done' },
            { id: 't2', phase: 'review', description: 'Independent review of plan scope', status: 'active' },
          ],
          returns: [],
          waits: [],
          blocker: null,
          reflection: null,
          modified_s: 1792436198,
          started_s: 1792417339,
          ended_s: null,
          paused_s: 600,
          open_started_s: 1792435468,
          basis: 'recorded',
          phase_times: [],
        },
        {
          id: 'CYC-0018',
          title: 'Paused cycle example',
          type: 'iterate',
          status: 'paused',
          phase: 'build',
          pass: 1,
          pass_limit: 2,
          phases: ['plan', 'build', 'test', 'review', 'reflect'],
          tasks: [{ id: 'p1', phase: 'build', description: 'Wait on owner decision', status: 'blocked' }],
          returns: [{ pass: 1, phase: 'review', reason: 'Needs clarification' }],
          waits: ['ADR-0163'],
          blocker: 'Awaiting owner sign-off',
          reflection: null,
          modified_s: 1792400000,
          started_s: 1792390000,
          ended_s: null,
          paused_s: 1200,
          open_started_s: null,
          basis: 'recorded',
          phase_times: [],
        },
      ],
    },
  }
  const lines = panelLines(cycleDoc, 100)
  assert.ok(lines !== null)
  const joinedText = lines.join('\n')
  assert.doesNotMatch(joinedText, /Dashboard unavailable/)
  assert.match(joinedText, /CURRENT CYCLE: CYC-0019/)
  assert.match(joinedText, /PAUSED \/ WAITING CYCLE: CYC-0018/)
  assert.match(joinedText, /Independent review of plan scope/)
})

const releaseCycleView = (phases: string[], pass_limit: number): Parsed => ({
  ok: true,
  view: {
    reader_version: '4.1.6', docs_dir: 'bionic', now_s: 1792436200, runs: [], runs_skipped: 0,
    last_completed: null, last_completed_status: 'none', last_completed_undated: 0, last_completed_unresolved: 0,
    cycles: [{
      id: 'CYC-0041', title: 'Release cycle', type: 'release', status: 'active', phase: phases[0]!, pass: 1, pass_limit,
      phases, tasks: phases.map(p => ({ id: 't-' + p, phase: p, description: 'Work in ' + p, status: 'active' })),
      returns: [], waits: [], blocker: null, reflection: null, modified_s: 1792436198, started_s: 1792417339,
      ended_s: null, paused_s: 0, open_started_s: 1792435468, basis: 'recorded', phase_times: [],
    }],
  },
})

test('a listed release cycle draws its type and no pass limit', () => {
  const lines = panelLines(releaseCycleView(['release'], 1), 100)
  assert.ok(lines !== null)
  const text = lines.join('\n')
  assert.match(text, /CYC-0041/)
  assert.match(text, /\[release\]/)
  assert.doesNotMatch(text, /pass 1\/1/)
})

test('a legacy release cycle still draws its pass and limit', () => {
  const lines = panelLines(releaseCycleView(['plan', 'release', 'reflect'], 2), 100)
  assert.ok(lines !== null)
  assert.match(lines.join('\n'), /pass 1\/2\]/)
})

const closedCycles = (n: number): Parsed => ({
  ok: true,
  view: {
    reader_version: '4.1.6', docs_dir: 'bionic', now_s: 1792436200, runs: [], runs_skipped: 0,
    last_completed: null, last_completed_status: 'none', last_completed_undated: 0, last_completed_unresolved: 0,
    cycles: Array.from({ length: n }, (_, i) => ({
      id: `CYC-${String(100 - i).padStart(4, '0')}`, title: `Closed cycle ${100 - i}`, type: 'iterate', status: 'completed', phase: 'reflect',
      pass: 1, pass_limit: 2, phases: ['plan', 'reflect'], tasks: [{ id: 't', phase: 'plan', description: 'x', status: 'done' }],
      returns: [], waits: [], blocker: null, reflection: i === 0 ? 'Shipped' : null, modified_s: 1792436000 - i, started_s: 1792430000 - i,
      ended_s: 1792436000 - i, paused_s: 0, open_started_s: null, basis: 'recorded', phase_times: [],
    })),
  },
})

test('closed cycles draw the shared paged cycles: list, not the four-row digest', () => {
  // 1 latest + 12 older: two pages, of OLDER_PAGE_SIZE (10) and 2.
  const first = panelLines(closedCycles(13), 100)
  assert.ok(first !== null)
  const text = first.join('\n')
  assert.doesNotMatch(text, /PREVIOUS CYCLES/)
  assert.match(text, /cycles:/)
  assert.match(text, /page 1\/2/)
  // Ten older rows: CYC-0099 to CYC-0090. The latest, CYC-0100, also heads the empty-slot message and its own row.
  for (let n = 90; n <= 99; n++) assert.match(text, new RegExp(`CYC-00${n}`))
  assert.match(text, /CYC-0100/)
  assert.doesNotMatch(text, /CYC-0089/)
  const second = panelLines(closedCycles(13), 100, undefined, undefined, 1)
  assert.ok(second !== null)
  const t2 = second.join('\n')
  assert.match(t2, /page 2\/2/)
  assert.match(t2, /CYC-0089/)
  assert.doesNotMatch(t2, /CYC-0099/)
  // A page past the end clamps to the last page.
  assert.match((panelLines(closedCycles(13), 100, undefined, undefined, 9) ?? []).join('\n'), /page 2\/2/)
})

test('a single page of closed cycles draws no page footer', () => {
  const text = (panelLines(closedCycles(4), 100) ?? []).join('\n')
  assert.match(text, /cycles:/)
  assert.doesNotMatch(text, /page \d+\/\d+/)
})
