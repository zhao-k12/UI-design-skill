import copy
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'core/pipeline'))
from html_composition import compile_tree


class TableColumnCoverageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.source = Path(self.tmp.name) / 'prototype'
        self.source.write_bytes(b'prototype fixture')
        self.sha = hashlib.sha256(self.source.read_bytes()).hexdigest()
        self.content = {
            'sourceSha256': self.sha,
            'root': {'id': 'results', 'kind': 'component', 'component': 'Table',
                     'sourceIds': ['table'], 'props': {'columns': [
                         {'type': 'selection', 'width': 55},
                         {'title': '编号', 'key': 'id'},
                         {'title': '状态', 'key': 'status'},
                         {'title': '操作', 'key': 'action'},
                     ], 'data': []}},
        }
        traits = {'leading': 'none', 'trailing': 'none', 'surface': 'plain',
                  'shape': 'rect', 'role': 'table'}
        self.observation = {'sourceSha256': self.sha, 'items': [
            {'id': 'table', 'region': 'results', 'traits': traits,
             'decision': 'include', 'sourceEvidence': '三列和选择框', 'treeRef': 'results'}]}
        self.scan = {'sourceSha256': self.sha, 'items': [
            {'id': 'table', 'region': 'results', 'traits': copy.deepcopy(traits), 'visual': '三列和选择框'}]}

    def tearDown(self):
        self.tmp.cleanup()

    def compile(self):
        return compile_tree(self.source, self.content, self.observation, self.scan)

    def record(self, observed, scanned=None):
        self.observation['tableColumns'] = {'results': observed}
        self.scan['tableColumns'] = {'results': list(observed) if scanned is None else scanned}

    def test_independent_matching_lists_cover_only_titled_columns(self):
        self.record(['编号', '状态', '操作'])
        report = self.compile()['qa_report']
        self.assertEqual(report['tableColumnCoverage']['status'], 'checked')
        self.assertEqual(report['tableColumnCoverage']['checkedTables'], ['results'])
        self.assertIn('not source completeness', report['statusMeaning'])

    def test_source_and_scan_must_both_be_supplied(self):
        self.observation['tableColumns'] = {'results': ['编号', '状态', '操作']}
        with self.assertRaisesRegex(ValueError, 'table_columns_both_observations_required'):
            self.compile()

    def test_disagreeing_independent_observations_are_rejected(self):
        self.record(['编号', '状态', '操作'], ['编号', '操作', '状态'])
        with self.assertRaisesRegex(ValueError, 'table_columns_observation_disagrees:results'):
            self.compile()

    def test_missing_or_reordered_tree_column_is_rejected(self):
        self.record(['编号', '状态', '操作'])
        self.content['root']['props']['columns'].pop(2)
        with self.assertRaisesRegex(ValueError, 'table_columns_tree_mismatch:results'):
            self.compile()
        self.content['root']['props']['columns'].insert(2, {'title': '操作', 'key': 'action'})
        self.content['root']['props']['columns'].pop()
        self.content['root']['props']['columns'].append({'title': '状态', 'key': 'status'})
        with self.assertRaisesRegex(ValueError, 'table_columns_tree_mismatch:results'):
            self.compile()

    def test_legacy_job_remains_valid_but_coverage_is_unchecked(self):
        report = self.compile()['qa_report']
        self.assertEqual(report['status'], 'PASS')
        self.assertEqual(report['tableColumnCoverage']['status'], 'not_checked')
        self.assertEqual(report['tableColumnCoverage']['uncheckedTables'], ['results'])

    def test_multiple_tables_report_partial_coverage(self):
        original = self.content['root']
        second = copy.deepcopy(original)
        second['id'] = 'other-results'
        second.pop('sourceIds')
        self.content['root'] = {'id': 'page', 'kind': 'container',
                                'children': [original, second]}
        self.record(['编号', '状态', '操作'])
        coverage = self.compile()['qa_report']['tableColumnCoverage']
        self.assertEqual(coverage['status'], 'partial')
        self.assertEqual(coverage['checkedTables'], ['results'])
        self.assertEqual(coverage['uncheckedTables'], ['other-results'])

    def test_invalid_or_unknown_inventory_is_rejected(self):
        self.record(['编号', '', '操作'])
        with self.assertRaisesRegex(ValueError, 'table_columns_inventory_invalid'):
            self.compile()
        self.observation['tableColumns'] = {'other': ['编号']}
        self.scan['tableColumns'] = {'other': ['编号']}
        with self.assertRaisesRegex(ValueError, 'table_columns_inventory_unknown_table'):
            self.compile()

    def test_grouped_columns_are_not_claimed_as_verified(self):
        self.record(['编号', '状态', '操作'])
        self.content['root']['props']['columns'][1]['children'] = [{'title': '编号', 'key': 'id'}]
        with self.assertRaisesRegex(ValueError, 'table_columns_grouped_or_invalid'):
            self.compile()


if __name__ == '__main__':
    unittest.main()
