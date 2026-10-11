import copy
import importlib
from pathlib import Path
import unittest
from validators.ui_ir import load_json

ROOT=Path(__file__).resolve().parents[1]
layout=importlib.import_module('core.component-resolver.slot_layout')
geometry_module=importlib.import_module('core.component-resolver.placement')


class CellSlotTests(unittest.TestCase):
    def setUp(self):
        self.registry=geometry_module.registry_module.ComponentRegistry(load_json(ROOT/'registries/components/catalog.json'),load_json(ROOT/'registries/components/fidelity-reports.json'))
        self.geometry=geometry_module.SourceGeometry(load_json(ROOT/'adapters/figma/metadata/official-fixture-reference/component_ir.json'),self.registry)
        self.tokens=importlib.import_module('core.design-rules.tokens').TokenRegistry(load_json(ROOT/'registries/tokens/default.json'))
        lock=load_json(ROOT/'registries/icons/current.json')
        self.icons=importlib.import_module('core.icon-resolver.registry').IconRegistry(load_json(ROOT/'registries/icons/snapshots'/lock['snapshotSha256']/'registry.json'))
        self.icon_sources={i:(ROOT/'registries/icons/objects'/(self.icons.resolve(i)['descriptor']['svgSha256']+'.svg')).read_bytes() for i in ('remix.settings-3-line','remix.download-line')}
        fixed=lambda w,h:{'width':{'mode':'fixed','value':w},'height':{'mode':'fixed','value':h}}
        text=lambda identifier,value,width:dict(id=identifier,type='Text',text=value,sourceIds=['slot-case'],layout=fixed(width,22),style={'typographyToken':{'token':'typography.body'},'colorToken':{'token':'color.text'}})
        self.slots={
            'leading-icon':[dict(id='slot-leading',type='IconInstance',iconId='remix.settings-3-line',sourceIds=['slot-case'],layout=fixed(24,24))],
            'label':[text('slot-label','姓名',28)],
            'control':[dict(id='slot-control',type='ComponentInstance',componentId='form.input.default.medium',variant='default',sourceIds=['slot-case'],layout=fixed(240,32))],
            'trailing-icon':[dict(id='slot-trailing',type='IconInstance',iconId='remix.download-line',sourceIds=['slot-case'],layout=fixed(24,24))],
            'content':[text('slot-content','用户列表',56)],
            'actions':[dict(id='slot-action',type='ComponentInstance',componentId='action.button.primary.medium',variant='default',sourceIds=['slot-case'],layout=fixed(60,32))]}
        self.box=dict(x=24,y=24,width=1392,height=32)

    def compose(self):
        return layout.compose('slot-cell',self.box,'slot-case',self.slots,self.geometry,self.registry,self.icons,self.tokens,
                              ['姓名、请输入姓名、用户列表、查询、设置图标、下载图标'],self.icon_sources)

    def test_all_roles_use_real_registry_components_and_keep_cell_envelope(self):
        before=copy.deepcopy((self.slots,self.box));cell=self.compose()
        self.assertEqual(cell['id'],'slot-cell');self.assertEqual(cell['layout']['width']['value'],1392)
        self.assertEqual(len(cell['children']),6)
        self.assertEqual(cell['children'][2]['children'][0]['layout']['width']['value'],240)
        self.assertEqual((self.slots,self.box),before)

    def test_overflow_stretch_source_text_and_icon_tampering_rejected(self):
        for mutate in (lambda:self.box.update(width=400),lambda:self.box.update(height=24),
                       lambda:self.slots['control'][0]['layout']['width'].update(value=241),
                       lambda:self.slots['label'][0].update(text='invented'),
                       lambda:self.icon_sources.update({'remix.settings-3-line':b'changed'}),
                       lambda:self.slots['label'][0].update(type='IconInstance')):
            self.setUp();mutate()
            with self.assertRaises((ValueError,KeyError)):self.compose()
