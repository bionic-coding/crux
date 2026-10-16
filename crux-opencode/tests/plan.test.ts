import { test, expect } from 'claude-code/testing'
import { capabilities } from '../capabilities.ts'
import { isSupported, planLaunch } from '../lib/plan.ts'
import { CLONE, HOME, MODS_JSON, PLUGIN_JSON, PROJECT, SCRIPT, UV, makeFake, okWorld } from './fixtures/fake.ts'
import type { World } from './fixtures/fake.ts'

const LAUNCH = capabilities.launch
const world = (change: World = {}): World => ({ ...okWorld(), ...change })
const planOf = (change: World = {}) => planLaunch(makeFake(world(change)).host)
const codeOf = (change: World = {}) => {
  const p = planOf(change)
  return p.ok ? 'ok' : p.code
}
const without = (list: string[] | undefined, ...drop: string[]) => (list ?? []).filter(p => !drop.includes(p))

// --- the version range ---------------------------------------------------------

for (const v of ['2.0.26', '2.0', '2.1.0', '2.12', '2.0.0-beta.1', '2.007.1']) {
  test(`version ${v} is supported`, () => {
    expect(isSupported(v)).toBe(true)
  })
}

for (const v of ['1.9.9', '3.0.0', '20.0.0', '02.0.1', '2', '2.', '2.x.1', '2.-1', '2.1e3', '', ' 2.0', '2 .0', 'v2.0.1', '.2.0']) {
  test(`version "${v}" is unsupported`, () => {
    expect(isSupported(v)).toBe(false)
  })
}

test('an absent version is unsupported', () => {
  expect(isSupported(undefined)).toBe(false)
})

// --- the success value ---------------------------------------------------------

test('a plan on a clean machine carries its four fields', () => {
  expect(planOf()).toEqual({ ok: true, uv: UV, crux: `${CLONE}/crux`, home: HOME, root: PROJECT })
})

test('the uv is the located candidate real path', () => {
  const real = '/opt/homebrew/Cellar/uv/0.9/bin/uv'
  const p = planOf({ reals: { [UV]: real } })
  expect(p.ok ? p.uv : p.code).toBe(real)
})

test('the first candidate that is a file is the uv that runs', () => {
  const second = '/usr/local/bin/uv'
  const third = `${HOME}/.local/bin/uv`
  const files = (list: string[]) => without(okWorld().files, UV).concat(list)
  expect(planOf({ files: files([second, third]) })).toEqual({ ok: true, uv: second, crux: `${CLONE}/crux`, home: HOME, root: PROJECT })
  expect(planOf({ files: files([third]) })).toEqual({ ok: true, uv: third, crux: `${CLONE}/crux`, home: HOME, root: PROJECT })
  expect(planOf({ files: files([`${HOME}/.cargo/bin/uv`]) })).toEqual({
    ok: true, uv: `${HOME}/.cargo/bin/uv`, crux: `${CLONE}/crux`, home: HOME, root: PROJECT,
  })
})

test('home is HOME as the host reports it', () => {
  const p = planOf({ env: { HOME: '/home/other' }, files: [SCRIPT, UV, PLUGIN_JSON, MODS_JSON], dirs: [...(okWorld().dirs ?? []), '/home/other'] })
  expect(p.ok ? p.home : p.code).toBe('/home/other')
})

test('the project root is the directory the host names, not its real path', () => {
  const p = planOf({ directory: '/link', reals: { '/link': '/proj' } })
  expect(p).toEqual({ ok: true, uv: UV, crux: `${CLONE}/crux`, home: HOME, root: '/link' })
})

test('the clone directory gives the crux directory', () => {
  const p = planOf({
    cloneDir: '/opt/c',
    files: ['/opt/c/crux/scripts/visualize-run-progress.py', UV, '/opt/c/crux/plugin.json', '/opt/c/crux-mods/.claude-plugin/plugin.json'],
    dirs: [PROJECT, HOME, '/usr/bin', '/bin'],
    texts: { '/opt/c/crux/plugin.json': '{"version":"1.2.3"}', '/opt/c/crux-mods/.claude-plugin/plugin.json': '{"version":"1.2.3"}' },
  })
  expect(p).toEqual({ ok: true, uv: UV, crux: '/opt/c/crux', home: HOME, root: PROJECT })
})

