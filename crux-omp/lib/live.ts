// Live OMP subagent and activity tracking for crux-omp.
// Builds a real-time parent -> child subagent tree across sessions, detects active tool calls and
// task batches, and flags potentially blocked or long-running agents without mutating host state.
import type { Block, Line, Span } from '../../crux-mods/hooks/lib/draw.ts'
import { BAR_OFF, BAR_ON, LOOP_GLYPH, STATE_GLYPHS, TRACK_SEP, drawn, fitLine, joined, lineCells } from '../../crux-mods/hooks/lib/draw.ts'
import type { CycleView } from '../../crux-mods/hooks/lib/view.ts'
import { cycleTimeText } from '../../crux-mods/hooks/lib/view.ts'
import { cells } from '../../crux-mods/hooks/lib/width.ts'

export type SubagentStatus = 'running' | 'idle' | 'blocked' | 'done' | 'error'

export type SubagentNode = {
  id: string
  name: string
  role: string
  parentId: string | null
  depth: number
  status: SubagentStatus
  task: string
  activeTool: string | null
  toolTarget: string | null
  startedAtMs: number
  updatedAtMs: number
  model: string | null
  blockerReason: string | null
}

export type ActiveToolEntry = {
  callId: string
  agentId: string
  agentName: string
  toolName: string
  detail: string
  startedAtMs: number
}

export type AsyncJobInfo = {
  id: string
  type: string
  state: string
  label?: string
}

export type QueueItemView = {
  id: string
  title: string
  suggestedType: string
  state: string
  dependsOn: string[]
  cycle: string | null
  holdReason: string | null
  authorized: boolean
}

export type CycleQueueView = {
  items: QueueItemView[]
  authKind: string | null
  remaining: string[]
}

export type LiveRuntimeSnapshot = {
  nowMs: number
  mainStreaming: boolean
  activeTools: ActiveToolEntry[]
  subagents: SubagentNode[]
  asyncJobs: AsyncJobInfo[]
  queue?: CycleQueueView | null
}

const span = (text: string, style: Omit<Span, 'text'> = {}): Span => ({ text, ...style })

const STALE_BLOCKED_MS = 90_000
const LONG_TOOL_MS = 45_000

const STATUS_GLYPH: Readonly<Record<SubagentStatus, string>> = {
  running: STATE_GLYPHS.running ?? '\u{25B8}',
  idle: STATE_GLYPHS.pending ?? '\u{25CC}',
  blocked: '!',
  done: STATE_GLYPHS.done ?? '\u{2713}',
  error: STATE_GLYPHS.blocked ?? '\u{2717}',
}

const STATUS_COLOR: Readonly<Record<SubagentStatus, Span['color']>> = {
  running: 'claude',
  idle: 'subtle',
  blocked: 'warning',
  done: 'success',
  error: 'error',
}

export function formatDurationMs(ms: number): string {
  const secs = Math.max(0, Math.floor(ms / 1000))
  if (secs < 60) return `${secs}s`
  const mins = Math.floor(secs / 60)
  const remSecs = secs % 60
  if (mins < 60) return remSecs > 0 ? `${mins}m${String(remSecs).padStart(2, '0')}s` : `${mins}m`
  const hrs = Math.floor(mins / 60)
  const remMins = mins % 60
  return `${hrs}h${String(remMins).padStart(2, '0')}m`
}

