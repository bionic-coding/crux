import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register, Timer } from 'claude-code'
import {
  LAUNCH, RECORD, ancestorsOf, buildLaunch, classifyFinished, classifyRejection, isInside, isSlow, ownMarketplace,
  parseEntry, parseOwnVersion, trimSlash, uvCandidates,
} from './lib/launch.ts'
import type { Launch, LaunchCode, Outcome } from './lib/launch.ts'
import { KEPT_SHAPE, agents, answer, kept, parseReader, touchesRunFile } from './lib/view.ts'
import type { Parsed } from './lib/view.ts'
import type { Kept } from '../types'
import { band, pane, styleOf } from './lib/draw.ts'
import type { Block } from './lib/draw.ts'
import { asksForTheRun } from './lib/phrases.ts'

// The mods loader follows `$` only into functions declared in this file, so
// every call on `$` lives here and lib/ holds pure functions.

type Eng = EngineInterface
type Plan = { ok: true; launch: Launch } | { ok: false; code: LaunchCode }

const PANE_ID = 'crux-dashboard'
// One reader run takes about 0.3 s on 144 runs, so a 15 s refresh costs little and
// keeps the band current between writes the observer cannot see, such as a run
// file written by a command that does not name its path.
const REFRESH_MS = 15_000
// A burst of edits to a run file, or of commands naming one, within 1.5 s starts
// one reader run, not one each.
const WRITE_REFRESH_MS = 1_500
// A request for the run refreshes on the next tick: the pane draws the kept result at once, and
// the refresh replaces it when the reader answers.
const OPEN_REFRESH_MS = 0

// What the last reader run found, kept by Claude Code for the session so a reload of this
// code keeps the band and the pane. It holds only checked reader output or a closed status
// code, never an event payload. Claude Code holds it in memory and writes no file.
const current = atom({ plugin: 'crux-mods', key: 'current' } as const, null as Kept | null, { shape: KEPT_SHAPE })
let inFlight: Promise<Parsed> | undefined
let timer: Timer | undefined
// True while the 15 s timer skips its refresh because the reader ran out of time.
let backedOff = false
let writeScheduled = false

// A reader that runs out of time again and again (a hostile or oversized tree)
// would cost up to its whole time limit of CPU every 15 s for the rest of the
// session. After such a result the timer keeps ticking but starts no reader. A
// run-file write, a command naming a run file, a request for the run, or
// /crux-dashboard still refreshes, and a refresh that ends any other way, a
// failure included, lets the timer refresh again. The timer itself
// is never stopped and restarted: it lives on the session.start dispatch, where
// session-long work belongs, and the mods loader lets no hook keep that `$`.
function pace(p: Parsed) {
  backedOff = !p.ok && isSlow(p.code)
}

async function statOf($: Eng, path: string) {
  try {
    return await $.fs.stat(path, { resolve: true })
  } catch {
    return undefined
  }
}

async function sameDir($: Eng, a: string, b: string): Promise<boolean> {
  if (trimSlash(a) === trimSlash(b)) return true
  const sa = await statOf($, a)
  const sb = await statOf($, b)
  return sa?.realPath !== undefined && sa.realPath === sb?.realPath
}

// Every loader variable is a literal call so the validator lists each name. The
// mod refuses instead of relying on `env -i`: /usr/bin/env itself starts under the
// inherited environment before it clears anything, so a dynamic-loader variable
// could run code inside env.
async function anyLoaderVarSet($: Eng): Promise<boolean> {
  const values = await Promise.all([
    $.env.get('LD_PRELOAD'),
    $.env.get('LD_AUDIT'),
    $.env.get('LD_LIBRARY_PATH'),
    $.env.get('DYLD_INSERT_LIBRARIES'),
    $.env.get('DYLD_LIBRARY_PATH'),
    $.env.get('DYLD_FRAMEWORK_PATH'),
    $.env.get('DYLD_FALLBACK_LIBRARY_PATH'),
    $.env.get('DYLD_FALLBACK_FRAMEWORK_PATH'),
    $.env.get('DYLD_VERSIONED_LIBRARY_PATH'),
    $.env.get('DYLD_VERSIONED_FRAMEWORK_PATH'),
    $.env.get('DYLD_ROOT_PATH'),
    $.env.get('DYLD_IMAGE_SUFFIX'),
  ])
  return values.some(v => v !== undefined)
}

