// Planning the one launch crux-opencode ever makes. planLaunch reads only through Host,
// runs the refusals in a fixed order, and returns either a refusal code or the four
// values the launch is built from. It starts nothing.
import { capabilities } from '../capabilities.ts'
import { ancestorsOf, isInside, parseOwnVersion, trimSlash, uvCandidates } from '../../crux-mods/hooks/lib/launch.ts'
import type { Host, Planned } from './host.ts'
import { CRUX_NOT_FOUND, HOME_INVALID, INSIDE_PROJECT, PROJECT_ROOT_UNRESOLVED, UV_NOT_FOUND, VERSION_MISMATCH } from './status.ts'

// The launch values the reader is started from. lib/reader.ts imports this name; nothing
// else does.
export const LAUNCH_VALUES = capabilities.launch

export type Plan = Planned | { ok: false; code: string }

// OpenCode 2: the first dot-separated field is exactly 2, the second a non-negative integer.
export function isSupported(version: string | undefined): boolean {
  if (typeof version !== 'string') return false
  const fields = version.split('.')
  const minor = fields[1]
  return fields[0] === '2' && minor !== undefined && /^[0-9]+$/.test(minor)
}

// A path as the filesystem resolves it. A path that does not exist resolves through its
// nearest existing ancestor, with the rest appended.
function resolved(host: Host, path: string): string {
  const own = host.real(path)
  if (own !== undefined) return own
  for (const above of ancestorsOf(path)) {
    const real = host.real(above)
    if (real !== undefined) return trimSlash(real) + path.slice(above.length)
  }
  return path
}

// The real path of the first uv candidate that is a file (the candidate itself when its real path cannot be read), or undefined when none is.
function locateUv(host: Host, candidates: string[]): string | undefined {
  for (const candidate of candidates) {
    if (host.isFile(candidate)) return host.real(candidate) ?? candidate
  }
  return undefined
}

export function planLaunch(host: Host): Plan {
  const no = (code: string): Plan => ({ ok: false, code })

  // 1. The project root: the directory the host names, which must resolve to a directory.
  // Every comparison below uses its real path. The reader receives the name itself.
  const root = host.directory()
  if (root === undefined || !root.startsWith('/')) return no(PROJECT_ROOT_UNRESOLVED)
  const rootReal = host.real(root)
  if (rootReal === undefined || !host.isDir(rootReal)) return no(PROJECT_ROOT_UNRESOLVED)

  // 2. HOME.
  const home = host.env('HOME')
  if (home === undefined || !home.startsWith('/')) return no(HOME_INVALID)

  // 3. The clone's crux directory holds the reader script.
  const cloneDir = host.cloneDir
  if (cloneDir === undefined) return no(CRUX_NOT_FOUND)
  const crux = cloneDir + '/crux'
  if (!host.isFile(crux + '/' + LAUNCH_VALUES.scripts['visualize-run-progress'].path)) return no(CRUX_NOT_FOUND)

  // 4. uv: the first candidate that is a file. Its real path is the uv that runs.
  const candidates = uvCandidates(LAUNCH_VALUES, home)
  const uv = locateUv(host, candidates)

  // 5. Everything the launch reads or runs lies outside the project, links resolved.
  // The script path is listed beside its directory because the file can be a link that leaves it.
  const reach = [crux, crux + '/' + LAUNCH_VALUES.scripts['visualize-run-progress'].path, trimSlash(home), trimSlash(home) + '/.cache/uv', trimSlash(home) + '/.local/share/uv']
  if (uv !== undefined) reach.push(uv)
  for (const entry of LAUNCH_VALUES.env_constants.PATH.split(':')) reach.push(entry)
  const projectReal = trimSlash(rootReal)
  for (const path of reach) {
    if (isInside(resolved(host, path), projectReal)) return no(INSIDE_PROJECT)
  }

  // 6. A uv was located. This follows step 5, so a uv inside the project reads inside-project.
  if (uv === undefined) return no(UV_NOT_FOUND)

  // 7. The clone's two plugin manifests name one version.
  const own = parseOwnVersion(host.read(cloneDir + '/crux/plugin.json') ?? '')
  const mods = parseOwnVersion(host.read(cloneDir + '/crux-mods/.claude-plugin/plugin.json') ?? '')
  if (own === undefined || own !== mods) return no(VERSION_MISMATCH)

  return { ok: true, uv, crux, home, root }
}
