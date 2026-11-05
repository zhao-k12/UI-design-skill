import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from confirmed_modules import summary_panel, steps_panel, module_panel, form_section, light_tag


def test_summary_owns_meta_spacing_and_copies_content():
    tag = light_tag('status', '待处理')
    metadata = [{'id':'meta-value','kind':'text','value':'显式内容'}]
    node = summary_panel('summary', '任务标题', tag_node=tag, metadata=metadata)
    assert [n['designRole'] for n in node['children']] == ['summary-heading','module-close','summary-meta']
    assert node['children'][0]['children'][0]['layout']['direction'] == 'horizontal'
    metadata[0]['value'] = 'changed'
    assert node['children'][2]['children'][0]['value'] == '显式内容'
    assert node['children'][1]['children'][0]['name'] == 'close-line'


def test_independent_modules_and_fluid_form_have_no_extra_wrapper():
    steps = {'id':'official-steps','kind':'component','component':'Steps','children':[]}
    node = steps_panel('progress', steps)
    assert node['designRole'] == 'steps-panel'
    assert node['children'][0]['designRole'] == 'progress-steps'
    assert 'designRole' not in steps
    assert module_panel('module', [])['designRole'] == 'module-panel'
    field = {'id':'field','kind':'component','component':'FormItem','props':{'label':'名称'}}
    form = form_section('form', '资料', [field], columns='auto')
    grid = form['children'][1]['children'][0]
    assert grid['designRole'] == 'form-grid-fluid'
    assert grid['children'] == [field]
