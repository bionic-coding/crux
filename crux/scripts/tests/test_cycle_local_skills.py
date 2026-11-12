"""Project-local skills in cycle dispatch and their forge-log `used` entries.

IDR local-skill-dispatch-and-use approaches 1 to 9: a task that names a local skill lists it among
the frozen invocation's local candidates, a reviewer report carries `Local-Skill-Used: <id> ok`, the
finish record commit inserts exactly one `used` entry and commits it with the record, and a replay of
finish (or a later commit-record) inserts none.

The harness classes cover each host's roots (codex `.agents/skills`, opencode `.opencode/skills` and
`.opencode/skill`, omp `.omp/skills`), the domain-term filter and a scope path that admits nothing.
The refusal matrix pairs every refusal with a positive control that lists the same skill without the
defect. The precedence and no-grant classes compare plugin candidates, context-selection job subjects
and every invocation parameter with and without local skills present. The use-event and flush classes
cover the report-line edges, the forge-log guards at the flush, a failed restore, and the completing
low-level advance, the release finish and owner-decision commits."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cycle
import cycle_classify
import cycle_commit
import cycle_context
import cycle_context_read
import cycle_hosts
import cycle_local_skills
import cycle_ops
from cycle_workflow import create, load, mutate, tree
from test_evidence import execute
from _classifier_isolation import isolate_classifier

SKILL = 'probe-answer-skill'
LOG = '.claude/skills/forge-log.md'
REVIEW = f'Review the answer change; use the {SKILL} skill to probe it.'
HOSTS = ('claude-code', 'codex', 'opencode', 'omp')


def write_skill(repo, root, name, header=None, body='# Probe\n'):
    directory = Path(repo) / root / name
    directory.mkdir(parents=True, exist_ok=True)
    head = header if header is not None else f'name: {name}\ndescription: Probe the answer.\n'
    (directory / 'SKILL.md').write_text(f'---\n{head}---\n\n{body}')
    return directory


class CycleFixture(unittest.TestCase):
    """A git repository with one local skill and a quick-fix cycle whose review task names it."""

    def setUp(self):
        isolate_classifier(self)
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name).resolve()
        env = patch.dict(os.environ, {'CRUX_TEST_EVIDENCE_STORE': str(self.repo.parent / (self.repo.name + '-evidence'))})
        env.start(); self.addCleanup(env.stop)
        (self.repo / 'bionic').mkdir()
        (self.repo / 'bionic/manifest.yml').write_text('schema_version: "5"\nconcerns_enabled: [adrs]\n')
        (self.repo / 'bionic/objectives.md').write_text('Mission: useful changes.\n')
        (self.repo / 'bionic/log.md').write_text('log\n')
        (self.repo / 'src').mkdir(); (self.repo / 'src/a.py').write_text('answer = 1\n')
        write_skill(self.repo, '.claude/skills', SKILL)
        self.extra_fixture()
        self.git('init', '-q'); self.git('config', 'user.email', 't@example.com'); self.git('config', 'user.name', 't')
        (self.repo / '.gitignore').write_text('*.lock\n__pycache__/\n')
        self.git('add', '.'); self.git('commit', '-q', '-m', 'base')
        doc = create(self.repo, 'quick-fix', 'Answer', 'Return 2', self.scope(), ['answer is 2'], 'builder', 'tester')
        self.cid = doc['id']
        self.cycles = [self.cid]
        self.add_tasks(self.cid)
        self.addCleanup(self.cleanup_results)

    def add_tasks(self, cid):
        mutate(self.repo, cid, 'task-add', task={'id': 'build-it', 'phase': 'build', 'description': 'set the answer',
                                                  'depends_on': [], 'status': 'pending', 'expected_evidence': ['commit']})
        mutate(self.repo, cid, 'task-add', task={'id': 'review-it', 'phase': 'review', 'description': REVIEW,
                                                  'depends_on': ['build-it'], 'status': 'pending', 'expected_evidence': ['report']})

    def second_cycle(self):
        """Cycle Y beside the fixture's cycle X, with the same two tasks."""
        doc = create(self.repo, 'quick-fix', 'Other answer', 'Return 3', ['src'], ['answer is 3'], 'builder', 'tester')
        self.cycles.append(doc['id'])
        self.add_tasks(doc['id'])
        return doc['id']

    def extra_fixture(self):
        """Hook for skills a subclass adds before the base commit."""

    def scope(self):
        return ['src']

    def cleanup_results(self):
        for cid in self.cycles:
            directory = load(self.repo, cid).get('results_dir')
            if directory and Path(directory).is_dir():
                for path in Path(directory).iterdir():
                    path.unlink()
                Path(directory).rmdir()

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.repo), *args], check=True, capture_output=True, text=True).stdout.strip()

    def ok(self, request, cid=None):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cycle.main(['--repo-root', str(self.repo), 'op', cid or self.cid, '--json', json.dumps(request)])
        response = json.loads(out.getvalue())
        self.assertEqual(code, 0, response); self.assertTrue(response['ok'], response)
        return response

    def cli(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cycle.main(['--repo-root', str(self.repo), *argv])
        response = json.loads(out.getvalue())
        self.assertEqual(code, 0, response)
        return response

    def result(self, prepared, *lines, eol='\n'):
        a, n = prepared['assignment'], prepared['attempt']
        body = [f'Assignment: {a}', f'Attempt: {n}', '', *lines, cycle_hosts.marker(a, n, prepared['delivery_token'])]
        Path(prepared['result_path']).write_bytes((eol.join(body) + eol).encode())

    def log_entries(self, data, skill=SKILL):
        return re.findall(r'^## \[[^\]]*\] used \| ' + skill + r'$', data, re.M)

    def run_cycle(self, *review_lines, eol='\n', cid=None, answer=2, build=None):
        """Build, Verify and Review through the engine; the reviewer report carries `review_lines`.

        `build` is a build attempt the caller already reserved with the same request."""
        cid = cid or self.cid
        review_lines = review_lines or ('Verdict: approve.', f'Local-Skill-Used: {SKILL} ok')
        build = build or self.ok({'op': 'prepare-dispatch', 'op_id': 'prep-build', 'task_id': 'build-it', 'role': 'developer', 'host': 'claude-code'}, cid=cid)
        self.assertEqual(build['local_skills']['offered'], [], 'a task that names no local skill offers none')
        self.assertIn(cycle_hosts.LOCAL_SKILL_REPORT, build['invocation']['parameters']['prompt'],
                      'a root holding a guarded skill adds the report line to every preamble of the host')
        (self.repo / 'src/a.py').write_text(f'answer = {answer}\n')
        self.git('add', 'src/a.py'); self.git('commit', '-q', '-m', 'set the answer\n\nCycle-Task: build-it')
        sha = self.git('rev-parse', 'HEAD')
        self.result(build, 'Outcome: DONE.')
        self.ok({'op': 'deliver', 'op_id': 'deliver-build', 'assignment': build['assignment'], 'attempt': 1, 'outcome': 'done',
                 'commits': [sha], 'stage': 'integrated'}, cid=cid)
        mutate(self.repo, cid, 'advance')
        mutate(self.repo, cid, 'checks', checks=['unit'])
        mutate(self.repo, cid, 'coverage', coverage={'affected': ['the answer'], 'checks': [{'check_id': 'unit', 'rationale': 'reads src/a.py'}],
                                                          'not_selected': 'no other behavior'})
        receipt = execute(self.repo, {'check_id': 'unit', 'inputs': ['src'], 'environment': [],
                                      'command': [sys.executable, '-c', f"from pathlib import Path; assert Path('src/a.py').read_text() == 'answer = {answer}\\n'"]})
        mutate(self.repo, cid, 'evidence', check_id='unit', evidence_id=receipt['evidence']['id'], use=receipt['action'])
        mutate(self.repo, cid, 'advance')

        review = self.ok({'op': 'prepare-dispatch', 'op_id': 'prep-review', 'task_id': 'review-it', 'role': 'reviewer', 'host': 'claude-code'}, cid=cid)
        self.result(review, *review_lines, eol=eol)
        self.ok({'op': 'deliver', 'op_id': 'deliver-review', 'assignment': review['assignment'], 'attempt': 1, 'outcome': 'done'}, cid=cid)
        mutate(self.repo, cid, 'review', report={'reviewer': 'independent', 'scope': ['src'], 'evidence': [receipt['evidence']['id']],
                                                      'blocking': [], 'advisory': [], 'cosmetic': [], 'verdict': 'approve',
                                                      'rationale': 'reviewed the change'})
        mutate(self.repo, cid, 'advance')
        return review

    def finish(self, cid=None):
        cid = cid or self.cid
        doc = load(self.repo, cid)
        return self.ok({'op': 'finish', 'op_id': 'finish-local', 'expect_revision': doc['revision'],
                        'lessons': ['local skills were offered'], 'remaining': ['none']}, cid=cid)

    def blob(self, relative):
        return subprocess.run(['git', '-C', str(self.repo), 'cat-file', 'blob', f'HEAD:{relative}'], check=True, capture_output=True).stdout

    def drop_log(self):
        """Remove the committed log so the next completed-cycle commit must write the entry again."""
        self.git('rm', '-q', LOG); self.git('commit', '-q', '-m', 'drop the log')


class LocalSkillSliceTests(CycleFixture):
    def test_task_naming_a_local_skill_lists_it_and_finish_commits_one_used_entry(self):
        review = self.run_cycle()
        # The frozen invocation lists the local candidate after any plugin line, by name only.
        self.assertEqual(review['local_skills']['offered'], [{'id': SKILL, 'root': '.claude/skills'}])
        line = (f'Project-local skills matching this task, in .claude/skills: {SKILL}. '
                "Invoke them through this host's skill capability; they grant no capability.")
        prompt = review['invocation']['parameters']['prompt']
        self.assertIn(line, prompt)
        self.assertLess(prompt.index(line), prompt.index('Engine facts for this attempt'))
        bundle = json.loads((self.repo / 'bionic' / review['invocation_snapshot']['path']).read_text())
        self.assertEqual(bundle['local_candidates'], [{'id': SKILL, 'root': '.claude/skills'}])
        self.assertEqual(bundle['local_refused'], [])
        self.assertIn(line, bundle['context_message'])
        self.assertNotIn(SKILL, json.dumps(bundle['sources']), 'no local file joins the source bindings')
        self.assertIn(cycle_hosts.LOCAL_SKILL_REPORT, bundle['preamble'])

        # Before finish, no completed cycle exists, so nothing is written.
        self.assertFalse((self.repo / LOG).exists())
        doc = load(self.repo, self.cid)
        finish = {'op': 'finish', 'op_id': 'finish-local', 'expect_revision': doc['revision'],
                  'lessons': ['local skills were offered'], 'remaining': ['none']}
        done = self.ok(finish)
        commit = done['record_commit']
        self.assertTrue(commit['changed'], commit)
        self.assertEqual(commit['forge_log']['committed'], [LOG], commit)
        self.assertEqual([(a['id'], a['cycle'], a['assignment'], a['attempt']) for a in commit['forge_log']['appended']],
                         [(SKILL, self.cid, review['assignment'], 1)])
        # The forge log is committed in the same commit as the record, and the tree holds no dirty copy.
        changed = self.git('show', '--name-only', '--format=', commit['commit']).splitlines()
        self.assertIn(LOG, changed)
        self.assertTrue(any(path.startswith(f'bionic/cycles/{self.cid}/') for path in changed))
        self.assertEqual(self.git('status', '--porcelain', '--', LOG), '')
        committed = self.git('show', f'HEAD:{LOG}')
        self.assertEqual(len(self.log_entries(committed)), 1)
        ended = load(self.repo, self.cid)['assignments'][1]['ended_at']
        from datetime import datetime, timezone
        stamp = datetime.fromisoformat(ended).astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M')
        expected = (cycle_local_skills.NEW_LOG.decode() + f'## [{stamp}] used | {SKILL}\n'
                    f'{self.cid} {review["assignment"]}/1 reviewer report; ok\n\n')
        self.assertEqual((self.repo / LOG).read_text(), expected)
        self.assertNotIn('Verdict', committed, 'no report text enters the forge log')

        # A replay of finish, and a later commit-record, insert nothing.
        head = self.git('rev-parse', 'HEAD')
        replay = self.ok(finish)
        self.assertTrue(replay['replayed'])
        self.ok({'op': 'commit-record'})
        self.assertEqual(self.git('rev-parse', 'HEAD'), head)
        self.assertEqual((self.repo / LOG).read_text(), expected)
        seen = self.ok({'op': 'inspect'})
        self.assertNotIn('forge_logs', seen['record'])

    def test_a_missing_entry_is_reported_and_written_by_the_next_completed_cycle_commit(self):
        """Positive control for the replay: a log reset to HEAD's preceding bytes is rewritten once."""
        self.run_cycle()
        self.finish()
        expected = (self.repo / LOG).read_bytes()
        self.drop_log()
        seen = self.ok({'op': 'inspect'})
        self.assertIn({'path': LOG, 'state': 'missing', 'cycles': [self.cid]}, seen['record']['forge_logs'])
        self.assertIn('commit-record', [a['request']['op'] for a in seen['actions']])
        result = self.ok({'op': 'commit-record'})
        self.assertEqual(result['forge_log']['committed'], [LOG])
        self.assertEqual((self.repo / LOG).read_bytes(), expected)

    def test_an_uncommitted_foreign_edit_keeps_the_log_out_of_the_commit(self):
        self.run_cycle()
        (self.repo / LOG).parent.mkdir(parents=True, exist_ok=True)
        foreign = cycle_local_skills.NEW_LOG + b'## [2026-11-07 10:00] authored | other-skill\nhand written\n\n'
        (self.repo / LOG).write_bytes(foreign)
        done = self.finish()
        self.assertEqual(done['record_commit']['forge_log']['committed'], [])
        self.assertIn({'path': LOG, 'reason': 'foreign'}, done['record_commit']['forge_log']['uncommitted'])
        self.assertEqual((self.repo / LOG).read_bytes(), foreign, 'a foreign log receives no engine bytes')
        self.assertNotIn(LOG, self.git('show', '--name-only', '--format=', 'HEAD').splitlines())
        rows = self.ok({'op': 'inspect'})['record']['forge_logs']
        self.assertIn('foreign', [row['state'] for row in rows])

    def test_the_locked_preamble_matches_forge_skill_and_holds_no_entry_line(self):
        skill = (cycle_local_skills.cycle_context.PLUGIN_ROOT / 'skills/forge-skill/SKILL.md').read_text()
        block = skill.split('**Preamble (written once on first write):**', 1)[1].split('```markdown\n', 1)[1].split('```', 1)[0]
        self.assertEqual(cycle_local_skills.PREAMBLE.decode(), block)
        self.assertFalse(any(line.startswith('## [') for line in cycle_local_skills.NEW_LOG.decode().split('\n')))


# ───────────────────────────── per-harness dispatch (approaches 1, 5 and 6) ─────────────────────────────

NAMED = {
    'claude-code': [('.claude/skills', 'probe-claude-skill')],
    'codex': [('.agents/skills', 'probe-codex-skill')],
    'opencode': [('.opencode/skills', 'probe-opencode-skill'), ('.opencode/skill', 'probe-opencode-singular')],
    'omp': [('.omp/skills', 'probe-omp-skill')],
}
TERM_HEADER = 'name: {name}\ndescription: Probe by domain.\nmetadata:\n  domain_terms: "harness fixture | widget probing"\n'
BAD_TERMS_HEADER = 'name: {name}\ndescription: Bad terms.\nmetadata:\n  domain_terms: "ab"\n'
HARNESS_TASK = ('Exercise probe-claude-skill, probe-codex-skill, probe-opencode-skill, probe-opencode-singular, '
                'probe-omp-skill, opencode-dup-skill and bad-terms-skill for the harness fixture.')


class HarnessDispatchTests(CycleFixture):
    """A fixture cycle with a local skill in each harness directory, dispatched once on each host."""

    def extra_fixture(self):
        for host, rows in NAMED.items():
            for root, name in rows:
                write_skill(self.repo, root, name)
            first = rows[0][0]
            write_skill(self.repo, first, f'terms-{host}-skill', header=TERM_HEADER.format(name=f'terms-{host}-skill'))
        # A second copy of an OpenCode id in the singular root loses to `.opencode/skills`.
        write_skill(self.repo, '.opencode/skills', 'opencode-dup-skill')
        write_skill(self.repo, '.opencode/skill', 'opencode-dup-skill')
        write_skill(self.repo, '.agents/skills', 'bad-terms-skill', header=BAD_TERMS_HEADER.format(name='bad-terms-skill'))
        # A skill that only a scope path names.
        write_skill(self.repo, '.claude/skills', 'scope-only-skill')

    def scope(self):
        return ['src', '.claude/skills/scope-only-skill']

    def dispatch(self, host, description, task_id=None):
        task_id = task_id or f'host-{host}'
        mutate(self.repo, self.cid, 'task-add', task={'id': task_id, 'phase': 'build', 'description': description,
                                                       'depends_on': [], 'status': 'pending', 'expected_evidence': ['report']})
        return self.ok({'op': 'prepare-dispatch', 'op_id': f'prep-{task_id}', 'task_id': task_id, 'role': 'reviewer', 'host': host})

    def test_each_host_lists_its_own_roots_under_the_shared_domain_filter(self):
        expected = {
            'claude-code': [('probe-claude-skill', '.claude/skills'), ('terms-claude-code-skill', '.claude/skills')],
            'codex': [('bad-terms-skill', '.agents/skills'), ('probe-codex-skill', '.agents/skills'),
                      ('terms-codex-skill', '.agents/skills')],
            'opencode': [('opencode-dup-skill', '.opencode/skills'), ('probe-opencode-skill', '.opencode/skills'),
                         ('terms-opencode-skill', '.opencode/skills'), ('probe-opencode-singular', '.opencode/skill')],
            'omp': [('probe-omp-skill', '.omp/skills'), ('terms-omp-skill', '.omp/skills')],
        }
        own_ids = {host: {name for name, _ in rows} for host, rows in expected.items()}
        for host in HOSTS:
            with self.subTest(host=host):
                prepared = self.dispatch(host, HARNESS_TASK)
                offered = [(item['id'], item['root']) for item in prepared['local_skills']['offered']]
                self.assertEqual(offered, expected[host])
                other = set().union(*(ids for name, ids in own_ids.items() if name != host)) - own_ids[host]
                self.assertFalse(other & {item[0] for item in offered}, 'another host\'s roots list nothing here')
                bundle = json.loads((self.repo / 'bionic' / prepared['invocation_snapshot']['path']).read_text())
                self.assertEqual(bundle['local_candidates'], prepared['local_skills']['offered'])
                prompt = bundle['context_message']
                for root in dict.fromkeys(root for _, root in expected[host]):
                    ids = ', '.join(name for name, r in expected[host] if r == root)
                    self.assertIn(f'Project-local skills matching this task, in {root}: {ids}.', prompt)
                refused = prepared['local_skills']['refused']
                if host == 'opencode':
                    self.assertIn({'id': 'opencode-dup-skill', 'root': '.opencode/skill', 'reason': 'duplicate-id'}, refused)
                if host == 'codex':
                    # An invalid value records the refusal and keeps the skill listed, eligible by its explicit id.
                    self.assertIn({'id': 'bad-terms-skill', 'root': '.agents/skills', 'reason': 'invalid-domain-terms'}, refused)

    def test_a_domain_term_alone_admits_the_skill_that_declares_it(self):
        for host in HOSTS:
            with self.subTest(host=host):
                prepared = self.dispatch(host, 'Tidy the widget probing notes.', task_id=f'terms-{host}')
                self.assertEqual([item['id'] for item in prepared['local_skills']['offered']], [f'terms-{host}-skill'])

    def test_a_scope_path_alone_admits_no_local_skill(self):
        # Positive control: the same skill is offered when the description names it.
        named = self.dispatch('claude-code', 'Check scope-only-skill.', task_id='scope-named')
        self.assertIn({'id': 'scope-only-skill', 'root': '.claude/skills'}, named['local_skills']['offered'])
        self.assertIn('.claude/skills/scope-only-skill', load(self.repo, self.cid)['plan']['scope'])
        prepared = self.dispatch('claude-code', 'Tidy the notes.', task_id='scope-alone')
        self.assertEqual(prepared['local_skills']['offered'], [])
        self.assertIn(cycle_hosts.LOCAL_SKILL_REPORT, prepared['invocation']['parameters']['prompt'],
                      'the root was listed: the preamble carries the report line')


# ───────────────────────────── refusal matrix (approaches 2 to 4) ─────────────────────────────

class RefusalMatrixTests(unittest.TestCase):
    """Each refusal beside a positive control that lists the same skill without the defect."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.count = 0

    def fresh(self):
        self.count += 1
        repo = self.base / f'repo-{self.count}'
        repo.mkdir()
        return repo

    def listed(self, repo, host='claude-code', plugin=frozenset()):
        found = cycle_local_skills.listing(repo, host, plugin)
        return [item['id'] for item in found['skills']], found['refused']

    def assert_control(self, repo, name, host='claude-code', plugin=frozenset()):
        ids, refused = self.listed(repo, host, plugin)
        self.assertEqual((ids, refused), ([name], []), 'positive control: the skill lists without the defect')

    def assert_refused(self, repo, row, host='claude-code', plugin=frozenset()):
        ids, refused = self.listed(repo, host, plugin)
        self.assertEqual(ids, [])
        self.assertEqual(refused, [row])

    def test_a_symlinked_root_is_refused(self):
        repo = self.fresh()
        outside = self.base / 'outside-root'
        write_skill(outside, 'skills', 'probe-x')
        (repo / '.claude').mkdir()
        shutil.copytree(outside / 'skills', repo / '.claude/skills')
        self.assert_control(repo, 'probe-x')
        shutil.rmtree(repo / '.claude/skills')
        (repo / '.claude/skills').symlink_to(outside / 'skills', target_is_directory=True)
        self.assert_refused(repo, {'id': None, 'root': '.claude/skills', 'reason': 'symlink-root'})

    def test_a_symlinked_ancestor_is_refused(self):
        repo = self.fresh()
        outside = self.base / 'outside-ancestor'
        write_skill(outside, 'skills', 'probe-x')
        shutil.copytree(outside, repo / '.claude')
        self.assert_control(repo, 'probe-x')
        shutil.rmtree(repo / '.claude')
        (repo / '.claude').symlink_to(outside, target_is_directory=True)
        self.assert_refused(repo, {'id': None, 'root': '.claude/skills', 'reason': 'symlink-ancestor'})

    def test_a_symlinked_skill_directory_is_refused(self):
        repo = self.fresh()
        write_skill(repo, '.claude/skills', 'probe-x')
        self.assert_control(repo, 'probe-x')
        outside = self.base / 'outside-dir'
        shutil.move(str(repo / '.claude/skills/probe-x'), outside)
        (repo / '.claude/skills/probe-x').symlink_to(outside, target_is_directory=True)
        self.assert_refused(repo, {'id': 'probe-x', 'root': '.claude/skills', 'reason': 'symlink-skill-directory'})

    def test_a_symlinked_skill_file_is_refused(self):
        repo = self.fresh()
        directory = write_skill(repo, '.claude/skills', 'probe-x')
        self.assert_control(repo, 'probe-x')
        outside = self.base / 'outside-SKILL.md'
        shutil.move(str(directory / 'SKILL.md'), outside)
        (directory / 'SKILL.md').symlink_to(outside)
        self.assert_refused(repo, {'id': 'probe-x', 'root': '.claude/skills', 'reason': 'symlink-skill-file'})

    def test_a_skill_file_that_resolves_outside_the_root_is_refused(self):
        """Every symlink component is refused earlier, so the containment check is driven by a resolve that
        lands outside the root; the unpatched listing of the same skill is the positive control."""
        repo = self.fresh()
        write_skill(repo, '.claude/skills', 'probe-x')
        self.assert_control(repo, 'probe-x')
        outside = self.base / 'escaped' / 'SKILL.md'
        original = Path.resolve

        def escaping(path, strict=False):
            return outside if path.name == 'SKILL.md' else original(path, strict)
        with patch.object(Path, 'resolve', escaping):
            self.assert_refused(repo, {'id': 'probe-x', 'root': '.claude/skills', 'reason': 'escapes-root'})

    def test_an_oversized_skill_file_is_refused_at_one_byte_past_the_limit(self):
        repo = self.fresh()
        directory = write_skill(repo, '.claude/skills', 'probe-x')
        head = (directory / 'SKILL.md').read_bytes()
        (directory / 'SKILL.md').write_bytes(head + b'x' * (cycle_local_skills.MAX_FILE_BYTES - len(head)))
        self.assert_control(repo, 'probe-x')
        (directory / 'SKILL.md').write_bytes(head + b'x' * (cycle_local_skills.MAX_FILE_BYTES - len(head) + 1))
        self.assert_refused(repo, {'id': 'probe-x', 'root': '.claude/skills', 'reason': 'oversized'})

    def test_a_skill_file_that_is_not_a_regular_file_is_refused(self):
        repo = self.fresh()
        directory = write_skill(repo, '.claude/skills', 'probe-x')
        self.assert_control(repo, 'probe-x')
        (directory / 'SKILL.md').unlink()
        (directory / 'SKILL.md').mkdir()
        self.assert_refused(repo, {'id': 'probe-x', 'root': '.claude/skills', 'reason': 'not-regular-file'})

    def test_a_fifo_skill_file_is_refused_without_blocking(self):
        repo = self.fresh()
        directory = write_skill(repo, '.claude/skills', 'probe-x')
        self.assert_control(repo, 'probe-x')
        (directory / 'SKILL.md').unlink()
        os.mkfifo(directory / 'SKILL.md')
        found = {}
        worker = threading.Thread(target=lambda: found.update(result=self.listed(repo)), daemon=True)
        worker.start(); worker.join(10)
        if worker.is_alive():
            # Unblock the reader so the daemon thread ends, then fail.
            with open(os.open(directory / 'SKILL.md', os.O_WRONLY | os.O_NONBLOCK), 'wb'):
                pass
            self.fail('listing blocked on a FIFO SKILL.md')
        self.assertEqual(found['result'], ([], [{'id': 'probe-x', 'root': '.claude/skills', 'reason': 'not-regular-file'}]))

    def test_a_name_mismatch_is_refused(self):
        repo = self.fresh()
        directory = write_skill(repo, '.claude/skills', 'probe-x')
        self.assert_control(repo, 'probe-x')
        (directory / 'SKILL.md').write_text('---\nname: probe-y\ndescription: x\n---\n')
        self.assert_refused(repo, {'id': 'probe-x', 'root': '.claude/skills', 'reason': 'name-mismatch'})

    def test_an_invalid_id_is_refused(self):
        repo = self.fresh()
        write_skill(repo, '.claude/skills', 'probe-x')
        self.assert_control(repo, 'probe-x')
        shutil.rmtree(repo / '.claude/skills/probe-x')
        write_skill(repo, '.claude/skills', 'probe_x')
        self.assert_refused(repo, {'id': 'probe_x', 'root': '.claude/skills', 'reason': 'invalid-id'})

    def test_an_invalid_frontmatter_is_refused(self):
        repo = self.fresh()
        directory = write_skill(repo, '.claude/skills', 'probe-x')
        self.assert_control(repo, 'probe-x')
        (directory / 'SKILL.md').write_text('---\n- not a mapping\n---\n')
        self.assert_refused(repo, {'id': 'probe-x', 'root': '.claude/skills', 'reason': 'invalid-frontmatter'})

    def test_a_declared_tool_grant_is_refused_at_the_top_level_and_under_metadata(self):
        for key in cycle_local_skills.GRANT_KEYS:
            for header in (f'name: probe-x\ndescription: x\n{key}: Bash\n',
                           f'name: probe-x\ndescription: x\nmetadata:\n  {key}: Bash\n'):
                with self.subTest(key=key, header=header):
                    repo = self.fresh()
                    directory = write_skill(repo, '.claude/skills', 'probe-x')
                    self.assert_control(repo, 'probe-x')
                    (directory / 'SKILL.md').write_text(f'---\n{header}---\n')
                    self.assert_refused(repo, {'id': 'probe-x', 'root': '.claude/skills', 'reason': 'declares-tool-grant'})

    def test_a_plugin_id_is_refused_and_the_catalog_supplies_the_ids(self):
        repo = self.fresh()
        write_skill(repo, '.claude/skills', 'cycle')
        self.assert_control(repo, 'cycle', plugin=frozenset())
        self.assert_refused(repo, {'id': 'cycle', 'root': '.claude/skills', 'reason': 'shadows-plugin-skill'}, plugin=frozenset({'cycle'}))
        found = cycle_local_skills.listing(repo, 'claude-code')
        self.assertEqual(found['refused'], [{'id': 'cycle', 'root': '.claude/skills', 'reason': 'shadows-plugin-skill'}])

    def test_a_credential_path_is_refused(self):
        name = 'credentials'
        self.assertIn(name, cycle_context_read.FORBIDDEN_PARTS)
        repo = self.fresh()
        write_skill(repo, '.claude/skills', 'probe-x')
        self.assert_control(repo, 'probe-x')
        shutil.rmtree(repo / '.claude/skills/probe-x')
        write_skill(repo, '.claude/skills', name)
        self.assert_refused(repo, {'id': name, 'root': '.claude/skills', 'reason': 'credential-path'})

    def test_a_root_past_the_directory_cap_records_one_over_cap_row(self):
        repo = self.fresh()
        for index in range(cycle_local_skills.MAX_DIRECTORIES):
            write_skill(repo, '.claude/skills', f'probe-{index:03d}')
        ids, refused = self.listed(repo)
        self.assertEqual((len(ids), refused), (cycle_local_skills.MAX_DIRECTORIES, []), 'positive control: 64 list')
        write_skill(repo, '.claude/skills', 'probe-999')
        ids, refused = self.listed(repo)
        self.assertEqual(len(ids), cycle_local_skills.MAX_DIRECTORIES)
        self.assertNotIn('probe-999', ids)
        self.assertEqual(refused, [{'id': None, 'root': '.claude/skills', 'reason': 'over-cap', 'skipped': 1}])

    def test_the_ninth_eligible_skill_is_refused_as_over_cap(self):
        repo = self.fresh()
        names = [f'probe-{index}' for index in range(cycle_local_skills.MAX_CANDIDATES + 1)]
        for name in names:
            write_skill(repo, '.claude/skills', name)
        found = cycle_local_skills.candidates(repo, 'claude-code', ' '.join(names[:-1]), frozenset())
        self.assertEqual(len(found['offered']), cycle_local_skills.MAX_CANDIDATES, 'positive control: eight are offered')
        found = cycle_local_skills.candidates(repo, 'claude-code', ' '.join(names), frozenset())
        self.assertEqual([item['id'] for item in found['offered']], sorted(names)[:cycle_local_skills.MAX_CANDIDATES])
        self.assertEqual(found['refused'], [{'id': sorted(names)[-1], 'root': '.claude/skills', 'reason': 'over-cap'}])

    def test_a_refusal_reaches_the_prepare_dispatch_response(self):
        """The entry point: a symlinked SKILL.md is refused in prepare-dispatch, and the regular copy is offered."""
        fixture = RefusalDispatch('drive')
        fixture.setUp()
        try:
            fixture.drive()
        finally:
            fixture.doCleanups()


class RefusalDispatch(CycleFixture):
    """Driven from RefusalMatrixTests through prepare-dispatch; its method name keeps the loader from collecting it."""

    def extra_fixture(self):
        directory = write_skill(self.repo, '.claude/skills', 'linked-skill')
        target = self.repo / 'elsewhere.md'
        (directory / 'SKILL.md').rename(target)
        (directory / 'SKILL.md').symlink_to(target)

    def drive(self):
        mutate(self.repo, self.cid, 'task-add', task={'id': 'refuse-it', 'phase': 'build', 'description': f'use linked-skill and {SKILL}',
                                                       'depends_on': [], 'status': 'pending', 'expected_evidence': ['report']})
        prepared = self.ok({'op': 'prepare-dispatch', 'op_id': 'prep-refuse', 'task_id': 'refuse-it', 'role': 'reviewer', 'host': 'claude-code'})
        self.assertEqual(prepared['local_skills']['offered'], [{'id': SKILL, 'root': '.claude/skills'}])
        self.assertIn({'id': 'linked-skill', 'root': '.claude/skills', 'reason': 'symlink-skill-file'}, prepared['local_skills']['refused'])
        bundle = json.loads((self.repo / 'bionic' / prepared['invocation_snapshot']['path']).read_text())
        self.assertIn(f'in .claude/skills: {SKILL}.', bundle['context_message'])
        self.assertNotIn('linked-skill', bundle['context_message'])


# ───────────────────────────── precedence and no grant (approaches 3, 4 and 6) ─────────────────────────────

PRECEDENCE_TASK = f'Use council and check-drift; also {SKILL}, cycle and the drift probing.'


class PrecedenceAndGrantTests(CycleFixture):
    """Plugin candidates, job subjects and every invocation parameter except the prompt text are identical
    with and without local skills present."""

    def extra_fixture(self):
        # A local copy of a plugin id and a skill admitted by a term both stay out of the plugin list.
        write_skill(self.repo, '.claude/skills', 'council')
        write_skill(self.repo, '.claude/skills', 'drift-term-skill',
                    header='name: drift-term-skill\ndescription: x\nmetadata:\n  domain_terms: "drift probing"\n')
        for host, rows in NAMED.items():
            for root, name in rows:
                write_skill(self.repo, root, name)

    def hide_local_roots(self):
        """Move every local root aside; return a callable that puts them back."""
        moved = []
        for root in cycle_local_skills.ALL_ROOTS:
            path = self.repo / root
            if path.exists():
                aside = self.repo.parent / (self.repo.name + '-aside-' + root.replace('/', '_'))
                shutil.move(str(path), aside)
                moved.append((aside, path))

        def restore():
            for aside, path in moved:
                shutil.move(str(aside), path)
        return restore

    def jobs_and_candidates(self, task_id, role):
        doc = load(self.repo, self.cid)
        task = next(t for t in doc['plan']['tasks'] if t['id'] == task_id)
        candidates = cycle_context.candidates(doc, task, role)
        with patch.object(cycle_classify, 'classify', return_value={'classifications': []}) as classify:
            cycle_classify._context_bundles(self.repo, self.cid, task_id, role)
        jobs = [(job.kind, job.subject, job.trigger) for job in classify.call_args.args[2]]
        return candidates, jobs

    def test_plugin_candidates_and_job_subjects_are_identical_with_and_without_local_skills(self):
        mutate(self.repo, self.cid, 'task-add', task={'id': 'prec-it', 'phase': 'build', 'description': PRECEDENCE_TASK,
                                                       'depends_on': [], 'status': 'pending', 'expected_evidence': ['report']})
        local = cycle_local_skills.candidates(self.repo, 'claude-code', PRECEDENCE_TASK)
        # Positive control: local skills are present and eligible for this task.
        self.assertEqual([item['id'] for item in local['offered']], ['drift-term-skill', SKILL])
        self.assertIn({'id': 'council', 'root': '.claude/skills', 'reason': 'shadows-plugin-skill'}, local['refused'])
        with_local = self.jobs_and_candidates('prec-it', 'reviewer')
        restore = self.hide_local_roots()
        try:
            self.assertEqual(cycle_local_skills.candidates(self.repo, 'claude-code', PRECEDENCE_TASK)['offered'], [])
            without_local = self.jobs_and_candidates('prec-it', 'reviewer')
        finally:
            restore()
        self.assertEqual(with_local, without_local)
        ids = [item['id'] for item in with_local[0]]
        self.assertIn('council', ids)
        self.assertNotIn(SKILL, ids)
        self.assertEqual([subject for _, subject, _ in with_local[1]], [f'prec-it:skill-{i}' for i in range(len(ids))])

    def test_skill_bundle_refuses_a_local_id(self):
        self.assertEqual(cycle_context.skill_bundle('cycle')['id'], 'cycle', 'positive control: a plugin body loads')
        self.assertTrue((self.repo / '.claude/skills' / SKILL / 'SKILL.md').is_file())
        with self.assertRaisesRegex(ValueError, 'canonical skill body is unavailable'):
            cycle_context.skill_bundle(SKILL)

    def test_no_invocation_parameter_but_the_prompt_text_changes_on_any_host(self):
        for host in HOSTS:
            with self.subTest(host=host):
                task_id = f'grant-{host}'
                description = PRECEDENCE_TASK + ' ' + ' '.join(name for _, name in NAMED[host])
                mutate(self.repo, self.cid, 'task-add', task={'id': task_id, 'phase': 'build', 'description': description,
                                                               'depends_on': [], 'status': 'pending', 'expected_evidence': ['report']})
                prepared = self.ok({'op': 'prepare-dispatch', 'op_id': f'prep-{task_id}', 'task_id': task_id, 'role': 'reviewer', 'host': host})
                cfg, doc = tree(self.repo), load(self.repo, self.cid)
                entry = next(e for e in doc['assignments'] if e['task'] == task_id)
                request = {'op': 'prepare-dispatch', 'task_id': task_id, 'role': 'reviewer', 'host': host}
                with_local, _ = cycle_ops.build_invocation(cfg, doc, request, entry)
                restore = self.hide_local_roots()
                try:
                    without_local, _ = cycle_ops.build_invocation(cfg, doc, request, entry)
                finally:
                    restore()
                # Positive control: local skills changed the prompt text of this invocation.
                prompt_key = 'message' if host == 'codex' else 'prompt'
                self.assertTrue(with_local['local_candidates'])
                self.assertEqual(with_local['invocation']['parameters'][prompt_key], prepared['invocation']['parameters'][prompt_key])
                self.assertNotEqual(with_local['invocation']['parameters'][prompt_key], without_local['invocation']['parameters'][prompt_key])
                if host == 'codex':
                    # Codex's task_name ends in a digest of role, description and message: a function of the prompt text.
                    for built in (with_local, without_local):
                        parameters = built['invocation']['parameters']
                        digest = hashlib.sha256(('reviewer\n' + f'{task_id} attempt 1' + '\n' + parameters['message']).encode()).hexdigest()[:12]
                        self.assertTrue(parameters['task_name'].endswith('_' + digest), parameters['task_name'])
                derived = {prompt_key, 'task_name'} if host == 'codex' else {prompt_key}
                strip = lambda invocation: {**invocation, 'parameters': {k: v for k, v in invocation['parameters'].items() if k not in derived}}
                self.assertEqual(strip(with_local['invocation']), strip(without_local['invocation']))
                self.assertEqual(with_local['native_context'], without_local['native_context'])
                self.assertEqual(with_local['sources'], without_local['sources'])
                self.assertEqual((with_local['selected'], with_local['retrievable']), (without_local['selected'], without_local['retrievable']))


# ───────────────────────────── use events (approaches 7 and 9) ─────────────────────────────

class UseEventTests(CycleFixture):
    def committed_log(self):
        return self.git('show', f'HEAD:{LOG}')

    def test_positive_control_an_ok_line_commits_one_entry(self):
        self.run_cycle('Verdict: approve.', f'Local-Skill-Used: {SKILL} ok')
        done = self.finish()
        self.assertTrue((self.repo / LOG).is_file())
        self.assertEqual(done['record_commit']['forge_log']['committed'], [LOG])
        self.assertEqual(len(self.log_entries(self.committed_log())), 1)

    def test_a_prose_mention_records_no_use(self):
        self.run_cycle('Verdict: approve.', f'I used {SKILL} to probe the answer; Local-Skill-Used: {SKILL} ok inline.')
        done = self.finish()
        self.assertEqual(done['record_commit']['forge_log']['appended'], [])
        self.assertEqual(done['record_commit']['forge_log']['ignored'], [])
        self.assertFalse((self.repo / LOG).exists())

    def test_a_crlf_report_line_counts(self):
        self.run_cycle('Verdict: approve.', f'Local-Skill-Used: {SKILL} ok', eol='\r\n')
        done = self.finish()
        self.assertEqual(done['record_commit']['forge_log']['committed'], [LOG])
        self.assertEqual(len(self.log_entries(self.committed_log())), 1)

    def test_a_plugin_id_line_is_ignored_beside_a_local_one(self):
        review = self.run_cycle('Verdict: approve.', 'Local-Skill-Used: cycle ok', f'Local-Skill-Used: {SKILL} ok')
        done = self.finish()
        report = load(self.repo, self.cid)['assignments'][1]['delivery']['path']
        self.assertIn({'report': report, 'id': 'cycle', 'reason': 'plugin-skill'}, done['record_commit']['forge_log']['ignored'])
        log = self.committed_log()
        self.assertEqual(len(self.log_entries(log)), 1)
        self.assertEqual(self.log_entries(log, 'cycle'), [])
        self.assertIn(f'{review["assignment"]}/1 reviewer report; ok', log)

    def test_an_unknown_id_line_is_ignored_beside_a_known_one(self):
        self.run_cycle('Verdict: approve.', 'Local-Skill-Used: no-such-skill ok', f'Local-Skill-Used: {SKILL} ok')
        done = self.finish()
        reasons = [(row['id'], row['reason']) for row in done['record_commit']['forge_log']['ignored']]
        self.assertEqual(reasons, [('no-such-skill', 'unknown-local-skill')])
        log = self.committed_log()
        self.assertEqual(self.log_entries(log, 'no-such-skill'), [])
        self.assertEqual(len(self.log_entries(log)), 1)

    def test_conflicting_outcomes_record_one_partial_entry(self):
        review = self.run_cycle('Verdict: approve.', f'Local-Skill-Used: {SKILL} partial', f'Local-Skill-Used: {SKILL} ok')
        self.finish()
        log = self.committed_log()
        self.assertEqual(len(self.log_entries(log)), 1)
        self.assertIn(f'{review["assignment"]}/1 reviewer report; partial', log)
        self.assertNotIn('report; ok', log)

    def test_conflicting_outcomes_are_partial_in_either_order_and_agreeing_ones_keep_their_value(self):
        from types import SimpleNamespace
        cases = {('ok', 'partial'): 'partial', ('partial', 'ok'): 'partial', ('ok', 'ok'): 'ok', ('partial', 'partial'): 'partial'}
        for index, (outcomes, expected) in enumerate(cases.items()):
            with self.subTest(outcomes=outcomes):
                docs = self.repo / f'scan-{index}'
                results = docs / 'cycles/CYC-0009/results'
                results.mkdir(parents=True)
                lines = [f'Local-Skill-Used: {SKILL} {outcome}' for outcome in outcomes]
                (results / 'r.md').write_text('\n'.join(['Assignment: a', 'Attempt: 1', *lines]) + '\n')
                uses, ignored = cycle_local_skills.scan(SimpleNamespace(docs_root=docs), frozenset())
                self.assertEqual([use['outcome'] for use in uses.values()], [expected])
                self.assertEqual(ignored, [])

    def test_a_report_changed_after_delivery_records_no_use(self):
        self.run_cycle()
        report = self.repo / 'bionic' / load(self.repo, self.cid)['assignments'][1]['delivery']['path']
        report.write_bytes(report.read_bytes() + b'edited after delivery\n')
        done = self.finish()
        reasons = [(row['id'], row['reason']) for row in done['record_commit']['forge_log']['ignored']]
        self.assertEqual(reasons, [(SKILL, 'report-changed')])
        self.assertEqual(done['record_commit']['forge_log']['appended'], [])
        self.assertFalse((self.repo / LOG).exists())

    def test_the_seventeenth_line_is_ignored_as_over_cap(self):
        lines = [f'Local-Skill-Used: probe-{index} ok' for index in range(cycle_local_skills.MAX_REPORT_LINES + 1)]
        header, found, past = cycle_local_skills.report_uses(('Assignment: a\nAttempt: 1\n' + '\n'.join(lines) + '\n').encode())
        self.assertEqual(header, ('a', 1))
        self.assertEqual(len(found), cycle_local_skills.MAX_REPORT_LINES)
        self.assertEqual(past, 1)
        self.assertNotIn(('probe-16', 'ok'), found)
        header, found, past = cycle_local_skills.report_uses(('Assignment: a\nAttempt: 1\n' + '\n'.join(lines[:-1]) + '\n').encode())
        self.assertEqual((len(found), past), (cycle_local_skills.MAX_REPORT_LINES, 0), 'positive control: sixteen all count')


# ───────────────────────────── flush guards and completing paths (approaches 8 and 9) ─────────────────────────────

class FlushGuardTests(CycleFixture):
    def test_positive_control_a_regular_log_receives_the_entry(self):
        self.run_cycle()
        (self.repo / LOG).write_bytes(cycle_local_skills.NEW_LOG)
        done = self.finish()
        self.assertEqual(done['record_commit']['forge_log']['committed'], [LOG])
        self.assertTrue((self.repo / LOG).is_file())
        self.assertEqual(len(self.log_entries((self.repo / LOG).read_text())), 1)

    def test_a_symlinked_forge_log_is_refused_and_its_target_is_unchanged(self):
        self.run_cycle()
        target = self.repo.parent / (self.repo.name + '-target.md')
        target.write_bytes(cycle_local_skills.NEW_LOG)
        self.addCleanup(target.unlink)
        (self.repo / LOG).symlink_to(target)
        done = self.finish()
        self.assertEqual(done['record_commit']['forge_log']['committed'], [])
        self.assertIn({'path': LOG, 'reason': 'forge-log-not-regular'}, done['record_commit']['forge_log']['uncommitted'])
        self.assertEqual(target.read_bytes(), cycle_local_skills.NEW_LOG, 'no byte is written through the link')
        self.assertTrue((self.repo / LOG).is_symlink())
        rows = self.ok({'op': 'inspect'})['record']['forge_logs']
        self.assertIn({'path': LOG, 'state': 'foreign', 'cycles': [], 'reason': 'forge-log-not-regular', 'resolver': 'main session'}, rows)

    def test_a_non_regular_forge_log_is_refused(self):
        self.run_cycle()
        (self.repo / LOG).mkdir()
        done = self.finish()
        self.assertEqual(done['record_commit']['forge_log']['committed'], [])
        self.assertIn({'path': LOG, 'reason': 'forge-log-not-regular'}, done['record_commit']['forge_log']['uncommitted'])
        self.assertTrue((self.repo / LOG).is_dir())

    def test_a_root_swapped_to_a_symlink_after_the_check_receives_no_write(self):
        """The write opens each directory from the repository root without following links, so a root
        swapped to a symlink between the guarded read and the write is refused, not written through."""
        self.run_cycle()
        outside = self.repo.parent / (self.repo.name + '-swapped')
        self.addCleanup(shutil.rmtree, outside, True)
        real_insert = cycle_local_skills.insert

        def swapping(base, block):
            shutil.move(str(self.repo / '.claude/skills'), outside)
            (self.repo / '.claude/skills').symlink_to(outside, target_is_directory=True)
            return real_insert(base, block)
        with patch.object(cycle_local_skills, 'insert', swapping):
            done = self.finish()
        flush = done['record_commit']['forge_log']
        self.assertEqual(flush['committed'], [])
        self.assertEqual(flush['appended'], [])
        self.assertEqual([row['root'] for row in flush['error']], ['.claude/skills'])
        self.assertFalse((outside / 'forge-log.md').exists(), 'no byte lands outside the repository')
        self.assertEqual([p.name for p in outside.iterdir()], [SKILL], 'no temporary is left outside either')

    def test_a_log_swapped_to_a_symlink_after_the_check_is_left_alone(self):
        self.run_cycle()
        target = self.repo.parent / (self.repo.name + '-link-target.md')
        target.write_bytes(b'foreign\n')
        self.addCleanup(target.unlink)
        real_insert = cycle_local_skills.insert

        def swapping(base, block):
            (self.repo / LOG).symlink_to(target)
            return real_insert(base, block)
        with patch.object(cycle_local_skills, 'insert', swapping):
            done = self.finish()
        flush = done['record_commit']['forge_log']
        self.assertEqual((flush['committed'], flush['appended']), ([], []))
        self.assertEqual([row['root'] for row in flush['error']], ['.claude/skills'])
        self.assertIn('not a regular file', flush['error'][0]['problem'])
        self.assertTrue((self.repo / LOG).is_symlink(), 'the link is neither followed nor replaced')
        self.assertEqual(target.read_bytes(), b'foreign\n')

    def test_a_fifo_forge_log_is_refused_without_blocking(self):
        self.run_cycle()
        os.mkfifo(self.repo / LOG)
        done = self.finish()
        self.assertEqual(done['record_commit']['forge_log']['committed'], [])
        self.assertIn({'path': LOG, 'reason': 'forge-log-not-regular'}, done['record_commit']['forge_log']['uncommitted'])
        rows = self.ok({'op': 'inspect'})['record']['forge_logs']
        self.assertIn('foreign', [row['state'] for row in rows])

    def test_a_failed_restore_leaves_rederivable_bytes_that_commit_record_recovers(self):
        """anthropic_top:F2 and openai_top:F1: the commit step does not land, the restore fails, the engine
        bytes stay dirty, inspect reports them committable, and commit-record commits them."""
        self.run_cycle()
        (self.repo / LOG).write_bytes(cycle_local_skills.NEW_LOG)
        self.git('add', LOG); self.git('commit', '-q', '-m', 'empty log')
        real_commit, real_write = cycle_commit.commit_paths, cycle_local_skills._write
        calls = {'commit': 0, 'write': 0}

        def failing_commit(cfg, paths, message):
            calls['commit'] += 1
            if calls['commit'] == 1:
                return {'changed': False, 'commit': None, 'paths': paths, 'message': None, 'deferred': 'commit-failed',
                        'detail': 'simulated', 'pending': paths}
            return real_commit(cfg, paths, message)

        def failing_restore(repo_root, relative, data):
            calls['write'] += 1
            if calls['write'] == 2:
                raise PermissionError('simulated restore failure')
            return real_write(repo_root, relative, data)
        with patch.object(cycle_commit, 'commit_paths', failing_commit), patch.object(cycle_local_skills, '_write', failing_restore):
            done = self.finish()
        flush = done['record_commit']['forge_log']
        self.assertEqual(calls, {'commit': 1, 'write': 2})
        self.assertEqual(flush['committed'], [])
        self.assertEqual([row['root'] for row in flush['error']], [LOG])
        self.assertIn('restore-failed', flush['error'][0]['problem'])
        written = (self.repo / LOG).read_bytes()
        self.assertEqual(len(self.log_entries(written.decode())), 1, 'the engine bytes stay in the working tree')
        rows = self.ok({'op': 'inspect'})['record']['forge_logs']
        self.assertIn({'path': LOG, 'state': 'committable', 'cycles': [self.cid]}, rows)
        recovered = self.ok({'op': 'commit-record'})
        self.assertEqual(recovered['forge_log']['committed'], [LOG])
        self.assertEqual(self.blob(LOG), written)
        self.assertEqual(self.git('status', '--porcelain', '--', LOG), '')

    def test_a_restore_that_succeeds_returns_the_prior_bytes(self):
        """Positive control for the failed restore: the same unlanded commit restores the committed log."""
        self.run_cycle()
        (self.repo / LOG).write_bytes(cycle_local_skills.NEW_LOG)
        self.git('add', LOG); self.git('commit', '-q', '-m', 'empty log')
        real_commit = cycle_commit.commit_paths
        calls = {'commit': 0}

        def failing_commit(cfg, paths, message):
            calls['commit'] += 1
            if calls['commit'] == 1:
                return {'changed': False, 'commit': None, 'paths': paths, 'message': None, 'deferred': 'commit-failed',
                        'detail': 'simulated', 'pending': paths}
            return real_commit(cfg, paths, message)
        with patch.object(cycle_commit, 'commit_paths', failing_commit):
            done = self.finish()
        self.assertIsNone(done['record_commit']['forge_log']['error'])
        self.assertIn({'path': LOG, 'reason': 'commit-failed'}, done['record_commit']['forge_log']['uncommitted'])
        self.assertEqual((self.repo / LOG).read_bytes(), cycle_local_skills.NEW_LOG)

    def test_a_friction_commit_on_a_completed_cycle_flushes(self):
        """A quick-fix Reflect closes through finish, so ReleaseFinishFlushTests drives the completing low-level
        advance; the friction commit on a completed cycle flushes too."""
        self.run_cycle()
        self.finish()
        self.drop_log()
        result = self.cli('friction', self.cid, '--json', json.dumps({'who': 'w', 'what': 'w', 'cost': 'c', 'category': 'c', 'fix': 'f'}))
        self.assertEqual(result['record_commit']['forge_log']['committed'], [LOG])
        self.assertIn(LOG, self.git('show', '--name-only', '--format=', 'HEAD').splitlines())

    def test_owner_decision_on_a_completed_cycle_flushes(self):
        """anthropic_top:F5: the owner-decision commit path. The action is stubbed; the commit after it is real."""
        self.run_cycle()
        self.finish()
        self.drop_log()
        import owner_decision
        with patch.object(owner_decision, 'present', return_value={'presentation': 'stub'}):
            result = self.cli('owner-decision', 'present', '--json', json.dumps({'cycle_id': self.cid}))
        self.assertEqual(result['record_commit']['forge_log']['committed'], [LOG])
        self.assertIn(LOG, self.git('show', '--name-only', '--format=', 'HEAD').splitlines())


class ReleaseFinishFlushTests(CycleFixture):
    """anthropic_top:F5: the release finish and a completing low-level advance both reach the flush."""

    def release(self):
        doc = create(self.repo, 'release', 'Beta', 'Ship beta', ['src', 'bionic/log.md'], ['beta'], 'releaser', 'tester',
                     release_list='beta')
        self.cycles.append(doc['id'])
        for task in doc['plan']['tasks'][:-1]:
            doc = mutate(self.repo, doc['id'], 'task', task_id=task['id'], state='done')
        return doc['id']

    def deliver_record(self, cid):
        prepared = self.ok({'op': 'prepare-dispatch', 'op_id': 'prep-rec01', 'task_id': 'record', 'role': 'developer',
                            'host': 'claude-code', 'assignment_text': 'Record the release.'}, cid=cid)
        (self.repo / 'bionic/log.md').write_text('released\n')
        self.git('add', 'bionic/log.md'); self.git('commit', '-q', '-m', 'record the release\n\nCycle-Task: record')
        sha = self.git('rev-parse', 'HEAD')
        self.result(prepared, 'Recorded.', f'Local-Skill-Used: {SKILL} ok')
        return prepared, {'op': 'deliver', 'op_id': 'deliver-rec1', 'assignment': prepared['assignment'], 'attempt': 1,
                          'outcome': 'done', 'commits': [sha]}

    def test_the_release_finish_flushes(self):
        cid = self.release()
        prepared, request = self.deliver_record(cid)
        response = self.ok(request, cid=cid)
        self.assertTrue(response['finish']['ok'], response['finish'])
        flush = response['finish']['record_commit']['forge_log']
        self.assertEqual(flush['committed'], [LOG])
        self.assertEqual([(a['cycle'], a['assignment']) for a in flush['appended']], [(cid, prepared['assignment'])])
        self.assertIn(f'{cid} {prepared["assignment"]}/1 developer report; ok', self.git('show', f'HEAD:{LOG}'))

    def test_a_completing_low_level_advance_flushes(self):
        cid = self.release()
        prepared, request = self.deliver_record(cid)
        with patch.object(cycle_ops, 'release_finish', lambda *a, **k: {}):
            self.ok(request, cid=cid)
        self.assertEqual(load(self.repo, cid)['status'], 'active')
        self.assertFalse((self.repo / LOG).exists(), 'an active cycle commit writes no forge log')
        mutate(self.repo, cid, 'completion', commits=[request['commits'][0]], remaining='none')
        result = self.cli('advance', cid)
        self.assertEqual(result['cycle']['status'], 'completed')
        self.assertEqual(result['record_commit']['forge_log']['committed'], [LOG])
        self.assertIn(f'{cid} {prepared["assignment"]}/1 developer report; ok', self.git('show', f'HEAD:{LOG}'))


# ───────────────────────────── the open-attempt gate across cycles (approach 8, review B1) ─────────────────────────────

class TwoCycleGateTests(CycleFixture):
    """IDR intended evidence 7: an open attempt in active cycle Y defers the flush of completed cycle X.

    The over-1-MiB variants pin review B1: the gate and the rederivation read a cycle record with no size cap,
    as the engine's own loader does, so a large record neither hides an open attempt nor drops a use."""

    def pad(self, cid):
        """Grow a record past the 1 MiB context-reader cap with trailing JSON whitespace; its content is unchanged."""
        path = self.repo / 'bionic/cycles' / cid / 'cycle.json'
        path.write_bytes(path.read_bytes() + b' ' * (cycle_local_skills.MAX_FILE_BYTES + 1))
        self.assertGreater(path.stat().st_size, cycle_local_skills.MAX_FILE_BYTES)
        self.assertEqual(load(self.repo, cid)['id'], cid, 'the engine loader reads the padded record')

    def hold(self, cid):
        """Reserve Y's build attempt with the exact request run_cycle sends, so a later run_cycle replays it."""
        return self.ok({'op': 'prepare-dispatch', 'op_id': 'prep-build', 'task_id': 'build-it', 'role': 'developer',
                        'host': 'claude-code'}, cid=cid)

    def release(self, cid, held):
        self.result(held, 'Outcome: BLOCKED.')
        self.ok({'op': 'deliver', 'op_id': 'deliver-held', 'assignment': held['assignment'], 'attempt': 1,
                 'outcome': 'blocked', 'note': 'closed for the gate test'}, cid=cid)

    def assert_deferred(self, done, other):
        flush = done['record_commit']['forge_log']
        self.assertEqual(flush['deferred'], 'open-attempts', flush)
        self.assertIn(other, flush['open_attempts'])
        self.assertEqual((flush['appended'], flush['committed']), ([], []))
        self.assertFalse((self.repo / LOG).exists(), 'the deferred flush writes no forge-log byte')
        self.assertNotIn(LOG, self.git('show', '--name-only', '--format=', 'HEAD').splitlines())
        self.assertTrue(done['record_commit']['changed'], 'the record commit itself lands')

    def two_cycle(self, pad):
        review = self.run_cycle()
        other = self.second_cycle()
        held = self.hold(other)
        if pad:
            self.pad(other)
        self.assert_deferred(self.finish(), other)
        seen = self.ok({'op': 'inspect'})
        self.assertIn({'path': LOG, 'state': 'missing', 'cycles': [self.cid]}, seen['record']['forge_logs'])
        self.assertIn(other, seen['record']['forge_log_open_attempts'])
        self.release(other, held)
        if pad:
            self.pad(other)
        result = self.ok({'op': 'commit-record'})
        self.assertIsNone(result['forge_log']['deferred'], result['forge_log'])
        self.assertEqual(result['forge_log']['committed'], [LOG])
        log = self.git('show', f'HEAD:{LOG}')
        self.assertEqual(len(self.log_entries(log)), 1)
        self.assertIn(f'{self.cid} {review["assignment"]}/1 reviewer report; ok', log)

    def test_an_open_attempt_in_another_cycle_defers_the_flush_until_it_closes(self):
        self.two_cycle(pad=False)

    def test_the_other_attempt_retained_proof_stays_identical_across_a_deferred_finish(self):
        """CYC-0120 review N3: X's deferred finish leaves Y's retained execution proof byte-identical."""
        self.run_cycle()
        other = self.second_cycle()
        held = self.hold(other)
        proved = self.ok({'op': 'execution-check', 'op_id': 'other-proof-before', 'assignment': held['assignment'],
                          'attempt': 1, 'checkout': str(self.repo)}, cid=other)
        proof = self.repo / 'bionic' / proved['execution']['proof']['path']

        def retained():
            entry = next(a for a in load(self.repo, other)['assignments'] if a['id'] == held['assignment'])
            return entry['execution'], proof.read_bytes()

        before = retained()
        self.assertEqual(before[0]['proof'], proved['execution']['proof'], 'positive control: Y retained the proof')
        self.assertEqual(hashlib.sha256(before[1]).hexdigest(), before[0]['proof']['sha256'])
        self.assert_deferred(self.finish(), other)
        self.assertEqual(retained(), before)
        self.assertEqual(self.blob(f'bionic/{before[0]["proof"]["path"]}'), before[1])

    def test_an_open_attempt_in_a_record_over_one_mib_defers_the_flush(self):
        self.two_cycle(pad=True)

    def test_an_unreadable_active_record_defers_the_flush_by_cycle_id(self):
        self.run_cycle()
        other = self.second_cycle()
        path = self.repo / 'bionic/cycles' / other / 'cycle.json'
        valid = path.read_bytes()
        self.addCleanup(path.write_bytes, valid)
        path.write_bytes(b'{"status": "active", "assignments": [')
        done = self.finish()
        self.assert_deferred(done, other)
        self.assertEqual(done['record_commit']['forge_log']['unreadable_records'], [other])
        seen = self.ok({'op': 'inspect'})['record']
        self.assertEqual((seen['forge_log_open_attempts'], seen['forge_log_unreadable_records']), ([other], [other]))
        # Positive control: the same record, readable and holding no open attempt, defers nothing.
        path.write_bytes(valid)
        result = self.ok({'op': 'commit-record'})
        self.assertEqual(result['forge_log']['committed'], [LOG])
        self.assertNotIn('unreadable_records', result['forge_log'])

    def test_a_record_of_the_wrong_shape_defers_the_flush(self):
        self.run_cycle()
        other = self.second_cycle()
        path = self.repo / 'bionic/cycles' / other / 'cycle.json'
        self.addCleanup(path.write_bytes, path.read_bytes())
        for shape in (b'[]', b'{"status": "active", "assignments": {}}', b'{"status": 7, "assignments": []}'):
            with self.subTest(shape=shape):
                path.write_bytes(shape)
                self.assertEqual(cycle_local_skills.blocking_cycles(tree(self.repo)), ([other], [other]))
        # Positive control: a readable closed record holding a running assignment defers nothing.
        path.write_bytes(b'{"status": "abandoned", "assignments": [{"state": "running"}]}')
        self.assertEqual(cycle_local_skills.blocking_cycles(tree(self.repo)), ([], []))

    def test_a_deeply_nested_record_defers_the_flush(self):
        """JSON nested past the parser's recursion limit is an invalid record, not a crash."""
        self.run_cycle()
        other = self.second_cycle()
        path = self.repo / 'bionic/cycles' / other / 'cycle.json'
        self.addCleanup(path.write_bytes, path.read_bytes())
        path.write_bytes(b'[' * 200000 + b']' * 200000)
        self.assertEqual(cycle_local_skills._load_record(tree(self.repo), other), (None, 'invalid'))
        self.assertEqual(cycle_local_skills.blocking_cycles(tree(self.repo)), ([other], [other]))

    def test_a_cycle_directory_without_a_record_defers_nothing(self):
        """Historical cycle directories can hold no cycle.json; a missing record is not an unreadable one."""
        self.run_cycle()
        (self.repo / 'bionic/cycles/CYC-0999').mkdir()
        done = self.finish()
        self.assertEqual(done['record_commit']['forge_log']['committed'], [LOG])

    def test_a_completed_record_over_one_mib_still_records_its_use(self):
        self.run_cycle()
        self.finish()
        expected = (self.repo / LOG).read_bytes()
        self.drop_log()
        self.pad(self.cid)
        result = self.ok({'op': 'commit-record'})
        self.assertEqual(result['forge_log']['ignored'], [], result['forge_log'])
        self.assertEqual(result['forge_log']['committed'], [LOG])
        self.assertEqual((self.repo / LOG).read_bytes(), expected)

    def test_a_report_over_the_cap_is_reported_as_an_ignored_row(self):
        from types import SimpleNamespace
        docs = self.repo / 'scan-cap'
        results = docs / 'cycles/CYC-0009/results'
        results.mkdir(parents=True)
        body = f'Assignment: a\nAttempt: 1\nLocal-Skill-Used: {SKILL} ok\n'
        (results / 'small.md').write_text(body)
        (results / 'large.md').write_text(body + 'x' * cycle_local_skills.MAX_FILE_BYTES + '\n')
        uses, ignored = cycle_local_skills.scan(SimpleNamespace(docs_root=docs), frozenset())
        self.assertEqual([use['report'] for use in uses.values()], ['cycles/CYC-0009/results/small.md'],
                         'positive control: the small report records its use')
        self.assertEqual(ignored, [{'report': 'cycles/CYC-0009/results/large.md', 'id': None, 'reason': 'report-oversized'}])

    def test_a_deferred_finish_then_a_second_completed_cycle_commits_both_entries(self):
        """IDR intended evidence 6: Y's finish, after X's deferred finish, commits X's and Y's entries in one commit."""
        first = self.run_cycle()
        other = self.second_cycle()
        held = self.hold(other)
        self.assert_deferred(self.finish(), other)
        second = self.run_cycle(cid=other, answer=3, build=held)
        done = self.finish(cid=other)
        flush = done['record_commit']['forge_log']
        self.assertEqual(flush['committed'], [LOG])
        self.assertEqual(sorted((a['cycle'], a['assignment']) for a in flush['appended']),
                         sorted([(self.cid, first['assignment']), (other, second['assignment'])]))
        changed = self.git('show', '--name-only', '--format=', done['record_commit']['commit']).splitlines()
        self.assertIn(LOG, changed)
        self.assertTrue(any(path.startswith(f'bionic/cycles/{other}/') for path in changed))
        log = self.git('show', f'HEAD:{LOG}')
        self.assertEqual(len(self.log_entries(log)), 2)

    def test_a_completed_cycle_holding_its_own_open_assignment_defers_no_flush(self):
        """IDR intended evidence 7: owner-complete with an open assignment in its own cycle flushes."""
        self.run_cycle()
        mutate(self.repo, self.cid, 'task-add', task={'id': 'left-open', 'phase': 'reflect', 'description': 'an attempt left open',
                                                       'depends_on': [], 'status': 'pending', 'expected_evidence': ['report']})
        self.ok({'op': 'prepare-dispatch', 'op_id': 'prep-open', 'task_id': 'left-open', 'role': 'developer', 'host': 'claude-code'})
        self.assertIn(self.cid, cycle_local_skills.open_attempt_cycles(tree(self.repo)),
                      'positive control: while active, the cycle\'s own open attempt defers the flush')
        owner = {'origin': 'owner-conversation', 'quote': 'close it', 'date': '2026-11-07', 'conversation': 'c'}
        result = self.cli('owner-complete', self.cid, '--json', json.dumps(owner))
        self.assertEqual(load(self.repo, self.cid)['status'], 'completed')
        self.assertTrue(any(a['state'] in cycle_local_skills.OPEN for a in load(self.repo, self.cid)['assignments']))
        flush = result['record_commit']['forge_log']
        self.assertIsNone(flush['deferred'], flush)
        self.assertEqual(flush['committed'], [LOG])


# ───────────────────────────── commit rule and flush edges (approaches 8 and 9, review A1 and A4) ─────────────────────────────

class CommitRuleEdgeTests(CycleFixture):
    def finished(self):
        self.run_cycle()
        self.finish()
        return (self.repo / LOG).read_bytes()

    def test_a_hand_copied_duplicate_entry_leaves_the_log_foreign(self):
        committed = self.finished()
        entry = committed[len(cycle_local_skills.NEW_LOG):]
        duplicate = cycle_local_skills.insert(committed, entry)
        self.assertEqual(len(self.log_entries(duplicate.decode())), 2)
        (self.repo / LOG).write_bytes(duplicate)
        rows = self.ok({'op': 'inspect'})['record']['forge_logs']
        self.assertIn({'path': LOG, 'state': 'foreign', 'cycles': [], 'resolver': 'main session'}, rows)
        result = self.ok({'op': 'commit-record'})
        self.assertIn({'path': LOG, 'reason': 'foreign'}, result['forge_log']['uncommitted'])
        self.assertEqual((self.repo / LOG).read_bytes(), duplicate)
        self.assertEqual(self.blob(LOG), committed)

    def test_an_engine_entry_hand_copied_into_another_root_stays_uncommitted(self):
        """Review A4: an entry belongs to the root that holds the skill; the same bytes in another root are foreign."""
        committed = self.finished()
        self.drop_log()
        other = '.agents/skills/forge-log.md'
        (self.repo / '.agents/skills').mkdir(parents=True)
        (self.repo / other).write_bytes(committed)
        result = self.ok({'op': 'commit-record'})
        flush = result['forge_log']
        self.assertEqual(flush['committed'], [LOG], 'positive control: the owning root receives and commits the entry')
        self.assertIn({'path': other, 'reason': 'foreign'}, flush['uncommitted'])
        self.assertNotIn(other, self.git('show', '--name-only', '--format=', 'HEAD').splitlines())
        self.assertEqual((self.repo / other).read_bytes(), committed)

    def test_a_working_log_deleted_while_head_holds_one_is_reported_and_not_recreated(self):
        self.finished()
        (self.repo / LOG).unlink()
        result = self.ok({'op': 'commit-record'})
        self.assertIn({'path': LOG, 'reason': 'absent-working-log'}, result['forge_log']['uncommitted'])
        self.assertFalse((self.repo / LOG).exists())
        self.assertTrue(self.blob(LOG), 'HEAD still holds the log')

    def test_an_index_lock_deferral_writes_no_forge_log_byte(self):
        expected = self.finished()
        self.drop_log()
        lock = Path(self.git('rev-parse', '--absolute-git-dir')) / 'index.lock'
        lock.write_bytes(b'')
        self.addCleanup(lambda: lock.unlink(missing_ok=True))
        result = self.ok({'op': 'commit-record'})
        self.assertEqual(result['forge_log']['deferred'], 'index-locked')
        self.assertEqual(result['forge_log']['appended'], [])
        self.assertFalse((self.repo / LOG).exists())
        self.assertEqual(list((self.repo / '.claude/skills').glob('.forge-log-*')), [])
        lock.unlink()
        recovered = self.ok({'op': 'commit-record'})
        self.assertEqual(recovered['forge_log']['committed'], [LOG], 'positive control: without the lock the entry lands')
        self.assertEqual((self.repo / LOG).read_bytes(), expected)

    def test_an_attempt_scoped_to_the_forge_log_passes_its_execution_check_after_a_lock_deferral(self):
        """CYC-0120 review N3: once an index-lock deferral clears, no forge-log byte stays dirty for a later attempt."""
        expected = self.finished()
        self.drop_log()
        lock = Path(self.git('rev-parse', '--absolute-git-dir')) / 'index.lock'
        lock.write_bytes(b'')
        self.addCleanup(lambda: lock.unlink(missing_ok=True))
        self.assertEqual(self.ok({'op': 'commit-record'})['forge_log']['deferred'], 'index-locked')
        lock.unlink()
        self.assertEqual(self.ok({'op': 'commit-record'})['forge_log']['committed'], [LOG])
        doc = create(self.repo, 'quick-fix', 'Log', 'Touch the log', [LOG], ['log kept'], 'builder', 'tester')
        self.cycles.append(doc['id'])
        self.add_tasks(doc['id'])
        held = self.ok({'op': 'prepare-dispatch', 'op_id': 'prep-build', 'task_id': 'build-it', 'role': 'developer',
                        'host': 'claude-code'}, cid=doc['id'])
        request = {'op': 'execution-check', 'op_id': 'log-scope-check', 'assignment': held['assignment'], 'attempt': 1,
                   'checkout': str(self.repo)}
        proved = self.ok(request, cid=doc['id'])
        self.assertEqual(proved['execution']['dirty_paths'], [])
        self.assertIn(LOG, proved['execution']['owned_paths'])
        self.assertEqual((self.repo / LOG).read_bytes(), expected)
        # Positive control: a forge-log byte left in the working tree refuses the same check.
        (self.repo / LOG).write_bytes(expected + b'stray\n')
        self.addCleanup((self.repo / LOG).write_bytes, expected)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cycle.main(['--repo-root', str(self.repo), 'op', doc['id'], '--json',
                               json.dumps({**request, 'op_id': 'log-scope-dirty'})])
        self.assertEqual(code, 1)
        self.assertIn('execution-dirty-owned-paths', [e['code'] for e in json.loads(out.getvalue())['errors']])

    def test_a_stale_temporary_is_reported_by_inspect_and_removed_by_the_next_flush(self):
        self.finished()
        self.drop_log()
        stale = self.repo / '.claude/skills/.forge-log-deadbeef.tmp'
        stale.write_bytes(b'partial')
        rows = self.ok({'op': 'inspect'})['record']['forge_logs']
        self.assertIn({'path': '.claude/skills/.forge-log-deadbeef.tmp', 'state': 'stale-temporary', 'cycles': []}, rows)
        result = self.ok({'op': 'commit-record'})
        self.assertFalse(stale.exists())
        self.assertEqual(result['forge_log']['committed'], [LOG])

    def test_a_restore_skips_bytes_that_changed_after_the_flush_wrote_them(self):
        """anthropic_top:F1: the unlanded commit finds the written log changed and leaves it alone."""
        self.run_cycle()
        (self.repo / LOG).write_bytes(cycle_local_skills.NEW_LOG)
        self.git('add', LOG); self.git('commit', '-q', '-m', 'empty log')
        edited = b'edited by another writer\n'

        def failing_commit(cfg, paths, message):
            (self.repo / LOG).write_bytes(edited)
            return {'changed': False, 'commit': None, 'paths': paths, 'message': None, 'deferred': 'commit-failed',
                    'detail': 'simulated', 'pending': paths}
        with patch.object(cycle_commit, 'commit_paths', failing_commit):
            done = self.finish()
        flush = done['record_commit']['forge_log']
        self.assertEqual([row['root'] for row in flush['error']], [LOG])
        self.assertIn('restore-skipped', flush['error'][0]['problem'])
        self.assertEqual((self.repo / LOG).read_bytes(), edited, 'the changed bytes stay as the other writer left them')


class SecondRootTests(CycleFixture):
    """IDR intended evidence 7: a flush error at a second root after a write at the first leaves both roots
    at their pre-flush bytes after a landed record-only commit."""

    CODEX_SKILL = 'probe-codex-answer'
    CODEX_LOG = '.agents/skills/forge-log.md'

    def extra_fixture(self):
        write_skill(self.repo, '.agents/skills', self.CODEX_SKILL)

    def codex_use(self):
        self.run_cycle()
        mutate(self.repo, self.cid, 'task-add', task={'id': 'codex-probe', 'phase': 'reflect',
                                                       'description': f'Probe with {self.CODEX_SKILL}.',
                                                       'depends_on': [], 'status': 'pending', 'expected_evidence': ['report']})
        prepared = self.ok({'op': 'prepare-dispatch', 'op_id': 'prep-codex', 'task_id': 'codex-probe', 'role': 'reviewer', 'host': 'codex'})
        self.assertEqual(prepared['local_skills']['offered'], [{'id': self.CODEX_SKILL, 'root': '.agents/skills'}])
        self.result(prepared, f'Local-Skill-Used: {self.CODEX_SKILL} ok')
        self.ok({'op': 'deliver', 'op_id': 'deliver-codex', 'assignment': prepared['assignment'], 'attempt': 1, 'outcome': 'done'})

    def test_positive_control_both_roots_receive_and_commit_their_entries(self):
        self.codex_use()
        flush = self.finish()['record_commit']['forge_log']
        self.assertEqual(sorted(flush['committed']), sorted([LOG, self.CODEX_LOG]))
        self.assertEqual(len(self.log_entries(self.git('show', f'HEAD:{self.CODEX_LOG}'), self.CODEX_SKILL)), 1)

    def test_an_error_at_the_second_root_restores_the_first(self):
        self.codex_use()
        real_write = cycle_local_skills._write

        def failing(repo_root, relative, data):
            if relative == self.CODEX_LOG:
                raise PermissionError('simulated second-root failure')
            return real_write(repo_root, relative, data)
        with patch.object(cycle_local_skills, '_write', failing):
            done = self.finish()
        flush = done['record_commit']['forge_log']
        self.assertTrue(done['record_commit']['changed'], 'the record-only commit lands')
        self.assertEqual(flush['committed'], [])
        self.assertEqual([row['root'] for row in flush['error']], ['.agents/skills'])
        self.assertFalse((self.repo / LOG).exists(), 'the first root is back to its pre-flush absence')
        self.assertFalse((self.repo / self.CODEX_LOG).exists())
        changed = self.git('show', '--name-only', '--format=', done['record_commit']['commit']).splitlines()
        self.assertFalse([path for path in changed if path.endswith('forge-log.md')])


class InsertionRuleTests(unittest.TestCase):
    """anthropic_top:F4: a log with no entry and no trailing LF receives exactly one LF before the block."""

    BLOCK = b'## [2026-11-07 10:00] used | probe-x\nCYC-0001 a/1 reviewer report; ok\n\n'

    def test_one_lf_joins_a_log_without_a_trailing_lf(self):
        base = b'# Forge log'
        written = cycle_local_skills.insert(base, self.BLOCK)
        self.assertEqual(written, base + b'\n' + self.BLOCK)
        self.assertEqual(cycle_local_skills.inserted_block(written, base), self.BLOCK)
        derived = {('probe-x', 'CYC-0001', 'a', 1): self.BLOCK}
        self.assertEqual(cycle_local_skills.committable(written, base, derived), (True, [('probe-x', 'CYC-0001', 'a', 1)]))
        # No LF, or two, is not the rule's one LF.
        self.assertIsNone(cycle_local_skills.inserted_block(base + self.BLOCK, base))
        self.assertFalse(cycle_local_skills.committable(base + b'\n\n' + self.BLOCK, base, derived)[0])

    def test_a_log_ending_in_lf_receives_no_extra_lf(self):
        base = b'# Forge log\n'
        self.assertEqual(cycle_local_skills.insert(base, self.BLOCK), base + self.BLOCK)
        self.assertEqual(cycle_local_skills.inserted_block(base + self.BLOCK, base), self.BLOCK)

    def test_a_block_lands_before_the_first_entry(self):
        base = cycle_local_skills.NEW_LOG + b'## [2026-01-01 00:00] authored | probe-x\nold\n\n'
        written = cycle_local_skills.insert(base, self.BLOCK)
        self.assertEqual(written, cycle_local_skills.NEW_LOG + self.BLOCK + base[len(cycle_local_skills.NEW_LOG):])


class ListingEdgeTests(unittest.TestCase):
    """Review A5, A6 and A7."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()

    def test_a_refused_opencode_skills_copy_does_not_promote_the_singular_copy(self):
        control = self.base / 'control'
        write_skill(control, '.opencode/skill', 'dup-skill')
        found = cycle_local_skills.listing(control, 'opencode', frozenset())
        self.assertEqual([item['id'] for item in found['skills']], ['dup-skill'], 'positive control: the singular copy lists alone')
        repo = self.base / 'repo'
        write_skill(repo, '.opencode/skills', 'dup-skill', header='name: dup-skill\ndescription: x\ntools: Bash\n')
        write_skill(repo, '.opencode/skill', 'dup-skill')
        found = cycle_local_skills.listing(repo, 'opencode', frozenset())
        self.assertEqual(found['skills'], [])
        self.assertEqual(found['refused'], [{'id': 'dup-skill', 'root': '.opencode/skills', 'reason': 'declares-tool-grant'},
                                            {'id': 'dup-skill', 'root': '.opencode/skill', 'reason': 'duplicate-id'}])

    def test_closed_statuses_come_from_the_cycle_engine(self):
        import cycle_workflow
        self.assertIs(cycle_local_skills.CLOSED, cycle_workflow.CLOSED)

    def test_deeply_nested_frontmatter_is_refused_and_never_fails_the_listing(self):
        repo = self.base / 'nested'
        write_skill(repo, '.claude/skills', 'good-skill')
        depth = 5000
        write_skill(repo, '.claude/skills', 'nested-skill',
                    header='name: nested-skill\ndescription: x\nx: ' + '[' * depth + ']' * depth + '\n')
        found = cycle_local_skills.listing(repo, 'claude-code', frozenset())
        self.assertEqual([item['id'] for item in found['skills']], ['good-skill'], 'positive control: the sibling still lists')
        self.assertEqual(found['refused'], [{'id': 'nested-skill', 'root': '.claude/skills', 'reason': 'invalid-frontmatter'}])



# ───────────────────────────── rendering, frozen bundles and instruction text (review A1, A2) ─────────────────────────────

class RenderingAndBundleTests(CycleFixture):
    LINE = (f'Project-local skills matching this task, in .claude/skills: {SKILL}. '
            "Invoke them through this host's skill capability; they grant no capability.")

    def dispatch(self, task_id, description):
        mutate(self.repo, self.cid, 'task-add', task={'id': task_id, 'phase': 'build', 'description': description,
                                                       'depends_on': [], 'status': 'pending', 'expected_evidence': ['report']})
        return self.ok({'op': 'prepare-dispatch', 'op_id': f'prep-{task_id}', 'task_id': task_id, 'role': 'reviewer',
                        'host': 'claude-code'})

    def bundle(self, prepared):
        return json.loads((self.repo / 'bionic' / prepared['invocation_snapshot']['path']).read_text())

    def test_the_local_line_renders_alone_with_no_plugin_body_or_name(self):
        import cycle_dispatch
        cfg, doc = tree(self.repo), load(self.repo, self.cid)
        offered = [{'id': SKILL, 'root': '.claude/skills'}]
        self.assertEqual(cycle_dispatch._reference_message(cfg, doc, [], [], offered), '\n\n' + self.LINE + '\n')
        self.assertEqual(cycle_dispatch._reference_message(cfg, doc, [], [], []), '', 'no plugin and no local name renders nothing')
        # Positive control: a plugin name renders its own line before the local one.
        both = cycle_dispatch._reference_message(cfg, doc, [], ['council'], offered)
        self.assertIn('Other candidate skills remain retrievable through the host Skill capability: council.', both)
        self.assertLess(both.index('council'), both.index(self.LINE))
        prepared = self.dispatch('alone-it', f'Use {SKILL}.')
        # This dispatch also retrieves the plugin `cycle` skill, so the local line renders last, after the plugin line.
        self.assertTrue(self.bundle(prepared)['context_message'].endswith('\n\n' + self.LINE + '\n'))

    def test_a_bundle_frozen_before_local_candidates_verifies_unchanged(self):
        """IDR intended evidence 13: a bundle without local fields loads, reads as no local skills, and its
        replayed preamble carries no report line, with local roots present or not."""
        import cycle_dispatch
        aside = self.repo.parent / (self.repo.name + '-aside-claude')
        shutil.move(str(self.repo / '.claude/skills'), aside)
        try:
            prepared = self.dispatch('frozen-it', f'Review the change with {SKILL}.')
        finally:
            shutil.move(str(aside), self.repo / '.claude/skills')
        bundle = self.bundle(prepared)
        self.assertNotIn(cycle_hosts.LOCAL_SKILL_REPORT, bundle['preamble'])
        old = {key: value for key, value in bundle.items() if key not in ('local_candidates', 'local_refused')}
        raw = cycle_dispatch._encode(old)
        sha = hashlib.sha256(raw).hexdigest()
        doc = load(self.repo, self.cid)
        ref = {'path': f'{cycle_dispatch._root(doc)}/{sha}.json', 'sha256': sha}
        (self.repo / 'bionic' / ref['path']).write_bytes(raw)
        loaded = cycle_dispatch.load(tree(self.repo), doc, ref)
        self.assertEqual(loaded, old)
        self.assertEqual(cycle_dispatch.local_skills(loaded), {'offered': [], 'refused': []})
        self.assertNotIn(cycle_hosts.LOCAL_SKILL_REPORT, loaded['preamble'])
        self.assertTrue((self.repo / '.claude/skills' / SKILL / 'SKILL.md').is_file(), 'the local root is present again')
        # Positive control: a bundle reserved now, with the root present, carries the report line.
        current = self.bundle(self.dispatch('current-it', f'Review the change with {SKILL}.'))
        self.assertIn(cycle_hosts.LOCAL_SKILL_REPORT, current['preamble'])


if __name__ == '__main__':
    unittest.main()
