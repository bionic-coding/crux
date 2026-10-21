// The entry OMP loads: the run band above the editor, the run dashboard panel and the
// /crux-dashboard command. This is the one file that imports a host package or a built-in module
// and the one file that names the host's context. Everything else is a pure module that reaches
// the host through the Host value built here.
import type { ExtensionAPI } from '@oh-my-pi/pi-coding-agent'
import { spawn } from 'node:child_process'
import { readFileSync, realpathSync, statSync } from 'node:fs'
import { dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { runCommand } from './lib/command.ts'
import { asksForTheRun, summarizeToolDetail, touchesRunFile } from './lib/events.ts'
import type { Host, KeptEnvelope, ReaderSink } from './lib/host.ts'
import { registerAll } from './lib/lifecycle.ts'
import { parseCycleQueueYaml } from './lib/live.ts'
import type { ActiveToolEntry, AsyncJobInfo, LiveRuntimeSnapshot, SubagentNode } from './lib/live.ts'
import { createScheduler } from './lib/refresh.ts'
import type { Scheduler } from './lib/refresh.ts'
import { bandLines, panelLines, readView } from './lib/render.ts'
import type { OmpStyler } from './lib/render.ts'

// The width the drawing is fitted to. OMP's widget strings are rendered by the host, which clips
// what does not fit; a fixed width keeps every row within a normal terminal.
const WIDTH = 120
const BAND = 'crux-band'
const PANEL = 'crux-panel'
const STATUS = 'crux'
const LEASE_KEY = Symbol.for('crux-omp.lease')
const LIVE_KEY = Symbol.for('crux-omp.live')

type WidgetComponent = {
  render: (width: number) => readonly string[]
  invalidate: () => void
}

type WidgetContent = string[] | ((tui: unknown, theme: unknown) => WidgetComponent) | undefined

type Ui = {
  setWidget: (key: string, content: WidgetContent) => void
  setStatus: (key: string, text: string | undefined) => void
  notify: (text: string, level?: 'info' | 'warning' | 'error') => void
}

type AgentInfo = {
  kind?: string
  id?: string
  name?: string
  depth?: number
  parentId?: string
}

type Ctx = {
  cwd: string
  ui: Ui
  agent?: AgentInfo
  sessionManager: { getSessionId: () => string }
  getAsyncJobSnapshot?: () => unknown
  setTimeout: (fn: () => void, ms: number) => unknown
  setInterval: (fn: () => void, ms: number) => unknown
  clearTimer: (handle: unknown) => void
}

type LeaseCell = { running: boolean }

type LiveStore = {
  subagents: Map<string, SubagentNode>
  activeTools: Map<string, ActiveToolEntry>
  mainPaint: (() => void) | null
}

type Session = {
  host: Host
  scheduler: Scheduler
  paint: () => void
  stop: () => void
  docsDir: () => string | undefined
}

const liveStore = (): LiveStore => {
  const scope = globalThis as unknown as { [key: symbol]: LiveStore | undefined }
  const existing = scope[LIVE_KEY]
  if (existing !== undefined) return existing
  const created: LiveStore = {
    subagents: new Map<string, SubagentNode>(),
    activeTools: new Map<string, ActiveToolEntry>(),
    mainPaint: null,
  }
  scope[LIVE_KEY] = created
  return created
}

// The lease lives on the process, not in a factory closure: OMP can reload an extension, and the
// reloaded factory must see the reader the previous one may still have running.
const leaseCell = (): LeaseCell => {
  const scope = globalThis as unknown as { [key: symbol]: LeaseCell | undefined }
  const existing = scope[LEASE_KEY]
  if (existing !== undefined) return existing
  const created: LeaseCell = { running: false }
  scope[LEASE_KEY] = created
  return created
}

const asText = (value: unknown): string | undefined => (typeof value === 'string' ? value : undefined)
const asNumber = (value: unknown): number | undefined => (typeof value === 'number' ? value : undefined)
const asByte = (value: unknown): number => (typeof value === 'number' ? value : -1)

export default function cruxOmpExtension(pi: ExtensionAPI): (() => void) | undefined {
  const cloneDir = dirname(dirname(fileURLToPath(import.meta.url)))
  const sessions = new Map<string, Session>()

  const keyOf = (ctx: Ctx): string => {
    try {
      return ctx.sessionManager.getSessionId()
    } catch {
      return 'default'
    }
  }

  const extractAsyncJobs = (ctx: Ctx): AsyncJobInfo[] => {
    if (typeof ctx.getAsyncJobSnapshot !== 'function') return []
    try {
      const snap = ctx.getAsyncJobSnapshot()
      if (snap === null || typeof snap !== 'object') return []
      const s = snap as Record<string, unknown>
      const rawList = Array.isArray(s.jobs) ? s.jobs : Array.isArray(s.running) ? s.running : []
      const out: AsyncJobInfo[] = []
      for (const item of rawList) {
        if (item !== null && typeof item === 'object') {
          const rec = item as Record<string, unknown>
          const id = typeof rec.id === 'string' ? rec.id : typeof rec.jobId === 'string' ? rec.jobId : ''
          if (id !== '') {
            out.push({
              id,
              type: typeof rec.type === 'string' ? rec.type : 'job',
              state: typeof rec.state === 'string' ? rec.state : typeof rec.status === 'string' ? rec.status : 'running',
              label: typeof rec.label === 'string' ? rec.label : undefined,
            })
          }
        }
      }
      return out
    } catch {
      return []
    }
  }

  const ensureSubagentFromCtx = (ctx: Ctx) => {
    if (ctx.agent?.kind !== 'sub') return
    const id = typeof ctx.agent.id === 'string' && ctx.agent.id !== '' ? ctx.agent.id : typeof ctx.agent.name === 'string' && ctx.agent.name !== '' ? ctx.agent.name : 'subagent'
    const name = typeof ctx.agent.name === 'string' && ctx.agent.name !== '' ? ctx.agent.name : id
    const depth = typeof ctx.agent.depth === 'number' ? ctx.agent.depth : 1
    const parentId = typeof ctx.agent.parentId === 'string' && ctx.agent.parentId !== '' ? ctx.agent.parentId : null
    const store = liveStore()
    const now = Date.now()
    const existing = store.subagents.get(id)
    if (existing !== undefined) {
      existing.updatedAtMs = now
      if (existing.parentId === null && parentId !== null) existing.parentId = parentId
      return
    }
    store.subagents.set(id, {
      id,
      name,
      role: name,
      parentId,
      depth,
      status: 'running',
      task: '',
      activeTool: null,
      toolTarget: null,
      startedAtMs: now,
      updatedAtMs: now,
      model: null,
      blockerReason: null,
    })
  }

  const updateFromTaskToolCall = (event: Record<string, unknown>, ctx: Ctx, phase: 'start' | 'update' | 'end') => {
    const store = liveStore()
    const now = Date.now()
    const callerId = ctx.agent?.kind === 'sub' ? (typeof ctx.agent.id === 'string' && ctx.agent.id !== '' ? ctx.agent.id : null) : null
    const callerDepth = ctx.agent?.kind === 'sub' && typeof ctx.agent.depth === 'number' ? ctx.agent.depth : 0
    const args = (event.args ?? event.input) as Record<string, unknown> | undefined
    if (phase === 'start' && args !== undefined && args !== null && typeof args === 'object') {
      const items = Array.isArray(args.tasks) ? args.tasks : [args]
      for (const raw of items) {
        if (raw === null || typeof raw !== 'object') continue
        const item = raw as Record<string, unknown>
        const name = typeof item.name === 'string' && item.name !== '' ? item.name : typeof item.agent === 'string' && item.agent !== '' ? item.agent : ''
        if (name === '') continue
        const role = typeof item.agent === 'string' && item.agent !== '' ? item.agent : 'task'
        const taskText = typeof item.task === 'string' ? item.task.replace(/\s+/g, ' ').trim().slice(0, 80) : ''
        const id = callerId !== null && !name.includes('.') ? `${callerId}.${name}` : name
        if (!store.subagents.has(id)) {
          store.subagents.set(id, {
            id,
            name,
            role,
            parentId: callerId,
            depth: callerDepth + 1,
            status: 'running',
            task: taskText,
            activeTool: null,
            toolTarget: null,
            startedAtMs: now,
            updatedAtMs: now,
            model: null,
            blockerReason: null,
          })
        }
      }
    }
    const resultObj = (event.partialResult ?? event.result ?? event) as Record<string, unknown> | undefined
    const details = (resultObj?.details ?? event.details) as Record<string, unknown> | undefined
    if (details !== undefined && details !== null && typeof details === 'object') {
      const progressList = Array.isArray(details.progress) ? details.progress : []
      for (const p of progressList) {
        if (p === null || typeof p !== 'object') continue
        const prog = p as Record<string, unknown>
        const rawId = typeof prog.id === 'string' && prog.id !== '' ? prog.id : typeof prog.name === 'string' ? prog.name : ''
        if (rawId === '') continue
        const existing = store.subagents.get(rawId)
        const statusStr = typeof prog.status === 'string' ? prog.status : typeof prog.state === 'string' ? prog.state : 'running'
        const mappedStatus =
          statusStr === 'completed' || statusStr === 'done'
            ? 'done'
            : statusStr === 'failed' || statusStr === 'error' || statusStr === 'aborted'
              ? 'error'
              : statusStr === 'idle' || statusStr === 'parked'
                ? 'idle'
                : 'running'
        const curTool = typeof prog.currentTool === 'string' ? prog.currentTool : typeof prog.tool === 'string' ? prog.tool : null
        if (existing !== undefined) {
          existing.status = mappedStatus
          existing.updatedAtMs = now
          if (curTool !== null) existing.activeTool = curTool
        } else {
          store.subagents.set(rawId, {
            id: rawId,
            name: rawId,
            role: typeof prog.agent === 'string' ? prog.agent : 'task',
            parentId: callerId,
            depth: callerDepth + 1,
            status: mappedStatus,
            task: typeof prog.description === 'string' ? prog.description : '',
            activeTool: curTool,
            toolTarget: null,
            startedAtMs: now,
            updatedAtMs: now,
            model: null,
            blockerReason: null,
          })
        }
      }
      if (phase === 'end' && Array.isArray(details.results)) {
        for (const r of details.results) {
          if (r === null || typeof r !== 'object') continue
          const res = r as Record<string, unknown>
          const rawId = typeof res.id === 'string' ? res.id : ''
          const node = store.subagents.get(rawId)
          if (node !== undefined) {
            node.status = res.error || res.aborted ? 'error' : 'done'
            node.activeTool = null
            node.toolTarget = null
            node.updatedAtMs = now
          }
        }
      }
    }
  }

  const makeSession = (ctx: Ctx): Session => {
    const state: { current: KeptEnvelope | null; docsDir: string | undefined } = { current: null, docsDir: undefined }
    let panel = false

    const buildLiveSnapshot = (): LiveRuntimeSnapshot => {
      const store = liveStore()
      const nowMs = Date.now()
      const asyncJobs = extractAsyncJobs(ctx)
      // Merge any task jobs from getAsyncJobSnapshot into subagents if not already present
      for (const job of asyncJobs) {
        if (job.type === 'task' && !store.subagents.has(job.id)) {
          store.subagents.set(job.id, {
            id: job.id,
            name: job.id,
            role: 'task',
            parentId: null,
            depth: 1,
            status: job.state === 'running' ? 'running' : job.state === 'failed' ? 'error' : 'done',
            task: job.label ?? '',
            activeTool: null,
            toolTarget: null,
            startedAtMs: nowMs,
            updatedAtMs: nowMs,
            model: null,
            blockerReason: null,
          })
        }
      }
      // Prune completed subagents older than 2 minutes so the tree stays focused on active/recent work
      for (const [id, node] of store.subagents.entries()) {
        if ((node.status === 'done' || node.status === ' idle' as never) && nowMs - node.updatedAtMs > 120_000) {
          store.subagents.delete(id)
        }
      }
      let queue = null
      const cwd = asText(ctx.cwd)
      if (cwd !== undefined && cwd.startsWith('/')) {
        const docsDir = state.docsDir ?? 'bionic'
        const rawQueue = host.read(`${cwd.replace(/\/+$/, '')}/${docsDir}/queue/cycles.yaml`)
        if (rawQueue !== undefined) {
          queue = parseCycleQueueYaml(rawQueue)
        }
      }
      return {
        nowMs,
        mainStreaming: store.activeTools.size > 0,
        activeTools: [...store.activeTools.values()],
        subagents: [...store.subagents.values()],
        asyncJobs,
        queue,
      }
    }

    // Extension flags belong to the host API, not to a handler context. A host without the flag
    // channel, or one that never registered the flag, keeps the band. The value is a string
    // because OMP's boolean flag form can only set true; `--cruxOmpBand=false` is the off form.
    const showBand = (() => {
      try {
        if (typeof getFlag !== 'function') return true
        return getFlag.call(pi, 'cruxOmpBand') !== 'false'
      } catch {
        return true
      }
    })()

    const paint = () => {
      const parsed = readView(() => state.current)
      if (parsed !== null && parsed.ok) state.docsDir = parsed.view.docs_dir
      const live = buildLiveSnapshot()
      const band = bandLines(parsed, WIDTH, live)
      const status = band === null || band.length === 0 ? undefined : band[0]
      try {
        ctx.ui.setWidget(BAND, showBand ? (band ?? undefined) : undefined)
      } catch {
        // The next paint writes again.
      }
      try {
        ctx.ui.setStatus(STATUS, status)
      } catch {
        // The next paint writes again.
      }
      try {
        ctx.ui.setWidget(
          PANEL,
          panel
            ? (_tui: unknown, theme: unknown) => {
                const styler = theme !== null && typeof theme === 'object' ? (theme as OmpStyler) : undefined
                return {
                  render: (width: number) => panelLines(parsed, width, buildLiveSnapshot(), styler) ?? [],
                  invalidate: () => {},
                }
              }
            : undefined,
        )
      } catch {
        // The next paint writes again.
      }
    }

    const host: Host = {
      directory: asText(ctx.cwd),
      cloneDir,
      // One case per name the manifest's launch block allows. Each read is spelled with a literal
      // name so the source check can read the name.
      env: (name: string) => {
        switch (name) {
          case 'HOME':
            return asText(process.env.HOME)
          default:
            return undefined
        }
      },
      isFile: (path: string) => {
        try {
          return statSync(path).isFile() === true
        } catch {
          return false
        }
      },
      isDir: (path: string) => {
        try {
          return statSync(path).isDirectory() === true
        } catch {
          return false
        }
      },
      real: (path: string) => {
        try {
          return asText(realpathSync(path))
        } catch {
          return undefined
        }
      },
      read: (path: string) => {
        try {
          return asText(readFileSync(path, 'utf8'))
        } catch {
          return undefined
        }
      },
      // Starts the one reader process. The launch plan builds argv for /usr/bin/env, whose first
      // argument is -i. Any other first argument means the argv did not come from the plan, so the
      // host starts nothing. -i also empties the environment, and the empty env {} below makes the
      // spawn carry no inherited variable even if env ignored its flag.
      start: (argv: string[], cwd: string, sink: ReaderSink) => {
        if (argv[0] !== '-i') return undefined
        try {
          const child = spawn('/usr/bin/env', argv, { env: {}, cwd, stdio: ['ignore', 'pipe', 'pipe'] })
          try {
            child.on('spawn', () => {
              sink.spawned()
            })
            child.on('exit', () => {
              sink.exited()
            })
            child.stdout.on('data', chunk => {
              try {
                sink.out(Array.from(chunk, asByte))
              } catch {
                sink.out([-1])
              }
            })
            child.stderr.on('data', chunk => {
              try {
                sink.err(Array.from(chunk, asByte))
              } catch {
                sink.err([-1])
              }
            })
            child.on('error', () => {
              sink.failed()
            })
            child.on('close', code => {
              sink.closed(asNumber(code))
            })
            return {
              term: () => {
                try {
                  child.kill('SIGTERM')
                } catch {}
              },
              hard: () => {
                try {
                  child.kill('SIGKILL')
                } catch {}
              },
            }
          } catch {
            try {
              child.kill('SIGKILL')
            } catch {}
            return 'untracked'
          }
        } catch {
          return undefined
        }
      },
      // OMP's managed timers contain a throw and are cleared on session shutdown. They are also
      // the host's own recommendation for extension background work.
      after: (ms: number, fn: () => void) => {
        const timer = ctx.setTimeout(() => {
          fn()
        }, ms)
        return () => {
          try {
            ctx.clearTimer(timer)
          } catch {}
        }
      },
      every: (ms: number, fn: () => void) => {
        const timer = ctx.setInterval(() => {
          fn()
        }, ms)
        return () => {
          try {
            ctx.clearTimer(timer)
          } catch {}
        }
      },
      leaseRead: () => {
        try {
          return leaseCell().running ? 'held' : 'free'
        } catch {
          return 'unknown'
        }
      },
      leaseWrite: (b: boolean) => {
        try {
          leaseCell().running = b === true
          return true
        } catch {
          return false
        }
      },
      writeKept: (v: KeptEnvelope | null) => {
        state.current = v
        paint()
      },
      openPanel: () => {
        panel = true
        paint()
        return true
      },
      panelOpen: () => panel,
      closePanel: () => {
        panel = false
        try {
          ctx.ui.setWidget(PANEL, undefined)
        } catch {
          // The panel state is closed even when the host refused the removal.
        }
        return true
      },
      toast: (code: string) => {
        try {
          ctx.ui.notify(code, 'error')
        } catch {}
      },
    }

    const scheduler = createScheduler(host)

    return {
      host,
      scheduler,
      paint,
      docsDir: () => state.docsDir,
      stop: () => {
        scheduler.stop()
        panel = false
        try {
          ctx.ui.setWidget(BAND, undefined)
        } catch {}
        try {
          ctx.ui.setWidget(PANEL, undefined)
        } catch {}
        try {
          ctx.ui.setStatus(STATUS, undefined)
        } catch {}
      },
    }
  }

  const repaintMain = () => {
    try {
      liveStore().mainPaint?.()
    } catch {}
  }

  const boot = (ctx: Ctx) => {
    if (ctx.agent?.kind === 'sub') {
      ensureSubagentFromCtx(ctx)
      repaintMain()
      return
    }
    // A start or a switch replaces the session this factory served before; its timers and reader
    // must not keep running beside the new one.
    for (const old of sessions.values()) old.stop()
    sessions.clear()
    const key = keyOf(ctx)
    const session = makeSession(ctx)
    sessions.set(key, session)
    liveStore().mainPaint = () => {
      session.paint()
    }
    session.scheduler.start()
    session.paint()
  }

  const sessionFor = (ctx: Ctx): Session | undefined => sessions.get(keyOf(ctx))

  const attemptVoid = (register: () => unknown): (() => void) | undefined => {
    try {
      register()
      return () => {}
    } catch {
      return undefined
    }
  }

  // The flag channel is on ExtensionAPI, and its methods retain their binding when destructured.
  // Both are optional at runtime so an older host that predates them still draws the band.
  const registerFlag = pi.registerFlag
  const getFlag = pi.getFlag
  if (typeof registerFlag === 'function') {
    try {
      registerFlag.call(pi, 'cruxOmpBand', {
        type: 'string',
        default: 'true',
        description: 'Show the Crux run band above the editor; set false to hide it.',
      })
    } catch {
      // A host that cannot register the flag keeps the band.
    }
  }

  pi.setLabel('Crux dashboard')

  const registrations = [
    () =>
      attemptVoid(() =>
        pi.on('session_start', async (_event, ctx) => {
          boot(ctx as unknown as Ctx)
        }),
      ),
    () =>
      attemptVoid(() =>
        pi.on('session_switch', async (_event, ctx) => {
          boot(ctx as unknown as Ctx)
        }),
      ),
    () =>
      attemptVoid(() =>
        pi.on('session_shutdown', async (_event, ctx) => {
          const context = ctx as unknown as Ctx
          if (context.agent?.kind === 'sub') {
            const id = typeof context.agent.id === 'string' ? context.agent.id : ''
            const node = liveStore().subagents.get(id)
            if (node !== undefined) {
              if (node.status === 'running' || node.status === 'blocked') node.status = 'done'
              node.activeTool = null
              node.toolTarget = null
              node.updatedAtMs = Date.now()
            }
            repaintMain()
            return
          }
          const key = keyOf(context)
          sessions.get(key)?.stop()
          sessions.delete(key)
        }),
      ),
    () =>
      attemptVoid(() =>
        pi.on('before_subagent_spawn', async (event, ctx) => {
          const context = ctx as unknown as Ctx
          const e = (event ?? {}) as Record<string, unknown>
          const agentRole = typeof e.agent === 'string' && e.agent !== '' ? e.agent : 'task'
          const spawnId = typeof e.spawnKey === 'string' && e.spawnKey !== '' ? e.spawnKey : agentRole
          const parentId = context.agent?.kind === 'sub' && typeof context.agent.id === 'string' && context.agent.id !== '' ? context.agent.id : null
          const depth = context.agent?.kind === 'sub' && typeof context.agent.depth === 'number' ? context.agent.depth + 1 : 1
          const store = liveStore()
          const now = Date.now()
          const existing = store.subagents.get(spawnId)
          if (existing !== undefined) {
            existing.role = agentRole
            existing.status = 'running'
            existing.updatedAtMs = now
          } else {
            store.subagents.set(spawnId, {
              id: spawnId,
              name: spawnId,
              role: agentRole,
              parentId,
              depth,
              status: 'running',
              task: '',
              activeTool: null,
              toolTarget: null,
              startedAtMs: now,
              updatedAtMs: now,
              model: typeof e.modelRole === 'string' ? e.modelRole : null,
              blockerReason: null,
            })
          }
          repaintMain()
        }),
      ),
    () =>
      attemptVoid(() =>
        pi.on('tool_execution_start', async (event, ctx) => {
          const context = ctx as unknown as Ctx
          const e = (event ?? {}) as Record<string, unknown>
          const toolName = typeof e.toolName === 'string' ? e.toolName : ''
          if (toolName === '') return
          const callId = typeof e.toolCallId === 'string' && e.toolCallId !== '' ? e.toolCallId : `${toolName}:${Date.now()}`
          const detail = summarizeToolDetail(toolName, e.args ?? e.input)
          const isSub = context.agent?.kind === 'sub'
          const agentId = isSub && typeof context.agent?.id === 'string' && context.agent.id !== '' ? context.agent.id : 'main'
          const agentName = isSub && typeof context.agent?.name === 'string' && context.agent.name !== '' ? context.agent.name : agentId
          const store = liveStore()
          const now = Date.now()
          store.activeTools.set(`${agentId}:${callId}`, {
            callId,
            agentId,
            agentName,
            toolName,
            detail,
            startedAtMs: now,
          })
          if (isSub) {
            ensureSubagentFromCtx(context)
            const node = store.subagents.get(agentId)
            if (node !== undefined) {
              node.status = 'running'
              node.activeTool = toolName
              node.toolTarget = detail || null
              node.updatedAtMs = now
            }
          }
          if (toolName.toLowerCase() === 'task') {
            updateFromTaskToolCall(e, context, 'start')
          }
          repaintMain()
        }),
      ),
    () =>
      attemptVoid(() =>
        pi.on('tool_execution_update', async (event, ctx) => {
          const context = ctx as unknown as Ctx
          const e = (event ?? {}) as Record<string, unknown>
          const toolName = typeof e.toolName === 'string' ? e.toolName : ''
          if (toolName.toLowerCase() === 'task') {
            updateFromTaskToolCall(e, context, 'update')
            repaintMain()
          }
        }),
      ),
    () =>
      attemptVoid(() =>
        pi.on('tool_execution_end', async (event, ctx) => {
          const context = ctx as unknown as Ctx
          const e = (event ?? {}) as Record<string, unknown>
          const toolName = typeof e.toolName === 'string' ? e.toolName : ''
          const callId = typeof e.toolCallId === 'string' ? e.toolCallId : ''
          const isSub = context.agent?.kind === 'sub'
          const agentId = isSub && typeof context.agent?.id === 'string' && context.agent.id !== '' ? context.agent.id : 'main'
          const store = liveStore()
          if (callId !== '') {
            store.activeTools.delete(`${agentId}:${callId}`)
          } else {
            for (const [k, v] of store.activeTools.entries()) {
              if (v.agentId === agentId && v.toolName === toolName) store.activeTools.delete(k)
            }
          }
          if (isSub) {
            const node = store.subagents.get(agentId)
            if (node !== undefined) {
              node.activeTool = null
              node.toolTarget = null
              node.updatedAtMs = Date.now()
            }
          }
          if (toolName.toLowerCase() === 'task') {
            updateFromTaskToolCall(e, context, 'end')
          }
          repaintMain()
        }),
      ),
    () =>
      attemptVoid(() =>
        pi.on('tool_result', async (event, ctx) => {
          const context = ctx as unknown as Ctx
          const e = event as { toolName?: unknown; input?: unknown }
          if (typeof e.toolName === 'string' && e.toolName.toLowerCase() === 'task') {
            updateFromTaskToolCall(event as Record<string, unknown>, context, 'end')
            repaintMain()
          }
          const session = sessionFor(context)
          if (session === undefined) return
          if (!touchesRunFile(e.toolName, e.input, session.docsDir())) return
          session.scheduler.request('event')
          session.paint()
        }),
      ),
    () =>
      attemptVoid(() =>
        pi.on('input', async (event, ctx) => {
          if (!asksForTheRun(event)) return
          const session = sessionFor(ctx as unknown as Ctx)
          if (session === undefined) return
          session.scheduler.request('event')
          session.paint()
        }),
      ),
    () =>
      attemptVoid(() =>
        pi.registerCommand('crux-dashboard', {
          description: 'Toggle the crux run dashboard',
          handler: async (_args: string, ctx: Ctx) => {
            const session = sessionFor(ctx)
            if (session !== undefined) runCommand(session.host, session.scheduler)
          },
        }),
      ),
  ]

  return registerAll(registrations, undefined, () => {
    for (const session of sessions.values()) session.stop()
    sessions.clear()
  })
}
