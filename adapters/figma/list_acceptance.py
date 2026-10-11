"""TASK-009 acceptance of a fixed native list, independent readback and PNGs."""
import base64
import hashlib
from io import BytesIO
import json
from PIL import Image
from pathlib import Path
from adapters.figma.qa import validate_native_evidence
from adapters.figma.native_capture import verify_saved_capture
from adapters.figma.cross_renderer_normalization import require
from validators.ui_ir import ROOT,load_json
from validators.visual.fidelity import digest,file_hash


def run(metadata,page_directory):
    metadata=Path(metadata);page_directory=Path(page_directory)
    plan=load_json(page_directory/'adapter_preflight_report.json')['plan']
    assembly=load_json(metadata/'list-acceptance-native-evidence.json')
    independent=load_json(metadata/'list-independent-readback.json');identity=load_json(metadata/'list-file-identity.json')
    icons=load_json(metadata/'icon-bindings.json');contract=validate_native_evidence(plan,assembly,icons)
    require(contract['status']=='PASS','assembly_contract_not_passed')
    require(identity['status']=='PASS' and identity['fileReference']==plan['fileReference'] and identity['pageReference']==identity['parentPageReference']==assembly['pageReference'] and identity['rootReference']==assembly['rootReference'] and identity['rootType']=='FRAME','page_identity_mismatch')
    require(independent['status']=='PASS' and independent['createdNodeIds']==independent['mutatedNodeIds']==[] and independent['pageReference']==assembly['pageReference'] and independent['rootReference']==assembly['rootReference'],'invalid_independent_readback')
    observed={r['uiIrId']:r for r in independent['evidence']};require(len(observed)==len(independent['evidence'])==contract['logicalNodes'],'independent_inventory_mismatch')
    root=observed['acceptance-page']['absoluteBounds']
    for recorded in assembly['evidence']:
        actual=observed[recorded['uiIrId']]
        for key,value in recorded.items():
            if key=='namedStyleFontWeight':continue
            require(actual.get(key)==value,'independent_property_mismatch:'+recorded['uiIrId']+':'+key)
        box=actual['absoluteBounds'];require(box is not None and box['x']>=root['x'] and box['y']>=root['y'] and box['x']+box['width']<=root['x']+root['width'] and box['y']+box['height']<=root['y']+root['height'],'logical_node_overflows_page')
    reports=load_json(ROOT/'registries/components/fidelity-reports.json');catalog=load_json(ROOT/'registries/components/catalog.json')
    require(plan['componentsSha256']==digest(catalog),'registry_migration_invalidates_page')
    require({r['componentType'] for r in reports.values()}=={'Button','Input','Select','Table'} and all(r['status']=='PASS' and r['admissionEligible'] is True and r['scope']=='production' for r in reports.values()),'missing_component_fidelity')
    captures={'12:8':metadata/'render-state-captures/form.input.default.medium','12:15':metadata/'render-state-captures/form.select.default.medium','18:5':metadata/'render-state-captures/action.button.primary.medium','28:3':metadata/'table-native-capture-v2'}
    rasters=load_json(metadata/'list-instance-pngs.json')
    require(rasters['status']=='PASS' and rasters['scope']=='figma_independent_instance_png' and rasters['fileReference']==plan['fileReference'] and rasters['pageReference']==assembly['pageReference'] and rasters['scale']==1 and rasters['format']=='PNG' and rasters['createdNodeIds']==rasters['mutatedNodeIds']==[],'invalid_instance_raster_capture')
    require(len(rasters['observations'])==4 and {r['mainComponentReference'] for r in rasters['observations']}==set(captures),'instance_raster_inventory_mismatch')
    comparisons=[]
    for row in rasters['observations']:
        actual=next(r for r in observed.values() if r['nodeId']==row['instanceReference'])
        require(actual['type']=='INSTANCE' and actual['mainComponentReference']==row['mainComponentReference'],'flattened_or_wrong_instance')
        require(actual['editableTextCount']>0,'component_text_not_editable')
        directory=captures[row['mainComponentReference']];require(verify_saved_capture(directory)['status']=='PASS','admitted_capture_changed')
        raw=base64.b64decode(row['base64'],validate=True);require(hashlib.sha256(raw).hexdigest()==row['pngSha256']==file_hash(directory/'native.png'),'instance_pixels_changed_after_assembly')
        with Image.open(BytesIO(raw)) as image,Image.open(directory/'native.png') as master:
            image,master=image.convert('RGBA'),master.convert('RGBA');require(image.size==master.size==(row['width'],row['height']) and image.tobytes()==master.tobytes(),'instance_decoded_pixels_mismatch')
        comparisons.append({'instanceReference':row['instanceReference'],'mainComponentReference':row['mainComponentReference'],'status':'PASS','changedPixels':0,'pngSha256':row['pngSha256']})
    png=load_json(page_directory/'native-page-png.json');page_png=page_directory/'native-page.png'
    require(png['scope']=='figma_native_page_png' and png['status']=='PASS' and png['scale']==1 and png['fileReference']==plan['fileReference'] and png['pageReference']==assembly['pageReference'] and png['rootReference']==assembly['rootReference'] and png['createdNodeIds']==png['mutatedNodeIds']==[] and png['pngSha256']==file_hash(page_png),'invalid_native_page_png')
    with Image.open(page_png) as image:require(image.format=='PNG' and image.size==(root['width'],root['height'])==(png['width'],png['height']),'native_page_screenshot_size_mismatch')
    return {'scope':'task009_figma_native_list_acceptance','task':'TASK-009','status':'PASS','fullTaskAcceptance':'PASS',
        'fileReference':plan['fileReference'],'pageReference':assembly['pageReference'],'rootReference':assembly['rootReference'],
        'uiIrSha256':plan['uiIrSha256'],'componentsSha256':plan['componentsSha256'],'logicalNodes':contract['logicalNodes'],'nativeInstances':contract['instanceCount'],
        'componentTypes':['Button','Input','Select','Table'],'instanceRasterComparisons':comparisons,
        'nativePagePngSha256':file_hash(page_png),'screenshotDimensions':[png['width'],png['height']],
        'inputHashes':{name:file_hash(metadata/name) for name in ('list-acceptance-native-evidence.json','list-independent-readback.json','list-file-identity.json','list-instance-pngs.json')},
        'issues':[],'limits':['Fixed static fixture; admitted source content is unchanged.','Table is the official showHeader=false body variant; column labels belong to UI-IR.','Other planned component types, arbitrary props/slots and Penpot release acceptance remain separate tasks.']}


if __name__=='__main__':
    directory=ROOT/'artifacts/task-009/list-acceptance';target=directory/'task009-final-qa.json'
    target.write_text('{"status":"RUNNING"}\n',encoding='utf-8')
    try:report=run(ROOT/'adapters/figma/metadata',directory)
    except Exception as exc:report={'task':'TASK-009','status':'FAIL','issues':[{'code':type(exc).__name__,'detail':str(exc)}]}
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':report['status'],'issues':report['issues'],'nativeInstances':report.get('nativeInstances')},ensure_ascii=False));raise SystemExit(0 if report['status']=='PASS' else 1)
