import { test } from 'node:test'
import assert from 'node:assert/strict'
import { KEPT_CODES, PLAN_CODES, READER_FAILED_CODES, RUN_CODE_LIST, VIEW_CODE_LIST } from '../lib/status.ts'
import { RUN_CODES } from '../../crux-mods/hooks/lib/launch.ts'
import { READER_ERROR_CODES, VIEW_CODES } from '../../crux-mods/hooks/lib/view.ts'

test('the kept set holds every plan, run, view and reader-failed code', () => {
  for (const code of [...PLAN_CODES, ...RUN_CODE_LIST, ...VIEW_CODE_LIST, ...READER_FAILED_CODES]) {
    assert.equal(KEPT_CODES.includes(code), true, code)
  }
})

test('the run codes are this plugin\'s two and the core\'s five', () => {
  assert.deepEqual([...RUN_CODE_LIST], ['reader-timeout', 'reader-cannot-start', ...RUN_CODES])
})

test('the view codes are the core\'s view codes', () => {
  assert.deepEqual([...VIEW_CODE_LIST], [...VIEW_CODES])
})

test('each reader error is kept under the reader-failed prefix', () => {
  assert.deepEqual([...READER_FAILED_CODES], READER_ERROR_CODES.map(code => 'reader-failed:' + code))
})
