import { test, expect } from 'claude-code/testing'
import { pane } from '../hooks/lib/draw.ts'
import type { Block } from '../hooks/lib/draw.ts'
import { answer, parseReader } from '../hooks/lib/view.ts'
import { nineteenTasks, queueParsed } from './fixtures/queue.ts'
import { applyQueueAction, queueControl, queueExpanded } from '../hooks/lib/queue.ts'
import { install, texts, PANE } from './fixtures/world.ts'
import { queueDoc } from './fixtures/queue.ts'
import { cells } from '../hooks/lib/width.ts'

const HARNESS = { bandPrefix: 'crux', stallNote: 'quiet' }
const lines = (block: Block): string[] => block.kind === 'line' ? [block.line.map(s => s.text).join('')] : block.children.flatMap(lines)
const draw = (count: number, expanded = false) => pane(queueParsed(count), { available: false }, 80, 'docked', HARNESS, 0, expanded)

test('the queue initially shows six rows and the exact hidden count', () => {
  for (const count of [0, 1, 6, 7, 14]) {
    const rows = lines(draw(count))
    expect(rows.filter(row => /^◌ Q-/.test(row)).length).toBe(Math.min(6, count))
    if (count > 6) expect(rows).toContain(`+${count - 6} more`)
    else expect(rows.some(row => row.includes(' more'))).toBe(false)
  }
})

test('expanded queues expose every ID through the parser and renderer, including more than fifty', () => {
  for (const count of [7, 14, 51, 500]) {
    const parsed = queueParsed(count)
    expect(parsed.ok).toBe(true)
    const rows = lines(draw(count, true))
    for (let n = 1; n <= count; n++) expect(rows.some(row => row.includes(`Q-${String(n).padStart(4, '0')} `))).toBe(true)
    expect(rows).toContain('Show less')
  }
})

test('text-only dashboard replies expose all queued IDs', () => {
  const text = answer(queueParsed(51))
  for (let n = 1; n <= 51; n++) expect(text).toContain(`queue Q-${String(n).padStart(4, '0')} pending`)
})

test('the reported nineteen-task cycle retains one phase progression and seven of nineteen progress', () => {
  const rows = lines(pane(queueParsed(0, [nineteenTasks()]), { available: false }, 100, 'docked', HARNESS))
  expect(rows.some(row => row.startsWith('✓ plan › ▸ build › ◌ test'))).toBe(true)
  expect(rows.some(row => row.startsWith('plan ✓ build '))).toBe(false)
  expect(rows.some(row => row.includes('7/19 tasks'))).toBe(true)
  expect(rows.filter(row => /^(✓|▸|◌) (plan|build|test|review|reflect):/.test(row)).length).toBe(19)
})

test('queue actions are root-bound, current, idempotent and survive refresh counts', () => {
  const parsed = queueParsed(14)
  if (!parsed.ok) throw new Error('fixture refused')
  const more = queueControl(parsed.view.queue, false)!
  expect(more.label).toBe('+8 more')
  const state = applyQueueAction(parsed, null, '/first', more.action)!
  expect(queueExpanded(state, '/first')).toBe(true)
  expect(queueExpanded(state, '/second')).toBe(false)
  expect(applyQueueAction(parsed, state, '/first', more.action)).toBeNull()
  expect(queueExpanded(state, '/first')).toBe(true)
  const refreshed = queueParsed(51)
  expect(applyQueueAction(refreshed, state, '/first', more.action)).toBeNull()
  expect(queueExpanded(state, '/first')).toBe(true)
  if (!refreshed.ok) throw new Error('fixture refused')
  const less = queueControl(refreshed.view.queue, true)!
  expect(less.label).toBe('Show less')
  expect(applyQueueAction(refreshed, state, '/first', less.action)).toEqual({ root: '/first', expanded: false })
  const short = queueParsed(6)
  if (!short.ok) throw new Error('fixture refused')
  expect(queueControl(short.view.queue, true)).toBeNull()
})

test('every expanded queue line fits narrow widths and strips unsafe title controls', () => {
  const doc = queueDoc(14)
  doc.queue.items[0]!.title = '漢字 <text>\u001b[31m\nsecond line\tend'
  const parsed = parseReader(JSON.stringify(doc))
  for (const width of [1, 5, 20, 30, 40, 60]) {
    const block = pane(parsed, { available: false }, width, 'docked', HARNESS, 0, true)
    for (const row of lines(block)) {
      expect(cells(row)).toBeLessThanOrEqual(width)
      expect(/[\u0000-\u001f\u007f]/.test(row)).toBe(false)
    }
  }
})

test('Claude queue buttons expand and collapse the actual pane without new reader calls', async ($, on) => {
  const world = install(on, { reader: { exitCode: 0, stdout: JSON.stringify(queueDoc(14)) } })
  await $.command.run({ command: 'crux-dashboard' } as any)
  const ui = await $.ui.mount({ plugin: 'crux-mods', surface: 'terminal', component: 'Pane', requestId: 'crux-dashboard', props: PANE })
  const text = async () => texts(await ui.drawn()).join('\n')
  expect(await text()).toContain('+8 more')
  expect(await text()).not.toContain('Q-0014')
  const button = await ui.find({ type: 'Button', key: 'queue-toggle' }) as any
  expect(button.props.hotkey).toBe('q')
  const calls = world.runs.length
  await ui.press({ key: 'queue-toggle' })
  expect(await text()).toContain('Q-0014')
  expect(await text()).toContain('Show less')
  await ui.press({ key: 'queue-toggle' })
  expect(await text()).not.toContain('Q-0014')
  expect(await text()).toContain('+8 more')
  expect(world.runs.length).toBe(calls)
  await ui.unmount()
})
