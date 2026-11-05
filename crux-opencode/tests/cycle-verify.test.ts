// crux-opencode reads and draws records of both phase vocabularies (`test` before the rename, `verify`
// after it) and a release cycle, through the shared core.
import { test, expect } from 'claude-code/testing'
import { panelNode, readView } from '../lib/render.ts'
import { cycleRow, doc, plain, rowsOf } from './fixtures/cycles.ts'
import { jsonText } from './fixtures/plain.ts'

const TEST_SEQ = ['plan', 'build', 'test', 'review', 'reflect']
const recordOf = (phases: string[], over: Record<string, unknown> = {}) => ({
  ...cycleRow(3, 'active'), schema_version: 3, revision: 1, phases, phase: phases[0], phase_times: [],
  tasks: phases.map(p => ({ id: 't-' + p, phase: p, description: 'Work in ' + p, status: 'pending' })), ...over,
})
const linesOf = (d: unknown): string[] => {
  const p = readView(true, () => ({ ok: true, stdout: jsonText(d) }))
  if (p === null || !p.ok) throw new Error('the document did not read as a view')
  return rowsOf(panelNode(p, 'crux-dashboard', 100, 0)).map(plain)
}

test('a record of either vocabulary reads and draws its checking phase', () => {
  for (const word of ['test', 'verify']) {
    const text = linesOf(doc([recordOf(TEST_SEQ.map(p => (p === 'test' ? word : p)))])).join('\n')
    expect(text).toContain('Work in ' + word)
  }
})

test('a record that mixes the two vocabularies is refused', () => {
  const mixed = recordOf(['plan', 'build', 'test', 'verify', 'review', 'reflect'])
  expect(readView(true, () => ({ ok: true, stdout: jsonText(doc([mixed])) }))?.ok).toBe(false)
})

test('a release cycle draws its verify step as a task', () => {
  const release = recordOf(['release'], {
    type: 'release', pass_limit: 1,
    tasks: [{ id: 'verify', phase: 'release', description: 'Run release verify', status: 'active' }],
  })
  expect(linesOf(doc([release])).join('\n')).toContain('Run release verify')
})