// Refusals run in a fixed order: the launcher, the loader, the project root,
// the record, the paths that must lie outside the project, uv, the version.
async function planLaunch($: Eng): Promise<Plan> {
  const no = (code: LaunchCode): Plan => ({ ok: false, code })
  const pluginRoot = $.plugin.root

  const launcher = await statOf($, LAUNCH.launcher)
  if (launcher === undefined || launcher.kind !== 'file') return no('no-env-binary')

  if (await anyLoaderVarSet($)) return no('loader-var-set')

  // The session's project root, which a shell `cd` does not move; the directory
  // the session runs in can be a subdirectory or another repository.
  const projectRoot = await $.session.root()
  const project = await statOf($, projectRoot)
  if (project === undefined || project.kind !== 'dir') return no('project-root-invalid')
  const projectReal = project.realPath ?? projectRoot

  const home = await $.env.get('HOME')
  const claudeDir = await $.env.get('CLAUDE_CONFIG_DIR')
  if (home === undefined || !home.startsWith('/')) return no('home-invalid')

  // The config dir is the nearest ancestor of this plugin's root that holds the
  // plugin record: an installed crux-mods lives under <config>/plugins/cache/, so
  // that ancestor is the config Claude Code loaded it from, whatever the session's
  // CLAUDE_CONFIG_DIR says. A CLAUDE_CONFIG_DIR naming another directory means the
  // two disagree about which crux is installed, and the mod refuses rather than
  // guess. A development folder has no such ancestor and falls back to the variable.
  let above: string | undefined
  for (const dir of ancestorsOf(pluginRoot)) {
    const st = await statOf($, dir + RECORD)
    if (st !== undefined && st.kind === 'file') {
      above = dir
      break
    }
  }
  let configDir: string
  if (above !== undefined) {
    if (claudeDir !== undefined && claudeDir !== '' && !(await sameDir($, claudeDir, above))) return no('config-dir-mismatch')
    configDir = above
  } else {
    configDir = claudeDir !== undefined && claudeDir !== '' ? claudeDir : home + '/.claude'
  }
  configDir = trimSlash(configDir)

  const recordPath = configDir + RECORD
  const recordStat = await statOf($, recordPath)
  if (recordStat === undefined || recordStat.kind !== 'file') return no('crux-not-installed')
  let recordText = ''
  try {
    recordText = await $.fs.read(recordPath)
  } catch {
    return no('crux-not-installed')
  }
  const entry = parseEntry(recordText, `crux@${ownMarketplace(pluginRoot)}`, [projectRoot, projectReal])
  if (entry === undefined) return no('crux-not-installed')

  let uv: string | undefined
  for (const path of uvCandidates(home)) {
    const st = await statOf($, path)
    if (st !== undefined && st.kind === 'file') {
      uv = path
      break
    }
  }

  // Everything the launch reads or runs must lie outside the project, links resolved.
  const reach = [configDir, entry.installPath, trimSlash(home), home + '/.cache/uv', home + '/.local/share/uv']
  if (uv !== undefined) reach.push(uv)
  for (const path of reach) {
    const st = await statOf($, path)
    if (isInside(st?.realPath ?? path, projectReal)) return no('inside-project')
  }
  if (uv === undefined) return no('uv-not-found')

  let own: string | undefined
  try {
    own = parseOwnVersion(await $.fs.read(pluginRoot + '/.claude-plugin/plugin.json'))
  } catch {
    own = undefined
  }
  if (own === undefined || own !== entry.version) return no('version-mismatch')

  return { ok: true, launch: buildLaunch(uv, entry, home, projectRoot) }
}

