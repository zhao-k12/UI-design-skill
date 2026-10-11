import copy
import json
from pathlib import Path
import unittest
from adapters.figma.true_type_encoding_diagnostic import inspect, runtime, verify
from validators.ui_ir import ROOT


class ArialEncodingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ft=runtime(ROOT/'artifacts/task-019/freetype-probe-deps')
        cls.font=Path('C:/Windows/Fonts/arial.ttf')
        cls.metadata=ROOT/'adapters/figma/metadata/configurable-table-native'
        cls.captures=[json.loads((cls.metadata/f'arial-glyph-readback-{i}.json').read_text(encoding='utf-8')) for i in range(1,5)]
        for i in (0,1): cls.captures.extend(json.loads((cls.metadata/f'table-text-outlines-{i}.json').read_text(encoding='utf-8')))

    def test_complete_actual_strings(self):
        report=inspect(self.captures,self.font,self.ft)
        self.assertEqual(report['status'],'PASS')
        self.assertEqual(len(report['observations']),26)
        self.assertFalse(report['admissionEligible'])

    def test_baseline_controlpoint_and_width_rejected(self):
        observation=self.captures[0]['observations'][0]
        for old,new in [('1.27148','1.27149'),(' 15',' 14')]:
            altered=copy.deepcopy(observation)
            altered['svg']=altered['svg'].replace(old,new)
            self.assertEqual(verify(altered,self.font,self.ft)['status'],'FAIL')
        altered=copy.deepcopy(observation);altered['absoluteBounds']['width']+=1
        self.assertEqual(verify(altered,self.font,self.ft)['status'],'FAIL')

    def test_wrong_font_uncovered_text_paint_and_typography_rejected(self):
        observation=self.captures[0]['observations'][0]
        for key,value in [('characters','b'),('fontSize',15),('fontWeight',500),('svg',observation['svg'].replace('#515A6E','#000000'))]:
            altered=copy.deepcopy(observation);altered[key]=value
            with self.assertRaises(ValueError): verify(altered,self.font,self.ft)
        with self.assertRaises(ValueError): verify(observation,ROOT/'SKILL.md',self.ft)

    def test_missing_and_duplicate_observations_rejected(self):
        self.assertEqual(inspect(self.captures[1:],self.font,self.ft)['status'],'FAIL')
        with self.assertRaises(ValueError): inspect(self.captures+[self.captures[0]],self.font,self.ft)
        for key,value in [('fileReference','other-file'),('pageReference','other-page')]:
            altered=copy.deepcopy(self.captures);altered[0][key]=value
            with self.assertRaises(ValueError): inspect(altered,self.font,self.ft)
