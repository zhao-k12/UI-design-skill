"""Script ownership and invalidation tests; builders here are explicit fixtures."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from adapters.figma.candidates import run
from validators.ui_ir import ROOT


class CandidateScriptTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='candidate-tests-',dir=ROOT/'artifacts')
        self.addCleanup(self.temp.cleanup)
        self.directory=Path(self.temp.name)
        self.reference=self.directory/'inputs'; self.reference.mkdir()
        self.output=self.directory/'output'
        self.bundle={'components':[{'logicalComponentId':'fixture.button','componentType':'Button'},
            {'logicalComponentId':'fixture.input','componentType':'Input'}]}
        (self.reference/'component_ir.json').write_text(json.dumps(self.bundle))
        self.evidence=self.reference/'fonts.json';self.evidence.write_text('{}')
        self.discovery=self.reference/'discovery.json';self.discovery.write_text('{}')
        self.pass_report={'status':'PASS','issues':[],'script':'// fixture only\n','nativeExecution':'NOT_RUN'}
        self.blocked={'status':'REVIEW','issues':[{'code':'missing_official_font'}],'script':None}
        self.button_patch=patch('adapters.figma.candidates.prepare_button',return_value=self.pass_report.copy())
        self.input_patch=patch('adapters.figma.candidates.prepare_form',return_value=self.pass_report.copy())
        self.button=self.button_patch.start();self.form=self.input_patch.start()
        self.addCleanup(self.button_patch.stop);self.addCleanup(self.input_patch.stop)

    def execute(self,**kwargs):
        return run(self.reference,self.evidence,self.discovery,output=self.output,
            file_reference='fixture',page_reference='fixture-page',**kwargs)

    def test_whole_selection_blocks_and_revokes_previous_scripts(self):
        self.assertEqual(self.execute()['status'],'PASS')
        self.assertEqual(len(list(self.output.glob('*.js'))),2)
        self.button.return_value=self.pass_report.copy();self.form.return_value=self.blocked.copy()
        self.assertEqual(self.execute()['status'],'REVIEW')
        self.assertEqual(list(self.output.glob('*.js')),[])
        self.assertEqual(json.loads((self.output/'candidate_scripts.json').read_text())['scripts'],{})

    def test_selected_component_emits_one_script_and_hash(self):
        report=self.execute(logical_ids=['fixture.button'])
        self.assertEqual(report['status'],'PASS')
        self.form.assert_not_called()
        path=self.output/'candidate-fixture.button.js'
        ledger=json.loads((self.output/'candidate_scripts.json').read_text())
        self.assertEqual(ledger['scripts'][path.name],hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertEqual(report['nativeExecution'],'NOT_RUN')

    def test_modified_script_preserved_before_any_owned_deletion(self):
        self.execute()
        path=self.output/'candidate-fixture.button.js';path.write_text('// user edit')
        report=self.execute()
        self.assertEqual(report['status'],'FAIL')
        self.assertEqual(path.read_text(),'// user edit')
        self.assertTrue((self.output/'candidate-fixture.input.js').exists())
        self.assertIn('modified_candidate_script_preserved',report['issues'][0]['detail'])
        ledger=json.loads((self.output/'candidate_scripts.json').read_text())
        self.assertEqual(ledger['status'],'FAIL');self.assertEqual(ledger['scripts'],{})
        self.assertEqual(len(ledger['preservedScripts']),2)
        self.assertEqual(self.execute()['status'],'FAIL')

    def test_unowned_script_and_invalid_input_cannot_keep_pass_report(self):
        self.output.mkdir()
        path=self.output/'candidate-fixture.button.js';path.write_text('// unowned')
        report=self.execute()
        self.assertEqual(report['status'],'FAIL');self.assertEqual(path.read_text(),'// unowned')
        self.assertFalse((self.output/'candidate-fixture.input.js').exists())
        path.unlink();self.evidence.write_text('not json')
        self.assertEqual(self.execute()['status'],'FAIL')
        self.assertEqual(json.loads((self.output/'candidate_build_report.json').read_text())['status'],'FAIL')

    def test_output_cannot_overwrite_inputs(self):
        with self.assertRaisesRegex(ValueError,'separate_artifacts'):
            run(self.reference,self.evidence,self.discovery,output=self.reference,
                file_reference='fixture',page_reference='fixture-page')
