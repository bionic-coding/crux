// The theme-token map: one closed table from each of the core's ten theme keys to the name of a
// theme token. A token name is a path into the host's resolved theme, such as `syntax.keyword`. This
// module holds names only: no colour value reaches a pure module, and the boundary file turns a
// name into a colour when it draws.
//
// Four rules complete the table:
// - a span with no colour draws in text.base;
// - a dim span with no colour draws in text.muted;
// - where a span is both coloured and dim, the colour wins;
// - the frame colour comes through the same table, so a frame draws in text.muted.
import type { Span } from '../../crux-mods/hooks/lib/draw.ts'
import { PANEL_BORDER } from '../../crux-mods/hooks/lib/draw.ts'

export const TEXT_BASE = 'text.base'
export const TEXT_MUTED = 'text.muted'

// Each core key and the token it draws in.
export const TOKEN_TABLE: readonly (readonly [string, string])[] = [
  ['merged', 'syntax.keyword'],
  ['permission', 'syntax.type'],
  ['claude', 'syntax.function'],
  ['suggestion', 'text.feedback.info.base'],
  ['success', 'text.feedback.success.base'],
  ['inactive', TEXT_MUTED],
  ['text', TEXT_BASE],
  ['error', 'text.feedback.error.base'],
  ['warning', 'text.feedback.warning.base'],
  ['subtle', TEXT_MUTED],
]

// Every token name this module can produce.
export const TOKENS: readonly string[] = [
  'syntax.keyword',
  'syntax.type',
  'syntax.function',
  'text.feedback.info.base',
  'text.feedback.success.base',
  'text.feedback.error.base',
  'text.feedback.warning.base',
  TEXT_MUTED,
  TEXT_BASE,
]

// The token of a core key. A key the table does not name draws in text.base.
export function tokenOfKey(key: string): string {
  const row = TOKEN_TABLE.find(r => r[0] === key)
  return row === undefined ? TEXT_BASE : row[1]
}

// The token a span draws in.
export function spanToken(s: Span): string {
  if (s.color !== undefined) return tokenOfKey(s.color)
  return s.dim === true ? TEXT_MUTED : TEXT_BASE
}

// The token a bordered box draws its frame in.
export const FRAME_TOKEN: string = tokenOfKey(PANEL_BORDER)
