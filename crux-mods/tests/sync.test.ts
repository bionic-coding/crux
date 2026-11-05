// A cycle's tasks change mid-cycle: task-add, a fix task, a hand-over, a return's reset, a task
// status change. Each change is a write to the cycle record, which the observer sees as a tool call
// naming cycle.py. The next refresh after that write must draw the record as it stands after it.
//
// The reader here reads the record when its process starts, as visualize-run-progress does, and
// answers after READ_MS. On an idle machine the reader takes about 0.3 s; READ_MS stands for a
// machine busy with a test suite, where a run outlasts the 1.5 s write debounce. A refresh that
// joins a reader run started before the write draws the record as it stood before the write, and
// nothing reads it again until the 15 s timer.
import { test, expect } from 'claude-code/testing'
import { PANE, install, texts } from './fixtures/world.ts'

const READ_MS = 2_000

type Task = { id: string; phase: string; description: string; status: string }
type State = { phase: string; pass: number; tasks: Task[]; returns: { pass: number; phase: string; reason: string }[] }

const doc = (s: State) => ({
  format: 'crux.cycle-progress', format_version: 5, ok: true, docs_dir: 'bionic', now_s: 1780000000, queue: null,
  cycles: [{
    id: 'CYC-0001', schema_version: 3, revision: 1, assignments: [], classification_count: 0, exception: null,
    title: 'Keep the dashboard in sync', type: 'iterate', status: 'active', phase: s.phase, pass: s.pass, pass_limit: 2,
    phases: ['plan', 'build', 'verify', 'review', 'reflect'], tasks: s.tasks, returns: s.returns, waits: [], blocker: null,
    reflection: null, modified_s: 1780000000, started_s: 1779999000, ended_s: null, paused_s: 0, open_started_s: 1779999500,
    basis: 'recorded', phase_times: [{ phase: s.phase, active_s: 500, paused_s: 0 }],
  }],
})

const PLAN: Task = { id: 'plan', phase: 'plan', description: 'Write the plan', status: 'done' }
const UNIT: Task = { id: 'build-unit', phase: 'build', description: 'Build the unit', status: 'active' }
const BEFORE: State = { phase: 'build', pass: 1, tasks: [PLAN, UNIT], returns: [] }
const IN_VERIFY: State = { phase: 'verify', pass: 1, tasks: [PLAN, { ...UNIT, status: 'done' }], returns: [] }

// Each change: the record before it, the record after it, and a text the pane draws only after it.
const CHANGES: { name: string; command: string; before: State; after: State; shows: string }[] = [
  {
    name: 'task-add',
    command: 'uv run /x/crux/scripts/cycle.py task-add CYC-0001 --json @task.json',
    before: BEFORE,
    after: { ...BEFORE, tasks: [PLAN, UNIT, { id: 'build-more', phase: 'build', description: 'Build the added unit', status: 'pending' }] },
    shows: 'Build the added unit',
  },
  {
    name: 'a fix task',
    command: 'uv run /x/crux/scripts/cycle.py task-add CYC-0001 --json @fix.json',
    before: IN_VERIFY,
    after: { ...IN_VERIFY, tasks: [...IN_VERIFY.tasks, { id: 'fix-1', phase: 'verify', description: 'Fix finding F-1', status: 'pending' }] },
    shows: 'Fix finding F-1',
  },
  {
    name: 'a hand-over',
    command: 'uv run /x/crux/scripts/cycle.py task-add CYC-0001 --json @handover.json',
    before: BEFORE,
    after: { ...BEFORE, tasks: [PLAN, UNIT, { id: 'handover-1', phase: 'build', description: 'Hand-over: tools/x.py, Stream R, format bump', status: 'active' }] },
    shows: 'Hand-over: tools/x.py',
  },
  {
    name: "a return's reset",
    command: 'uv run /x/crux/scripts/cycle.py return CYC-0001 --json @return.json',
    before: IN_VERIFY,
    after: { phase: 'build', pass: 2, tasks: [PLAN, { ...UNIT, status: 'pending' }], returns: [{ pass: 1, phase: 'verify', reason: 'one defect remains' }] },
    shows: '1/2 tasks',
  },
  {
    name: 'a task status change',
    command: "uv run /x/crux/scripts/cycle.py op CYC-0001 --json '{\"op\":\"deliver\"}'",
    before: BEFORE,
    after: { ...BEFORE, tasks: [PLAN, { ...UNIT, status: 'done' }] },
    shows: '2/2 tasks',
  },
]

// The mocked machine, with a reader that reads `record.state` when it starts and answers READ_MS later.
function world(on: any, record: { state: State }) {
  const w = install(on, { readAtStart: () => ({ exitCode: 0, stdout: JSON.stringify(doc(record.state)), delayMs: READ_MS }) })
  on('tool.call', () => ({ result: 'ok' }) as any)
  return w
}

// The pane, mounted once per test; each read draws it as it stands then.
const mountPane = async ($: any) => {
  const m = await $.ui.mount({ plugin: 'crux-mods', surface: 'terminal', component: 'Pane', requestId: 'crux-dashboard', props: PANE })
  return async () => texts(await m.drawn()).join('\n')
}

for (const change of CHANGES) {
  test(`after ${change.name}, the next refresh draws the record as it stands after the write`, async ($, on) => {
    const record = { state: change.before }
    const w = world(on, record)
    // The session starts a reader run at 0 s; it reads the record before the change.
    await $.session.start({ cwd: '/proj' } as any)
    await w.clock.advance(100)
    expect(w.runs.length).toBe(1)
    // The change lands at 0.1 s, while that run is still reading.
    record.state = change.after
    await $.tool.call({ tool: 'Bash', command: change.command } as any)
    // The write's refresh is due at 1.6 s. By 5 s it has had time to read and answer; the 15 s timer has not fired.
    await w.clock.advance(4_900)
    const pane = await mountPane($)
    expect(await pane()).toContain(change.shows)
  })

  test(`control: after ${change.name} with no reader run in flight, the next refresh draws the change`, async ($, on) => {
    const record = { state: change.before }
    const w = world(on, record)
    await $.session.start({ cwd: '/proj' } as any)
    await w.clock.advance(2_500)
    // The case is what it claims: the first run drew the record before the change.
    const pane = await mountPane($)
    expect(await pane()).not.toContain(change.shows)
    record.state = change.after
    await $.tool.call({ tool: 'Bash', command: change.command } as any)
    await w.clock.advance(4_900)
    expect(w.runs.length).toBe(2)
    expect(await pane()).toContain(change.shows)
  })
}

test('/crux-dashboard after a write answers from a reader run that started after it', async ($, on) => {
  const record = { state: BEFORE }
  const w = world(on, record)
  await $.session.start({ cwd: '/proj' } as any)
  await w.clock.advance(100)
  record.state = CHANGES[4]!.after
  await $.tool.call({ tool: 'Bash', command: CHANGES[4]!.command } as any)
  const pending = $.command.run({ command: 'crux-dashboard' } as any)
  await w.clock.advance(4_900)
  const text = String((await pending).text)
  expect(text).toContain('tasks done 2 total 2')
})
