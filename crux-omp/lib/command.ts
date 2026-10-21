// The /crux-dashboard command toggles the panel. When the host reports the panel open, the command
// closes it and does nothing else. Otherwise it asks for a refresh, then opens the panel. When the
// host does not open it, the toast carries the status code alone.
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
