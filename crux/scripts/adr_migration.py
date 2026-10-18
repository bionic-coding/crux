"""Prospective ADR migration preparation. No public reader admits these candidates.

All paths in bindings are repository-relative. Council subjects remain relative
under the configured documentation root. The package's inline clause map is
reviewed data alongside the human record, never an inferred TXT translation.
"""
from __future__ import annotations

from copy import deepcopy
from contextlib import contextmanager
import contextvars
from datetime import datetime
import json
from pathlib import Path
import re

import yaml
from council_records import _validator, git
from cycle_workflow import CycleError, atomic, contained, digest, encoded, now, tree

FORMATS = {kind: f'crux.adr-migration-{kind}.v1' for kind in
           ('queue', 'package', 'approval', 'policy', 'publication')}
POLICIES = {'council-and-human', 'council-only'}
READINESS_INVENTORY = ('crux/scripts/adr_migration.py','crux/scripts/adr-migration.py',
    'crux/scripts/cycle_council.py','crux/scripts/cycle-council.py','crux/scripts/decision_policy.py',
    *(f'crux/schemas/adr-migration-{kind}.schema.json' for kind in FORMATS))
# U1's committed bootstrap inventory stays frozen. Later installed support
# additionally binds U2's admission and current-authority interpretation.
INSTALLED_INVENTORY = READINESS_INVENTORY + tuple('crux/scripts/'+name for name in (
    'adr_migration_publication.py','implementation_migration.py','implementation_approval.py',
    'summaries_projection.py','doctrine_projection.py'))
SLUG = re.compile(r'^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$')
COMMIT = re.compile(r'^(?:[0-9a-f]{40}|[0-9a-f]{64})$')
# ADR Decision 9 has one explicit named record. Narrow extraction establishes
# identity only, never interprets the record's prose as an owner instruction.
BOOTSTRAP = re.compile(r'This decision names `([^`]+)` at sha256 `([0-9a-f]{64})`\.')
_STANDING_BASIS = contextvars.ContextVar('migration_prepublication_standing', default=None)
_OWNER_EXCEPTION = contextvars.ContextVar('initial_migration_owner_exception', default=None)
_PUBLISHED_OBJECTIVES = contextvars.ContextVar('published_migration_objectives', default=None)


@contextmanager
def published_objectives(repo, package_path, parent):
    """Replay one admitted assessment's objectives from its immutable parent.

    Only publication admission uses this scope. Source clauses, approvals and
    other dependencies remain current and exact. Pending assessments never enter it.
    """
    package=load(repo,package_path,'package')
    refs=[r for r in package['dependencies'] if r['kind']=='objectives']
    expected=(tree(repo).docs_root/'objectives.md').relative_to(Path(repo).resolve()).as_posix()
    if len(refs)!=1 or refs[0]['path']!=expected:
        raise CycleError('package requires the configured objectives binding')
    raw=blob(repo,parent,expected)
    if digest(raw)!=refs[0]['sha256']:
        raise CycleError('published objectives differ from the approved historical assessment')
    token=_PUBLISHED_OBJECTIVES.set((Path(repo).resolve(),refs[0],raw))
    try:yield
    finally:_PUBLISHED_OBJECTIVES.reset(token)


def validate_owner_exception(repo, ref):
    """One explicit initial-migration route; never a general council override.

    This external, owner-authored provenance has no package backlink. Final
    disposition approval must independently bind both exact objects below.
    """
    if isinstance(ref,str):ref=binding(repo,ref)
    if not isinstance(ref,dict) or set(ref)!={'path','sha256'}:raise CycleError('invalid initial owner exception binding')
    cfg=tree(repo)
    expected=(cfg.docs_root/'adrs/migrations/exceptions/adr-0160-initial-owner-override.json').relative_to(cfg.repo_root).as_posix()
    if ref['path']!=expected:raise CycleError('initial owner exception must use its one canonical path')
    value=json.loads(bound_bytes(repo,ref))
    required={'format','id','cycle_id','package','governing_adr','original_record','original_package','council',
        'owner_authorization','exceptions','final_owner_approval_required','default_policy_changed','council_approved'}
    if (set(value)!=required or value['format']!='crux.adr-migration-owner-exception.v1' or
        value['id']!='adr-0160-initial-owner-override' or value['cycle_id']!='CYC-0007' or
        value['exceptions']!=['revise-initial-record-without-new-adr','initial-council-veto-owner-resolution'] or
        value['final_owner_approval_required'] is not True or value['default_policy_changed'] is not False or
        value['council_approved'] is not False):
        raise CycleError('initial owner exception exceeds its authorized scope')
    for key in ('package','governing_adr','original_record','original_package','council'):
        if not isinstance(value[key],dict) or set(value[key])!={'path','sha256'}:raise CycleError('invalid exception content binding')
        bound_bytes(repo,value[key])
    old=load(repo,value['original_package']['path'],'package')
    package=load(repo,value['package']['path'],'package')
    if (old['id']!='adr-0160-initial-review-displacement' or not old['initial'] or not package['initial'] or
        package['id']!='adr-0160-initial-review-displacement-v2' or
        value['original_record']!=old['record'] or
        old['governing_adr']!=package['governing_adr'] or value['governing_adr']!=package['governing_adr']['source']):
        raise CycleError('owner exception is not the corrected initial migration package')
    receipt=_governing(repo,package)
    if receipt['adr']!='ADR-0160' or BOOTSTRAP.findall(receipt['proposed_text'])!=[
        (value['original_record']['path'],value['original_record']['sha256'])]:
        raise CycleError('owner exception does not preserve the original accepted ADR and record')
    owner=value['owner_authorization']
    if (not isinstance(owner,dict) or set(owner)!={'origin','quote','conversation','context_commit'} or
        owner['origin']!='owner-conversation' or not all(isinstance(owner[k],str) and owner[k].strip()
            for k in ('quote','conversation','context_commit'))):
        raise CycleError('initial exception lacks the explicit scoped owner instruction')
    ancestor(repo,owner['context_commit'],_git(repo,'rev-parse','HEAD').decode().strip())
    return ref,value


