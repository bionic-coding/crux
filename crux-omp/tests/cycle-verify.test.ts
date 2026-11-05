// crux-omp reads both phase vocabularies and draws the `verify` phase in Test's colour key, never in
// Review's. The completeness scan keeps every phase table that names `review` and `test` naming
// `verify` too, in the shared core and in this extension.
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync, readdirSync } from 'node:fs'
import { panelLines, readView } from '../lib/render.ts'
import { buildOmpCyclesPane } from '../lib/live.ts'
import { parseReader } from '../../crux-mods/hooks/lib/view.ts'
import type { Block, Span } from '../../crux-mods/hooks/lib/draw.ts'
import { jsonText } from './fixtures/plain.ts'

const TEST_SEQ = ['plan', 'build', 'test', 'review', 'reflect']
const row = (phases: string[], phase: string, over: Record<string, unknown> = {}) => ({
  id: 'CYC-0007', schema_version: 3, revision: 4, assignments: [], classification_count: 0, exception: null,
  title: 'A cycle', type: 'dev', status: 'active', phase, pass: 1, pass_limit: 2, phases,
  tasks: phases.map(p => ({ id: 't-' + p, phase: p, description: 'Work in ' + p, status: 'active' })),
  returns: [], waits: [], blocker: null, reflection: null, modified_s: 1780000000, started_s: 1779999000,
  ended_s: null, paused_s: 0, open_started_s: 1779999500, basis: 'recorded', phase_times: [], ...over,
})
const doc = (cycles: unknown[]) => ({ format: 'crux.cycle-progress', format_version: 5, ok: true, docs_dir: 'bionic', now_s: 1780000000, cycles })
const readOf = (d: unknown) => readView(() => ({ ok: true, stdout: jsonText(d) }))
const textOf = (d: unknown): string => {
  const p = readOf(d)
  assert.ok(p !== null && p.ok, 'the document did not read as a view')
  const lines = panelLines(p, 120)
  assert.ok(lines !== null)
  return lines.join('\n')
}
const spansOf = (b: Block): Span[] => (b.kind === 'line' ? b.line : b.children.flatMap(spansOf))
const colourOf = (phases: string[], word: string) => {
  const p = parseReader(jsonText(doc([row(phases, phases[0]!)])))
  assert.ok(p.ok && p.view.cycles !== undefined, 'the document did not parse')
  const found = spansOf(buildOmpCyclesPane(p.view.cycles, p.view.now_s, undefined, 120)).filter(s => s.text === word)
  assert.ok(found.length > 0, `no span drew ${word}`)
  return found[0]!.color
}

test('a record of either vocabulary reads and draws its phase', () => {
  for (const word of ['test', 'verify']) {
    const phases = TEST_SEQ.map(p => (p === 'test' ? word : p))
    assert.match(textOf(doc([row(phases, 'build')])), new RegExp('Work in ' + word))
  }
})

test('a release cycle reads and draws its verify step as a task', () => {
  const release = row(['release'], 'release', {
    type: 'release', pass_limit: 1,
    tasks: [{ id: 'verify', phase: 'release', description: 'Run release verify', status: 'active' }],
  })
  assert.match(textOf(doc([release])), /Run release verify/)
})

test('verify draws in the colour of test and not the colour of review', () => {
  const verifyPhases = TEST_SEQ.map(p => (p === 'test' ? 'verify' : p))
  const verify = colourOf(verifyPhases, 'verify')
  assert.equal(verify, colourOf(TEST_SEQ, 'test'))
  assert.notEqual(verify, colourOf(verifyPhases, 'review'))
})

// --- completeness scan -----------------------------------------------------------------------------

const DIRS = ['../../crux-mods/hooks/lib/', '../lib/']
// A literal is an array or object with no literal inside it; an enclosing object is read by its parts.
const LITERAL = /\[[^[\]]*\]|\{[^{}]*\}/g
const names = (body: string, word: string) => new RegExp(`['"]${word}['"]|(?:^|[\\s,{])${word}\\s*:`).test(body)

test('every phase table that names review and test names verify', () => {
  let scanned = 0
  const missing: string[] = []
  for (const dir of DIRS) {
    const base = new URL(dir, import.meta.url)
    for (const file of readdirSync(base).filter(f => f.endsWith('.ts'))) {
      const text = readFileSync(new URL(file, base), 'utf8')
      // The historical sequence table holds the `test` sequences on purpose; verifyOf derives the new ones.
      const table = /const CYCLE_PHASES[^=]*=\s*\{[\s\S]*?\n\}/.exec(text)
      const exempt = table === null ? null : [table.index, table.index + table[0].length]
      for (const m of text.matchAll(LITERAL)) {
        if (exempt !== null && m.index >= exempt[0] && m.index < exempt[1]) continue
        if (names(m[0], 'review') && names(m[0], 'test')) {
          scanned++
          if (!names(m[0], 'verify')) missing.push(`${file}: ${m[0].slice(0, 70)}`)
        }
      }
    }
  }
  // Positive control: the scan met the phase tables it guards.
  assert.ok(scanned >= 3, `the scan met ${scanned} tables`)
  assert.deepEqual(missing, [])
})
