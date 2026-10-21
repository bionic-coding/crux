import { test } from 'node:test'
import assert from 'node:assert/strict'
import { fileURLToPath } from 'node:url'
import cruxOmpExtension from '../index.ts'

type Handler = (event: unknown, ctx: unknown) => unknown
type FlagDefinition = { type?: string; default?: unknown; description?: string }
type RigOptions = { cwd?: string; flagChannel?: boolean; manualTimers?: boolean }

// A file path, not a directory: the launch plan refuses it with project-root-unresolved, so the
// scheduler paints a non-empty status without starting a reader process.
const FILE_CWD = fileURLToPath(new URL('./fixtures/docs.ts', import.meta.url))

function rig(sessionId = 'session-1', options: RigOptions = {}) {
  const handlers = new Map<string, Handler>()
  const commands = new Map<string, { description: string; handler: (args: string, ctx: unknown) => unknown }>()
  const widgets = new Map<string, unknown>()
  const statuses = new Map<string, string | undefined>()
  const notices: string[] = []
  const flags = new Map<string, FlagDefinition>()
  const flagValues = new Map<string, unknown>()
  const timers = new Map<number, () => void>()
  let nextTimer = 0
  let label = ''

  const pi = {
    setLabel: (value: string) => {
      label = value
    },
    on: (event: string, handler: Handler) => {
      handlers.set(event, handler)
      return () => handlers.delete(event)
    },
    registerCommand: (name: string, definition: { description: string; handler: (args: string, ctx: unknown) => unknown }) => {
      commands.set(name, definition)
      return () => commands.delete(name)
    },
    ...(options.flagChannel === false
      ? {}
      : {
          registerFlag: (name: string, definition: FlagDefinition) => {
            flags.set(name, definition)
            if (definition.default !== undefined) flagValues.set(name, definition.default)
          },
          getFlag: (name: string) => (flags.has(name) ? flagValues.get(name) : undefined),
        }),
  }

  const schedule = (fn: () => void) => {
    nextTimer += 1
    if (options.manualTimers === true) timers.set(nextTimer, fn)
    return nextTimer
  }

  const ctx = {
    cwd: options.cwd ?? process.cwd(),
    agent: { kind: 'main' },
    sessionManager: { getSessionId: () => sessionId },
    ui: {
      setWidget: (key: string, content: unknown) => {
        widgets.set(key, content)
      },
      setStatus: (key: string, text: string | undefined) => {
        statuses.set(key, text)
      },
      notify: (text: string) => {
        notices.push(text)
      },
    },
    setTimeout: (fn: () => void, _ms: number) => schedule(fn),
    setInterval: (fn: () => void, _ms: number) => schedule(fn),
    clearTimer: (handle: unknown) => {
      if (typeof handle === 'number') timers.delete(handle)
    },
  }

  const cleanup = cruxOmpExtension(pi as never)

  // Runs the scheduler's queued timers in order. The scheduler only reaches the reader start after
  // its hold and poll timers, so this drives the same path a live host does.
  const runTimers = () => {
    let steps = 0
    while (timers.size > 0) {
      if (steps++ > 64) throw new Error('timer chain did not settle')
      const next = timers.entries().next().value as [number, () => void]
      timers.delete(next[0])
      next[1]()
    }
  }

  return { handlers, commands, widgets, statuses, notices, ctx, cleanup, flags, flagValues, runTimers, label: () => label }
}

test('the factory registers the lifecycle, tool, input and command surfaces', () => {
  const r = rig()
  assert.equal(r.label(), 'Crux dashboard')
  for (const event of [
    'session_start',
    'session_switch',
    'session_shutdown',
    'before_subagent_spawn',
    'tool_execution_start',
    'tool_execution_update',
    'tool_execution_end',
    'tool_result',
    'input',
  ]) {
    assert.equal(r.handlers.has(event), true, event)
  }
  assert.equal(r.commands.has('crux-dashboard'), true)
  r.cleanup?.()
})

test('session_start clears the status when nothing is kept and no subagents run', async () => {
  const r = rig()
  await r.handlers.get('session_start')?.({}, r.ctx)
  assert.equal(r.widgets.get('crux-band'), undefined)
  assert.equal(r.statuses.get('crux'), undefined)
  r.cleanup?.()
})