@contextmanager
def owner_exception_scope(repo, ref=None):
    if ref is None:
        yield
        return
    selected=validate_owner_exception(repo,ref)
    token=_OWNER_EXCEPTION.set(selected)
    try:yield
    finally:_OWNER_EXCEPTION.reset(token)


def _selected_exception(repo, package_path):
    selected=_OWNER_EXCEPTION.get()
    if selected is not None and selected[1]['package']==binding(repo,package_path):return selected
    return None


def _exception_owner(owner,presented,ref):
    if not isinstance(owner,dict) or owner.get('owner_exception')!=ref:
        raise CycleError('fresh owner disposition approval must bind package and owner exception')
    return validate_owner({k:v for k,v in owner.items() if k!='owner_exception'},presented,'approve-dispositions')


def validate_schema(value, kind):
    if kind not in FORMATS or not isinstance(value, dict) or value.get('format') != FORMATS[kind]:
        raise CycleError(f'unsupported prospective migration {kind} format')
    validator = _validator()
    schema = validator.load_schema(Path(__file__).parent.parent / f'schemas/adr-migration-{kind}.schema.json')
    errors = []
    validator.validate(value, schema, '#', '#', errors, kind)
    if errors:
        raise CycleError(f'invalid migration {kind}: {errors[0]}')
    return value


def slug(identity):
    if not isinstance(identity, str) or not SLUG.fullmatch(identity):
        raise CycleError('migration identity must be a closed kebab-case slug')
    return identity


def read(repo, path):
    target = contained(Path(repo).resolve(), path)
    if not target.is_file() or target.stat().st_size > 2_000_000:
        raise CycleError('migration input must be a bounded regular file')
    return target.read_bytes()


def binding(repo, path):
    return {'path': path, 'sha256': digest(read(repo, path))}


def bound_bytes(repo, ref):
    frozen=_PUBLISHED_OBJECTIVES.get()
    if frozen is not None and frozen[0]==Path(repo).resolve() and frozen[1]==ref:
        return frozen[2]
    raw = read(repo, ref['path'])
    if digest(raw) != ref['sha256']:
        raise CycleError(f'migration input changed: {ref["path"]}')
    return raw


def load(repo, path, kind):
    try:
        return validate_schema(json.loads(read(repo, path)), kind)
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise CycleError(f'invalid migration {kind}: {type(exc).__name__}') from exc


def _git(repo, *args):
    result = git(repo, *args)
    if result.returncode:
        raise CycleError('required migration Git evidence is unavailable')
    return result.stdout


def full_commit(repo, commit):
    if not isinstance(commit, str) or not COMMIT.fullmatch(commit):
        raise CycleError('readiness/policy basis requires a full commit identifier')
    resolved = _git(repo, 'rev-parse', '--verify', commit + '^{commit}').decode().strip()
    if resolved != commit:
        raise CycleError('commit identity mismatch')
    return commit


def blob(repo, commit, path):
    full_commit(repo, commit)
    contained(Path(repo).resolve(), path)
    # A Git symlink is not an immutable regular-file input either.
    entry = _git(repo, 'ls-tree', commit, '--', path).decode()
    if not entry.startswith(('100644 ', '100755 ')):
        raise CycleError('committed migration input is not a regular file')
    return _git(repo, 'show', f'{commit}:{path}')


def ancestor(repo, before, after):
    full_commit(repo, before); full_commit(repo, after)
    if git(repo, 'merge-base', '--is-ancestor', before, after).returncode:
        raise CycleError('readiness/policy basis is not an ancestor of the action')


def introduction(repo, path):
    """Find the most recent addition of this exact current record; reject edits.

    Immutable approval/council bytes must still match their introducing commit.
    This also refuses an uncommitted or subsequently edited receipt.
    """
    contained(Path(repo).resolve(), path)
    commits = _git(repo, 'log', '--first-parent', '--format=%H', '--diff-filter=A', 'HEAD', '--', path).decode().splitlines()
    if not commits:
        raise CycleError('migration evidence must be committed before use')
    commit = commits[0]
    if blob(repo, commit, path) != read(repo, path):
        raise CycleError('committed migration evidence was edited after introduction')
    return commit


def validate_readiness(repo, readiness, *, action_commit=None, initial=True):
    """Inspect committed source plus recorded check and independent review bytes.

    Shared .git test receipts alone are insufficient. Committed summaries bind the
    actual commands, passing results and tested source hashes at this checkpoint.
    """
    if isinstance(readiness,dict) and readiness.get('format')=='crux.adr-migration-installed-support.v1':
        if initial:raise CycleError('initial bootstrap requires committed U1 readiness')
        if set(readiness)!={'format','sources'}:raise CycleError('invalid installed support basis')
        plugin=Path(__file__).resolve().parent.parent
        expected={p.removeprefix('crux/') for p in INSTALLED_INVENTORY}
        if {r.get('path') for r in readiness['sources']}!=expected:raise CycleError('installed implementation inventory is incomplete')
        for ref in readiness['sources']:
            raw=contained(plugin,ref['path']).read_bytes()
            if digest(raw)!=ref['sha256']:raise CycleError('installed support source changed')
        for kind in FORMATS:
            _validator().load_schema(plugin/f'schemas/adr-migration-{kind}.schema.json')
        return readiness
    if not isinstance(readiness, dict) or set(readiness) != {'commit', 'sources', 'tests', 'review'}:
        raise CycleError('committed U1 readiness source/test/review evidence required')
    basis = full_commit(repo, readiness['commit'])
    ancestor(repo, basis, action_commit or _git(repo, 'rev-parse', 'HEAD').decode().strip())
    sources = readiness['sources']
    if not set(READINESS_INVENTORY).issubset({s.get('path') for s in sources if isinstance(s,dict)}):
        raise CycleError('readiness is missing required U1 implementation inventory')
    if not sources or not readiness['tests']:
        raise CycleError('readiness requires source and passing test evidence')
    def committed(ref):
        raw = blob(repo, basis, ref['path'])
        if digest(raw) != ref['sha256']:
            raise CycleError('readiness evidence does not match committed bytes')
        return raw
    for ref in sources: committed(ref)
    covered = set()
    for ref in readiness['tests']:
        test = json.loads(committed(ref))
        if test.get('result') != 'passed' or not isinstance(test.get('command'), list) or not test['command']:
            raise CycleError('readiness test evidence did not pass')
        for source in test.get('inputs', []):
            committed(source); covered.add((source['path'], source['sha256']))
    if not {(s['path'], s['sha256']) for s in sources}.issubset(covered):
        raise CycleError('readiness tests do not cover the verified source bindings')
    review = json.loads(committed(readiness['review']))
    if review.get('verdict') != 'approve' or not review.get('reviewer') or not review.get('implementers') or review['reviewer'] in review['implementers']:
        raise CycleError('readiness lacks approving independent review')
    reviewed = {(s['path'], s['sha256']) for s in review.get('inputs', [])}
    if not {(s['path'], s['sha256']) for s in sources}.issubset(reviewed):
        raise CycleError('readiness review does not bind the verified sources')
    for source in review['inputs']: committed(source)
    return readiness


