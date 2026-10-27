import {test, expect} from 'claude-code/testing'
import {parseReader, answer} from '../hooks/lib/view.ts'
import {touchesRunFile} from '../hooks/lib/claude.ts'

const cycleRow = (n: number, status = 'completed') => ({
  id: `CYC-${String(n).padStart(4, '0')}`, title: `Cycle title ${n}`, type: 'quick-fix', status, phase: 'test', pass: 1, pass_limit: 1,
  phases: ['build', 'test', 'review', 'reflect'], tasks: [{id: 'check', phase: 'test', description: 'Verify', status: status === 'active' ? 'active' : 'done'}],
  returns: [], waits: [], blocker: null, reflection: null, modified_s: 1780000000,
  started_s: 1779999000, ended_s: status === 'active' || status === 'paused' ? null : 1779999900, paused_s: 0,
  open_started_s: status === 'active' || status === 'paused' ? 1779999500 : null, basis: 'recorded',
  phase_times: [{phase: 'build', active_s: 500, paused_s: 0}],
})
const qItem = (n: number, state: string, extra: Record<string, unknown> = {}) => ({
  id: `Q-${String(n).padStart(4, '0')}`, title: `Queue secret title ${n}`, state, suggested_type: 'iterate', cycle: null, cycle_status: null, ...extra,
})
const doc = (cycles: unknown[], queue?: unknown) => ({
  format: 'crux.cycle-progress', format_version: 2, ok: true, docs_dir: 'bionic', now_s: 1780000000, cycles,
  ...(queue === undefined ? {} : {queue}),
})
const parse = (d: unknown) => parseReader(JSON.stringify(d))
const text = (d: unknown) => answer(parse(d))

test('the parser accepts the document with and without queue', () => {
  expect(parse(doc([cycleRow(1)])).ok).toBe(true)
  expect(parse(doc([cycleRow(1)], null)).ok).toBe(true)
  const p = parse(doc([cycleRow(1)], {ok: true, items: [qItem(1, 'pending')], authorization: {kind: 'next', remaining: ['Q-0001']}}))
  expect(p.ok).toBe(true)
  expect(parse(doc([cycleRow(1)], {ok: false, error: 'bad file'})).ok).toBe(true)
})

test('the parser rejects a malformed queue', () => {
  const ok = (items: unknown[], auth: unknown = null) => ({ok: true, items, authorization: auth})
  expect(parse(doc([], ok([qItem(1, 'bogus')]))).ok).toBe(false)
  expect(parse(doc([], ok([{...qItem(1, 'pending'), id: 'X-1'}]))).ok).toBe(false)
  expect(parse(doc([], ok([{...qItem(1, 'pending'), extra: 1}]))).ok).toBe(false)
  expect(parse(doc([], ok([qItem(1, 'started', {cycle: 'CYC-0001', cycle_status: 'weird'})]))).ok).toBe(false)
  expect(parse(doc([], ok([], {kind: 'sometimes', remaining: []}))).ok).toBe(false)
  expect(parse(doc([], ok([], {kind: 'queue', remaining: ['nope']}))).ok).toBe(false)
  expect(parse(doc([], {ok: true, items: [], authorization: null, extra: 1})).ok).toBe(false)
  expect(parse(doc([], ok(Array.from({length: 51}, (_, i) => qItem(i + 1, 'pending'))))).ok).toBe(false)
  expect(parse(doc([], {ok: false})).ok).toBe(false)
  expect(parse(doc([], 'text')).ok).toBe(false)
})

test('the answer shows the latest closed cycle in full, then a cycles list of at most 10 compact lines', () => {
  const t = text(doc([1, 2, 3, 4, 5, 6].map(n => cycleRow(n))))
  expect(t).toContain('dashboard status ok cycles 6')
  const lines = t.split('\n')
  const at = (prefix: string) => lines.findIndex(l => l.startsWith(prefix))
  expect(at('cycle CYC-0006 type quick-fix status completed phase test pass 1 limit 1')).toBeGreaterThan(-1)
  expect(lines[at('cycle CYC-0006 ') + 1]).toBe('tasks done 1 total 1 returns 0 approval-waits 0')
  expect(lines[at('cycles:') + 1]).toBe('CYC-0005 type quick-fix status completed pass 1 limit 1')
  expect(lines.slice(at('cycles:') + 1).filter(l => l.startsWith('CYC-')).length).toBe(5)
  expect(t).not.toContain('more')
  expect(t).not.toContain('older')
  // The other cycles draw no block: no tasks line for them.
  expect(lines.filter(l => l.startsWith('tasks done')).length).toBe(1)
})

test('the cycles list cuts at 10 lines and counts the rest', () => {
  const eleven = text(doc(Array.from({length: 12}, (_, i) => cycleRow(12 - i))))
  expect(eleven.split('\n').filter(l => /^CYC-\d+ type/.test(l)).length).toBe(10)
  expect(eleven).toContain('+1 more')
  const exact = text(doc(Array.from({length: 11}, (_, i) => cycleRow(11 - i))))
  expect(exact.split('\n').filter(l => /^CYC-\d+ type/.test(l)).length).toBe(10)
  expect(exact).not.toContain('more')
  const one = text(doc([cycleRow(1)]))
  expect(one).not.toContain('cycles:')
  expect(one).toContain('cycle CYC-0001 ')
})

