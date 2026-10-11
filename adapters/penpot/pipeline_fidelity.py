"""Full static-pipeline instance fidelity, retaining the approved source/edge rules."""
import base64
import hashlib
import io
import json
from pathlib import Path
from PIL import Image
from validators.ui_ir import ROOT
from adapters.penpot.page_final_qa import require,equal,translated_path_exact
from adapters.penpot.icon_admission import verify_binding
from adapters.penpot.icon_precision import validate_approved_icon_encoding
from adapters.penpot.icon_raster_diagnostic import observe_pixels

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
            icon_id=next(k for k,v in icons['bindings'].items() if v['componentReference']==spec['componentReference'])
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
