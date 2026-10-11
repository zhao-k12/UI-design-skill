import copy
from pathlib import Path
import unittest
import tempfile

from core.prototype.parser import parse
from validators.structure.gate import builder, check
from validators.ui_ir import load_json

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'examples/prototype-semantic'


class StructureTests(unittest.TestCase):
    def setUp(self):
        self.analysis = load_json(BASE / 'prototype_analysis.json')
        self.tree = builder.build(self.analysis)

    def approved_fixture(self):
        # Synthetic receipt exercises the contract; never a real user's approval.
        observations = load_json(BASE / 'observations.json')
        observations['unknowns'] = []
        self.analysis = parse(observations, BASE)
        self.tree = builder.build(self.analysis)
        return dict(version='0.1.0', analysisSha256=builder.fingerprint(self.analysis),
                    decision='approved', reviewedBy='synthetic-test-fixture',
                    reviewedAt='2026-10-08T12:00:00+08:00', note='Contract test only')

    def test_real_example_stays_review_and_not_frozen(self):
        report = check(self.analysis, self.tree, BASE)
        self.assertEqual(report['status'], 'Review')
        self.assertFalse(report['readyForLayout'])
        self.assertNotIn('freeze', report)
        self.assertEqual(self.tree, load_json(BASE / 'structure/page_tree.json'))
        self.assertEqual(report, load_json(BASE / 'structure/structure_qa_report.json'))

    def test_positive_contract_fixture_freezes_exact_hash(self):
        review = self.approved_fixture()
        report = check(self.analysis, self.tree, BASE, review)
        self.assertEqual(report['status'], 'PASS')
        self.assertEqual(report['freeze']['pageTreeSha256'], builder.fingerprint(self.tree))

    def test_missing_rejected_stale_review_does_not_pass(self):
        review = self.approved_fixture()
        self.assertEqual(check(self.analysis, self.tree, BASE)['status'], 'Review')
        review['decision'] = 'rejected'
        self.assertEqual(check(self.analysis, self.tree, BASE, review)['status'], 'Review')
        review['analysisSha256'] = '0' * 64
        self.assertEqual(check(self.analysis, self.tree, BASE, review)['status'], 'FAIL')

    def test_unknowns_block_even_with_approval(self):
        review = self.approved_fixture()
        self.analysis = load_json(BASE / 'prototype_analysis.json')
        self.tree = builder.build(self.analysis)
        review['analysisSha256'] = builder.fingerprint(self.analysis)
        self.assertEqual(check(self.analysis, self.tree, BASE, review)['status'], 'Review')

    def test_omission_move_duplicates_content_and_hierarchy_rejected(self):
        mutations = [
            lambda t: t['page']['children'].pop(),
            lambda t: t['page']['children'].reverse(),
            lambda t: t['page']['children'][0]['children'].pop(0),
            lambda t: t['page']['children'][1]['children'].append(t['page']['children'][0]['children'].pop()),
            lambda t: t['page']['children'].append(copy.deepcopy(t['page']['children'][0])),
            lambda t: t['page']['children'][0]['children'][0]['description'].update(text='changed'),
            lambda t: t['page']['children'][0]['children'][0].update(kind='buttons'),
            lambda t: t['page']['children'][0]['children'][0].update(children=[]),
            lambda t: t['page'].update(kind='Section'),
            lambda t: t.update(analysisSha256='0'*64),
            lambda t: t['page']['children'][0].update(color='red'),
            lambda t: t['page'].update(id='different-page'),
        ]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                tree = copy.deepcopy(self.tree)
                mutate(tree)
                result = check(self.analysis, tree, BASE)
                self.assertEqual(result['status'], 'FAIL')
                self.assertFalse(result['readyForLayout'])
                self.assertNotIn('freeze', result)

    def test_source_and_analysis_tampering_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'prototype.txt').write_text('changed', encoding='utf-8')
            self.assertEqual(check(self.analysis, self.tree, root)['status'], 'FAIL')
        self.analysis['evidence'][0]['quote'] = 'invented'
        self.tree = builder.build(self.analysis)
        self.assertEqual(check(self.analysis, self.tree, BASE)['status'], 'FAIL')

    def test_builder_does_not_mutate_analysis_or_invent_sections(self):
        before = copy.deepcopy(self.analysis)
        self.tree['page']['identity']['text'] = 'changed'
        self.assertEqual(self.analysis, before)
        self.assertEqual([s['id'] for s in builder.build(before)['page']['children']],
                         [s['id'] for s in before['page']['blocks']])


if __name__ == '__main__':
    unittest.main()
