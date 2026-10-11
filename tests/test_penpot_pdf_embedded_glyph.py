"""Mutate a saved PDF to ensure unsupported font mappings stop verification."""
from pathlib import Path
import tempfile
import unittest
from validators.ui_ir import ROOT
from adapters.penpot.pdf_embedded_glyph import compare_embedded_glyph
try:
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import NameObject
except ImportError:
    PdfReader=None


@unittest.skipUnless(PdfReader,'Optional diagnostic pypdf runtime is required')
class EmbeddedGlyphTests(unittest.TestCase):
    PDF=ROOT/'adapters/penpot/metadata/select-native-v1/native.pdf'
    SOURCE=ROOT/'node_modules/view-ui-plus/dist/styles/fonts/ionicons.ttf'
    SHA='13d29fa1b804cd295603d17a7c9296c425af2724feaac7ce621f7cad43d8a31d'

    def test_actual_subset_glyph_and_unsupported_mapping(self):
        result=compare_embedded_glyph(self.PDF,self.SOURCE,self.SHA,'\uf116','Ionicons')
        self.assertEqual(result['status'],'PASS');self.assertFalse(result['admissionEligible'])
        for field,value in [('/Encoding','/Identity-V'),('/BaseFont','/WrongFont')]:
            writer=PdfWriter();writer.append(PdfReader(self.PDF))
            font=next(v.get_object() for v in writer.pages[0]['/Resources']['/Font'].values() if v.get_object()['/Subtype']=='/Type0')
            font[NameObject(field)]=NameObject(value)
            with tempfile.TemporaryDirectory() as folder:
                path=Path(folder,'changed.pdf');writer.write(path)
                with self.assertRaises(ValueError):compare_embedded_glyph(path,self.SOURCE,self.SHA,'\uf116','Ionicons')
        with self.assertRaises(ValueError):compare_embedded_glyph(self.PDF,self.SOURCE,'0'*64,'\uf116','Ionicons')
        with self.assertRaises(ValueError):compare_embedded_glyph(self.PDF,self.SOURCE,self.SHA,'\uf117','Ionicons')