async function runReader($: Eng): Promise<Outcome> {
  const plan = await planLaunch($)
  if (!plan.ok) return plan
  try {
    const res = await $.process.run(plan.launch.argv, { cwd: plan.launch.cwd, timeoutMs: plan.launch.timeoutMs })
    return classifyFinished(res)
  } catch (err) {
    return classifyRejection(err)
  }
}

// The kept result as a result to draw, or null when nothing is kept. A read that Claude Code
// refuses reads as nothing kept, so a drawing passes its event on, as agentsOf does for the agent
// list.
async function keptNow($: Eng): Promise<Parsed | null> {
  try {
    return kept(await read($, current))
  } catch {
    return null
  }
}

// The only writer of the kept result, called from refresh. A refused write never becomes a status
// code. When Claude Code refuses the value, one write of null replaces what stands. When that is
// refused too, what stands stays until a later write lands.
async function keepResult($: Eng, keep: Kept): Promise<void> {
  try {
    await update($, current, () => keep)
  } catch {
    try {
      await update($, current, () => null)
    } catch {
      // The next refresh writes again.
    }
  }
}

// One launch at a time: a caller that arrives while one is in flight waits for
// it instead of starting another. It returns the result its own launch produced.
function refresh($: Eng): Promise<Parsed> {
  if (inFlight !== undefined) return inFlight
  inFlight = (async () => {
    try {
      let result: Parsed
      let keep: Kept
      try {
        const r = await runReader($)
        if (r.ok) {
          result = parseReader(r.stdout)
          keep = result.ok ? { ok: true, stdout: r.stdout } : { ok: false, code: result.code }
        } else {
          result = r
          keep = { ok: false, code: r.code }
        }
      } catch {
        result = { ok: false, code: 'reader-failed' }
        keep = { ok: false, code: 'reader-failed' }
      }
      await keepResult($, keep)
      pace(result)
      try {
        $.ui.invalidate('ui.render')
      } catch {
        // A redraw that cannot be asked for leaves the next refresh to draw it.
      }
      return result
    } finally {
      inFlight = undefined
    }
  })()
  return inFlight
}

function scheduleWriteRefresh($: Eng) {
  if (writeScheduled) return
  writeScheduled = true
  $.clock.after(WRITE_REFRESH_MS, () => {
    writeScheduled = false
    void refresh($)
  })
}

// Schedules the refresh that follows a request for the run. It runs from a timer of its own and
// captures `$` alone, so no part of the prompt reaches it, and it outlives the dispatch that set it.
function scheduleOpenRefresh($: Eng) {
  $.clock.after(OPEN_REFRESH_MS, () => {
    void refresh($)
  })
}

// This session's subagents, or an unavailable list when the engine cannot list them: a
// drawing never fails on the agent list.
async function agentsOf($: Eng) {
  try {
    return agents(await $.agent.list())
  } catch {
    return agents(undefined)
  }
}

// A block from lib/draw.ts as elements. A line is one Text holding a Text per span, so it stays one
// line of text: sibling Texts in a row Box would be laid out side by side as columns. A box is a Box,
// round-bordered with one cell of padding when it names a border key. The dashboard draws no
// other element.
function element(Box: any, Text: any, b: Block): any {
  if (b.kind === 'line') return <Text wrap="truncate">{b.line.map(s => <Text {...styleOf(s)}>{s.text}</Text>)}</Text>
  const children = b.children.map(c => element(Box, Text, c))
  if (b.border !== null) {
    return (
      <Box flexDirection={b.direction} width={b.width} borderStyle="round" borderColor={b.border} paddingX={1}>
        {children}
      </Box>
    )
  }
  if (b.direction === 'row') {
    return (
      <Box flexDirection="row" width={b.width} columnGap={b.gap}>
        {children}
      </Box>
    )
  }
  return (
    <Box flexDirection="column" width={b.width}>
      {children}
    </Box>
  )
}

