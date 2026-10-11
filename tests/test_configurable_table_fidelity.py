"""Actual mixed-font fidelity and malicious/corrupt PDF rejection checks."""
from io import BytesIO
from pathlib import Path
import tempfile
import unittest
from fontTools.ttLib import TTFont
from pypdf import PdfReader,PdfWriter
from pypdf.generic import DecodedStreamObject,NameObject
from adapters.penpot.pdf_truetype_geometry import compare_embedded_truetype,unicode_mapping
from adapters.penpot.configurable_table_fidelity import evaluate,FONT_HASHES
from validators.ui_ir import ROOT,load_json

NATIVE=ROOT/'adapters/penpot/metadata/configurable-table-native'
SOURCES=ROOT/'component-builder/runtime-renderer/metadata/configurable-table-source'
FONT_PATHS={'Arial':Path('C:/Windows/Fonts/arial.ttf'),'PingFang SC':Path('C:/Users/38442/AppData/Local/Microsoft/Windows/Fonts/PingFang SC-Regular.otf')}


class ConfigurableTableFidelityTests(unittest.TestCase):
    def test_actual_two_and_four_column_native_gates_pass_with_exact_pdf_glyphs(self):
        fonts=load_json(NATIVE/'font-discovery.json')['result']['fonts']
        bindings={f['family']:{'fontId':f['fontId'],'fontVariantId':'normal-400'} for f in fonts if f['family'] in FONT_PATHS}
        with tempfile.TemporaryDirectory(dir=ROOT/'artifacts') as tmp:
            for case in ('two-column','four-column'):
                # The saved probe hashes its program and actual readback.
                report,proof,candidate=evaluate(NATIVE/(case+'-capture-after-background.json'),NATIVE/case/'after-background',SOURCES/case,FONT_PATHS,bindings,Path(tmp)/case)
                self.assertEqual(report['status'],'PASS');self.assertEqual(report['gateVersion'],'0.2.1')
                self.assertEqual(report['checks']['screenshot']['changedPixelsOutsideEdgeBand'],0)
                self.assertEqual(proof['glyphGeometry']['Arial']['status'],'PASS')
                self.assertEqual(proof['glyphGeometry']['PingFang SC']['status'],'PASS')

    def test_changed_embedded_coordinates_advance_or_hint_program_cannot_pass(self):
        source=NATIVE/'four-column/native-after-background.pdf'
        # This real subset contains only the five digits 0,1,2,3,4.
        self.assertEqual(compare_embedded_truetype(source,FONT_PATHS['Arial'],FONT_HASHES['Arial'],'01234')['status'],'PASS')
        with tempfile.TemporaryDirectory() as tmp:
            for mutation in ('coordinate','advance','hint'):
                reader=PdfReader(source);writer=PdfWriter();writer.add_page(reader.pages[0])
                font=next(ref.get_object() for ref in writer.pages[0]['/Resources']['/Font'].values() if ref.get_object()['/Subtype']=='/Type0')
                descriptor=font['/DescendantFonts'][0]['/FontDescriptor'].get_object()
                tt=TTFont(BytesIO(descriptor['/FontFile2'].get_data()))
                gid=next(cid for cid,char in unicode_mapping(font['/ToUnicode'].get_data().decode('ascii')).items() if char=='0');name=tt.getGlyphOrder()[gid]
                if mutation=='coordinate':
                    glyph=tt['glyf'][name];glyph.coordinates[0]=(glyph.coordinates[0][0]+1,glyph.coordinates[0][1])
                elif mutation=='advance':
                    advance,bearing=tt['hmtx'][name];tt['hmtx'][name]=(advance+1,bearing)
                else:tt['fpgm'].program.fromBytecode(tt['fpgm'].program.getBytecode()+b'\x00')
                data=BytesIO();tt.save(data);stream=DecodedStreamObject();stream.set_data(data.getvalue());descriptor[NameObject('/FontFile2')]=writer._add_object(stream)
                changed=Path(tmp)/(mutation+'.pdf');writer.write(changed)
                if mutation=='hint':
                    with self.assertRaisesRegex(ValueError,'hint_tables_mismatch'):compare_embedded_truetype(changed,FONT_PATHS['Arial'],FONT_HASHES['Arial'],'01234')
                else:self.assertEqual(compare_embedded_truetype(changed,FONT_PATHS['Arial'],FONT_HASHES['Arial'],'01234')['status'],'FAIL')

    def test_unicode_alias_or_unexpected_inventory_cannot_substitute_ascii(self):
        source=NATIVE/'four-column/native-after-background.pdf'
        with self.assertRaisesRegex(ValueError,'cid_text_inventory_mismatch'):compare_embedded_truetype(source,FONT_PATHS['Arial'],FONT_HASHES['Arial'],'01235')
        with self.assertRaisesRegex(ValueError,'source_font_hash_mismatch'):compare_embedded_truetype(source,FONT_PATHS['Arial'],'0'*64,'01234')
        with self.assertRaisesRegex(ValueError,'unsupported_cid_bfrange'):unicode_mapping('1 beginbfrange <0001> <0002> [<0030> <0031>] endbfrange')


if __name__=='__main__':unittest.main()
