import { test, expect } from 'claude-code/testing'
import { registerAll } from '../lib/lifecycle.ts'
import type { Registration } from '../lib/lifecycle.ts'

// A set of registrations that log their calls. The one at `failAt` returns undefined.
function rig(count: number, failAt: number | undefined, how: 'undefined' | 'throw' = 'undefined') {
  const log: string[] = []
  const registrations: Registration[] = Array.from({ length: count }, (_, i) => () => {
    log.push('register' + i)
    if (i === failAt) {
      if (how === 'throw') throw new Error('register' + i)
      return undefined
    }
    return () => {
      log.push('release' + i)
    }
  })
  const start = () => {
    log.push('start')
  }
  const stop = () => {
    log.push('stop')
  }
  return { log, registrations, start, stop }
}

for (const failAt of [0, 1, 2, 3]) {
  test(`a failure at registration ${failAt} releases the earlier ones in reverse order and starts nothing`, () => {
    const { log, registrations, start, stop } = rig(4, failAt)
    const cleanup = registerAll(registrations, start, stop)
    const registered = Array.from({ length: failAt + 1 }, (_, i) => 'register' + i)
    const released = Array.from({ length: failAt }, (_, i) => 'release' + (failAt - 1 - i))
    expect(log).toEqual([...registered, ...released])
    // The cleanup it returns stops the scheduler and releases nothing twice.
    cleanup()
    expect(log).toEqual([...registered, ...released, 'stop'])
    cleanup()
    expect(log.length).toBe(registered.length + released.length + 1)
  })

  test(`a registration that throws at position ${failAt} is a failure`, () => {
    const { log, registrations, start, stop } = rig(4, failAt, 'throw')
    registerAll(registrations, start, stop)
    expect(log.includes('start')).toBe(false)
    expect(log.filter(e => e.startsWith('register')).length).toBe(failAt + 1)
    expect(log.filter(e => e.startsWith('release')).length).toBe(failAt)
  })
}

test('on success every registration runs in order and start is called once, last', () => {
  const { log, registrations, start, stop } = rig(4, undefined)
  registerAll(registrations, start, stop)
  expect(log).toEqual(['register0', 'register1', 'register2', 'register3', 'start'])
})

test('the cleanup calls stop and then each release once, in reverse order', () => {
  const { log, registrations, start, stop } = rig(3, undefined)
  const cleanup = registerAll(registrations, start, stop)
  log.length = 0
  cleanup()
  expect(log).toEqual(['stop', 'release2', 'release1', 'release0'])
})

test('a second cleanup call does nothing more', () => {
  const { log, registrations, start, stop } = rig(3, undefined)
  const cleanup = registerAll(registrations, start, stop)
  cleanup()
  const after = log.length
  cleanup()
  cleanup()
  expect(log.length).toBe(after)
})

test('a release that throws does not skip the others', () => {
  const log: string[] = []
  const make = (i: number, boom: boolean): Registration => () => {
    log.push('register' + i)
    return () => {
      log.push('release' + i)
      if (boom) throw new Error('release' + i)
    }
  }
  const cleanup = registerAll([make(0, false), make(1, true), make(2, true)], undefined, () => {
    log.push('stop')
  })
  log.length = 0
  cleanup()
  expect(log).toEqual(['stop', 'release2', 'release1', 'release0'])
  cleanup()
  expect(log.length).toBe(4)
})

test('a stop that throws does not skip the releases', () => {
  const { log, registrations } = rig(2, undefined)
  const cleanup = registerAll(registrations, undefined, () => {
    log.push('stop')
    throw new Error('stop')
  })
  log.length = 0
  cleanup()
  expect(log).toEqual(['stop', 'release1', 'release0'])
})

test('with no start function nothing starts', () => {
  const { log, registrations, stop } = rig(3, undefined)
  const cleanup = registerAll(registrations, undefined, stop)
  expect(log).toEqual(['register0', 'register1', 'register2'])
  cleanup()
  expect(log.slice(3)).toEqual(['stop', 'release2', 'release1', 'release0'])
})

test('a start that throws does not make registerAll throw, and the cleanup still works', () => {
  const log: string[] = []
  const cleanup = registerAll(
    [() => () => {
      log.push('release0')
    }],
    () => {
      log.push('start')
      throw new Error('start')
    },
    () => {
      log.push('stop')
    },
  )
  expect(log).toEqual(['start'])
  cleanup()
  expect(log).toEqual(['start', 'stop', 'release0'])
})

test('an empty list starts and stops', () => {
  const log: string[] = []
  const cleanup = registerAll([], () => {
    log.push('start')
  }, () => {
    log.push('stop')
  })
  cleanup()
  expect(log).toEqual(['start', 'stop'])
})

test('a registration that returns undefined in the middle stops the sequence', () => {
  // The registrar forms of the boundary return a function or undefined, nothing else.
  const log: string[] = []
  const cleanup = registerAll(
    [() => () => {
      log.push('release0')
    }, () => undefined, () => {
      log.push('never')
      return () => {}
    }],
    () => {
      log.push('start')
    },
    () => {
      log.push('stop')
    },
  )
  expect(log).toEqual(['release0'])
  cleanup()
  expect(log).toEqual(['release0', 'stop'])
})
