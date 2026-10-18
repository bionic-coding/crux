#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6.0"]
# ///
"""Read-only cycle visualization. JSON is shared with the optional dashboard."""
import argparse
import json
import sys
from pathlib import Path

# Read-only entry point: sibling imports must neither create bytecode nor use project code.
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cycle_progress import view,render


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--project-root',default='.');p.add_argument('--cycle');p.add_argument('--json',action='store_true');a=p.parse_args(argv)
    try:
        document=view(a.project_root,a.cycle)
        print(json.dumps(document) if a.json else render(document));return 0
    except (ValueError,OSError,KeyError) as exc:
        print(json.dumps({'format':'crux.cycle-progress','format_version':1,'ok':False,'error':{'code':'run-invalid'}}) if a.json else str(exc));return 1

if __name__=='__main__':sys.exit(main())
