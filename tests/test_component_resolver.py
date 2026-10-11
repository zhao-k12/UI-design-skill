import copy
import importlib
from pathlib import Path
import unittest

from tests import test_layout_builder as layout_fixture
from validators.ui_ir import load_json
from validators.structure.gate import builder

resolver = importlib.import_module('core.component-resolver.resolver')
BASE, ROOT = layout_fixture.BASE, layout_fixture.ROOT


class ResolverTests(unittest.TestCase):
    def setUp(self):
        self.fixture = layout_fixture.LayoutBuilderTests()
        self.fixture.setUp()
        self.registry = resolver.registry_module.ComponentRegistry(
            load_json(ROOT / 'registries/components/catalog.json'),
            load_json(ROOT / 'registries/components/fidelity-reports.json'))
        tree, _ = self.fixture.run_plan()
        self.decisions = dict(version='0.1.0', layoutTreeSha256=builder.fingerprint(tree),
                              registrySha256=self.registry.fingerprint, items=[])
        for section in self.fixture.page['page']['children']:
            for item in section['children']:
                intent = {'fields':'text','buttons':'action','dataRegions':'records','staticContent':'static'}[item['kind']]
                if item['id'] == 'status':
                    intent = 'choice'
                self.decisions['items'].append(dict(sourceId=item['id'], intent=intent, confidence='high',
                    rationale='Explicit contract fixture judgment', evidence=item['description']['evidence'],
                    preferredId=None, variant=None))

    def run_mapping(self, allow=True):
        f = self.fixture
        return resolver.resolve(f.analysis, f.page, BASE, f.review, f.plan, self.decisions,
                                self.registry, f.registry, allow_test_fixtures=allow)

    def test_registered_types_and_missing_static_content(self):
        result = self.run_mapping()
        rows = {r['sourceId']:r for r in result['rows']}
        self.assertEqual(rows['name']['componentType'], 'Input')
        self.assertEqual(rows['status']['componentType'], 'Select')
        self.assertEqual(rows['users']['componentType'], 'Table')
        self.assertEqual(rows['add']['componentType'], 'Button')
        self.assertEqual(rows['example-row']['status'], 'Missing')
        self.assertIsNone(rows['example-row']['componentId'])
        self.assertEqual(result['status'], 'Missing')
        self.assertFalse(result['readyForAssembly'])
        self.assertTrue(result['diagnosticOnly'])
        self.assertEqual(len(result['rows']), 9)

    def test_low_confidence_and_same_capability_medium_fallback(self):
        self.decisions['items'][0].update(confidence='low')
        self.decisions['items'][1].update(confidence='medium', preferredId='missing.custom.select')
        rows = {r['sourceId']:r for r in self.run_mapping()['rows']}
        self.assertEqual(rows['name']['status'], 'Review')
        self.assertIsNone(rows['name']['componentId'])
        self.assertEqual(rows['status']['componentType'], 'Select')
        self.assertTrue(rows['status']['fallbackUsed'])

    def test_unavailable_complex_types_never_lossy_fallback(self):
        for intent in ('hierarchy', 'location', 'date-range'):
            self.decisions['items'][0].update(intent=intent, confidence='medium')
            row = next(r for r in self.run_mapping()['rows'] if r['sourceId']=='name')
            self.assertEqual(row['status'], 'Missing')
            self.assertIsNone(row['componentId'])

    def test_high_preferred_planned_component_does_not_silently_replace(self):
        decision = next(i for i in self.decisions['items'] if i['sourceId']=='add')
        decision['preferredId'] = 'action.button.default.medium'
        row = next(r for r in self.run_mapping()['rows'] if r['sourceId']=='add')
        self.assertEqual(row['status'], 'Missing')

    def test_stale_missing_duplicates_evidence_and_type_conflict(self):
        original = copy.deepcopy(self.decisions)
        mutations = [lambda d:d.update(registrySha256='0'*64),
                     lambda d:d.update(layoutTreeSha256='0'*64),
                     lambda d:d['items'].pop(),
                     lambda d:d['items'].append(copy.deepcopy(d['items'][0])),
                     lambda d:d['items'][0].update(evidence=['e3']),
                     lambda d:d['items'][0].update(intent='action'),
                     lambda d:d['items'][0].update(preferredId='action.button.primary.medium'),
                     lambda d:d['items'][0].update(color='red')]
        for mutate in mutations:
            self.decisions = copy.deepcopy(original)
            mutate(self.decisions)
            self.assertEqual(self.run_mapping()['status'], 'FAIL')

    def test_default_gate_and_no_input_mutation(self):
        before = copy.deepcopy(self.decisions)
        result = self.run_mapping(allow=False)
        self.assertEqual(result['rows'], [])
        self.assertFalse(result['readyForAssembly'])
        self.run_mapping()
        self.assertEqual(self.decisions, before)

    def test_all_registered_contract_fixture_passes_but_cannot_assemble(self):
        observations = load_json(BASE / 'observations.json')
        observations['unknowns'] = []
        for section in observations['page']['blocks']:
            section['staticContent'] = []
        from core.prototype.parser import parse
        f = self.fixture
        f.analysis = parse(observations, BASE)
        f.page = builder.build(f.analysis)
        f.review['analysisSha256'] = builder.fingerprint(f.analysis)
        f.plan['pageTreeSha256'] = builder.fingerprint(f.page)
        f.plan['measurements'] = {k:v for k,v in f.plan['measurements'].items()
                                  if k not in ('example-row', 'scope-note')}
        tree, _ = f.run_plan()
        self.decisions['layoutTreeSha256'] = builder.fingerprint(tree)
        self.decisions['items'] = [i for i in self.decisions['items']
                                    if i['sourceId'] not in ('example-row', 'scope-note')]
        result = self.run_mapping()
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(len(result['rows']), 7)
        self.assertFalse(result['readyForAssembly'])

    def test_annotation_escapes_content_and_colors_stay_outside_mapping(self):
        result = self.run_mapping()
        result['rows'][0]['label'] = '<script>alert(1)</script>'
        view = resolver.annotation(result)
        self.assertNotIn('<script>', view)
        self.assertIn('&lt;script&gt;', view)
        self.assertIn('form.input.default.medium', view)
        self.assertNotIn('color', result['rows'][0])


if __name__ == '__main__':
    unittest.main()
