"""Retired entry points of the historical-format migration application.

`apply` published an immutable witness for one historical-format batch and refreshed seven
derived outputs. `dry_run` planned that application. Both now refuse every call with the
named refusal `historical-migration-writes-retired`, and neither reads, stages or writes
anything before it: the refusal is each function's first statement.

Verification is unchanged. Every authority reader (`implementation_migration.authority_view`,
publication discovery and proof, `binding_memo.validate_historical_migration_binding`) still
proves an existing historical publication, and none of them imports this module. New
migrations use the prospective format (`adr-migration.py`, migration receipts).

`implementation_migration.dry_run` delegates here by name, so this module keeps both
function names and their signatures.
"""
from __future__ import annotations

import implementation_migration as migration

CODE = "historical-migration-writes-retired"
REMEDY = ("Propose clause migrations in the prospective format through migrate-adrs "
          "(adr-migration.py). Existing historical publications are still verified by every "
          "authority reader.")


def _retired():
    return migration._with_remedy(migration.Refused(CODE), REMEDY)


def apply(repo_root, batch_path):
    """Refuse: historical-format migration application is retired."""
    raise _retired()


def dry_run(repo_root, batch_path):
    """Refuse: planning a historical-format migration application is retired."""
    raise _retired()
