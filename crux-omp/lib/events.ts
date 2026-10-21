// What crux-omp takes from a host event: whether a submitted prompt asks for the run, and whether
// a finished tool call wrote a run or cycle file. Both functions read only the values they are
// given; neither keeps them.
import { matchesPhrase } from '../../crux-mods/hooks/lib/phrases.ts'

const WRITING_TOOLS = ['write', 'edit', 'apply_patch', 'multiedit', 'notebookedit']
const RUN_DIRECTORIES = ['/promptbooks/runs/', '/cycles/', '/queue/']
// The reader reports run_path and book_path relative to the tree root, so a tool argument can name
// the directory without a leading slash.
const RUN_DIRECTORIES_RELATIVE = ['promptbooks/runs/', 'queue/cycles.yaml']
const RUN_COMMANDS = ['cycle.py', 'cycle_queue.py']

// True when a submitted prompt asks for the run: the user typed it at the composer or sent it
// through RPC, it carries no image, and its text matches one of the run phrases.
export function asksForTheRun(event: unknown): boolean {
  if (event === null || typeof event !== 'object') return false
  const e = event as Record<string, unknown>
  if (e.source !== 'interactive' && e.source !== 'rpc') return false
  if (Array.isArray(e.images) && e.images.length > 0) return false
  return typeof e.text === 'string' && matchesPhrase(e.text)
}

// The paths an event's input names: the fields OMP's write and edit tools use, and a patch body
// for apply_patch.
function pathsOf(input: Record<string, unknown>): string[] {
  const out: string[] = []
  for (const key of ['path', 'file_path', 'filePath', 'notebook_path']) {
    const value = input[key]
    if (typeof value === 'string' && value !== '') out.push(value)
  }
  if (typeof input.patch === 'string' && input.patch !== '') out.push(input.patch)
  return out
}

// True when a finished tool call wrote a file under a run or cycle directory, or ran a command
// naming one. The docs directory narrows the answer when the reader has reported it; without one,
// the run-directory segments alone decide.
export function touchesRunFile(toolName: unknown, input: unknown, docsDir?: unknown): boolean {
  if (typeof toolName !== 'string' || input === null || typeof input !== 'object') return false
  const tool = toolName.toLowerCase()
  const fields = input as Record<string, unknown>
  const roots: string[] = []
  if (typeof docsDir === 'string' && docsDir !== '') {
    const base = docsDir.replace(/\/+$/, '')
    for (const segment of RUN_DIRECTORIES) roots.push(base + segment)
  }
  roots.push(...RUN_DIRECTORIES, ...RUN_DIRECTORIES_RELATIVE)
  const names = (text: string) => roots.some(root => text.includes(root))

  if (tool === 'bash') {
    const command = fields.command
    if (typeof command !== 'string') return false
    return names(command) || RUN_COMMANDS.some(word => command.includes(word))
  }
  if (!WRITING_TOOLS.includes(tool)) return false
  return pathsOf(fields).some(names)
}

// Extracts a short, single-line human target/summary from a tool input object for live display.
export function summarizeToolDetail(toolName: unknown, input: unknown): string {
  if (typeof toolName !== 'string' || input === null || typeof input !== 'object') return ''
  const tool = toolName.toLowerCase()
  const fields = input as Record<string, unknown>
  if (typeof fields.i === 'string' && fields.i.trim() !== '') {
    return fields.i.trim().slice(0, 72)
  }
  if (tool === 'task') {
    if (Array.isArray(fields.tasks)) {
      const names = fields.tasks
        .map(t => (t !== null && typeof t === 'object' ? ((t as Record<string, unknown>).name ?? (t as Record<string, unknown>).agent) : undefined))
        .filter((v): v is string => typeof v === 'string' && v !== '')
      return names.length > 0 ? `${fields.tasks.length} subagents (${names.slice(0, 3).join(', ')})` : `${fields.tasks.length} subagents`
    }
    if (typeof fields.name === 'string' && fields.name !== '') return fields.name
    if (typeof fields.agent === 'string' && fields.agent !== '') return fields.agent
  }
  for (const key of ['path', 'file_path', 'filePath', 'pattern', 'query', 'command', 'url']) {
    const val = fields[key]
    if (typeof val === 'string' && val.trim() !== '') {
      return val.trim().replace(/\s+/g, ' ').slice(0, 64)
    }
  }
  return ''
}
