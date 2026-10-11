import copy
import importlib
from pathlib import Path
import unittest
import json
import subprocess
import sys
import tempfile

from core.layout.builder import generate, tokens
from core.prototype.parser import parse
from validators.structure.gate import builder
from validators.ui_ir import load_json

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'examples/prototype-semantic'


class LayoutBuilderTests(unittest.TestCase):
    def setUp(self):
        observations = load_json(BASE / 'observations.json')
        observations['unknowns'] = []  # Explicitly synthetic contract fixture.
        self.analysis = parse(observations, BASE)
        self.page = builder.build(self.analysis)
        self.review = dict(version='0.1.0', analysisSha256=builder.fingerprint(self.analysis),
                           decision='approved', reviewedBy='synthetic-test-fixture',
                           reviewedAt='2026-10-08T12:00:00+08:00', note='Not user approval')
        self.registry = tokens.TokenRegistry(load_json(ROOT / 'registries/tokens/default.json'))
        self.plan = dict(version='0.1.0', pattern='list-page', pageTreeSha256=builder.fingerprint(self.page),
                         tokenRegistrySha256=self.registry.fingerprint,
                         sectionRegions=dict(filters='query', toolbar='toolbar', results='table', note='header'),
                         measurements={item['id']:dict(width=160, height=32,
                            source=dict(kind='test-fixture', reference='TASK-013-contract-test'))
                            for section in self.page['page']['children'] for item in section['children']})

    def run_plan(self, **kwargs):
        return generate(self.analysis, self.page, BASE, self.review, self.plan, self.registry,
                        allow_test_fixtures=kwargs.get('allow', True))

    def test_standard_patterns_with_complete_provenance(self):
        before = copy.deepcopy((self.analysis, self.page, self.plan))
        tree, report = self.run_plan()
        self.assertEqual(report['status'], 'PASS', report)
        self.assertTrue(report['testFixture'])
        self.assertFalse(report['readyForMapping'])
        self.assertEqual((self.analysis, self.page, self.plan), before)
        cells = []
        def walk(node):
            if node['type'] == 'Cell':
                cells.extend(node['sourceIds'])
                self.assertNotIn('x', node)
                if node.get('role') == 'field':
                    self.assertEqual(node['layout']['span'], 6)
            for child in node.get('children', []):
                walk(child)
        walk(tree['page'])
        expected = [item['id'] for section in self.page['page']['children'] for item in section['children']]
        self.assertCountEqual(cells, expected)
        self.assertEqual(len(cells), len(set(cells)))
        self.assertNotIn('pagination', [s['role'] for s in tree['page']['children']])
        self.assertEqual(self.run_plan(), (tree, report))

    def test_recomputes_structure_gate(self):
        self.analysis = load_json(BASE / 'prototype_analysis.json')
        self.page = builder.build(self.analysis)
        tree, report = self.run_plan()
        self.assertIsNone(tree)
        self.assertNotEqual(report['status'], 'PASS')
        self.page['page']['children'].pop()
        self.assertEqual(self.run_plan()[1]['status'], 'FAIL')

    def test_fixture_measurements_rejected_by_default(self):
        self.assertIsNone(self.run_plan(allow=False)[0])
        self.assertEqual(self.run_plan(allow=False)[1]['status'], 'FAIL')

    def test_missing_stale_ambiguous_and_free_coordinates_rejected(self):
        mutations = [lambda p:p['measurements'].pop('name'),
                     lambda p:p.update(pageTreeSha256='0'*64),
                     lambda p:p.update(tokenRegistrySha256='0'*64),
                     lambda p:p['sectionRegions'].update(toolbar='query'),
                     lambda p:p['sectionRegions'].update(note='invented'),
                     lambda p:p['sectionRegions'].pop('results'),
                     lambda p:p.update(pattern='free'),
                     lambda p:p.update(x=30),
                     lambda p:p['measurements']['name'].update(width=float('nan'))]
        before = copy.deepcopy(self.plan)
        for mutate in mutations:
            self.plan = copy.deepcopy(before)
            mutate(self.plan)
            with self.subTest(mutation=mutate):
                self.assertEqual(self.run_plan()[1]['status'], 'FAIL')

    def test_wide_button_overflow_rejected(self):
        self.plan['measurements']['add']['width'] = 5000
        tree, report = self.run_plan()
        self.assertEqual(report['status'], 'FAIL')
        self.assertFalse(report['readyForMapping'])
        self.assertIsNone(report['engineReport']['skeleton'])

    def test_all_standard_pattern_families(self):
        for pattern, region in [('list-page', 'query'), ('detail-page', 'detail'),
                                ('form-page', 'form'), ('dashboard-basic', 'content'),
                                ('sidebar-content', 'content')]:
            self.setUp()
            observations = load_json(BASE / 'observations.json')
            observations['unknowns'] = []
            observations['page']['blocks'] = observations['page']['blocks'][:1]
            self.analysis = parse(observations, BASE)
            self.page = builder.build(self.analysis)
            self.review['analysisSha256'] = builder.fingerprint(self.analysis)
            self.plan.update(pattern=pattern, pageTreeSha256=builder.fingerprint(self.page),
                             sectionRegions={'filters': region})
            self.plan['measurements'] = {key: value for key, value in self.plan['measurements'].items()
                                         if key in {'name', 'status', 'search', 'reset'}}
            with self.subTest(pattern=pattern):
                self.assertEqual(self.run_plan()[1]['status'], 'PASS')

    def test_cli_review_replaces_stale_layout_and_blocks_exit(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            plan = output / 'plan.json'
            plan.write_text(json.dumps(self.plan), encoding='utf-8')
            (output / 'layout_tree.json').write_text('{"stale":"success"}', encoding='utf-8')
            result = subprocess.run([sys.executable, '-m', 'core.layout.builder',
                str(BASE / 'prototype_analysis.json'), str(BASE / 'structure/page_tree.json'),
                str(plan), '--source-root', str(BASE), '--output-dir', str(output)],
                cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertIsNone(load_json(output / 'layout_tree.json'))
            self.assertEqual(load_json(output / 'layout_qa_report.json')['status'], 'Review')


if __name__ == '__main__':
    unittest.main()
