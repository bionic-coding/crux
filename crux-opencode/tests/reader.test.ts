import { test, expect } from 'claude-code/testing'
import { ERR_CAP, READ_CAP, openSink, startReader } from '../lib/reader.ts'
import type { Ended, RunSink } from '../lib/reader.ts'
import type { Planned } from '../lib/host.ts'
import { planLaunch } from '../lib/plan.ts'
import { CLONE, HOME, PROJECT, SCRIPT, UV, makeFake, okWorld } from './fixtures/fake.ts'
import { jsonText } from './fixtures/plain.ts'
import { VIEW_DOC, readerErrorDoc } from './fixtures/sched-docs.ts'

const OK_STDOUT = jsonText(VIEW_DOC)

// A sink with its hooks recorded: the ends it reports and the kills it asks for.
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
const blank = (n: number) => Array.from({ length: n }, () => 0x20)
// A value the type system does not know: null.
const nothing = JSON.parse('null')

// --- decoding ------------------------------------------------------------------

test('ASCII output split across byte arrays decodes to one text', () => {
  const { run, ends } = rig()
  const doc = '{"ok":true,"k":"v"}'
  for (let i = 0; i < doc.length; i += 3) run.out(ascii(doc.slice(i, i + 3)))
  expect(ends.length).toBe(0)
  run.closed(0)
  expect(ends).toEqual([{ ok: true, stdout: doc }])
})

test('a text longer than one decoder slice decodes whole', () => {
  const { run, ends } = rig()
  const text = '{"pad":"' + 'a'.repeat(10000) + '"}'
  run.out(ascii(text))
  run.closed(0)
  expect(ends).toEqual([{ ok: true, stdout: text }])
})

for (const bad of [0x80, 0xff, 0x100, 0xe9, -1, -2, 65.5, NaN, Infinity]) {
  test(`stdout byte ${bad} ends the read as reader-output-invalid and kills`, () => {
    const { run, ends, state } = rig()
    run.out(ascii('{"a":'))
    run.out([0x31, bad, 0x7d])
    expect(state.kills).toBe(1)
    expect(run.status()).toBe('reader-output-invalid')
    // The run is still open until the process closes.
    expect(ends.length).toBe(0)
    run.closed(0)
    expect(ends).toEqual([{ ok: false, code: 'reader-output-invalid' }])
  })
}

test('the bounds of ASCII are accepted: 0 and 0x7f', () => {
  const { run, ends, state } = rig()
  run.out([0x7b, 0, 0x7f, 0x7d])
  expect(state.kills).toBe(0)
  run.closed(0)
  expect(ends.length).toBe(1)
  expect(ends[0]!.ok).toBe(true)
})

test('output after a refusal is ignored and the kill is asked once', () => {
  const { run, ends, state } = rig()
  run.out([0x80])
  run.out(ascii('{"x":1}'))
  run.out([0x81])
  expect(state.kills).toBe(1)
  run.closed(0)
  expect(ends).toEqual([{ ok: false, code: 'reader-output-invalid' }])
})

test('the first recorded status wins', () => {
  const { run, ends } = rig()
  run.out([0x80])
  run.record('reader-timeout')
  run.closed(0)
  expect(ends).toEqual([{ ok: false, code: 'reader-output-invalid' }])
  const second = rig()
  second.run.record('reader-timeout')
  second.run.out([0x80])
  second.run.closed(0)
  expect(second.ends).toEqual([{ ok: false, code: 'reader-timeout' }])
})

test('output at the cap is accepted and one byte more is refused', () => {
  const doc = (n: number) => '{' + ' '.repeat(n - 2) + '}'
  const atCap = rig()
  atCap.run.out(ascii(doc(READ_CAP)))
  expect(atCap.state.kills).toBe(0)
  atCap.run.closed(0)
  expect(atCap.ends.length).toBe(1)
  expect(atCap.ends[0]!.ok).toBe(true)

  const over = rig()
  over.run.out(ascii(doc(READ_CAP)))
  over.run.out([0x20])
  expect(over.state.kills).toBe(1)
  expect(over.run.status()).toBe('reader-output-invalid')
  over.run.closed(0)
  expect(over.ends).toEqual([{ ok: false, code: 'reader-output-invalid' }])
})

test('the cap is 1 MiB and the stderr cap is 64 KiB', () => {
  expect(READ_CAP).toBe(1048576)
  expect(ERR_CAP).toBe(65536)
})

