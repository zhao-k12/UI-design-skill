import base64
import json
from pathlib import Path
from shutil import copytree
from tempfile import TemporaryDirectory
import unittest
from PIL import Image
from adapters.penpot.headed_table_pdf_proof import evaluate as pdf_proof
from adapters.penpot.headed_table_vector_proof import evaluate as vector_proof
from validators.ui_ir import ROOT
from validators.visual.fidelity import file_hash

EVIDENCE=ROOT/'adapters/penpot/metadata/headed-table-native'
SOURCES=ROOT/'component-builder/runtime-renderer/metadata/headed-table-source'
FONT_DIR=Path('C:/Users/38442/AppData/Local/Microsoft/Windows/Fonts')

class HeadedNativeProofTests(unittest.TestCase):
    def test_actual_pdf_paths_fonts_and_all_baselines(self):
        for number,case,count in ((2,'two-column',6),(3,'four-column',20)):
            with TemporaryDirectory() as temporary:
                result=pdf_proof(EVIDENCE/'header-union'/f'discovery-{number}.json',SOURCES/(case+'-typography'),FONT_DIR,Path('C:/Windows/Fonts/arial.ttf'),Path(temporary)/'proof')
                self.assertEqual(result['status'],'PASS')
                self.assertEqual(len(result['baselines']),count)
                self.assertFalse(result['productionAdmission'])

    def test_actual_independent_vectors_and_exact_nonhorizontal_pixels(self):
        for number,case in ((2,'two-column'),(3,'four-column')):
            result=vector_proof(EVIDENCE/'header-union'/f'discovery-{number}.json',SOURCES/(case+'-typography'),EVIDENCE/(case+'-svg-proof'))
            self.assertEqual(result['status'],'PASS')
            self.assertEqual(result['outsideExactHorizontalRegions'],0)
            self.assertFalse(result['productionAdmission'])

    def test_wrong_pdf_header_weight_is_rejected(self):
        with TemporaryDirectory() as temporary:
            temporary=Path(temporary)
            receipt=json.loads((EVIDENCE/'header-union/discovery-2.json').read_text(encoding='utf8'))
            data=base64.b64decode(receipt['result']['nativePdf']['base64'])
            self.assertIn(b'/FontWeight 600',data)
            receipt['result']['nativePdf']['base64']=base64.b64encode(data.replace(b'/FontWeight 600',b'/FontWeight 400')).decode()
            path=temporary/'receipt.json';path.write_text(json.dumps(receipt),encoding='utf8')
            with self.assertRaisesRegex(ValueError,'pdf_source_weight_mismatch'):
                pdf_proof(path,SOURCES/'two-column-typography',FONT_DIR,Path('C:/Windows/Fonts/arial.ttf'),temporary/'proof')

    def test_changed_vector_line_length_cannot_hide_behind_same_png(self):
        from hashlib import sha256
        with TemporaryDirectory() as temporary:
            temporary=Path(temporary);probe_dir=temporary/'probe'
            copytree(EVIDENCE/'two-column-svg-proof',probe_dir)
            receipt=json.loads((EVIDENCE/'header-union/discovery-2.json').read_text(encoding='utf8'))
            svg=base64.b64decode(receipt['result']['nativeSvgBase64'])
            self.assertIn(b'width="721"',svg)
            svg=svg.replace(b'width="721"',b'width="720"')
            receipt['result']['nativeSvgBase64']=base64.b64encode(svg).decode()
            path=temporary/'receipt.json';path.write_text(json.dumps(receipt),encoding='utf8')
            probe=json.loads((probe_dir/'svg-probe.json').read_text(encoding='utf8'))
            probe['nativeReceiptSha256']=file_hash(path);probe['sample']['svgSha256']=sha256(svg).hexdigest()
            (probe_dir/'svg-probe.json').write_text(json.dumps(probe),encoding='utf8')
            with self.assertRaisesRegex(ValueError,'headed_vector_rectangle_mismatch'):
                vector_proof(path,SOURCES/'two-column-typography',probe_dir)

    def test_difference_outside_line_regions_is_rejected(self):
        with TemporaryDirectory() as temporary:
            probe_dir=Path(temporary)/'probe';copytree(EVIDENCE/'two-column-svg-proof',probe_dir)
            png=probe_dir/'native-svg.png'
            with Image.open(png) as image:
                image=image.convert('RGBA');image.putpixel((0,0),(255,0,0,255));image.save(png)
            path=probe_dir/'svg-probe.json';probe=json.loads(path.read_text(encoding='utf8'))
            probe['sample']['pngSha256']=file_hash(png);path.write_text(json.dumps(probe),encoding='utf8')
            with self.assertRaisesRegex(ValueError,'headed_vector_difference_outside_horizontal_regions'):
                vector_proof(EVIDENCE/'header-union/discovery-2.json',SOURCES/'two-column-typography',probe_dir)
