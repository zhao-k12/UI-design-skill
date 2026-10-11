"""Mutations of saved measurements test rejection; no native execution occurs."""
from copy import deepcopy
from importlib import import_module
from pathlib import Path
import json
import unittest
from adapters.penpot.button_fidelity import validate_geometry
from adapters.penpot.admission import validate_receipt
from validators.ui_ir import ROOT


class ButtonProofTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        read=lambda p:json.loads((ROOT/p).read_text(encoding='utf-8'))
        cls.native=read('adapters/penpot/metadata/button-admitted/capture.json')['result']
        cls.reference=read('adapters/figma/metadata/official-fixture-reference/component_ir.json')['components'][0]
        cls.font=read('adapters/penpot/metadata/font-bindings.json')['PingFang SC:400']
        cls.receipt=next(iter(read('adapters/penpot/metadata/native-fidelity.json').values()))
        cls.registry=import_module('core.component-resolver.registry').ComponentRegistry(
            read('registries/components/catalog.json'),read('registries/components/fidelity-reports.json'))
        cls.descriptor=cls.registry.resolve('action.button.primary.medium','default')['descriptor']
        cls.expected={k:cls.receipt[k] for k in ('platform','status','fileReference','componentReference','logicalId','variant','sourceIrSha256','registryReportSha256')}

    def test_geometry_rejects_changed_font_position_corner_and_effect(self):
        for index,field,value in [(2,'fontWeight','600'),(2,'x',97),(1,'borderRadius',4),(0,'opacity',.5),(0,'shadows',[{'color':'red'}])]:
            changed=deepcopy(self.native);changed['nodes'][index][field]=value
            with self.assertRaises(ValueError):validate_geometry(changed,self.reference,self.font)

    def test_native_transparency_and_gradient_cannot_be_union_normalized(self):
        for field,value in [('fillOpacity',.5),('fillColorGradient',{'type':'linear'})]:
            changed=deepcopy(self.native);changed['nodes'][1]['fills'][0][field]=value
            with self.assertRaises(ValueError):validate_geometry(changed,self.reference,self.font)

    def test_admission_rejects_corrupted_native_png_and_missing_full_bundle(self):
        for field,value in [('nativePngSha256','0'*64),('comparisonPngSha256','0'*64),('proofBundle',{})]:
            changed=deepcopy(self.receipt);changed[field]=value
            with self.assertRaises(ValueError):validate_receipt(changed,self.expected,self.registry,self.descriptor)