test('output past the cap in many chunks is refused', () => {
  const { run, state } = rig()
  for (let i = 0; i < 20; i++) run.out(blank(65536))
  expect(state.kills).toBe(1)
})

// --- stderr --------------------------------------------------------------------

test('stderr selects the classification and is never kept', () => {
  const usage = rig()
  usage.run.err(ascii('usage: visualize-run-progress\nerror: unrecognized arguments: --json'))
  usage.run.closed(2)
  expect(usage.ends).toEqual([{ ok: false, code: 'reader-no-json-mode' }])

  const offline = rig()
  offline.run.err(ascii('error: No interpreter found'))
  offline.run.closed(2)
  expect(offline.ends).toEqual([{ ok: false, code: 'offline-unavailable' }])
})

test('a byte above 0x7f in stderr becomes a replacement and does not end the read', () => {
  const { run, ends, state } = rig()
  run.err([0xe9, 0x80, -1, ...ascii('offline')])
  run.out(ascii('{"a":1}'))
  expect(state.kills).toBe(0)
  expect(run.status()).toBe(undefined)
  run.closed(2)
  // Standard output opens with a brace, so the answer is the output.
  expect(ends).toEqual([{ ok: true, stdout: '{"a":1}' }])
  const bare = rig()
  bare.run.err([0xe9, 0x80, -1, ...ascii('offline')])
  bare.run.closed(1)
  expect(bare.ends).toEqual([{ ok: false, code: 'offline-unavailable' }])
})

test('stderr past 64 KiB is dropped', () => {
  const within = rig()
  within.run.err(blank(ERR_CAP - 7))
  within.run.err(ascii('offline'))
  within.run.closed(1)
  // Positive control: the wording inside the cap selects offline-unavailable.
  expect(within.ends).toEqual([{ ok: false, code: 'offline-unavailable' }])

  const beyond = rig()
  beyond.run.err(blank(ERR_CAP))
  beyond.run.err(ascii('offline'))
  beyond.run.closed(1)
  expect(beyond.ends).toEqual([{ ok: false, code: 'reader-failed' }])
})

test('stderr decoding refuses nothing and kills nothing at any size', () => {
  const { run, state } = rig()
  for (let i = 0; i < 4; i++) run.err(blank(ERR_CAP))
  expect(state.kills).toBe(0)
})

// --- ending a run --------------------------------------------------------------

test('a run ends exactly once', () => {
  const { run, ends } = rig()
  run.closed(0)
  run.closed(0)
  run.failed()
  run.closed(1)
  expect(ends.length).toBe(1)
})

test('events after the end are ignored', () => {
  const { run, ends, state } = rig()
  run.out(ascii('{"a":1}'))
  run.closed(0)
  expect(ends.length).toBe(1)
  run.out([0x80])
  run.err([0x80])
  run.exited()
  run.spawned()
  expect(state.kills).toBe(0)
  expect(ends.length).toBe(1)
  expect(run.hasEnded()).toBe(true)
})

test('an error before spawn ends the run as reader-cannot-start, and the close after it is ignored', () => {
  const { run, ends } = rig()
  run.failed()
  expect(ends).toEqual([{ ok: false, code: 'reader-cannot-start' }])
  run.closed(-2)
  expect(ends.length).toBe(1)
  expect(ends[0]).toEqual({ ok: false, code: 'reader-cannot-start' })
})

test('an error after spawn ends nothing', () => {
  const { run, ends } = rig()
  run.spawned()
  run.failed()
  expect(ends.length).toBe(0)
  expect(run.hasEnded()).toBe(false)
  run.out(ascii('{"a":1}'))
  run.exited()
  run.closed(0)
  expect(ends).toEqual([{ ok: true, stdout: '{"a":1}' }])
})

test('exit only marks the process gone and the close ends the run', () => {
  const { run, ends } = rig()
  expect(run.hasExited()).toBe(false)
  run.spawned()
  run.exited()
  expect(run.hasExited()).toBe(true)
  expect(ends.length).toBe(0)
  run.closed(0)
  expect(ends.length).toBe(1)
})