export function effectiveSubagentStatus(node: SubagentNode, allNodes: readonly SubagentNode[], nowMs: number): { status: SubagentStatus; reason: string | null } {
  if (node.status === 'error' || node.status === 'done') {
    return { status: node.status, reason: node.blockerReason }
  }
  if (node.blockerReason !== null) {
    return { status: 'blocked', reason: node.blockerReason }
  }
  const activeChildren = allNodes.filter(child => child.parentId === node.id && (child.status === 'running' || child.status === 'blocked'))
  if (node.activeTool === 'wait' && activeChildren.length === 0) {
    return { status: 'blocked', reason: 'waiting with no running child subagent' }
  }
  if (node.activeTool === 'ask') {
    return { status: 'blocked', reason: 'awaiting user input (ask)' }
  }
  const idleAge = nowMs - node.updatedAtMs
  if (node.status === 'running' && node.activeTool === null && activeChildren.length === 0 && idleAge >= STALE_BLOCKED_MS) {
    return { status: 'blocked', reason: `no tool activity for ${formatDurationMs(idleAge)}` }
  }
  if (node.status === 'running' && node.activeTool !== null && idleAge >= LONG_TOOL_MS && activeChildren.length === 0) {
    return { status: 'running', reason: `${node.activeTool} running ${formatDurationMs(idleAge)}` }
  }
  return { status: node.status, reason: null }
}

// Orders subagents into a depth-first parent -> child hierarchy with tree branch connectors.
export type TreeRow = {
  node: SubagentNode
  prefix: string
  effectiveStatus: SubagentStatus
  reason: string | null
}

export function buildSubagentTree(nodes: readonly SubagentNode[], nowMs: number): TreeRow[] {
  if (nodes.length === 0) return []
  const byId = new Set(nodes.map(n => n.id))
  const childrenOf = new Map<string | null, SubagentNode[]>()
  for (const n of nodes) {
    const parentKey = n.parentId !== null && byId.has(n.parentId) ? n.parentId : null
    const list = childrenOf.get(parentKey) ?? []
    list.push(n)
    childrenOf.set(parentKey, list)
  }
  const out: TreeRow[] = []
  const visited = new Set<string>()

  const walk = (parentKey: string | null, ancestorPrefixes: string[]) => {
    const children = childrenOf.get(parentKey) ?? []
    children.forEach((child, idx) => {
      if (visited.has(child.id)) return
      visited.add(child.id)
      const isLast = idx === children.length - 1
      const branch = ancestorPrefixes.length === 0 ? '' : ancestorPrefixes.join('') + (isLast ? '\u{2514}\u{2500} ' : '\u{251C}\u{2500} ')
      const eff = effectiveSubagentStatus(child, nodes, nowMs)
      out.push({
        node: child,
        prefix: branch,
        effectiveStatus: eff.status,
        reason: eff.reason,
      })
      const nextAncestors = ancestorPrefixes.length === 0 ? ['  '] : [...ancestorPrefixes, isLast ? '   ' : '\u{2502}  ']
      walk(child.id, nextAncestors)
    })
  }

  walk(null, [])
  for (const n of nodes) {
    if (!visited.has(n.id)) {
      const eff = effectiveSubagentStatus(n, nodes, nowMs)
      out.push({ node: n, prefix: '', effectiveStatus: eff.status, reason: eff.reason })
    }
  }
  return out
}

// --- Cycle categorization & focused rendering ----------------------------------------------------

const PHASE_COLORS: Readonly<Record<string, Span['color']>> = {
  plan: 'merged',
  build: 'suggestion',
  test: 'permission',
  review: 'text',
  release: 'text',
  reflect: 'inactive',
}

const CYCLE_BADGE: Readonly<Record<string, { glyph: string; label: string; color: Span['color'] }>> = {
  active: { glyph: STATE_GLYPHS.running ?? '\u{25B8}', label: 'CURRENT', color: 'claude' },
  paused: { glyph: STATE_GLYPHS.skipped ?? '\u{2298}', label: 'PAUSED', color: 'warning' },
  completed: { glyph: STATE_GLYPHS.done ?? '\u{2713}', label: 'COMPLETED', color: 'success' },
  abandoned: { glyph: STATE_GLYPHS.blocked ?? '\u{2717}', label: 'ABANDONED', color: 'error' },
}

