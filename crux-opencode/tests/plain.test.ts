import { test, expect } from 'claude-code/testing'
import { containsText, jsonText } from './fixtures/plain.ts'
import { ALL_DOCS, CONTROL_TITLE, FORMAT_TEXT, READER_EMPTY } from './fixtures/reader-docs.ts'
import { VIEW_DOC, readerErrorDoc } from './fixtures/sched-docs.ts'

test('jsonText writes the text JSON.parse reads back as the same value', () => {
  const values: unknown[] = [
    null, true, false, 0, -3, 1791687839, '', 'plain', 'a "quoted" word', 'back\\slash', 'line\nbreak', CONTROL_TITLE, FORMAT_TEXT,
    [], {}, [1, [2, null], { a: [] }], { a: 1, b: { c: ['x', false] } },
  ]
  values.forEach(v => expect(JSON.parse(jsonText(v))).toEqual(v))
  ;[...ALL_DOCS, READER_EMPTY, VIEW_DOC, readerErrorDoc('time-limit')].forEach(doc => expect(JSON.parse(jsonText(doc))).toEqual(doc))
})

test('jsonText writes the exact text of a small value, in member order', () => {
  expect(jsonText({ ok: true, stdout: 'a"b', n: [1, null] })).toBe('{"ok":true,"stdout":"a\\"b","n":[1,null]}')
  expect(jsonText({ a: 1, b: undefined })).toBe('{"a":1}')
  expect(jsonText('\u0007\ud800')).toBe('"\\u0007\\ud800"')
})

test('jsonText refuses a value that has no JSON text', () => {
  expect(() => jsonText(NaN)).toThrow()
  expect(() => jsonText(Infinity)).toThrow()
  expect(() => jsonText(() => 1)).toThrow()
})

test('containsText finds a string as a string, an array member, a key and an object value', () => {
  expect(containsText('say SECRET now', 'SECRET')).toBe(true)
  expect(containsText(['a', 'xSECRETx'], 'SECRET')).toBe(true)
  expect(containsText({ a: { b: ['SECRET'] } }, 'SECRET')).toBe(true)
  expect(containsText({ SECRET: 1 }, 'SECRET')).toBe(true)
  expect(containsText([{ ok: false, code: 'a-code' }, null, 3, true], 'SECRET')).toBe(false)
  expect(containsText({ a: 'secret' }, 'SECRET')).toBe(false)
  expect(containsText(null, 'SECRET')).toBe(false)
})
