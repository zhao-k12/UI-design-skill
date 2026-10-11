"""Unadmitted mixed-font Table source plans; platform references stay in adapters."""
from importlib import import_module
from pathlib import Path
from hashlib import sha256
import json
import re
from validators.ui_ir import ROOT, load_json
from validators.component_ir import verify_artifacts
from validators.visual.fidelity import file_hash
from adapters.penpot.component_candidate import px, color

def require(condition, message):
    if not condition: raise ValueError(message)

def prepare_source(directory):
    directory=Path(directory)
    require(not verify_artifacts(directory,expected_types={'Table'}),'invalid_table_reference')
    bundle=load_json(directory/'component_ir.json');require(len(bundle['components'])==1,'ambiguous_table_fixture')
    source=bundle['components'][0];request=load_json(directory/'request.json');receipt=load_json(directory/'configurable-source.json')
    observation=load_json(directory/'table-observation.json')
    require(receipt['status']=='PASS' and receipt['productionAdmission'] is False and receipt['fidelityGate']=='NOT_RUN','source_is_not_unadmitted_extraction')
    require(receipt['requestFileSha256']==file_hash(directory/'request.json') and receipt['componentIrSha256']==file_hash(directory/'component_ir.json') and receipt['observationSha256']==file_hash(directory/'table-observation.json'),'table_source_binding_mismatch')
    require(receipt['scriptSha256']==file_hash(directory/'source-extractor.mjs'),'table_extractor_binding_mismatch')
    digest=sha256(json.dumps(request,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
    require(digest==receipt['requestSha256'] and source['logicalComponentId']=='data.table.config.'+digest,'table_request_identity_mismatch')
    require(source['props']['columns']==request['columns'] and source['props']['data']==request['records'] and source['rootBounds']['width']==request['containerWidth'],'table_request_props_mismatch')
    catalog=load_json(ROOT/'registries/components/catalog.json')
    require(source['provenance']['sourceVersion']==catalog['sourceVersion'],'table_source_version_mismatch')
    require(observation['status']=='PASS' and observation['scope']=='official_table_runtime_supplement' and observation['referenceComponentIrSha256']==file_hash(directory/'component_ir.json') and observation['environment']==source['environment'] and observation['provenance']==source['provenance'],'table_observation_binding_mismatch')
    require(all(source['props'][k] is False for k in ('showHeader','border','stripe')),'unsupported_table_variant')
    visible=[n for n in source['nodes'] if n['visible']];rows=[];cursor=0
    count=len(request['columns'])*len(request['records'])
    require(len(observation['baselines'])==len(observation['fonts'])==count,'table_observation_inventory_mismatch')
    for tr in [n for n in visible if n['tag']=='tr']:
        cells=[]
        for cell in [n for n in visible if n['parentPath']==tr['path'] and n['tag']=='td']:
            texts=[n for n in visible if n['path'].startswith(cell['path']+'.') and n['textRuns']]
            require(len(texts)==1 and len(texts[0]['textRuns'])==1,'unsupported_table_cell_content')
            text=texts[0];run=text['textRuns'][0];baseline=observation['baselines'][cursor];fonts=[f for f in observation['fonts'][cursor] if f['glyphCount']];cursor+=1
            require(len(fonts)==1 and (fonts[0]['familyName'],fonts[0]['postScriptName']) in (('Arial','ArialMT'),('PingFang SC','PingFangSC-Regular')),'unsupported_table_cell_font')
            require(run['text']==baseline['characters'] and run['bounds']==baseline['range'] and baseline['restored'] is True,'table_text_baseline_mismatch')
            typ=text['computedStyle'];style=cell['computedStyle']
            require(typ['font-size']=='14px' and typ['font-weight']=='400' and typ['line-height']=='21px' and typ['font-style']=='normal','unsupported_table_typography')
            require(typ['display']=='inline' and typ['width']=='auto' and typ['height']=='auto','unsupported_table_text_sizing')
            for node in (tr,cell,text):
                state=node['computedStyle'];require(state['opacity']=='1' and state['transform']=='none' and state['box-shadow']=='none','unsupported_table_render_state')
            require(style['border-bottom-style']=='solid' and all(style['border-'+side+'-width']=='0px' for side in ('top','right','left')),'unsupported_table_cell_border')
            cells.append({'path':cell['path'],'bounds':cell['bounds'],'fill':color(style['background-color']),
                'text':{'path':text['path'],'characters':run['text'],'sourceTextBounds':run['bounds'],'sourceSizing':{'display':'inline','width':'auto','height':'auto'},'fontSize':14,'fontWeight':400,'fontFamily':fonts[0]['familyName'],'postScriptName':fonts[0]['postScriptName'],'fill':color(typ['color']),'sourceBaselineY':baseline['baselineComponentY']},
                'bottomBorder':{'height':px(style['border-bottom-width']),'fill':color(style['border-bottom-color'])}})
        require(len(cells)==len(request['columns']) and sum(c['bounds']['width'] for c in cells)==tr['bounds']['width'],'unsupported_table_row_geometry')
        require(all(c['bottomBorder']==cells[0]['bottomBorder'] for c in cells),'nonuniform_table_row_border')
        rows.append({'path':tr['path'],'bounds':tr['bounds'],'cells':cells,'bottomBorder':cells[0]['bottomBorder']})
    require(cursor==count and len(rows)==len(request['records']),'table_row_inventory_mismatch')
    require([[c['text']['characters'] for c in row['cells']] for row in rows]==[[record[c['key']] for c in request['columns']] for record in request['records']],'table_visible_records_mismatch')
    css=ROOT/'node_modules/view-ui-plus/dist/styles/viewuiplus.css';require(file_hash(css)==source['provenance']['officialCssSha256'],'table_css_changed')
    rule=re.search(r'\.ivu-table:before\{([^{}]+)\}',css.read_text(encoding='utf-8'));require(rule is not None,'table_pseudo_rule_missing')
    declarations=dict(item.split(':',1) for item in rule[1].split(';') if item)
    require(all(declarations.get(k)==v for k,v in {'left':'0','bottom':'0','height':'1px','width':'100%','position':'absolute'}.items()),'unsupported_table_pseudo_geometry')
    pseudo=next(n for n in visible if n['path']=='0.0')['pseudoElements']['::before']
    container=next(n for n in visible if n['path']=='0.0')
    require(container['bounds']=={'x':0,'y':0,**source['rootBounds']} and container['computedStyle']['opacity']=='1' and container['computedStyle']['transform']=='none' and container['computedStyle']['box-shadow']=='none','unsupported_table_container_background')
    root_fill=color(container['computedStyle']['background-color'])
    return {'logicalId':source['logicalComponentId'],'sourceVersion':catalog['sourceVersion'],
        'componentIrSha256':import_module('core.component-resolver.registry').digest(source),'rootBounds':source['rootBounds'],'rootFill':root_fill,'rootFillSourcePath':'0.0','rows':rows,
        'sourceObservationSha256':file_hash(directory/'table-observation.json'),'requiredFonts':sorted({c['text']['fontFamily'] for r in rows for c in r['cells']}),
        'bottomPseudo':{'height':px(pseudo['height']),'width':px(pseudo['width']),'fill':color(pseudo['background-color']),'sourceCssRule':rule[0]},
        'admissionEligible':False,'fidelityGate':'NOT_RUN'}

def prepare_penpot(directory,file_reference,page_reference):
    plan=prepare_source(directory)
    return {**plan,'fileReference':file_reference,'pageReference':page_reference,'name':'candidate/'+plan['logicalId']+'/penpot-v1'}
