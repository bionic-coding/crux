"""Test helper: turn a freshly created cycle record into one created before the Verify rename.

A record without `phase_names` names the phase after Build 'test'. Tests that drive that phase by its old name
through direct writes call `make_historical` right after `create`, so they keep covering historical records."""
import json
from pathlib import Path


def rename_phase(value, old, new):
    """Rename every `phase` value `old` to `new` anywhere in a decoded record, history snapshots included."""
    if isinstance(value, dict):
        for key, item in value.items():
            if key == 'phase' and item == old:
                value[key] = new
            else:
                rename_phase(item, old, new)
    elif isinstance(value, list):
        for item in value:
            rename_phase(item, old, new)


def make_historical(repo, cycle_id):
    """Strip phase_names from the stored record; return the record path."""
    matches = sorted(Path(repo).glob(f'**/cycles/{cycle_id}/cycle.json'))
    path = matches[0]
    raw = json.loads(path.read_text())
    raw.pop('phase_names', None)
    rename_phase(raw, 'verify', 'test')
    path.write_text(json.dumps(raw, indent=2, sort_keys=True) + '\n')
    return path
