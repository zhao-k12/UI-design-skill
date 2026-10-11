"""Synthetic Type3 paths verify strict rejection, never platform admission."""
import copy
import hashlib
from decimal import Decimal
from pathlib import Path
import tempfile
import unittest
from adapters.penpot.pdf_glyph_geometry import parse_type3_glyph, compare_glyphs, parse_bfchar_mapping
from tests import test_penpot_font_container as font_fixtures
from fontTools.ttLib import TTFont


class PdfGlyphTests(unittest.TestCase):
    DATA=b'500 0 0 -600 400 0 d1\n0 0 m\n400 0 l\n200 -600 l\nh\nf\n'
    def test_multiple_bfchar_entries_reject_count_duplicate_and_unknown_mapping(self):
        value='2 beginbfchar\n<01> <4E09>\n<02> <5F20>\nendbfchar'
        self.assertEqual(parse_bfchar_mapping(value),[(1,0x4e09),(2,0x5f20)])
        for changed in (value.replace('2 begin','3 begin'),value.replace('<02>','<01>'),value+'\n1 beginbfrange',value.replace('<5F20>','<4E09>')):
            with self.assertRaises(ValueError):parse_bfchar_mapping(changed)

    def test_unknown_paint_and_incomplete_paths_stop(self):
        for data in (self.DATA.replace(b'f\n',b'f*\n'),self.DATA.replace(b'h\n',b''), self.DATA+b'0 0 m\n'):
            with self.assertRaises(ValueError):parse_type3_glyph(data)

    def test_exact_paths_wrong_font_changed_curve_and_advance(self):
        with tempfile.TemporaryDirectory() as folder:
            source,digest=font_fixtures.FontContainerTests().source(folder)
            commands,advance=parse_type3_glyph(self.DATA)
            observation={'character':'A','postscriptName':'TestOnly-Regular','fontWeight':400,
                'nativeCommands':commands,'advanceFontUnits':advance,'pathSha256':'test-only',
                'nativePdfSha256':'a'*64,
                'fontMatrix':['0.0010000001','0','0','-0.0010000001','0','0']}
            result=compare_glyphs(source,digest,[observation],'A')
            self.assertEqual(result['status'],'PASS');self.assertFalse(result['admissionEligible'])
            for field,value in [('postscriptName','WrongFont'),('advanceFontUnits',Decimal(501))]:
                changed=copy.deepcopy(observation);changed[field]=value
                self.assertEqual(compare_glyphs(source,digest,[changed],'A')['status'],'FAIL')
            changed=copy.deepcopy(observation)
            changed['nativeCommands'][1]=('lineTo',((Decimal(401),Decimal(0)),))
            self.assertEqual(compare_glyphs(source,digest,[changed],'A')['status'],'FAIL')
            changed=copy.deepcopy(observation);changed['fontMatrix'][0]='0.002'
            with self.assertRaisesRegex(ValueError,'font_matrix'):
                compare_glyphs(source,digest,[changed],'A')
            with TTFont(source) as font:
                for table in font['cmap'].tables:
                    if table.isUnicode():table.cmap[ord('B')]=table.cmap[ord('A')]
                font.save(source)
            digest=hashlib.sha256(source.read_bytes()).hexdigest()
            alias=copy.deepcopy(observation);alias['character']='B'
            result=compare_glyphs(source,digest,[alias],'A')
            self.assertEqual(result['status'],'PASS')
            self.assertEqual(result['glyphs'][0]['nativeUnicodeCharacter'],'B')
            self.assertTrue(result['glyphs'][0]['sourceCmapGlyphAlias'])
            alias['character']='C'
            with self.assertRaisesRegex(ValueError,'missing_or_ambiguous'):compare_glyphs(source,digest,[alias],'A')
