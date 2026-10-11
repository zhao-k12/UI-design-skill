import hashlib
from pathlib import Path
import unittest
from fontTools.ttLib import TTFont
from adapters.figma.served_font_comparison import compare_served_glyph
from tests import test_font_outline_comparison as fixtures


class ServedFontTests(unittest.TestCase):
    def setUp(self):
        fixtures.FontOutlineComparisonTests.setUp(self)
        with TTFont(self.path) as font:
            for table in font['cmap'].tables:
                if table.isUnicode():table.cmap[0xf116]='fixture'
            font.save(self.path)
        self.digest=hashlib.sha256(self.path.read_bytes()).hexdigest()
        self.woff=Path(self.directory.name)/'fixture.woff2'
        with TTFont(self.path) as font:
            font.flavor='woff2';font.save(self.woff)
        self.woff_hash=hashlib.sha256(self.woff.read_bytes()).hexdigest()
        self.manifest={'servedResources':[{'path':'/vendor/styles/fonts/ionicons.woff2','sha256':self.woff_hash}]}

    def compare(self):
        return compare_served_glyph(self.manifest,self.woff,self.woff_hash,self.path,self.digest)

    def test_real_woff2_roundtrip_preserves_glyph_and_hint_tables(self):
        result=self.compare();self.assertEqual(result['status'],'PASS')
        self.assertFalse(result['admissionEligible'])

    def test_request_evidence_and_file_hash_are_required(self):
        self.manifest['servedResources'][0]['sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'served_resource'):self.compare()
        self.manifest['servedResources'][0]['sha256']=self.woff_hash
        self.path.write_bytes(self.path.read_bytes()+b'changed')
        with self.assertRaisesRegex(ValueError,'hash_mismatch'):self.compare()

    def test_changed_metrics_fail_even_with_valid_new_file_hash(self):
        with TTFont(self.path) as font:
            font['hmtx']['fixture']=(999,50);font.save(self.path)
        self.digest=hashlib.sha256(self.path.read_bytes()).hexdigest()
        self.assertEqual(self.compare()['status'],'FAIL')
