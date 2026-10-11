"""Reject mutations of observed Table geometry and content."""
from copy import deepcopy
import json
import unittest
from validators.ui_ir import ROOT
from adapters.penpot.table_candidate import prepare_table_candidate
from adapters.penpot.table_fidelity import validate_geometry


class TableProofTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        read=lambda p:json.loads((ROOT/p).read_text(encoding='utf-8'))
        cls.native=read('adapters/penpot/metadata/table-native-v1/capture.json')['result']
        cls.plan=prepare_table_candidate(ROOT/'adapters/figma/metadata/table-reference',cls.native['fileReference'],cls.native['pageReference'])
        cls.font=read('adapters/penpot/metadata/font-bindings.json')['PingFang SC:400']

    def test_changed_cell_width_text_clip_and_border_rejected(self):
        validate_geometry(self.native,self.plan,self.font)
        for kind,field,value in [('root','clipContent',False),('cell','width',464),('text','characters','错误'),('text','fontWeight','600'),('text','x',99),('border','height',2)]:
            changed=deepcopy(self.native)
            node=changed['nodes'][0] if kind=='root' else next(n for n in changed['nodes'] if (kind=='text' and n['type']=='text') or (kind=='cell' and n['type']=='board' and n['width']==464.328125) or (kind=='border' and n['type']=='rectangle'))
            node[field]=value
            with self.assertRaises(ValueError):validate_geometry(changed,self.plan,self.font)

    def test_paint_reference_and_wrong_parent_rejected(self):
        changed=deepcopy(self.native);text=next(n for n in changed['nodes'] if n['type']=='text');text['parentReference']='foreign'
        with self.assertRaises(ValueError):validate_geometry(changed,self.plan,self.font)
        changed=deepcopy(self.native);paint=next(n for n in changed['nodes'] if n['fills']);paint['fills'][0]['fillColorGradient']={'type':'linear'}
        with self.assertRaises(ValueError):validate_geometry(changed,self.plan,self.font)
