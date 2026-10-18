// What crux-mods holds that belongs to Claude Code alone: its plugin record, its status codes, its
// tool-call and agent-list shapes, its process result, its pane placement, and the text its band and
// stall note draw. The view core (launch.ts, view.ts, draw.ts, width.ts) takes these as parameters
// and names none of them, so a package for another host imports the core without this file.
// Nothing here calls `$`: the mods loader follows `$` only into functions declared in the hooks
// module itself, so every call on `$` stays in register.tsx and this file takes values and returns
// values.
import { capabilities } from '../capabilities.ts'
import { trimSlash } from './launch.ts'
import type { Finished } from './launch.ts'
import { READER_ERROR_CODES, VIEW_CODES, drawText } from './view.ts'
import type { Agent, Agents } from './view.ts'
import type { Harness, PaneLayout } from './draw.ts'

export const LAUNCH = capabilities.launch
export const RECORD = '/plugins/installed_plugins.json'

// Closed status codes of the launch. A text answer carries only these, the
// reader's own closed error codes, and values the reader emitted.
export const LAUNCH_CODES = [
  'no-env-binary', 'config-dir-mismatch', 'inside-project', 'project-root-invalid',
  'home-invalid', 'uv-not-found', 'crux-not-installed', 'version-mismatch', 'reader-no-json-mode',
  'offline-unavailable', 'reader-timeout', 'reader-cannot-start', 'reader-cpu-limit', 'reader-failed',
  'reader-output-invalid', 'no-active-run',
] as const
export type LaunchCode = (typeof LAUNCH_CODES)[number]

// Every status a refresh can end with and keep: the launch codes, the view's own codes and
// reader-failed:<each reader error code>. Together they are the 31 statuses the tests list.
export const KEPT_CODES: readonly string[] = [...LAUNCH_CODES, ...VIEW_CODES, ...READER_ERROR_CODES.map(c => `reader-failed:${c}`)]

// The result of a refresh's launch: the reader's standard output, or the code that names why there is none.
export type Result = { ok: true; stdout: string } | { ok: false; code: LaunchCode }

export type Entry = { installPath: string; version: string }

// The marketplace a plugin was installed from is the path segment under
// plugins/cache/. Under a development folder there is none, and the record key
// is crux@crux.
export function ownMarketplace(root: string): string {
  const m = /\/plugins\/cache\/([^/]+)\//.exec(root + '/')
  return m && m[1] ? m[1] : 'crux'
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

// Claude Code 2.1.296 rejects $.process.run with "aborted: still running after
// <timeoutMs>ms" when the timeout passes.
const TIMED_OUT = /still running after \d+ ?ms/

// A process that did not finish: still running at the timeout, or never started.
export function classifyRejection(err: unknown): { ok: false; code: LaunchCode } {
  const text = String((err as { message?: unknown } | null)?.message ?? err)
  return { ok: false, code: TIMED_OUT.test(text) ? 'reader-timeout' : 'reader-cannot-start' }
}

// $.process.run's result as the core's finished-process shape.
export function finishedOf(res: { exitCode: number; stdout: string; stderr: string; isStdoutTruncated: boolean }): Finished {
  return { exit: res.exitCode, stdout: res.stdout, stderr: res.stderr, truncated: res.isStdoutTruncated }
}

// The Pane render event's placement as the core's layout: inline draws the mini layout, any other
// placement the docked one.
export function layoutOf(placement: unknown): PaneLayout {
  return placement === 'inline' ? 'mini' : 'docked'
}

export const STALL_NOTE = "This session's agent list cannot see subagents in another Claude Code session, work in Codex or OpenCode, main-thread work or a background command; each can run for a long time without changing the run file."

// The text the core draws for this plugin: the band's status prefix, which says which plugin drew
// the line, and the stall note.
export const HARNESS: Harness = { bandPrefix: 'crux-mods dashboard: ', stallNote: STALL_NOTE }

type Obj = Record<string, unknown>
const MAX_AGENTS = 30

// The engine's agent list as the core's Agents: the whole list counted, at most MAX_AGENTS shown.
// A value that is not a list is an unavailable list, never an empty one.
export function agents(list: unknown): Agents {
  if (!Array.isArray(list)) return { available: false, running: 0, shown: [] }
  const shown: Agent[] = []
  let running = 0
  for (const a of list) {
    if (a === null || typeof a !== 'object') continue
    const o = a as Obj
    const status = typeof o.status === 'string' ? drawText(o.status, 20) : 'unknown'
    if (status === 'running') running++
    if (shown.length < MAX_AGENTS) {
      shown.push({
        status,
        type: typeof o.type === 'string' ? drawText(o.type, 40) : '',
        description: typeof o.description === 'string' ? drawText(o.description, 120) : '',
      })
    }
  }
  return { available: true, running, shown }
}

const WRITING_TOOLS = ['Write', 'Edit', 'MultiEdit', 'NotebookEdit']

// True when a tool call writes a file under a promptbook run directory, or is a
// shell command naming one: run-promptbook advances a run through Bash. The
// answer is the only thing taken from the event; none of it is kept.
export function touchesRunFile(e: unknown): boolean {
  if (e === null || typeof e !== 'object') return false
  const o = e as Obj
  if (o.tool === 'Bash') return typeof o.command === 'string' && (o.command.includes('/promptbooks/runs/') || o.command.includes('cycle.py') || o.command.includes('/cycles/'))
  if (typeof o.tool !== 'string' || !WRITING_TOOLS.includes(o.tool)) return false
  const path = typeof o.file_path === 'string' ? o.file_path : typeof o.notebook_path === 'string' ? o.notebook_path : ''
  return path.includes('/promptbooks/runs/') || path.includes('/cycles/')
}
