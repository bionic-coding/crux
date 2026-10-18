"""Prospective publication admission and bounded activation preparation.

The immutable Git introduction, not a file's authority field, grants admission.
Approval is checked under the introducing commit's first parent and again under
the installed reader. Original standing comes from that parent; source bytes,
amenders and material dependencies must still match in the current checkout.
"""
from contextlib import contextmanager
import json
import importlib.util
from pathlib import Path
import subprocess
import sys

import adr_migration as m
from cycle_workflow import CycleError, atomic, contained, digest, encoded, tree


PRIOR_READER_TIMEOUT_SECONDS=900

def initial_transition_paths(repo, package, publication_path):
    """The one named bootstrap's reviewed connected implementation scope."""
    receipt=json.loads(m.read(repo,package['governing_adr']['receipt']))
    if not package['initial'] or receipt['adr']!='ADR-0160':return {publication_path}
    docs=tree(repo).docs_root.relative_to(Path(repo).resolve()).as_posix()
    return {publication_path,'AGENTS.md','crux/templates/AGENTS.md.tmpl',docs+'/AGENTS.md',
        'crux/skills/migrate-adrs/SKILL.md','crux/skills/review-decisions/SKILL.md',
        'crux/skills/cleanup-campsite/SKILL.md','crux/agents/architect.md',
        'crux/catalog/bundles.yml','crux/catalog/skills.json','crux/catalog/agents.json','crux/catalog/rules.json',
        'crux/plugin.json','README.md','USER_GUIDE.md','crux/scripts/adr_migration_publication.py',
        'crux/scripts/implementation_approval.py','crux/scripts/tests/test_adr_migration_publication.py',
        'crux/scripts/implementation_migration.py','crux/scripts/summaries_projection.py','crux/scripts/doctrine_projection.py',
        'crux/scripts/tests/test_review_decisions_prose.py','crux/scripts/tests/test_review_recording_contract.py',
        'crux/templates/adr-review-template.md','crux/scripts/journal_index.py','crux/scripts/review_findings.py',
        'crux/scripts/generate-reviews-index.py','opencode/agents/architect.md',
        docs+'/adrs/summaries/resolver.json',docs+'/adrs/summaries/_meta.json',
        docs+'/adrs/doctrine/index.md',docs+'/adrs/doctrine/_meta.json'}


def validate_initial_transition(repo, package, publication_path, commit):
    required=initial_transition_paths(repo,package,publication_path)
    if len(required)==1:return
    changed=set(m._git(repo,'diff-tree','--no-commit-id','--name-only','-r',commit).decode().splitlines())
    if not required<=changed:raise CycleError('initial activation is missing connected transition items')
    docs=tree(repo).docs_root.relative_to(Path(repo).resolve()).as_posix()
    if any(p.startswith(docs+'/adrs/migrations/approvals/') for p in changed):
        raise CycleError('activation must not write disposition approval evidence')
    if (Path(repo)/'crux/skills/review-decisions').exists():raise CycleError('old review workflow survives activation')
    for name in ('crux/catalog/skills.json','crux/catalog/bundles.yml','crux/agents/architect.md',
                 'crux/templates/AGENTS.md.tmpl'):
        raw=m.read(repo,name)
        if b'review-decisions' in raw or b'migrate-adrs' not in raw:
            raise CycleError('initial activation routing is incomplete')


