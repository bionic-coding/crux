import { test } from 'node:test'
import assert from 'node:assert/strict'
import { READ_CAP, openSink, startReader } from '../lib/reader.ts'
import type { Ended } from '../lib/reader.ts'
import type { Planned } from '../lib/host.ts'
import { CLONE, HOME, PROJECT, SCRIPT, UV, makeFake } from './fixtures/fake.ts'
import { VIEW_STDOUT } from './fixtures/docs.ts'

function rig() {
  const ends: Ended[] = []
  const state = { kills: 0 }
  const run = openSink({
    kill: () => {
      state.kills += 1
    },
    end: e => {
      ends.push(e)
    },
  })
  return { run, ends, state }
}

const ascii = (s: string) => Array.from(s, c => c.charCodeAt(0))

test('ASCII output split across byte arrays decodes to one text', () => {
  const { run, ends } = rig()
  const doc = '{"ok":true,"k":"v"}'
  for (let i = 0; i < doc.length; i += 3) run.out(ascii(doc.slice(i, i + 3)))
  assert.equal(ends.length, 0)
  run.closed(0)
  assert.deepEqual(ends, [{ ok: true, stdout: doc }])
})

test('a non-ASCII stdout byte ends the read as reader-output-invalid and kills', () => {
  const { run, ends, state } = rig()
  run.out([0x7b, 0x80])
  assert.equal(state.kills, 1)
  assert.equal(run.status(), 'reader-output-invalid')
  assert.equal(ends.length, 0)
  run.closed(0)
  assert.deepEqual(ends, [{ ok: false, code: 'reader-output-invalid' }])
})

test('output past the read cap is refused', () => {
  const { run, ends } = rig()
  const chunk = Array.from({ length: READ_CAP + 1 }, () => 0x20)
  run.out(chunk)
  run.closed(0)
  assert.deepEqual(ends, [{ ok: false, code: 'reader-output-invalid' }])
})

test('an error before spawn ends the run as reader-cannot-start', () => {
  const { run, ends } = rig()
  run.failed()
  assert.deepEqual(ends, [{ ok: false, code: 'reader-cannot-start' }])
})

test('an error after spawn ends nothing; the close ends the run', () => {
  const { run, ends } = rig()
  run.spawned()
  run.failed()
  assert.equal(ends.length, 0)
  run.closed(0)
  assert.equal(ends.length, 1)
})

test('a recorded status wins over the finished classification', () => {
  const { run, ends } = rig()
  run.record('reader-timeout')
  run.out(ascii(VIEW_STDOUT))
  run.closed(0)
  assert.deepEqual(ends, [{ ok: false, code: 'reader-timeout' }])
})

test('startReader starts the launcher with -i and the planned cwd', () => {
  const fake = makeFake()
  const plan: Planned = { ok: true, uv: UV, crux: `${CLONE}/crux`, home: HOME, root: PROJECT }
  const handle = startReader(fake.host, plan, openSink({ kill: () => {}, end: () => {} }))
  assert.ok(handle !== undefined && handle !== 'untracked')
  const proc = fake.procs[0]!
  assert.equal(proc.argv[0], '-i')
  assert.equal(proc.cwd, `${CLONE}/crux`)
  assert.ok(proc.argv.includes(UV))
  assert.ok(proc.argv.includes(SCRIPT))
  assert.ok(proc.argv.includes(PROJECT))
})

test('startReader starts nothing when the host starts nothing', () => {
  const fake = makeFake()
  fake.startMode.value = 'undefined'
  const plan: Planned = { ok: true, uv: UV, crux: `${CLONE}/crux`, home: HOME, root: PROJECT }
  assert.equal(startReader(fake.host, plan, openSink({ kill: () => {}, end: () => {} })), undefined)
})
