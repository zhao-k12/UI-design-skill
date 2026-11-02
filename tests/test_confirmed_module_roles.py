import copy
import hashlib
from pathlib import Path
import sys
import json
import subprocess
import tempfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'core/pipeline'))
sys.path.insert(0, str(ROOT / 'scripts'))
from html_composition import compile_tree
from confirmed_modules import sidebar, topbar, breadcrumb, search_panel, table_panel, page_shell, action_column, project_logo


@pytest.fixture
def source_case(tmp_path):
    source = tmp_path / 'source.png'
    source.write_bytes(b'isolated prototype fixture')
    sha = hashlib.sha256(source.read_bytes()).hexdigest()
    traits = dict(leading='none', trailing='none', surface='plain', shape='rect', role='region')
    observation = {'sourceSha256': sha, 'items': [dict(id='region', region='body', traits=traits,
                    decision='include', sourceEvidence='fixture region', treeRef='region')]}
    scan = {'sourceSha256': sha, 'items': [dict(id='region', region='body', traits=copy.deepcopy(traits),
            visual='fixture region')]}
    return source, sha, observation, scan


@pytest.mark.parametrize('role,label', [('search-panel', '物料编号'), ('table-panel', '项目状态')])
def test_role_survives_compilation_without_business_defaults(source_case, role, label):
    source, sha, observation, scan = source_case
    content = {'sourceSha256': sha, 'root': {'id': 'region', 'kind': 'container',
               'designRole': role, 'sourceIds': ['region'],
               'children': [{'id': 'label', 'kind': 'text', 'value': label}]}}
    ir = compile_tree(source, content, observation, scan)['ui_ir']
    assert ir['root']['designRole'] == role
    assert ir['root']['children'][0]['value'] == label
    assert '风电场' not in str(ir['root'])


def test_unknown_or_non_container_role_is_rejected(source_case):
    source, sha, observation, scan = source_case
    content = {'sourceSha256': sha, 'root': {'id': 'region', 'kind': 'container',
               'designRole': 'invented', 'sourceIds': ['region']}}
    with pytest.raises(ValueError, match='unsupported_design_role'):
        compile_tree(source, content, observation, scan)


def test_equal_spacing_rejects_fixed_or_ambiguous_columns(source_case):
    source, sha, observation, scan = source_case
    table={'id':'region','kind':'component','component':'Table','sourceIds':['region'],
           'equalGapColumns':True,'props':{'columns':[{'title':'编号','key':'id','width':100}], 'data':[]}}
    with pytest.raises(ValueError, match='equal_gap_incompatible_with_fixed_columns'):
        compile_tree(source,{'sourceSha256':sha,'root':table},observation,scan)
    table['props']['columns']=[{'title':'编号','key':'id'},{'title':'名称','key':'id'}]
    with pytest.raises(ValueError, match='equal_gap_requires_unique_column_keys'):
        compile_tree(source,{'sourceSha256':sha,'root':table},observation,scan)


def test_selection_column_keeps_caller_width():
    panel=table_panel('results',[{'type':'selection','width':55},{'title':'编号','key':'id'}],[])
    table=next(node for node in panel['children'] if node.get('component')=='Table')
    assert table['equalGapColumns'] is False
    assert table['props']['columns'][0]['width']==55


def test_project_logo_rejects_external_svg_content(source_case):
    source, sha, observation, scan = source_case
    path=source.parent/'unsafe.svg'
    path.write_text('<svg xmlns="http://www.w3.org/2000/svg"><image href="https://example.com/x.png"/></svg>',encoding='utf-8')
    node=project_logo('region',path);node['sourceIds']=['region']
    with pytest.raises(ValueError,match='project_logo_svg_unsafe'):
        compile_tree(source,{'sourceSha256':sha,'root':node},observation,scan)


