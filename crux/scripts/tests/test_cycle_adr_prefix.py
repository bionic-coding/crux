"""Prefixed new ADRs retain acceptance proof through live readers and indexes."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(SCRIPTS))
import decision_policy as dp
import summaries_projection as sp
from cycle_workflow import digest,encoded


def script(name):
    spec=importlib.util.spec_from_file_location('_prefix_'+name.replace('-','_'),SCRIPTS/(name+'.py'))
    mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)
    return mod


class PrefixIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name).resolve()
        self.docs=self.root/'bionic';self.docs.mkdir()
        (self.root/'.bionic.yml').write_text('config_version: "1"\ndocs_dir: bionic\nartifact_prefix: DEMO\nadr:\n  acceptance: council-only\n')
        (self.docs/'manifest.yml').write_text('schema_version: "5"\nconcerns_enabled: [adrs]\nadr:\n  next_number: 1\n')
    def accepted(self):
        proposal={'title':'Preserve useful evidence','body':'# Decision\n\nKeep the evidence.\n','governs':[{'domain':'evidence','rule':'Keep useful evidence.','scope':'src/','handle':'keep-evidence'}]}
        subject=dp.propose(self.root,proposal,origin='direct')['path']
        record={'format':'crux.cycle-council','purpose':'adr','subject':subject,'subject_sha256':digest((self.docs/subject).read_bytes()),'outcome':'approved','cycle_id':None,'seats':[{'provider':p,'decision':'APPROVE','errored':False,'findings':[]} for p in ('openai','anthropic','google')]}
        record['record_sha256']=digest(encoded(record));path=self.docs/'adrs/councils/approval.json';path.parent.mkdir();path.write_bytes(encoded(record))
        dp.accept(self.root,subject,path.relative_to(self.docs).as_posix())
        return self.docs/subject
    def test_prefixed_acceptance_projects_and_indexes(self):
        path=self.accepted();records=sp.collect_records(self.docs/'adrs')
        self.assertEqual(['DEMO-ADR-0001/keep-evidence'],[r['handle'] for r in records])
        resolver=sp.build_resolver(records)
        row=resolver['DEMO-ADR-0001/keep-evidence']
        self.assertEqual(row['source_adr'],'DEMO-ADR-0001');self.assertEqual(row['source_status'],'Accepted');self.assertEqual(row['authority'],'prescriptive')
        index=script('generate-adr-index');self.assertIn('DEMO-ADR-0001',index.build(self.root)[1])
        lineage=script('generate-lineage');self.assertIn('DEMO-ADR-0001',lineage.render(lineage._load_adrs(self.docs/'adrs')))
        rollup=script('generate-index-rollup');self.assertIn('DEMO-ADR-0001',rollup.render_section(rollup.load_adrs(self.docs/'adrs')))
        citation=script('lint-governs-references')
        self.assertEqual(['DEMO-ADR-0001'],citation.find_doc_refs('See DEMO-ADR-0001.'))
        self.assertEqual(['DEMO-ADR-0001/keep-evidence'],citation.find_handles('DEMO-ADR-0001/keep-evidence'))
        self.assertEqual([],citation.find_doc_refs('DEMO-ADR-0001/keep-evidence'))
        self.assertTrue(sp._HANDLE_ANCHOR_RE.fullmatch('DEMO-ADR-0001/keep-evidence'))
        self.assertEqual(sp._HANDLE_ANCHOR_RE.fullmatch('DEMO-ADR-0001/keep-evidence').group(1),'0001')
    def test_missing_prefixed_receipt_is_refused(self):
        self.accepted()
        (self.docs/'adrs/acceptances/DEMO-ADR-0001.json').unlink()
        with self.assertRaisesRegex(ValueError,'acceptance receipt missing'):sp.collect_records(self.docs/'adrs')
    def test_archived_prefixed_handles_and_identity_remain_retrievable(self):
        path=self.accepted();archive=self.docs/'adrs/archive';archive.mkdir();path.rename(archive/path.name)
        self.assertEqual(set(),set(r['handle'] for r in sp.collect_records(self.docs/'adrs')))
        self.assertIn('DEMO-ADR-0001/keep-evidence',sp.archived_handles(self.docs/'adrs'))
        self.assertIn('DEMO-ADR-0001',sp._adr_ids_including_archive(self.docs/'adrs'))
        index=script('generate-adr-index');self.assertIn('DEMO-ADR-0001',index.build(self.root)[1]);self.assertIn('## Archived (1)',index.build(self.root)[1])
    def test_same_number_foreign_prefix_cannot_claim_a_rule(self):
        import yaml
        self.accepted()
        bad={'id':'DEMO-ADR-0002','status':'Accepted','governs':[{'domain':'evidence','rule':'Keep useful evidence.','scope':'src/','handle':'OTHER-ADR-0002/foreign-rule','provenance':'authored'}]}
        (self.docs/'adrs/DEMO-ADR-0002-foreign.md').write_text('---\n'+yaml.safe_dump(bad)+'---\n\n# Decision\n')
        with self.assertRaises(sp.GovernsValidationError) as caught:
            sp.collect_records(self.docs/'adrs')
        self.assertTrue(any('anchors OTHER-ADR-0002' in problem['problem'] for problem in caught.exception.problems))
    def test_unrelated_markdown_and_malformed_prefix_are_not_new_adr_inputs(self):
        self.accepted()
        for name in ('index.md','X-ADR-0002-no.md','lower-ADR-0003-no.md'):
            (self.docs/'adrs'/name).write_text('not an ADR')
        self.assertEqual(1,len(sp.collect_records(self.docs/'adrs')))

if __name__=='__main__':unittest.main()
