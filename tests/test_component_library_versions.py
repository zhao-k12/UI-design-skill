from copy import deepcopy
from importlib import import_module
import unittest
from adapters.component_library_versions import load
from adapters.penpot.configurable_table_admission import validate_receipt
from validators.ui_ir import ROOT,load_json
from validators.visual.fidelity import digest


class ComponentLibraryVersions(unittest.TestCase):
    def setUp(self):
        self.registry,self.bindings=load('0.2.1')
        self.reports=load_json(ROOT/'releases/component-library-0.2.1/fidelity-reports.json')
        self.logical=next(k for k in self.registry.snapshot['components'] if k.startswith('data.table.config.'))

    def test_explicit_dual_platform_bindings_and_native_receipts(self):
        self.assertEqual(self.registry.library_version,'0.2.1')
        records=load_json(ROOT/'adapters/penpot/metadata/component-library-0.2.1/native-fidelity.json')
        for logical,descriptor in self.registry.snapshot['components'].items():
            if not logical.startswith('data.table.config.'):continue
            for platform in ('figma','penpot'):
                reference=self.bindings[platform].resolve(logical)
                self.assertEqual(reference['fidelityReportSha256'],descriptor['fidelity']['reportSha256'])
            proof=records[self.bindings['penpot'].resolve(logical)['componentReference']]
            expected={k:proof[k] for k in ('platform','status','fileReference','componentReference','logicalId','variant','sourceIrSha256','registryReportSha256')}
            validate_receipt(proof,expected,self.registry,descriptor)
        old=import_module('core.component-resolver.registry').ComponentRegistry(load_json(ROOT/'registries/components/catalog.json'),load_json(ROOT/'registries/components/fidelity-reports.json'))
        self.assertEqual(old.library_version,'0.1.0-dev')
        with self.assertRaises(ValueError):old.resolve(self.logical)
        with self.assertRaises(ValueError):load('latest')

    def test_missing_policy_and_outside_pixels_cannot_be_admitted(self):
        catalog=self.registry.snapshot;report_id=catalog['components'][self.logical]['fidelity']['reportId']
        for mutation in ('policy','pixels','glyph','type'):
            reports=deepcopy(self.reports);changed=reports[report_id]
            if mutation=='policy':changed['pixelRegionPolicy']='wrong'
            elif mutation=='pixels':changed['checks']['screenshot']['changedPixelsOutsideEdgeBand']=1
            elif mutation=='glyph':changed['checks']['glyphRetention'][0]['status']='FAIL'
            else:changed['componentType']='Button'
            data=deepcopy(catalog)
            if mutation=='type':data['components'][self.logical]['componentType']='Button'
            data['components'][self.logical]['fidelity']['reportSha256']=digest(changed)
            with self.assertRaises(ValueError):type(self.registry)(data,reports)

    def test_policy_cannot_expand_to_other_table_request(self):
        data=self.registry.snapshot;reports=deepcopy(self.reports);old=self.logical;new='data.table.config.unapproved'
        entry=data['components'].pop(old);data['components'][new]=entry;report=reports[entry['fidelity']['reportId']];report['logicalComponentId']=new
        entry['fidelity']['reportSha256']=digest(report)
        with self.assertRaises(ValueError):type(self.registry)(data,reports)

    def test_explicit_release_can_preflight_immutable_instances(self):
        from adapters.figma.compiler import prepare as figma_prepare
        from adapters.penpot.configurable_table_compiler import prepare as penpot_prepare
        tokens=import_module('core.design-rules.tokens').TokenRegistry(load_json(ROOT/'registries/tokens/default.json'))
        icons=import_module('core.icon-resolver.registry').IconRegistry(import_module('icon-manager.remix-sync.manager').current())
        native=load_json(ROOT/'adapters/penpot/metadata/component-library-0.2.1/native-fidelity.json')
        for case in ('two-column','four-column'):
            source=load_json(ROOT/f'component-builder/runtime-renderer/metadata/configurable-table-source/{case}/component_ir.json')['components'][0]
            logical=source['logicalComponentId'];size=source['rootBounds']
            document={'uiIrVersion':'0.1.0','documentId':'synthetic-release-preflight','pages':[{'id':'page','type':'Page','layout':{'width':{'mode':'fixed','value':1440}},'children':[{'id':'body','type':'ComponentInstance','componentId':logical,'layout':{key:{'mode':'fixed','value':size[key]} for key in ('width','height')}}]}]}
            original=deepcopy(document)
            f=figma_prepare(document,tokens,self.registry,self.bindings['figma'],icons,file_reference='0vGWSRoLxBiVPXiZ8xJAX9')
            p=penpot_prepare(document,tokens,self.registry,self.bindings['penpot'],icons,file_reference='91396aad-60c8-808b-8008-c0885ca79899',native_fidelity=native)
            self.assertEqual(f['status'],'PASS',f['issues']);self.assertEqual(p['status'],'PASS',p['issues'])
            self.assertEqual(f['nativeExecution'],p['nativeExecution']);self.assertEqual(f['nativeExecution'],'NOT_RUN')
            self.assertEqual(document,original)
