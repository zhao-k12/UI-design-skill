import copy
import importlib
import unittest
from tests import test_component_resolver as fixture_module
from validators.structure.gate import builder

mapping=importlib.import_module('core.component-resolver.primitive_mapping')
assembly=importlib.import_module('core.component-resolver.assembly')


class PrimitiveContentTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixture_module.ResolverTests();self.fixture.setUp();f=self.fixture.fixture
        self.mapping=mapping.resolve(f.analysis,f.page,fixture_module.BASE,f.review,f.plan,
            self.fixture.decisions,self.fixture.registry,f.registry,allow_text_primitives=True,allow_test_fixtures=True)
        self.content=dict(version='0.1.0',mappingSha256=builder.fingerprint(self.mapping),items=[])
        for row in self.mapping['rows']:
            item=dict(sourceId=row['sourceId'],props={},slots={})
            claim=dict(text=row['label'],evidence=row['evidence'])
            if row.get('primitive')=='Text':
                item['props']['text']=claim
                item['textStyle']={'typographyToken':{'token':'typography.body'},'colorToken':{'token':'color.text'}}
            elif row['componentType']=='Button':item['slots']['label']=[{'kind':'text','claim':claim}]
            elif row['componentType'] in ('Input','Select'):item['props']['placeholder']=claim
            else:item['props']['headers']=[{'text':'姓名','evidence':row['evidence']}]
            self.content['items'].append(item)

    def run_assembly(self):
        f=self.fixture.fixture
        return assembly.assemble(f.analysis,f.page,fixture_module.BASE,f.review,f.plan,
            self.fixture.decisions,self.fixture.registry,f.registry,self.content,
            allow_text_primitives=True,allow_test_fixtures=True)

    def test_explicit_source_text_primitive_does_not_create_a_registry_component(self):
        self.assertEqual(self.mapping['status'],'PASS')
        result=self.run_assembly();self.assertEqual(result['status'],'PASS',result['issues'])
        nodes=[o['instance'] for o in result['operations'] if o['sourceId'] in ('example-row','scope-note')]
        self.assertEqual(len(nodes),2)
        self.assertTrue(all(n['type']=='Text' and 'componentId' not in n for n in nodes))
        self.assertFalse(result['readyForAdapter'])
        self.assertNotIn('Text',self.fixture.registry.snapshot['components'])

    def test_unknown_style_and_missing_style_are_rejected(self):
        original=copy.deepcopy(self.content)
        for change in ('missing','unknown'):
            self.content=copy.deepcopy(original)
            item=next(i for i in self.content['items'] if i['sourceId']=='scope-note')
            if change=='missing':item.pop('textStyle')
            else:item['textStyle']['typographyToken']['token']='typography.unknown'
            self.assertEqual(self.run_assembly()['status'],'FAIL')

    def test_low_confidence_and_explicit_widget_requests_do_not_become_primitives(self):
        f=self.fixture.fixture
        for change in ('confidence','preferredId'):
            original=copy.deepcopy(self.fixture.decisions)
            decision=next(d for d in self.fixture.decisions['items'] if d['sourceId']=='scope-note')
            decision[change]='low' if change=='confidence' else 'missing.text-widget'
            result=mapping.resolve(f.analysis,f.page,fixture_module.BASE,f.review,f.plan,
                self.fixture.decisions,self.fixture.registry,f.registry,allow_text_primitives=True,allow_test_fixtures=True)
            row=next(r for r in result['rows'] if r['sourceId']=='scope-note')
            self.assertNotIn('primitive',row)
            self.fixture.decisions=original