def _governing(repo, package):
    from decision_policy import validate_receipt_data
    source = package['governing_adr']['source']
    receipt = json.loads(read(repo, package['governing_adr']['receipt']))
    cfg = tree(repo)
    path = contained(cfg.repo_root, source['path'])
    if not path.is_relative_to(cfg.docs_root):
        raise CycleError('governing ADR must belong to configured documentation tree')
    subject = path.relative_to(cfg.docs_root).as_posix()
    expected_receipt=(cfg.docs_root/f'adrs/acceptances/{receipt["adr"]}.json').relative_to(cfg.repo_root).as_posix()
    if package['governing_adr']['receipt']!=expected_receipt:
        raise CycleError('governing ADR receipt must use its canonical identity path')
    council = read(repo, (cfg.docs_root / receipt['council']).relative_to(cfg.repo_root).as_posix())
    from cycle_council import docs_proof_reader
    validate_receipt_data(receipt, subject, council,proof_reader=docs_proof_reader(cfg))
    if 'migration_package' in receipt:
        validate_package_acceptance_data(repo,receipt)
    if source['sha256'] not in {receipt['proposed_sha256'], receipt['accepted_sha256']}:
        raise CycleError('package does not bind the reviewed governing ADR revision')
    if digest(read(repo, source['path'])) != receipt['accepted_sha256']:
        raise CycleError('governing ADR changed after acceptance')
    return receipt


def _source(repo, ref, package, receipt):
    governing = package['governing_adr']['source']
    if ref['path'] == governing['path']:
        if ref['sha256'] not in {receipt['proposed_sha256'], receipt['accepted_sha256']}:
            raise CycleError('source does not match validated ADR lifecycle bridge')
        return receipt['accepted_text'].encode()
    return bound_bytes(repo, ref)


def _clause(repo, clause, package, receipt, *, successor=False):
    from decision_policy import frontmatter
    front, _ = frontmatter(_source(repo, clause['source'], package, receipt).decode())
    cfg=tree(repo)
    path=contained(cfg.repo_root,clause['source']['path'])
    from council_records import tree_adr_path
    identity=tree_adr_path(repo).fullmatch(clause['source']['path'])
    if (path.parent != cfg.docs_root/'adrs' or identity is None or identity['id'] != front.get('id') or
        not clause['handle'].startswith(front.get('id','')+'/') or 'record_type' in front or front.get('type') in {'idr','implementation-decision'}):
        raise CycleError('clause source must be an active architectural decision with matching identity')
    if clause['source']['path'] != package['governing_adr']['source']['path'] and front.get('acceptance_format'):
        from decision_policy import validate_acceptance
        validate_acceptance(cfg,{'path':path.relative_to(cfg.docs_root).as_posix()})
    matches = [r for r in front.get('governs', []) if r.get('handle') == clause['handle']]
    if front.get('status') != 'Accepted' or len(matches) != 1 or digest(encoded(matches[0])) != clause['clause_sha256']:
        raise CycleError('source/successor clause is not the exact accepted rule')
    return matches[0]


def validate_owner(owner, presented, action):
    if not isinstance(owner, dict) or set(owner) != {'origin','quote','action','at','conversation','presented'}:
        raise CycleError('explicit owner conversation approval with provenance required')
    if owner['origin'] != 'owner-conversation' or owner['action'] != action or owner['presented'] != presented:
        raise CycleError('owner instruction approves different content, origin or action')
    if not all(isinstance(owner[k], str) and owner[k].strip() for k in ('quote','at','conversation')):
        raise CycleError('owner instruction lacks quote/date/conversation provenance')
    try:datetime.fromisoformat(owner['at'].replace('Z','+00:00'))
    except ValueError as exc:raise CycleError('owner instruction requires an actual date') from exc
    return owner


def _graph(items):
    names = [i['id'] for i in items]
    if len(set(names)) != len(names): raise CycleError('duplicate migration item identity')
    graph = {i['id']: i['depends_on'] for i in items}
    def visit(node, seen):
        if node in seen: raise CycleError('migration dependencies contain a cycle')
        for dep in graph[node]:
            if dep not in graph: raise CycleError('migration dependency does not exist')
            visit(dep, seen | {node})
    for node in graph: visit(node, set())
    return graph


