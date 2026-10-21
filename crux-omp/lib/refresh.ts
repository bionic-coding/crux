// The refresh scheduler. It decides when the reader runs, runs at most one reader at a time,
// settles each run into the kept value, and backs off when the reader is slow. It reads no clock:
// timers schedule every step. A late timer only postpones the step it schedules, and the reader
// lease keeps two setups from starting two readers.
//
// States: new, holding, idle, running, stopping, cooling, and the terminal stopped.
// Flags: pendingExplicit, pendingTick, backedOff, drainQueued, and holdDone and freeDone, which
// record that the start hold and the free cool-down have each run out; holding ends when both are set.
import { isSlow } from '../../crux-mods/hooks/lib/launch.ts'
import { parseReader } from '../../crux-mods/hooks/lib/view.ts'
import type { Parsed } from '../../crux-mods/hooks/lib/view.ts'
import type { Host, KeptEnvelope, ReaderHandle } from './host.ts'
import { acquire, leaseFree, release } from './lease.ts'
import { planLaunch } from './plan.ts'
import { openSink, startReader } from './reader.ts'
import { READER_CANNOT_START, READER_OUTPUT_INVALID, READER_TIMEOUT } from './status.ts'
import type { Ended, RunSink, SinkHooks } from './reader.ts'

// The periodic reason is tick; the other three are explicit. tool_result and input requests use
// the event reason.
export type Reason = 'tick' | 'panel' | 'command' | 'event'

export type Scheduler = {
  start: () => void
  stop: () => void
  request: (reason: Reason) => void
}

// The periodic tick: one request for a reader run every 15 s while the scheduler runs.
export const INTERVAL_MS = 15000
// How long a new setup stays in holding. It only backs up the reader lease, which alone keeps a
// reload from starting a second reader, so no safety property depends on this value. The cost is
// that the first view waits this long.
export const HOLD_MS = 4100
// How often holding reads the lease, 4 times a second; the first read runs on a 0 ms timer.
export const POLL_MS = 250
// The floor between one run's close and the next start is 2 seconds; the 100 ms margin covers a
// timer that fires up to 1 ms early.
export const COOL_MS = 2100
// A reader run that has not closed after 10 s is sent term. A test pins this to the manifest's
// launch.timeout_ms.
export const TIMEOUT_MS = 10000
// After term, a process that has not closed within 2 s is sent the hard kill.
export const GRACE_MS = 2000

type State = 'new' | 'holding' | 'idle' | 'running' | 'stopping' | 'cooling' | 'stopped'
type Cancel = () => void

// One reader run.
type Active = {
  sink: RunSink | undefined
  handle: ReaderHandle | undefined
  // This run holds the lease.
  acquired: boolean
  // A process was created but its listeners were not all attached: the lease stays held.
  untracked: boolean
  ended: boolean
  // term was sent.
  killed: boolean
  // A kill was asked before the handle came back.
  killWanted: boolean
  cancelTimeout: Cancel | undefined
  cancelGrace: Cancel | undefined
}

const clear = (cancel: Cancel | undefined) => {
  if (cancel === undefined) return
  try {
    cancel()
  } catch {
    // A timer that cannot be cancelled fires into a state that ignores it.
  }
}

const newActive = (): Active => ({
  sink: undefined,
  handle: undefined,
  acquired: false,
  untracked: false,
  ended: false,
  killed: false,
  killWanted: false,
  cancelTimeout: undefined,
  cancelGrace: undefined,
})

