// Two helpers over plain values, written by hand so the tests use no runtime global beyond
// JSON.parse. jsonText writes the JSON text of a plain value: strings, finite numbers, booleans,
// null, arrays and objects, with an undefined member left out as a JSON writer leaves it out.
// containsText tells whether a string occurs anywhere in a plain value, as a string, as a member of
// an array or as a key or value of an object.

const hex4 = (code: number): string => ('0000' + code.toString(16)).slice(-4)

// A string as JSON text. Every UTF-16 unit outside printable ASCII is written as an escape, so a
// lone surrogate and a format character survive the round trip through JSON.parse.
function quoted(s: string): string {
  let out = '"'
  for (let i = 0; i < s.length; i++) {
    const code = s.charCodeAt(i)
    if (code === 0x22) out += '\\"'
    else if (code === 0x5c) out += '\\\\'
    else if (code < 0x20 || code > 0x7e) out += '\\u' + hex4(code)
    else out += s.charAt(i)
  }
  return out + '"'
}

export function jsonText(value: unknown): string {
  if (value === null) return 'null'
  if (typeof value === 'string') return quoted(value)
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) throw new Error('a number with no JSON text')
    return String(value)
  }
  if (typeof value === 'boolean') return String(value)
  if (Array.isArray(value)) return '[' + value.map(v => (v === undefined ? 'null' : jsonText(v))).join(',') + ']'
  if (typeof value === 'object') {
    const record = value as Record<string, unknown>
    const members: string[] = []
    for (const key of Object.keys(record)) {
      if (record[key] !== undefined) members.push(quoted(key) + ':' + jsonText(record[key]))
    }
    return '{' + members.join(',') + '}'
  }
  throw new Error('a value with no JSON text')
}

export function containsText(value: unknown, needle: string): boolean {
  if (typeof value === 'string') return value.includes(needle)
  if (Array.isArray(value)) return value.some(v => containsText(v, needle))
  if (typeof value === 'object' && value !== null) {
    const record = value as Record<string, unknown>
    return Object.keys(record).some(key => key.includes(needle) || containsText(record[key], needle))
  }
  return false
}