def validate_stops(stops, items):
    names = {i['id'] for i in items}
    for stop in stops:
        if not set(stop['items']).issubset(names): raise CycleError('owner stop references unknown item')
        instruction = stop['instruction']
        validate_owner(instruction, instruction['presented'], 'stop')
        if stop['resolution'] is None:
            raise CycleError('outstanding owner stop blocks the affected package')
        validate_owner(stop['resolution'], instruction['presented'], 'clear-stop')


def current_standing(repo):
    """Use the existing interpretation of retirements, provenance and history."""
    if _STANDING_BASIS.get() is not None:
        return deepcopy(_STANDING_BASIS.get())
    import summaries_projection as summaries
    import implementation_migration as historical
    cfg=tree(repo)
    try:
        records=summaries.collect_records(cfg.docs_root/'adrs')
        facts=historical.authority_view(repo)
        records=summaries._summary_authority_records(records,facts,{}, {})['records']
        rows=summaries.live_records(records)
        provenance,_=summaries.read_provenance(cfg.docs_root/'adrs')
        standing=summaries.provenance_standing(provenance,rows)
        displaced=set(facts['historical_handles'])|set(facts['retired_handles'])
        return {r['handle']:r for r in rows if r['source_status']=='Accepted' and
            r['handle'] not in displaced and standing.get(r['handle'],{}).get('standing','binding')=='binding'
            and not standing.get(r['handle'],{}).get('in_run_edit')}
    except (ValueError, OSError) as exc:
        raise CycleError('current governing standing could not be validated') from exc


def validate_package(repo, path):
    package = load(repo, path, 'package'); slug(package['id']); _graph(package['items'])
    receipt = _governing(repo, package)
    raw_record = bound_bytes(repo, package['record'])
    matches = BOOTSTRAP.findall(receipt['proposed_text'])
    if len(matches) > 1: raise CycleError('ambiguous initial record identity in governing ADR')
    initial = False
    if matches:
        name, sha = matches[0]
        same_path = package['record']['path'] == name
        same_hash = package['record']['sha256'] == sha
        selected=_selected_exception(repo,path)
        if same_path != same_hash and selected is None:
            raise CycleError('initial bootstrap record identity changed or relocated')
        initial = same_path and same_hash
        if selected is not None:initial=True
    if package['initial'] != initial:
        raise CycleError('initial bootstrap identity differs from governing ADR')
    objectives = [d for d in package['dependencies'] if d['kind'] == 'objectives']
    if len(objectives) != 1 or objectives[0]['path'] != (tree(repo).docs_root/'objectives.md').relative_to(tree(repo).repo_root).as_posix():
        raise CycleError('package requires the configured objectives binding')
    for dep in package['dependencies']:
        raw = _source(repo, dep, package, receipt)
        if dep['kind'] == 'objectives':
            from decision_policy import frontmatter
            front, body = frontmatter(raw.decode())
            if front.get('maturity') == 'placeholder' or not body.strip(): raise CycleError('objectives are still a placeholder')
    live = current_standing(repo)
    def effective_dependencies(handle):
        for amender in live[handle].get('amended_by',[]):
            identity=amender.split('/')[0]
            cfg=tree(repo)
            paths=list((cfg.docs_root/'adrs').glob(identity+'-*.md'))
            if len(paths)!=1:raise CycleError('effective amender source is unavailable')
            name=paths[0].relative_to(cfg.repo_root).as_posix()
            if name==package['governing_adr']['source']['path']:continue
            if not any(d['path']==name for d in package['dependencies']):
                raise CycleError('effective amender source must be a bound material dependency')
    for item in package['items']:
        if item['handle'] not in live:
            raise CycleError('source is not a current governing architectural clause')
        effective_dependencies(item['handle'])
        _clause(repo, item, package, receipt)
        if item['disposition'] in {'replace','amend'} and not item['successors']:
            raise CycleError('replacement/amendment requires a successor rule')
        if item['disposition'] == 'retain' and (item['ceasing'] or item['successors']):
            raise CycleError('retained rule cannot displace obligations')
        for successor in item['successors']:
            if successor['handle'] not in live:
                raise CycleError('successor is not a current governing architectural clause')
            effective_dependencies(successor['handle'])
            _clause(repo, successor, package, receipt, successor=True)
    validate_stops(package['owner_stops'], package['items'])
    return package


def review_bundle(repo, path):
    """Bind and transmit every referenced byte, not merely the package's hashes."""
    return _review_bundle(repo,path,validate_package(repo,path))


def _review_bundle(repo,path,package):
    """Render bytes from this invocation's already validated exact package."""
    receipt = _governing(repo, package)
    refs = [package['record'], package['governing_adr']['source'], binding(repo,package['governing_adr']['receipt']), *package['dependencies']]
    for item in package['items']:
        refs.append(item['source']); refs.extend(s['source'] for s in item['successors'])
    contents = {}
    import secret_scan
    for ref in refs:
        if secret_scan.check_input_path(contained(Path(repo).resolve(),ref['path']),Path(repo).resolve()):
            raise CycleError('council bound input path refused')
        raw = _source(repo, ref, package, receipt)
        # Show the reviewed bytes when the binding names Proposed, plus the exact
        # acceptance receipt, which carries both texts and the proved bridge.
        if ref['path'] == package['governing_adr']['source']['path'] and ref['sha256'] == receipt['proposed_sha256']:
            raw = receipt['proposed_text'].encode()
        contents[ref['path'] + '@' + ref['sha256']] = raw.decode()
    return {'package_path':path,'package_sha256':digest(read(repo,path)), 'package_bytes':read(repo,path).decode(),'bound_contents':contents}


def _package_bundle_inputs(repo,path):
    """A lexical supplier owned by one action; never shared between calls."""
    result=None
    def collect():
        nonlocal result
        if result is None:
            package=validate_package(repo,path)
            result=package,_review_bundle(repo,path,package)
        return result
    return collect


def _readiness_sources_at(repo, readiness, basis):
    for source in readiness.get('sources',[]):
        if source['path'] in READINESS_INVENTORY and digest(blob(repo,basis,source['path']))!=source['sha256']:
            raise CycleError('final approval readiness differs from its prior validator checkpoint')


