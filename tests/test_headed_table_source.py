import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from shutil import copytree
from adapters.headed_table import prepare_source
from validators.ui_ir import ROOT
from validators.visual.fidelity import file_hash

class HeadedTableSourceTests(unittest.TestCase):
    def test_exact_header_body_font_and_fractional_geometry(self):
        for case,columns,rows,height in [('two-column',2,3,134.875),('four-column',4,5,230.875)]:
            plan=prepare_source(ROOT/'component-builder/runtime-renderer/metadata/headed-table-source'/(case+'-typography'))
            self.assertFalse(plan['admissionEligible'])
            self.assertEqual(plan['fidelityGate'],'NOT_RUN')
            self.assertEqual(plan['rootBounds']['height'],height)
            self.assertEqual(len(plan['rows']),rows)
            self.assertEqual(len(plan['rows'][0]['cells']),columns)
            for cell in plan['rows'][0]['cells']:
                text=cell['text']
                self.assertEqual((text['role'],text['fontWeight'],text['sourceCssFontWeight'],text['postScriptName']),('header',600,700,'PingFangSC-Semibold'))
                self.assertEqual(text['sourceBaselineY'],23.875)
            for row in plan['rows'][1:]:
                self.assertTrue(all(cell['text']['fontWeight']==400 and cell['text']['role']=='body' for cell in row['cells']))

    def test_changed_baseline_receipt_is_rejected(self):
        source=ROOT/'component-builder/runtime-renderer/metadata/headed-table-source/two-column-typography'
        with TemporaryDirectory() as temporary:
            copy=Path(temporary)/'source';copytree(source,copy)
            path=copy/'table-observation.json';data=json.loads(path.read_text());data['baselines'][0]['baselineComponentY']+=1
            path.write_text(json.dumps(data),encoding='utf8')
            with self.assertRaisesRegex(ValueError,'table_source_binding_mismatch'):
                prepare_source(copy)

    def test_body_font_cannot_be_used_for_header_even_with_updated_observation_hash(self):
        source=ROOT/'component-builder/runtime-renderer/metadata/headed-table-source/two-column-typography'
        with TemporaryDirectory() as temporary:
            copy=Path(temporary)/'source';copytree(source,copy)
            path=copy/'table-observation.json';data=json.loads(path.read_text());data['fonts'][0][0]['postScriptName']='PingFangSC-Regular'
            path.write_text(json.dumps(data),encoding='utf8')
            receipt=copy/'configurable-source.json';binding=json.loads(receipt.read_text());binding['observationSha256']=file_hash(path);receipt.write_text(json.dumps(binding),encoding='utf8')
            with self.assertRaisesRegex(ValueError,'table_role_font_mismatch'):
                prepare_source(copy)
