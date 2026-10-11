import json
import unittest
from copy import deepcopy
from validators.ui_ir import ROOT
from adapters.penpot.page_final_qa import run,verify_flow,verify_instances,translated_path_exact


class PenpotFinalPageTests(unittest.TestCase):
    def test_actual_complete_page_passes_with_real_source_bound_instances(self):
        base=ROOT/'adapters/penpot/metadata/list-acceptance';read=lambda name:json.loads((base/name).read_bytes())
        report=run(base);self.assertEqual(report['status'],'PASS');self.assertEqual(report['logicalNodes'],34);self.assertEqual(report['nativeInstances'],6)
        plan=read('plan.json');execution=read('execution.json')['result'];capture=read('capture.json')['result'];packet=read('instances-capture.json')['result'];probe=read('icon-instance-svg-probe.json');previous=read('partial-instances-capture-2.json')['result']
        changed=deepcopy(capture);changed['topology'][1]['x']+=1
        with self.assertRaises(ValueError):verify_flow(plan,changed)
        for mutate in [lambda p:p.update(status='PARTIAL'),lambda p:p.update(fileRevision=0),lambda p:p['instances'][0].update(isComponentCopy=False),lambda p:p['instances'][1]['instanceNodes'][2].update(characters='wrong'),lambda p:p['instances'][0].update(componentReference='foreign'),lambda p:p['instances'][0]['instanceNodes'][3].update(d='M0 0L1 1Z')]:
            changed=deepcopy(packet);mutate(changed)
            with self.assertRaises(ValueError):verify_instances(plan,execution,capture,changed,probe,base,previous)

    def test_scene_encoding_requires_exact_float32_and_order(self):
        self.assertTrue(translated_path_exact('M0.1 0L1 0L1 1Z','M100.0999984741211 20L101 20L101 21Z',100,20))
        self.assertFalse(translated_path_exact('M0.1 0L1 0L1 1Z','M100.1 20L101 20L101 21Z',100,20))
        self.assertFalse(translated_path_exact('M0.1 0L1 0L1 1Z','M100.0999984741211 20L101 21L101 20Z',100,20))
