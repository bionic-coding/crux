"""Retained consumers on cycle_store: the deleted-module import scan and the canonical bytes of retained records.

The typed cycle engine is deleted. The scan reads every Python file under crux/ and tools/, tests
included, for an import of a deleted module: `import` and `from` statements at any depth, and
`__import__` or `importlib.import_module` calls with a literal name. No file may import one, and no
deleted module's file exists.

The canonical-bytes tests recompute the digests that committed council, acceptance, migration and
queue history records carry, with cycle_store's `digest` and `encoded`.
"""
import ast
import json
from pathlib import Path
import subprocess
import sys
import unittest

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent
sys.path.insert(0, str(SCRIPTS))
import cycle_store
from _dev_surface import REPO_ROOT, TREE, require_dev_surface

# Every module the engine cutover deleted (IDR engine-cutover A8). No file named here exists.
DELETED = frozenset({
    'cycle_workflow', 'cycle_ops', 'cycle_execution', 'cycle_dispatch', 'cycle_reconcile', 'cycle_commit',
    'cycle_context', 'cycle_context_read', 'cycle_hosts', 'cycle_classify', 'cycle_questions',
    'cycle_doc_classify', 'cycle_prereqs', 'cycle_activity', 'cycle_summary', 'cycle_timing',
    'cycle_worktrees', 'cycle_local_skills', 'cycle_legacy_cli', 'owner_approval',
})
FUNCTION, MODULE = 'function', 'module'
# Retained consumers once moved off the typed engine; importing them loads no deleted module.
RETAINED = ('cycle', 'cycle_writer', 'cycle_runtime', 'cycle_store', 'cycle_history', 'cycle_progress', 'cycle_queue',
            'cycle_council', 'cycle_council_events', 'council_native', 'council_policy', 'decision_policy',
            'owner_decision', 'adr_migration', 'adr_migration_publication', 'migration_receipts')
# Deliberately unparsable fixtures of the code-docs extractor.
UNPARSABLE = ('crux/scripts/tests/fixtures/python_code_docs/',)


def literal_name(call):
    """The literal module name an `__import__(...)` or `importlib.import_module(...)` call loads, else None."""
    func = call.func
    named = (isinstance(func, ast.Name) and func.id in ('__import__', 'import_module')
             or isinstance(func, ast.Attribute) and func.attr == 'import_module')
    if named and call.args and isinstance(call.args[0], ast.Constant) and isinstance(call.args[0].value, str):
        return call.args[0].value
    return None


def deleted_imports(path):
    """{(deleted module, 'module' or 'function')} for every import of a deleted module in `path`."""
    found = set()

    def visit(node, nested):
        for child in ast.iter_child_nodes(node):
            names = []
            if isinstance(child, ast.Import):
                names = [alias.name for alias in child.names]
            elif isinstance(child, ast.ImportFrom) and child.module and not child.level:
                names = [child.module]
            elif isinstance(child, ast.Call) and literal_name(child):
                names = [literal_name(child)]
            for name in names:
                if name.split('.')[0] in DELETED:
                    found.add((name.split('.')[0], FUNCTION if nested else MODULE))
            visit(child, nested or isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)))

    visit(ast.parse(path.read_text(encoding='utf-8')), False)
    return found


def inventory(root):
    rows = {}
    for base in ('crux', 'tools'):
        for path in sorted((root / base).rglob('*.py')):
            relative = path.relative_to(root).as_posix()
            if '/node_modules/' in relative or relative.startswith(UNPARSABLE):
                continue
            found = deleted_imports(path)
            if found:
                rows[relative] = found
    return rows


