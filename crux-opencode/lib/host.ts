// The boundary between crux-opencode's pure modules and the host. tui.tsx builds one
// value of type Host from guarded reads and wrapper functions, and passes it to the
// pure modules. Every field is a primitive or a function. No function throws, and each
// returns a primitive, undefined, or a function or object the boundary file wrote.

// What the process the host started hands back: two ways to stop it. Neither is called
// after the process has exited.
export type ReaderHandle = { term: () => void; hard: () => void }

// The calls the host makes on the sink of one reader run, one per process event.
// out and err receive byte values, one number per byte; -1 stands for a chunk the
// boundary could not convert. closed receives the exit code, or undefined after a signal.
export type ReaderSink = {
  spawned: () => void
  exited: () => void
  out: (bytes: number[]) => void
  err: (bytes: number[]) => void
  failed: () => void
  closed: (code: number | undefined) => void
}

// What the kept memory value holds: the reader's standard output, or a status code.
export type KeptEnvelope = { ok: true; stdout: string } | { ok: false; code: string }

// A successful plan: the four values the one admitted launch is built from.
export type Planned = { ok: true; uv: string; crux: string; home: string; root: string }

export type Host = {
  version: string | undefined
  directory: string | undefined
  cloneDir: string | undefined
  env: (name: string) => string | undefined
  isFile: (path: string) => boolean
  isDir: (path: string) => boolean
  real: (path: string) => string | undefined
  read: (path: string) => string | undefined
  // Starts the reader process. Three results: a handle that stops the process; 'untracked', a process
  // exists but its listeners were not all attached, so the caller keeps the lease and cannot stop it;
  // undefined, no process was started.
  start: (argv: string[], cwd: string, sink: ReaderSink) => ReaderHandle | 'untracked' | undefined
  after: (ms: number, fn: () => void) => () => void
  every: (ms: number, fn: () => void) => () => void
  leaseRead: () => 'held' | 'free' | 'unknown'
  leaseWrite: (b: boolean) => boolean
  writeKept: (v: KeptEnvelope | null) => void
  openPanel: () => boolean
  // Whether the host reports crux's panel open. False when the host cannot say.
  panelOpen: () => boolean
  // Closes crux's panel. False when the host refused the call.
  closePanel: () => boolean
  toast: (code: string) => void
}
