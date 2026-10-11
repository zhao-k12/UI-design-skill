"""Contract fixtures mock artifact verification; these never prove native acceptance."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from adapters.figma.candidate_preflight import prepare_candidates, file_hash


class CandidatePreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.reference = Path(self.temp.name)
        self.bundle = {'components': [self.component('button'), self.component('select')]}
        (self.reference / 'component_ir.json').write_text(json.dumps(self.bundle), encoding='utf-8')
        (self.reference / 'runtime_manifest.json').write_text('{}')
        self.evidence = {'scope': 'official_runtime_font_diagnostic', 'status': 'PASS',
            'referenceComponentIrSha256': file_hash(self.reference / 'component_ir.json'),
            'environment': {}, 'provenance': {},
            'referenceMatches': [{'logicalId': name, 'screenshotMatches': True, 'environmentMatches': True} for name in ('button', 'select')],
            'observations': [{'logicalId': name, 'path': '0', 'surface': 'element',
                'fonts': [{'familyName': family, 'glyphCount': 1}]} for name, family in [('button', 'TextFont'), ('select', 'IconFont')]]}
        self.discovery = {'scope': 'figma_official_font_discovery', 'fileReference': 'fixture',
            'queriedFamilies': ['TextFont', 'IconFont'], 'matches': [{'family': 'TextFont', 'style': 'Regular'}]}
        self.mock = patch('adapters.figma.candidate_preflight.verify_artifacts', return_value=[])
        self.verify = self.mock.start()
        self.addCleanup(self.mock.stop)

    def component(self, name):
        return {'logicalComponentId': name, 'componentType': 'Button', 'variant': 'default',
            'state': 'default-static', 'environment': {}, 'provenance': {'sourceVersion': 'fixture'},
            'screenshot': {'path': name + '.png', 'sha256': '0' * 64}}

    def run_preflight(self, **kwargs):
        self.evidence['provenance']['sourceVersion'] = 'fixture'
        return prepare_candidates(self.reference, self.evidence, self.discovery, file_reference='fixture', **kwargs)

    def test_selected_button_does_not_require_unrelated_icon_font(self):
        report = self.run_preflight(logical_ids=['button'], bindings={'TextFont': {'family': 'TextFont', 'style': 'Regular'}})
        self.assertEqual(report['status'], 'PASS')
        self.assertEqual(report['preparation']['nativeBuilder'], 'NOT_IMPLEMENTED')
        self.assertFalse(report['admissionEligible'])
        self.assertEqual([item['logicalId'] for item in report['preparation']['components']], ['button'])
        self.assertNotIn('measurements', report['preparation'])
        self.assertEqual(self.run_preflight()['status'], 'REVIEW')

    def test_reference_hash_mismatch_and_unknown_observations_fail(self):
        self.evidence['referenceComponentIrSha256'] = '0' * 64
        self.assertEqual(self.run_preflight()['status'], 'FAIL')
        self.evidence['referenceComponentIrSha256'] = file_hash(self.reference / 'component_ir.json')
        self.evidence['observations'][0]['logicalId'] = 'unrelated'
        self.assertIn('unknown_component', self.run_preflight()['issues'][0]['detail'])

    def test_inventory_environment_and_file_mismatch_fail(self):
        self.evidence['referenceMatches'].append(deepcopy(self.evidence['referenceMatches'][0]))
        self.assertEqual(self.run_preflight()['status'], 'FAIL')
        self.evidence['referenceMatches'].pop()
        self.evidence['environment'] = {'browser': 'other'}
        self.assertIn('environment_mismatch', self.run_preflight()['issues'][0]['detail'])
        self.discovery['fileReference'] = 'other'
        self.assertIn('file_mismatch', self.run_preflight()['issues'][0]['detail'])

    def test_bad_selection_and_failed_artifacts_cannot_produce_preparation(self):
        for selection in ([], ['missing'], ['button', 'button']):
            report = self.run_preflight(logical_ids=selection)
            self.assertEqual(report['status'], 'FAIL')
            self.assertIsNone(report['preparation'])
        self.verify.return_value = [{'code': 'evidence_hash_mismatch'}]
        self.assertEqual(self.run_preflight()['issues'][0]['code'], 'evidence_hash_mismatch')

    def test_screenshot_escape_is_rejected_before_artifact_reads(self):
        self.bundle['components'][0]['screenshot']['path'] = '../outside.png'
        (self.reference / 'component_ir.json').write_text(json.dumps(self.bundle))
        self.assertIn('outside_reference', self.run_preflight()['issues'][0]['detail'])
        self.verify.assert_not_called()
