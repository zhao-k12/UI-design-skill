import base64
from io import BytesIO
import json
import unittest
from PIL import Image
from adapters.headed_table_pixel_regions import compare_regions,intersects,source_regions
from validators.ui_ir import ROOT

class HeadedPixelRegionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.samples=[]
        for number,case in ((2,'two-column'),(3,'four-column')):
            source=ROOT/'component-builder/runtime-renderer/metadata/headed-table-source'/(case+'-typography')
            figma=(ROOT/'adapters/figma/metadata/headed-table-native'/(case+'-native.png')).read_bytes()
            penpot=json.loads((ROOT/'adapters/penpot/metadata/headed-table-native/header-union'/f'discovery-{number}.json').read_text(encoding='utf8'))['result']
            cls.samples.extend([(source,'figma',figma),(source,'penpot',base64.b64decode(penpot['nativePngBase64']))])

    def test_four_actual_exports_have_zero_outside_differences(self):
        for source,platform,raw in self.samples:
            result=compare_regions(source,platform,raw)
            self.assertEqual(result['categories']['outside'],0)
            self.assertEqual(result['categories']['horizontal'],4320 if 'two-column' in str(source) else 9600)
            self.assertFalse(result['productionAdmission'])

    def test_fractional_lines_have_only_two_intersecting_rows(self):
        for source,_,_ in self.samples:
            plan,texts,lines=source_regions(source)
            first=lines[0]['region']
            self.assertEqual(first['y'],37.875)
            self.assertEqual([y for y in range(40) if intersects(first,0,y)],[37,38])
            self.assertFalse(intersects(first,0,36))
            self.assertFalse(intersects(first,0,39))

    def test_one_outside_pixel_rejects_both_platforms(self):
        for source,platform,raw in self.samples:
            image=Image.open(BytesIO(raw)).convert('RGBA');image.putpixel((0,0),(255,0,0,255))
            output=BytesIO();image.save(output,format='PNG')
            with self.assertRaisesRegex(ValueError,'headed_difference_outside_source_regions'):
                compare_regions(source,platform,output.getvalue())

    def test_touching_boundary_does_not_count_as_positive_area(self):
        region={'x':1,'y':1,'width':1,'height':1}
        self.assertFalse(intersects(region,0,1))
        self.assertFalse(intersects(region,1,0))
        self.assertFalse(intersects(region,2,1))
        self.assertTrue(intersects(region,1,1))
