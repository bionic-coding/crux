// Display width for the dashboard: how many terminal cells a text takes, how to cut a text to a
// width, and the drawing width a render event reports. Pure functions; this file imports nothing,
// reads no clock and calls nothing on `$`.
//
// A code point counts two cells when Unicode 17.0.0 gives it the East Asian Width W or F, and one
// cell otherwise. That is the computed display width the dashboard's width rule binds, not a
// measure of any terminal: a terminal can draw an Ambiguous character, such as the ellipsis, two
// cells wide in a CJK locale, and can draw some emoji sequences wider than their code points count.
// A combining mark counts one cell, so a row with one is cut early and never overflows. Callers
// remove control, format and default-ignorable characters before they measure.

// The most cells a drawing takes: twice the reader's 200-code-point title cap.
export const MAX_WIDTH = 400
// The drawing width when the render event reports none.
export const DEFAULT_WIDTH = 40
export const ELLIPSIS = '\u{2026}'

// Every code point whose East Asian Width is W or F in Unicode 17.0.0, as 123 merged ranges,
// with the unassigned code points EastAsianWidth.txt's header defaults to W (the three CJK
// ideograph blocks and planes 2 and 3). Generated from
// https://www.unicode.org/Public/17.0.0/ucd/EastAsianWidth.txt (SHA-256
// ea7ce50f3444a050333448dffef1cadd9325af55cbb764b4a2280faf52170a33), which is not committed:
//
//   python3 - EastAsianWidth.txt <<'PY'
//   import sys
//   val = {}
//   for line in open(sys.argv[1], encoding='utf-8'):
//       body = line.split('#', 1)[0].strip()
//       if body:
//           rng, v = (x.strip() for x in body.split(';'))
//           lo, _, hi = rng.partition('..')
//           for cp in range(int(lo, 16), int(hi or lo, 16) + 1): val[cp] = v
//   for lo, hi in [(0x3400, 0x4DBF), (0x4E00, 0x9FFF), (0xF900, 0xFAFF), (0x20000, 0x2FFFD), (0x30000, 0x3FFFD)]:
//       for cp in range(lo, hi + 1): val.setdefault(cp, 'W')
//   out = []
//   for cp in sorted(cp for cp, v in val.items() if v in ('W', 'F')):
//       if out and out[-1][1] == cp - 1: out[-1][1] = cp
//       else: out.append([cp, cp])
//   for lo, hi in out: print(f'[0x{lo:X}, 0x{hi:X}],')
//   PY
//
// CPython 3.15's unicodedata (Unicode 17.0.0) reports the same set. The table is a frozen constant
// of the mod: a later Unicode version changes it only by regenerating it here.
const WIDE: readonly (readonly [number, number])[] = [
  [0x1100, 0x115F], [0x231A, 0x231B], [0x2329, 0x232A], [0x23E9, 0x23EC],
  [0x23F0, 0x23F0], [0x23F3, 0x23F3], [0x25FD, 0x25FE], [0x2614, 0x2615],
  [0x2630, 0x2637], [0x2648, 0x2653], [0x267F, 0x267F], [0x268A, 0x268F],
  [0x2693, 0x2693], [0x26A1, 0x26A1], [0x26AA, 0x26AB], [0x26BD, 0x26BE],
  [0x26C4, 0x26C5], [0x26CE, 0x26CE], [0x26D4, 0x26D4], [0x26EA, 0x26EA],
  [0x26F2, 0x26F3], [0x26F5, 0x26F5], [0x26FA, 0x26FA], [0x26FD, 0x26FD],
  [0x2705, 0x2705], [0x270A, 0x270B], [0x2728, 0x2728], [0x274C, 0x274C],
  [0x274E, 0x274E], [0x2753, 0x2755], [0x2757, 0x2757], [0x2795, 0x2797],
  [0x27B0, 0x27B0], [0x27BF, 0x27BF], [0x2B1B, 0x2B1C], [0x2B50, 0x2B50],
  [0x2B55, 0x2B55], [0x2E80, 0x2E99], [0x2E9B, 0x2EF3], [0x2F00, 0x2FD5],
  [0x2FF0, 0x303E], [0x3041, 0x3096], [0x3099, 0x30FF], [0x3105, 0x312F],
  [0x3131, 0x318E], [0x3190, 0x31E5], [0x31EF, 0x321E], [0x3220, 0x3247],
  [0x3250, 0xA48C], [0xA490, 0xA4C6], [0xA960, 0xA97C], [0xAC00, 0xD7A3],
  [0xF900, 0xFAFF], [0xFE10, 0xFE19], [0xFE30, 0xFE52], [0xFE54, 0xFE66],
  [0xFE68, 0xFE6B], [0xFF01, 0xFF60], [0xFFE0, 0xFFE6], [0x16FE0, 0x16FE4],
  [0x16FF0, 0x16FF6], [0x17000, 0x18CD5], [0x18CFF, 0x18D1E], [0x18D80, 0x18DF2],
  [0x1AFF0, 0x1AFF3], [0x1AFF5, 0x1AFFB], [0x1AFFD, 0x1AFFE], [0x1B000, 0x1B122],
  [0x1B132, 0x1B132], [0x1B150, 0x1B152], [0x1B155, 0x1B155], [0x1B164, 0x1B167],
  [0x1B170, 0x1B2FB], [0x1D300, 0x1D356], [0x1D360, 0x1D376], [0x1F004, 0x1F004],
  [0x1F0CF, 0x1F0CF], [0x1F18E, 0x1F18E], [0x1F191, 0x1F19A], [0x1F200, 0x1F202],
  [0x1F210, 0x1F23B], [0x1F240, 0x1F248], [0x1F250, 0x1F251], [0x1F260, 0x1F265],
  [0x1F300, 0x1F320], [0x1F32D, 0x1F335], [0x1F337, 0x1F37C], [0x1F37E, 0x1F393],
  [0x1F3A0, 0x1F3CA], [0x1F3CF, 0x1F3D3], [0x1F3E0, 0x1F3F0], [0x1F3F4, 0x1F3F4],
  [0x1F3F8, 0x1F43E], [0x1F440, 0x1F440], [0x1F442, 0x1F4FC], [0x1F4FF, 0x1F53D],
  [0x1F54B, 0x1F54E], [0x1F550, 0x1F567], [0x1F57A, 0x1F57A], [0x1F595, 0x1F596],
  [0x1F5A4, 0x1F5A4], [0x1F5FB, 0x1F64F], [0x1F680, 0x1F6C5], [0x1F6CC, 0x1F6CC],
  [0x1F6D0, 0x1F6D2], [0x1F6D5, 0x1F6D8], [0x1F6DC, 0x1F6DF], [0x1F6EB, 0x1F6EC],
  [0x1F6F4, 0x1F6FC], [0x1F7E0, 0x1F7EB], [0x1F7F0, 0x1F7F0], [0x1F90C, 0x1F93A],
  [0x1F93C, 0x1F945], [0x1F947, 0x1F9FF], [0x1FA70, 0x1FA7C], [0x1FA80, 0x1FA8A],
  [0x1FA8E, 0x1FAC6], [0x1FAC8, 0x1FAC8], [0x1FACD, 0x1FADC], [0x1FADF, 0x1FAEA],
  [0x1FAEF, 0x1FAF8], [0x20000, 0x2FFFD], [0x30000, 0x3FFFD],
]

