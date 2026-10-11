import unittest
import json
import hashlib
from copy import deepcopy
from pathlib import Path
from adapters.penpot.icon_native_evidence import verify_icon_native_evidence


class IconNativeEvidenceTests(unittest.TestCase):
    def test_actual_complete_exports_pass_subcheck_without_admission(self):
        base=Path(__file__).resolve().parents[1]/'adapters/penpot/metadata'
        plan=json.loads((base/'icon-source-plan/plan.json').read_bytes())
        raw=(base/'icons-native-v1/latest-main-capture.json').read_bytes()
        receipt=json.loads(raw)
        probe=json.loads((base/'icons-native-v1/latest-svg-probe.json').read_bytes())
        report=verify_icon_native_evidence(plan,receipt,probe,raw)
        self.assertEqual(report['status'],'PASS');self.assertFalse(report['admissionEligible'])
        self.assertEqual(report['actualInstanceAcceptance'],'NOT_RUN')
        mutations=[lambda r:r['result'].update(status='PARTIAL'),lambda r:r['result'].update(fileReference='foreign'),lambda r:r['result'].update(mutatedNodeIds=['x']),lambda r:r['result']['icons'][0].update(nativePngBase64=''),lambda r:r['result']['icons'][0].update(rasterScope='content'),lambda r:r['result']['icons'][0]['nodes'][3].update(parentReference='foreign'),lambda r:r['result']['icons'][0]['nodes'][3]['fills'][0].update(fillOpacity=0.9),lambda r:r['result']['icons'][0]['nodes'][3].update(d='M0 0L1 1Z'),lambda r:r['result']['icons'][0]['nodes'][1].update(rotation=1)]
        for mutate in mutations:
            changed=deepcopy(receipt);mutate(changed)
            changed_raw=json.dumps(changed).encode(); changed_probe=deepcopy(probe)
            changed_probe['nativeReceiptSha256']=hashlib.sha256(changed_raw).hexdigest()
            with self.assertRaises(ValueError):verify_icon_native_evidence(plan,changed,changed_probe,changed_raw)
        for key,value in [('completeNativeCapture',False),('nativeReceiptSha256','wrong')]:
            changed=deepcopy(probe);changed[key]=value
            with self.assertRaises(ValueError):verify_icon_native_evidence(plan,receipt,changed,raw)
