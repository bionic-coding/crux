import { parseReader } from '../../hooks/lib/view.ts'

export const queueItem = (n: number, state = 'pending') => ({
  id: `Q-${String(n).padStart(4, '0')}`, title: `Queued item ${n}`, state,
  suggested_type: 'iterate', cycle: null, cycle_status: null,
})

export const queueDoc = (count: number, cycles: unknown[] = []) => ({
  format: 'crux.cycle-progress', format_version: 5, ok: true, docs_dir: 'bionic', now_s: 1780000000,
  cycles, queue: { ok: true, items: Array.from({ length: count }, (_, i) => queueItem(i + 1)), authorization: null },
})

export const queueParsed = (count: number, cycles: unknown[] = []) => parseReader(JSON.stringify(queueDoc(count, cycles)))

export const nineteenTasks = () => ({
  id: 'CYC-0057', schema_version: 2, revision: null, assignments: [], classification_count: 0, exception: null,
  title: 'P10B — Current visibility checks and index lifecycle', type: 'dev', status: 'active', phase: 'build', pass: 1, pass_limit: 7,
  phases: ['plan', 'build', 'test', 'review', 'reflect'],
  tasks: [
    { id: 'plan', phase: 'plan', description: 'Plan complete', status: 'done' },
    ...['done', 'done', 'active', ...Array.from({ length: 7 }, () => 'pending'), ...Array.from({ length: 4 }, () => 'done')]
      .map((status, i) => ({ id: `build-${i}`, phase: 'build', description: `Build task ${i}`, status })),
    { id: 'test', phase: 'test', description: 'Verify', status: 'pending' },
    { id: 'review', phase: 'review', description: 'Independent review', status: 'pending' },
    { id: 'security', phase: 'review', description: 'Relevant security review', status: 'pending' },
    { id: 'reflect', phase: 'reflect', description: 'Reflect', status: 'pending' },
  ],
  returns: [], waits: [], blocker: null, reflection: null, modified_s: 1780000000,
  started_s: 1779999000, ended_s: null, paused_s: 0, open_started_s: 1779999500, basis: 'recorded',
  phase_times: [{ phase: 'plan', active_s: 100, paused_s: 0 }],
})
