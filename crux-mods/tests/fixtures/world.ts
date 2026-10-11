// A mocked machine for the dashboard tests: the environment, the file system
// the mod may stat and read, and the one process it may start. The test kit has
// no file system, network or process of its own, so every answer comes from the
// hooks this file registers on the test's `on`.
import { mock } from 'claude-code/testing'

export type Kind = 'file' | 'dir' | 'other'

export type Reader = { exitCode: number; stdout: string; stderr?: string; truncated?: boolean; delayMs?: number }

export type Opts = {
  env?: Record<string, string>
  // The session's project root, and the directory it runs in. They differ after
  // a shell cd; the mod must read the root.
  root?: string
  cwd?: string
  // What `fs.stat` finds. A path absent here rejects, as a missing path does.
  files?: Record<string, Kind>
  // path -> where it lands, for a link.
  links?: Record<string, string>
  // The installed plugin record. `ancestor` answers the first
  // `<dir>/plugins/installed_plugins.json` the mod asks for, a path answers only that
  // config dir, and `none` answers no record.
  installedAt?: 'ancestor' | 'none' | string
  record?: unknown
  ownVersion?: string
  // `throw` for a plugin.json of this mod that cannot be read.
  ownRead?: 'throw'
  // The reader process: a result, or `throw` for a process that cannot start.
  reader?: Reader | 'throw'
  // Successive reader results, the last repeating; overrides `reader`.
  readers?: Reader[]
  // `throw` for an agent list the engine cannot answer.
  agents?: unknown[] | 'throw'
  // `throw` for a pane the engine cannot open, `unplaced` for one it does not place.
  open?: 'throw' | 'unplaced'
}

export const CRUX = '/cfg/plugins/cache/crux/crux/3.27.4'
export const UV = '/opt/homebrew/bin/uv'

export const baseEnv = { HOME: '/home/u', CLAUDE_CONFIG_DIR: '/cfg' }

export const baseRecord = (installPath = CRUX, version = '3.27.4') => ({
  version: 2,
  plugins: { 'crux@crux': [{ scope: 'user', installPath, version }] },
})

export type Run = { argv: string[]; init: Record<string, unknown> | undefined }

export type World = {
  runs: Run[]
  stats: string[]
  reads: string[]
  opened: any[]
  registered: any[]
  clock: ReturnType<typeof mock.clock>
}

export function install(on: any, o: Opts = {}): World {
  const clock = mock.clock(on, { now: 0 })
  const w: World = { runs: [], stats: [], reads: [], opened: [], registered: [], clock }
  const files: Record<string, Kind> = { '/proj': 'dir', '/usr/bin/env': 'file', [UV]: 'file', [CRUX]: 'dir', ...(o.files ?? {}) }
  const links = o.links ?? {}
  const installedAt = o.installedAt ?? '/cfg'
  let recordPath: string | undefined
  const stat = (path: string) => {
    w.stats.push(path)
    if (path.endsWith('/plugins/installed_plugins.json')) {
      const dir = path.slice(0, -'/plugins/installed_plugins.json'.length)
      if (installedAt === 'none') throw new Error('ENOENT')
      if (installedAt === 'ancestor') {
        if (recordPath === undefined) recordPath = path
        if (recordPath !== path) throw new Error('ENOENT')
      } else if (dir !== installedAt) throw new Error('ENOENT')
      return { kind: 'file', size: 1, mtimeMs: 0, isLink: false, realPath: path }
    }
    const kind = files[path]
    if (kind === undefined) throw new Error('ENOENT')
    const real = links[path]
    return { kind, size: 1, mtimeMs: 0, isLink: real !== undefined, realPath: real ?? path }
  }
  mock.env(on, o.env ?? baseEnv)
  on('session.root', () => ({ value: o.root ?? '/proj' }) as any)
  on('session.cwd', () => ({ value: o.cwd ?? '/proj/sub' }) as any)
  on('fs.stat', (_$: any, e: any) => ({ value: stat(e.path) }) as any)
  on('fs.read', (_$: any, e: any) => {
    w.reads.push(e.path)
    if (e.path.endsWith('/plugins/installed_plugins.json')) return { value: JSON.stringify(o.record ?? baseRecord()) } as any
    if (e.path.endsWith('/.claude-plugin/plugin.json')) {
      if (o.ownRead === 'throw') throw new Error('EACCES')
      return { value: JSON.stringify({ name: 'crux-mods', version: o.ownVersion ?? '3.27.4' }) } as any
    }
    throw new Error('ENOENT')
  })
  on('process.run', async (_$: any, e: any) => {
    w.runs.push({ argv: [...e.argv], init: e.init })
    const r = o.readers !== undefined ? o.readers[Math.min(w.runs.length - 1, o.readers.length - 1)]! : (o.reader ?? { exitCode: 0, stdout: '' })
    if (r === 'throw') throw new Error('cannot start')
    if (r.delayMs !== undefined) await clock.sleep(r.delayMs)
    return { value: { exitCode: r.exitCode, stdout: r.stdout, stderr: r.stderr ?? '', isStdoutTruncated: r.truncated === true, isStderrTruncated: false } } as any
  })
  on('ui.open', (_$: any, e: any) => {
    w.opened.push(e)
    if (o.open === 'throw') throw new Error('no surface')
    return { value: { isPlaced: o.open !== 'unplaced' } } as any
  })
  on('command.register', (_$: any, e: any) => { w.registered.push(e); return { value: undefined } as any })
  on('agent.list', () => {
    if (o.agents === 'throw') throw new Error('agent list unavailable')
    return { value: o.agents ?? [] } as any
  })
  // What the engine itself answers beneath the mod: its own start, and an empty
  // drawing for a component the mod passes on.
  on('session.start', (_$: any, e: any) => ({ cwd: e.cwd }) as any)
  on('ui.render', () => ({ type: 'Box', props: {}, children: [] }) as any)
  return w
}

// Every string a drawn tree holds, in order.
export function texts(tree: unknown): string[] {
  const out: string[] = []
  const walk = (n: unknown) => {
    if (typeof n === 'string') out.push(n)
    else if (Array.isArray(n)) n.forEach(walk)
    else if (n !== null && typeof n === 'object') {
      const o = n as Record<string, unknown>
      if ('children' in o) walk(o.children)
      if ('props' in o && o.props !== null && typeof o.props === 'object') {
        const p = o.props as Record<string, unknown>
        if ('children' in p) walk(p.children)
        if (typeof p.label === 'string') out.push(p.label)
      }
    }
  }
  walk(tree)
  return out
}

export const BAND = { hasSurvey: false, isWorking: false, maxRows: 6, bodyColumns: 100, scroll: { offset: 0, bodyRows: 6 }, view: {} }
export const PANE = { title: 'Dashboard', isFocused: false, bodyColumns: 100, placement: 'inline' as const, scroll: { offset: 0, bodyRows: 30 }, view: {} }
