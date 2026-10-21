// The reader lease: one boolean in the host that records whether a reader process this crux-omp
// started may still run. It is the only guard between two setups that share memory across a reload.
// leaseRead and leaseWrite are the only code that reaches the value; neither throws.
import type { Host } from './host.ts'

export type Acquired = 'acquired' | 'busy' | 'failed'

// An unreadable lease is never free.
export function leaseFree(host: Host): boolean {
  return host.leaseRead() === 'free'
}

// A test-and-set. It runs inside one synchronous callback, and the host runs one callback at a
// time, so no other setup acquires between the read of free and the read of held. It writes nothing
// when the lease is not free. It confirms an acquisition only when the write reports success and a
// second read returns held; on any other outcome it writes false, which also undoes a write that
// changed the value before it failed.
export function acquire(host: Host): Acquired {
  if (host.leaseRead() !== 'free') return 'busy'
  if (host.leaseWrite(true) === true && host.leaseRead() === 'held') return 'acquired'
  host.leaseWrite(false)
  return 'failed'
}

export function release(host: Host): void {
  host.leaseWrite(false)
}