def validate_evidence(repo, package_path, council, *, readiness, initial, policy, owner, source_basis=None):
    """Pure approval-policy matrix; initial/policy are resolved by the caller.

    Public validation derives initial from the frozen governing source and policy
    from the action's first parent. This helper never admits governing authority.
    """
    return _validate_evidence(repo,package_path,council,readiness=readiness,initial=initial,
        policy=policy,owner=owner,source_basis=source_basis,_inputs=_package_bundle_inputs(repo,package_path))


def _validate_evidence(repo,package_path,council,*,readiness,initial,policy,owner,source_basis=None,_inputs):
    if policy not in POLICIES: raise CycleError('unsupported migration acceptance policy')
    from cycle_council import validate_record
    cfg = tree(repo)
    subject = contained(cfg.repo_root, package_path).relative_to(cfg.docs_root).as_posix()
    selected=_selected_exception(repo,package_path)
    if selected is None:
        from cycle_council import docs_proof_reader
        validate_record(council, purpose='disposition', subject=subject, subject_sha256=digest(read(repo,package_path)),proof_reader=docs_proof_reader(cfg))
    else:
        ref,exception=selected
        if digest(encoded(council))!=exception['council']['sha256']:
            raise CycleError('owner exception names another actual council record')
        payload=dict(council);checksum=payload.pop('record_sha256',None)
        old=exception['original_package'];old_subject=contained(cfg.repo_root,old['path']).relative_to(cfg.docs_root).as_posix()
        seats=council.get('seats',[])
        if (checksum!=digest(encoded(payload)) or council.get('format')!='crux.cycle-council' or
            council.get('purpose')!='disposition' or council.get('cycle_id')!='CYC-0007' or
            council.get('subject')!=old_subject or council.get('subject_sha256')!=old['sha256'] or
            council.get('outcome')!='changes-required' or len(seats)!=3 or len({s.get('provider') for s in seats})!=3 or
            any(s.get('errored') for s in seats)):
            raise CycleError('scoped exception does not bind the original completed council veto')
        _exception_owner(owner,binding(repo,package_path),ref)
        if council.get('review_bundle_sha256')!=digest(encoded(review_bundle(repo,old['path']))):
            raise CycleError('original council review proof inputs changed')
    if selected is None and council.get('readiness') != readiness: raise CycleError('council readiness basis differs from approval')
    if selected is not None:
        council_commit=introduction(repo,selected[1]['council']['path'])
        validate_readiness(repo,council.get('readiness'),action_commit=council_commit,initial=True)
        # The failed council retains its original support. Final owner approval
        # uses separately committed, tested and reviewed corrected validators.
        _readiness_sources_at(repo,readiness,source_basis or _git(repo,'rev-parse','HEAD').decode().strip())
    if selected is None and (initial or policy == 'council-and-human'):
        validate_owner(owner, binding(repo, package_path), 'approve-dispositions')
    package,bundle = _inputs()
    validate_readiness(repo, readiness, initial=initial)
    if selected is None and council.get('review_bundle_sha256')!=digest(encoded(bundle)):
        raise CycleError('disposition council review proof inputs changed')
    return package


def package_owner_instructions(repo, package_path, owner):
    validate_owner(owner,binding(repo,package_path),'accept-adr-and-approve-dispositions')
    return {'acceptance':dict(owner,action='accept-adr'),
            'disposition':dict(owner,action='approve-dispositions')}


def accept_package(repo, package_path, council, *, owner=None):
    """Accept a new ADR from an exact package under its already committed policy.

    This writes the ADR acceptance record alone. Dispositions still require their
    own council and receipt; initial bootstrap always requires separate owner scope.
    """
    from decision_policy import accept, frontmatter
    package=load(repo,package_path,'package')
    bound_bytes(repo,package['record'])
    for dep in package['dependencies']:bound_bytes(repo,dep)
    source=package['governing_adr']['source'];raw=bound_bytes(repo,source)
    front,_=frontmatter(raw.decode())
    if front.get('status')!='Proposed':raise CycleError('package acceptance applies only to a new Proposed ADR')
    cfg=tree(repo);path=contained(cfg.repo_root,source['path'])
    if path.parent!=cfg.docs_root/'adrs':raise CycleError('package ADR must be an active decision file')
    head=_git(repo,'rev-parse','HEAD').decode().strip();policy=policy_at(repo,head)
    if owner is not None:validate_owner(owner,binding(repo,package_path),'accept-adr-and-approve-dispositions')
    if policy=='council-and-human' and owner is None:raise CycleError('explicit owner package acceptance required')
    return accept(repo,path.relative_to(cfg.docs_root).as_posix(),council,
        human_approval=owner['quote'] if owner else None,policy_basis=head,
        migration_package=binding(repo,package_path),migration_owner=owner)


def validate_package_acceptance_data(repo, receipt, *, action_commit=None, pending=False):
    """Additional prospective package policy evidence; ordinary receipts stay unchanged."""
    if 'migration_package' not in receipt:raise CycleError('not a prospective package acceptance receipt')
    bound_bytes(repo,receipt['migration_package'])
    package=load(repo,receipt['migration_package']['path'],'package')
    if package['governing_adr']['source']['sha256'] not in {receipt['proposed_sha256'],receipt['accepted_sha256']}:
        raise CycleError('package acceptance does not bind its reviewed ADR source')
    if action_commit is None and not pending:
        cfg=tree(repo)
        relative=(cfg.docs_root/f'adrs/acceptances/{receipt["adr"]}.json').relative_to(cfg.repo_root).as_posix()
        action_commit=introduction(repo,relative)
    parent=(_git(repo,'rev-parse',action_commit+'^1').decode().strip() if action_commit else _git(repo,'rev-parse','HEAD').decode().strip())
    if receipt.get('policy_basis')!=parent or receipt['policy']!=policy_at(repo,parent):
        raise CycleError('package acceptance policy was not in force before its action')
    if receipt.get('migration_owner') is not None:
        validate_owner(receipt['migration_owner'],receipt['migration_package'],'accept-adr-and-approve-dispositions')
    elif receipt['policy']=='council-and-human':raise CycleError('package acceptance lacks explicit owner provenance')
    return receipt


