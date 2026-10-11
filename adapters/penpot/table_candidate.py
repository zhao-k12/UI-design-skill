"""Lock a static Table plan to official browser evidence, without native offsets."""
from pathlib import Path
import re
from importlib import import_module
from validators.ui_ir import ROOT,load_json
from validators.component_ir import verify_artifacts
from validators.visual.fidelity import file_hash
from adapters.penpot.component_candidate import px,color


def require(condition,reason):
    if not condition:raise ValueError(reason)


def prepare_table_candidate(reference_directory,file_reference,page_reference):
    directory=Path(reference_directory)
    require(not verify_artifacts(directory,expected_types={'Table'}),'invalid_table_reference')
    bundle=load_json(directory/'component_ir.json');require(len(bundle['components'])==1,'ambiguous_table_fixture')
    source=bundle['components'][0];logical='data.table.default'
    catalog=load_json(ROOT/'registries/components/catalog.json');digest=import_module('core.component-resolver.registry').digest
    require(source['logicalComponentId']==logical and digest(source)==catalog['components'][logical]['fidelity']['componentIrSha256'] and source['provenance']['sourceVersion']==catalog['sourceVersion'],'table_source_mismatch')
    observation_path=directory/'table-observation.json'
    require(file_hash(observation_path)=='63ede3fc28f5016dbbfc7d6b6478491658b0133046e3d9ce0c0f2b3bc9cc093e','table_observation_changed')
    observation=load_json(observation_path)
    require(observation['status']=='PASS' and observation['scope']=='official_table_runtime_supplement' and observation['referenceComponentIrSha256']==file_hash(directory/'component_ir.json') and observation['environment']==source['environment'] and observation['provenance']==source['provenance'],'table_observation_binding_mismatch')
    require(source['props']['showHeader'] is False and source['props']['border'] is False and source['props']['stripe'] is False,'unsupported_table_variant')
    visible=[n for n in source['nodes'] if n['visible']];rows=[];cursor=0
    for tr in [n for n in visible if n['tag']=='tr']:
        cells=[]
        for cell in [n for n in visible if n['parentPath']==tr['path'] and n['tag']=='td']:
            texts=[n for n in visible if n['path'].startswith(cell['path']+'.') and n['textRuns']]
            require(len(texts)==1 and len(texts[0]['textRuns'])==1,'unsupported_table_cell_content')
            text=texts[0];run=text['textRuns'][0];baseline=observation['baselines'][cursor];fonts=observation['fonts'][cursor];cursor+=1
            require(run['text']==baseline['characters'] and run['bounds']==baseline['range'] and baseline['restored'] is True,'table_text_baseline_mismatch')
            require(all(f['familyName']=='PingFang SC' and f['postScriptName']=='PingFangSC-Regular' for f in fonts if f['glyphCount']),'table_source_font_mismatch')
            typ=text['computedStyle'];style=cell['computedStyle']
            require(typ['font-size']=='14px' and typ['font-weight']=='400' and typ['line-height']=='21px' and typ['font-style']=='normal','unsupported_table_typography')
            for node in (tr,cell,text):
                state=node['computedStyle'];require(state['opacity']=='1' and state['transform']=='none' and state['box-shadow']=='none','unsupported_table_render_state')
            require(style['border-bottom-style']=='solid' and all(style['border-'+side+'-width']=='0px' for side in ('top','right','left')),'unsupported_table_cell_border')
            cells.append({'path':cell['path'],'bounds':cell['bounds'],'fill':color(style['background-color']),
                'text':{'path':text['path'],'characters':run['text'],'sourceTextBounds':run['bounds'],'fontSize':14,'fontWeight':400,'fill':color(typ['color']),'sourceBaselineY':baseline['baselineComponentY']},
                'bottomBorder':{'height':px(style['border-bottom-width']),'fill':color(style['border-bottom-color'])}})
        require(len(cells)==3 and sum(c['bounds']['width'] for c in cells)==tr['bounds']['width'],'unsupported_table_row_geometry')
        require(all(c['bottomBorder']==cells[0]['bottomBorder'] for c in cells),'nonuniform_table_row_border')
        rows.append({'path':tr['path'],'bounds':tr['bounds'],'cells':cells,'bottomBorder':cells[0]['bottomBorder']})
    require(cursor==9 and len(rows)==3 and len(observation['fonts'])==9,'unsupported_table_inventory')
    css=ROOT/'node_modules/view-ui-plus/dist/styles/viewuiplus.css'
    require(file_hash(css)==source['provenance']['officialCssSha256'],'table_css_changed')
    rule=re.search(r'\.ivu-table:before\{([^{}]+)\}',css.read_text(encoding='utf-8'));require(rule is not None,'table_pseudo_rule_missing')
    declarations=dict(item.split(':',1) for item in rule[1].split(';') if item)
    require(all(declarations.get(k)==v for k,v in {'left':'0','bottom':'0','height':'1px','width':'100%','position':'absolute'}.items()),'unsupported_table_pseudo_geometry')
    pseudo=next(n for n in visible if n['path']=='0.0')['pseudoElements']['::before']
    return {'fileReference':file_reference,'pageReference':page_reference,'logicalId':logical,'name':'candidate/'+logical+'/penpot-v1',
        'sourceVersion':catalog['sourceVersion'],'componentIrSha256':digest(source),'rootBounds':source['rootBounds'],'rows':rows,
        'fontFamily':'PingFang SC','fontWeight':400,'sourceObservationSha256':file_hash(observation_path),
        'bottomPseudo':{'height':px(pseudo['height']),'width':px(pseudo['width']),'fill':color(pseudo['background-color']),'sourceCssRule':rule[0]},
        'nativeBaselineCalibration':'NOT_RUN','fidelityGate':'NOT_RUN'}