function phaseTrackLine(c: CycleView, width: number): Line {
  const curIdx = c.phases.indexOf(c.phase)
  const cellsList: Line[] = c.phases.map((p, idx) => {
    if (c.status === 'completed' || idx < curIdx) {
      return [span(STATE_GLYPHS.done ?? '\u{2713}', { color: 'success' }), span(` ${p}`, { color: 'success' })]
    }
    if (idx > curIdx) {
      return [span(STATE_GLYPHS.pending ?? '\u{25CC}', { dim: true }), span(` ${p}`, { dim: true })]
    }
    const badge = CYCLE_BADGE[c.status] ?? { glyph: '?', color: 'warning' as const }
    return [span(badge.glyph, { color: badge.color, bold: true }), span(` ${p}`, { color: badge.color, bold: true })]
  })
  const full = joined(cellsList, ` ${TRACK_SEP} `)
  return fitLine(full, width)
}

function progressBar(done: number, total: number, width: number): Line {
  if (total <= 0) return []
  const pct = Math.round((100 * done) / total)
  const barW = Math.min(18, Math.max(6, Math.floor(width / 5)))
  const filled = Math.max(0, Math.min(barW, Math.round((pct * barW) / 100)))
  return [
    span(BAR_ON.repeat(filled), { color: pct === 100 ? 'success' : 'claude' }),
    span(BAR_OFF.repeat(barW - filled), { dim: true }),
    span(` ${done}/${total} tasks (${pct}%)`, { dim: true }),
  ]
}

export function buildLiveActivitySection(live: LiveRuntimeSnapshot, innerWidth: number): Line[] {
  const lines: Line[] = []
  const tree = buildSubagentTree(live.subagents, live.nowMs)
  const runningSubagents = tree.filter(r => r.effectiveStatus === 'running')
  const blockedSubagents = tree.filter(r => r.effectiveStatus === 'blocked')

  // Header summary
  const summaryParts: Line[] = [[span('NOW RUNNING & SUBAGENT TREE', { bold: true, color: 'claude' })]]
  if (runningSubagents.length > 0) {
    summaryParts.push([span(`${runningSubagents.length} running`, { color: 'claude', bold: true })])
  }
  if (blockedSubagents.length > 0) {
    summaryParts.push([span(`${blockedSubagents.length} blocked/waiting`, { color: 'warning', bold: true })])
  } else if (tree.length > 0) {
    summaryParts.push([span('no agents blocked', { color: 'success' })])
  }
  lines.push(fitLine(joined(summaryParts, '  \u{00B7}  '), innerWidth))

  // Active tools in flight
  if (live.activeTools.length > 0) {
    for (const tool of live.activeTools.slice(0, 6)) {
      const elapsed = formatDurationMs(live.nowMs - tool.startedAtMs)
      const who = tool.agentId === 'main' ? 'main' : tool.agentName
      const detail = tool.detail ? ` ${drawn(tool.detail, Math.max(20, innerWidth - 28))}` : ''
      lines.push(
        fitLine(
          [
            span(STATE_GLYPHS.running ?? '\u{25B8}', { color: 'claude', bold: true }),
            span(` [${drawn(who, 18)}] `, { color: 'permission' }),
            span(drawn(tool.toolName, 16), { bold: true }),
            span(detail, { dim: true }),
            span(` (${elapsed})`, { dim: true }),
          ],
          innerWidth,
        ),
      )
    }
  } else if (runningSubagents.length === 0 && !live.mainStreaming) {
    lines.push(fitLine([span('\u{25CC} Idle \u{2014} no tools or subagents currently executing', { dim: true })], innerWidth))
  }

  // Subagent nesting tree
  if (tree.length > 0) {
    lines.push(fitLine([span('main (session)', { bold: true, dim: true })], innerWidth))
    for (const row of tree.slice(0, 16)) {
      const n = row.node
      const glyph = STATUS_GLYPH[row.effectiveStatus]
      const color = STATUS_COLOR[row.effectiveStatus]
      const elapsed = formatDurationMs(live.nowMs - n.startedAtMs)
      const shortName = n.parentId !== null && n.name.startsWith(`${n.parentId}.`) ? n.name.slice(n.parentId.length + 1) : n.name
      const roleLabel = n.role && n.role !== shortName ? `${shortName} (${n.role})` : shortName
      const toolInfo = n.activeTool !== null ? ` \u{2192} ${n.activeTool}${n.toolTarget ? ` ${drawn(n.toolTarget, 24)}` : ''}` : ''
      const reasonInfo = row.reason !== null ? ` [${row.reason}]` : ''
      const taskPreview = n.task ? ` \u{2014} ${drawn(n.task, Math.max(16, innerWidth - 42))}` : ''
      lines.push(
        fitLine(
          [
            span(row.prefix, { dim: true }),
            span(glyph, { color, bold: row.effectiveStatus === 'running' || row.effectiveStatus === 'blocked' }),
            span(` ${drawn(roleLabel, 32)}`, { bold: row.effectiveStatus === 'running', color: row.effectiveStatus === 'blocked' ? 'warning' : undefined }),
            span(` ${row.effectiveStatus}`, { color }),
            span(` (${elapsed})`, { dim: true }),
            span(toolInfo, { color: 'suggestion' }),
            span(reasonInfo, { color: row.effectiveStatus === 'blocked' ? 'warning' : 'subtle', bold: row.effectiveStatus === 'blocked' }),
            span(taskPreview, { dim: true }),
          ],
          innerWidth,
        ),
      )
    }
  }
  return lines
}

