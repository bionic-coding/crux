import type { EngineInterface, Register, Timer } from 'claude-code'
import {
  LAUNCH, RECORD, ancestorsOf, buildLaunch, classifyFinished, classifyRejection, isInside, isSlow, ownMarketplace,
  parseEntry, parseOwnVersion, trimSlash, uvCandidates,
} from './lib/launch.ts'
import type { Launch, LaunchCode, Outcome } from './lib/launch.ts'
import { agents, answer, bandLine, paneRows, parseReader, touchesRunFile } from './lib/view.ts'
import type { Parsed, Row } from './lib/view.ts'

// The mods loader follows `$` only into functions declared in this file, so
// every call on `$` lives here and lib/ holds pure functions.

type Eng = EngineInterface
type Plan = { ok: true; launch: Launch } | { ok: false; code: LaunchCode }

const PANE_ID = 'crux-dashboard'
// One reader run takes about 0.3 s on 144 runs, so a 15 s refresh costs little and
// keeps the band current between writes the observer cannot see (advance-run.py
// writes run files through Bash).
const REFRESH_MS = 15_000
// A burst of edits to a run file within 1.5 s starts one reader run, not one each.
const WRITE_REFRESH_MS = 1_500

// What the last reader run found. Held in memory only: a hot reload drops it
// and the next refresh restores it.
let current: Parsed | undefined
let inFlight: Promise<void> | undefined
let timer: Timer | undefined
// True while the 15 s timer skips its refresh because the reader ran out of time.
let backedOff = false
let writeScheduled = false

// A reader that runs out of time again and again (a hostile or oversized tree)
// would cost up to its whole time limit of CPU every 15 s for the rest of the
// session. After such a result the timer keeps ticking but starts no reader. A
// run-file write or /crux-dashboard still refreshes, and a refresh that ends any
// other way, a failure included, lets the timer refresh again. The timer itself
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

// One launch at a time: a caller that arrives while one is in flight waits for
// it instead of starting another.
function refresh($: Eng): Promise<void> {
  if (inFlight !== undefined) return inFlight
  inFlight = (async () => {
    let result: Parsed
    try {
      const r = await runReader($)
      result = r.ok ? parseReader(r.stdout) : r
    } catch {
      result = { ok: false, code: 'reader-failed' }
    }
    current = result
    pace(result)
    inFlight = undefined
    try {
      $.ui.invalidate('ui.render')
    } catch {
      // A redraw that cannot be asked for leaves the next refresh to draw it.
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

// The running subagents, or none when the engine cannot list them: a drawing
// never fails on the agent list.
async function agentsOf($: Eng) {
  try {
    return agents(await $.agent.list())
  } catch {
    return agents([])
  }
}

function rowsOf(Text: any, rows: Row[]) {
  return rows.map(r => {
    if (r.tone === 'bold') return <Text bold>{r.text}</Text>
    if (r.tone === 'dim') return <Text dimColor>{r.text}</Text>
    if (r.tone === 'bad') return <Text color="error">{r.text}</Text>
    return <Text>{r.text}</Text>
  })
}

export const register: Register = on => {
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
  on('tool.call', async ($, e, next) => {
    try {
      if (touchesRunFile(e)) scheduleWriteRefresh($)
    } catch {
      // An observer that cannot schedule still passes the call on.
    }
    return next(e)
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    if (e.props.hasSurvey || current === undefined) return next(e)
    const line = bandLine(current, await agentsOf($))
    if (line === null) return next(e)
    const { Box, Text } = $.ui.resolve(e) as any
    return (
      <Box>
        <Text dimColor>{line}</Text>
      </Box>
    )
  })

  on('ui.render', { component: 'Pane' }, async ($, e, next) => {
    if (e.requestId !== PANE_ID || current === undefined) return next(e)
    const rows = paneRows(current, await agentsOf($))
    const { Box, Text } = $.ui.resolve(e) as any
    return <Box flexDirection="column">{rowsOf(Text, rows)}</Box>
  })

  // The command is crux-dashboard, not dashboard: Claude Code reserves dashboard
  // for a built-in, and a hook that answered it would replace that command. The
  // name is a literal at both sites so the validator lists it as a command this
  // module answers. Always answers text: where nothing draws, the text is the
  // whole answer.
  on('command.run', { command: 'crux-dashboard' }, async $ => {
    await refresh($)
    try {
      await $.ui.open({ id: PANE_ID, title: 'Dashboard' })
    } catch {
      // The text answer stands without a pane.
    }
    return { text: answer(current ?? { ok: false, code: 'reader-failed' }) }
  })
}
