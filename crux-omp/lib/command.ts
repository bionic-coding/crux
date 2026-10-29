// The /crux-dashboard command toggles the panel. When the host reports the panel open, the command
// closes it and does nothing else. Otherwise it asks for a refresh, then opens the panel. When the
// host does not open it, the toast carries the status code alone.
import { clampPage, olderPages } from '../../crux-mods/hooks/lib/draw.ts'
import type { Parsed } from '../../crux-mods/hooks/lib/view.ts'
import type { Host } from './host.ts'
import { PANEL_UNAVAILABLE } from './status.ts'
import type { Scheduler } from './refresh.ts'

export function runCommand(host: Host, scheduler: Scheduler): void {
  let open = false
  try {
    open = host.panelOpen() === true
  } catch {
    // A panel state the host cannot report counts as closed.
  }
  if (open) {
    try {
      host.closePanel()
    } catch {
      // A command that cannot close the panel has nothing more to do.
    }
    return
  }
  try {
    scheduler.request('command')
  } catch {
    // The panel opens whether or not the refresh was requested.
  }
  try {
    if (host.openPanel() === false) host.toast(PANEL_UNAVAILABLE)
  } catch {
    // A command that cannot open the panel has nothing more to do.
  }
}

// The page-turn arguments of /crux-dashboard: `next` is 1, `prev` is -1. Any other argument, the empty
// one included, is not a page turn and leaves the toggle as it was.
export function pageDelta(args: string): 1 | -1 | null {
  const a = typeof args === 'string' ? args.trim().toLowerCase() : ''
  return a === 'next' ? 1 : a === 'prev' ? -1 : null
}

// The page after a turn, bounded to the pages the view has. Never throws.
export function turnedPage(current: number, delta: number, parsed: Parsed | null): number {
  try {
    if (parsed === null) return 0
    const pages = olderPages(parsed)
    return clampPage(clampPage(current, pages) + delta, pages)
  } catch {
    return 0
  }
}
