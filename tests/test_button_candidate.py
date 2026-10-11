from copy import deepcopy
import unittest
import hashlib
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from adapters.figma.button_candidate import translate_button, paint, px, calibrated_span


class ButtonCandidateTests(unittest.TestCase):
    def setUp(self):
        style = {'transform':'none', 'box-shadow':'none', 'opacity':'1', 'font-style':'normal',
            'text-transform':'none', 'letter-spacing':'normal', 'box-sizing':'border-box', 'text-align':'center',
            'background-color':'rgb(45, 140, 240)', 'color':'rgb(255, 255, 255)',
            'font-weight':'400', 'font-size':'14px', 'line-height':'21px'}
        for side in ('top', 'right', 'bottom', 'left'):
            style.update({f'border-{side}-width':'1px', f'border-{side}-style':'solid',
                f'border-{side}-color':'rgb(45, 140, 240)', f'padding-{side}':'0px' if side in ('top','bottom') else '15px'})
        for corner in ('top-left','top-right','bottom-right','bottom-left'):
            style[f'border-{corner}-radius'] = '4px'
        self.component = {'componentType':'Button', 'state':'default-static', 'props':{'type':'primary','size':'default'},
            'logicalComponentId':'fixture.button', 'provenance':{'sourceVersion':'fixture'},
            'rootBounds':{'width':60,'height':32}, 'iconMetrics':[], 'content':{'text':'查询','options':[]},
            'nodes':[{'tag':'button','path':'0','visible':True,'computedStyle':style,'pseudoElements':{}},
                {'tag':'span','path':'0.0','parentPath':'0','visible':True,'computedStyle':deepcopy(style),
                 'pseudoElements':{},'textRuns':[{'text':'查询'}]}]}
        self.font = {'family':'Fixture Source','style':'Regular'}

    def test_exact_source_values_and_font_binding(self):
        spec = translate_button(self.component, self.font)
        self.assertEqual((spec['width'],spec['height'],spec['fontSize'],spec['lineHeight']), (60,32,14,21))
        self.assertEqual(spec['padding']['left'],15)
        self.assertEqual(spec['fill']['color']['b'],240/255)
        self.assertEqual(spec['fontName'], self.font)

    def test_nonuniform_border_and_visible_pseudo_rejected(self):
        self.component['nodes'][0]['computedStyle']['border-left-width'] = '2px'
        with self.assertRaisesRegex(ValueError,'nonuniform'): translate_button(self.component,self.font)
        self.component['nodes'][0]['computedStyle']['border-left-width'] = '1px'
        self.component['nodes'][0]['pseudoElements'] = {'::before':{'display':'block','content':'"x"'}}
        with self.assertRaisesRegex(ValueError,'visible_pseudo'): translate_button(self.component,self.font)

    def test_unsupported_style_variant_and_content_rejected(self):
        for key in ('transform','font-style'):
            original = self.component['nodes'][1]['computedStyle'][key]
            self.component['nodes'][1]['computedStyle'][key] = 'unsupported'
            with self.assertRaises(ValueError): translate_button(self.component,self.font)
            self.component['nodes'][1]['computedStyle'][key] = original
        self.component['props']['size'] = 'large'
        with self.assertRaisesRegex(ValueError,'variant'): translate_button(self.component,self.font)

    def test_no_css_guessing(self):
        for value in ('auto','1em','-2px','NaNpx'):
            with self.assertRaises(ValueError): px(value)
        for value in ('red','rgb(300, 0, 0)','var(--primary)'):
            with self.assertRaises(ValueError): paint(value)

    def test_calibration_requires_exact_reference_and_native_font_binding(self):
        with tempfile.TemporaryDirectory() as folder:
            directory=Path(folder);reference=directory/'reference';reference.mkdir()
            (reference/'component_ir.json').write_bytes(b'fixture')
            digest=hashlib.sha256(b'fixture').hexdigest()
            spec=translate_button(self.component,self.font)
            self.component['nodes'][1]['bounds']={'x':16,'y':5.5,'width':28,'height':21}
            text={'textReference':'text','fontName':self.font,'fontSize':14,'fontWeight':400,
                'characters':'查询','lineHeight':{'unit':'PIXELS','value':21},
                'absoluteBounds':{'width':28,'height':21},'svg':'<svg>fixture</svg>'}
            files={'official-runtime-complete-baseline-evidence.json':{'referenceComponentIrSha256':digest},
                'native-text-outline-after-baseline-revision.json':{'fileReference':'file','observations':[text]},
                'font-file-identity.json':{},'official-native-candidate-execution.json':{}}
            for name,value in files.items():(directory/name).write_text(json.dumps(value),encoding='utf-8')
            report={'observations':[{'logicalId':'fixture.button','exactContourCoordinatesEqual':True,
                'textReference':'text','sourceBaselineComponentY':20.5,'nativeSvgBaselineOffset':16}]}
            with patch('adapters.figma.button_candidate.compare_baseline_alignment',return_value=report):
                result=calibrated_span(reference,self.component,spec,directory,'file')
                self.assertEqual(result['textOffsetY'],-1);self.assertEqual(len(result['evidenceHashes']),4)
                spec['fontName']={'family':'Wrong','style':'Regular'}
                with self.assertRaisesRegex(ValueError,'binding_mismatch'):calibrated_span(reference,self.component,spec,directory,'file')
                (reference/'component_ir.json').write_bytes(b'changed')
                with self.assertRaisesRegex(ValueError,'reference_mismatch'):calibrated_span(reference,self.component,spec,directory,'file')
