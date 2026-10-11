"""Actual mixed-font source and native readbacks, including admission blockers."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from adapters.configurable_table import prepare_source,prepare_penpot
from adapters.penpot.configurable_table_qa import validate_geometry
from adapters.penpot.host import configurable_table_server as host
from validators.ui_ir import ROOT,load_json
from validators.visual.fidelity import file_hash

SOURCES=ROOT/'component-builder/runtime-renderer/metadata/configurable-table-source'
NATIVE=ROOT/'adapters/penpot/metadata/configurable-table-native'

class ConfigurableTableTests(unittest.TestCase):
    def test_actual_sources_bind_fonts_per_cell_without_admitting_new_components(self):
        for case,rows,columns in [('two-column',2,2),('four-column',4,4)]:
            plan=prepare_source(SOURCES/case)
            self.assertEqual(plan['requiredFonts'],['Arial','PingFang SC'])
            self.assertEqual((len(plan['rows']),len(plan['rows'][0]['cells'])),(rows,columns))
            self.assertFalse(plan['admissionEligible']);self.assertEqual(plan['fidelityGate'],'NOT_RUN')
            self.assertEqual(plan['rows'][0]['cells'][0]['text']['fontFamily'],'PingFang SC' if columns==2 else 'Arial')

    def test_changed_source_request_baseline_font_or_extractor_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'source';shutil.copytree(SOURCES/'two-column',target)
            for name in ('request.json','table-observation.json','source-extractor.mjs'):
                original=(target/name).read_bytes();(target/name).write_bytes(original+b'\n')
                with self.assertRaises(ValueError):prepare_source(target)
                (target/name).write_bytes(original)
            observation=load_json(target/'table-observation.json');observation['fonts'][1][0]['familyName']='Substitute'
            (target/'table-observation.json').write_text(json.dumps(observation),encoding='utf8')
            receipt=load_json(target/'configurable-source.json');receipt['observationSha256']=file_hash(target/'table-observation.json')
            (target/'configurable-source.json').write_text(json.dumps(receipt),encoding='utf8')
            with self.assertRaisesRegex(ValueError,'unsupported_table_cell_font'):prepare_source(target)

    def test_independent_actual_native_geometry_passes_with_two_font_identities(self):
        fonts=load_json(NATIVE/'font-discovery.json')['result']['fonts']
        bindings={f['family']:{'fontId':f['fontId'],'fontVariantId':'normal-400'} for f in fonts if f['family'] in ('Arial','PingFang SC')}
        for case,count in [('two-column',14),('four-column',42)]:
            native=load_json(NATIVE/(case+'-capture-after-background.json'))['result']
            plan=prepare_penpot(SOURCES/case,native['fileReference'],native['pageReference'])
            report=validate_geometry(native,plan,bindings)
            self.assertEqual(report['status'],'PASS');self.assertEqual(len(native['nodes']),count)
            self.assertFalse(report['productionAdmission']);self.assertEqual(report['fidelityGate'],'NOT_RUN')
            with self.assertRaisesRegex(ValueError,'table_fill_mismatch'):
                validate_geometry(load_json(NATIVE/(case+'-capture-initial.json'))['result'],plan,bindings)
            for mutation in ('font','content','geometry','inventory'):
                changed=deepcopy(native);text=next(n for n in changed['nodes'] if n['type']=='text' and n['fontFamily']=='Arial')
                if mutation=='font':text['fontId']=bindings['PingFang SC']['fontId']
                elif mutation=='content':text['characters']='substituted'
                elif mutation=='geometry':text['width']+=1
                else:changed['nodes'].pop()
                with self.assertRaises(ValueError):validate_geometry(changed,plan,bindings)

    def test_source_host_recovery_requires_same_actual_source_and_target(self):
        original=host.SOURCE_DIRECTORIES;self.addCleanup(setattr,host,'SOURCE_DIRECTORIES',original)
        host.SOURCE_DIRECTORIES=[SOURCES/'two-column',SOURCES/'four-column']
        readback=load_json(NATIVE/'creation.json')['result'];file=readback['fileReference']
        served=host.table_assets('http://127.0.0.1:57831',file,'nonce',readback)
        self.assertIn('captureConfigurablePenpotTable',served['/plugin.js'][1])
        self.assertIn('table_existing_page_requires_recovery',served['/plugin.js'][1])
        for changed in (None,'source'):
            broken=deepcopy(readback)
            if changed is None:broken['fileReference']='another-file'
            else:broken['candidates'][0]['componentIrSha256']='0'*64
            with self.assertRaises(ValueError):host.table_assets('http://127.0.0.1:57831',file,'nonce',broken)
