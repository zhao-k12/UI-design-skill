"""Synthetic translation fixtures, not native design evidence."""
from copy import deepcopy
import unittest

from adapters.figma.form_candidate import translate_form, geometry, font_for_path


def style(*, transparent=True, padding=None, border=False):
    value = {'transform':'none','box-shadow':'none','opacity':'1','font-style':'normal',
        'text-transform':'none','visibility':'visible','letter-spacing':'normal',
        'background-color':'rgba(0, 0, 0, 0)' if transparent else 'rgb(255, 255, 255)',
        'color':'rgb(81, 90, 110)','font-size':'14px','font-weight':'400','line-height':'normal',
        'box-sizing':'border-box','position':'static'}
    for side in ('top','right','bottom','left'):
        value.update({f'border-{side}-width':'1px' if border else '0px',
            f'border-{side}-color':'rgb(220, 222, 226)',f'border-{side}-style':'solid' if border else 'none',
            f'padding-{side}':str((padding or {}).get(side,0))+'px'})
    for corner in ('top-left','top-right','bottom-right','bottom-left'):
        value[f'border-{corner}-radius']='4px' if border else '0px'
    return value


def node(path, tag, css, bounds=None, **extra):
    return {'path':path,'parentPath':None if path=='0' else path.rsplit('.',1)[0],
        'tag':tag,'visible':True,'bounds':bounds or {'x':0,'y':0,'width':240,'height':32},
        'computedStyle':css,'pseudoElements':{},'attributes':{},'value':None,'textRuns':[],**extra}


def fixture(kind):
    component={'componentType':kind,'logicalComponentId':'fixture.'+kind.lower(),
        'state':'default-static','variant':'default','provenance':{'sourceVersion':'fixture'},
        'rootBounds':{'width':240,'height':32},'content':{'options':[]},
        'nodes':[node('0','div',style())]}
    requirements=[{'family':'FixtureText','binding':{'family':'FixtureText','style':'Regular'},
        'uses':[{'path':'0.1' if kind=='Input' else '0.0.1.0','surface':'element'}]}]
    if kind=='Input':
        component['props']={'size':'default','modelValue':'','placeholder':'请输入姓名','elementId':'fixture-input'}
        placeholder=style(); placeholder['color']='rgb(197, 200, 206)'
        component['nodes'].append(node('0.1','input',style(transparent=False,border=True,padding={'top':4,'right':7,'bottom':4,'left':7}),
            value='',attributes={'type':'text','placeholder':'请输入姓名'},pseudoElements={'::placeholder':placeholder}))
    else:
        component['props']={'size':'default','modelValue':'enabled','placeholder':'请选择状态','elementId':'fixture-select','transfer':False}
        component['content']['options']=[{'value':'enabled','label':'启用'}]
        inner={'x':1,'y':1,'width':238,'height':30}
        label_style=style(padding={'left':8,'right':24}); label_style['line-height']='30px'
        arrow_style=style(); arrow_style.update(transform='matrix(1, 0, 0, 1, 0, -7)',position='absolute')
        pseudo=style(); pseudo.update(content='"\uf116"',**{'line-height':'14px'})
        component['nodes'] += [node('0.0','div',style(transparent=False,border=True)),
            node('0.0.1','div',style(),inner),node('0.0.1.0','span',label_style,inner,textRuns=[{'text':'启用'}]),
            node('0.0.1.1','i',arrow_style,{'x':217,'y':9,'width':14,'height':14},pseudoElements={'::before':pseudo})]
        requirements.append({'family':'FixtureIcons','binding':{'family':'FixtureIcons','style':'Regular'},
            'uses':[{'path':'0.0.1.1','surface':'pseudo:before'}]})
    return component,requirements