@pytest.mark.parametrize('label,with_tabs', [('库存编号', False), ('合同名称', True)])
def test_roles_render_in_real_exporter(source_case, label, with_tabs):
    source, sha, observation, scan = source_case
    sidebar = {'id': 'side', 'kind': 'container', 'designRole': 'sidebar', 'children': [
        {'id': 'menu', 'kind': 'component', 'component': 'Menu', 'props': {'theme': 'light'},
         'children': [{'id': 'item', 'kind': 'component', 'component': 'MenuItem',
                       'props': {'name': 'item'}, 'children': [{'id': 'menu-label', 'kind': 'text', 'value': label}]}]}]}
    panel_children = [{'id': 'search-label', 'kind': 'text', 'value': label},
                      {'id': 'search-input', 'kind': 'component', 'component': 'Input', 'props': {'placeholder': '请输入'}}]
    if with_tabs:
        panel_children.append({'id': 'tabs', 'kind': 'component', 'component': 'Tabs',
                               'children': [{'id': 'tab', 'kind': 'component', 'component': 'TabPane',
                                             'props': {'label': '全部', 'name': 'all'}}]})
    content = {'sourceSha256': sha, 'root': {'id': 'region', 'kind': 'container', 'designRole': 'page-shell',
               'sourceIds': ['region'], 'layout': {'direction': 'horizontal'}, 'children': [sidebar,
               {'id': 'main', 'kind': 'container', 'layout': {'fill': True}, 'children': [
                   {'id': 'header', 'kind': 'container', 'designRole': 'topbar'},
                   {'id': 'search', 'kind': 'container', 'designRole': 'search-panel', 'children': panel_children}]}]}}
    result = compile_tree(source, content, observation, scan)
    with tempfile.TemporaryDirectory(prefix='confirmed-module-test-', dir=ROOT / 'artifacts') as tmp:
        tmp = Path(tmp)
        core = tmp / 'core'
        core.mkdir()
        ir_path = core / 'ui_ir.json'
        ir_path.write_text(json.dumps(result['ui_ir'], ensure_ascii=False), encoding='utf-8')
        qa = result['qa_report']
        qa['uiIrSha256'] = hashlib.sha256(ir_path.read_bytes()).hexdigest()
        (core / 'qa_report.json').write_text(json.dumps(qa, ensure_ascii=False), encoding='utf-8')
        subprocess.run(['node', str(ROOT / 'scripts/export_html_composition.mjs'), str(core), str(tmp / 'html'), '1200', '800'],
                       cwd=ROOT, check=True, capture_output=True, text=True, timeout=180)
        page = (tmp / 'html/page.html').as_uri()
        code = '''const {chromium}=require('playwright');(async()=>{const b=await chromium.launch();
        const p=await b.newPage({viewport:{width:1200,height:800}});await p.goto(process.argv[1]);
        const r=await p.evaluate(()=>{let s=document.querySelector('[data-design-role=sidebar]').getBoundingClientRect();
        let h=document.querySelector('[data-design-role=topbar]').getBoundingClientRect();
        let i=document.querySelector('[data-design-role=search-panel] input').getBoundingClientRect();
        return {sidebar:s.width,header:h.height,input:i.height,text:document.body.innerText}});
        console.log(JSON.stringify(r));await b.close()})()'''
        output = subprocess.run(['node', '-e', code, page], cwd=ROOT, check=True,
                                capture_output=True, text=True, encoding='utf-8', timeout=60)
        actual = json.loads(output.stdout)
        assert (actual['sidebar'], actual['header'], actual['input']) == (256, 64, 34)
        assert label in actual['text']
        assert '风电场' not in actual['text']


