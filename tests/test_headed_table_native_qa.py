import copy
import json
import unittest
from adapters.figma.headed_table_qa import geometry
from adapters.headed_table import prepare_penpot
from adapters.penpot.headed_table_qa import validate_geometry
from validators.ui_ir import ROOT,load_json

class HeadedNativeGeometryTests(unittest.TestCase):
    def figma_inputs(self):
        directory=ROOT/'adapters/figma/metadata/headed-table-native'
        outlines=load_json(directory/'text-outlines.json')
        return (load_json(directory/'two-column-readback.json')['nativeEvidence'],load_json(directory/'candidate-specs.json')[0],{o['textReference']:o for o in outlines['observations']},load_json(directory/'glyph-diagnostic.json'))

    def test_actual_figma_geometry_and_semibold_are_source_bound(self):
        self.assertEqual(geometry(*self.figma_inputs())['status'],'PASS')

    def test_wrong_figma_header_font_weight_is_rejected(self):
        native,plan,outlines,glyphs=self.figma_inputs()
        header=next(n for n in native['nodes'] if n['type']=='TEXT')
        header['properties']['fontWeight']=400
        with self.assertRaisesRegex(ValueError,'native_text_style'):
            geometry(native,plan,outlines,glyphs)

    def test_shifted_figma_row_is_rejected(self):
        native,plan,outlines,glyphs=self.figma_inputs()
        next(n for n in native['nodes'] if n['type']=='FRAME')['absoluteBounds']['y']+=1
        with self.assertRaisesRegex(ValueError,'native_source_geometry'):
            geometry(native,plan,outlines,glyphs)

    def test_penpot_geometry_rejects_shift_and_keeps_unadmitted_state(self):
        directory=ROOT/'adapters/penpot/metadata/headed-table-native'
        native=load_json(directory/'font-recovery-discovery-6.json')['result']
        case='two-column-typography' if '.613ac' in native['logicalId'] else 'four-column-typography'
        plan=prepare_penpot(ROOT/'component-builder/runtime-renderer/metadata/headed-table-source'/case,native['fileReference'],native['pageReference'])
        bindings={'Arial/400':{'fontId':'custom-b65bc280-c7a5-8006-8008-c4950e2dd987','fontVariantId':'normal-400'},'PingFang SC/400':{'fontId':'custom-5ad61700-1d7d-8066-8008-c08a8bdbd70d','fontVariantId':'normal-400'},'PingFang SC/600':{'fontId':'custom-5ad61700-1d7d-8066-8008-c08a8bdbd70d','fontVariantId':'normal-600'}}
        report=validate_geometry(native,plan,bindings)
        self.assertEqual(report['status'],'PASS');self.assertFalse(report['productionAdmission'])
        next(n for n in native['nodes'] if n['type']=='text')['x']+=1
        with self.assertRaisesRegex(ValueError,'table_geometry_mismatch'):
            validate_geometry(native,plan,bindings)
