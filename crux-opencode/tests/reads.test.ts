import { test, expect } from 'claude-code/testing'
import { capabilities } from '../capabilities.ts'
import { createScheduler } from '../lib/refresh.ts'
import { CLONE, HOME, MODS_JSON, PLUGIN_JSON, PROJECT, SCRIPT, UV, makeFake, okWorld } from './fixtures/fake.ts'
import type { Fake } from './fixtures/fake.ts'
import { containsText, jsonText } from './fixtures/plain.ts'
import { VIEW_STDOUT } from './fixtures/sched-docs.ts'

const LAUNCH = capabilities.launch

// A full run on a clean machine: the plan reads, the process runs, the value is kept.
function fullRun(stdout = VIEW_STDOUT, stderr = '', exit = 0) {
  const world = { ...okWorld(), env: { HOME, PYTHONPATH: '/evil/py', UV_CACHE_DIR: '/evil/cache', PATH: '/evil/bin', TOKEN: 'secret' } }
  const fake = makeFake(world)
  const sched = createScheduler(fake.host)
  sched.start()
  fake.clock.advance(4100)
  const p = fake.procs[0]
  if (p === undefined) throw new Error('no reader started')
  p.spawn()
  p.err(stderr)
  p.out(stdout)
  p.exit()
  p.close(exit)
  fake.clock.advance(60000)
  return { fake, sched }
}

const names = (fake: Fake, prefix: string) => fake.asked(prefix).map(e => e.slice(prefix.length))
const distinct = (list: string[]) => list.filter((e, i) => list.indexOf(e) === i)

test('the environment reads are the one declared name', () => {
  const { fake } = fullRun()
  const asked = distinct(names(fake, 'env:'))
  // Positive control: the plan did read.
  expect(asked.length).toBeGreaterThan(0)
  expect(asked.includes('HOME')).toBe(true)
  const declared = ['HOME']
  expect(declared.length).toBe(1)
  expect(asked.filter(n => !declared.includes(n))).toEqual([])
  expect(asked.slice().sort()).toEqual(declared.slice().sort())
})

test('no hostile variable of the fake environment is ever asked for', () => {
  const { fake } = fullRun()
  expect(fake.world.env).toEqual({ HOME, PYTHONPATH: '/evil/py', UV_CACHE_DIR: '/evil/cache', PATH: '/evil/bin', TOKEN: 'secret' })
  const asked = names(fake, 'env:')
  for (const hostile of ['PYTHONPATH', 'UV_CACHE_DIR', 'PATH', 'TOKEN', 'CLAUDE_CONFIG_DIR']) expect(asked.includes(hostile)).toBe(false)
})

test('the file reads are the reader script and the uv candidates', () => {
  const { fake } = fullRun()
  const asked = distinct(names(fake, 'isFile:'))
  const candidates = LAUNCH.uv_locations.map(spec => spec.replace('{HOME}', HOME))
  expect(asked.includes(SCRIPT)).toBe(true)
  expect(asked.includes(UV)).toBe(true)
  expect(asked.filter(p => p !== SCRIPT && !candidates.includes(p))).toEqual([])
  // The candidates after the located one are never asked.
  expect(asked.includes(candidates[1] ?? '')).toBe(false)
})

test('the directory check is for the project root alone', () => {
  const { fake } = fullRun()
  expect(distinct(names(fake, 'isDir:'))).toEqual([PROJECT])
})

test('the text reads are the two plugin manifests', () => {
  const { fake } = fullRun()
  expect(distinct(names(fake, 'read:')).sort()).toEqual([PLUGIN_JSON, MODS_JSON].sort())
})

test('the real-path reads are the project root, the located uv, and the reach list with its ancestors', () => {
  const { fake } = fullRun()
  const asked = distinct(names(fake, 'real:'))
  const allowed = [
    PROJECT, UV, `${CLONE}/crux`, SCRIPT, HOME, `${HOME}/.cache/uv`, `${HOME}/.cache`, `${HOME}/.local/share/uv`, `${HOME}/.local/share`, `${HOME}/.local`,
    '/usr/bin', '/bin',
  ]
  expect(asked.includes(PROJECT)).toBe(true)
  expect(asked.includes(UV)).toBe(true)
  expect(asked.filter(p => !allowed.includes(p))).toEqual([])
})

test('the launcher path is never among the reads', () => {
  const { fake } = fullRun()
  // Positive control: the log holds many entries of every read kind.
  for (const kind of ['env:', 'isFile:', 'isDir:', 'real:', 'read:']) expect(fake.asked(kind).length).toBeGreaterThan(0)
  expect(fake.log.filter(e => e.includes(LAUNCH.launcher)).length).toBe(0)
})

test('every logged call is a declared read, a lease call, a start or a kept write', () => {
  const { fake } = fullRun()
  fake.clock.advance(20000)
  const known = ['env:', 'isFile:', 'isDir:', 'real:', 'read:', 'leaseRead:', 'leaseWrite:']
  const other = fake.log.filter(e => !known.some(prefix => e.startsWith(prefix)))
  expect(distinct(other).sort()).toEqual(['start', 'writeKept'])
})

test('memory holds only the kept envelope and the lease', () => {
  const { fake } = fullRun()
  expect(fake.mem.current).toEqual({ ok: true, stdout: VIEW_STDOUT })
  for (const write of fake.mem.writes) {
    const text = jsonText(write)
    const view = /^\{"ok":true,"stdout":".*"\}$/.test(text)
    const code = /^\{"ok":false,"code":"[a-z:-]+"\}$/.test(text)
    expect(text === 'null' || view || code).toBe(true)
  }
  // Lease writes are booleans and nothing else.
  for (const e of fake.asked('leaseWrite:')) expect(e.startsWith('leaseWrite:true:') || e.startsWith('leaseWrite:false:')).toBe(true)
})

test('the reader error text is neither kept nor drawn: standard error selects a code and is dropped', () => {
  const secret = 'SECRET-STDERR-TEXT'
  const { fake } = fullRun('', 'error: ' + secret + ' offline', 1)
  // Positive control: standard error reached the decoder and chose the code.
  expect(fake.mem.current).toEqual({ ok: false, code: 'offline-unavailable' })
  expect(containsText(fake.mem.writes, secret)).toBe(false)
  expect(containsText(fake.log, secret)).toBe(false)
})

test('output that is not a document is not kept', () => {
  const text = 'PLAIN-STDOUT-TEXT'
  const { fake } = fullRun(text, '', 1)
  expect(fake.mem.current).toEqual({ ok: false, code: 'reader-failed' })
  expect(containsText(fake.mem.writes, text)).toBe(false)
})

test('a plan refusal reads nothing past its step and keeps only its code', () => {
  const world = { ...okWorld(), directory: undefined }
  const fake = makeFake(world)
  const sched = createScheduler(fake.host)
  sched.start()
  fake.clock.advance(4100)
  expect(fake.mem.current).toEqual({ ok: false, code: 'project-root-unresolved' })
  expect(fake.asked('isFile:')).toEqual([])
  expect(fake.asked('real:')).toEqual([])
  expect(fake.asked('read:')).toEqual([])
  expect(fake.asked('isDir:')).toEqual([])
})
