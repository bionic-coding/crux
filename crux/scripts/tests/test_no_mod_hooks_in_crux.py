"""No file under the crux plugin directory registers a mod hook.

A mod hook is a module Claude Code loads into its own interface. The opt-in
`crux-mods` plugin owns every such hook, so installing crux alone changes
nothing. This test walks the plugin directory that holds this file and refuses
four shapes:

  * a `hooks/hooks.json` file,
  * a `hooks` key in a plugin manifest (`.claude-plugin/plugin.json` or
    `plugin.json`),
  * a `.ts`, `.tsx`, `.mts`, `.cts`, `.js`, `.jsx`, `.mjs` or `.cjs` file that
    names the `claude-code` module, which is how a mod gets its types and its
    `register` entry point; a symlinked file with one of those suffixes is
    reported too, because the scan does not follow it,
  * a `.claude-plugin/types/` directory, the residue Claude Code writes when it
    hot-reloads a mod.

The plugin directory comes from this file's own path, so the test holds in the
staged crux-only artifact `sync.sh` runs the suite against. Every shape has a
positive control: the same scanner flags a seeded temporary tree, so a scanner
that silently stopped matching would fail here rather than pass an empty tree.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
import unittest
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[2]

# Directories that hold third-party or generated material, never plugin source.
_PRUNE = {".cache", "node_modules", "__pycache__", ".git"}
# Every suffix a hooks module, or a file it imports, may carry.
_TS_SUFFIXES = {".ts", ".tsx", ".mts", ".cts", ".js", ".jsx", ".mjs", ".cjs"}
_MANIFESTS = (".claude-plugin/plugin.json", "plugin.json")
# A string literal naming the module or one of its subpaths, in any import form.
_CLAUDE_CODE_MODULE = re.compile(r"""['"]claude-code(?:/[^'"]*)?['"]""")


def scan(plugin_root: Path) -> list[str]:
    """Return one finding per mod-hook registration under `plugin_root`."""
    findings: list[str] = []

    for rel in _MANIFESTS:
        manifest = plugin_root / rel
        if not manifest.is_file():
            continue
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            findings.append(f"{rel}: unreadable manifest ({type(exc).__name__}); cannot show it has no hooks key")
            continue
        if isinstance(data, dict) and "hooks" in data:
            findings.append(f"{rel}: carries a `hooks` key")

    for dirpath, dirnames, filenames in os.walk(plugin_root):
        dirnames[:] = sorted(d for d in dirnames if d not in _PRUNE)
        here = Path(dirpath)
        rel_dir = here.relative_to(plugin_root)

        if rel_dir.name == "hooks" and "hooks.json" in filenames:
            findings.append(f"{(rel_dir / 'hooks.json').as_posix()}: a hooks/hooks.json file")
        if rel_dir.as_posix().endswith(".claude-plugin/types") or rel_dir.as_posix() == ".claude-plugin/types":
            findings.append(f"{rel_dir.as_posix()}: a .claude-plugin/types directory")

        for name in sorted(filenames):
            path = here / name
            if path.suffix not in _TS_SUFFIXES:
                continue
            if path.is_symlink():
                findings.append(f"{path.relative_to(plugin_root).as_posix()}: a symlinked module file; cannot show it does not import claude-code")
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                findings.append(f"{path.relative_to(plugin_root).as_posix()}: unreadable source; cannot show it does not import claude-code")
                continue
            if _CLAUDE_CODE_MODULE.search(text):
                findings.append(f"{path.relative_to(plugin_root).as_posix()}: imports claude-code")

    return sorted(findings)


class NoModHooksInCruxTests(unittest.TestCase):
    def test_plugin_root_is_the_directory_that_holds_this_test(self):
        # The walk is vacuous if the root is wrong; pin that it found the plugin.
        self.assertTrue((PLUGIN_ROOT / "scripts" / "tests" / Path(__file__).name).is_file())
        self.assertTrue((PLUGIN_ROOT / ".claude-plugin" / "plugin.json").is_file())

    def test_crux_registers_no_mod_hook(self):
        self.assertEqual(scan(PLUGIN_ROOT), [])


class ScannerPositiveControlTests(unittest.TestCase):
    """The scanner flags each shape in a seeded tree, and only that shape."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "crux"
        (self.root / ".claude-plugin").mkdir(parents=True)
        (self.root / ".claude-plugin" / "plugin.json").write_text(
            json.dumps({"name": "crux", "version": "1.0.0"}), encoding="utf-8"
        )

    def _write(self, rel: str, body: str) -> None:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")

    def test_clean_tree_has_no_findings(self):
        self._write("scripts/ok.ts", "export const x = 1\n")
        self._write("hooks/notes.md", "not a registration\n")
        self.assertEqual(scan(self.root), [])

    def test_flags_hooks_json(self):
        self._write("hooks/hooks.json", '{"modules": ["./register.tsx"]}')
        self.assertEqual(scan(self.root), ["hooks/hooks.json: a hooks/hooks.json file"])

    def test_flags_hooks_key_in_bare_manifest(self):
        (self.root / ".claude-plugin" / "plugin.json").write_text(
            json.dumps({"name": "crux", "hooks": "./hooks/hooks.json"}), encoding="utf-8"
        )
        self.assertEqual(scan(self.root), [".claude-plugin/plugin.json: carries a `hooks` key"])

    def test_flags_hooks_key_in_rich_manifest(self):
        self._write("plugin.json", json.dumps({"name": "crux", "hooks": {}}))
        self.assertEqual(scan(self.root), ["plugin.json: carries a `hooks` key"])

    def test_flags_unparseable_manifest(self):
        (self.root / ".claude-plugin" / "plugin.json").write_text("{not json", encoding="utf-8")
        findings = scan(self.root)
        self.assertEqual(len(findings), 1)
        self.assertIn("unreadable manifest", findings[0])

    def test_flags_typescript_importing_claude_code(self):
        for suffix, body in (
            (".ts", "import type { Register } from 'claude-code'\n"),
            (".tsx", 'import { register } from "claude-code"\n'),
            (".mts", "const m = await import('claude-code')\n"),
            (".cts", "const m = require('claude-code/ui')\n"),
        ):
            with self.subTest(suffix=suffix):
                rel = f"src/mod{suffix}"
                self._write(rel, body)
                self.assertEqual(scan(self.root), [f"{rel}: imports claude-code"])
                (self.root / rel).unlink()

    def test_flags_javascript_importing_claude_code(self):
        # A hooks module may be named .js, .jsx, .mjs or .cjs as well as a TypeScript suffix.
        for suffix in (".js", ".jsx", ".mjs", ".cjs"):
            with self.subTest(suffix=suffix):
                rel = f"src/mod{suffix}"
                self._write(rel, "import { register } from 'claude-code'\n")
                self.assertEqual(scan(self.root), [f"{rel}: imports claude-code"])
                (self.root / rel).unlink()

    def test_flags_symlinked_module_file(self):
        # The scan does not follow a link, so it cannot show a linked module clean.
        self._write("src/real.txt", "import { register } from 'claude-code'\n")
        (self.root / "src" / "mod.ts").symlink_to(self.root / "src" / "real.txt")
        self.assertEqual(scan(self.root), ["src/mod.ts: a symlinked module file; cannot show it does not import claude-code"])

    def test_typescript_not_naming_the_module_is_clean(self):
        self._write("src/other.ts", "import { x } from 'claude-code-helpers'\n")
        self.assertEqual(scan(self.root), [])

    def test_flags_types_residue_directory(self):
        self._write(".claude-plugin/types/claude-code.d.ts", "declare module 'x' {}\n")
        self.assertEqual(
            scan(self.root), [".claude-plugin/types: a .claude-plugin/types directory"]
        )

    def test_a_types_directory_elsewhere_is_not_residue(self):
        self._write("skills/types/readme.md", "x\n")
        self.assertEqual(scan(self.root), [])

    def test_pruned_directories_are_not_walked(self):
        self._write(".cache/dep/hooks/hooks.json", "{}")
        self.assertEqual(scan(self.root), [])


if __name__ == "__main__":
    unittest.main()
