from copy import deepcopy
import unittest
from adapters.figma.render_state_diagnostic import compare_render_state


class RenderStateTests(unittest.TestCase):
    def setUp(self):
        self.reference={'logicalComponentId':'fixture.button','componentType':'Button'}
        style={'opacity':'1','box-shadow':'none','text-shadow':'none','filter':'none',
            'mix-blend-mode':'normal','text-transform':'none','text-decoration-line':'none','letter-spacing':'normal'}
        self.settings={'rows':[{'path':path,'surface':'element','properties':deepcopy(style)} for path in ('0','0.0')]}
        self.native={'nodes':[{'reference':'root','type':'COMPONENT','name':'fixture','properties':{'opacity':1,'effects':[],'blendMode':'NORMAL'}},
            {'reference':'text','type':'TEXT','name':'label','properties':{
            'opacity':1,'effects':[],'blendMode':'NORMAL','textCase':'ORIGINAL','textDecoration':'NONE',
            'letterSpacing':{'unit':'PIXELS','value':0}}}]}

    def compare(self):return compare_render_state(self.reference,self.native,self.settings)

    def test_observed_states_pass_without_fidelity_admission(self):
        result=self.compare();self.assertEqual(result['status'],'PASS');self.assertFalse(result['admissionEligible'])

    def test_actual_shadow_opacity_decoration_or_tracking_mismatches_fail(self):
        for field,value in [('opacity',.5),('effects',[{'type':'DROP_SHADOW'}]),('textDecoration','UNDERLINE'),
                            ('letterSpacing',{'unit':'PIXELS','value':1}),('blendMode','MULTIPLY')]:
            with self.subTest(field=field):
                original=deepcopy(self.native);self.native['nodes'][-1]['properties'][field]=value
                self.assertEqual(self.compare()['status'],'FAIL');self.native=original

    def test_missing_or_mixed_native_state_and_passthrough_text_remain_review(self):
        for field,value in [('textCase',{'nativeMixed':True}),('blendMode','PASS_THROUGH')]:
            original=deepcopy(self.native);self.native['nodes'][-1]['properties'][field]=value
            result=self.compare()
            self.assertEqual(result['status'],'REVIEW')
            self.native=original
        del self.native['nodes'][-1]['properties']['textDecoration']
        self.assertEqual(self.compare()['status'],'REVIEW')

    def test_source_effects_or_unobserved_css_are_not_assumed_none(self):
        del self.settings['rows'][0]['properties']['text-shadow']
        result=self.compare();self.assertEqual(result['status'],'REVIEW')
        self.assertTrue(any(row['field']=='effects' for row in result['unverified']))