def inventory(repo):
    # Discovery preserves legacy trees without imposing today's write schema.
    # Any discovered prospective record still passes full current validation.
    from bionic_config import load_config
    import implementation_migration as historical
    repo=Path(repo).resolve()
    inputs={rel:historical._read(repo,rel)[0] for rel in historical._config_inputs()
            if (repo/rel).exists() or (repo/rel).is_symlink()}
    relative=historical._discovery_directory(repo,inputs)
    folder=repo/relative
    history=historical._InvocationHistory(repo)
    directories={relative}
    for entries in history.metadata(historical._config_inputs()).values():
        directories.add(historical._historical_directory(repo,entries,history))
    paths=set(m._git(repo,'log','--first-parent','--format=','--name-only','HEAD','--',*sorted(directories)).decode().splitlines())
    paths={p for p in paths if Path(p).parent.as_posix() in directories and p.endswith('.publication.json')}
    if folder.exists():paths.update(p.relative_to(repo).as_posix() for p in folder.glob('*.publication.json'))
    # A legacy layout may prove absence without enrolling in the current write
    # schema. A prospective publication never receives that compatibility path.
    if paths:load_config(repo)
    rows=[]
    for path in sorted(paths):
        if Path(path).parent.as_posix()!=relative:raise CycleError('prospective publication layout changed')
        value=m.load(repo,path,'publication')
        commit=m.introduction(repo,path)
        # A deletion or edit followed by restoration is still a rewritten proof.
        changes=m._git(repo,'log','--first-parent','--format=%H',commit+'..HEAD','--',path).decode().splitlines()
        if changes:raise CycleError('prospective publication history changed')
        rows.append(dict(path=path,sha256=digest(m.read(repo,path)),publication_commit=commit,content=encoded(value)))
    return rows