// --- the refusals, one by one ---------------------------------------------------

test('a loader variable set does not stop the plan', () => {
  const clean = planOf()
  expect(clean.ok).toBe(true)
  expect(planOf({ env: { HOME, LD_LIBRARY_PATH: '/opt/conda/lib' } })).toEqual(clean)
  expect(planOf({ env: { HOME, LD_LIBRARY_PATH: '/opt/conda/lib', DYLD_LIBRARY_PATH: '/opt/homebrew/lib' } })).toEqual(clean)
  expect(planOf({ env: { HOME, LD_PRELOAD: '' } })).toEqual(clean)
})

test('a directory that is not absolute is project-root-unresolved', () => {
  expect(codeOf({ directory: 'proj' })).toBe('project-root-unresolved')
  expect(codeOf({ directory: '' })).toBe('project-root-unresolved')
})

test('a missing directory is project-root-unresolved', () => {
  expect(codeOf({ directory: undefined })).toBe('project-root-unresolved')
})

test('a directory with no real path is project-root-unresolved', () => {
  expect(codeOf({ directory: '/gone' })).toBe('project-root-unresolved')
})

test('a directory that resolves to a file is project-root-unresolved', () => {
  expect(codeOf({ directory: '/afile', files: [...(okWorld().files ?? []), '/afile'] })).toBe('project-root-unresolved')
})

test('a link to a missing target is project-root-unresolved', () => {
  expect(codeOf({ directory: '/link', dirs: [...(okWorld().dirs ?? []), '/link'], reals: { '/link': '/gone' } })).toBe('project-root-unresolved')
})

test('a directory that resolves through a link to a directory passes', () => {
  expect(codeOf({ directory: '/link', reals: { '/link': PROJECT } })).toBe('ok')
})

test('a missing HOME is home-invalid', () => {
  expect(codeOf({ env: {} })).toBe('home-invalid')
})

test('a HOME that is not absolute is home-invalid', () => {
  expect(codeOf({ env: { HOME: 'home/u' } })).toBe('home-invalid')
  expect(codeOf({ env: { HOME: '' } })).toBe('home-invalid')
})

test('a missing clone directory is crux-not-found', () => {
  expect(codeOf({ cloneDir: undefined })).toBe('crux-not-found')
})

test('a clone without the reader script is crux-not-found', () => {
  expect(codeOf({ files: without(okWorld().files, SCRIPT) })).toBe('crux-not-found')
})

test('a reader script that is a directory is crux-not-found', () => {
  expect(codeOf({ files: without(okWorld().files, SCRIPT), dirs: [...(okWorld().dirs ?? []), SCRIPT] })).toBe('crux-not-found')
})

test('no uv anywhere is uv-not-found', () => {
  expect(codeOf({ files: without(okWorld().files, UV) })).toBe('uv-not-found')
})

test('a uv candidate that is not a file is not located', () => {
  expect(codeOf({ files: without(okWorld().files, UV), dirs: [...(okWorld().dirs ?? []), UV] })).toBe('uv-not-found')
})

test('two plugin versions that differ are version-mismatch', () => {
  expect(codeOf({ texts: { [PLUGIN_JSON]: '{"version":"3.31.1"}', [MODS_JSON]: '{"version":"3.31.2"}' } })).toBe('version-mismatch')
})

test('a missing, unparsable or versionless plugin file is version-mismatch', () => {
  expect(codeOf({ texts: { [PLUGIN_JSON]: '{"version":"3.31.1"}' } })).toBe('version-mismatch')
  expect(codeOf({ texts: { [MODS_JSON]: '{"version":"3.31.1"}' } })).toBe('version-mismatch')
  expect(codeOf({ texts: { [PLUGIN_JSON]: 'nope', [MODS_JSON]: 'nope' } })).toBe('version-mismatch')
  expect(codeOf({ texts: { [PLUGIN_JSON]: '{}', [MODS_JSON]: '{}' } })).toBe('version-mismatch')
  expect(codeOf({ texts: { [PLUGIN_JSON]: '{"version":3}', [MODS_JSON]: '{"version":3}' } })).toBe('version-mismatch')
})

// --- the order of the refusals --------------------------------------------------

