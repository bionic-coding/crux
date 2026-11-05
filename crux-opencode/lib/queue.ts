import { applyQueueAction, queueControl, queueExpanded } from '../../crux-mods/hooks/lib/queue.ts'
import type { QueueAction as CoreQueueAction } from '../../crux-mods/hooks/lib/queue.ts'
import type { Parsed } from '../../crux-mods/hooks/lib/view.ts'
import type { Host } from './host.ts'
export type QueueAction = CoreQueueAction

export function expandedQueue(host: Host): boolean {
  try {
    return queueExpanded(host.queueRead(), host.directory())
  } catch {
    return false
  }
}

// Clicks belong to their drawn panel/root. Keyboard commands additionally require live focus.
// A refusal returns exactly false so OpenCode passes an unhandled key through to the prompt.
export function changeQueue(host: Host, parsed: Parsed | null, action: QueueAction, renderedRoot: string | undefined, keyboard = false): boolean {
  try {
    if (host.panelOpen() !== true || (keyboard && host.panelFocused() !== true)) return false
    const root = host.directory()
    if (root !== renderedRoot) return false
    const next = applyQueueAction(parsed, host.queueRead(), root, action)
    return next !== null && host.queueWrite(next) === true
  } catch {
    return false
  }
}

export function toggleQueue(host: Host, parsed: Parsed | null): boolean {
  try {
    if (parsed === null || !parsed.ok) return false
    const root = host.directory()
    const control = queueControl(parsed.view.queue, queueExpanded(host.queueRead(), root))
    return control !== null && changeQueue(host, parsed, control.action, root, true)
  } catch {
    return false
  }
}

// The actual render callback observes only its own pointer button. Disposal revokes it.
export function queueClick(host: Host, read: () => Parsed | null, root: string | undefined, active: () => boolean): (action: QueueAction | undefined, button: unknown) => boolean {
  return (action, button) => {
    try {
      return action !== undefined && button === 0 && active() === true && changeQueue(host, read(), action, root)
    } catch {
      return false
    }
  }
}