// The cells one code point takes: a binary search of the table.
export function cpWidth(cp: number): number {
  let lo = 0
  let hi = WIDE.length - 1
  while (lo <= hi) {
    const mid = (lo + hi) >> 1
    const [a, b] = WIDE[mid]!
    if (cp < a) hi = mid - 1
    else if (cp > b) lo = mid + 1
    else return 2
  }
  return 1
}

// The cells a text takes. A lone surrogate counts one.
export function cells(s: string): number {
  let n = 0
  for (const ch of s) n += cpWidth(ch.codePointAt(0)!)
  return n
}

// The longest head of the text that takes at most n cells. It never splits a code point.
export function head(s: string, n: number): string {
  let used = 0
  let out = ''
  for (const ch of s) {
    const w = cpWidth(ch.codePointAt(0)!)
    if (used + w > n) break
    used += w
    out += ch
  }
  return out
}

// The text whole when it takes at most n cells. A longer text keeps its longest head of at most
// n-1 cells and gains an ellipsis, so the result never takes more than n cells. At n = 1 the
// result is the ellipsis alone, and below 1 it is empty.
export function fit(s: string, n: number): string {
  if (cells(s) <= n) return s
  if (n < 1) return ''
  return head(s, n - 1) + ELLIPSIS
}

// The text cut into chunks of at most n cells each, in order, never splitting a code point. An
// empty text is one empty chunk. A code point wider than n draws as an ellipsis in a chunk of its own.
export function wrap(s: string, n: number): string[] {
  const out: string[] = []
  let cur = ''
  let used = 0
  for (const ch of s) {
    const w = cpWidth(ch.codePointAt(0)!)
    if (w > n) {
      if (cur !== '') out.push(cur)
      out.push(fit(ch, n))
      cur = ''
      used = 0
      continue
    }
    if (used + w > n) {
      out.push(cur)
      cur = ''
      used = 0
    }
    cur += ch
    used += w
  }
  if (cur !== '' || out.length === 0) out.push(cur)
  return out
}

// The drawing width: the render event's bodyColumns rounded down when it is a finite number of at
// least 1, else DEFAULT_WIDTH, and never more than MAX_WIDTH.
export function drawingWidth(cols: unknown): number {
  if (typeof cols !== 'number' || !Number.isFinite(cols) || cols < 1) return DEFAULT_WIDTH
  return Math.min(Math.floor(cols), MAX_WIDTH)
}
