"""Shared prospective council policy and outcome evaluation; legacy records stay Strict."""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import re
import yaml
from bionic_config import load_config,load_council_policy,validate_council_policy,validate_workflow_policy
from council_records import git
from cycle_workflow import CycleError,atomic,contained,digest,encoded,now,tree

MODES=('lite','standard','strict')
RIGOR={name:i for i,name in enumerate(MODES)}
RECORD='crux.cycle-council.v2'
ATTEMPT='crux.cycle-council-attempt.v2'
POLICY='crux.council-policy-instruction.v1'
INITIAL='crux.council-initialization.v1'
APPROVING={'APPROVE','APPROVE_WITH_NITS'}
DISSENTING={'REQUEST_CHANGES','REJECT','ARCHITECTURAL','DEFER_TO_HUMAN'}


def checked_bytes(repo,path):
    import secret_scan
    target=contained(Path(repo).resolve(),path)
    if secret_scan.check_input_path(target,Path(repo).resolve()) or target.stat().st_size>2_000_000:
        raise CycleError('council artifact is not a bounded safe regular input')
    data=target.read_bytes()
    if secret_scan.scan_text(data.decode()):raise CycleError('council input secret scan refused')
    return data


def ref(repo,path):return {'path':path,'sha256':digest(checked_bytes(repo,path))}


def read_json(repo,path):
    try:return json.loads(checked_bytes(repo,path))
    except (UnicodeError,json.JSONDecodeError) as exc:raise CycleError('invalid council JSON artifact') from exc


def seal(value):
    value=deepcopy(value);value.pop('record_sha256',None);value['record_sha256']=digest(encoded(value));return value


def verify_seal(value):
    payload=dict(value);checksum=payload.pop('record_sha256',None)
    if checksum!=digest(encoded(payload)):raise CycleError('council record integrity check failed')


def raw_config(repo,revision=None):
    repo=Path(repo).resolve()
    for path in ('.bionic.yml','.crux'):
        if revision is None:
            if not (repo/path).exists():continue
            raw=checked_bytes(repo,path)
        else:
            result=git(repo,'show',revision+':'+path)
            if result.returncode:continue
            raw=result.stdout
        from bionic_config import parse_config_text
        parse_config_text(raw.decode(),source=path,path=path)
        return yaml.safe_load(raw) or {},path
    return {},None


def normalized(raw):
    result=validate_council_policy(raw)
    return dict(result,human_policy=validate_workflow_policy(raw)['adr.acceptance'])


def effective(settings,purpose):
    kind={'adr-creation':'adr','disposition':'migration'}.get(purpose,purpose)
    return settings['overrides'].get(kind,settings['mode'])


def initialize(repo,mode='standard',*,selection):
    """Record an explicit first setup choice, never reset an existing policy."""
    if mode not in MODES or not isinstance(selection,str) or not selection.strip():
        raise CycleError('explicit initial council mode selection is required')
    repo=Path(repo).resolve();cfg=load_config(repo)
    folder=cfg.docs_root/'adrs/councils'
    head=git(repo,'rev-parse','--verify','HEAD')
    basis=head.stdout.decode().strip() if head.returncode==0 else None
    prior,_=raw_config(repo,basis) if basis else ({},None)
    prior_tree=bool(basis and git(repo,'cat-file','-e',basis+':'+cfg.docs_dir+'/manifest.yml').returncode==0)
    if prior or prior_tree or list(folder.rglob('attempt-*.json')):
        raise CycleError('initialization cannot change an existing project council policy')
    raw,path=raw_config(repo)
    target=repo/'.bionic.yml'
    previous=raw.get('council',{})
    if previous and previous.get('mode')!=mode:
        raise CycleError('initialization preserves existing configured council selection')
    raw.setdefault('config_version','1');raw.setdefault('docs_dir',cfg.docs_dir)
    raw['council']=dict(previous,mode=mode,max_attempts=previous.get('max_attempts',7))
    from decision_policy import write_text_atomic
    write_text_atomic(target,yaml.safe_dump(raw,sort_keys=False))
    record=seal({'format':INITIAL,'at':now(),'selection':selection,'policy':normalized(raw),
                 'config':ref(repo,'.bionic.yml'),'basis':basis})
    dest=folder/'initialization.json'
    if dest.exists():
        old=read_json(repo,dest.relative_to(repo).as_posix())
        if old['policy']!=record['policy']:raise CycleError('initial council policy already recorded')
        return old
    atomic(dest,record);return record