test('an undefined exit code reads as -1, a failing exit, so the stderr wording still selects offline-unavailable', () => {
  // Only a non-zero exit reaches the stderr classification, so this fails if undefined read as 0.
  const offline = rig()
  offline.run.err(ascii('error: No interpreter found'))
  offline.run.closed(undefined)
  expect(offline.ends).toEqual([{ ok: false, code: 'offline-unavailable' }])
  const failed = rig()
  failed.run.closed(undefined)
  expect(failed.ends).toEqual([{ ok: false, code: 'reader-failed' }])
  // A -1 exit with output still answers when the output opens with a brace.
  const answered = rig()
  answered.run.out(ascii('{"a":1}'))
  answered.run.closed(undefined)
  expect(answered.ends).toEqual([{ ok: true, stdout: '{"a":1}' }])
})

test('the core classifies the finished process', () => {
  const cases: [number, string, string, Ended][] = [
    [0, OK_STDOUT, '', { ok: true, stdout: OK_STDOUT }],
    [0, '', '', { ok: false, code: 'reader-failed' }],
    [0, 'not json', '', { ok: false, code: 'reader-failed' }],
    [152, '', '', { ok: false, code: 'reader-cpu-limit' }],
    [2, '', 'usage: x\nunrecognized arguments', { ok: false, code: 'reader-no-json-mode' }],
    [1, '', 'offline mode', { ok: false, code: 'offline-unavailable' }],
    [1, '', 'something else', { ok: false, code: 'reader-failed' }],
    [1, jsonText(readerErrorDoc('time-limit')), '', { ok: true, stdout: jsonText(readerErrorDoc('time-limit')) }],
  ]
  for (const [exit, stdout, stderr, want] of cases) {
    const { run, ends } = rig()
    run.out(ascii(stdout))
    run.err(ascii(stderr))
    run.closed(exit)
    expect(ends).toEqual([want])
  }
})

test('a recorded status wins over the output', () => {
  const { run, ends } = rig()
  run.out(ascii(OK_STDOUT))
  run.record('reader-timeout')
  run.closed(0)
  expect(ends).toEqual([{ ok: false, code: 'reader-timeout' }])
  const cannot = rig()
  cannot.run.record('reader-cannot-start')
  cannot.run.closed(0)
  expect(cannot.ends).toEqual([{ ok: false, code: 'reader-cannot-start' }])
})

// --- exceptions ----------------------------------------------------------------

test('a sink method whose body throws records reader-output-invalid and kills', () => {
  const calls: ((run: RunSink) => void)[] = [run => run.out(nothing), run => run.err(nothing)]
  for (const call of calls) {
    const { run, ends, state } = rig()
    call(run)
    expect(state.kills).toBe(1)
    expect(run.status()).toBe('reader-output-invalid')
    run.closed(0)
    expect(ends).toEqual([{ ok: false, code: 'reader-output-invalid' }])
  }
})

test('the sink catches a throwing kill hook', () => {
  const ends: Ended[] = []
  const run = openSink({
    kill: () => {
      throw new Error('kill')
    },
    end: e => {
      ends.push(e)
    },
  })
  run.out([0x80])
  run.out(nothing)
  run.closed(0)
  expect(ends).toEqual([{ ok: false, code: 'reader-output-invalid' }])
})

test('the sink catches a throwing end hook and still ignores later events', () => {
  const calls = { ends: 0, kills: 0 }
  const run = openSink({
    kill: () => {
      calls.kills += 1
    },
    end: () => {
      calls.ends += 1
      throw new Error('end')
    },
  })
  run.closed(0)
  run.closed(0)
  run.out([0x80])
  expect(calls.ends).toBe(1)
  expect(calls.kills).toBe(0)
})

test('a failed error path also ends once when the end hook throws', () => {
  const calls = { ends: 0 }
  const run = openSink({
    kill: () => {},
    end: () => {
      calls.ends += 1
      throw new Error('end')
    },
  })
  run.failed()
  run.closed(-2)
  expect(calls.ends).toBe(1)
})

// --- startReader ---------------------------------------------------------------

const EXPECTED_ARGV = [
  '-i',
  `HOME=${HOME}`, 'PATH=/usr/bin:/bin', 'UV_OFFLINE=1', 'UV_NO_CONFIG=1', 'UV_PYTHON_DOWNLOADS=never',
  'PYTHONDONTWRITEBYTECODE=1', 'CRUX_NO_UV_REEXEC=1', 'NO_COLOR=1',
  UV, 'run', '--offline', '--no-project', '--no-config', '--quiet',
  SCRIPT, '--json', '--project-root', PROJECT,
]

function planned(fake: ReturnType<typeof makeFake>) {
  const p = planLaunch(fake.host)
  if (!p.ok) throw new Error('plan refused: ' + p.code)
  return p
}