test('subagent nesting and blocked-agent detection render live in the dashboard', async () => {
  const r = rig('main-1')
  await r.handlers.get('session_start')?.({}, r.ctx)
  await r.commands.get('crux-dashboard')!.handler('', r.ctx)

  // Spawn parent subagent (dev-lead) and nested child subagent (developer)
  await r.handlers.get('before_subagent_spawn')?.({ agent: 'dev-lead', spawnKey: 'LeadAgent' }, r.ctx)
  await r.handlers.get('session_start')?.(
    {},
    { ...r.ctx, agent: { kind: 'sub', id: 'LeadAgent', name: 'dev-lead', depth: 1 } },
  )
  await r.handlers.get('before_subagent_spawn')?.(
    { agent: 'developer', spawnKey: 'LeadAgent.UnitDev' },
    { ...r.ctx, agent: { kind: 'sub', id: 'LeadAgent', name: 'dev-lead', depth: 1 } },
  )
  await r.handlers.get('tool_execution_start')?.(
    { toolCallId: 'c1', toolName: 'edit', args: { path: 'src/index.ts', i: 'Editing index.ts' } },
    { ...r.ctx, agent: { kind: 'sub', id: 'LeadAgent.UnitDev', name: 'developer', depth: 2, parentId: 'LeadAgent' } },
  )

  const factory = r.widgets.get('crux-panel') as (tui: unknown, theme: unknown) => { render: (w: number) => readonly string[] }
  const lines = factory(null, null).render(100).join('\n')
  assert.match(lines, /NOW RUNNING & SUBAGENT TREE/)
  assert.match(lines, /LeadAgent/)
  assert.match(lines, /└─ ▸ UnitDev \(developer\)/)
  assert.match(lines, /edit Editing index\.ts/)
  r.cleanup?.()
})

test('the command opens the panel and paints it', async () => {
  const r = rig()
  await r.handlers.get('session_start')?.({}, r.ctx)
  await r.commands.get('crux-dashboard')!.handler('', r.ctx)
  assert.ok(r.widgets.has('crux-panel'))
  r.cleanup?.()
})

test('a run-phrase input and a run-file tool result are accepted without throwing', async () => {
  const r = rig()
  await r.handlers.get('session_start')?.({}, r.ctx)
  await r.handlers.get('input')?.({ text: 'show the run', source: 'interactive' }, r.ctx)
  await r.handlers.get('tool_result')?.({ toolName: 'write', input: { path: '/repo/bionic/cycles/CYCLE-1.yml' } }, r.ctx)
  await r.handlers.get('input')?.({ text: 'unrelated', source: 'interactive' }, r.ctx)
  r.cleanup?.()
})

test('a subagent session starts no dashboard', async () => {
  const r = rig('sub-1')
  await r.handlers.get('session_start')?.({}, { ...r.ctx, agent: { kind: 'sub' } })
  assert.equal(r.widgets.size, 0)
  r.cleanup?.()
})

test('session_shutdown clears the widgets and status', async () => {
  const r = rig()
  await r.handlers.get('session_start')?.({}, r.ctx)
  await r.commands.get('crux-dashboard')!.handler('', r.ctx)
  await r.handlers.get('session_shutdown')?.({}, r.ctx)
  assert.equal(r.widgets.get('crux-band'), undefined)
  assert.equal(r.widgets.get('crux-panel'), undefined)
  assert.equal(r.statuses.get('crux'), undefined)
  r.cleanup?.()
})

test('the registered cruxOmpBand flag hides only the band', async () => {
  const r = rig('session-1', { cwd: FILE_CWD, manualTimers: true })
  r.flagValues.set('cruxOmpBand', 'false')
  await r.handlers.get('session_start')?.({}, r.ctx)
  r.runTimers()

  // The band would have drawn the refusal line, so this assertion is not vacuous.
  assert.equal(r.widgets.get('crux-band'), undefined)
  const status = r.statuses.get('crux')
  assert.equal(typeof status, 'string')
  assert.ok(status !== undefined && status.length > 0, 'the status bar stays populated')

  await r.commands.get('crux-dashboard')!.handler('', r.ctx)
  const panel = r.widgets.get('crux-panel') as ((tui: unknown, theme: unknown) => { render: (width: number) => readonly string[] }) | undefined
  assert.equal(typeof panel, 'function')
  assert.ok(panel !== undefined && panel(null, null).render(100).length > 0, 'the panel still renders')
  assert.equal(r.flags.get('cruxOmpBand')?.default, 'true')
  r.cleanup?.()
})

test('the band shows by default and when the host has no flag channel', async () => {
  const enabled = rig('session-1', { cwd: FILE_CWD, manualTimers: true })
  await enabled.handlers.get('session_start')?.({}, enabled.ctx)
  enabled.runTimers()
  const enabledBand = enabled.widgets.get('crux-band')
  assert.ok(Array.isArray(enabledBand) && enabledBand.length > 0)
  assert.ok((enabled.statuses.get('crux') ?? '').length > 0)
  enabled.cleanup?.()

  const older = rig('session-2', { cwd: FILE_CWD, manualTimers: true, flagChannel: false })
  await older.handlers.get('session_start')?.({}, older.ctx)
  older.runTimers()
  const olderBand = older.widgets.get('crux-band')
  assert.ok(Array.isArray(olderBand) && olderBand.length > 0)
  assert.ok((older.statuses.get('crux') ?? '').length > 0)
  older.cleanup?.()
})