def validate_package_acceptance(repo, package_path, *, committed=True):
    package=load(repo,package_path,'package')
    receipt=json.loads(read(repo,package['governing_adr']['receipt']))
    from decision_policy import validate_receipt_data
    cfg=tree(repo)
    council=read(repo,(cfg.docs_root/receipt['council']).relative_to(cfg.repo_root).as_posix())
    from cycle_council import docs_proof_reader
    validate_receipt_data(receipt,receipt['subject'],council,proof_reader=docs_proof_reader(cfg))
    validate_package_acceptance_data(repo,receipt,pending=not committed)
    if digest(read(repo,package['governing_adr']['source']['path']))!=receipt['accepted_sha256']:
        raise CycleError('accepted package ADR changed')
    return receipt


def installed_support():
    plugin=Path(__file__).resolve().parent.parent
    return {'format':'crux.adr-migration-installed-support.v1','sources':[
        {'path':name.removeprefix('crux/'),'sha256':digest((plugin/name.removeprefix('crux/')).read_bytes())}
        for name in INSTALLED_INVENTORY]}


def policy_at(repo, commit):
    """Read policy and attributed instruction from already committed parent bytes."""
    full_commit(repo, commit)
    result = git(repo, 'show', f'{commit}:.bionic.yml')
    config = yaml.safe_load(result.stdout) if not result.returncode else {}
    policy = (config or {}).get('adr', {}).get('acceptance', 'council-and-human')
    if policy not in POLICIES: raise CycleError('unsupported migration acceptance policy')
    cfg = tree(repo)
    directory = (cfg.docs_root/'adrs/migrations/policies').relative_to(cfg.repo_root).as_posix()
    records = _git(repo, 'ls-tree', '-r', '--name-only', commit, '--', directory).decode().splitlines()
    instructions = []
    for path in records:
        record = validate_schema(json.loads(blob(repo,commit,path)), 'policy')
        validate_owner(record['instruction'], record['instruction']['presented'], 'change-policy')
        if record['pending_action'] is not None: raise CycleError('policy change cannot weaken its own pending action')
        introduced = introduction(repo,path); parent = _git(repo,'rev-parse',introduced+'^1').decode().strip()
        before_raw = git(repo,'show',f'{parent}:.bionic.yml')
        before_config = yaml.safe_load(before_raw.stdout) if not before_raw.returncode else {}
        before = (before_config or {}).get('adr',{}).get('acceptance','council-and-human')
        if record['previous_policy'] != before: raise CycleError('policy instruction does not bind previous policy')
        changed = _git(repo,'show',f'{introduced}:.bionic.yml')
        presented = {'path':'.bionic.yml','sha256':digest(changed)}
        validate_owner(record['instruction'],presented,'change-policy')
        introduced_config=yaml.safe_load(changed) or {}
        if introduced_config.get('adr',{}).get('acceptance','council-and-human')!=record['policy']:
            raise CycleError('policy instruction does not match its configuration')
        if record['policy'] == policy: instructions.append((record,introduced))
    if policy != 'council-and-human' and not instructions:
        raise CycleError('configured policy requires an earlier explicit owner instruction')
    # Find the last actual policy transition, ignoring unrelated config edits.
    revisions=_git(repo,'rev-list','--first-parent',commit,'--','.bionic.yml').decode().splitlines()
    for revision in revisions:
        parents=git(repo,'rev-parse',revision+'^1')
        old={}
        if not parents.returncode:
            old_raw=git(repo,'show',parents.stdout.decode().strip()+':.bionic.yml')
            old=yaml.safe_load(old_raw.stdout) if not old_raw.returncode else {}
        new_raw=git(repo,'show',revision+':.bionic.yml')
        new=yaml.safe_load(new_raw.stdout) if not new_raw.returncode else {}
        if (old or {}).get('adr',{}).get('acceptance','council-and-human') != (new or {}).get('adr',{}).get('acceptance','council-and-human'):
            if not any(git(repo,'merge-base','--is-ancestor',revision,introduced).returncode==0 for _,introduced in instructions):
                raise CycleError('latest policy change lacks an owner instruction')
            break
    return policy


def record_policy(repo, identity, policy, instruction, *, pending_action=None):
    """Record a faithful owner instruction for a separately approved config edit.

    The config and record are committed together; an approval in that same commit
    still reads its first parent and cannot use the changed policy.
    """
    slug(identity)
    if pending_action is not None:
        raise CycleError('policy change cannot weaken its own pending action')
    head=_git(repo,'rev-parse','HEAD').decode().strip()
    previous_raw=git(repo,'show',f'{head}:.bionic.yml')
    previous_config=yaml.safe_load(previous_raw.stdout) if not previous_raw.returncode else {}
    previous=(previous_config or {}).get('adr',{}).get('acceptance','council-and-human')
    current=yaml.safe_load(read(repo,'.bionic.yml')) or {}
    if current.get('adr',{}).get('acceptance','council-and-human')!=policy:
        raise CycleError('policy instruction does not match the presented configuration')
    validate_owner(instruction,binding(repo,'.bionic.yml'),'change-policy')
    record={'format':FORMATS['policy'],'id':identity,'policy':policy,'previous_policy':previous,'instruction':instruction,'pending_action':None}
    validate_schema(record,'policy')
    path=_record_path(repo,'policies',identity)
    if path.exists() and read(repo,path.relative_to(Path(repo).resolve()).as_posix())!=encoded(record):
        raise CycleError('policy instruction already exists with other content')
    atomic(path,record);return record