test('startReader passes the builder list without its first element', () => {
  const fake = makeFake()
  const { run } = rig()
  const handle = startReader(fake.host, planned(fake), run)
  expect(handle === undefined || handle === 'untracked').toBe(false)
  expect(fake.procs.length).toBe(1)
  expect(fake.procs[0]!.argv).toEqual(EXPECTED_ARGV)
  expect(fake.procs[0]!.argv[0]).toBe('-i')
  expect(fake.procs[0]!.cwd).toBe(`${CLONE}/crux`)
  expect(fake.procs[0]!.sink).toBe(run)
})

test('the environment of the host does not reach the started list', () => {
  const hostile = {
    HOME, PYTHONPATH: '/evil/py', VIRTUAL_ENV: '/evil/venv', UV_PYTHON: '/evil/python', UV_INDEX_URL: 'http://evil.example',
    UV_CACHE_DIR: '/evil/cache', PATH: '/evil/bin', PYTHONHOME: '/evil/home',
  }
  const fake = makeFake({ ...okWorld(), env: hostile })
  const askedHome = fake.host.env('PYTHONPATH')
  startReader(fake.host, planned(fake), rig().run)
  expect(fake.procs[0]!.argv).toEqual(EXPECTED_ARGV)
  const text = fake.procs[0]!.argv.join('\n')
  // Positive control: the fake environment does hold the hostile values.
  expect(askedHome).toBe('/evil/py')
  expect(text.includes('/evil')).toBe(false)
  expect(text.includes('PYTHONPATH')).toBe(false)
})

test('a loader variable in the host environment reaches no launch argument', () => {
  const fake = makeFake({ ...okWorld(), env: { HOME, LD_PRELOAD: '/evil/lib.so', DYLD_LIBRARY_PATH: '/evil/dyld' } })
  // Positive control: the fake environment does hold the loader values.
  expect(fake.host.env('LD_PRELOAD')).toBe('/evil/lib.so')
  expect(fake.host.env('DYLD_LIBRARY_PATH')).toBe('/evil/dyld')
  const plan = planLaunch(fake.host)
  expect(plan.ok).toBe(true)
  if (!plan.ok) return
  startReader(fake.host, plan, rig().run)
  expect(fake.procs.length).toBe(1)
  expect(fake.procs[0]!.argv[0]).toBe('-i')
  expect(fake.procs[0]!.argv).toEqual(EXPECTED_ARGV)
  expect(fake.procs[0]!.argv.filter(a => a.includes('LD_') || a.includes('DYLD_')).length).toBe(0)
})

test('the reader receives the directory the host named, not its real path', () => {
  const fake = makeFake({ ...okWorld(), directory: '/link', reals: { '/link': PROJECT } })
  startReader(fake.host, planned(fake), rig().run)
  const argv = fake.procs[0]!.argv
  expect(argv[argv.length - 1]).toBe('/link')
  expect(argv.includes(PROJECT)).toBe(false)
})

test('the started list is the launch block in the builder order, around the four plan fields', () => {
  const fake = makeFake()
  const plan = planned(fake)
  startReader(fake.host, plan, rig().run)
  const argv = fake.procs[0]!.argv
  // The launcher itself is never in the list: the host adds it.
  expect(argv.includes('/usr/bin/env')).toBe(false)
  expect(argv.indexOf(plan.uv)).toBe(9)
  expect(argv.indexOf(plan.crux + '/scripts/visualize-run-progress.py')).toBe(15)
  expect(argv[argv.length - 1]).toBe(plan.root)
  expect(argv.length).toBe(19)
})

test('startReader returns what the host returns', () => {
  const none = makeFake()
  none.startMode.value = 'undefined'
  expect(startReader(none.host, planned(none), rig().run)).toBe(undefined)
  expect(none.started()).toBe(1)
  const lost = makeFake()
  lost.startMode.value = 'untracked'
  expect(startReader(lost.host, planned(lost), rig().run)).toBe('untracked')
})

test('startReader returns undefined when the builder throws, and starts nothing', () => {
  const fake = makeFake()
  const plan = planned(fake)
  const broken: Planned = { ok: true, uv: plan.uv, crux: plan.crux, home: nothing, root: plan.root }
  expect(startReader(fake.host, broken, rig().run)).toBe(undefined)
  expect(fake.started()).toBe(0)
})
