// A JSON writer over plain values, written by hand so the tests use no runtime global beyond
// JSON.parse. An undefined member is left out, as a JSON writer leaves it out.
const hex4 = (code: number): string => ('0000' + code.toString(16)).slice(-4)

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
