"""Frozen legacy cycle records for the historical-reader tests.

`fixtures/cycle-history/fresh/` holds records the typed engine wrote on creation (one per type, a
paused quick-fix, and the quick-fix stepped back to schema versions 2 and 1). The other folders under
`fixtures/cycle-history/` and `fixtures/cycle-records/` are committed records copied byte for byte.
A test copies a record into a temporary tree and changes it as JSON; no typed-engine code runs.
"""
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
HISTORY = HERE / 'fixtures/cycle-history'
RECORDS = HERE / 'fixtures/cycle-records'
FRESH = HISTORY / 'fresh'


def tree(root):
    """A minimal documentation tree the readers accept."""
    root = Path(root)
    (root / 'bionic').mkdir(parents=True, exist_ok=True)
    (root / 'bionic/manifest.yml').write_text('schema_version: "5"\nconcerns_enabled: [adrs]\n')
    return root


def fresh(name):
    """A parsed copy of a fresh fixture record: `dev`, `iterate`, `refactor`, `quick-fix`, `release`,
    `quick-fix-paused`, `quick-fix-v2` or `quick-fix-v1`."""
    return json.loads((FRESH / f'{name}.json').read_text())


def put(root, doc, identity=None):
    """Write `doc` as the record of `identity` (default: its own id) and return the id."""
    doc = dict(doc)
    if identity is not None:
        doc['id'] = identity
    folder = Path(root) / 'bionic/cycles' / doc['id']
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'cycle.json').write_text(json.dumps(doc, indent=2, sort_keys=True) + '\n')
    return doc['id']


def path_of(root, identity):
    return Path(root) / 'bionic/cycles' / identity / 'cycle.json'


def read(root, identity):
    return json.loads(path_of(root, identity).read_text())


def copy(root, source):
    """Copy a committed fixture record folder (its cycle.json and any review reports) into the tree."""
    target = Path(root) / 'bionic/cycles' / source.name
    shutil.copytree(source, target)
    return source.name
