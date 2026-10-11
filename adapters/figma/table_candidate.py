"""Generate a bounded static Table candidate from official DOM/cell evidence."""
import json
import re
from pathlib import Path
from validators.ui_ir import ROOT,load_json
from validators.component_ir import verify_artifacts
from adapters.figma.font_outline_comparison import compare_font_files
from adapters.figma.cross_renderer_normalization import require
from validators.visual.fidelity import file_hash


def prepare(reference_directory,metadata_directory,*,file_reference,page_reference):
    directory=Path(reference_directory);metadata=Path(metadata_directory)
    require(not verify_artifacts(directory,expected_types={'Table'}),'invalid_table_reference')
    bundle=load_json(directory/'component_ir.json');require(len(bundle['components'])==1,'ambiguous_table_fixture')
    reference=bundle['components'][0];observation=load_json(directory/'table-observation.json')
    require(reference['componentType']=='Table' and reference['props']['showHeader'] is False,'unsupported_table_variant')
    require(observation['referenceComponentIrSha256']==file_hash(directory/'component_ir.json') and observation['environment']==reference['environment'] and observation['provenance']==reference['provenance'],'table_observation_binding_mismatch')
    require(len(observation['baselines'])==len(observation['fonts'])==9 and all(all(f['familyName']=='PingFang SC' and f['postScriptName']=='PingFangSC-Regular' for f in row if f['glyphCount']) for row in observation['fonts']),'table_font_unverified')
    current=load_json(metadata/'native-current-text-outline.json');identity=load_json(metadata/'font-file-identity.json')
    calibration=next(r for r in compare_font_files(current,identity)['observations'] if r['textReference']=='18:3')
    require(calibration['contourComparison']['nonzeroWinding']['status']=='PASS','table_baseline_calibration_unverified')
    offset=calibration['nativeSvg']['pathBoundsSvgCoordinates']['y']-calibration['source']['unshapedInkBoundsBaselineCoordinates']['y']
    query=next(r for r in current['observations'] if r['textReference']=='18:3')
    require(query['fontName']=={'family':'PingFang SC','style':'Regular'} and query['fontSize']==14 and query['fontWeight']==400 and query['lineHeight']=={'unit':'PIXELS','value':21},'unsupported_table_calibration_font')
    visible=[n for n in reference['nodes'] if n['visible']];rows=[];cursor=0
    for tr in [n for n in visible if n['tag']=='tr']:
        cells=[]
        for cell in [n for n in visible if n['parentPath']==tr['path'] and n['tag']=='td']:
            texts=[n for n in visible if n['path'].startswith(cell['path']+'.') and n['textRuns']]
            require(len(texts)==1 and len(texts[0]['textRuns'])==1,'unsupported_table_cell_content')
            text=texts[0];run=text['textRuns'][0];baseline=observation['baselines'][cursor];cursor+=1
            require(run['text']==baseline['characters'] and run['bounds']==baseline['range'] and baseline['restored'] is True,'table_text_baseline_mismatch')
            require(text['computedStyle']['font-size']=='14px' and text['computedStyle']['font-weight']=='400' and text['computedStyle']['line-height']=='21px','unsupported_table_typography')
            cells.append({'path':cell['path'],'bounds':cell['bounds'],'style':cell['computedStyle'],
                'text':{'path':text['path'],'characters':run['text'],'style':text['computedStyle'],
                    'width':run['bounds']['width'],'x':run['bounds']['x']-cell['bounds']['x'],
                    'y':baseline['baselineComponentY']-cell['bounds']['y']-offset}})
        rows.append({'path':tr['path'],'bounds':tr['bounds'],'cells':cells})
    require(cursor==9 and len(rows)==3 and all(len(row['cells'])==3 for row in rows),'unsupported_table_row_inventory')
    css_path=ROOT/'node_modules/view-ui-plus/dist/styles/viewuiplus.css'
    require(file_hash(css_path)==reference['provenance']['officialCssSha256'],'table_css_file_changed')
    rule=re.search(r'\.ivu-table:before\{([^{}]+)\}',css_path.read_text(encoding='utf-8'))
    require(rule is not None,'table_pseudo_rule_missing')
    declarations=dict(item.split(':',1) for item in rule[1].split(';') if item)
    require(declarations.get('left')=='0' and declarations.get('bottom')=='0' and declarations.get('height')=='1px' and declarations.get('width')=='100%' and declarations.get('position')=='absolute','unsupported_table_pseudo_geometry')
    pseudo=next(n for n in visible if n['path']=='0.0')['pseudoElements']['::before']
    for row in rows:
        styles=[c['style'] for c in row['cells']]
        require(all(s['border-bottom-style']=='solid' and all(s['border-'+side+'-width']=='0px' for side in ('top','right','left')) and s['border-bottom-color']==styles[0]['border-bottom-color'] and s['border-bottom-width']==styles[0]['border-bottom-width'] for s in styles),'nonuniform_table_row_border')
        require(sum(c['bounds']['width'] for c in row['cells'])==row['bounds']['width'],'noncontiguous_table_row_border')
        row['bottomBorder']={'height':float(styles[0]['border-bottom-width'][:-2]),'color':styles[0]['border-bottom-color']}
    request={'fileReference':file_reference,'pageReference':page_reference,'logicalId':reference['logicalComponentId'],
        'rootBounds':reference['rootBounds'],'rows':rows,'fontName':query['fontName'],'fontSize':14,'lineHeight':21,
        'referenceComponentIrSha256':file_hash(directory/'component_ir.json'),
        'calibrationCaptureSha256':file_hash(metadata/'native-current-text-outline.json'),'calibrationBaselineOffset':offset}
    request['bottomPseudo']={'height':float(pseudo['height'][:-2]),'width':float(pseudo['width'][:-2]),'color':pseudo['background-color'],'sourceCssRule':rule[0]}
    return request,(ROOT/'adapters/figma/table_candidate.js').read_text(encoding='utf-8')+'\nreturn await buildTableCandidate(figma,'+json.dumps(request,ensure_ascii=False,separators=(',',':'))+');\n'
