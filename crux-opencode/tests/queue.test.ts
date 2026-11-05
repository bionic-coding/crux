import { test, expect } from 'claude-code/testing'
import { queueControl, queueExpanded } from '../../crux-mods/hooks/lib/queue.ts'
import { queueParsed, nineteenTasks } from './fixtures/queue.ts'
import { queueClick, toggleQueue } from '../lib/queue.ts'
import { panelNode } from '../lib/render.ts'
import type { PlainNode } from '../lib/render.ts'
import { makeFake } from './fixtures/fake.ts'
import { createScheduler, HOLD_MS } from '../lib/refresh.ts'
import { readView } from '../lib/render.ts'
import { queueDoc } from './fixtures/queue.ts'
import { createFocusSlot } from '../lib/focus.ts'

const actions = (node: PlainNode | null): NonNullable<Extract<PlainNode, { kind: 'text' }>['action']>[] => {
  if (node === null || node.kind === 'spacer') return []
  return node.kind === 'text' ? node.action === undefined ? [] : [node.action] : node.children.flatMap(actions)
}
const strings = (node: PlainNode | null): string[] => node === null || node.kind === 'spacer' ? [] : node.kind === 'text' ? [node.spans.map(s => s.text).join('')] : node.children.flatMap(strings)

test('OpenCode draws the real shared action and shows every queued ID when expanded', () => {
  for (const count of [7, 14, 51, 500]) {
    const parsed = queueParsed(count)
    const collapsed = panelNode(parsed, 'crux-dashboard', 60, 0)
    expect(strings(collapsed)).toContain(`+${count - 6} more`)
    expect(actions(collapsed).length).toBe(1)
    const expanded = panelNode(parsed, 'crux-dashboard', 60, 0, true)
    expect(strings(expanded)).toContain('Show less')
    for (let n = 1; n <= count; n++) expect(strings(expanded).some(row => row.includes(`Q-${String(n).padStart(4, '0')} `))).toBe(true)
  }
})

test('an owned left click expands, repeated click declines, collapse works and disposed clicks decline', () => {
  const fake = makeFake()
  fake.opens.open = true
  let active = true
  const parsed = queueParsed(14)
  const click = queueClick(fake.host, () => parsed, '/proj', () => active)
  const more = actions(panelNode(parsed, 'crux-dashboard', 60, 0))[0]!
  expect(click(more, 2)).toBe(false)
  expect(click(more, 0)).toBe(true)
  expect(queueExpanded(fake.mem.queue, '/proj')).toBe(true)
  expect(click(more, 0)).toBe(false)
  const less = actions(panelNode(parsed, 'crux-dashboard', 60, 0, true))[0]!
  expect(click(less, 0)).toBe(true)
  active = false
  expect(click(more, 0)).toBe(false)
  expect(queueExpanded(fake.mem.queue, '/proj')).toBe(false)
})

test('old root and old queue controls decline while refresh preserves expansion', () => {
  const fake = makeFake()
  fake.opens.open = true
  let parsed = queueParsed(14)
  const click = queueClick(fake.host, () => parsed, '/proj', () => true)
  const more = actions(panelNode(parsed, 'crux-dashboard', 60, 0))[0]!
  expect(click(more, 0)).toBe(true)
  parsed = queueParsed(51)
  expect(queueExpanded(fake.mem.queue, '/proj')).toBe(true)
  expect(click(more, 0)).toBe(false)
  fake.world.directory = '/other'
  expect(queueExpanded(fake.mem.queue, '/other')).toBe(false)
  expect(click(more, 0)).toBe(false)
  expect(queueClick(fake.host, () => parsed, '/other', () => true)(actions(panelNode(parsed, 'crux-dashboard', 60, 0))[0]!, 0)).toBe(true)
})

test('q declines with literal false for closed/unfocused panels and consumes only an owned action', () => {
  const fake = makeFake()
  const parsed = queueParsed(14)
  expect(toggleQueue(fake.host, parsed)).toBe(false)
  fake.opens.open = true
  expect(toggleQueue(fake.host, parsed)).toBe(false)
  fake.pager.focused = true
  expect(toggleQueue(fake.host, parsed)).toBe(true)
  expect(toggleQueue(fake.host, parsed)).toBe(true)
  expect(toggleQueue(fake.host, queueParsed(6))).toBe(false)
  expect(toggleQueue(fake.host, null)).toBe(false)
  fake.pager.writeFails = true
  expect(toggleQueue(fake.host, parsed)).toBe(false)
})

test('the nineteen-task OpenCode card has one phase header and all task rows', () => {
  const rows = strings(panelNode(queueParsed(0, [nineteenTasks()]), 'crux-dashboard', 100, 0))
  expect(rows.some(row => row.startsWith('plan ✓ build '))).toBe(false)
  expect(rows.some(row => row.includes('7/19 tasks'))).toBe(true)
  expect(rows.filter(row => /^(✓|▸|◌) (plan|build|test|review|reflect):/.test(row)).length).toBe(19)
})

test('a reader started in the previous project cannot populate the new project queue', () => {
  const fake = makeFake()
  const scheduler = createScheduler(fake.host)
  scheduler.start()
  fake.clock.advance(HOLD_MS)
  expect(fake.procs.length).toBe(1)
  fake.world.directory = '/other'
  fake.procs[0]!.finish(JSON.stringify(queueDoc(14)))
  expect(fake.mem.currentRoot).toBe('/proj')
  expect(readView(true, () => fake.mem.current, '/other', fake.mem.currentRoot)).toBeNull()
  expect(readView(true, () => fake.mem.current, '/proj', fake.mem.currentRoot)?.ok).toBe(true)
  scheduler.stop()
})

test('panel remount and cleanup revoke only their own queue click lifetime', () => {
  const slot = createFocusSlot()
  const old = () => false
  const next = () => false
  const release = slot.publish(old)
  expect(slot.owns(old)).toBe(true)
  slot.publish(next)
  expect(slot.owns(old)).toBe(false)
  release()
  expect(slot.owns(next)).toBe(true)
  slot.clear()
  expect(slot.owns(next)).toBe(false)
})
