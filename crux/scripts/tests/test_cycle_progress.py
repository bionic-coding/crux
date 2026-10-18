"""Cycle visualization uses guarded reads and distinct cycle semantics."""
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cycle_workflow import create,mutate,CycleError
from cycle_progress import view,render
from admission_source_io import SourceIORefusal


class ProgressTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        (self.root/'bionic').mkdir();(self.root/'src').mkdir()
        (self.root/'bionic/manifest.yml').write_text('schema_version: "5"\nconcerns_enabled: [adrs]\n')
    def test_cycle_phases_passes_and_history(self):
        doc=create(self.root,'quick-fix','Fix','Correct behavior',['src'],['passes'],'builder','tester')
        output=view(self.root)
        c=output['cycles'][0]
        self.assertEqual(output['format'],'crux.cycle-progress');self.assertEqual(c['phases'],['build','test','review','reflect'])
        self.assertEqual(c['pass_limit'],1);self.assertIn('Pass 1 of 1',render(output))
        mutate(self.root,doc['id'],'pause',reason='needs owner')
        self.assertEqual(view(self.root)['cycles'][0]['blocker'],'needs owner')
    def test_outside_symlink_config_is_refused(self):
        other=Path(self.temp.name).parent/'cycle-reader-outside.yml'
        other.write_text('config_version: "1"\ndocs_dir: bionic\n');self.addCleanup(other.unlink)
        (self.root/'.bionic.yml').symlink_to(other)
        with self.assertRaises(SourceIORefusal):view(self.root)
    def test_dashboard_entry_automatically_selects_cycles(self):
        create(self.root,'iterate','Fix','Correct behavior',['src'],['passes'],'builder','tester')
        path=Path(__file__).resolve().parents[1]/'visualize-run-progress.py'
        spec=importlib.util.spec_from_file_location('cycle_dashboard_legacy',path);mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)
        output=io.StringIO()
        with redirect_stdout(output):code=mod.main(['--json','--project-root',str(self.root)])
        self.assertEqual(code,0);self.assertEqual(json.loads(output.getvalue())['format'],'crux.cycle-progress')
    def test_symlink_cycle_record_refused(self):
        doc=create(self.root,'iterate','Fix','Correct behavior',['src'],['passes'],'builder','tester')
        path=self.root/'bionic/cycles'/doc['id']/'cycle.json';data=path.read_text();path.unlink()
        other=self.root/'other.json';other.write_text(data);path.symlink_to(other)
        with self.assertRaises((CycleError,SourceIORefusal)):view(self.root)

if __name__=='__main__':unittest.main()
