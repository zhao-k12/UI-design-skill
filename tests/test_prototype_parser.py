import copy
from pathlib import Path
import tempfile
import unittest

from core.prototype.parser import AnalysisError, parse
from validators.ui_ir import load_json
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'examples/prototype-semantic'


class PrototypeParserTests(unittest.TestCase):
    def setUp(self):
        self.obs = load_json(BASE / 'observations.json')

    def reject(self, document):
        with self.assertRaises(AnalysisError):
            parse(document, BASE)

    def test_semantic_output_is_source_bound_and_not_design(self):
        before = copy.deepcopy(self.obs)
        result = parse(self.obs, BASE)
        self.assertEqual(result['page']['identity']['text'], '用户管理')
        self.assertEqual(len(result['page']['blocks']), 4)
        self.assertFalse(result['readyForStructure'])
        self.assertEqual(result['status'], 'Review')
        self.assertEqual(self.obs, before)
        self.assertEqual(result, load_json(BASE / 'prototype_analysis.json'))
        Draft202012Validator(load_json(ROOT / 'schemas/prototype-analysis.schema.json')).validate(result)

    def test_unknowns_are_preserved(self):
        self.assertEqual(parse(self.obs, BASE)['unknowns'], self.obs['unknowns'])

    def test_no_automatic_approval_even_without_unknowns(self):
        self.obs['unknowns'] = []
        self.assertFalse(parse(self.obs, BASE)['readyForStructure'])

    def test_rejects_visual_component_and_interaction_fields(self):
        for field in ('component', 'color', 'spacing', 'gridSpan', 'layout', 'onClick', 'figmaNodeId'):
            with self.subTest(field=field):
                doc = copy.deepcopy(self.obs)
                doc['page']['blocks'][0][field] = 'invented'
                self.reject(doc)

    def test_tampered_quote_hash_and_references(self):
        for mutate in (
            lambda d: d['evidence'][0].update(quote='invented'),
            lambda d: d['sources'][0].update(sha256='0'*64),
            lambda d: d['evidence'][0].update(end=999999),
            lambda d: d['evidence'][0].update(sourceId='missing'),
            lambda d: d['page']['identity'].update(evidence=['missing']),
            lambda d: d['sources'][0].update(path='../outside.txt'),
            lambda d: d['page']['blocks'][1].update(id='filters'),
            lambda d: d['evidence'].append(copy.deepcopy(d['evidence'][0])),
            lambda d: d['sources'].append(copy.deepcopy(d['sources'][0])),
        ):
            doc = copy.deepcopy(self.obs)
            mutate(doc)
            self.reject(doc)

    def test_source_bytes_change_invalidates_observations(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            (base / 'prototype.txt').write_text('changed', encoding='utf-8')
            with self.assertRaises(AnalysisError):
                parse(self.obs, base)

    def test_empty_evidence_and_missing_semantic_categories_rejected(self):
        self.obs['page']['identity']['evidence'] = []
        self.reject(self.obs)
        self.setUp()
        del self.obs['page']['blocks'][0]['fields']
        self.reject(self.obs)


if __name__ == '__main__':
    unittest.main()
