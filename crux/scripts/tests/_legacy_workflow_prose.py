"""Explicit pre-cycle instruction fixtures; never used by runtime readers.

Only retired promptbook prose contracts read these fixtures. Current workflow
contracts are asserted by test_cycle_instruction_contracts against shipped files.
"""
from pathlib import Path
PLUGIN = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).parent / "fixtures" / "legacy_workflow"
def legacy_path(path):
    path = Path(path)
    try:
        relative = path.relative_to(PLUGIN)
    except ValueError:
        return path
    fixture = FIXTURES / relative
    fixture = fixture.with_name(fixture.name + ".fixture")
    return fixture if fixture.is_file() else path
