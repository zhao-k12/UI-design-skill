"""Source-bound fixed-page QA; never substitute a Figma pass for Penpot evidence."""
import base64
import hashlib
import io
import json
import math
import struct
from pathlib import Path
from PIL import Image
from fontTools.svgLib.path import parse_path
from fontTools.pens.recordingPen import RecordingPen
from validators.ui_ir import ROOT
from adapters.penpot.qa import validate_output
from adapters.penpot.icon_admission import verify_binding
from adapters.penpot.icon_precision import validate_approved_icon_encoding
from adapters.penpot.icon_raster_diagnostic import observe_pixels


def require(condition,reason):
    if not condition:raise ValueError(reason)


def equal(a,b):return type(a) in (int,float) and type(b) in (int,float) and math.isfinite(a) and math.isfinite(b) and abs(a-b)<=1e-6


def verify_flow(plan,capture):
    tree={r['nodeId']:r for r in capture['topology']};logical={r['uiIrId']:r for r in capture['evidence']}
    checks=[]
    def flow(parent,children,layout):
        direction=layout['direction'];main='x' if direction=='horizontal' else 'y';cross='y' if main=='x' else 'x';size='width' if main=='x' else 'height';cs='height' if size=='width' else 'width'
        p=layout['padding'];start=p['left' if main=='x' else 'top'];cstart=p['top' if cross=='y' else 'left'];cend=p['bottom' if cross=='y' else 'right'];cursor=parent[main]+start
        require(layout['alignment']['main']=='start' and not layout['wrap'],'fixed_page_flow_not_observed')
        for child in children:
            offset=cstart
            if layout['alignment']['cross']=='center':offset+=(parent[cs]-cstart-cend-child[cs])/2
            require(equal(child[main],cursor) and equal(child[cross],parent[cross]+offset),'native_flow_position_mismatch')
            cursor+=child[size]+layout['gap']
        checks.append(parent['nodeId'])
    helper=lambda direction,gap:{'direction':direction,'gap':gap,'wrap':False,'padding':dict.fromkeys(('top','right','bottom','left'),0),'alignment':{'main':'start','cross':'start'}}
    def walk(spec):
        if spec.get('children') and not spec.get('componentReference'):
            parent=tree[logical[spec['id']]['nodeId']];children=[tree[c] for c in parent['childNodeIds']]
            if spec['type']=='Grid':
                flow(parent,children,{**spec['layout'],'direction':'vertical'})
                for row in children:
                    cells=[tree[c] for c in row['childNodeIds']];flow(row,cells,helper('horizontal',spec['layout']['gap']))
                    for cell in cells:flow(cell,[tree[c] for c in cell['childNodeIds']],helper('vertical',0))
            else:flow(parent,children,spec['layout'])
        for child in spec.get('children',[]):walk(child)
    walk(plan['pages'][0]);return len(checks)


def translated_path_exact(main_d,instance_d,dx,dy):
    main,copy=RecordingPen(),RecordingPen();parse_path(main_d,main);parse_path(instance_d,copy)
    f32=lambda value:struct.unpack('f',struct.pack('f',value))[0]
    return [(op,tuple((f32(x+dx),f32(y+dy)) for x,y in points)) for op,points in main.value]==copy.value


