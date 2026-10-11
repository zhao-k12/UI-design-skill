import hashlib
from pathlib import Path
import tempfile
import unittest
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from adapters.figma.font_outline_comparison import measure_glyphs


class FontOutlineComparisonTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.path=Path(self.directory.name)/'fixture.ttf'
        builder=FontBuilder(1000,isTTF=True);builder.setupGlyphOrder(['.notdef','fixture'])
        glyphs={}
        for name in ('.notdef','fixture'):
            pen=TTGlyphPen(None)
            if name=='fixture':
                pen.moveTo((50,0));pen.lineTo((450,0));pen.lineTo((250,700));pen.closePath()
            glyphs[name]=pen.glyph()
        builder.setupCharacterMap({0x4e00:'fixture'});builder.setupGlyf(glyphs)
        builder.setupHorizontalMetrics({name:(1000,50) for name in glyphs});builder.setupHorizontalHeader(ascent=800,descent=-200)
        builder.setupNameTable({'familyName':'Fixture','styleName':'Regular','uniqueFontIdentifier':'Fixture-Regular','fullName':'Fixture Regular','psName':'Fixture-Regular'})
        builder.setupOS2(sTypoAscender=800,sTypoDescender=-200,usWinAscent=800,usWinDescent=200)
        builder.setupPost();builder.setupMaxp();builder.save(self.path)
        self.digest=hashlib.sha256(self.path.read_bytes()).hexdigest()

    def test_measures_real_font_tables_with_explicit_unshaped_advances(self):
        report=measure_glyphs(self.path,self.digest,'一一',14)
        self.assertEqual(report['advancePx'],28)
        self.assertEqual(report['unshapedInkBoundsBaselineCoordinates'],{'x':.7,'y':-9.8,'width':19.6,'height':9.8})
        self.assertEqual(len(report['glyphs']),2)
        self.assertTrue(report['shaping'].startswith('NONE'))

    def test_changed_font_file_or_missing_glyph_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'hash_mismatch'):measure_glyphs(self.path,'0'*64,'一',14)
        with self.assertRaisesRegex(ValueError,'glyph_missing'):measure_glyphs(self.path,self.digest,'二',14)

    def test_complex_script_and_invalid_size_do_not_get_guessed_geometry(self):
        for text,size in [('fi',14),('一',float('nan')),('一',True),('',14)]:
            with self.assertRaises(ValueError):measure_glyphs(self.path,self.digest,text,size)
