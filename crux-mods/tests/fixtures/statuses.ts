// Every status the dashboard reports, with a mocked machine that makes the launch report it. A test
// holds this set equal to the launch codes, reader-failed:<each reader error code> and the view's
// own codes: 30 statuses in all.
//
// reader-timeout's machine is a process hook that answers `{ deny }` in Claude Code's own timeout
// wording; world.ts says why a thrown error cannot stand in for it.
import type { Opts } from './world.ts'
import { UV, baseEnv } from './world.ts'
import { READER_EMPTY, READER_OK, readerError } from './reader-output.ts'

const ok = (doc: unknown) => ({ exitCode: 0, stdout: JSON.stringify(doc) })

// The reader's closed error codes, as visualize-run-progress.py emits them.
const READER_CODES = [
  'usage', 'project-root-invalid', 'config-invalid', 'tree-missing', 'containment', 'book-not-found',
  'run-not-found', 'run-invalid', 'book-invalid', 'token-set-unavailable', 'yaml-unavailable', 'time-limit',
  'internal',
]

export const STATUS_MACHINES: Record<string, Opts> = {
  'no-env-binary': { files: { '/usr/bin/env': 'other' } },
  'config-dir-mismatch': { installedAt: 'ancestor', env: { HOME: '/home/u', CLAUDE_CONFIG_DIR: '/other' } },
  'inside-project': { env: { HOME: '/proj/home', CLAUDE_CONFIG_DIR: '/cfg' } },
  'project-root-invalid': { files: { '/proj': 'file' } },
  'home-invalid': { env: { CLAUDE_CONFIG_DIR: '/cfg' } },
  'uv-not-found': { files: { [UV]: 'other' } },
  'crux-not-installed': { record: { plugins: {} } },
  'version-mismatch': { ownVersion: '9.9.9' },
  'reader-no-json-mode': { reader: { exitCode: 2, stdout: '', stderr: 'usage: visualize-run-progress target\nvisualize-run-progress: error: unrecognized arguments: --json\n' } },
  'offline-unavailable': { reader: { exitCode: 1, stdout: '', stderr: 'error: Failed to download `pyyaml==6.0.2`\n' } },
  'reader-timeout': { reader: 'timeout' },
  'reader-cannot-start': { reader: 'throw' },
  'reader-cpu-limit': { reader: { exitCode: 152, stdout: '' } },
  'reader-failed': { reader: { exitCode: 1, stdout: 'Traceback' } },
  'reader-output-invalid': { reader: { exitCode: 0, stdout: '{"format": ' } },
  'no-active-run': { reader: ok(READER_EMPTY) },
  'reader-format-mismatch': { reader: ok({ ...READER_OK, format_version: 1 }) },
  ...Object.fromEntries(READER_CODES.map(c => [`reader-failed:${c}`, { reader: { exitCode: 1, stdout: JSON.stringify(readerError(c)) } }])),
}

export const STATUS_CODES = Object.keys(STATUS_MACHINES)
