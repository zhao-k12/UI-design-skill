"""Reject mutations of actual Input measurements; no native execution claim."""
from copy import deepcopy
import json
from importlib import import_module
import unittest
from validators.ui_ir import ROOT
from adapters.penpot.input_fidelity import validate_geometry
from adapters.penpot.admission import validate_receipt


class InputProofTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        read=lambda p:json.loads((ROOT/p).read_text(encoding='utf-8'))
        cls.native=read('adapters/penpot/metadata/input-native-v1/capture.json')['result']
        cls.reference=next(c for c in read('adapters/figma/metadata/official-fixture-reference/component_ir.json')['components'] if c['logicalComponentId']=='form.input.default.medium')
        cls.font=read('adapters/penpot/metadata/font-bindings.json')['PingFang SC:400']
        cls.packet=read('adapters/penpot/metadata/native-fidelity.json')[cls.native['componentReference']]
        cls.registry=import_module('core.component-resolver.registry').ComponentRegistry(read('registries/components/catalog.json'),read('registries/components/fidelity-reports.json'))
        cls.descriptor=cls.registry.resolve(cls.native['logicalId'],'default')['descriptor']
        cls.expected={k:cls.packet[k] for k in ('platform','status','fileReference','componentReference','logicalId','variant','sourceIrSha256','registryReportSha256')}

    def test_wrong_placeholder_font_position_paint_and_layer_order_rejected(self):
        for index,field,value in [(2,'characters','请输入地址'),(2,'fontWeight','600'),(2,'y',169),(1,'borderRadius',4),(0,'opacity',.5)]:
            changed=deepcopy(self.native);changed['nodes'][index][field]=value
            with self.assertRaises(ValueError):validate_geometry(changed,self.reference,self.font)
        changed=deepcopy(self.native);changed['nodes'][1],changed['nodes'][2]=changed['nodes'][2],changed['nodes'][1]
        with self.assertRaises(ValueError):validate_geometry(changed,self.reference,self.font)
        changed=deepcopy(self.native);changed['nodes'][2]['fills'][0]['fillColorGradient']={'type':'linear'}
        with self.assertRaises(ValueError):validate_geometry(changed,self.reference,self.font)

    def test_full_penpot_receipt_required(self):
        validate_receipt(self.packet,self.expected,self.registry,self.descriptor)
        for field,value in [('proofBundle',{}),('nativePngSha256','0'*64),('comparisonPngSha256','0'*64)]:
            changed=deepcopy(self.packet);changed[field]=value
            with self.assertRaises(ValueError):validate_receipt(changed,self.expected,self.registry,self.descriptor)
