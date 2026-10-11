import unittest
from adapters.penpot.icon_precision import compare_path_encoding,validate_approved_icon_encoding
from pathlib import Path
import json


class IconPrecisionTests(unittest.TestCase):
    def test_approved_actual_paths_pass_only_geometry_subcheck(self):
        base=Path(__file__).resolve().parents[1]
        plan=json.loads((base/'adapters/penpot/metadata/icon-source-plan/plan.json').read_text(encoding='utf-8'))
        receipt=json.loads((base/'adapters/penpot/metadata/icons-native-v1/restored-capture.json').read_text(encoding='utf-8'))['result']
        for icon in plan['icons']:
            native=next(i for i in receipt['icons'] if i['iconId']==icon['iconId'])
            path=next(n['d'] for n in native['nodes'] if n['type']=='path')
            result=validate_approved_icon_encoding(icon['iconId'],icon['svg'].encode(),path)
            self.assertEqual(result['status'],'PASS');self.assertFalse(result['admissionEligible'])
            self.assertFalse(result['sourceCoordinatesExact'])
            for wrong_id,wrong_source,wrong_path in [('unapproved',icon['svg'].encode(),path),(icon['iconId'],icon['svg'].encode()+b' ',path),(icon['iconId'],icon['svg'].encode(),path+'M0 0L1 1Z')]:
                with self.assertRaises(ValueError):validate_approved_icon_encoding(wrong_id,wrong_source,wrong_path)
    def test_exact_float32_encoding_is_distinguished_from_source_equality(self):
        result=compare_path_encoding('M0.1 0L1 0L0.1 1Z','M0.10000000149011612 0L1 0L0.10000000149011612 1Z')
        self.assertFalse(result['sourceCoordinatesExact']);self.assertTrue(result['sourceFloat32EncodingExact'])
        self.assertFalse(result['admissionEligible'])
        wrong=compare_path_encoding('M0.1 0L1 0L0.1 1Z','M0.10001 0L1 0L0.10001 1Z')
        self.assertFalse(wrong['sourceFloat32EncodingExact'])

    def test_contour_order_or_missing_contour_cannot_be_precision_normalized(self):
        for changed in ('M0 0L0 1L1 0Z','M0 0L1 0Z'):
            self.assertFalse(compare_path_encoding('M0 0L1 0L0 1Z',changed)['sourceFloat32EncodingExact'])
