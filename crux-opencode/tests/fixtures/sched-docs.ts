// Reader documents for the scheduler tests, kept as constants because a test cannot read
// a file. They follow the version-2 document of the installed crux reader.
import { jsonText } from './plain.ts'

const RUN = {
  book_id: 'PB-0149',
  run_id: 'RUN-001',
  status: 'in_progress',
  current_prompt: 2,
  run_path: 'promptbooks/runs/PB-0149-a-book/run-RUN-001.yaml',
  book_path: 'promptbooks/active/PB-0149-a-book.yaml',
  modified_s: 1791687539,
  started_s: 1791680000,
  completed_s: null,
  tag_joined: true,
  progress: { total: 2, terminal: 1, done: 1, pct: 50, counts: { done: 1, skipped: 0, blocked: 0, running: 1, pending: 0 } },
  prompts: [
    { n: 1, state: 'done', module_tag: 'adr-1', title: 'First', started_s: 1791680000, completed_s: 1791682000 },
    { n: 2, state: 'running', module_tag: null, title: 'Second', started_s: 1791687100, completed_s: null },
  ],
  councils: [],
  councils_skipped: 0,
  gates: [],
  summary: [],
  summary_truncated: false,
  escalations: [],
}

// A success document with one run in progress.
export const VIEW_DOC = {
  format: 'crux.run-progress',
  format_version: 2,
  ok: true,
  reader_version: '3.27.4',
  docs_dir: 'bionic',
  now_s: 1791687839,
  runs: [RUN],
  runs_skipped: 0,
  last_completed: null,
  last_completed_status: 'run-in-progress',
  last_completed_undated: 0,
  last_completed_unresolved: 0,
}

// A success document with no run: the view code no-active-run.
export const NO_RUN_DOC = { ...VIEW_DOC, runs: [], last_completed_status: 'none' }

// A document of the reader's own format at another format version.
export const OTHER_FORMAT_DOC = { ...VIEW_DOC, format_version: 3 }

export const readerErrorDoc = (code: string) => ({ format: 'crux.run-progress', format_version: 2, ok: false, error: { code } })

export const VIEW_STDOUT = jsonText(VIEW_DOC)