def verify_instances(plan,execution,capture,packet,probe,base,previous):
    require(packet['status']=='CAPTURED' and packet['scope']=='production-native-instance-capture' and packet['createdNodeIds']==packet['mutatedNodeIds']==[],'instances_not_complete_native_capture')
    for key in ('fileReference','pageReference','rootReference'):require(packet[key]==execution[key],'instances_wrong_context')
    require(packet['fileRevision']==capture['fileRevision'],'instances_different_document_revision')
    specs={}
    def walk(n):
        if n.get('componentReference'):specs[n['id']]=n
        for child in n.get('children',[]):walk(child)
    walk(plan['pages'][0]);require(len(packet['instances'])==6 and {r['uiIrId'] for r in packet['instances']}==set(specs),'instances_inventory_mismatch')
    components=json.loads((ROOT/'adapters/penpot/metadata/native-fidelity.json').read_bytes());icons=json.loads((ROOT/'adapters/penpot/metadata/icon-bindings.json').read_bytes());source=json.loads((ROOT/'adapters/penpot/metadata/icon-source-plan/plan.json').read_bytes());results=[]
    for row in packet['instances']:
        spec=specs[row['uiIrId']]
        require(row['status']=='CAPTURED' and row['exportIssues']==[] and row['isComponentCopy'] is True and row['isComponentRoot'] is True and row['isRealMain'] is True and row['componentReference']==spec['componentReference'] and row['instanceReference']==execution['nodeMap'][spec['id']],'instance_not_real_admitted_copy')
        if row.get('reusedFormats'):
            for key in ('fileReference','pageReference','rootReference','fileRevision'):require(previous[key]==packet[key],'instance_reuse_wrong_context')
            old=next(r for r in previous['instances'] if r['uiIrId']==row['uiIrId'])
            require(old['mainNodes']==row['mainNodes'] and old['instanceNodes']==row['instanceNodes'],'instance_reuse_changed_geometry')
            for format in row['reusedFormats']:
                key={'png':'nativePngBase64','svg':'nativeSvgBase64'}[format];require(old[key]==row[key],'instance_reuse_changed_export')
        png=base64.b64decode(row['nativePngBase64'],validate=True);svg=base64.b64decode(row['nativeSvgBase64'],validate=True)
        require((base/(spec['id']+'.png')).read_bytes()==png and (base/(spec['id']+'.svg')).read_bytes()==svg,'instance_saved_export_changed')
        main,copy=row['mainNodes'],row['instanceNodes'];require(len(main)==len(copy),'instance_node_inventory_mismatch')
        require(main[0]['reference']==row['mainReference'] and copy[0]['reference']==row['instanceReference'],'instance_root_mismatch')
        dx,dy=copy[0]['x']-main[0]['x'],copy[0]['y']-main[0]['y']
        for i,(a,b) in enumerate(zip(main,copy)):
            for key in ('type','fills','strokes','opacity','rotation','flipX','flipY','hidden','visible','blendMode','shadows','blur','borderRadius','clipContent','characters','fontId','fontFamily','fontVariantId','fontWeight','fontStyle','fontSize','lineHeight','letterSpacing'):
                require(a.get(key)==b.get(key),'instance_style_font_or_content_mismatch')
            if i:
                parents={n['reference']:j for j,n in enumerate(main)};copies={n['reference']:j for j,n in enumerate(copy)}
                require(parents[a['parentReference']]==copies[b['parentReference']],'instance_parent_mismatch')
            if spec['type']!='IconInstance' or a['type']!='path':
                require(all(equal(a[k],b[k]) for k in ('width','height')) and equal(a['x']+dx,b['x']) and equal(a['y']+dy,b['y']),'instance_relative_geometry_mismatch')
        native_hash=hashlib.sha256(png).hexdigest()
        if spec['type']=='ComponentInstance':
            master=components[row['componentReference']];require(master['status']=='PASS' and master['nativeEvidence']['mainReference']==row['mainReference'],'instance_unadmitted_master')
            saved={n['reference']:n for n in master['nativeEvidence']['nodes']};require(set(saved)=={n['reference'] for n in main},'instance_master_inventory_changed')
            for n in main:
                for key,value in n.items():
                    if key in saved[n['reference']]:require(value==saved[n['reference']][key],'instance_master_observed_property_changed')
            require(native_hash==master['nativePngSha256'],'component_instance_png_differs_from_admitted_master')
            require(any(n.get('characters') for n in copy),'instance_text_not_editable')
            results.append({'uiIrId':spec['id'],'status':'PASS','masterNativePngBytesExact':True,'editableTextCount':sum(n['type']=='text' for n in copy)})
        else:
            icon_id='remix.settings-3-line' if spec['id']=='header.settings' else 'remix.download-line'
            binding=icons['bindings'][icon_id];verify_binding(icon_id,binding,plan['fileReference'],icons['registrySha256'])
            source_icon=next(i for i in source['icons'] if i['iconId']==icon_id)
            a=next(n for n in main if n['type']=='path');b=next(n for n in copy if n['type']=='path')
            validate_approved_icon_encoding(icon_id,source_icon['svg'].encode(),a['d'])
            require(translated_path_exact(a['d'],b['d'],dx,dy),'icon_instance_not_exact_master_affine_float32')
            obs=next(r for r in probe['observations'] if r['iconId']==icon_id)
            require(obs['native']['svgSha256']==hashlib.sha256(svg).hexdigest() and obs['sourceNativeVectorPngBytesEqual'] is True,'icon_instance_svg_source_mismatch')
            paths=[base/(icon_id+suffix) for suffix in ('.source.png','.native.png')]
            for path,role in zip(paths,('source','native')):require(hashlib.sha256(path.read_bytes()).hexdigest()==obs[role]['pngSha256'],'icon_instance_vector_raster_binding_mismatch')
            with Image.open(paths[0]) as s,Image.open(io.BytesIO(png)) as n,Image.open(paths[1]) as v:pixel=observe_pixels(s,n,v)
            require(pixel['proposedEvidenceConditionsMet'],'icon_instance_native_raster_failed')
            results.append({'uiIrId':spec['id'],'status':'PASS','exactMasterAffineFloat32':True,'sourceNativeVectorPngBytesExact':True,'nativeSourceChangedPixels':pixel['changedPixels'],'outsideVerifiedEdgeBand':pixel['changedPixelsOutsideVerifiedEdgeBand'],'nativePngSha256':native_hash})
    return results