@pytest.mark.parametrize('label,field_count,with_tabs', [('合同', 2, False), ('物料', 3, False), ('库存', 4, True)])
def test_module_builders_export_distinct_configurations(source_case, label, field_count, with_tabs):
    source, sha, observation, scan = source_case
    fields=[{'label':label+str(i), 'component':'Input', 'props':{'placeholder':'请输入'}} for i in range(field_count)]
    logo_path=source.parent/'project.svg'
    logo_path.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 20"><rect width="40" height="20" fill="#36a"/></svg>',encoding='utf-8')
    project_brand=project_logo('custom-brand',logo_path) if field_count==3 else None
    menu=sidebar('side', [{'name':'group','label':label+'管理','children':[{'name':'list','label':label+'列表'}]}],
                 active_name='list', open_names=['group'], brand_node=project_brand)
    header=topbar('header',username='测试用户')
    query=search_panel('search',fields)
    columns=[{'title':'编号','key':'id'}, {'title':'名称','key':'name'},
             {'title':'备注','key':'remark'}, action_column('actions')]
    rows=[{'id':'A-1','name':label+'项目','remark':'可用','actions':[{'label':'详情','icon':'eye-line','tone':''},
                                  {'label':'删除','icon':'delete-bin-line','tone':'danger'}]},
          {'id':'A-2','name':label+'测试','remark':'示例备注内容','actions':[{'label':'详情','icon':'eye-line','tone':''}]}]
    table=table_panel('result',columns,rows,
                      tabs=[{'name':'all','label':'全部','count':12}] if with_tabs else None,
                      active_tab='all' if with_tabs else None,
                      buttons=[{'label':'新增','icon':'add-line','primary':True}],
                      page={'modelValue':1,'pageSize':10,'total':100,'showSizer':True})
    crumb=breadcrumb('crumb',[label+'管理',label+'列表'])
    content={'sourceSha256':sha,'icons':['eye-line','delete-bin-line'],'root':page_shell('region',sidebar_node=menu,topbar_node=header,
             breadcrumb_node=crumb,sections=[query,table],source_ids=['region'])}
    result=compile_tree(source,content,observation,scan)
    assert result['ui_ir']['requiredAssets']==([] if field_count==3 else ['default-logo'])
    with tempfile.TemporaryDirectory(prefix='confirmed-build-test-',dir=ROOT/'artifacts') as tmp:
        tmp=Path(tmp);core=tmp/'core';core.mkdir()
        ir=core/'ui_ir.json';ir.write_text(json.dumps(result['ui_ir'],ensure_ascii=False),encoding='utf-8')
        qa=result['qa_report'];qa['uiIrSha256']=hashlib.sha256(ir.read_bytes()).hexdigest()
        (core/'qa_report.json').write_text(json.dumps(qa,ensure_ascii=False),encoding='utf-8')
        subprocess.run(['node',str(ROOT/'scripts/export_html_composition.mjs'),str(core),str(tmp/'html'),'1600','900'],
                       cwd=ROOT,check=True,capture_output=True,text=True,encoding='utf-8',timeout=180)
        code='''const {chromium}=require('playwright');(async()=>{const b=await chromium.launch();
        const p=await b.newPage({viewport:{width:1600,height:900}});await p.goto(process.argv[1]);
        console.log(JSON.stringify(await p.evaluate(()=>{let l=document.querySelector('[data-component=asset]');
        let a=document.querySelector('[data-design-role=search-actions]').getBoundingClientRect();
        let fields=[...document.querySelectorAll('[data-design-role=search-field]')].map(e=>e.getBoundingClientRect());
        let h=document.querySelector('[data-design-role=topbar]').getBoundingClientRect();
        let c=document.querySelector('[data-design-role=breadcrumb]').getBoundingClientRect();
        let q=document.querySelector('[data-design-role=search-panel]').getBoundingClientRect();
        let t=document.querySelector('[data-design-role=table-panel]').getBoundingClientRect();
        let pg=document.querySelector('[data-design-role=pagination]');
        let prev=pg.querySelector('.ivu-page-prev .ivu-icon');let down=pg.querySelector('.ivu-select-arrow');
        let box=down.closest('.ivu-select-selection').getBoundingClientRect(),arrow=down.getBoundingClientRect();
        let actionRows=[...document.querySelectorAll('.ivu-table-body tbody tr')].map(r=>[...r.querySelectorAll('[data-design-role=row-action]')]);
        let actions=actionRows[0].map(e=>e.getBoundingClientRect());
        let headerCell=document.querySelector('.ivu-table-header th').getBoundingClientRect();
        let bodyRows=[...document.querySelectorAll('.ivu-table-body tbody tr')];
        let tab=document.querySelector('.ivu-tabs-tab');
        return {logo:l.getBoundingClientRect().height,logoLoaded:l.complete&&l.naturalWidth>0,fieldCount:fields.length,
        crumbTop:c.top-h.bottom,searchTop:q.top-h.bottom,tableGap:t.top-q.bottom,
        prevMask:getComputedStyle(prev).maskImage,downMask:getComputedStyle(down).maskImage,
        downOffset:(arrow.top+arrow.bottom-box.top-box.bottom)/2,
        actionCounts:actionRows.map(r=>r.length),actionGap:actions[1].left-actions[0].right,
        dangerColor:getComputedStyle(actionRows[0][1]).color,
        tableHeader:headerCell.height,tableRows:bodyRows.map(r=>r.getBoundingClientRect().height),
        columnWidths:[...document.querySelectorAll('.ivu-table-header th')].map(e=>e.getBoundingClientRect().width),
        rowColors:bodyRows.map(r=>getComputedStyle(r.querySelector('td')).backgroundColor),
        tabHeight:tab?.getBoundingClientRect().height||null,
        actionTop:a.top,firstRowTop:fields[0].top,lastRowTop:fields.at(-1).top,
        tabs:document.querySelectorAll('[data-component=Tabs]').length,
        badge:document.querySelector('[data-design-role=tab-count]')?.innerText||null,text:document.body.innerText}})));await b.close()})()'''
        out=subprocess.run(['node','-e',code,(tmp/'html/page.html').as_uri()],cwd=ROOT,check=True,
                           capture_output=True,text=True,encoding='utf-8',timeout=60)
        actual=json.loads(out.stdout)
        assert actual['logo']==32 and actual['logoLoaded']
        assert actual['fieldCount']==field_count and label in actual['text']
        assert (actual['crumbTop'],actual['searchTop'],actual['tableGap'])==(12,44,16)
        assert actual['prevMask'].startswith('url(') and actual['downMask'].startswith('url(')
        assert abs(actual['downOffset']) <= 1
        assert actual['actionCounts']==[2,1] and actual['actionGap']==16
        assert actual['dangerColor']=='rgb(237, 64, 20)'
        assert actual['tableHeader']==40 and actual['tableRows']==[48,48]
        sizing=json.loads((tmp/'html/qa.json').read_text(encoding='utf-8'))['layoutSizing'][0]
        assert 'equalGap' in sizing
        extras=[width-col['measuredMinimum'] for width,col in zip(actual['columnWidths'],sizing['columns'])]
        assert max(extras)-min(extras) <= 2
        assert actual['rowColors'][1]=='rgb(248, 248, 249)'
        assert actual['tabHeight']==(37 if with_tabs else None)
        assert actual['tabs']==int(with_tabs)
        assert actual['badge']==('12' if with_tabs else None)
        assert (actual['actionTop'] > actual['lastRowTop']) if field_count==4 else (actual['actionTop']==actual['firstRowTop'])
    content['root'].update(kind='text', value='x', designRole='sidebar')
    with pytest.raises(ValueError, match='unsupported_design_role'):
        compile_tree(source, content, observation, scan)
