import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { capabilities } from '../capabilities.ts'

const source = readFileSync(new URL('../capabilities.ts', import.meta.url), 'utf8')
const between = source.split('// BEGIN CAPABILITIES')[1]?.split('// END CAPABILITIES')[0] ?? ''

test('the manifest is strict JSON between its markers', () => {
  const body = between.trim().replace(/^export const capabilities =\s*/, '').replace(/\s*as const;\s*$/, '')
  const parsed = JSON.parse(body)
  assert.deepEqual(parsed, capabilities)
})

test('the manifest names the OMP host, entry and UI surface', () => {
  assert.equal(capabilities.extension_id, 'crux-omp')
  assert.equal(capabilities.host, 'omp')
  assert.equal(capabilities.entry, 'index.ts')
  assert.equal(capabilities.label, 'Crux dashboard')
  assert.deepEqual([...capabilities.ui_methods], ['setStatus', 'setWidget', 'notify'])
  assert.deepEqual([...capabilities.env_reads], ['HOME'])
})

test('the manifest subscribes to the lifecycle, subagent, tool and input events', () => {
  assert.deepEqual([...capabilities.events], [
    'session_start',
    'session_switch',
    'session_shutdown',
    'before_subagent_spawn',
    'tool_execution_start',
    'tool_execution_update',
    'tool_execution_end',
    'tool_result',
    'input',
  ])
  assert.deepEqual([...capabilities.commands], ['crux-dashboard'])
})

test('the launch block keeps the reader contract', () => {
  const launch = capabilities.launch
  assert.deepEqual([...launch.uv_args], ['run', '--offline', '--no-project', '--no-config', '--quiet'])
  assert.deepEqual([...launch.scripts['visualize-run-progress'].args], ['--json', '--project-root', '{project_root}'])
  assert.equal(launch.scripts['visualize-run-progress'].path, 'scripts/visualize-run-progress.py')
  assert.equal(launch.timeout_ms, 10000)
})
