import copy
import importlib
import unittest

from tests import test_component_resolver as resolver_fixture
from core.prototype.parser import parse
from validators.structure.gate import builder
from validators.ui_ir import load_json

assembly = importlib.import_module('core.component-resolver.assembly')
BASE, ROOT = resolver_fixture.BASE, resolver_fixture.ROOT


class AssemblyTests(unittest.TestCase):
    def setUp(self):
        self.fixture = resolver_fixture.ResolverTests()
        self.fixture.setUp()
        f = self.fixture.fixture
        observations = load_json(BASE / 'observations.json')
        observations['unknowns'] = []
        for section in observations['page']['blocks']:
            section['staticContent'] = []
        f.analysis = parse(observations, BASE)
        f.page = builder.build(f.analysis)
        f.review['analysisSha256'] = builder.fingerprint(f.analysis)
        f.plan['pageTreeSha256'] = builder.fingerprint(f.page)
        f.plan['measurements'] = {k:v for k,v in f.plan['measurements'].items()
                                  if k not in ('example-row', 'scope-note')}
        tree, _ = f.run_plan()
        self.fixture.decisions['layoutTreeSha256'] = builder.fingerprint(tree)
        self.fixture.decisions['items'] = [i for i in self.fixture.decisions['items']
                                           if i['sourceId'] not in ('example-row', 'scope-note')]
        mapping = self.fixture.run_mapping()
        self.content = dict(version='0.1.0', mappingSha256=builder.fingerprint(mapping), items=[])
        for row in mapping['rows']:
            claim = {'text': row['label'], 'evidence': row['evidence']}
            props, slots = {}, {}
            if row['componentType'] == 'Button':
                slots['label'] = [{'kind': 'text', 'claim': claim}]
            elif row['componentType'] in ('Input', 'Select'):
                props['placeholder'] = claim
            else:
                props['headers'] = [{'text': t, 'evidence': row['evidence']} for t in ('姓名', '邮箱', '状态')]
            self.content['items'].append({'sourceId':row['sourceId'], 'props':props, 'slots':slots})

    def run_assembly(self, previous=None, allow=True):
        f = self.fixture.fixture
        return assembly.assemble(f.analysis, f.page, BASE, f.review, f.plan, self.fixture.decisions,
                                  self.fixture.registry, f.registry, self.content,
                                  previous=previous, allow_test_fixtures=allow)

    def test_instance_payloads_preserve_existing_cells_and_boxes(self):
        before = copy.deepcopy(self.content)
        result = self.run_assembly()
        self.assertEqual(result['status'], 'PASS', result['issues'])
        self.assertEqual(len(result['operations']), 7)
        self.assertFalse(result['readyForAdapter'])
        self.assertFalse(result['nativeInstancesCreated'])
        self.assertEqual(self.content, before)
        for op in result['operations']:
            self.assertEqual(op['instance']['id'], op['targetCellId'])
            self.assertEqual(op['instance']['layout']['width']['value'], op['box']['width'])
        self.assertEqual(self.run_assembly(result)['operations'], [])

    def test_content_change_rebuilds_only_affected_section(self):
        previous = self.run_assembly()
        entry = next(i for i in self.content['items'] if i['sourceId']=='add')
        entry['slots']['label'][0]['claim']['text'] = '新增'
        current = self.run_assembly(previous)
        self.assertEqual(current['status'], 'PASS')
        self.assertEqual(current['changedSections'], ['toolbar'])
        self.assertEqual({op['sourceId'] for op in current['operations']}, {'add','export'})
        self.assertEqual(current['sections']['filters'], previous['sections']['filters'])

    def test_mapping_change_rebuilds_only_affected_section(self):
        previous = self.run_assembly()
        decision = next(i for i in self.fixture.decisions['items'] if i['sourceId']=='name')
        decision.update(intent='choice', preferredId='form.select.default.medium')
        self.content['mappingSha256'] = builder.fingerprint(self.fixture.run_mapping())
        current = self.run_assembly(previous)
        self.assertEqual(current['status'], 'PASS', current['issues'])
        self.assertEqual(current['changedSections'], ['filters'])
        self.assertEqual(current['sections']['toolbar'], previous['sections']['toolbar'])

    def test_stale_content_fabricated_text_unknown_slots_and_props_rejected(self):
        original = copy.deepcopy(self.content)
        mutations = [lambda c:c.update(mappingSha256='0'*64),
                     lambda c:c['items'][0]['props']['placeholder'].update(text='不存在的占位文字'),
                     lambda c:c['items'][0]['props'].update(onClick={'text':'姓名','evidence':['e2']}),
                     lambda c:c['items'][0]['slots'].update(label=[{'kind':'text','claim':{'text':'姓名','evidence':['e2']}}]),
                     lambda c:c['items'].pop()]
        for mutate in mutations:
            self.content = copy.deepcopy(original)
            mutate(self.content)
            result = self.run_assembly()
            self.assertEqual(result['status'], 'FAIL')
            self.assertEqual(result['operations'], [])

    def test_modified_checkpoint_and_unapproved_inputs_block(self):
        previous = self.run_assembly()
        previous['sections']['filters'][0]['box']['x'] += 1
        self.assertEqual(self.run_assembly(previous)['status'], 'FAIL')
        self.assertFalse(self.run_assembly(allow=False)['readyForAdapter'])
        self.assertEqual(self.run_assembly(allow=False)['operations'], [])

    def test_six_slot_roles_with_explicitly_synthetic_descriptors(self):
        logical = self.fixture.registry
        data = logical.snapshot
        data.update(scope='test-fixture', sourceVersion='assembly-fixture')
        reports = {}
        for logical_id, entry in data['components'].items():
            if entry['status'] != 'active':
                continue
            report = dict(scope='test-fixture', status='PASS', logicalComponentId=logical_id,
                          componentType=entry['componentType'], variants=entry['variants'],
                          sourceVersion='assembly-fixture', componentIrSha256='1'*64)
            report_id = 'fixture.'+logical_id
            reports[report_id] = report
            entry['fidelity'] = dict(reportId=report_id,
                reportSha256=assembly.resolver.registry_module.digest(report), componentIrSha256='1'*64)
        data['components']['form.input.default.medium']['slots'] = list(assembly.SLOTS)
        self.fixture.registry = assembly.resolver.registry_module.ComponentRegistry(data,reports,allow_test_fixtures=True)
        self.fixture.decisions['registrySha256'] = self.fixture.registry.fingerprint
        self.content['mappingSha256'] = builder.fingerprint(self.fixture.run_mapping())
        target = next(e for e in self.content['items'] if e['sourceId']=='name')
        claim = {'text':'姓名','evidence':['e2']}
        nested = {'componentId':'form.input.default.medium','variant':'default',
                  'props':{'value':claim},'slots':{}}
        action = {'componentId':'action.button.primary.medium','variant':'default',
                  'props':{},'slots':{'label':[{'kind':'text','claim':claim}]}}
        target['slots'] = {
            'leading-icon':[{'kind':'icon','iconId':'remix.settings-3-line'}],
            'trailing-icon':[{'kind':'icon','iconId':'remix.download-line'}],
            'label':[{'kind':'text','claim':claim}], 'content':[{'kind':'text','claim':claim}],
            'control':[{'kind':'instance','instance':nested}],
            'actions':[{'kind':'instance','instance':action}]}
        icons_module = importlib.import_module('core.icon-resolver.registry')
        lock = load_json(ROOT/'registries/icons/current.json')
        icons = icons_module.IconRegistry(load_json(ROOT/'registries/icons/snapshots'/lock['snapshotSha256']/'registry.json'))
        f = self.fixture.fixture
        result = assembly.assemble(f.analysis,f.page,BASE,f.review,f.plan,self.fixture.decisions,
                                  self.fixture.registry,f.registry,self.content,
                                  icon_registry=icons,allow_test_fixtures=True)
        self.assertEqual(result['status'],'PASS',result['issues'])
        node = next(op['instance'] for op in result['operations'] if op['sourceId']=='name')
        self.assertEqual(set(node['slots']),set(assembly.SLOTS))
        self.assertFalse(result['readyForAdapter'])
        missing = self.run_assembly()
        self.assertEqual(missing['status'],'Missing')
        self.assertEqual(missing['issues'][0]['code'],'missing_icon')


if __name__ == '__main__':
    unittest.main()
