// The cycle view reads both phase vocabularies: a record made before the rename names its checking
// phase `test`, a record made after names it `verify`. A sequence is one vocabulary or the other,
// never a mix, and a release cycle (whose step list has its own `verify` step) reads as before.
import {test, expect} from 'claude-code/testing'
import {parseReader, answer} from '../hooks/lib/view.ts'
import {HARNESS, agents} from '../hooks/lib/claude.ts'
import {pane} from '../hooks/lib/draw.ts'

const SEQ: Record<string, string[]> = {
  dev: ['plan','build','test','review','reflect'], iterate: ['plan','build','test','review','reflect'],
  refactor: ['plan','build','test','review','reflect'], 'quick-fix': ['build','test','review','reflect'],
  simplify: ['plan','build','test','review','reflect'],
}
const named = (phases: string[], word: string) => phases.map(p => p === 'test' ? word : p)
const docOf = (type: string, phases: string[], over: Record<string, unknown> = {}) => ({
  format:'crux.cycle-progress',format_version:5,ok:true,docs_dir:'bionic',now_s:1780000000,
  cycles:[{id:'CYC-0001',schema_version:3,revision:2,assignments:[],classification_count:0,exception:null,title:'Rename',type,status:'active',
    phase:phases[0],pass:1,pass_limit:2,phases,
    tasks:phases.map(p => ({id:'t-'+p,phase:p,description:'Work in '+p,status:'pending'})),
    returns:[],waits:[],blocker:null,reflection:null,modified_s:1780000000,started_s:1779999000,ended_s:null,paused_s:0,
    open_started_s:1779999500,basis:'recorded',phase_times:[],...over}],
})
const paneOf = (doc: unknown) => JSON.stringify(pane(parseReader(JSON.stringify(doc)),agents([]),100,'docked',HARNESS))

test('every type reads and draws a record of either vocabulary', () => {
  for (const type of Object.keys(SEQ)) for (const word of ['test','verify']) {
    const phases = named(SEQ[type]!, word)
    const parsed = parseReader(JSON.stringify(docOf(type, phases)))
    expect(parsed.ok).toBe(true)
    expect(paneOf(docOf(type, phases))).toContain('Work in ' + word)
    expect(answer(parsed)).toContain('type ' + type)
  }
})

test('a record on the verify phase reads its stored phase, tasks and returns', () => {
  const phases = named(SEQ.dev!, 'verify')
  const doc = docOf('dev', phases, {phase:'verify',returns:[{pass:1,phase:'verify',reason:'A check failed'}],phase_times:[{phase:'verify',active_s:10,paused_s:0}]})
  const parsed = parseReader(JSON.stringify(doc))
  expect(parsed.ok).toBe(true)
  expect(answer(parsed)).toContain('phase verify')
})

test('one record never mixes the two vocabularies', () => {
  expect(parseReader(JSON.stringify(docOf('dev', ['plan','build','verify','review','reflect']))).ok).toBe(true)
  expect(parseReader(JSON.stringify(docOf('dev', ['plan','build','test','verify','review','reflect']))).ok).toBe(false)
})

test('a release cycle reads, and its verify step is a task, not a phase', () => {
  const doc = docOf('release', ['release'], {pass_limit:1})
  doc.cycles[0]!.tasks = [{id:'verify',phase:'release',description:'Run release verify',status:'active'}]
  const parsed = parseReader(JSON.stringify(doc))
  expect(parsed.ok).toBe(true)
  expect(paneOf(doc)).toContain('Run release verify')
  expect(parseReader(JSON.stringify(docOf('release', ['plan','verify','reflect']))).ok).toBe(false)
})
