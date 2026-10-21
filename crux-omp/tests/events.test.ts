import { test } from 'node:test'
import assert from 'node:assert/strict'
import { asksForTheRun, touchesRunFile } from '../lib/events.ts'

test('the run phrases match after spacing, case and one closing mark', () => {
  for (const text of ['show the run', '  SHOW   THE RUN. ', 'run status?', 'Run Status!', 'show run progress']) {
    assert.equal(asksForTheRun({ text, source: 'interactive' }), true, text)
  }
})

test('another prompt does not ask for the run', () => {
  for (const text of ['show the dashboard', 'run', 'show the runs', 'status']) {
    assert.equal(asksForTheRun({ text, source: 'interactive' }), false, text)
  }
})

test('an attached image, a programmatic source, or a non-string text does not ask', () => {
  assert.equal(asksForTheRun({ text: 'show the run', source: 'interactive', images: ['x'] }), false)
  assert.equal(asksForTheRun({ text: 'show the run', source: 'synthetic' }), false)
  assert.equal(asksForTheRun({ text: 1, source: 'interactive' }), false)
  assert.equal(asksForTheRun(null), false)
})

test('a write or edit under a run directory touches the run', () => {
  const docs = '/repo/bionic'
  assert.equal(touchesRunFile('write', { path: `${docs}/promptbooks/runs/PB-1/run-RUN-001.yaml` }, docs), true)
  assert.equal(touchesRunFile('edit', { file_path: `${docs}/cycles/CYCLE-1.yml` }, docs), true)
  assert.equal(touchesRunFile('write', { path: '/repo/src/index.ts' }, docs), false)
})

test('a bash command naming a run or cycle touches the run', () => {
  assert.equal(touchesRunFile('bash', { command: 'python3 crux/scripts/cycle.py advance' }, '/repo/bionic'), true)
  assert.equal(touchesRunFile('bash', { command: 'cat bionic/promptbooks/runs/PB-1/run-RUN-001.yaml' }, '/repo/bionic'), true)
  assert.equal(touchesRunFile('bash', { command: 'git status' }, '/repo/bionic'), false)
})

test('without a known docs directory the run-directory segments still match', () => {
  assert.equal(touchesRunFile('write', { path: '/elsewhere/promptbooks/runs/PB-1/run.yaml' }), true)
  assert.equal(touchesRunFile('write', { path: '/elsewhere/cycles/CYCLE-1.yml' }), true)
  assert.equal(touchesRunFile('write', { path: 'promptbooks/runs/PB-1/run.yaml' }), true)
})

test('another tool, or a malformed event, touches nothing', () => {
  assert.equal(touchesRunFile('read', { path: '/repo/bionic/cycles/CYCLE-1.yml' }), false)
  assert.equal(touchesRunFile('write', null), false)
  assert.equal(touchesRunFile(undefined, {}), false)
})
