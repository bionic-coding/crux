import { test, expect } from 'claude-code/testing'
import {
  BAND_PREFIX, DRAW_ONLY, HARNESS, INVALID, KEPT_CODES, OWN_RUN_CODES, PLAN_CODES, READER_FAILED_CODES, RUN_CODE_LIST, STALL_NOTE,
  UNAVAILABLE_AGENTS, UNSUPPORTED, UNSUPPORTED_WORDS, VIEW_CODE_LIST,
} from '../lib/status.ts'
import { kept } from '../../crux-mods/hooks/lib/view.ts'

// The expected sets are written out here, apart from status.ts and the core.
const PLAN = ['project-root-unresolved', 'home-invalid', 'crux-not-found', 'uv-not-found', 'inside-project', 'version-mismatch']
const OWN_RUN = ['reader-timeout', 'reader-cannot-start']
const CORE_RUN = ['reader-no-json-mode', 'offline-unavailable', 'reader-cpu-limit', 'reader-failed', 'reader-output-invalid']
const VIEW = ['reader-output-invalid', 'no-active-run', 'reader-format-mismatch']
const READER_ERRORS = [
  'usage', 'project-root-invalid', 'config-invalid', 'tree-missing', 'containment', 'book-not-found', 'run-not-found', 'run-invalid',
  'book-invalid', 'token-set-unavailable', 'yaml-unavailable', 'time-limit', 'internal',
]

test('the plan codes are the six, in order', () => {
  expect(PLAN_CODES).toEqual(PLAN)
  expect(PLAN_CODES.length).toBe(6)
})

test('the run codes are the two crux-opencode records and the core five', () => {
  expect(OWN_RUN_CODES).toEqual(OWN_RUN)
  expect(RUN_CODE_LIST).toEqual([...OWN_RUN, ...CORE_RUN])
})

test('the view codes and the reader-failed codes are the core sets', () => {
  expect(VIEW_CODE_LIST).toEqual(VIEW)
  expect(READER_FAILED_CODES).toEqual(READER_ERRORS.map(c => `reader-failed:${c}`))
  expect(READER_FAILED_CODES.length).toBe(13)
})

test('the draw-only codes are the two, and no kept code is one of them', () => {
  expect(DRAW_ONLY).toEqual(['opencode-version-unsupported', 'panel-unavailable'])
  DRAW_ONLY.forEach(code => expect(KEPT_CODES).not.toContain(code))
})

test('the kept set is the plan, run, view and reader-failed codes and nothing else', () => {
  const want = [...PLAN, ...OWN_RUN, ...CORE_RUN, ...VIEW, ...READER_ERRORS.map(c => `reader-failed:${c}`)]
  want.forEach(code => expect(KEPT_CODES).toContain(code))
  KEPT_CODES.forEach(code => expect(want).toContain(code))
})

test('a code of Claude Code stays out of every part, and so does the plan code of its session root', () => {
  const absent = ['no-env-binary', 'config-dir-mismatch', 'crux-not-installed', 'project-root-invalid']
  absent.forEach(code => {
    expect(PLAN_CODES).not.toContain(code)
    expect(OWN_RUN_CODES).not.toContain(code)
    expect(RUN_CODE_LIST).not.toContain(code)
    expect(VIEW_CODE_LIST).not.toContain(code)
    expect(DRAW_ONLY).not.toContain(code)
    expect(KEPT_CODES).not.toContain(code)
  })
  // The reader's own error of that name stays, under its prefix.
  expect(KEPT_CODES).toContain('reader-failed:project-root-invalid')
})

test('the two status values are Parsed values with their codes', () => {
  expect(UNSUPPORTED).toEqual({ ok: false, code: 'opencode-version-unsupported' })
  expect(INVALID).toEqual({ ok: false, code: 'reader-output-invalid' })
})

test('the wordings', () => {
  expect(BAND_PREFIX).toBe('crux-opencode dashboard: ')
  expect(UNSUPPORTED_WORDS).toBe('unsupported OpenCode version')
  expect(STALL_NOTE).toBe('Work this view cannot see can run for a long time without changing the run file.')
  expect(HARNESS).toEqual({ bandPrefix: BAND_PREFIX, stallNote: STALL_NOTE })
  expect(UNAVAILABLE_AGENTS).toEqual({ available: false, running: 0, shown: [] })
})

test('every kept code reads back as itself through the core with the kept set', () => {
  KEPT_CODES.forEach(code => {
    expect(kept({ ok: false, code }, KEPT_CODES)).toEqual({ ok: false, code })
  })
})

test('the round trip is not vacuous: a code outside the set reads back as reader-output-invalid', () => {
  expect(kept({ ok: false, code: 'no-env-binary' }, KEPT_CODES)).toEqual(INVALID)
  expect(kept({ ok: false, code: 'a-code-nobody-defined' }, KEPT_CODES)).toEqual(INVALID)
})

test('each draw-only code reads back as reader-output-invalid', () => {
  DRAW_ONLY.forEach(code => {
    expect(kept({ ok: false, code }, KEPT_CODES)).toEqual({ ok: false, code: 'reader-output-invalid' })
  })
})
