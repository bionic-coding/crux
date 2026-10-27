// The one effect of the page-turn commands: move the stored page of the `cycles:` list by one.
//
// The host passes a key to the focused prompt only when a command's run returns exactly false, and
// consumes the key on true, on undefined and on a throw. So turnPage returns the literal false on
// every declining path, never undefined, and returns true only when it moved (or held) the page.
// It declines unless the panel is open, the panel has focus, the view has more than one page and the
// write succeeds. It never throws: the whole body sits in one try.
//
// The page size and the clamp belong to the core. This file states no page size.
import { clampPage, olderPages } from '../../crux-mods/hooks/lib/draw.ts'
import type { Parsed } from '../../crux-mods/hooks/lib/view.ts'
import type { Host } from './host.ts'

export function turnPage(host: Host, parsed: Parsed | null, delta: number): boolean {
  try {
    if (host.panelOpen() !== true) return false
    if (host.panelFocused() !== true) return false
    if (parsed === null) return false
    const pages = olderPages(parsed)
    if (pages <= 1) return false
    // Bound the stored index first, so a stale or hostile value never makes a key look dead.
    const next = clampPage(clampPage(host.pageRead(), pages) + delta, pages)
    return host.pageWrite(next) === true
  } catch {
    return false
  }
}
