// Presentation only. A retained action names the queue it was drawn for and the desired state,
// so a repeated click is idempotent and an action from an older reader snapshot is declined.
import type { Parsed, QueueItemView, QueueView } from './view.ts'

export const QUEUE_COLLAPSED_ROWS = 6
export type QueueExpansion = { root: string; expanded: boolean }
export type QueueAction = { kind: 'queue'; basis: string; expanded: boolean }

export const upcomingItems = (q: QueueView & { ok: true }): QueueItemView[] => q.items.filter(i => i.state !== 'started')

export function queueControl(q: QueueView | null | undefined, expanded: boolean): { label: string; action: QueueAction } | null {
  if (q === null || q === undefined || !q.ok) return null
  const upcoming = upcomingItems(q)
  if (upcoming.length <= QUEUE_COLLAPSED_ROWS) return null
  return {
    label: expanded ? 'Show less' : `+${upcoming.length - QUEUE_COLLAPSED_ROWS} more`,
    action: { kind: 'queue', basis: JSON.stringify(upcoming.map(i => [i.id, i.state])), expanded: !expanded },
  }
}

export function queueExpanded(state: QueueExpansion | null | undefined, root: string | undefined): boolean {
  return typeof root === 'string' && root !== '' && state?.root === root && state.expanded === true
}

export function applyQueueAction(parsed: Parsed | null, state: QueueExpansion | null | undefined, root: string | undefined, action: QueueAction): QueueExpansion | null {
  if (typeof root !== 'string' || root === '' || parsed === null || !parsed.ok || action?.kind !== 'queue') return null
  const current = queueControl(parsed.view.queue, queueExpanded(state, root))
  if (current === null || action.basis !== current.action.basis || action.expanded !== current.action.expanded) return null
  return { root, expanded: action.expanded }
}
