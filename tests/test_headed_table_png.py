import base64
from io import BytesIO
import json
import unittest
from PIL import Image
from adapters.headed_table import prepare_source
from adapters.headed_table_png import verify_raw_png
from validators.ui_ir import ROOT

class HeadedTablePngTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.samples=[]
        for number,case in ((2,'two-column'),(3,'four-column')):
            plan=prepare_source(ROOT/'component-builder/runtime-renderer/metadata/headed-table-source'/(case+'-typography'))
            figma=(ROOT/'adapters/figma/metadata/headed-table-native'/(case+'-native.png')).read_bytes()
            penpot=json.loads((ROOT/'adapters/penpot/metadata/headed-table-native/header-union'/f'discovery-{number}.json').read_text(encoding='utf8'))['result']
            cls.samples.extend([(plan,'figma',figma),(plan,'penpot',base64.b64decode(penpot['nativePngBase64']))])

    def test_four_actual_raw_exports(self):
        for plan,platform,raw in self.samples:
            report=verify_raw_png(plan,platform,raw)
            self.assertEqual(report['status'],'PASS')
            self.assertFalse(report['productionAdmission'])

    def test_one_wrong_alpha_pixel_rejects_every_platform(self):
        for plan,platform,raw in self.samples:
            for y in (0,Image.open(BytesIO(raw)).height-1):
                image=Image.open(BytesIO(raw)).convert('RGBA')
                pixel=image.getpixel((0,y));image.putpixel((0,y),(*pixel[:3],222))
                output=BytesIO();image.save(output,format='PNG')
                with self.assertRaisesRegex(ValueError,'headed_png_alpha_mismatch'):
                    verify_raw_png(plan,platform,output.getvalue())

    def test_cropped_export_rejected(self):
        for plan,platform,raw in self.samples:
            image=Image.open(BytesIO(raw));output=BytesIO()
            image.crop((0,0,image.width-1,image.height)).save(output,format='PNG')
            with self.assertRaisesRegex(ValueError,'headed_png_dimensions_mismatch'):
                verify_raw_png(plan,platform,output.getvalue())

    def test_other_source_identity_cannot_reuse_alpha_rule(self):
        from copy import deepcopy
        plan,platform,raw=self.samples[0];plan=deepcopy(plan);plan['logicalId']+='0'
        with self.assertRaisesRegex(ValueError,'headed_approval_scope_mismatch'):
            verify_raw_png(plan,platform,raw)