def _owner(owner,action,mode=None,limit=None):
    if (not isinstance(owner,dict) or owner.get('origin')!='owner-conversation' or
        not all(isinstance(owner.get(k),str) and owner[k].strip() for k in ('quote','conversation'))):
        raise CycleError('council policy change requires explicit owner conversation authorization')
    actions=owner.get('approved_actions',[])
    if owner.get('action')==action:
        actions=[owner]
    matches=[a for a in actions if a.get('action')==action and
             (mode is None or a.get('value')==mode) and (limit is None or a.get('limit')==limit)]
    if not matches:raise CycleError('owner instruction does not authorize this council policy action')
    return deepcopy(owner)


def record_policy(repo,identity,owner_path,*,action='select-council-mode',logical_id=None,limit=None):
    if not re.fullmatch(r'[a-z][a-z0-9-]*',identity):raise CycleError('invalid council policy identity')
    repo=Path(repo).resolve();cfg=tree(repo);raw,path=raw_config(repo);settings=normalized(raw)
    owner=read_json(repo,owner_path)
    _owner(owner,action,settings['mode'] if action=='select-council-mode' else None,limit)
    head=git(repo,'rev-parse','--verify','HEAD')
    if head.returncode:raise CycleError('policy changes require a committed prior policy')
    basis=head.stdout.decode().strip();before,_=raw_config(repo,basis)
    baseline=normalized(before)
    if settings['overrides']!=baseline['overrides']:
        actions=owner.get('approved_actions',[owner])
        if not any(a.get('action')==action and a.get('value')==settings['mode'] and
                   a.get('overrides')==settings['overrides'] for a in actions):
            raise CycleError('owner instruction must name the actual council override change')
    value=seal({'format':POLICY,'at':now(),'action':action,'logical_id':logical_id,'limit':limit,
        'previous':baseline,'selected':settings,'basis':basis,'config':ref(repo,path),
        'owner':owner,'owner_source':ref(repo,owner_path)})
    target=cfg.docs_root/'adrs/councils/policies'/f'{identity}.json'
    if target.exists():raise CycleError('council policy instruction already exists')
    atomic(target,value);return value


def _authorizations(repo,settings,action,*,logical_id=None,limit=None):
    cfg=tree(repo);rows=[]
    for path in sorted((cfg.docs_root/'adrs/councils/policies').glob('*.json')):
        row=read_json(repo,path.relative_to(cfg.repo_root).as_posix());verify_seal(row)
        if row.get('format')!=POLICY:raise CycleError('unknown council policy instruction format')
        if row.get('action')!=action or row.get('selected')!=settings:continue
        if row.get('logical_id') not in (None,logical_id):continue
        if limit is not None and row.get('limit')!=limit:continue
        _owner(row['owner'],action,settings['mode'] if action=='select-council-mode' else None,limit)
        prior,_=raw_config(repo,row['basis'])
        if normalized(prior)!=row['previous']:raise CycleError('council policy prior basis mismatch')
        if git(repo,'merge-base','--is-ancestor',row['basis'],'HEAD').returncode:
            raise CycleError('council policy basis is not in project history')
        if ref(repo,row['owner_source']['path'])!=row['owner_source']:
            raise CycleError('council owner instruction bytes changed')
        if row['selected']['overrides']!=row['previous']['overrides']:
            actions=row['owner'].get('approved_actions',[row['owner']])
            if not any(a.get('action')==action and a.get('value')==settings['mode'] and
                       a.get('overrides')==settings['overrides'] for a in actions):
                raise CycleError('owner instruction does not authorize council overrides')
        rows.append(ref(repo,path.relative_to(cfg.repo_root).as_posix()))
        rows.append(row['owner_source'])
    return rows


