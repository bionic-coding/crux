// The registration sequence and the cleanup. The boundary file passes one registration
// per host call it makes, each of which catches its own failure and returns either a
// function that releases what it registered or undefined.

export type Registration = () => (() => void) | undefined

// Calls each registration in order and stops at the first that returns undefined (or
// throws). It then releases every registration it acquired, in reverse order, and calls
// no later registration and not start. When all succeed and start is given, it calls
// start last. It returns the cleanup: stop, then each acquired release in reverse order,
// each in its own try and at most once. A second call of the cleanup does nothing more.
// registerAll itself throws nothing: every call it makes is in a try.
export function registerAll(registrations: Registration[], start: (() => void) | undefined, stop: () => void): () => void {
  const acquired: (() => void)[] = []
  let failed = false
  for (const register of registrations) {
    let undo: (() => void) | undefined
    try {
      undo = register()
    } catch {
      undo = undefined
    }
    if (undo === undefined) {
      failed = true
      break
    }
    acquired.push(undo)
  }

  // Each acquired release leaves the list as it is called, so none runs twice.
  const releaseAll = () => {
    for (let i = acquired.length - 1; i >= 0; i--) {
      const undo = acquired[i]
      acquired.length = i
      if (undo === undefined) continue
      try {
        undo()
      } catch {
        // The release that failed cannot be retried; the others still run.
      }
    }
  }

  if (failed) {
    releaseAll()
  } else if (start !== undefined) {
    try {
      start()
    } catch {
      // A scheduler that did not start draws nothing and reads nothing more.
    }
  }

  let done = false
  return () => {
    if (done) return
    done = true
    try {
      stop()
    } catch {
      // The releases below still run.
    }
    releaseAll()
  }
}