export function createScheduler(host: Host): Scheduler {
  let state: State = 'new'
  let pendingExplicit = false
  let pendingTick = false
  let backedOff = false
  let drainQueued = false
  let holdDone = false
  let freeDone = false
  let cancelInterval: Cancel | undefined
  let cancelHold: Cancel | undefined
  let cancelPoll: Cancel | undefined
  let cancelFree: Cancel | undefined
  let cancelCool: Cancel | undefined
  let cancelDrain: Cancel | undefined
  let current: Active | undefined

  // --- timers -------------------------------------------------------------------

  const startCool = () => {
    clear(cancelCool)
    cancelCool = host.after(COOL_MS, () => {
      try {
        if (state !== 'cooling') return
        state = 'idle'
        queueDrain()
      } catch {
        // The next request or tick queues a drain.
      }
    })
  }

  const queueDrain = () => {
    if (drainQueued) return
    drainQueued = true
    cancelDrain = host.after(0, () => {
      drainQueued = false
      try {
        drain()
      } catch {
        // drain recovers its own run.
      }
    })
  }

  const leaveHold = () => {
    if (state === 'holding' && holdDone && freeDone) {
      state = 'idle'
      queueDrain()
    }
  }

  // The first poll that reads free stops the polling. If the lease is already free on the first
  // check, leave the hold as soon as HOLD_MS elapses without adding an extra COOL_MS wait.
  let polledWhileBusy = false
  const poll = () => {
    if (state !== 'holding') return
    if (leaseFree(host)) {
      if (!polledWhileBusy) {
        freeDone = true
        leaveHold()
        return
      }
      cancelFree = host.after(COOL_MS, () => {
        try {
          freeDone = true
          leaveHold()
        } catch {
          // The hold ends at the next request.
        }
      })
      return
    }
    polledWhileBusy = true
    cancelPoll = host.after(POLL_MS, () => {
      try {
        poll()
      } catch {
        // Polling stops; the hold stays.
      }
    })
  }

  // --- the run ------------------------------------------------------------------

  const killRun = (act: Active) => {
    try {
      if (act.ended || act.killed) return
      if (act.handle === undefined || act.sink === undefined) {
        act.killWanted = true
        return
      }
      // After exit the process id may be reused: send no signal.
      if (act.sink.hasExited()) return
      act.killed = true
      if (state === 'running') state = 'stopping'
      act.handle.term()
      act.cancelGrace = host.after(GRACE_MS, () => {
        try {
          if (act.ended || act.sink === undefined || act.sink.hasExited() || act.handle === undefined) return
          act.handle.hard()
        } catch {
          // The process closes on its own time.
        }
      })
    } catch {
      // A kill that cannot be sent leaves the run to its timeout and close.
    }
  }

  // Each step of a run's end is in its own try, so a throw in one skips no later step and no
  // exception skips the release.
  const endRun = (act: Active, ended: Ended) => {
    if (act.ended) return
    act.ended = true
    clear(act.cancelTimeout)
    clear(act.cancelGrace)
    if (current === act) current = undefined
    const live = state !== 'stopped'

    let result: Parsed = { ok: false, code: READER_OUTPUT_INVALID }
    let envelope: KeptEnvelope = { ok: false, code: READER_OUTPUT_INVALID }
    try {
      if (ended.ok) {
        const parsed = parseReader(ended.stdout)
        envelope = parsed.ok ? { ok: true, stdout: ended.stdout } : { ok: false, code: parsed.code }
        result = parsed
      } else {
        envelope = { ok: false, code: ended.code }
        result = { ok: false, code: ended.code }
      }
    } catch {
      // The result stays reader-output-invalid.
    }

    if (live) {
      try {
        host.writeKept(envelope)
      } catch {
        // The next run writes again.
      }
    }
    if (act.acquired && !act.untracked) {
      try {
        release(host)
      } catch {
        // A lease left held stops later starts; it never allows an overlap.
      }
    }
    if (live) {
      try {
        if (!result.ok && isSlow(result.code)) {
          backedOff = true
          pendingTick = false
        } else {
          backedOff = false
        }
        state = 'cooling'
        startCool()
      } catch {
        // The next request or tick restarts the cycle.
      }
    }
  }

  // A run takes the lease when its hooks are made: the drain makes them after the lease branches,
  // so a run that never reached them never releases a lease it does not hold.
  const ownedHooks = (act: Active): SinkHooks => {
    act.acquired = true
    return {
      kill: () => {
        killRun(act)
      },
      end: ended => {
        endRun(act, ended)
      },
    }
  }

  const afterStart = (act: Active, sink: RunSink, handle: ReaderHandle | 'untracked' | undefined) => {
    act.sink = sink
    // The run already ended while the host was starting the process.
    if (act.ended) return
    if (handle === undefined) {
      endRun(act, { ok: false, code: READER_CANNOT_START })
      return
    }
    if (handle === 'untracked') {
      act.untracked = true
      endRun(act, { ok: false, code: READER_CANNOT_START })
      return
    }
    act.handle = handle
    current = act
    state = 'running'
    act.cancelTimeout = host.after(TIMEOUT_MS, () => {
      try {
        if (act.ended) return
        sink.record(READER_TIMEOUT)
        killRun(act)
      } catch {
        // The close ends the run.
      }
    })
    if (sink.status() !== undefined || act.killWanted) killRun(act)
  }

  const recover = (act: Active) => {
    try {
      if (act.ended) return
      if (act.handle !== undefined) {
        killRun(act)
        return
      }
      endRun(act, { ok: false, code: READER_CANNOT_START })
    } catch {
      // Nothing more can be done here.
    }
  }

  const drain = () => {
    if (state !== 'idle') return
    if (!(pendingExplicit || (pendingTick && !backedOff))) return
    const wasExplicit = pendingExplicit
    const wasTick = pendingTick
    pendingExplicit = false
    pendingTick = false
    const act = newActive()
    try {
      const plan = planLaunch(host)
      if (!plan.ok) {
        endRun(act, { ok: false, code: plan.code })
        return
      }
      const lease = acquire(host)
      if (lease === 'busy') {
        if (wasExplicit) pendingExplicit = true
        if (wasTick) pendingTick = true
        state = 'cooling'
        startCool()
        return
      }
      if (lease === 'failed') {
        endRun(act, { ok: false, code: READER_CANNOT_START })
        return
      }
      const sink = openSink(ownedHooks(act))
      const handle = startReader(host, plan, sink)
      afterStart(act, sink, handle)
    } catch {
      recover(act)
    }
  }

  // --- the public steps -----------------------------------------------------------

  const request = (reason: Reason) => {
    try {
      if (state === 'new' || state === 'stopped') return
      if (reason === 'tick') {
        // A tick under back-off is dropped, not queued.
        if (backedOff) return
        pendingTick = true
      } else {
        pendingExplicit = true
      }
      if (state === 'holding' && reason === 'command' && leaseFree(host)) {
        clear(cancelHold)
        clear(cancelPoll)
        clear(cancelFree)
        holdDone = true
        freeDone = true
        state = 'idle'
      }
      if (state === 'idle') queueDrain()
    } catch {
      // A lost request is asked again by the next tick.
    }
  }

  const start = () => {
    try {
      if (state !== 'new') return
      state = 'holding'
      pendingExplicit = true
      cancelInterval = host.every(INTERVAL_MS, () => {
        request('tick')
      })
      cancelHold = host.after(HOLD_MS, () => {
        try {
          holdDone = true
          leaveHold()
        } catch {
          // The hold ends at the next request.
        }
      })
      cancelPoll = host.after(0, () => {
        try {
          poll()
        } catch {
          // Polling stops; the hold stays.
        }
      })
    } catch {
      // A scheduler that did not start draws nothing and reads nothing more.
    }
  }

  const stop = () => {
    try {
      if (state === 'stopped') return
      state = 'stopped'
      clear(cancelInterval)
      clear(cancelHold)
      clear(cancelPoll)
      clear(cancelFree)
      clear(cancelCool)
      clear(cancelDrain)
      drainQueued = false
      pendingExplicit = false
      pendingTick = false
      const act = current
      if (act !== undefined) {
        clear(act.cancelTimeout)
        killRun(act)
      }
    } catch {
      // A reader that is not stopped here ends on its own limits.
    }
  }

  return { start, stop, request }
}
