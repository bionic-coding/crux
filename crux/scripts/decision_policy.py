"""Prospective ADR creation/acceptance policy; historical provenance stays immutable."""
from __future__ import annotations
import json
from pathlib import Path
import re
import os
import tempfile
import yaml
from bionic_config import load_workflow_policy
from cycle_workflow import CycleError, contained, digest, now, locked, load, save, event, atomic
from cycle_council import validate_approval


def write_text_atomic(path, text):
    fd, temporary = tempfile.mkstemp(prefix='.decision-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def frontmatter(text):
    match = re.match(r'^---\n(.*?)\n---\n', text, re.S)
    if not match:
        raise CycleError('ADR frontmatter is invalid')
    front = yaml.safe_load(match.group(1))
    if not isinstance(front, dict):
        raise CycleError('ADR frontmatter must be a mapping')
    return front, text[match.end():]


def receipt_identity(receipt):
    """Return the immutable identity of an original or recovery receipt."""
    adr=receipt['adr']
    if not isinstance(adr,str) or not re.fullmatch(r'(?:[A-Z][A-Z0-9]*-)?ADR-\d{4,}',adr):
        raise CycleError('invalid acceptance receipt ADR identity')
    if 'recovery_of' not in receipt:
        return f'adrs/acceptances/{adr}.json'
    sha=receipt['owner_decision']['sha256']
    if not isinstance(sha,str) or not re.fullmatch('[0-9a-f]{64}',sha):
        raise CycleError('invalid recovery owner evidence digest')
    return f'adrs/acceptances/recoveries/{adr}/{sha}.json'


def _receipt_reference(read, reference):
    if (not isinstance(reference,dict) or set(reference)!={'path','sha256'}
            or not isinstance(reference['path'],str)
            or not re.fullmatch(r'adrs/acceptances/(?:(?:[A-Z][A-Z0-9]*-)?ADR-\d{4,}\.json|recoveries/(?:[A-Z][A-Z0-9]*-)?ADR-\d{4,}/[0-9a-f]{64}\.json)',reference['path'])):
        raise CycleError('invalid acceptance receipt reference')
    raw=read(reference['path'])
    if digest(raw)!=reference['sha256']:
        raise CycleError('acceptance receipt reference changed')
    receipt=json.loads(raw)
    if receipt_identity(receipt)!=reference['path']:
        raise CycleError('acceptance receipt reference identity mismatch')
    return receipt


def _recovery_root(receipt, read):
    """Validate immutable predecessor receipts without consulting mutable currentness."""
    seen=set()
    while 'recovery_of' in receipt:
        identity=receipt_identity(receipt)
        if identity in seen:
            raise CycleError('cyclic acceptance recovery')
        seen.add(identity)
        previous=receipt['recovery_of']
        prior=_receipt_reference(read,previous)
        validate_receipt_data(prior,receipt['subject'],read(prior['council']),proof_reader=read,_history=False)
        ignored={'owner_decision','human_approval','at','recovery_of'}
        if ({k:v for k,v in prior.items() if k not in ignored}
                != {k:v for k,v in receipt.items() if k not in ignored}):
            raise CycleError('acceptance recovery changed proposal or approval bindings')
        from owner_decision import validate_reapproval
        validate_reapproval(read,prior.get('owner_decision'),receipt.get('owner_decision'))
        receipt=prior
    return receipt_identity(receipt)


def resolve_acceptance(adr, *, proof_reader, exists, _pending=False):
    """Resolve the current immutable receipt; a present invalid binding never falls back."""
    canonical=receipt_identity({'adr':adr})
    binding_path=f'adrs/acceptances/{adr}.current.json'
    original=proof_reader(canonical)
    selected=canonical
    if exists(binding_path):
        binding=json.loads(proof_reader(binding_path))
        if (not isinstance(binding,dict) or set(binding)!={'format','adr','original','current'}
                or binding['format']!='crux.adr-acceptance-current.v1' or binding['adr']!=adr
                or binding['original']!={'path':canonical,'sha256':digest(original)}):
            raise CycleError('invalid current acceptance binding')
        receipt=_receipt_reference(proof_reader,binding['current'])
        selected=binding['current']['path']
        if selected==canonical or _recovery_root(receipt,proof_reader)!=canonical:
            raise CycleError('current acceptance must bind a recovery of its original receipt')
    else:
        if exists(f'adrs/acceptances/recoveries/{adr}') and not _pending:
            raise CycleError('current acceptance binding missing')
        receipt=json.loads(original)
        if receipt_identity(receipt)!=canonical:
            raise CycleError('invalid original acceptance identity')
    validate_receipt_data(receipt,receipt['subject'],proof_reader(receipt['council']),proof_reader=proof_reader)
    return selected,receipt


def _current_receipt(cfg, adr, *, _pending=False):
    from cycle_council import docs_proof_reader
    return resolve_acceptance(adr,proof_reader=docs_proof_reader(cfg),
                              exists=lambda name:contained(cfg.docs_root,name).exists(),_pending=_pending)


def _recover_receipt(cfg, receipt, owner_decision, captured):
    """Bind a later approval only while the caller holds the acceptance mutation lock."""
    from cycle_council import docs_proof_reader
    from owner_decision import validate_reapproval
    read=docs_proof_reader(cfg)
    validate_reapproval(read,receipt.get('owner_decision'),owner_decision['capture'])
    prior=receipt_identity(receipt)
    recovered={**receipt,'owner_decision':owner_decision['capture'],'human_approval':captured['quote'],
               'at':now(),'recovery_of':{'path':prior,'sha256':digest(read(prior))}}
    _validate_receipt(cfg,recovered,receipt['subject'])
    name=receipt_identity(recovered)
    path=contained(cfg.docs_root,name)
    if path.exists():
        retained=json.loads(read(name))
        if {k:v for k,v in retained.items() if k!='at'}!={k:v for k,v in recovered.items() if k!='at'}:
            raise CycleError('conflicting immutable acceptance recovery')
        recovered=retained
    else:
        atomic(path,recovered)
    canonical=f'adrs/acceptances/{receipt["adr"]}.json'
    atomic(contained(cfg.docs_root,f'adrs/acceptances/{receipt["adr"]}.current.json'),{
        'format':'crux.adr-acceptance-current.v1','adr':receipt['adr'],
        'original':{'path':canonical,'sha256':digest(read(canonical))},
        'current':{'path':name,'sha256':digest(read(name))}})
    return recovered


def propose(repo, proposal, *, origin, cycle_id=None, creation_approval=None, creation_subject=None):
    """Allocate an ADR only after cycle creation justification, when applicable."""
    if origin not in {'direct','whiteboard','inbox','cycle'}:
        raise CycleError('unknown ADR origin')
    if not proposal.get('title') or not proposal.get('body') or not proposal.get('governs'):
        raise CycleError('proposal requires title, body and governs')
    with locked(repo) as (cfg,directory):
        if origin=='cycle':
            if not cycle_id or not creation_approval or not creation_subject:
                raise CycleError('cycle ADR creation requires a council justification record')
            cycle=load(repo,cycle_id)
            if cycle['status']!='active' or cycle['phase']!='plan':
                raise CycleError('cycle ADR creation requires active planning')
            receipt=validate_approval(repo,creation_approval,purpose='adr-creation',subject=creation_subject)
            if receipt['cycle_id']!=cycle_id: raise CycleError('creation approval belongs to another cycle')
        elif cycle_id:
            raise CycleError('cycle-originated proposals cannot use another creation entry point')
        manifest=contained(cfg.docs_root,'manifest.yml')
        text=manifest.read_text(); data=yaml.safe_load(text)
        allocation=data.get('adr',{}).get('next_number',1)
        adrs=contained(cfg.docs_root,'adrs'); adrs.mkdir(exist_ok=True)
        used=[int(m.group(1)) for path in adrs.rglob('*.md') if (m:=re.search(r'(?:^|-)ADR-(\d+)-',path.name))]
        number=max(allocation,max(used,default=0)+1)
        identity=f"{cfg.artifact_prefix + '-' if cfg.artifact_prefix else ''}ADR-{number:04d}"
        slug=re.sub(r'[^a-z0-9]+','-',proposal['title'].lower()).strip('-')[:60] or 'decision'
        path=contained(adrs,f'{identity}-{slug}.md')
        rules = proposal['governs']
        if not isinstance(rules, list) or not rules:
            raise CycleError('governs must be a nonempty list')
        normalized = []
        for item in rules:
            rule = dict(item)
            if not all(isinstance(rule.get(k), str) and rule[k].strip() for k in ('domain', 'rule', 'scope', 'handle')):
                raise CycleError('each rule requires domain, rule, scope and handle')
            slug = rule['handle'].split('/')[-1]
            if not re.fullmatch(r'[a-z][a-z0-9]*(?:-[a-z0-9]+)*', slug):
                raise CycleError('rule handle requires a letter-led kebab-case slug')
            rule['handle'] = identity + '/' + slug
            rule['provenance'] = 'authored'
            if set(rule) - {'domain', 'rule', 'scope', 'handle', 'provenance', 'anchor', 'retires'}:
                raise CycleError('unknown governs fields')
            normalized.append(rule)
        if len({r['handle'] for r in normalized}) != len(normalized):
            raise CycleError('duplicate rule handles')
        front={'id':identity,'title':proposal['title'],'status':'Proposed','acceptance_format':'crux.adr-acceptance.v1',
               'date':now()[:10], 'proposed_date':now()[:10], 'accepted_date':None,
               'deprecated_date':None, 'superseded_date':None, 'supersedes':[],
               'superseded_by':None, 'amends':proposal.get('amends', []),
               'deciders':proposal.get('deciders', ['owner']), 'tags':proposal.get('tags', []),
               'related_briefs':proposal.get('related_briefs', []),
               'related_research':proposal.get('related_research', []), 'governs':normalized}
        content='---\n'+yaml.safe_dump(front,sort_keys=False)+'---\n\n'+proposal['body'].rstrip()+'\n'
        # Counter first: a crash leaves a gap, never a reused number.
        match=re.search(r'(?m)^adr:\s*\n(?:^[ \t]+.*\n)*',text)
        if not match: raise CycleError('manifest requires an adr allocation mapping')
        block=match.group()
        if re.search(r'(?m)^  next_number:',block):
            new=re.sub(r'(?m)^  next_number:.*$',f'  next_number: {number+1}',block)
        else: new=block+f'  next_number: {number+1}\n'
        write_text_atomic(manifest, text[:match.start()]+new+text[match.end():])
        metadata=contained(cfg.docs_root, f'adrs/proposals/{identity}.json')
        atomic(metadata, {'format':'crux.adr-proposal', 'adr':identity,
                          'subject':path.relative_to(cfg.docs_root).as_posix(),
                          'origin':origin, 'cycle_id':cycle_id,
                          'creation_approval':creation_approval, 'creation_subject':creation_subject})
        with path.open('x') as stream:
            stream.write(content)
        if cycle_id:
            cycle['decisions'].append({'path':path.relative_to(cfg.docs_root).as_posix(),'sha256':digest(path.read_bytes()),'kind':'adr','name':identity,'approval':None,'accepted':False})
            event(cycle,'adr-proposed',adr=identity);save(cfg,cycle)
        return {'adr':identity,'path':path.relative_to(cfg.docs_root).as_posix()}


class AdoptRefused(CycleError):
    def __init__(self, code, detail):
        self.code = code
        super().__init__(f'{code}: {detail}')


def adopt(repo, subject):
    """Write proposal metadata (origin legacy-adoption) for a HEAD-tracked legacy Proposed ADR; allocates nothing.

    Changes no ADR byte and grants no approval: acceptance still needs council approval of the exact bytes and,
    under council-and-human, an owner capture."""
    import subprocess
    with locked(repo) as (cfg, directory):
        try:
            path = contained(cfg.docs_root, subject)
        except CycleError as exc:
            raise AdoptRefused('adopt-not-an-active-adr', str(exc)) from None
        if (path.parent != cfg.docs_root/'adrs' or not re.fullmatch(r'(?:[A-Z][A-Z0-9]*-)?ADR-\d{4,}-.+\.md', path.name)
                or not path.is_file()):
            raise AdoptRefused('adopt-not-an-active-adr', 'adopt names an active decision file under adrs/')
        data = path.read_bytes()
        front, _ = frontmatter(data.decode())
        identity = front.get('id')
        if not isinstance(identity, str) or not path.name.startswith(identity + '-'):
            raise AdoptRefused('adopt-identity-mismatch', 'the frontmatter id must name the file')
        if front.get('status') != 'Proposed':
            raise AdoptRefused('adopt-not-proposed', f"the ADR is {front.get('status')}, not Proposed")
        if front.get('acceptance_format') != 'crux.adr-acceptance.v1':
            raise AdoptRefused('adopt-missing-acceptance-format', 'the frontmatter lacks acceptance_format crux.adr-acceptance.v1; edit it while Proposed, then adopt')
        if not isinstance(front.get('governs'), list) or not front['governs']:
            raise AdoptRefused('adopt-missing-governs', 'the frontmatter lacks a non-empty governs list; edit it while Proposed, then adopt')
        relative = path.relative_to(cfg.repo_root).as_posix()
        shown = subprocess.run(['git', '-C', str(cfg.repo_root), 'show', f'HEAD:{relative}'], capture_output=True)
        if shown.returncode != 0:
            raise AdoptRefused('adopt-not-tracked-at-head', f'{relative} is not tracked at HEAD')
        if shown.stdout != data:
            raise AdoptRefused('adopt-differs-from-head', f'{relative} differs from its bytes at HEAD; commit or restore it first')
        if contained(cfg.docs_root, f'adrs/proposals/{identity}.json').exists():
            raise AdoptRefused('adopt-metadata-exists', f'adrs/proposals/{identity}.json already exists')
        if contained(cfg.docs_root, f'adrs/provenance/{identity}.yaml').exists():
            raise AdoptRefused('adopt-historical-provenance', 'historical provenance cannot be changed by new acceptance')
        receipts = cfg.docs_root/'adrs'/'acceptances'
        if (contained(cfg.docs_root, f'adrs/acceptances/{identity}.json').exists()
                or contained(cfg.docs_root, f'adrs/acceptances/{identity}.current.json').exists()
                or (receipts/'recoveries'/identity).exists()):
            raise AdoptRefused('adopt-receipt-exists', 'an acceptance receipt already exists for this ADR')
        metadata = {'format':'crux.adr-proposal', 'adr':identity, 'subject':subject, 'origin':'legacy-adoption',
                    'cycle_id':None, 'creation_approval':None, 'creation_subject':None, 'adopted_sha256':digest(data)}
        atomic(contained(cfg.docs_root, f'adrs/proposals/{identity}.json'), metadata)
        return {'adr':identity, 'path':subject, 'metadata':f'adrs/proposals/{identity}.json', 'adopted_sha256':digest(data),
                'next':'regenerate the summaries, obtain council approval of the exact bytes, then accept'}


def accept(repo, subject, approval, *, human_approval=None, policy_basis=None, migration_package=None, migration_owner=None,
           owner_decision=None):
    """Accept a prospective proposal; resume a receipt-first interrupted write."""
    with locked(repo) as (cfg, directory):
        package_policy=None
        if policy_basis is not None:
            from adr_migration import _git, policy_at, bound_bytes
            if _git(repo,'rev-parse','HEAD').decode().strip()!=policy_basis:
                raise CycleError('package acceptance policy basis must be the action parent')
            package_policy=policy_at(repo,policy_basis)
            if migration_package is None:raise CycleError('package acceptance requires exact package identity')
            bound_bytes(repo,migration_package)
        elif migration_package is not None or migration_owner is not None:
            raise CycleError('package acceptance requires prior policy basis')
        path=contained(cfg.docs_root, subject)
        if path.parent != cfg.docs_root/'adrs' or not re.fullmatch(r'(?:[A-Z][A-Z0-9]*-)?ADR-\d{4,}-.+\.md', path.name):
            raise CycleError('ADR must be an active decision file')
        text=path.read_text()
        front, body=frontmatter(text)
        metadata_path=contained(cfg.docs_root, f"adrs/proposals/{front['id']}.json")
        if not metadata_path.is_file():
            raise CycleError('this acceptance path applies only to new-policy proposals')
        metadata=json.loads(metadata_path.read_text())
        if metadata.get('subject') != subject or metadata.get('adr') != front['id']:
            raise CycleError('proposal identity mismatch')
        if contained(cfg.docs_root, f"adrs/provenance/{front['id']}.yaml").exists():
            raise CycleError('historical provenance cannot be changed by new acceptance')
        cycle=None
        target=None
        if metadata.get('cycle_id'):
            cycle=load(repo, metadata['cycle_id'])
            target=next((d for d in cycle['decisions'] if d['path']==subject), None)
            if target is None or cycle['status'] != 'active':
                raise CycleError('an active cycle ADR dependency is required')
        receipts=contained(cfg.docs_root, 'adrs/acceptances')
        receipts.mkdir(exist_ok=True)
        receipt_path=contained(receipts, f"{front['id']}.json")
        if receipt_path.exists() or contained(receipts,f"{front['id']}.current.json").exists():
            _,receipt=_current_receipt(cfg,front['id'],_pending=front.get('status')=='Proposed')
            if receipt['subject']!=subject:
                raise CycleError('acceptance receipt subject mismatch')
            if migration_package is not None and (receipt.get('migration_package')!=migration_package or receipt.get('migration_owner')!=migration_owner):
                raise CycleError('acceptance recovery binds another package or instruction')
            if receipt['council'] != approval:
                raise CycleError('acceptance already binds another council')
            if digest(text.encode()) not in {receipt['proposed_sha256'], receipt['accepted_sha256']}:
                raise CycleError('decision changed during acceptance recovery')
            if front.get('status') == 'Proposed':
                # Receipt persistence alone did not apply this acceptance.
                validate_approval(repo, approval, purpose='adr', subject=subject)
            if receipt.get('owner_decision') is not None or owner_decision is not None:
                from owner_decision import authorize_adr, adr_result
                if owner_decision is None:
                    owner_decision = {'purpose':'adr-acceptance','cycle_id':receipt['cycle_id'],'subject':subject,
                                      'subject_sha256':receipt['proposed_sha256'],'capture':receipt['owner_decision']}
                if digest(text.encode()) == receipt['accepted_sha256']:
                    if receipt.get('owner_decision') != owner_decision.get('capture'):
                        raise CycleError('acceptance already binds another owner evidence record')
                    if cycle is not None and (not target['accepted'] or target['approval'] != approval
                                              or target['sha256'] != receipt['accepted_sha256']):
                        target.update(approval=approval, accepted=True, sha256=receipt['accepted_sha256'])
                        event(cycle, 'adr-accepted', adr=front['id'], standing='binding')
                        save(cfg, cycle)
                    return adr_result(cfg, receipt, owner_decision, already_applied=True)
                captured=authorize_adr(cfg, owner_decision, subject, metadata.get('cycle_id'), receipt['proposed_sha256'])
                if receipt.get('owner_decision') != owner_decision.get('capture'):
                    receipt=_recover_receipt(cfg,receipt,owner_decision,captured)
            updated=receipt['accepted_text']
        else:
            if front.get('status') != 'Proposed':
                raise CycleError('acceptance requires a Proposed ADR')
            council=validate_approval(repo, approval, purpose='adr', subject=subject)
            if council.get('cycle_id') != metadata.get('cycle_id'):
                raise CycleError('ADR approval belongs to another cycle')
            policy=package_policy if package_policy is not None else load_workflow_policy(repo)['adr.acceptance']
            if metadata.get('origin')=='legacy-adoption' and policy=='council-and-human':
                # A legacy ADR's human approval carries verbatim words, provenance and the presented digest.
                if human_approval is not None:
                    raise CycleError('legacy-adoption acceptance refuses a free-text human approval; record an owner capture of purpose adr-acceptance')
                if owner_decision is None:
                    raise CycleError('legacy-adoption acceptance requires an owner capture of purpose adr-acceptance under council-and-human')
            if owner_decision is not None:
                from owner_decision import authorize_adr
                captured=authorize_adr(cfg, owner_decision, subject, metadata.get('cycle_id'), digest(text.encode()))
                human_approval=captured['quote']
            if policy=='council-and-human' and not (isinstance(human_approval, str) and human_approval.strip()):
                raise CycleError('human acceptance approval is required by repository policy')
            front.update(status='Accepted', date=now()[:10], accepted_date=now()[:10])
            updated='---\n'+yaml.safe_dump(front,sort_keys=False)+'---\n'+body
            receipt={'format':'crux.adr-acceptance','adr':front['id'],'subject':subject,
                     'proposed_sha256':digest(text.encode()),'accepted_sha256':digest(updated.encode()),
                     'proposed_text':text, 'accepted_text':updated,
                     'council':approval, 'council_sha256':digest(contained(cfg.docs_root,approval).read_bytes()),
                     'cycle_id':metadata.get('cycle_id'),'policy':policy,
                     'human_approval':human_approval,'standing':'binding','at':now()}
            if owner_decision is not None:
                receipt['owner_decision']=owner_decision['capture']
            if migration_package is not None:
                receipt.update(migration_package=migration_package,policy_basis=policy_basis,migration_owner=migration_owner)
                from adr_migration import validate_package_acceptance_data
                validate_package_acceptance_data(repo,receipt,pending=True)
            _validate_receipt(cfg, receipt, subject)
            atomic(receipt_path, receipt)
        write_text_atomic(path, updated)
        if cycle is not None:
            target.update(approval=approval, accepted=True, sha256=digest(path.read_bytes()))
            event(cycle, 'adr-accepted', adr=front['id'], standing='binding')
            save(cfg, cycle)
        if receipt.get('owner_decision') is not None:
            from owner_decision import adr_result
            return adr_result(cfg, receipt, owner_decision, already_applied=False)
        return receipt


def _validate_receipt(cfg, receipt, subject):
    raw=contained(cfg.docs_root,receipt['council']).read_bytes()
    from cycle_council import docs_proof_reader
    return validate_receipt_data(receipt, subject, raw,proof_reader=docs_proof_reader(cfg))


def validate_receipt_data(receipt, subject, raw, *, proof_reader=None, _history=True):
    """Validate captured bytes and any prospective Lite retained proof."""
    if receipt.get('format') != 'crux.adr-acceptance' or receipt.get('subject') != subject or receipt.get('standing') != 'binding':
        raise CycleError('invalid acceptance receipt identity')
    proposed=receipt['proposed_text']
    accepted=receipt['accepted_text']
    if digest(proposed.encode()) != receipt['proposed_sha256'] or digest(accepted.encode()) != receipt['accepted_sha256']:
        raise CycleError('acceptance text integrity mismatch')
    before, before_body=frontmatter(proposed)
    after, after_body=frontmatter(accepted)
    if before.get('status') != 'Proposed' or after.get('status') != 'Accepted' or before_body != after_body:
        raise CycleError('acceptance must preserve decision body')
    expected=dict(before)
    expected.update(status='Accepted', date=after.get('accepted_date'), accepted_date=after.get('accepted_date'))
    if after != expected or not after.get('accepted_date') or receipt['adr'] != before.get('id'):
        raise CycleError('acceptance changed non-lifecycle fields')
    policy=receipt.get('policy')
    if policy not in {'council-and-human','council-only'}:
        raise CycleError('invalid recorded acceptance policy')
    if policy=='council-and-human' and not str(receipt.get('human_approval') or '').strip():
        raise CycleError('ADR acceptance lacks required human approval')
    if receipt.get('owner_decision') is not None:
        from owner_decision import validate_capture_evidence, _binding
        if proof_reader is None:
            raise CycleError('owner acceptance evidence requires its retained proof reader')
        capture=validate_capture_evidence(proof_reader, receipt['owner_decision'])
        if (_binding(capture) != {'purpose':'adr-acceptance','cycle_id':receipt.get('cycle_id'),
                                  'subject':subject,'subject_sha256':receipt['proposed_sha256']}
                or capture['disposition'] != 'approve' or capture['quote'] != receipt.get('human_approval')):
            raise CycleError('owner acceptance evidence does not bind this approval')
    if digest(raw) != receipt['council_sha256']:
        raise CycleError('acceptance council record changed')
    record=json.loads(raw)
    from cycle_council import validate_record
    validate_record(record, purpose='adr', subject=subject,
                    subject_sha256=receipt['proposed_sha256'], cycle_id=receipt.get('cycle_id'),proof_reader=proof_reader)
    if record.get('cycle_id') != receipt.get('cycle_id'):
        raise CycleError('council does not bind this proposal owner')
    if _history and 'recovery_of' in receipt:
        if proof_reader is None:raise CycleError('acceptance recovery requires retained proofs')
        _recovery_root(receipt,proof_reader)
    return receipt


def validate_acceptance(cfg, decision):
    path=contained(cfg.docs_root,decision['path'])
    front, body=frontmatter(path.read_text())
    _,receipt=_current_receipt(cfg,front['id'])
    if receipt['subject']!=decision['path']:
        raise CycleError('acceptance receipt subject mismatch')
    if receipt['accepted_sha256'] != digest(path.read_bytes()):
        raise CycleError('ADR acceptance does not bind current decision contents')
    return receipt
