import unittest
from adapters.figma.font_preflight import preflight_source_fonts


class SourceFontPreflightTests(unittest.TestCase):
    def setUp(self):
        self.evidence = {'scope': 'official_runtime_font_diagnostic', 'status': 'PASS',
            'referenceMatches': [{'logicalId': 'button', 'screenshotMatches': True, 'environmentMatches': True}],
            'observations': [{'logicalId': 'button', 'path': '0', 'surface': 'element',
                'fonts': [{'familyName': 'Source Family', 'glyphCount': 2, 'postScriptName': 'Source-Regular', 'isCustomFont': False}]}]}
        self.discovery = {'scope': 'figma_official_font_discovery', 'fileReference': 'fixture',
            'queriedFamilies': ['Source Family'], 'matches': [], 'createdNodeIds': [], 'mutatedNodeIds': []}

    def test_missing_font_cannot_be_replaced_with_project_font(self):
        report = preflight_source_fonts(self.evidence, self.discovery, {'Source Family': {'family': 'Noto Sans SC', 'style': 'Regular'}})
        self.assertEqual(report['status'], 'REVIEW')
        self.assertEqual(report['issues'][0]['code'], 'missing_official_font')
        self.assertFalse(report['admissionEligible'])

    def test_style_is_not_guessed_from_postscript_name(self):
        self.discovery['matches'] = [{'family': 'Source Family', 'style': 'Regular'}]
        self.assertEqual(preflight_source_fonts(self.evidence, self.discovery, {'Source Family': 'Regular'})['requirements'][0]['status'], 'INVALID_BINDING')
        self.assertEqual(preflight_source_fonts(self.evidence, self.discovery)['requirements'][0]['status'], 'REQUIRES_EXPLICIT_STYLE_BINDING')
        report = preflight_source_fonts(self.evidence, self.discovery, {'Source Family': self.discovery['matches'][0]})
        self.assertEqual(report['status'], 'PASS')
        self.assertEqual(report['nativeExecution'], 'NOT_RUN')
        self.assertFalse(report['admissionEligible'])

    def test_discovery_drift_and_font_substitution_are_rejected(self):
        self.discovery['matches'] = [{'family': 'Source Family', 'style': 'Regular'}]
        report = preflight_source_fonts(self.evidence, self.discovery, {'Source Family': {'family': 'Other', 'style': 'Regular'}})
        self.assertEqual(report['requirements'][0]['status'], 'INVALID_BINDING')
        self.evidence['referenceMatches'][0]['screenshotMatches'] = False
        self.discovery['mutatedNodeIds'] = ['fixture-node']
        codes = {item['code'] for item in preflight_source_fonts(self.evidence, self.discovery)['issues']}
        self.assertIn('font_reference_not_reproduced', codes)
        self.assertIn('font_discovery_must_be_read_only', codes)

    def test_empty_glyph_usage_remains_unknown(self):
        self.evidence['observations'][0]['fonts'][0]['glyphCount'] = 0
        codes = {item['code'] for item in preflight_source_fonts(self.evidence, self.discovery)['issues']}
        self.assertIn('component_font_usage_unknown', codes)
        self.assertIn('no_observed_source_fonts', codes)