def resolve(repo,purpose,*,previous=None,logical_id=None,extension=None):
    cfg=tree(repo);raw,path=raw_config(repo);settings=normalized(raw);mode=effective(settings,purpose)
    inputs=[ref(repo,path)] if path else []
    initialized=False
    initial=cfg.docs_root/'adrs/councils/initialization.json'
    if initial.exists():
        row=read_json(repo,initial.relative_to(cfg.repo_root).as_posix());verify_seal(row)
        if row.get('format')!=INITIAL or not row.get('selection'):
            raise CycleError('invalid council initialization provenance')
        if row.get('basis'):
            before,_=raw_config(repo,row['basis'])
            old_tree=git(repo,'cat-file','-e',row['basis']+':'+cfg.docs_dir+'/manifest.yml').returncode==0
            if before or old_tree or git(repo,'merge-base','--is-ancestor',row['basis'],'HEAD').returncode:
                raise CycleError('initialization cannot replace prior project policy')
        initialized=row.get('policy')==settings and row.get('config')==ref(repo,path)
        inputs.append(ref(repo,initial.relative_to(cfg.repo_root).as_posix()))
    if previous is not None:
        before=previous['settings'];old_mode=previous['mode']
    else:
        head=git(repo,'rev-parse','--verify','HEAD')
        before={};old_mode='strict'
        if head.returncode==0:
            committed,_=raw_config(repo,'HEAD')
            if effective(normalized(committed),purpose)==mode:
                # Follow effective policy transitions, not whole-file edits.
                # Comments, unrelated overrides and acceptance settings cannot
                # launder an earlier unauthorized reduction for this purpose.
                changes=git(repo,'log','--first-parent','--format=%H','--','.bionic.yml','.crux')
                for commit in changes.stdout.decode().splitlines():
                    parent=git(repo,'rev-parse',commit+'^1')
                    candidate,_=raw_config(repo,parent.stdout.decode().strip()) if parent.returncode==0 else ({},None)
                    if effective(normalized(candidate),purpose)!=mode:
                        committed=candidate;break
            before=normalized(committed);old_mode=effective(before,purpose)
        else:before=normalized({})
    authorization=_authorizations(repo,settings,'select-council-mode',logical_id=logical_id)
    changed=previous is not None and settings!=before
    if ((RIGOR[mode]<RIGOR[old_mode] or changed) and not initialized and not authorization):
        raise CycleError('council mode change lacks owner authorization or explicit initialization')
    limit=settings['max_attempts']
    if previous and previous.get('legacy_limit') is not None:limit=previous['legacy_limit']
    if previous and previous.get('max_attempts',limit)>limit:
        retained=previous['max_attempts']
        authorized=_authorizations(repo,settings,'extend-council-limit',logical_id=logical_id,limit=retained)
        if not authorized:raise CycleError('frozen council extension no longer has its owner authorization')
        authorization+=authorized;limit=retained
    if extension is not None:
        if type(extension) is not int or extension<=limit:raise CycleError('extension must increase the attempt limit')
        ext=_authorizations(repo,settings,'extend-council-limit',logical_id=logical_id,limit=extension)
        if not ext:raise CycleError('council extension lacks explicit owner authorization')
        authorization+=ext;limit=extension
    inputs+=authorization
    return {'mode':mode,'settings':settings,'human_policy':settings['human_policy'],'max_attempts':limit,
            'policy_inputs':inputs,'initialization':initialized,'models':{}}


def approved(vote):
    return isinstance(vote,dict) and not vote.get('errored') and vote.get('decision') in APPROVING


def evidence_valid(item):
    evidence=item.get('evidence',{});text=item.get('evidence_text')
    if not isinstance(evidence,dict):return False
    path=evidence.get('path')
    return (isinstance(path,str) and bool(path) and not Path(path).is_absolute() and '..' not in Path(path).parts and
            isinstance(text,str) and digest(text.encode())==evidence.get('sha256'))


def evaluate(row):
    """Derive a mode-aware outcome; a dissent label alone is no veto."""
    mode=row.get('policy',{}).get('mode')
    if mode not in MODES:raise CycleError('unknown frozen council mode')
    if row.get('binding_failures'):return 'changes-required'
    seats=row.get('seats',[]);architect=row.get('architect') or {}
    agreement=(architect.get('agrees') is True and architect.get('subject_sha256')==row.get('subject_sha256')
               and isinstance(architect.get('rationale'),str) and architect['rationale'].strip())
    resolutions=architect.get('binding_resolutions',[])
    if not isinstance(resolutions,list) or any(not isinstance(r,dict) or r.get('kind') not in {'resolved','refuted'} or
        not r.get('explanation') or not evidence_valid(r) for r in resolutions):return 'changes-required'
    if mode=='lite':
        passes=row.get('passes',[])
        if len(passes)!=2 or [p.get('pass') for p in passes]!=['challenge','final']:return 'changes-required'
        if any(p.get('status')!='closed' or p.get('vote',{}).get('errored') or
               p.get('vote',{}).get('decision') not in APPROVING|{'REQUEST_CHANGES','DEFER_TO_HUMAN'} for p in passes):return 'changes-required'
        if any(f.get('binding_failure') or f.get('missing_authorization') for f in passes[-1].get('vote',{}).get('findings',[])):
            return 'changes-required'
        final=passes[1]
        return 'approved' if agreement and final.get('subject_sha256')==row.get('subject_sha256') and approved(final.get('vote')) else 'changes-required'
    if len(seats)!=3 or len({s.get('provider') for s in seats})!=3:return 'changes-required'
    if any(s.get('errored') or s.get('decision') not in APPROVING|DISSENTING for s in seats):return 'changes-required'
    if any(f.get('binding_failure') or f.get('missing_authorization') for s in seats for f in s.get('findings',[])):
        return 'changes-required'
    if mode=='strict':
        return 'approved' if all(approved(s) and all(f.get('kind')=='nit' for f in s.get('findings',[])) for s in seats) else 'changes-required'
    if sum(approved(s) for s in seats)<2 or not agreement:return 'changes-required'
    dissent={s['provider'] for s in seats if not approved(s) or any(f.get('kind')!='nit' for f in s.get('findings',[]))}
    dispositions=architect.get('dissent',[])
    if not isinstance(dispositions,list) or len({d.get('provider') for d in dispositions})!=len(dispositions):return 'changes-required'
    if {d.get('provider') for d in dispositions}!=dissent:return 'changes-required'
    for disposition in dispositions:
        kind=disposition.get('kind');explanation=disposition.get('explanation')
        if not isinstance(explanation,str) or not explanation.strip():return 'changes-required'
        if kind=='accepted-tradeoff':continue
        if kind not in {'resolved','refuted'}:return 'changes-required'
        if not evidence_valid(disposition):return 'changes-required'
    return 'approved'