function buildActiveOrPausedCycleCard(c: CycleView, label: string, innerWidth: number, nowS: number | null): Line[] {
  const badge = CYCLE_BADGE[c.status] ?? { glyph: '?', label: c.status.toUpperCase(), color: 'warning' as const }
  const done = c.tasks.filter(t => t.status === 'done').length
  const timeText = cycleTimeText(c, nowS)
  const lines: Line[] = [
    fitLine(
      [
        span(`${badge.glyph} ${label}: `, { color: badge.color, bold: true }),
        span(`${c.id} `, { bold: true }),
        span(drawn(c.title), { bold: true }),
        // A listed release cycle has the one phase release and no pass limit to draw.
        span(c.type === 'release' && c.phases.join(',') === 'release'
          ? `  [${c.type}]`
          : `  [${c.type} \u{00B7} ${LOOP_GLYPH} pass ${c.pass}/${c.pass_limit}]`, { color: 'permission' }),
      ],
      innerWidth,
    ),
    fitLine(
      joined(
        [
          phaseTrackLine(c, Math.max(20, innerWidth - 36)),
          ...(timeText !== null ? [[span(timeText, { dim: true })]] : []),
        ],
        '   ',
      ),
      innerWidth,
    ),
  ]

  if (c.tasks.length > 0) {
    lines.push(fitLine(progressBar(done, c.tasks.length, innerWidth), innerWidth))
  }

  // Highlight blockers, waits, and returns prominently
  const waiting = [...new Set(c.waits)]
  if (waiting.length > 0) {
    lines.push(fitLine([span('! Awaiting approval: ', { color: 'warning', bold: true }), span(waiting.map(w => drawn(w)).join(', '), { color: 'warning' })], innerWidth))
  }
  if (c.blocker !== null) {
    lines.push(fitLine([span('! Blocked / Paused: ', { color: 'error', bold: true }), span(drawn(c.blocker), { color: 'error' })], innerWidth))
  }

  // Show active/blocked/pending tasks first; collapse completed tasks to keep focus on what's remaining
  const activeOrBlocked = c.tasks.filter(t => t.status === 'active' || t.status === 'blocked')
  const pendingTasks = c.tasks.filter(t => t.status === 'pending')
  const doneTasks = c.tasks.filter(t => t.status === 'done')

  for (const t of activeOrBlocked) {
    const isBlocked = t.status === 'blocked'
    const g = isBlocked ? (STATE_GLYPHS.blocked ?? '\u{2717}') : (STATE_GLYPHS.running ?? '\u{25B8}')
    lines.push(
      fitLine(
        [
          span(`  ${g} `, { color: isBlocked ? 'error' : 'claude', bold: true }),
          span(t.phase, { color: PHASE_COLORS[t.phase] ?? 'text', bold: true }),
          span(': '),
          span(drawn(t.description), { bold: true, color: isBlocked ? 'error' : undefined }),
        ],
        innerWidth,
      ),
    )
  }
  for (const t of pendingTasks.slice(0, 5)) {
    lines.push(
      fitLine(
        [
          span(`  ${STATE_GLYPHS.pending ?? '\u{25CC}'} `, { dim: true }),
          span(t.phase, { color: PHASE_COLORS[t.phase] ?? 'text' }),
          span(': '),
          span(drawn(t.description), { dim: true }),
        ],
        innerWidth,
      ),
    )
  }
  if (pendingTasks.length > 5) {
    lines.push(fitLine([span(`  \u{2026} +${pendingTasks.length - 5} more pending tasks`, { dim: true })], innerWidth))
  }
  if (doneTasks.length > 0 && activeOrBlocked.length === 0 && pendingTasks.length === 0) {
    for (const t of doneTasks.slice(-3)) {
      lines.push(
        fitLine(
          [
            span(`  ${STATE_GLYPHS.done ?? '\u{2713}'} `, { color: 'success' }),
            span(t.phase, { color: PHASE_COLORS[t.phase] ?? 'text' }),
            span(': '),
            span(drawn(t.description), { dim: true }),
          ],
          innerWidth,
        ),
      )
    }
  }
  const lastReturn = c.returns[c.returns.length - 1]
  if (lastReturn !== undefined) {
    lines.push(
      fitLine(
        [
          span(`  ${LOOP_GLYPH} pass ${lastReturn.pass} returned from ${lastReturn.phase}: ${drawn(lastReturn.reason)}`, { color: 'warning' }),
        ],
        innerWidth,
      ),
    )
  }
  return lines
}

