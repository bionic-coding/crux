// The session-state contract of crux-mods. Claude Code requires this file to be self-contained, so it
// has no import.

// The last reader result: the reader's standard output once it was checked, or the status code the
// refresh ended with. It holds only checked reader output or a closed status code, never an event
// payload.
export type Kept = { ok: true; stdout: string } | { ok: false; code: string }

declare module 'claude-code' {
  interface PluginState {
    'crux-mods': {
      current: Shaped<Kept | null>
    }
  }
}