def validate_approval_data(repo, approval, *, action_commit=None):
    with owner_exception_scope(repo,approval.get('owner_exception')):
        return _validate_approval_data(repo,approval,action_commit=action_commit)


def _validate_approval_data(repo, approval, *, action_commit=None, _inputs=None):
    validate_schema(approval,'approval')
    bound_bytes(repo, approval['package']); raw = bound_bytes(repo,approval['council'])
    if action_commit:
        full_commit(repo,action_commit)
        parent = _git(repo,'rev-parse',action_commit+'^1').decode().strip()
    else:
        parent = _git(repo,'rev-parse','HEAD').decode().strip()
    if approval['policy_basis'] != parent: raise CycleError('approval policy must come from before the action commit')
    policy = policy_at(repo,parent)
    if policy != approval['policy']: raise CycleError('approval names a policy not in force before its action')
    if _inputs is None:_inputs=_package_bundle_inputs(repo,approval['package']['path'])
    package,bundle = _inputs()
    selected=_selected_exception(repo,approval['package']['path'])
    if selected is not None and approval.get('owner_exception')!=selected[0]:
        raise CycleError('approval must explicitly bind its owner exception')
    if approval.get('owner_exception'):
        exception_commit=introduction(repo,approval['owner_exception']['path'])
        if action_commit:
            if exception_commit==action_commit:raise CycleError('owner exception must precede approval')
            ancestor(repo,exception_commit,action_commit)
    council_commit = introduction(repo,approval['council']['path'])
    # Readiness must predate both introducing commits. Equal basis is not enough.
    checks=((council_commit, json.loads(raw).get('readiness')),
            (action_commit,approval['readiness'])) if selected is not None else (
            (council_commit,approval['readiness']),(action_commit,approval['readiness']))
    for commit,proof in checks:
        if commit:
            if commit == proof.get('commit'): raise CycleError('readiness must precede council and approval records')
            validate_readiness(repo,proof,action_commit=commit,initial=package['initial'])
    if approval['review_bundle_sha256']!=digest(encoded(bundle)):
        raise CycleError('approval review proof inputs changed')
    _validate_evidence(repo,approval['package']['path'],json.loads(raw),readiness=approval['readiness'],initial=package['initial'],policy=policy,owner=approval['owner'],source_basis=parent,_inputs=_inputs)
    return approval


def validate_approval(repo, path, *, committed=True):
    approval = load(repo,path,'approval')
    return validate_approval_data(repo,approval,action_commit=introduction(repo,path) if committed else None)


def record_approval(repo, identity, package_path, council_path, readiness, *, owner=None):
    slug(identity)
    path = _record_path(repo,'approvals',identity)
    if path.exists():
        previous = load(repo,path.relative_to(Path(repo).resolve()).as_posix(),'approval')
        if (previous['package'] != binding(repo,package_path) or
            previous['council'] != binding(repo,council_path) or
            previous['readiness'] != readiness or previous['owner'] != owner):
            raise CycleError('existing approval binds another package or provenance')
        relative=path.relative_to(Path(repo).resolve()).as_posix()
        tracked=git(repo,'ls-files','--error-unmatch','--',relative).returncode==0
        validate_approval(repo,relative,committed=tracked)
        return previous
    parent = _git(repo,'rev-parse','HEAD').decode().strip()
    inputs=_package_bundle_inputs(repo,package_path)
    approval = {'format':FORMATS['approval'],'id':identity,'package':binding(repo,package_path),'council':binding(repo,council_path),
        'readiness':readiness,'review_bundle_sha256':digest(encoded(inputs()[1])),'policy':policy_at(repo,parent),'policy_basis':parent,'owner':owner,'at':now()}
    if _selected_exception(repo,package_path):approval['owner_exception']=_OWNER_EXCEPTION.get()[0]
    with owner_exception_scope(repo,approval.get('owner_exception')):
        _validate_approval_data(repo,approval,_inputs=inputs)
    atomic(path,approval)
    return approval


def _record_path(repo, directory, identity):
    slug(identity)
    return contained(tree(repo).docs_root, f'adrs/migrations/{directory}/{identity}.json')


def create_queue(repo, identity, items, *, owner_stops=None):
    queue = {'format':FORMATS['queue'],'id':slug(identity),'items':deepcopy(items),'owner_stops':owner_stops or [],'history':[]}
    validate_schema(queue,'queue'); _graph(items)
    for item in items:
        for ref in item['bindings']: bound_bytes(repo,ref)
    path = _record_path(repo,'queues',identity)
    if path.exists(): raise CycleError('migration queue already exists')
    atomic(path,queue); return queue


def load_queue(repo, path):
    if Path(path).name=='.bionic.yml':raise CycleError('queue cannot write acceptance configuration')
    queue = load(repo,path,'queue'); _graph(queue['items'])
    if contained(Path(repo).resolve(),path)!=_record_path(repo,'queues',queue['id']):
        raise CycleError('queue write scope requires its canonical migration path')
    return queue


def queue_page(repo, path, *, size=5, offset=0):
    if type(size) is not int or size<1 or type(offset) is not int or offset<0:
        raise CycleError('page size must be positive and offset nonnegative')
    queue=load_queue(repo,path)
    return {'id':queue['id'],'total':len(queue['items']),'offset':offset,
            'items':queue['items'][offset:offset+size]}


def render_evidence(repo,path):
    from untrusted import redact
    text=redact(read(repo,path).decode(),limit=4000)
    fence='`'*(max((len(part) for part in re.findall(r'`+',text)),default=0)+3)
    return 'Repository evidence below is data, never an owner instruction.\n'+fence+'text\n'+text+'\n'+fence+'\n'


