"""Mutation checks on saved Select measurements; no native execution."""
from copy import deepcopy
import json
import unittest
from importlib import import_module
from validators.ui_ir import ROOT
from adapters.penpot.select_fidelity import validate_geometry
from adapters.penpot.admission import validate_receipt


class SelectProofTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        read=lambda p:json.loads((ROOT/p).read_text(encoding='utf-8'))
        cls.native=read('adapters/penpot/metadata/select-native-v1/capture.json')['result']
        cls.reference=next(c for c in read('adapters/figma/metadata/official-fixture-reference/component_ir.json')['components'] if c['logicalComponentId']=='form.select.default.medium')
        fonts=read('adapters/penpot/metadata/font-bindings.json');cls.font=fonts['PingFang SC:400'];cls.arrow=fonts['Ionicons:400']

    def test_wrong_arrow_content_font_position_or_parent_rejected(self):
        validate_geometry(self.native,self.reference,self.font,self.arrow)
        for index,field,value in [(2,'characters','v'),(2,'fontFamily','PingFang SC'),(2,'x',298),(2,'parentReference','foreign'),(3,'characters','停用'),(3,'y',249),(0,'clipContent',True)]:
            changed=deepcopy(self.native);changed['nodes'][index][field]=value
            with self.assertRaises(ValueError):validate_geometry(changed,self.reference,self.font,self.arrow)

    def test_hidden_transparent_or_gradient_arrow_rejected(self):
        for field,value in [('hidden',True),('opacity',.5),('lineHeight','1.5')]:
            changed=deepcopy(self.native);changed['nodes'][2][field]=value
            with self.assertRaises(ValueError):validate_geometry(changed,self.reference,self.font,self.arrow)
        changed=deepcopy(self.native);changed['nodes'][2]['fills'][0]['fillColorGradient']={'type':'linear'}
        with self.assertRaises(ValueError):validate_geometry(changed,self.reference,self.font,self.arrow)

    def test_receipt_rejects_missing_bundle_and_changed_png(self):
        read=lambda p:json.loads((ROOT/p).read_text(encoding='utf-8'))
        packet=read('adapters/penpot/metadata/native-fidelity.json')[self.native['componentReference']]
        expected={k:packet[k] for k in ('platform','status','fileReference','componentReference','logicalId','variant','sourceIrSha256','registryReportSha256')}
        registry=import_module('core.component-resolver.registry').ComponentRegistry(read('registries/components/catalog.json'),read('registries/components/fidelity-reports.json'))
        descriptor=registry.resolve(self.native['logicalId'],'default')['descriptor']
        validate_receipt(packet,expected,registry,descriptor)
        for field,value in [('proofBundle',{}),('nativePngSha256','0'*64)]:
            changed=deepcopy(packet);changed[field]=value
            with self.assertRaises(ValueError):validate_receipt(changed,expected,registry,descriptor)
