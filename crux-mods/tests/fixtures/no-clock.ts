// A guard for the dashboard's single clock: it runs a function with every process clock read
// throwing, and restores the clocks afterwards. The runtime freezes Date and performance, so the
// guard replaces the two globals instead of their methods. A Date made from a number still works,
// as view.ts's utc makes one from the reader's seconds.
export function withoutClock(run: () => void) {
  const g = globalThis as any
  const RealDate = Date
  const realPerformance = g.performance
  class NoClock extends RealDate {
    constructor(...args: any[]) {
      if (args.length === 0) throw new Error('clock read: new Date()')
      super(...(args as [number]))
    }
    static now(): number {
      throw new Error('clock read: Date.now()')
    }
  }
  g.Date = NoClock
  g.performance = { now: () => { throw new Error('clock read: performance.now()') } }
  try {
    run()
  } finally {
    g.Date = RealDate
    g.performance = realPerformance
  }
}

// The three shapes of a clock read the parity test also scans for.
export const CLOCK_READ = /\bDate\s*\.\s*now\s*\(|\bnew\s+Date\s*\(\s*\)|\bperformance\s*\.\s*now\s*\(/
