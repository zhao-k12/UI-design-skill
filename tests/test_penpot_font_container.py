"""Packaging must preserve table content and refuse wrong source/overwrites."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont
from adapters.penpot.font_container import prepare_woff, table_snapshot


class FontContainerTests(unittest.TestCase):
    def source(self, folder):
        builder = FontBuilder(1000, isTTF=True)
        builder.setupGlyphOrder(['.notdef', 'A'])
        builder.setupCharacterMap({65:'A'})
        pen=TTGlyphPen(None)
        pen.moveTo((0,0));pen.lineTo((400,0));pen.lineTo((200,600));pen.closePath()
        glyph=pen.glyph()
        builder.setupGlyf({'.notdef':glyph,'A':glyph})
        builder.setupHorizontalMetrics({'.notdef':(500,0),'A':(500,0)})
        builder.setupHorizontalHeader(ascent=800,descent=-200)
        builder.setupNameTable({'familyName':'TestOnly','styleName':'Regular','uniqueFontIdentifier':'TestOnly',
                               'psName':'TestOnly-Regular'})
        builder.setupOS2(sTypoAscender=800,sTypoDescender=-200,usWinAscent=800,usWinDescent=200)
        builder.setupPost();builder.setupMaxp()
        path=Path(folder)/'source.ttf';builder.save(path)
        return path,hashlib.sha256(path.read_bytes()).hexdigest()

    def test_packaging_preserves_tables_and_rejects_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            source,digest=self.source(folder);target=Path(folder)/'packed.woff'
            result=prepare_woff(source,target,digest)
            self.assertEqual(result['status'],'PASS')
            self.assertFalse(result['nativeRenderingVerified'])
            with self.assertRaisesRegex(ValueError,'font_artifact_exists'):
                prepare_woff(source,target,digest)

    def test_changed_metric_and_wrong_source_hash_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            source,digest=self.source(folder);target=Path(folder)/'packed.woff'
            with self.assertRaisesRegex(ValueError,'source_font_hash_mismatch'):
                prepare_woff(source,target,'0'*64)
            prepare_woff(source,target,digest)
            with TTFont(target,recalcTimestamp=False) as font:
                font['hhea'].ascent+=1
                font.save(Path(folder)/'changed.woff')
            self.assertNotEqual(table_snapshot(source),table_snapshot(Path(folder)/'changed.woff'))