test('every earlier refusal wins over every later one', () => {
  // A machine that breaks every step: each row removes the breakage of one step.
  const broken: World = {
    version: '2.0.26',
    directory: 'rel',
    cloneDir: undefined,
    env: {},
    files: [],
    dirs: [],
    texts: {},
  }
  expect(codeOf(broken)).toBe('project-root-unresolved')
  expect(codeOf({ ...broken, env: {}, directory: PROJECT, dirs: [PROJECT] })).toBe('home-invalid')
  expect(codeOf({ ...broken, env: { HOME }, directory: PROJECT, dirs: [PROJECT] })).toBe('crux-not-found')
  expect(codeOf({ ...broken, env: { HOME }, directory: PROJECT, dirs: [PROJECT], cloneDir: CLONE, files: [SCRIPT] })).toBe('uv-not-found')
  expect(codeOf({ ...broken, env: { HOME }, directory: PROJECT, dirs: [PROJECT], cloneDir: CLONE, files: [SCRIPT, UV] })).toBe('version-mismatch')
})

test('a reach member inside the project wins over a missing uv', () => {
  // Control: the same machine with HOME outside the project reads uv-not-found.
  const noUv: World = { files: without(okWorld().files, UV) }
  expect(codeOf(noUv)).toBe('uv-not-found')
  expect(codeOf({ ...noUv, directory: '/home', dirs: [...(okWorld().dirs ?? []), '/home'] })).toBe('inside-project')
})

test('the uv is located before the inside check, so its real path is checked', () => {
  expect(codeOf()).toBe('ok')
  expect(codeOf({ reals: { [UV]: `${PROJECT}/tools/uv` } })).toBe('inside-project')
})

test('a crux directory inside the project refuses before the missing uv', () => {
  expect(codeOf({ files: without(okWorld().files, UV), reals: { [`${CLONE}/crux`]: `${PROJECT}/crux` } })).toBe('inside-project')
})

test('inside-project wins over a version mismatch', () => {
  const mismatch = { texts: { [PLUGIN_JSON]: '{"version":"1"}', [MODS_JSON]: '{"version":"2"}' } }
  expect(codeOf(mismatch)).toBe('version-mismatch')
  expect(codeOf({ ...mismatch, reals: { [UV]: `${PROJECT}/uv` } })).toBe('inside-project')
})

// --- the reach list ------------------------------------------------------------

const extra = (...dirs: string[]) => [...(okWorld().dirs ?? []), ...dirs]

test('the reach list passes when every member is outside the project', () => {
  expect(codeOf()).toBe('ok')
})

test('the clone crux directory is on the reach list', () => {
  expect(codeOf({ reals: { [`${CLONE}/crux`]: `${PROJECT}/crux` } })).toBe('inside-project')
})

test('the located uv is on the reach list', () => {
  expect(codeOf({ reals: { [UV]: `${PROJECT}/uv` } })).toBe('inside-project')
})

test('HOME is on the reach list', () => {
  expect(codeOf({ directory: '/home', dirs: extra('/home') })).toBe('inside-project')
  expect(codeOf({ reals: { [HOME]: `${PROJECT}/h` } })).toBe('inside-project')
})

test('the uv cache is on the reach list', () => {
  expect(codeOf({ dirs: extra(`${HOME}/.cache/uv`), reals: { [`${HOME}/.cache/uv`]: `${PROJECT}/cache` } })).toBe('inside-project')
})

test('the uv interpreter directory is on the reach list', () => {
  expect(codeOf({ dirs: extra(`${HOME}/.local/share/uv`), reals: { [`${HOME}/.local/share/uv`]: `${PROJECT}/share` } })).toBe('inside-project')
})

test('each PATH entry is on the reach list', () => {
  expect(codeOf({ reals: { '/usr/bin': `${PROJECT}/usr-bin` } })).toBe('inside-project')
  expect(codeOf({ reals: { '/bin': `${PROJECT}/bin` } })).toBe('inside-project')
  expect(LAUNCH.env_constants.PATH).toBe('/usr/bin:/bin')
})

