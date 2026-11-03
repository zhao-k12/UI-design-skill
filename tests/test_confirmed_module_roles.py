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
from confirmed_modules import sidebar, topbar, breadcrumb, search_panel, table_panel, page_shell, action_column, project_logo, light_tag


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


def test_confirmed_header_default_is_overridable():
    default=topbar('header')
    user=default['children'][1]['children'][-1]
    assert user['children'][0]['name']=='default-avatar'
    assert user['children'][1]['value']=='钱多多'
    assert topbar('other',username=None)['children'][1]['children'][-1]['designRole']=='topbar-tool'


def test_light_tag_uses_official_palette_and_rejects_other_values():
    assert light_tag('tag','标签')['props']['color']=='blue'
    assert light_tag('tag','标签',color='green')['props']['color']=='green'
    with pytest.raises(ValueError,match='unsupported_light_tag_color'):
        light_tag('tag','标签',color='primary')


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
    fields[-1]={'label':label+'日期','component':'DatePicker','props':{'type':'daterange','placeholder':'请选择日期'}}
    logo_path=source.parent/'project.svg'
    logo_path.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 20"><rect width="40" height="20" fill="#36a"/></svg>',encoding='utf-8')
    project_brand=project_logo('custom-brand',logo_path) if field_count==3 else None
    menu=sidebar('side', [{'name':'closed','label':'其他','icon':'apps-line','expandable':True},
                         {'name':'group','label':label+'管理','icon':'settings-3-line','children':[{'name':'list','label':label+'列表'}]},
                         {'name':'leaf','label':'独立入口','icon':'apps-line'}],
                 active_name='leaf' if field_count==2 else 'list', open_names=['group'], brand_node=project_brand)
    header=topbar('header',username='测试用户')
    query=search_panel('search',fields)
    columns=[{'title':'编号','key':'id'}, {'title':'名称','key':'name'},
             {'title':'备注','key':'remark'}, action_column('actions')]
    rows=[{'id':'A-1','name':label+'项目','remark':'可用','actions':[{'label':'详情','icon':'eye-line','tone':''},
                                  {'label':'删除','icon':'delete-bin-line','tone':'danger'}]},
          {'id':'A-2','name':label+'测试','remark':'示例备注内容','actions':[{'label':'详情','icon':'eye-line','tone':''}]}]
    if field_count==2:
        rows[0]['actions']=rows[0]['actions'][:1]
    table=table_panel('result',columns,rows,
                      tabs=[{'name':'all','label':'全部','count':12}] if with_tabs else None,
                      active_tab='all' if with_tabs else None,
                      buttons=[{'label':'新增','icon':'add-large-line','primary':True}],
                      page={'modelValue':1,'pageSize':10,'total':100,'showSizer':True})
    crumb=breadcrumb('crumb',[label+'管理',label+'列表'])
    content={'sourceSha256':sha,'icons':['eye-line','delete-bin-line'],'root':page_shell('region',sidebar_node=menu,topbar_node=header,
             breadcrumb_node=crumb,sections=[query,table],source_ids=['region'])}
    result=compile_tree(source,content,observation,scan)
    assert result['ui_ir']['requiredAssets']==(['default-avatar'] if field_count==3 else ['default-avatar','default-logo'])
    with tempfile.TemporaryDirectory(prefix='confirmed-build-test-',dir=ROOT/'artifacts') as tmp:
        tmp=Path(tmp);core=tmp/'core';core.mkdir()
        ir=core/'ui_ir.json';ir.write_text(json.dumps(result['ui_ir'],ensure_ascii=False),encoding='utf-8')
        qa=result['qa_report'];qa['uiIrSha256']=hashlib.sha256(ir.read_bytes()).hexdigest()
        (core/'qa_report.json').write_text(json.dumps(qa,ensure_ascii=False),encoding='utf-8')
        subprocess.run(['node',str(ROOT/'scripts/export_html_composition.mjs'),str(core),str(tmp/'html'),'1600','900'],
                       cwd=ROOT,check=True,capture_output=True,text=True,encoding='utf-8',timeout=180)
        code='''const {chromium}=require('playwright');(async()=>{const b=await chromium.launch();
        const p=await b.newPage({viewport:{width:1600,height:900}});await p.goto(process.argv[1]);
        let actual=await p.evaluate(()=>{let l=document.querySelector('[data-component=asset]');
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
        let lastHeader=document.querySelector('.ivu-table-header th:last-child .ivu-table-cell>span').getBoundingClientRect();
        let rowCells=[...bodyRows[0].querySelectorAll('td')];
        let rowOffsets=rowCells.map(td=>{let box=td.getBoundingClientRect(),cell=td.querySelector('.ivu-table-cell').getBoundingClientRect();return ((box.top+box.bottom)-(cell.top+cell.bottom))/2});
        let tab=document.querySelector('.ivu-tabs-tab');
        let date=document.querySelector('[data-component=DatePicker]');
        let dateIcon=date.querySelector('.ivu-input-suffix .ivu-icon');
        let menuArrows=[...document.querySelectorAll('.ivu-menu-submenu-title-icon')].map(e=>e.getBoundingClientRect().right);
        let toolbar=document.querySelector('[data-design-role=table-toolbar]');
        let btn=toolbar.querySelector('button'),btnR=btn.getBoundingClientRect(),btnI=btn.querySelector('.remix-custom').getBoundingClientRect();
        let pageWrap=pg.parentElement.getBoundingClientRect(),panel=t;
        return {logo:l.getBoundingClientRect().height,logoLoaded:l.complete&&l.naturalWidth>0,fieldCount:fields.length,
        crumbTop:c.top-h.bottom,searchTop:q.top-h.bottom,tableGap:t.top-q.bottom,
        prevMask:getComputedStyle(prev).maskImage,downMask:getComputedStyle(down).maskImage,
        downOffset:(arrow.top+arrow.bottom-box.top-box.bottom)/2,
        actionCounts:actionRows.map(r=>r.length),actionGap:actions[1]?actions[1].left-actions[0].right:null,
        dangerColor:actionRows[0][1]?getComputedStyle(actionRows[0][1]).color:null,
        actionRight:document.querySelector('.ivu-table-body table').getBoundingClientRect().right-actions.at(-1).right,
        tableHeader:headerCell.height,tableRows:bodyRows.map(r=>r.getBoundingClientRect().height),
        columnWidths:[...document.querySelectorAll('.ivu-table-header th')].map(e=>e.getBoundingClientRect().width),
        rowColors:bodyRows.map(r=>getComputedStyle(r.querySelector('td')).backgroundColor),
        tabHeight:tab?.getBoundingClientRect().height||null,
        actionTop:a.top,firstRowTop:fields[0].top,lastRowTop:fields.at(-1).top,
        dateWidth:date.getBoundingClientRect().width,fieldWidth:document.querySelector('[data-design-role=search-field] .ivu-input-wrapper').getBoundingClientRect().width,
        dateMask:getComputedStyle(dateIcon).maskImage,dateBefore:getComputedStyle(dateIcon,'::before').content,
        menuArrows,toolbarBorder:getComputedStyle(toolbar).borderBottomWidth,buttonIconWidth:btnI.width,
        activeIconColor:document.querySelector('.ivu-menu-item-active .remix-custom')?getComputedStyle(document.querySelector('.ivu-menu-item-active .remix-custom')).color:null,
        buttonCenter:((btnI.top+btnI.bottom)-(btnR.top+btnR.bottom))/2,rowOffsets,
        actionHeaderOffset:((lastHeader.left+lastHeader.right)-(actions[0].left+actions.at(-1).right))/2,
        pagerRight:panel.right-pageWrap.right,
        tabs:document.querySelectorAll('[data-component=Tabs]').length,
        badge:document.querySelector('[data-design-role=tab-count]')?.innerText||null,text:document.body.innerText}});
        let leaf=p.locator('[data-tree-node=side-entry-2]'),initial=await leaf.evaluate(e=>[getComputedStyle(e).color,getComputedStyle(e).backgroundColor]),r=await leaf.boundingBox();await p.mouse.move(r.x+r.width/2,r.y+r.height/2);let after=await leaf.evaluate(e=>[getComputedStyle(e).color,getComputedStyle(e).backgroundColor]);
        await p.setViewportSize({width:2400,height:900});let wide=await p.evaluate(()=>{let panel=document.querySelector('[data-component=Table]').getBoundingClientRect(),table=document.querySelector('.ivu-table-body table').getBoundingClientRect();return {panel:panel.width,table:table.width}});
        await p.setViewportSize({width:500,height:900});let tr=await p.locator('[data-component=Table] .ivu-table').boundingBox();await p.mouse.move(tr.x+Math.min(50,tr.width/2),tr.y+20);await p.mouse.wheel(120,0);await p.waitForTimeout(100);let narrow=await p.evaluate(()=>{let t=document.querySelector('[data-component=Table] .ivu-table');return {overflow:t.scrollWidth>t.clientWidth,scroll:t.scrollLeft,header:document.querySelector('.ivu-table-header table').getBoundingClientRect().left,body:document.querySelector('.ivu-table-body table').getBoundingClientRect().left}});
        console.log(JSON.stringify({...actual,wide,narrow,initial,after}));await b.close()})()'''
        out=subprocess.run(['node','-e',code,(tmp/'html/page.html').as_uri()],cwd=ROOT,check=True,
                           capture_output=True,text=True,encoding='utf-8',timeout=60)
        actual=json.loads(out.stdout)
        assert actual['logo']==32 and actual['logoLoaded']
        assert actual['fieldCount']==field_count and label in actual['text']
        assert (actual['crumbTop'],actual['searchTop'],actual['tableGap'])==(12,44,16)
        assert actual['prevMask'].startswith('url(') and actual['downMask'].startswith('url(')
        assert actual['dateMask'].startswith('url(') and actual['dateBefore']=='none'
        assert actual['initial']==actual['after']
        if field_count==2: assert actual['activeIconColor']=='rgb(45, 140, 240)'
        assert abs(actual['dateWidth']-actual['fieldWidth']) <= 1
        assert abs(actual['wide']['table']-actual['wide']['panel']) <= 2
        assert actual['narrow']['overflow'] and actual['narrow']['scroll'] > 0
        assert abs(actual['narrow']['header']-actual['narrow']['body']) <= 1
        assert len(actual['menuArrows'])==2 and abs(actual['menuArrows'][0]-actual['menuArrows'][1]) <= 1
        assert actual['toolbarBorder']==('1px' if with_tabs else '0px')
        assert abs(actual['buttonCenter']) <= 1 and actual['pagerRight']==16
        assert actual['buttonIconWidth']==14
        assert max(map(abs, actual['rowOffsets'])) <= 1 and abs(actual['actionHeaderOffset']) <= 1
        assert abs(actual['downOffset']) <= 1
        assert actual['actionCounts']==([1,1] if field_count==2 else [2,1])
        assert abs(actual['actionRight']-(32 if field_count==2 else 18)) <= 1
        if field_count!=2:
            assert actual['actionGap']==16 and actual['dangerColor']=='rgb(237, 64, 20)'
        assert actual['tableHeader']==40 and actual['tableRows']==[48,48]
        sizing=json.loads((tmp/'html/qa.json').read_text(encoding='utf-8'))['layoutSizing'][0]
        assert 'equalGap' in sizing
        extras=[width-col['measuredMinimum'] for width,col in zip(actual['columnWidths'],sizing['columns'])]
        assert max(extras[:-1])-min(extras[:-1]) <= 2
        assert actual['rowColors'][1]=='rgb(248, 248, 249)'
        assert actual['tabHeight']==(37 if with_tabs else None)
        assert actual['tabs']==int(with_tabs)
        assert actual['badge']==('12' if with_tabs else None)
        assert (actual['actionTop'] > actual['lastRowTop']) if field_count==4 else (actual['actionTop']==actual['firstRowTop'])
    content['root'].update(kind='text', value='x', designRole='sidebar')
    with pytest.raises(ValueError, match='unsupported_design_role'):
        compile_tree(source, content, observation, scan)
