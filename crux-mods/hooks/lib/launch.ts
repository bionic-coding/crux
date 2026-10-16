// Pure helpers for locating the installed crux and building its reader launch.
// This file takes values and returns values: the importing package passes in the
// launch values it holds, and reads no harness state here. Every launch value comes
// from a fixed source the importer names: a constant in its capability manifest, the
// installed crux's location, or the one environment value the manifest names (HOME).
// Nothing the project holds, and nothing else in the session's environment, reaches
// the argument list.

// The reader's document for 20 runs is well under 1 MiB; anything larger is not
// a document this view can check, so it is refused before it is parsed.
const MAX_STDOUT = 1024 * 1024

// Closed status codes of a finished reader process, the ones classifyFinished returns.
// The importing package adds the codes of the steps it takes itself.
export const RUN_CODES = ['reader-no-json-mode', 'offline-unavailable', 'reader-cpu-limit', 'reader-failed', 'reader-output-invalid'] as const
export type RunCode = (typeof RUN_CODES)[number]

// Results that mean the reader ran out of time: its own time limit, its CPU limit, or
// the launch timeout. The importer stops its refresh after one of these. Each member
// is a status code or reader-failed:<a reader error code>; a test holds that.
export const SLOW_CODES: readonly string[] = ['reader-failed:time-limit', 'reader-cpu-limit', 'reader-timeout']
export const isSlow = (code: string): boolean => SLOW_CODES.includes(code)

// The launch block of a capability manifest: the launcher and its arguments, the places
// to look for uv, uv's arguments, the allow-listed environment names and the constants
// among them, the reader script and its arguments, and the timeout.
export type LaunchValues = {
  readonly launcher: string
  readonly launcher_args: readonly string[]
  readonly uv_locations: readonly string[]
  readonly uv_args: readonly string[]
  readonly env_allow: readonly string[]
  readonly env_constants: Readonly<Record<string, string>>
  readonly scripts: { readonly 'visualize-run-progress': { readonly path: string; readonly args: readonly string[] } }
  readonly timeout_ms: number
}

export const trimSlash = (p: string) => (p.length > 1 ? p.replace(/\/+$/, '') : p)

export function isInside(real: string, root: string): boolean {
  const r = trimSlash(root)
  return real === r || real.startsWith(r === '/' ? '/' : r + '/')
}

// Directories above the plugin root, nearest first. Forty levels is deeper than
// any real install path; the cap only bounds the loop.
export function ancestorsOf(root: string): string[] {
  const out: string[] = []
  let dir = trimSlash(root)
  for (let i = 0; i < 40; i++) {
    const cut = dir.lastIndexOf('/')
    if (cut <= 0) break
    dir = dir.slice(0, cut)
    out.push(dir)
  }
  return out
}

export function uvCandidates(launch: LaunchValues, home: string): string[] {
  return launch.uv_locations.map(spec => spec.replace('{HOME}', trimSlash(home)))
}

export function parseOwnVersion(text: string): string | undefined {
  try {
    const v = (JSON.parse(text) as { version?: unknown } | null)?.version
    return typeof v === 'string' ? v : undefined
  } catch {
    return undefined
  }
}

export type Launch = { argv: string[]; cwd: string; timeoutMs: number }

// The one argument list the dashboard ever starts: the fixed launcher with a
// cleared environment, the allow-listed variables, uv, and the installed
// crux's reader script. HOME is the only value that does not come from a constant.
// The environment is cleared through the launcher's `-i` because a host can set a
// started process's variables over its own environment and cannot remove one:
// without -i a project's PYTHONPATH or UV_* value would reach uv and the interpreter.
export function buildLaunch(launch: LaunchValues, uv: string, cruxDir: string, home: string, projectRoot: string): Launch {
  const script = launch.scripts['visualize-run-progress']
  const values: Record<string, string> = { ...launch.env_constants, HOME: trimSlash(home) }
  const pairs = launch.env_allow.map(name => `${name}=${values[name] ?? ''}`)
  const args = script.args.map(a => (a === '{project_root}' ? projectRoot : a))
  return {
    argv: [launch.launcher, ...launch.launcher_args, ...pairs, uv, ...launch.uv_args, cruxDir + '/' + script.path, ...args],
    cwd: cruxDir,
    timeoutMs: launch.timeout_ms,
  }
}

// uv's stderr wording when it cannot resolve offline (observed with uv 0.12.24),
// and argparse's wording for an unknown flag (a crux whose reader has no --json).
// Re-check both when either tool changes its messages.
const OFFLINE = /No interpreter found|Network connectivity is disabled|offline|downloads? (are|is) set to|No solution found|Failed to (download|fetch|resolve)/i
const USAGE_ERROR = /unrecognized arguments|the following arguments are required/
// uv exits 128 plus the signal number when its child dies by a signal. SIGXCPU is 24 on
// Darwin and Linux, so 152 with no JSON answer is a reader the kernel stopped at its
// CPU limit (observed with uv 0.12.24).
const CPU_LIMIT_EXIT = 128 + 24

// A finished reader process: its exit code, its two streams, and whether the host cut
// standard output short. The importer converts its host's result into this shape.
export type Finished = { exit: number; stdout: string; stderr: string; truncated: boolean }
export type Outcome = { ok: true; stdout: string } | { ok: false; code: RunCode }

// Standard output when it is a JSON object, else the closed status code that
// names why the reader did not answer. Neither stream's text is passed on.
export function classifyFinished(res: Finished): Outcome {
  if (res.truncated || res.stdout.length > MAX_STDOUT) return { ok: false, code: 'reader-output-invalid' }
  if (res.stdout.trimStart().startsWith('{')) return { ok: true, stdout: res.stdout }
  if (res.exit === CPU_LIMIT_EXIT) return { ok: false, code: 'reader-cpu-limit' }
  if (res.exit !== 0) {
    if (USAGE_ERROR.test(res.stderr) && res.stderr.includes('usage:')) return { ok: false, code: 'reader-no-json-mode' }
    if (OFFLINE.test(res.stderr)) return { ok: false, code: 'offline-unavailable' }
  }
  return { ok: false, code: 'reader-failed' }
}
