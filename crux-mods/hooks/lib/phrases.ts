// The requests that open the run dashboard pane. A pure module: it holds no state and keeps no
// input, and its functions only read what they are given and answer a boolean.
//
// The list between the markers is strict JSON, with no comment or trailing comma, because
// tools/tests/test_crux_mods_phrase_parity.py reads it with a JSON parser. That test holds each
// phrase to run-promptbook's SKILL.md: each is a metadata trigger, sits in the "When to use" bullet
// that routes to status, and sits in no start, advance or abandon bullet. Add a phrase there before
// you add it here.
// BEGIN PHRASES
export const PHRASES = ["show the run", "show run progress", "visualize run progress", "run status", "promptbook status", "cycle status"] as const;
// END PHRASES

// The length bound leaves 16 code units beyond the longest phrase for ASCII spacing and a closing
// mark. A longer prompt never matches, even one that would normalize to a phrase. The length check
// runs before any character is read, so MAX_PROMPT_UNITS bounds the work on any prompt, however
// long.
export const MAX_PROMPT_UNITS = Math.max(...PHRASES.map(p => p.length)) + 16

// The whitespace the match trims and collapses: space, tab, line feed, vertical tab, form feed and
// carriage return. No other code unit counts as whitespace.
const SPACE = new Set([' ', '\t', '\n', '\v', '\f', '\r'])

function trimSpace(s: string): string {
  let a = 0
  let b = s.length
  while (a < b && SPACE.has(s[a]!)) a++
  while (b > a && SPACE.has(s[b - 1]!)) b--
  return s.slice(a, b)
}

// True when the text is at most MAX_PROMPT_UNITS code units, holds no code unit above 0x7F, and
// equals a phrase after these steps: trim the whitespace, drop one closing `.`, `?` or `!`, trim
// again, collapse each whitespace run to one space, and fold A-Z to lower case.
// The non-ASCII refusal runs before these steps. The steps trim, collapse and fold ASCII only, so a
// non-ASCII text cannot match today. No test fails without the refusal. It stays so that a later
// Unicode-aware step can never turn a look-alike into a phrase.
export function matchesPhrase(text: string): boolean {
  if (text.length > MAX_PROMPT_UNITS) return false
  for (let i = 0; i < text.length; i++) if (text.charCodeAt(i) > 0x7f) return false
  let s = trimSpace(text)
  const last = s[s.length - 1]
  if (last === '.' || last === '?' || last === '!') s = s.slice(0, -1)
  s = trimSpace(s)
  let out = ''
  let gap = false
  for (let i = 0; i < s.length; i++) {
    const c = s[i]!
    if (SPACE.has(c)) {
      gap = true
      continue
    }
    if (gap) out += ' '
    gap = false
    const code = c.charCodeAt(0)
    out += code >= 0x41 && code <= 0x5a ? String.fromCharCode(code + 32) : c
  }
  return (PHRASES as readonly string[]).includes(out)
}

// Whether a submitted prompt is a request for the run: typed at the composer or sent through the
// bridge, with no attachment and a text that matches. It reads the origin kind first, then the
// attachments, then the text, and nothing else. So the text of a prompt the user did not type, or
// of one that carries an attachment, is never read. The result does not show the order; a test
// whose getters throw holds it.
export function asksForTheRun(input: { text?: unknown; origin?: { kind?: unknown }; attachments?: unknown }): boolean {
  const kind = input.origin?.kind
  if (kind !== 'composer' && kind !== 'bridge') return false
  const a = input.attachments
  if (a !== undefined && !(Array.isArray(a) && a.length === 0)) return false
  if (typeof input.text !== 'string') return false
  return matchesPhrase(input.text)
}