def disposition(repo,record_path,value):
    """The owning writer resolves and retains checkable dissent evidence bytes."""
    cfg=tree(repo);path=contained(cfg.docs_root,record_path);row=read_json(repo,path.relative_to(cfg.repo_root).as_posix())
    verify_seal(row)
    if row.get('format')!=RECORD:raise CycleError('architect disposition requires a new mode-aware record')
    if digest(checked_bytes(repo,(cfg.docs_root/row['subject']).relative_to(cfg.repo_root).as_posix()))!=row['subject_sha256']:
        raise CycleError('architect disposition subject changed')
    value=deepcopy(value)
    if value.get('subject_sha256')!=row['subject_sha256']:raise CycleError('architect disposition binds another revision')
    dissent_items=value.get('dissent',[])
    if not isinstance(dissent_items,list) or any(not isinstance(d,dict) for d in dissent_items):raise CycleError('typed architect dissent must be a list')
    def retain_evidence(item):
        evidence=item.get('evidence',{})
        if not isinstance(evidence,dict):raise CycleError('checkable evidence binding required')
        data=checked_bytes(repo,evidence.get('path',''))
        if digest(data)!=evidence.get('sha256'):raise CycleError('dissent evidence artifact changed')
        item['evidence_text']=data.decode()
    for dissent in dissent_items:
        if dissent.get('kind') in {'resolved','refuted'}:
            retain_evidence(dissent)
    existing=deepcopy(row.get('binding_failures',[]))
    incoming=value.pop('binding_failures',None)
    if incoming is not None and not isinstance(incoming,list):raise CycleError('binding failures must be a list')
    resolutions=value.get('binding_resolutions',[])
    if not isinstance(resolutions,list):raise CycleError('binding resolutions must be a list')
    for resolution in resolutions:
        if (not isinstance(resolution,dict) or resolution.get('kind') not in {'resolved','refuted'} or
            not resolution.get('explanation') or resolution.get('failure') not in existing):
            raise CycleError('clearing an established obligation requires an explicit checkable resolution')
        retain_evidence(resolution);existing.remove(resolution['failure'])
    if incoming is not None and any(f not in incoming for f in existing):
        raise CycleError('established binding failures cannot be cleared by replacement or omission')
    for fact in incoming or []:
        if fact not in existing:existing.append(fact)
    for dissent in dissent_items:
        if dissent.get('kind') in {'demonstrated-binding-failure','missing-authorization','unresolved-required-safety'}:
            if not dissent.get('explanation'):raise CycleError('typed blocking disposition requires its reason')
            if dissent not in existing:existing.append(deepcopy(dissent))
    row['binding_failures']=existing
    row['architect']=value;row['outcome']=evaluate(row)
    import secret_scan
    if secret_scan.scan_text(json.dumps(row)):raise CycleError('architect disposition output secret scan refused')
    updated=seal(row)
    if encoded(updated)==path.read_bytes():
        return {'record':record_path,'outcome':row['outcome']}
    atomic(path,updated)
    from cycle_council import commit_evidence
    commit_evidence(cfg.repo_root,[path],'Record exact architect council disposition')
    return {'record':record_path,'outcome':row['outcome']}