function buildPreviousCyclesSummary(previous: readonly CycleView[], innerWidth: number, nowS: number | null): Line[] {
  const lines: Line[] = [
    fitLine([span(`PREVIOUS CYCLES (${previous.length} recent)`, { bold: true, dim: true })], innerWidth),
  ]
  for (const c of previous.slice(0, 4)) {
    const done = c.tasks.filter(t => t.status === 'done').length
    const badge = CYCLE_BADGE[c.status] ?? { glyph: '?', label: c.status, color: 'subtle' as const }
    const timeText = cycleTimeText(c, nowS) ?? ''
    const titleBudget = Math.max(18, innerWidth - 48)
    lines.push(
      fitLine(
        [
          span(badge.glyph, { color: badge.color }),
          span(` ${c.id} `, { bold: true }),
          span(drawn(c.title, titleBudget)),
          span(`  ${c.type}`, { color: 'permission' }),
          span(`  ${done}/${c.tasks.length} tasks`, { dim: true }),
          ...(timeText ? [span(`  ${timeText.replace(/^elapsed /, '')}`, { dim: true })] : []),
        ],
        innerWidth,
      ),
    )
    if (c === previous[0] && c.reflection) {
      lines.push(
        fitLine(
          [span('    Outcome: ', { dim: true }), span(drawn(c.reflection, Math.max(24, innerWidth - 14)), { color: 'success', dim: true })],
          innerWidth,
        ),
      )
    }
  }
  return lines
}

