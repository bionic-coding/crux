import { test } from 'node:test'
import assert from 'node:assert/strict'
import { planLaunch } from '../lib/plan.ts'
import { CLONE, HOME, MODS_JSON, PLUGIN_JSON, PROJECT, SCRIPT, UV, makeFake, okWorld } from './fixtures/fake.ts'
import type { World } from './fixtures/fake.ts'

const world = (change: World = {}): World => ({ ...okWorld(), ...change })
const planOf = (change: World = {}) => planLaunch(makeFake(world(change)).host)
const codeOf = (change: World = {}) => {
  const p = planOf(change)
  return p.ok ? 'ok' : p.code
}
const without = (list: string[] | undefined, ...drop: string[]) => (list ?? []).filter(p => !drop.includes(p))

test('a plan on a clean machine carries its four fields', () => {
  assert.deepEqual(planOf(), { ok: true, uv: UV, crux: `${CLONE}/crux`, home: HOME, root: PROJECT })
})

test('the uv is the located candidate real path', () => {
  const real = '/opt/homebrew/Cellar/uv/0.9/bin/uv'
  const p = planOf({ reals: { [UV]: real } })
  assert.equal(p.ok ? p.uv : p.code, real)
})

test('the first candidate that is a file is the uv that runs', () => {
  const second = '/usr/local/bin/uv'
  const third = `${HOME}/.local/bin/uv`
  const files = (list: string[]) => without(okWorld().files, UV).concat(list)
  assert.deepEqual(planOf({ files: files([second, third]) }), { ok: true, uv: second, crux: `${CLONE}/crux`, home: HOME, root: PROJECT })
  assert.deepEqual(planOf({ files: files([third]) }), { ok: true, uv: third, crux: `${CLONE}/crux`, home: HOME, root: PROJECT })
})

test('the project root is the directory the host names, not its real path', () => {
  const p = planOf({ directory: '/link', reals: { '/link': '/proj' } })
  assert.deepEqual(p, { ok: true, uv: UV, crux: `${CLONE}/crux`, home: HOME, root: '/link' })
})

test('a directory that is not absolute is project-root-unresolved', () => {
  assert.equal(codeOf({ directory: 'proj' }), 'project-root-unresolved')
  assert.equal(codeOf({ directory: '' }), 'project-root-unresolved')
  assert.equal(codeOf({ directory: undefined }), 'project-root-unresolved')
})

test('a directory the host cannot resolve is project-root-unresolved', () => {
  assert.equal(codeOf({ dirs: without(okWorld().dirs, PROJECT) }), 'project-root-unresolved')
})

test('a missing or relative HOME is home-invalid', () => {
  assert.equal(codeOf({ env: {} }), 'home-invalid')
  assert.equal(codeOf({ env: { HOME: 'home' } }), 'home-invalid')
})

test('a clone without the reader script is crux-not-found', () => {
  assert.equal(codeOf({ files: without(okWorld().files, SCRIPT) }), 'crux-not-found')
  assert.equal(codeOf({ cloneDir: undefined }), 'crux-not-found')
})

test('a machine without uv is uv-not-found', () => {
  const files = without(okWorld().files, UV)
  assert.equal(codeOf({ files }), 'uv-not-found')
})

test('a uv, home or script inside the project is inside-project', () => {
  assert.equal(codeOf({ reals: { [UV]: `${PROJECT}/bin/uv` } }), 'inside-project')
  const homeInside = `${PROJECT}/home`
  assert.equal(codeOf({ env: { HOME: homeInside }, dirs: [...(okWorld().dirs ?? []), homeInside] }), 'inside-project')
})

test('the two plugin manifests must name one version', () => {
  const texts = { [PLUGIN_JSON]: '{"version":"3.31.1"}', [MODS_JSON]: '{"version":"3.30.0"}' }
  assert.equal(codeOf({ texts }), 'version-mismatch')
  assert.equal(codeOf({ texts: { [PLUGIN_JSON]: '{}', [MODS_JSON]: '{}' } }), 'version-mismatch')
})