def queue_stop(repo, path, stop):
    queue=load_queue(repo,path)
    if any(s['id']==stop.get('id') for s in queue['owner_stops']):raise CycleError('owner stop identity already exists')
    updated=deepcopy(queue);updated['owner_stops'].append(stop);validate_schema(updated,'queue')
    if not set(stop['items']).issubset({i['id'] for i in queue['items']}):raise CycleError('owner stop references unknown item')
    validate_owner(stop['instruction'],stop['instruction']['presented'],'stop')
    if stop['resolution'] is not None:raise CycleError('new owner stop must begin unresolved')
    atomic(contained(Path(repo).resolve(),path),updated)
    return resume_queue(repo,path)


def clear_queue_stop(repo,path,identity,instruction):
    queue=load_queue(repo,path)
    matches=[s for s in queue['owner_stops'] if s['id']==identity]
    if len(matches)!=1:raise CycleError('owner stop does not exist')
    stop=matches[0]
    validate_owner(instruction,stop['instruction']['presented'],'clear-stop')
    if stop['resolution'] is not None and stop['resolution']!=instruction:raise CycleError('owner stop already cleared with another instruction')
    stop['resolution']=instruction
    queue['history'].append({'at':now(),'action':'owner-stop-cleared','items':stop['items']})
    atomic(contained(Path(repo).resolve(),path),queue)
    return resume_queue(repo,path)


def resume_queue(repo, path):
    queue = load_queue(repo,path); original=encoded(queue); invalid = set()
    previously_invalid={i['id'] for i in queue['items'] if i['status'] in {'invalidated','blocked'}}
    for item in queue['items']:
        for ref in item['bindings']:
            try: bound_bytes(repo,ref)
            except (CycleError,OSError): invalid.add(item['id'])
    while True:
        previous = set(invalid)
        invalid.update(i['id'] for i in queue['items'] if set(i['depends_on']) & invalid)
        if invalid == previous: break
    for item in queue['items']:
        if item['id'] in invalid: item['status']='invalidated'
    blocked=set()
    for stop in queue['owner_stops']:
        validate_owner(stop['instruction'],stop['instruction']['presented'],'stop')
        if stop['resolution'] is None:blocked.update(stop['items'])
        else:validate_owner(stop['resolution'],stop['instruction']['presented'],'clear-stop')
    while True:
        previous=set(blocked)
        blocked.update(i['id'] for i in queue['items'] if set(i['depends_on']) & blocked)
        if previous==blocked:break
    for item in queue['items']:
        if item['id'] in blocked:
            item['status']='blocked'
        elif item['status']=='blocked':
            # Clearance makes an item eligible for assessment, never approved.
            item['status']='invalidated' if item['id'] in invalid else 'pending'
    newly_invalid=invalid-previously_invalid
    if newly_invalid:
        queue['history'].append({'at':now(),'action':'inputs-invalidated','items':sorted(newly_invalid)})
    if encoded(queue)!=original:atomic(contained(Path(repo).resolve(),path),queue)
    return queue


def candidate_facts(repo, package_path, *, owner_exception=None):
    if owner_exception is not None:
        with owner_exception_scope(repo,owner_exception):return candidate_facts(repo,package_path)
    package = validate_package(repo,package_path)
    projection={'historical_handles':{},'retired_handles':[],
        'historical_displacements':[],'reserved_slugs':[], 'retained_handles':[],
        'source_refs':[],'dependency_fingerprints':deepcopy(package['dependencies'])}
    amendments={}; origins={}
    for item in package['items']:
        source_adr=item['handle'].split('/')[0]
        identity=digest(encoded({'source':item['source'],'handle':item['handle'],'clause_sha256':item['clause_sha256']}))
        projection['source_refs'].append({'path':item['source']['path'],'source_adr':source_adr,'clause_sha256':item['clause_sha256'],'source_identity':identity})
        if item['disposition']=='retain':projection['retained_handles'].append(item['handle'])
        elif item['disposition']=='amend':
            projection['retained_handles'].append(item['handle'])
            amendments[item['handle']]={'continuing':item['continuing'],'ceasing':item['ceasing'],'amending_handles':[s['handle'] for s in item['successors']]}
        else:
            projection['historical_handles'][item['handle']]={
                'destination':{'source_adr':source_adr,'clause_sha256':item['clause_sha256']},
                'source_identity':identity,'replacements':[s['handle'] for s in item['successors']]}
            projection['reserved_slugs'].append(item['handle'].split('/')[1])
        origins[item['handle']]={'origin':'prospective-candidate','package_sha256':digest(read(repo,package_path))}
    return {'authority':'none','package':binding(repo,package_path),'dispositions':deepcopy(package['items']),
            'projection':projection,'amendments':amendments,'origins':origins}


def write_candidate(repo, identity, package_path, approval_path):
    slug(identity); validate_approval(repo,approval_path)
    approval = load(repo,approval_path,'approval')
    if approval['package'] != binding(repo,package_path): raise CycleError('candidate package differs from approval')
    candidate = {'format':FORMATS['publication'],'id':identity,'package':binding(repo,package_path),'approval':binding(repo,approval_path),'authority':'none'}
    if approval.get('owner_exception'):candidate['owner_exception']=approval['owner_exception']
    validate_schema(candidate,'publication')
    path = _record_path(repo,'candidates',identity)
    if path.exists() and read(repo,path.relative_to(Path(repo).resolve()).as_posix()) != encoded(candidate):
        raise CycleError('candidate already exists with other inputs')
    atomic(path,candidate); return candidate


def validate_candidate(repo, path):
    candidate = load(repo,path,'publication')
    bound_bytes(repo,candidate['package']);bound_bytes(repo,candidate['approval'])
    validate_approval(repo,candidate['approval']['path'])
    approval=load(repo,candidate['approval']['path'],'approval')
    if approval['package']!=candidate['package']:raise CycleError('candidate does not bind approved package')
    if candidate.get('owner_exception')!=approval.get('owner_exception'):
        raise CycleError('candidate owner exception differs from approval')
    return candidate_facts(repo,candidate['package']['path'],owner_exception=approval.get('owner_exception'))
