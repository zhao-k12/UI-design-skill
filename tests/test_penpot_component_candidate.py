"""Source plan integrity only; not platform fidelity acceptance."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from adapters.penpot.component_candidate import prepare_button_candidate, prepare_input_candidate, prepare_select_candidate
from adapters.penpot.host.server import candidate_assets
from validators.ui_ir import ROOT,load_json


class PenpotButtonPlanTests(unittest.TestCase):
    def test_select_uses_selected_value_and_source_arrow_without_admission(self):
        spec=prepare_select_candidate(ROOT/'adapters/figma/metadata/official-fixture-reference','test-file','test-page')
        self.assertEqual(spec['characters'],'启用');self.assertEqual(spec['arrow']['characters'],'\uf116')
        self.assertEqual(spec['sourceTextBounds'],{'x':9,'y':8,'width':28,'height':16})
        self.assertEqual(spec['arrow']['bounds'],{'x':217,'y':9,'width':14,'height':14})
        hosted=candidate_assets('http://127.0.0.1:60000','test-file','nonce',spec)
        self.assertIn('await buildPenpotSelectCandidate(penpot,candidateSpec)',hosted['/plugin.js'][1])
        self.assertIn('unsupported_select_action',hosted['/plugin.js'][1])
        changed=deepcopy(spec);changed['arrow']['bounds']['y']+=1
        with self.assertRaises(ValueError):candidate_assets('http://127.0.0.1:60000','test-file','nonce',changed)
    def test_input_placeholder_source_does_not_claim_native_text_geometry(self):
        p=prepare_input_candidate(ROOT/'adapters/figma/metadata/official-fixture-reference',
            ROOT/'adapters/figma/metadata/official-runtime-render-state-evidence.json','test-file','test-page')
        self.assertEqual(p['sourceTextBounds'],{'x':8,'y':8,'width':70,'height':16})
        self.assertEqual(p['ignoredHiddenPaths'],['0.0'])
        self.assertEqual(p['stroke'],'#dcdee2');self.assertEqual(p['fill'],'#ffffff')
        self.assertEqual(p['labelRole'],'placeholder');self.assertIsNone(p['nativeTextBounds'])
        self.assertEqual(p['fidelityGate'],'NOT_RUN')
        hosted=candidate_assets('http://127.0.0.1:60000','test-file','nonce',p)
        self.assertIn('await buildPenpotInputCandidate(penpot,candidateSpec)',hosted['/plugin.js'][1])
        self.assertIn('unsupported_input_action',hosted['/plugin.js'][1])
        changed=deepcopy(p);changed['sourceTextBounds']['y']+=1
        with self.assertRaises(ValueError):candidate_assets('http://127.0.0.1:60000','test-file','nonce',changed)

    def test_input_rejects_wrong_source_environment_or_placeholder_evidence(self):
        evidence=load_json(ROOT/'adapters/figma/metadata/official-runtime-render-state-evidence.json')
        for field in ('referenceComponentIrSha256','environment','observations'):
            changed=deepcopy(evidence)
            if field=='referenceComponentIrSha256':changed[field]='0'*64
            elif field=='environment':changed[field]['deviceScaleFactor']=2
            else:
                next(o for o in changed[field] if o['logicalId']=='form.input.default.medium')['text']='wrong'
            with tempfile.TemporaryDirectory() as folder:
                path=Path(folder,'evidence.json');path.write_text(json.dumps(changed),encoding='utf-8')
                with self.assertRaises(ValueError):prepare_input_candidate(
                    ROOT/'adapters/figma/metadata/official-fixture-reference',path,'test-file','test-page')

    def test_admitted_source_geometry_and_content_without_native_calibration(self):
        reference=ROOT/'adapters/figma/metadata/official-fixture-reference'
        p=prepare_button_candidate(reference,'test-file','test-page')
        source=load_json(reference/'component_ir.json')['components'][0]
        self.assertEqual(p['rootBounds'],source['rootBounds']);self.assertEqual(p['characters'],source['content']['text'])
        self.assertEqual(p['labelBounds'],source['nodes'][1]['bounds']);self.assertEqual(p['radius'],4)
        self.assertEqual(p['baselineCalibration'],'NOT_RUN');self.assertEqual(p['fidelityGate'],'NOT_RUN')
        self.assertNotIn('figma',json.dumps(p).lower())

    def test_changed_source_cannot_use_admitted_digest(self):
        data=load_json(ROOT/'adapters/figma/metadata/official-fixture-reference/component_ir.json')
        data=deepcopy(data);data['components'][0]['content']['text']='changed'
        with tempfile.TemporaryDirectory() as folder:
            Path(folder,'component_ir.json').write_text(json.dumps(data),encoding='utf-8')
            with self.assertRaises(ValueError):prepare_button_candidate(folder,'test-file','test-page')

    def test_host_rejects_modified_source_plan_before_generating_plugin(self):
        spec=prepare_button_candidate(ROOT/'adapters/figma/metadata/official-fixture-reference','test-file','test-page')
        changed=deepcopy(spec);changed['characters']='changed'
        with self.assertRaises(ValueError):candidate_assets('http://127.0.0.1:60000','test-file','test-nonce',changed)
        manifest=json.loads(candidate_assets('http://127.0.0.1:60000','test-file','test-nonce',spec)['/manifest.json'][1])
        self.assertEqual(manifest['permissions'],['content:write','library:write'])
