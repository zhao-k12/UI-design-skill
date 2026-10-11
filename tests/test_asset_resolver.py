import copy
from hashlib import sha256
import importlib
from pathlib import Path
import tempfile
import unittest
import json
import subprocess
import sys
from PIL import Image
from jsonschema.exceptions import ValidationError
from validators.ui_ir import validate_document, load_json, ROOT

registry=importlib.import_module('core.asset-resolver.registry')
resolver=importlib.import_module('core.asset-resolver.resolver')


class AssetTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        Image.new('RGB',(2,3),'white').save(self.root/'fixture.png')
        self.asset={'assetId':'test.logo','kind':'logo','path':'fixture.png','sha256':sha256((self.root/'fixture.png').read_bytes()).hexdigest(),
                    'mediaType':'image/png','width':2,'height':3,'sourceReference':'explicit-test-fixture'}
        self.data={'version':'0.1.0','assets':[self.asset]};self.assets=registry.AssetRegistry(self.data,self.root)
        self.document={'uiIrVersion':'0.1.0','documentId':'asset-test','pages':[{'id':'page','type':'Page','children':[{'id':'logo','type':'Image','assetId':'test.logo','alt':'Test asset'}]}]}

    def test_exact_prototype_asset_has_priority_and_inputs_stay_unchanged(self):
        prototype=copy.deepcopy(self.asset);prototype['sourceReference']='prototype-source'
        original=copy.deepcopy((self.document,self.data,prototype))
        result=resolver.resolve(self.document,self.assets,prototype_assets=[prototype],prototype_root=self.root)
        self.assertEqual(result['status'],'PASS');self.assertEqual(result['resolvedAssets']['logo']['origin'],'prototype')
        self.assertEqual((self.document,self.data,prototype),original)
        result['resolvedAssets']['logo']['descriptor']['width']=9
        self.assertEqual(self.assets.resolve('test.logo')['descriptor']['width'],2)

    def test_registry_fallback_and_all_business_asset_categories(self):
        for kind in registry.KINDS:
            asset=dict(self.asset,kind=kind)
            result=registry.AssetRegistry({'version':'0.1.0','assets':[asset]},self.root).resolve('test.logo')
            self.assertEqual(result['origin'],'registry');self.assertEqual(result['descriptor']['kind'],kind)

    def test_changed_bytes_or_dimensions_and_bad_prototype_do_not_fallback(self):
        for change in ({'sha256':'0'*64},{'width':3},{'path':'../outside.png'},{'mediaType':'image/jpeg'}):
            candidate=dict(self.asset,**change)
            result=resolver.resolve(self.document,self.assets,prototype_assets=[candidate],prototype_root=self.root)
            self.assertEqual(result['status'],'FAIL');self.assertIsNone(result['document']);self.assertFalse(result['readyForAdapter'])
        (self.root/'fixture.png').write_bytes(b'changed')
        with self.assertRaises(registry.AssetError):self.assets.resolve('test.logo')

    def test_missing_resources_are_representable_and_block_native_preflight(self):
        doc=copy.deepcopy(self.document);doc['pages'][0]['children'] += [
            {'id':'button','type':'ComponentInstance','componentId':'unavailable.button'},
            {'id':'icon','type':'IconInstance','iconId':'remix.unavailable'}]
        empty=registry.AssetRegistry({'version':'0.1.0','assets':[]},self.root)
        result=resolver.resolve(doc,empty)
        self.assertEqual(result['status'],'Missing');self.assertFalse(result['readyForAdapter'])
        self.assertEqual({i['code'] for i in result['issues']},{'missing_asset','missing_component','missing_icon'})
        self.assertEqual({i['code'] for i in validate_document(result['document'])},{'missing_asset','missing_component','missing_icon'})
        unsupported=resolver.resolve(doc,empty,unsupported_components=['unavailable.button'])
        self.assertEqual(unsupported['status'],'Unsupported')
        self.assertIn('unsupported_component',{i['code'] for i in validate_document(unsupported['document'])})

    def test_duplicate_asset_unknown_kind_and_invalid_static_image_rejected(self):
        with self.assertRaises(registry.AssetError):registry.AssetRegistry({'version':'0.1.0','assets':[self.asset,self.asset]},self.root)
        malformed=dict(self.asset,kind='generated-business-image')
        with self.assertRaises(ValidationError):registry.AssetRegistry({'version':'0.1.0','assets':[malformed]},self.root)
        (self.root/'fake.png').write_bytes(b'not an image')
        fake=dict(self.asset,path='fake.png',sha256=sha256(b'not an image').hexdigest())
        with self.assertRaises(registry.AssetError):registry.inspect(fake,self.root)

    def test_current_frozen_list_has_no_invented_image_requirements(self):
        components=importlib.import_module('core.component-resolver.registry').ComponentRegistry(load_json(ROOT/'registries/components/catalog.json'),load_json(ROOT/'registries/components/fidelity-reports.json'))
        lock=load_json(ROOT/'registries/icons/current.json')
        icons=importlib.import_module('core.icon-resolver.registry').IconRegistry(load_json(ROOT/'registries/icons/snapshots'/lock['snapshotSha256']/'registry.json'))
        result=resolver.resolve(load_json(ROOT/'examples/adapter-fidelity-acceptance.ui-ir.json'),self.assets,components=components,icons=icons)
        self.assertEqual(result['status'],'PASS');self.assertEqual(result['resolvedAssets'],{})

    def test_cli_replaces_stale_pass_with_current_missing_and_guards_inputs(self):
        doc=self.root/'document.json';catalog=self.root/'catalog.json';output=self.root/'result.json'
        doc.write_text(json.dumps(self.document),encoding='utf-8');catalog.write_text(json.dumps(self.data),encoding='utf-8')
        command=[sys.executable,'-m','core.asset-resolver.resolver',str(doc),'--catalog',str(catalog),'--asset-root',str(self.root),'--output',str(output)]
        passed=subprocess.run(command,cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(passed.returncode,0,passed.stderr)
        catalog.write_text(json.dumps({'version':'0.1.0','assets':[]}),encoding='utf-8')
        blocked=subprocess.run(command,cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(blocked.returncode,1);self.assertEqual(load_json(output)['status'],'Missing')
        original=doc.read_bytes();protected=subprocess.run(command[:-1]+[str(doc)],cwd=ROOT,capture_output=True,text=True)
        self.assertNotEqual(protected.returncode,0);self.assertEqual(doc.read_bytes(),original)
