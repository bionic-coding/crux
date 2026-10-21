"""Write the owner's direct approval record for one retained IDR revision.

The record is the one `cycle_council.validate_owner_approval` accepts. The
quote is required input and is never inferred or defaulted. An agent that
records an owner approval looks like self-approval, so the supported flow is
`--print-command`: it prints one command the owner runs, and writes nothing.
"""
from datetime import date as _date
import json
from pathlib import Path
import shlex
import sys

from cycle_workflow import CycleError, contained, digest, load, tree
from cycle_council import OWNER_APPROVAL


def record_path(identity, subject):
    return f"cycles/{identity}/approvals/owner-{Path(subject).stem}.json"


def write_owner_approval(repo, identity, subject, quote, conversation, date=None):
    """Create the approval record; refuse empty input, a missing subject, or an existing record."""
    if not isinstance(quote, str) or not quote.strip():
        raise CycleError('owner approval requires the owner\'s non-empty verbatim quote')
    if not isinstance(conversation, str) or not conversation.strip():
        raise CycleError('owner approval requires a non-empty conversation reference')
    cfg = tree(repo)
    load(repo, identity)
    parts = Path(subject).parts
    if len(parts) < 3 or parts[0] != 'cycles' or parts[1] != identity:
        raise CycleError('subject must be a retained decision of this cycle')
    source = contained(cfg.docs_root, subject)
    if not source.is_file():
        raise CycleError('subject file does not exist')
    rel = record_path(identity, subject)
    target = contained(cfg.docs_root, rel)
    record = {'format': OWNER_APPROVAL, 'purpose': 'idr', 'cycle_id': identity, 'subject': subject,
              'subject_sha256': digest(source.read_bytes()), 'origin': 'owner-conversation',
              'quote': quote, 'date': date or _date.today().isoformat(), 'conversation': conversation}
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with target.open('x') as stream:
            stream.write(json.dumps(record, indent=2) + '\n')
    except FileExistsError:
        raise CycleError(f'owner approval record already exists: {rel}')
    return rel


def printable_command(repo, identity, subject, quote, conversation, date=None):
    """Return one shell-safe command line for the owner to run; write nothing."""
    if not isinstance(quote, str) or not quote.strip():
        raise CycleError('owner approval requires the owner\'s non-empty verbatim quote')
    script = Path(__file__).resolve().with_name('cycle.py')
    q = shlex.quote
    return ' '.join(['uv', 'run', q(str(script)), '--repo-root', q(str(Path(repo).resolve())),
                     'owner-approval', q(identity), '--subject', q(subject),
                     q('--quote=' + quote), q('--conversation=' + conversation),
                     '--date', q(date or _date.today().isoformat()), '--approve'])