def run(base):
    base=Path(base);read=lambda name:json.loads((base/name).read_bytes())
    plan=read('plan.json');execution=read('execution.json')['result'];capture=read('capture.json')['result'];packet=read('instances-capture.json')['result'];probe=read('icon-instance-svg-probe.json')
    from adapters.penpot.host.server import fixed_page_plan
    require(plan==fixed_page_plan(plan['fileReference']),'fixed_page_plan_source_changed')
    structural=validate_output(plan,execution,capture);require(structural['structuralStatus']=='PASS' and capture['exporterVersion']=='penpot-native-output-v0.1.1','fixed_page_structural_qa_failed')
    require(probe['nativeReceiptSha256']==hashlib.sha256((base/'instances-capture.json').read_bytes()).hexdigest() and probe['probeScriptSha256']==hashlib.sha256((ROOT/'adapters/penpot/icon_instance_svg_probe.mjs').read_bytes()).hexdigest(),'instance_svg_probe_receipt_mismatch')
    flow_count=verify_flow(plan,capture)
    rows=verify_instances(plan,execution,capture,packet,probe,base,read('partial-instances-capture-2.json')['result'])
    figma=json.loads((ROOT/'adapters/figma/metadata/list-acceptance-native-evidence.json').read_bytes());require(figma['uiIrSha256']==plan['uiIrSha256'],'cross_platform_ui_ir_mismatch')
    native={r['uiIrId']:r for r in capture['evidence']};require(set(native)=={r['uiIrId'] for r in figma['evidence']},'cross_platform_logical_inventory_mismatch')
    for f in figma['evidence']:
        p=native[f['uiIrId']];require(equal(f['width'],p['width']) and equal(f['height'],p['height']),'cross_platform_logical_size_mismatch')
        if 'characters' in f:require(f['characters']==p['characters'],'cross_platform_text_content_mismatch')
    png=base64.b64decode(capture['nativePngBase64'],validate=True);require((base/'native-page.png').read_bytes()==png,'page_png_saved_bytes_mismatch')
    review=read('visual-review.json');require(review['status']=='PASS' and review['nativePngSha256']==hashlib.sha256(png).hexdigest(),'page_visual_review_not_bound')
    return {'scope':'task010_penpot_fixed_list_acceptance','status':'PASS','fullTaskAcceptance':'PASS','task':'TASK-010','fileReference':execution['fileReference'],'pageReference':execution['pageReference'],'rootReference':execution['rootReference'],'uiIrSha256':plan['uiIrSha256'],'logicalNodes':len(native),'createdNodes':len(execution['createdNodeIds']),'nativeInstances':len(rows),'verifiedNativeFlowContainers':flow_count,'crossPlatformLogicalStructure':'PASS','nativePngSha256':hashlib.sha256(png).hexdigest(),'instanceChecks':rows,'visualInspection':review,'issues':[],'limits':['Fixed static UI-IR only; no TASK-011 or full release gate claimed.','Float32 scene coordinates and native icon raster edges use the explicitly approved source-bound rules.']}