class InventoryTests(unittest.TestCase):
    def test_no_file_imports_a_deleted_module(self):
        require_dev_surface(self, REPO_ROOT / 'tools', 'tools/ sources')
        self.assertEqual(inventory(REPO_ROOT), {})

    def test_scan_sees_each_import_form(self):
        """Positive control: the scan reports module-level, nested and literal dynamic imports of a deleted module."""
        import tempfile
        with tempfile.TemporaryDirectory() as scratch:
            path = Path(scratch) / 'probe.py'
            path.write_text('import cycle_commit\n\ndef f():\n    from cycle_workflow import load\n'
                            '    importlib.import_module("cycle_ops")\n\n__import__("cycle_hosts")\n')
            self.assertEqual(deleted_imports(path), {('cycle_commit', MODULE), ('cycle_workflow', FUNCTION),
                                                     ('cycle_ops', FUNCTION), ('cycle_hosts', MODULE)})

    def test_deleted_modules_are_gone(self):
        self.assertTrue((SCRIPTS / 'cycle_store.py').is_file())  # control: SCRIPTS holds the retained modules
        for name in sorted(DELETED):
            with self.subTest(name=name):
                self.assertFalse((SCRIPTS / f'{name}.py').exists())

    def test_retained_consumers_load_no_deleted_module(self):
        code = ('import json, sys\n'
                f'sys.path.insert(0, {str(SCRIPTS)!r})\n'
                f'for name in {list(RETAINED)!r}:\n'
                '    __import__(name)\n'
                'print(json.dumps(sorted(sys.modules)))\n')
        done = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, cwd=SCRIPTS)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(set(json.loads(done.stdout)) & DELETED, set())


class CanonicalBytesTests(unittest.TestCase):
    def setUp(self):
        self.docs = REPO_ROOT / TREE
        require_dev_surface(self, self.docs / 'adrs', 'committed decision records')

    def test_council_records_recompute_their_seal(self):
        checked = 0
        for path in sorted(self.docs.rglob('*.json')):
            if 'councils' not in path.relative_to(self.docs).parts:
                continue
            value = json.loads(path.read_bytes())
            if not isinstance(value, dict) or 'record_sha256' not in value:
                continue
            payload = dict(value)
            sealed = payload.pop('record_sha256')
            with self.subTest(path=path.relative_to(self.docs).as_posix()):
                self.assertEqual(cycle_store.digest(cycle_store.encoded(payload)), sealed)
            checked += 1
        self.assertGreater(checked, 0)

    def test_acceptance_records_recompute_their_digests(self):
        checked = 0
        for path in sorted((self.docs / 'adrs/acceptances').glob('*.json')):
            raw = path.read_bytes()
            value = json.loads(raw)
            with self.subTest(path=path.name):
                self.assertEqual(cycle_store.encoded(value), raw)
                for text, key in (('proposed_text', 'proposed_sha256'), ('accepted_text', 'accepted_sha256')):
                    if text in value:
                        self.assertEqual(cycle_store.digest(value[text].encode()), value[key])
                        checked += 1
        self.assertGreater(checked, 0)

    def test_migration_receipts_recompute_their_bindings(self):
        checked = 0
        for path in sorted((self.docs / 'adrs/migrations/receipts').glob('*.json')):
            raw = path.read_bytes()
            value = json.loads(raw)
            with self.subTest(path=path.name):
                self.assertEqual(cycle_store.encoded(value), raw)
                for key in ('approval', 'package', 'publication'):
                    bound = value[key]
                    self.assertEqual(cycle_store.digest((REPO_ROOT / bound['path']).read_bytes()), bound['sha256'])
                    checked += 1
        self.assertGreater(checked, 0)

    def test_queue_history_recomputes_its_source_digest(self):
        import cycle_queue
        checked = 0
        for path in sorted((self.docs / 'queue/history/items').glob('Q-*.json')):
            value = json.loads(path.read_bytes())
            item = json.dumps(value['item'], ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
            with self.subTest(path=path.name):
                self.assertEqual(cycle_store.digest(item), value['source_sha256'])
                self.assertEqual(cycle_queue._item_digest(value['item']), value['source_sha256'])
            checked += 1
        self.assertGreater(checked, 0)


if __name__ == '__main__':
    unittest.main()
