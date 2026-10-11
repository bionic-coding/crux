// Pure helpers for locating the installed crux and building its reader launch.
// The mods loader follows `$` only into functions declared in the hooks module
// itself, so every call on `$` lives in register.tsx; this file takes values
// and returns values. Every launch value comes from a fixed source: a constant
// in the capability manifest, the installed plugin record, or the one
// environment value the manifest names (HOME). Nothing the project holds, and
// nothing else in the session's environment, reaches the argument list.
import { capabilities } from '../capabilities.ts'

export const LAUNCH = capabilities.launch
export const RECORD = '/plugins/installed_plugins.json'
// The reader's document for 20 runs is well under 1 MiB; anything larger is not
// a document this view can check, so it is refused before it is parsed.
const MAX_STDOUT = 1024 * 1024

// Closed status codes of the launch. A text answer carries only these, the
// reader's own closed error codes, and values the reader emitted.
export const LAUNCH_CODES = [
  'no-env-binary', 'loader-var-set', 'config-dir-mismatch', 'inside-project', 'project-root-invalid',
  'home-invalid', 'uv-not-found', 'crux-not-installed', 'version-mismatch', 'reader-no-json-mode',
  'offline-unavailable', 'reader-timeout', 'reader-cannot-start', 'reader-cpu-limit', 'reader-failed',
  'reader-output-invalid', 'no-active-run',
] as const
export type LaunchCode = (typeof LAUNCH_CODES)[number]

// Results that mean the reader ran out of time: its own time limit, its CPU limit, or
// the launch timeout. The hooks module stops the 15 s refresh after one of these. Each member
// is a launch code or reader-failed:<a reader error code>; a test holds that.
export const SLOW_CODES: readonly string[] = ['reader-failed:time-limit', 'reader-cpu-limit', 'reader-timeout']
export const isSlow = (code: string): boolean => SLOW_CODES.includes(code)

export type Entry = { installPath: string; version: string }

// The marketplace a plugin was installed from is the path segment under
// plugins/cache/. Under a development folder there is none, and the record key
// is crux@crux.
export function ownMarketplace(root: string): string {
  const m = /\/plugins\/cache\/([^/]+)\//.exec(root + '/')
  return m && m[1] ? m[1] : 'crux'
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

export function uvCandidates(home: string): string[] {
  return LAUNCH.uv_locations.map(spec => spec.replace('{HOME}', trimSlash(home)))
}

// The entry of the plugin record's list that this session's crux comes from, or
// undefined when there is none. An entry installed for this project (`local`, then
// `project`, matched on its projectPath) wins over the `user` entry. An entry
// installed for another project is never used. Each candidate must name an
// absolute install path and a version.
export function parseEntry(text: string, key: string, projectPaths: string[]): Entry | undefined {
  try {
    const rec: unknown = JSON.parse(text)
    const plugins = (rec as { plugins?: Record<string, unknown> } | null)?.plugins
    const list = plugins?.[key]
    if (!Array.isArray(list)) return undefined
    const here = projectPaths.map(trimSlash)
    const valid: { scope: unknown; projectPath: unknown; entry: Entry }[] = []
    for (const item of list) {
      const e = item as { installPath?: unknown; version?: unknown; scope?: unknown; projectPath?: unknown } | null
      if (typeof e?.installPath !== 'string' || !e.installPath.startsWith('/')) continue
      if (typeof e.version !== 'string') continue
      valid.push({ scope: e.scope, projectPath: e.projectPath, entry: { installPath: trimSlash(e.installPath), version: e.version } })
    }
    const ownProject = (v: (typeof valid)[number]) => typeof v.projectPath === 'string' && here.includes(trimSlash(v.projectPath))
    const pick =
      valid.find(v => v.scope === 'local' && ownProject(v)) ??
      valid.find(v => v.scope === 'project' && ownProject(v)) ??
      valid.find(v => (v.scope === 'user' || v.scope === undefined) && (v.projectPath === null || v.projectPath === undefined))
    return pick?.entry
  } catch {
    return undefined
  }
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
// The environment is cleared through `/usr/bin/env -i` because the mods API sets a
// started process's variables over Claude Code's own environment and cannot
// remove one: without -i a project's PYTHONPATH or UV_* value would reach uv and
// the interpreter.
export function buildLaunch(uv: string, entry: Entry, home: string, projectRoot: string): Launch {
  const script = LAUNCH.scripts['visualize-run-progress']
  const values: Record<string, string> = { ...LAUNCH.env_constants, HOME: trimSlash(home) }
  const pairs = LAUNCH.env_allow.map(name => `${name}=${values[name] ?? ''}`)
  const args = script.args.map(a => (a === '{project_root}' ? projectRoot : a))
  return {
    argv: [LAUNCH.launcher, ...LAUNCH.launcher_args, ...pairs, uv, ...LAUNCH.uv_args, entry.installPath + '/' + script.path, ...args],
    cwd: entry.installPath,
    timeoutMs: LAUNCH.timeout_ms,
  }
}

// uv's stderr wording when it cannot resolve offline (observed with uv 0.12.24),
// and argparse's wording for an unknown flag (a crux whose reader has no --json).
// Re-check both when either tool changes its messages.
const OFFLINE = /No interpreter found|Network connectivity is disabled|offline|downloads? (are|is) set to|No solution found|Failed to (download|fetch|resolve)/i
const USAGE_ERROR = /unrecognized arguments|the following arguments are required/
// Claude Code 2.1.296 rejects $.process.run with "aborted: still running after
// <timeoutMs>ms" when the timeout passes.
const TIMED_OUT = /still running after \d+ ?ms/
// uv exits 128 plus the signal number when its child dies by a signal. SIGXCPU is 24 on
// Darwin and Linux, so 152 with no JSON answer is a reader the kernel stopped at its
// CPU limit (observed with uv 0.12.24).
const CPU_LIMIT_EXIT = 128 + 24

export type Finished = { exitCode: number; stdout: string; stderr: string; isStdoutTruncated: boolean }
export type Outcome = { ok: true; stdout: string } | { ok: false; code: LaunchCode }

// Standard output when it is a JSON object, else the closed status code that
// names why the reader did not answer. Neither stream's text is passed on.
export function classifyFinished(res: Finished): Outcome {
  if (res.isStdoutTruncated || res.stdout.length > MAX_STDOUT) return { ok: false, code: 'reader-output-invalid' }
  if (res.stdout.trimStart().startsWith('{')) return { ok: true, stdout: res.stdout }
  if (res.exitCode === CPU_LIMIT_EXIT) return { ok: false, code: 'reader-cpu-limit' }
  if (res.exitCode !== 0) {
    if (USAGE_ERROR.test(res.stderr) && res.stderr.includes('usage:')) return { ok: false, code: 'reader-no-json-mode' }
    if (OFFLINE.test(res.stderr)) return { ok: false, code: 'offline-unavailable' }
  }
  return { ok: false, code: 'reader-failed' }
}

// A process that did not finish: still running at the timeout, or never started.
export function classifyRejection(err: unknown): { ok: false; code: LaunchCode } {
  const text = String((err as { message?: unknown } | null)?.message ?? err)
  return { ok: false, code: TIMED_OUT.test(text) ? 'reader-timeout' : 'reader-cannot-start' }
}