export function parseCycleQueueYaml(raw: string): CycleQueueView | null {
  if (!raw || !raw.includes('crux.cycle-queue')) return null
  const items: QueueItemView[] = []
  const authScope = new Set<string>()
  let authKind: string | null = null

  const authSection = raw.split(/\nauthorization:\s*/)[1]?.split(/\nauthorization_history:\s*/)[0] ?? ''
  if (authSection && !authSection.startsWith('null')) {
    const kindMatch = /^\s*kind:\s*['"]?([a-z0-9_-]+)['"]?/m.exec(authSection)
    if (kindMatch?.[1]) authKind = kindMatch[1]
    const scopeBlock = authSection.split(/\n\s*scope:\s*\n/)[1]?.split(/\n\s*[a-z_]+:/)[0] ?? ''
    for (const line of scopeBlock.split('\n')) {
      const m = /^\s*-\s*['"]?(Q-\d+)['"]?/.exec(line)
      if (m?.[1]) authScope.add(m[1])
    }
  }

  const itemsSection = raw.split(/\nitems:\s*\n/)[1]?.split(/\nauthorization:/)[0] ?? ''
  const rawItems = itemsSection.split(/^\s*-\s+id:\s*/m).slice(1)
  for (const chunk of rawItems) {
    const lines = chunk.split('\n')
    const id = (lines[0] ?? '').trim().replace(/^['"]|['"]$/g, '')
    if (!id.startsWith('Q-')) continue
    const field = (name: string): string | null => {
      const m = new RegExp(`^\\s*${name}:\\s*(.+)$`, 'm').exec(chunk)
      if (!m?.[1]) return null
      const v = m[1].trim().replace(/^['"]|['"]$/g, '')
      return v === 'null' || v === '' ? null : v
    }
    const dependsOn: string[] = []
    const depBlock = chunk.split(/^\s*depends_on:\s*$/m)[1]?.split(/^\s*[a-z_]+:/m)[0] ?? ''
    for (const dLine of depBlock.split('\n')) {
      const dm = /^\s*-\s*['"]?(Q-\d+)['"]?/.exec(dLine)
      if (dm?.[1]) dependsOn.push(dm[1])
    }
    items.push({
      id,
      title: field('title') ?? '',
      suggestedType: field('suggested_type') ?? 'dev',
      state: field('state') ?? 'pending',
      dependsOn,
      cycle: field('cycle'),
      holdReason: field('hold_reason'),
      authorized: authScope.has(id),
    })
  }

  if (items.length === 0 && authKind === null) return null
  const remaining = items.filter(i => i.authorized && (i.state === 'pending' || i.state === 'held')).map(i => i.id)
  return { items, authKind, remaining }
}

function buildCycleQueueCard(queue: CycleQueueView, cycles: readonly CycleView[], innerWidth: number): Line[] {
  const statusByCycle = new Map(cycles.map(c => [c.id, c.status]))
  const itemById = new Map(queue.items.map(i => [i.id, i]))
  const unstartedCount = queue.items.filter(i => i.state === 'pending' || i.state === 'held' || i.state === 'starting').length
  const authBadge = queue.authKind
    ? `auth: ${queue.authKind} (${queue.remaining.length > 0 ? queue.remaining.join(', ') : 'none remaining'})`
    : 'auth: none'
  const lines: Line[] = [
    fitLine(
      joined(
        [
          [span(`CYCLE QUEUE (${unstartedCount} queued / ${queue.items.length} total)`, { bold: true, color: 'permission' })],
          [span(authBadge, { color: queue.authKind ? 'success' : 'subtle', dim: !queue.authKind })],
        ],
        '  \u{00B7}  ',
      ),
      innerWidth,
    ),
  ]
  for (const item of queue.items.slice(0, 6)) {
    const st = item.state === 'started' && item.cycle ? (statusByCycle.get(item.cycle) ?? 'started') : item.state
    const glyph =
      st === 'completed'
        ? (STATE_GLYPHS.done ?? '\u{2713}')
        : st === 'active' || st === 'starting'
          ? (STATE_GLYPHS.running ?? '\u{25B8}')
          : st === 'held'
            ? (STATE_GLYPHS.skipped ?? '\u{2298}')
            : (STATE_GLYPHS.pending ?? '\u{25CC}')
    const color: Span['color'] =
      st === 'completed' ? 'success' : st === 'active' || st === 'starting' ? 'claude' : st === 'held' ? 'warning' : 'subtle'
    const deps =
      item.dependsOn.length > 0
        ? ` after ${item.dependsOn
            .map(d => {
              const dep = itemById.get(d)
              const depSt = dep === undefined ? '?' : dep.state === 'started' && dep.cycle ? (statusByCycle.get(dep.cycle) ?? 'started') : dep.state
              return `${d} (${depSt})`
            })
            .join(', ')}`
        : ''
    const cycLink = item.cycle ? ` \u{2192} ${item.cycle}` : ''
    const authMark = item.authorized ? ' [authorized]' : ''
    const holdMark = item.holdReason ? ` [held: ${drawn(item.holdReason, 24)}]` : ''
    lines.push(
      fitLine(
        [
          span(glyph, { color, bold: st === 'active' || st === 'starting' }),
          span(` ${item.id} `, { bold: true }),
          span(drawn(item.title, Math.max(20, innerWidth - 44))),
          span(`  [${item.suggestedType} \u{00B7} ${st}]`, { color: 'permission' }),
          ...(deps ? [span(deps, { dim: true })] : []),
          ...(cycLink ? [span(cycLink, { color: 'claude' })] : []),
          ...(authMark ? [span(authMark, { color: 'success' })] : []),
          ...(holdMark ? [span(holdMark, { color: 'warning' })] : []),
        ],
        innerWidth,
      ),
    )
  }
  return lines
}

export function buildOmpCyclesPane(cycles: readonly CycleView[], nowS: number | null, live: LiveRuntimeSnapshot | undefined, width: number): Block {
  const bordered = width >= 36
  const innerWidth = bordered ? width - 4 : width
  const boxOf = (lines: Line[], borderColor: Span['color'] = 'subtle'): Block => ({
    kind: 'box',
    direction: 'column',
    width,
    border: bordered ? (borderColor ?? 'subtle') : null,
    gap: 0,
    children: lines.map(line => ({ kind: 'line' as const, line: fitLine(line, innerWidth) })),
  })

  const blocks: Block[] = []

  // 1. Live Running & Subagent Nesting section
  if (live !== undefined) {
    blocks.push(boxOf(buildLiveActivitySection(live, innerWidth), 'claude'))
  }

  // 2. Partition cycles into Current (active), Paused (paused/waiting), and Previous (completed/abandoned)
  const activeCycles = cycles.filter(c => c.status === 'active')
  const pausedCycles = cycles.filter(c => c.status === 'paused' || (c.status === 'active' && (c.blocker !== null || c.waits.length > 0)))
  const pureActive = activeCycles.filter(c => !pausedCycles.includes(c))
  const previousCycles = cycles.filter(c => c.status === 'completed' || c.status === 'abandoned')

  if (pureActive.length > 0) {
    for (const c of pureActive.slice(0, 2)) {
      blocks.push(boxOf(buildActiveOrPausedCycleCard(c, 'CURRENT CYCLE', innerWidth, nowS), 'claude'))
    }
  } else if (pausedCycles.length === 0) {
    // No active or paused cycle: distinguish initial reader load (nowS === null) from empty active set
    const latest = previousCycles[0]
    const msg: Line[] =
      nowS === null && cycles.length === 0
        ? [
            fitLine(
              [
                span('\u{25B8} CYCLES: ', { bold: true, color: 'claude' }),
                span('Reading project cycles from bionic/cycles/\u{2026}', { dim: true }),
              ],
              innerWidth,
            ),
          ]
        : [
            fitLine(
              [
                span('\u{25CC} CURRENT CYCLE: ', { bold: true, color: 'subtle' }),
                span('No active cycle in progress', { dim: true }),
                ...(latest !== undefined ? [span(`  (last completed: ${latest.id} \u{2014} ${drawn(latest.title, Math.max(16, innerWidth - 48))})`, { dim: true })] : []),
              ],
              innerWidth,
            ),
          ]
    blocks.push(boxOf(msg, 'subtle'))
  }

  // 3. Paused / Blocked cycles
  for (const c of pausedCycles.slice(0, 2)) {
    blocks.push(boxOf(buildActiveOrPausedCycleCard(c, 'PAUSED / WAITING CYCLE', innerWidth, nowS), 'warning'))
  }

  // 4. Cycle Queue (when bionic/queue/cycles.yaml has queued items)
  if (live?.queue !== undefined && live.queue !== null && live.queue.items.length > 0) {
    blocks.push(boxOf(buildCycleQueueCard(live.queue, cycles, innerWidth), 'permission'))
  }

  // 5. Compact Previous Cycles Digest
  if (previousCycles.length > 0) {
    blocks.push(boxOf(buildPreviousCyclesSummary(previousCycles, innerWidth, nowS), 'subtle'))
  }
  return {
    kind: 'box',
    direction: 'column',
    width,
    border: null,
    gap: 0,
    children: blocks,
  }
}

export function buildOmpBandLine(cycles: readonly CycleView[], nowS: number | null, live: LiveRuntimeSnapshot | undefined, width: number): Line | null {
  const parts: Line[] = []
  const active = cycles.find(c => c.status === 'active')
  const paused = cycles.find(c => c.status === 'paused')
  const latest = active ?? paused ?? cycles[0]

  if (latest !== undefined) {
    const badge = CYCLE_BADGE[latest.status] ?? { glyph: '?', label: latest.status, color: 'subtle' as const }
    const done = latest.tasks.filter(t => t.status === 'done').length
    const activeTask = latest.tasks.find(t => t.status === 'active')
    parts.push([
      span(badge.glyph, { color: badge.color, bold: true }),
      span(` ${latest.id}`, { bold: true }),
      span(` ${latest.type}`, { color: 'permission' }),
      span(` \u{00B7} ${latest.phase}`, { color: PHASE_COLORS[latest.phase] ?? 'text', bold: latest.status === 'active' }),
      span(` (${done}/${latest.tasks.length})`, { dim: true }),
    ])
    if (latest.blocker !== null) {
      parts.push([span(`! paused: ${drawn(latest.blocker, 28)}`, { color: 'warning', bold: true })])
    } else if (latest.waits.length > 0) {
      parts.push([span(`! awaiting: ${drawn(latest.waits[0]!, 24)}`, { color: 'warning', bold: true })])
    } else if (activeTask !== undefined) {
      parts.push([span(`\u{25B8} ${drawn(activeTask.description, 32)}`, { color: 'claude' })])
    }
  }

  if (live !== undefined) {
    const tree = buildSubagentTree(live.subagents, live.nowMs)
    const running = tree.filter(r => r.effectiveStatus === 'running')
    const blocked = tree.filter(r => r.effectiveStatus === 'blocked')
    if (blocked.length > 0) {
      const names = blocked.slice(0, 2).map(b => b.node.name).join(', ')
      parts.push([span(`! ${blocked.length} blocked (${drawn(names, 24)})`, { color: 'warning', bold: true })])
    }
    if (running.length > 0) {
      const names = running.slice(0, 2).map(r => (r.node.depth > 1 ? `${r.node.name}[d${r.node.depth}]` : r.node.name)).join(', ')
      parts.push([span(`\u{25B8} ${running.length} subagent${running.length === 1 ? '' : 's'}: ${drawn(names, 28)}`, { color: 'claude', bold: true })])
    } else if (live.activeTools.length > 0) {
      const topTool = live.activeTools[0]!
      parts.push([span(`\u{25B8} ${drawn(topTool.toolName, 14)}${topTool.detail ? ` ${drawn(topTool.detail, 20)}` : ''}`, { color: 'suggestion' })])
    }
  }

  if (parts.length === 0) return null
  return fitLine(joined(parts, '  \u{2502}  '), Math.max(20, cells('x') * width))
}