test('a listed release in the cycles list omits pass and limit', () => {
  const release = {...cycleRow(7), type: 'release', phase: 'release', phases: ['release'], tasks: [{id: 'check', phase: 'release', description: 'Verify', status: 'done'}], phase_times: []}
  const t = text(doc([cycleRow(8), release]))
  expect(t.split('\n').some(l => /^CYC-0007 type release status completed( |$)/.test(l) && !l.includes('pass'))).toBe(true)
})

test('the open cycle comes first with its current task', () => {
  const t = text(doc([cycleRow(9), cycleRow(3, 'active')]))
  const lines = t.split('\n')
  const open = lines.findIndex(l => l.startsWith('cycle CYC-0003 '))
  const closed = lines.findIndex(l => l.startsWith('cycle CYC-0009 '))
  expect(open).toBeGreaterThan(-1)
  expect(open).toBeLessThan(closed)
  expect(t).toContain('current task check')
  expect(t).not.toContain('cycles:')
})

test('the queue summary covers empty, short and overflowing queues', () => {
  const empty = text(doc([cycleRow(1)], {ok: true, items: [], authorization: null}))
  expect(empty).toContain('queue queued 0 authorization none remaining none')
  expect(empty).not.toContain('queue more')
  const short = text(doc([cycleRow(1)], {
    ok: true,
    items: [qItem(1, 'started', {cycle: 'CYC-0001', cycle_status: 'completed'}), qItem(2, 'pending'), qItem(3, 'held')],
    authorization: {kind: 'queue', remaining: ['Q-0002', 'Q-0003']},
  }))
  expect(short).toContain('queue queued 2 authorization queue remaining Q-0002,Q-0003')
  expect(short).toContain('queue Q-0002 pending')
  expect(short).toContain('queue Q-0003 held')
  expect(short).toContain('queue Q-0001 completed CYC-0001')
  expect(short).not.toContain('queue more')
  const items = [
    qItem(1, 'started', {cycle: 'CYC-0001', cycle_status: 'completed'}),
    qItem(2, 'started', {cycle: 'CYC-0002', cycle_status: 'abandoned'}),
    qItem(3, 'started', {cycle: 'CYC-0003', cycle_status: 'completed'}),
    qItem(4, 'starting'), ...[5, 6, 7, 8, 9].map(n => qItem(n, 'pending')),
  ]
  const big = text(doc([cycleRow(1)], {ok: true, items, authorization: null}))
  expect(big).toContain('queue Q-0004 starting')
  expect(big).toContain('queue Q-0008 pending')
  expect(big).not.toContain('queue Q-0009 pending')
  expect(big).toContain('queue Q-0003 completed CYC-0003')
  expect(big).toContain('queue Q-0002 abandoned CYC-0002')
  expect(big).not.toContain('queue Q-0001 completed')
  // Only the one hidden upcoming item counts; the hidden finished item does not.
  expect(big).toContain('queue more 1')
  expect(text(doc([cycleRow(1)], {ok: false, error: 'broken'}))).toContain('queue unavailable')
  expect(text(doc([cycleRow(1)], null))).not.toContain('queue')
})

test('hidden finished items never produce a queue more line', () => {
  const items = [
    ...Array.from({length: 13}, (_, i) => qItem(i + 1, 'started', {cycle: `CYC-${String(i + 1).padStart(4, '0')}`, cycle_status: 'completed'})),
    ...Array.from({length: 4}, (_, i) => qItem(i + 14, 'pending')),
  ]
  expect(text(doc([cycleRow(1)], {ok: true, items, authorization: null}))).not.toContain('queue more')
})

test('the answer orders the open cycles, the queue summary, then the latest closed cycle and the cycles list', () => {
  const t = text(doc([cycleRow(9), cycleRow(8), cycleRow(7), cycleRow(6), cycleRow(5, 'active')], {ok: true, items: [qItem(1, 'pending')], authorization: null}))
  const lines = t.split('\n')
  const at = (prefix: string) => lines.findIndex(l => l.startsWith(prefix))
  expect(at('cycle CYC-0005 ')).toBeGreaterThan(-1)
  expect(at('cycle CYC-0005 ')).toBeLessThan(at('queue queued'))
  expect(at('queue queued')).toBeLessThan(at('cycle CYC-0009 '))
  expect(at('cycle CYC-0009 ')).toBeLessThan(at('cycles:'))
  expect(at('cycles:')).toBeLessThan(at('CYC-0008 type'))
  expect(at('cycle CYC-0008 ')).toBe(-1)
})

test('the answer contains no queue title', () => {
  const t = text(doc([cycleRow(1)], {ok: true, items: [qItem(1, 'pending')], authorization: null}))
  expect(t).toContain('queue Q-0001 pending')
  expect(t.includes('secret title')).toBe(false)
  expect(t.includes('Cycle title')).toBe(false)
})

test('a queue write refreshes the dashboard', () => {
  expect(touchesRunFile({tool: 'Write', file_path: '/project/bionic/queue/cycles.yaml'})).toBe(true)
  expect(touchesRunFile({tool: 'Edit', file_path: '/project/bionic/queue/cycles.yaml'})).toBe(true)
  expect(touchesRunFile({tool: 'Bash', command: 'sed -i s/a/b/ bionic/queue/cycles.yaml'})).toBe(true)
  expect(touchesRunFile({tool: 'Read', file_path: '/project/bionic/queue/cycles.yaml'})).toBe(false)
  expect(touchesRunFile({tool: 'Write', file_path: '/project/queued.ts'})).toBe(false)
})
