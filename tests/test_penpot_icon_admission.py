import json
import unittest
from copy import deepcopy
from unittest.mock import patch
from validators.ui_ir import ROOT
from adapters.penpot.icon_admission import build_gate,verify_binding


class IconAdmissionTests(unittest.TestCase):
    def test_actual_masters_have_recomputable_source_bound_proof(self):
        report=build_gate();self.assertEqual(report['status'],'PASS');self.assertTrue(report['admissionEligible'])
        self.assertEqual(report['actualInstanceAcceptance'],'NOT_RUN')
        metadata=json.loads((ROOT/'adapters/penpot/metadata/icon-bindings.json').read_bytes())
        for icon,binding in metadata['bindings'].items():
            self.assertEqual(verify_binding(icon,binding,report['fileReference'],metadata['registrySha256'])['status'],'PASS')
            for change in [{'fidelityReportSha256':'manual-pass'},{'componentReference':'foreign'},{'svgSha256':'changed'},{'fidelityReportPath':'external/report.json'}]:
                with self.assertRaises(ValueError):verify_binding(icon,{**binding,**change},report['fileReference'],metadata['registrySha256'])
            with self.assertRaises(ValueError):verify_binding(icon,binding,'foreign',metadata['registrySha256'])
        changed=deepcopy(report);changed['results'][0]['changedPixelsOutsideVerifiedEdgeBand']=1
        with patch('adapters.penpot.icon_admission.build_gate',return_value=changed):
            with self.assertRaises(ValueError):verify_binding(icon,binding,report['fileReference'],metadata['registrySha256'])
