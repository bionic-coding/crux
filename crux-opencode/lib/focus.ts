// Which reader says whether crux's panel has focus. The panel component publishes a reader, a
// function that asks the host's live render input at each call; the page-turn commands call read().
// The slot holds the reader, never a copy of what it answered, so a panel that throws or is dropped
// without its cleanup cannot leave a stale "focused" behind.
//
// createFocusSlot holds no module-level state. Setup makes one slot and keeps it in its closure, so
// a reload's new setup gets a fresh slot that the old setup's cleanup cannot touch.

export type FocusSlot = {
  // Stores the reader and returns its release. The release empties the slot only while the slot
  // still holds that reader, so a remount that publishes before the old cleanup runs is not undone.
  publish: (reader: () => boolean) => () => void
  // Calls the stored reader. False when the slot is empty, the reader throws or it answers anything
  // but exactly true.
  read: () => boolean
  // Empties the slot, whatever it holds.
  clear: () => void
}

export function createFocusSlot(): FocusSlot {
  let current: (() => boolean) | undefined = undefined
  return {
    publish: reader => {
      current = reader
      return () => {
        if (current === reader) current = undefined
      }
    },
    read: () => {
      const reader = current
      if (reader === undefined) return false
      try {
        return reader() === true
      } catch {
        return false
      }
    },
    clear: () => {
      current = undefined
    },
  }
}