test('a missing member resolves through its nearest existing ancestor', () => {
  // ~/.cache/uv does not exist; ~/.cache does, and it is a link into the project.
  const cache = { dirs: extra(`${HOME}/.cache`), reals: { [`${HOME}/.cache`]: `${PROJECT}/c` } }
  expect(codeOf(cache)).toBe('inside-project')
  // The same ancestor outside the project reads ok.
  expect(codeOf({ dirs: extra(`${HOME}/.cache`), reals: { [`${HOME}/.cache`]: '/elsewhere/c' } })).toBe('ok')
  // Two levels missing: ~/.local/share/uv with only ~/.local present.
  expect(codeOf({ dirs: extra(`${HOME}/.local`), reals: { [`${HOME}/.local`]: `${PROJECT}/l` } })).toBe('inside-project')
})

test('the nearest ancestor is used, not a farther one', () => {
  const share = `${HOME}/.local/share`
  const local = `${HOME}/.local`
  // The nearest ancestor of ~/.local/share/uv is ~/.local/share, and it is inside.
  expect(codeOf({ dirs: extra(local, share), reals: { [local]: '/ok/l', [share]: `${PROJECT}/s` } })).toBe('inside-project')
  // The nearest ancestor is outside while a farther one is inside: the farther one is not used.
  expect(codeOf({ dirs: extra(local, share), reals: { [local]: `${PROJECT}/l`, [share]: '/ok/s' } })).toBe('ok')
})

test('a reader script that links into the project refuses inside-project', () => {
  // The crux directory itself resolves outside; only the script file is a link into the project.
  expect(codeOf({ reals: { [SCRIPT]: `${PROJECT}/visualize-run-progress.py` } })).toBe('inside-project')
})

test('the project root itself counts as inside', () => {
  expect(codeOf({ reals: { [`${CLONE}/crux`]: PROJECT } })).toBe('inside-project')
})

test('a sibling directory with the project name as a prefix is not inside', () => {
  expect(codeOf({ reals: { [`${CLONE}/crux`]: `${PROJECT}-other/crux` } })).toBe('ok')
})

// --- comparisons against the real path ------------------------------------------

test('members are compared with the real path of the project, not the path the host names', () => {
  const link = { directory: '/link', reals: { '/link': PROJECT } }
  // Control: the project is named through a link, and nothing is inside it.
  expect(codeOf(link)).toBe('ok')
  // A member under the real path is inside, though it is not under the name the host gave.
  expect(codeOf({ ...link, reals: { ...link.reals, [`${CLONE}/crux`]: `${PROJECT}/crux` } })).toBe('inside-project')
  // A member under the name the host gave is not inside the real project.
  expect(codeOf({ ...link, reals: { ...link.reals, [`${CLONE}/crux`]: '/link/crux' } })).toBe('ok')
})

// --- the reads ----------------------------------------------------------------

test('the plan never reads the launcher', () => {
  const fake = makeFake(world())
  expect(planLaunch(fake.host).ok).toBe(true)
  // Positive control: the log records the paths the plan does read.
  expect(fake.log.includes(`isFile:${SCRIPT}`)).toBe(true)
  expect(fake.log.includes(`read:${PLUGIN_JSON}`)).toBe(true)
  expect(fake.log.filter(e => e.includes('/usr/bin/env')).length).toBe(0)
})

test('the plan reads no value while the host reports no project root', () => {
  const fake = makeFake(world({ directory: undefined }))
  expect(planLaunch(fake.host)).toEqual({ ok: false, code: 'project-root-unresolved' })
  expect(fake.asked('isFile:')).toEqual([])
  expect(fake.asked('real:')).toEqual([])
  expect(fake.asked('read:')).toEqual([])
  // Positive control: the same machine with a project root reads files.
  const clean = makeFake(world())
  planLaunch(clean.host)
  expect(clean.asked('isFile:').length).toBeGreaterThan(0)
})

test('a refusal ends the plan before the later reads', () => {
  const fake = makeFake(world({ env: {} }))
  expect(planLaunch(fake.host)).toEqual({ ok: false, code: 'home-invalid' })
  expect(fake.asked('isFile:')).toEqual([])
  expect(fake.asked('read:')).toEqual([])
})

test('the launch block holds the fixed launcher and its constants', () => {
  expect(LAUNCH.launcher).toBe('/usr/bin/env')
  expect(LAUNCH.launcher_args.join(',')).toBe('-i')
  expect(LAUNCH.timeout_ms).toBe(10000)
})
