// Starting the reader and reading what it writes. startReader is the one place that builds the
// launch and the one place that asks the host to start a process. openSink makes the per-run sink:
// it decodes the reader's output, ends the run exactly once, and catches every exception its own
// methods throw.
import { buildLaunch, classifyFinished } from '../../crux-mods/hooks/lib/launch.ts'
import { LAUNCH_VALUES } from './plan.ts'
import type { Host, Planned, ReaderHandle, ReaderSink } from './host.ts'
import { READER_CANNOT_START, READER_OUTPUT_INVALID } from './status.ts'

// The reader's output past this many bytes is not a document this view can check.
export const READ_CAP = 1024 * 1024
// Standard error only selects a status code, so a short prefix of it is enough.
export const ERR_CAP = 64 * 1024
// Characters passed to one String.fromCharCode call, which keeps each spread within any engine's
// argument limit.
const SLICE = 4096

export function startReader(host: Host, plan: Planned, sink: ReaderSink): ReaderHandle | 'untracked' | undefined {
  try {
    const launch = buildLaunch(LAUNCH_VALUES, plan.uv, plan.crux, plan.home, plan.root)
    // argv[0] is the launcher, /usr/bin/env, which the host's start names itself. The host receives
    // the rest, which begins with -i, and refuses any other first argument.
    return host.start(launch.argv.slice(1), launch.cwd, sink)
  } catch {
    return undefined
  }
}

// How a run ended: the reader's standard output, or the status code that names why there is none.
export type Ended = { ok: true; stdout: string } | { ok: false; code: string }

// What the scheduler gives a sink: stop the process, and take the end of the run.
export type SinkHooks = { kill: () => void; end: (ended: Ended) => void }

// The sink the host calls, and what the scheduler asks of the same run.
export type RunSink = ReaderSink & {
  // Records a status for the run. Only the first status counts.
  record: (code: string) => void
  status: () => string | undefined
  hasExited: () => boolean
  hasEnded: () => boolean
}

// ASCII bytes as text, in slices, so no chunk boundary can split a character.
const textOf = (bytes: number[]): string => {
  const parts: string[] = []
  for (let i = 0; i < bytes.length; i += SLICE) parts.push(String.fromCharCode(...bytes.slice(i, i + SLICE)))
  return parts.join('')
}

const isAscii = (v: number): boolean => Number.isInteger(v) && v >= 0 && v <= 0x7f

export function openSink(hooks: SinkHooks): RunSink {
  let ended = false
  let exited = false
  let spawned = false
  let truncated = false
  let status: string | undefined
  const outBytes: number[] = []
  const errBytes: number[] = []

  const record = (code: string) => {
    if (status === undefined) status = code
  }
  const refuse = (code: string) => {
    record(code)
    try {
      hooks.kill()
    } catch {
      // The scheduler catches its own; nothing more to do here.
    }
  }
  // A method that throws records reader-output-invalid and kills, as for a refused byte.
  const guard = (body: () => void) => {
    if (ended) return
    try {
      body()
    } catch {
      refuse(READER_OUTPUT_INVALID)
    }
  }
  const finish = (code: number | undefined) => {
    let result: Ended = { ok: false, code: READER_OUTPUT_INVALID }
    try {
      result =
        status !== undefined
          ? { ok: false, code: status }
          : classifyFinished({ exit: code ?? -1, stdout: textOf(outBytes), stderr: textOf(errBytes), truncated })
    } catch {
      // The code above stands.
    }
    try {
      hooks.end(result)
    } catch {
      // The scheduler catches its own.
    }
  }

  return {
    spawned: () => {
      guard(() => {
        spawned = true
      })
    },
    exited: () => {
      guard(() => {
        exited = true
      })
    },
    out: bytes => {
      guard(() => {
        if (status !== undefined) return
        for (const v of bytes) {
          if (!isAscii(v)) {
            refuse(READER_OUTPUT_INVALID)
            return
          }
          if (outBytes.length >= READ_CAP) {
            truncated = true
            refuse(READER_OUTPUT_INVALID)
            return
          }
          outBytes.push(v)
        }
      })
    },
    err: bytes => {
      guard(() => {
        for (const v of bytes) {
          if (errBytes.length >= ERR_CAP) return
          errBytes.push(isAscii(v) ? v : 0xfffd)
        }
      })
    },
    // An error before spawn means no process exists, so it ends the run. An error after spawn ends
    // nothing: the close that follows ends it.
    failed: () => {
      if (ended || spawned) return
      ended = true
      record(READER_CANNOT_START)
      finish(undefined)
    },
    closed: code => {
      if (ended) return
      ended = true
      finish(code)
    },
    record,
    status: () => status,
    hasExited: () => exited,
    hasEnded: () => ended,
  }
}