class FormCandidateTests(unittest.TestCase):
    def test_input_preserves_placeholder_color_padding_and_normal_line_height(self):
        component,fonts=fixture('Input'); spec=translate_form(component,fonts)
        self.assertEqual(spec['label']['characters'],'请输入姓名')
        self.assertEqual(spec['label']['fill']['color']['r'],197/255)
        self.assertEqual(spec['label']['lineHeight'],{'unit':'AUTO'})
        self.assertEqual(spec['surface']['padding']['left'],7)
        self.assertIsNone(spec['arrow'])

    def test_select_preserves_selected_value_and_actual_icon_glyph(self):
        component,fonts=fixture('Select'); spec=translate_form(component,fonts)
        self.assertEqual(spec['label']['characters'],'启用')
        self.assertEqual(spec['label']['padding']['right'],24)
        self.assertEqual(spec['arrow']['characters'],'\uf116')
        self.assertEqual(spec['arrow']['fontName']['family'],'FixtureIcons')
        self.assertEqual(spec['arrow']['bounds']['x'],217)

    def test_visible_dropdown_or_extra_input_node_are_unsupported(self):
        for kind in ('Input','Select'):
            component,fonts=fixture(kind)
            component['nodes'].append(node('0.9','div',style()))
            with self.assertRaisesRegex(ValueError,'structure'): translate_form(component,fonts)
            component['nodes'][-1]['visible']=False
            self.assertIn('0.9',translate_form(component,fonts)['ignoredHiddenPaths'])

    def test_input_value_and_selected_label_mismatch_fail(self):
        component,fonts=fixture('Input'); component['nodes'][1]['value']='unexpected'
        with self.assertRaisesRegex(ValueError,'placeholder'): translate_form(component,fonts)
        component,fonts=fixture('Select'); component['content']['options'][0]['label']='other'
        with self.assertRaisesRegex(ValueError,'value_mismatch'): translate_form(component,fonts)

    def test_pseudo_glyph_and_source_font_roles_cannot_be_guessed(self):
        component,fonts=fixture('Select')
        for content in ('none','"xx"','"\\e123"'):
            component['nodes'][-1]['pseudoElements']['::before']['content']=content
            with self.assertRaisesRegex(ValueError,'glyph'): translate_form(component,fonts)
        component,fonts=fixture('Select'); fonts[-1]['uses'][0]['surface']='element'
        with self.assertRaisesRegex(ValueError,'font_usage'): translate_form(component,fonts)

    def test_border_transform_parent_and_geometry_changes_fail(self):
        component,fonts=fixture('Input'); component['nodes'][1]['computedStyle']['border-left-width']='2px'
        with self.assertRaisesRegex(ValueError,'border'): translate_form(component,fonts)
        component,fonts=fixture('Select'); component['nodes'][-1]['computedStyle']['transform']='rotate(180deg)'
        with self.assertRaisesRegex(ValueError,'style'): translate_form(component,fonts)
        component,fonts=fixture('Input'); component['nodes'][1]['parentPath']='wrong'
        with self.assertRaisesRegex(ValueError,'parent'): translate_form(component,fonts)
        for width in (0,-1,float('nan'),True):
            with self.assertRaises(ValueError): geometry({'x':0,'y':0,'width':width,'height':32})
        component,fonts=fixture('Select'); component['nodes'][2]['bounds']['x']=2
        with self.assertRaisesRegex(ValueError,'geometry'): translate_form(component,fonts)
        component,fonts=fixture('Input'); component['nodes'][1]['pseudoElements']['::placeholder']['background-color']='rgb(255, 0, 0)'
        with self.assertRaisesRegex(ValueError,'decoration'): translate_form(component,fonts)

    def test_ambiguous_font_usage_and_replacement_binding_fail(self):
        component,fonts=fixture('Input'); fonts.append(deepcopy(fonts[0]))
        with self.assertRaisesRegex(ValueError,'font_usage'): translate_form(component,fonts)
        fonts.pop(); fonts[0]['binding']['family']='Replacement'
        with self.assertRaisesRegex(ValueError,'binding'): translate_form(component,fonts)