export const register: Register = (on, options) => {
  // True only when an options object arrives and its setting is true or unset. An unset value keeps
  // the decided default, on, for an engine that passes options without filling it. An engine that
  // passes no options object gets no prompt hook, so it reads no prompt. The object is checked
  // before the setting is read, so `register` does not throw on it. The other hooks still register,
  // so the band, the pane and /crux-dashboard still work. Claude Code 2.1.293, 2.1.296 and 2.1.299
  // were observed passing options with the default filled. The check names both values instead of
  // `!== false`, so a value of another type never reads as on.
  const readPrompts = options != null && (options.read_prompts === true || options.read_prompts === undefined)

  // The hook exists only while the setting is on, so with it off no prompt is read.
  // It observes only: it keeps nothing of the prompt, never delays or refuses it, and awaits nothing
  // before `next(e)`. Ahead of `next(e)` it does a few property reads (the origin, its kind, the
  // attachments and the text) and, on a match, asks for the pane and sets a timer. A failure inside
  // the `try` is swallowed and the prompt still goes on.
  if (readPrompts) {
    on('prompt.submit', async ($, e, next) => {
      try {
        if (asksForTheRun(e)) {
          $.ui.open({ id: PANE_ID, title: 'Dashboard' }).catch(() => {})
          scheduleOpenRefresh($)
        }
      } catch {}
      return next(e)
    })
  }

  on('session.start', async ($, e, next) => {
    try {
      await $.command.register({ name: 'crux-dashboard', description: 'Show in-progress promptbook runs: prompts, council decisions, gates and subagents', immediate: true })
    } catch {
      // Without the command the band and the pane still draw.
    }
    if (timer !== undefined) timer.cancel()
    backedOff = false
    timer = $.clock.every(REFRESH_MS, () => {
      if (!backedOff) void refresh($)
    })
    void refresh($)
    return next(e)
  })

  // Observes only: the event goes on unchanged, and nothing of the payload is kept.
  // The refresh is scheduled once the call has finished, so a slow command that
  // writes a run file is read after its write, not during it.
  on('tool.call', async ($, e, next) => {
    const result = await next(e)
    try {
      if (touchesRunFile(e)) scheduleWriteRefresh($)
    } catch {
      // An observer that cannot schedule still returns the call's result.
    }
    return result
  })

  // The band is one borderless line fitted to the width the event reports. Draw only: the handler
  // reads the event's props and the agent list, and adds nothing Claude reads.
  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    if (e.props.hasSurvey) return next(e)
    const now = await keptNow($)
    if (now === null) return next(e)
    const block = band(now, await agentsOf($), e.props.bodyColumns)
    if (block === null) return next(e)
    const { Box, Text } = $.ui.resolve(e) as any
    return element(Box, Text, block)
  })

  // The pane draws its mini layout when it is inline and its full layout otherwise, at the width the
  // event reports.
  on('ui.render', { component: 'Pane' }, async ($, e, next) => {
    if (e.requestId !== PANE_ID) return next(e)
    const now = await keptNow($)
    if (now === null) return next(e)
    const block = pane(now, await agentsOf($), e.props.bodyColumns, e.props.placement)
    const { Box, Text } = $.ui.resolve(e) as any
    return element(Box, Text, block)
  })

  // The command is crux-dashboard, not dashboard: Claude Code reserves dashboard
  // for a built-in, and a hook that answered it would replace that command. The
  // name is a literal at both sites so the validator lists it as a command this
  // module answers. Always answers text: where nothing draws, the text is the
  // whole answer.
  on('command.run', { command: 'crux-dashboard' }, async $ => {
    const result = await refresh($)
    try {
      await $.ui.open({ id: PANE_ID, title: 'Dashboard' })
    } catch {
      // The text answer stands without a pane.
    }
    return { text: answer(result) }
  })
}
