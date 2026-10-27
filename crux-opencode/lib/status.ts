// The closed status codes crux-opencode keeps and draws, and the words it draws them with. This
// file is the one home of the code literals: every other crux-opencode file names a code through an
// export here. The codes are:
// - plan: project-root-unresolved, home-invalid, crux-not-found, uv-not-found,
//   inside-project, version-mismatch;
// - own run: reader-timeout, reader-cannot-start;
// - reader-output-invalid;
// - draw-only: opencode-version-unsupported, panel-unavailable;
// - from the core: its five run codes, its view codes and reader-failed:<code> per reader error.
// Written here as literal strings, never derived from another package's launch codes:
// - the six plan codes, which a refresh writes before any process starts;
// - the two run codes crux-opencode records itself, reader-timeout and reader-cannot-start;
// - reader-output-invalid, the two draw-only codes and the unsupported-version code.
// Imported from the core, because the core defines and classifies them:
// - the five run codes the core's classification of a finished process returns;
// - the view codes;
// - the reader's own error codes, kept under the reader-failed: prefix.
// The kept set holds the plan codes, the run codes, the view codes and reader-failed:<code> for each
// code the reader reports. The core's `kept` reads back only a code in the set it is given, so every
// code written here reads back as itself after a reload, and a draw-only code reads back as
// reader-output-invalid.
import { RUN_CODES } from '../../crux-mods/hooks/lib/launch.ts'
import { READER_ERROR_CODES, VIEW_CODES } from '../../crux-mods/hooks/lib/view.ts'
import type { Agents, Parsed } from '../../crux-mods/hooks/lib/view.ts'
import type { Harness } from '../../crux-mods/hooks/lib/draw.ts'

// Refusals of the launch plan.
export const PROJECT_ROOT_UNRESOLVED = 'project-root-unresolved'
export const HOME_INVALID = 'home-invalid'
export const CRUX_NOT_FOUND = 'crux-not-found'
export const UV_NOT_FOUND = 'uv-not-found'
export const INSIDE_PROJECT = 'inside-project'
export const VERSION_MISMATCH = 'version-mismatch'
export const PLAN_CODES: readonly string[] = [
  PROJECT_ROOT_UNRESOLVED,
  HOME_INVALID,
  CRUX_NOT_FOUND,
  UV_NOT_FOUND,
  INSIDE_PROJECT,
  VERSION_MISMATCH,
]

// The two run codes crux-opencode records itself.
export const READER_TIMEOUT = 'reader-timeout'
export const READER_CANNOT_START = 'reader-cannot-start'
export const OWN_RUN_CODES: readonly string[] = [READER_TIMEOUT, READER_CANNOT_START]

// Its own run codes and the five the core's classification of a finished process returns.
export const RUN_CODE_LIST: readonly string[] = [...OWN_RUN_CODES, ...RUN_CODES]

// The view's own codes.
export const VIEW_CODE_LIST: readonly string[] = [...VIEW_CODES]

// The reader's own error codes, each under the reader-failed prefix.
export const READER_FAILED_CODES: readonly string[] = READER_ERROR_CODES.map(code => `reader-failed:${code}`)

// Codes that are drawn or shown and never kept.
export const UNSUPPORTED_CODE = 'opencode-version-unsupported'
export const PANEL_UNAVAILABLE = 'panel-unavailable'
export const DRAW_ONLY: readonly string[] = [UNSUPPORTED_CODE, PANEL_UNAVAILABLE]

export const KEPT_CODES: readonly string[] = [...PLAN_CODES, ...RUN_CODE_LIST, ...VIEW_CODE_LIST, ...READER_FAILED_CODES]

export const READER_OUTPUT_INVALID = 'reader-output-invalid'

// The results the render path substitutes for a value it cannot read or draw.
export const UNSUPPORTED: Parsed = { ok: false, code: UNSUPPORTED_CODE }
export const INVALID: Parsed = { ok: false, code: READER_OUTPUT_INVALID }

// The wording. The band's status line leads with the prefix, which says which plugin drew it. The
// panel keeps the core's neutral prefix.
export const BAND_PREFIX = 'crux-opencode dashboard: '
export const UNSUPPORTED_WORDS = 'unsupported OpenCode version'
export const STALL_NOTE = 'Work this view cannot see can run for a long time without changing the run file.'

// The values the core's drawing takes from its importer. The host cannot turn pages, so the `cycles:` list caps at one page and a `+N more` line.
export const HARNESS: Harness = { bandPrefix: BAND_PREFIX, stallNote: STALL_NOTE, pages: false }

// This session's agents cannot be listed, so the core draws "agents unavailable" and no stall.
export const UNAVAILABLE_AGENTS: Agents = { available: false, running: 0, shown: [] }