def validate_boundary(repo, approval_path, parent, *, _with_standing=False):
    """Execute exactly the previously committed reader, in its clean repository.

    The parent code must independently approve; a relaxed candidate cannot rescue
    its refusal. This is one narrow validation, not another suite execution.
    """
    import implementation_migration as historical
    repo=Path(repo).resolve();m.full_commit(repo,parent)
    with historical._revision_repository(repo,parent) as previous:
        script=previous/'crux/scripts/adr-migration.py'
        if not script.is_file():
            # Consuming projects keep the plugin installed, not vendored. The
            # earlier committed receipt must prove those exact installed bytes;
            # absence of source is never permission to substitute another reader.
            prior=m.load(previous,approval_path,'approval')
            support=prior['readiness']
            package=m.load(previous,prior['package']['path'],'package')
            if package['initial'] or support.get('format')!='crux.adr-migration-installed-support.v1':
                raise CycleError('parent migration validator is unavailable')
            m.validate_readiness(previous,support,initial=False)
            script=Path(m.__file__).resolve().with_name('adr-migration.py')
            expected=next((r['sha256'] for r in support['sources'] if r['path']=='scripts/adr-migration.py'),None)
            if not script.is_file() or digest(script.read_bytes())!=expected:
                raise CycleError('parent installed validator source changed')
        try:
            result=subprocess.run([sys.executable,str(script),'approval','--repo-root',str(previous),'--path',approval_path],
                capture_output=True,env=historical._revision_environment(),timeout=PRIOR_READER_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            raise CycleError(f'parent migration validator exceeded {PRIOR_READER_TIMEOUT_SECONDS} second budget; disposition approval was not accepted') from None
        if result.returncode:raise CycleError('parent migration validator refused disposition approval')
        # This is source standing, not an exemption for later byte drift.
        baseline=m.current_standing(previous)
    token=m._STANDING_BASIS.set(baseline)
    try:
        approval=m.validate_approval(repo,approval_path)
        return (approval,baseline) if _with_standing else approval
    finally:m._STANDING_BASIS.reset(token)


def publication_facts(repo, publication):
    repo=Path(repo).resolve();path=publication['path']
    record=m.load(repo,path,'publication')
    commit=publication['publication_commit']
    if m.introduction(repo,path)!=commit:raise CycleError('publication introduction changed')
    parent=m._git(repo,'rev-parse',commit+'^1').decode().strip()
    for ref in (record['approval'],record['package']):
        if digest(m.blob(repo,parent,ref['path']))!=ref['sha256']:
            raise CycleError('publication evidence must exist before activation')
        m.bound_bytes(repo,ref)
    with m.published_objectives(repo,record['package']['path'],parent):
        approval,baseline=validate_boundary(repo,record['approval']['path'],parent,_with_standing=True)
    if approval['package']!=record['package']:raise CycleError('publication package differs from approval')
    if record.get('owner_exception')!=approval.get('owner_exception'):
        raise CycleError('publication owner exception differs from approval')
    # Validate exact current inputs against original standing. Otherwise this
    # publication would invalidate itself by removing its own source handles.
    token=m._STANDING_BASIS.set(baseline)
    try:
        with m.published_objectives(repo,record['package']['path'],parent):
            facts=m.candidate_facts(repo,record['package']['path'],owner_exception=approval.get('owner_exception'))
    finally:m._STANDING_BASIS.reset(token)
    projection=facts['projection']
    projection['amendments']=facts['amendments']
    import summaries_projection as summaries
    if set(projection['historical_handles']) & summaries.signed_reconciliation_handles(tree(repo).docs_root/'adrs'):
        raise CycleError('prospective displacement would orphan a signed reconciliation')
    ref={k:publication[k] for k in ('path','sha256','publication_commit')}
    projection['origins']={h:dict(origin='prospective-publication',publication_ref=ref) for h in facts['origins']}
    # Projection source identities retain the complete historical schema.
    for source in projection['source_refs']:
        source.update(tier='active',status='Accepted')
    package=m.load(repo,record['package']['path'],'package')
    validate_initial_transition(repo,package,path,commit)
    bindings=[record['package'],record['approval'],package['record'],
              m.binding(repo,package['governing_adr']['receipt']),
              *(m.binding(repo,r['path']) if r['kind']=='objectives' else r for r in package['dependencies'])]
    if approval.get('owner_exception'):bindings.append(approval['owner_exception'])
    for item in package['items']:
        bindings.append(m.binding(repo,item['source']['path']))
        bindings.extend(m.binding(repo,s['source']['path']) for s in item['successors'])
    projection['dependency_fingerprints']=[dict(path=p,sha256=s) for p,s in sorted({(r['path'],r['sha256']) for r in bindings})]
    return projection


def prepare_outputs(repo, candidate_path, *, _validated=False, _base_view=None):
    """Compile a private candidate plan without admitting public authority.

    The resulting bytes omit the prospective commit identifier; only the runtime
    reader derives it. This allows canonical views and publication to share one
    activation commit, without a circular Git identifier or fabricated evidence.
    """
    repo=Path(repo).resolve();candidate=m.load(repo,candidate_path,'publication')
    if not _validated:
        parent=m._git(repo,'rev-parse','HEAD').decode().strip()
        validate_boundary(repo,candidate['approval']['path'],parent)
        m.validate_candidate(repo,candidate_path)
    import implementation_migration as historical
    import summaries_projection as summaries
    import doctrine_projection as doctrine
    facts=m.candidate_facts(repo,candidate['package']['path'],owner_exception=candidate.get('owner_exception'));projection=facts['projection']
    projection['amendments']=facts['amendments']
    package=m.load(repo,candidate['package']['path'],'package')
    destination=(tree(repo).docs_root/f'adrs/migrations/{candidate["id"]}.publication.json').relative_to(repo).as_posix()
    reference={'path':destination,'sha256':digest(encoded(candidate))}
    projection['origins']={h:dict(origin='prospective-prepared',publication_ref=reference) for h in facts['origins']}
    for ref in projection['source_refs']:ref.update(tier='active',status='Accepted')
    bindings=[candidate['package'],candidate['approval'],package['record'],m.binding(repo,package['governing_adr']['receipt']),*package['dependencies']]
    if candidate.get('owner_exception'):bindings.append(candidate['owner_exception'])
    for item in package['items']:
        bindings.append(m.binding(repo,item['source']['path']))
        bindings.extend(m.binding(repo,s['source']['path']) for s in item['successors'])
    projection['dependency_fingerprints']=[dict(path=p,sha256=s) for p,s in sorted({(r['path'],r['sha256']) for r in bindings})]
    if set(projection['historical_handles']) & summaries.signed_reconciliation_handles(tree(repo).docs_root/'adrs'):
        raise CycleError('prospective displacement would orphan a signed reconciliation')
    view=historical.authority_view(repo) if _base_view is None else _base_view
    view=combine(view,[projection]);view['state']='prepared'
    view['publications']=list(view['publications'])+[dict(reference,publication_commit=None)]
    prepared={'view':view,'candidate':candidate}
    spec=importlib.util.spec_from_file_location('_prospective_summary_driver',Path(__file__).with_name('summarize-adrs.py'))
    driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver)
    manifest=summaries.read_manifest(repo)
    loaded,_,pending,_=driver._load_summary_inputs(repo,manifest,_prepared=prepared)
    plan=summaries._plan_summary_outputs(loaded,view,pending)
    outputs=summaries._materialize_summary_outputs(plan,None)
    loaded,_,pending,_=doctrine._load_doctrine_inputs(repo,manifest,_prepared=prepared)
    plan=doctrine._plan_doctrine_outputs(loaded,view,pending)
    outputs.update(doctrine._materialize_doctrine_outputs(plan,None))
    if (repo/'crux/plugin.json').is_file():
        spec=importlib.util.spec_from_file_location('_prospective_catalog_driver',Path(__file__).with_name('generate-rules-catalog.py'))
        catalog=importlib.util.module_from_spec(spec);spec.loader.exec_module(catalog)
        loaded,_=catalog._load_catalog_inputs(repo,repo/'crux',_prepared=prepared)
        plan=catalog._plan_rules_catalog_outputs(loaded,view,pending)
        outputs.update(catalog._materialize_rules_catalog_outputs(plan))
    return {path.relative_to(repo).as_posix():raw for path,raw in outputs.items()}


def combine(view, prospective):
    """Combine separately proved families, preserving original proof references."""
    result=dict(view)
    result['historical_handles']=dict(view['historical_handles'])
    result['origins']=dict(view.get('origins',{}))
    result['amendments']=dict(view.get('amendments',{}))
    for key in ('historical_displacements','retired_handles','reserved_slugs','retained_handles','source_refs','dependency_fingerprints'):
        result[key]=list(view[key])
    for facts in prospective:
        overlap=set(result['historical_handles'])&set(facts['historical_handles'])
        if overlap:raise CycleError('connected publications displace the same source twice')
        result['historical_handles'].update(facts['historical_handles'])
        result['origins'].update(facts['origins'])
        result['amendments'].update(facts.get('amendments',{}))
        for key in ('historical_displacements','retired_handles','reserved_slugs','retained_handles','source_refs','dependency_fingerprints'):
            for value in facts[key]:
                if value not in result[key]:result[key].append(value)
    return result


def stage_transaction(repo, candidate_path, changes, *, initial_scope=None, fault_after=None):
    """Stage only declared candidate changes; rollback restores owned bytes.

    This prepares a connected tree for independent review and a single commit.
    It commits nothing. Public admission still requires that later commit.
    Initial workflow/code scope is the reviewed explicit list supplied by the
    conductor. Later publications write their one prospective record only.
    """
    repo=Path(repo).resolve();cfg=tree(repo)
    candidate=m.load(repo,candidate_path,'publication')
    # Cheap structural refusals precede expensive history replay. None grants
    # permission: exact parent and candidate validation still precedes writes.
    package=m.load(repo,candidate['package']['path'],'package')
    approval=m.load(repo,candidate['approval']['path'],'approval')
    destination=(cfg.docs_root/f'adrs/migrations/{candidate["id"]}.publication.json').relative_to(repo).as_posix()
    if changes.get(destination)!=encoded(candidate):raise CycleError('transaction requires the complete approved publication')
    docs=cfg.docs_root.relative_to(repo).as_posix()
    protected={'.bionic.yml',docs+'/manifest.yml',docs+'/objectives.md',candidate['package']['path'],
        candidate['approval']['path'],approval['council']['path'],package['record']['path'],
        package['governing_adr']['source']['path'],package['governing_adr']['receipt']}
    if approval.get('owner_exception'):protected.add(approval['owner_exception']['path'])
    if candidate.get('owner_exception'):protected.add(candidate['owner_exception']['path'])
    protected.update(ref['path'] for ref in package['dependencies'])
    protected.update(ref['path'] for ref in approval['readiness'].get('tests',[]))
    if 'review' in approval['readiness']:protected.add(approval['readiness']['review']['path'])
    generated={docs+'/adrs/'+part for part in ('summaries/rule-table.md','summaries/resolver.json',
        'summaries/implementation-map.md','summaries/_meta.json','doctrine/index.md','doctrine/_meta.json')}
    if (repo/'crux/plugin.json').is_file():generated.add('crux/catalog/rules.json')
    scope=(set(initial_scope or ()) if package['initial'] else {destination})|generated
    if not set(changes)<=scope:raise CycleError('transaction write is outside declared scope')
    for name in changes:
        path=contained(repo,name)
        if name in protected or name.split('/')[0]=='.git' or name.endswith('.application.json') or name.startswith((docs+'/adrs/acceptances/',
             docs+'/adrs/councils/',docs+'/adrs/migrations/approvals/',docs+'/adrs/migrations/policies/',
             docs+'/promptbooks/',docs+'/cycles/')):
            raise CycleError('transaction cannot write approval, configuration, objectives or historical proof')
        if path.parent==cfg.docs_root/'adrs' or path.is_relative_to(cfg.docs_root/'adrs/reviews') and path.name!='index.md':
            raise CycleError('transaction preserves historical bodies and reports')
    parent=m._git(repo,'rev-parse','HEAD').decode().strip()
    approval,baseline=validate_boundary(repo,candidate['approval']['path'],parent,_with_standing=True)
    if approval['package']!=candidate['package']:raise CycleError('candidate does not bind approved package')
    m.validate_candidate(repo,candidate_path)
    import implementation_migration as historical
    base_view=historical.authority_view(repo)
    changes=dict(changes)
    # Snapshot canonical destinations without rendering prospective authority
    # against source that this same transaction is about to replace/remove.
    owned=set(changes)|generated
    if not initial_transition_paths(repo,package,destination)<=owned:
        raise CycleError('transaction is missing connected initial transition items')
    snapshots={}
    for name in sorted(owned):
        path=contained(repo,name)
        if name in protected or name.endswith('.application.json') or name.startswith((docs+'/adrs/acceptances/',
             docs+'/adrs/councils/',docs+'/adrs/migrations/approvals/',docs+'/adrs/migrations/policies/',
             docs+'/promptbooks/',docs+'/cycles/')):
            raise CycleError('transaction cannot write approval, configuration or objectives')
        # No historical body/report/proof write belongs to activation either.
        if path.parent==cfg.docs_root/'adrs' or path.is_relative_to(cfg.docs_root/'adrs/reviews') and path.name!='index.md':
            raise CycleError('transaction preserves historical bodies and reports')
        snapshots[name]=path.read_bytes() if path.is_file() else None
    created=[];removed_dirs=[];write_count=0
    def write_owned(name,raw):
        nonlocal write_count
        path=contained(repo,name)
        if raw is None:
            path.unlink(missing_ok=True)
            old_skill=repo/'crux/skills/review-decisions'
            if path.parent==old_skill and old_skill.is_dir() and not any(old_skill.iterdir()):
                old_skill.rmdir();removed_dirs.append(old_skill)
        else:
            missing=[];directory=path.parent
            while not directory.exists():missing.append(directory);directory=directory.parent
            path.parent.mkdir(parents=True,exist_ok=True);created.extend(reversed(missing));path.write_bytes(raw)
        write_count+=1
        if fault_after==write_count:raise CycleError('injected transaction interruption')
    try:
        for name,raw in changes.items():
            if name not in generated:write_owned(name,raw)
        # Exact inputs are checked after source writes. Render only this staged
        # source and the privately captured prepublication authority, once.
        token=m._STANDING_BASIS.set(baseline)
        try:
            m.validate_candidate(repo,candidate_path)
            refreshed=prepare_outputs(repo,candidate_path,_validated=True,_base_view=base_view)
            if not set(refreshed)<=generated:raise CycleError('staged outputs exceed captured rollback scope')
            if not initial_transition_paths(repo,package,destination)<=(set(changes)-generated)|set(refreshed):
                raise CycleError('transaction is missing connected initial transition outputs')
            for name,raw in refreshed.items():write_owned(name,raw)
        finally:m._STANDING_BASIS.reset(token)
    except BaseException:
        for directory in removed_dirs:directory.mkdir(parents=True,exist_ok=True)
        for name,raw in snapshots.items():
            path=contained(repo,name)
            if raw is None:path.unlink(missing_ok=True)
            else:path.write_bytes(raw)
        for path in reversed(created):
            try:path.rmdir()
            except OSError:pass  # Preserve anything another writer added.
        raise
    return {'authority':'none','parent':parent,'publication':destination,'paths':sorted((set(changes)-generated)|set(refreshed))}
