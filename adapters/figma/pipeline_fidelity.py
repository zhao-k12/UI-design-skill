"""Verify six final native instances against the byte-bound admitted sources."""
import base64
from hashlib import sha256
import json
from pathlib import Path
from io import BytesIO
from PIL import Image
from adapters.figma.native_capture import verify_saved_capture
from validators.visual.cross_renderer import edge_band,glyph_retention
from validators.visual.fidelity import digest
from validators.ui_ir import ROOT


def verify(plan,execution,capture,packet,current_sources):
    def need(ok,code):
        if not ok:raise ValueError(code)
    need(packet['status']=='PASS' and packet['createdNodeIds']==packet['mutatedNodeIds']==[],'instances_not_readonly_complete')
    for k in ('fileReference','pageReference','rootReference','uiIrSha256'):need(packet[k]==execution[k],'instances_context_mismatch')
    specs={}
    def walk(n):
        if n.get('componentReference'):specs[n['id']]=n
        for c in n.get('children',[]):walk(c)
    walk(plan['pages'][0]);need({n['uiIrId'] for n in packet['observations']}==set(specs) and len(packet['observations'])==len(specs),'instances_inventory_mismatch')
    metadata=ROOT/'adapters/figma/metadata'
    sources={'12:8':metadata/'render-state-captures/form.input.default.medium','12:15':metadata/'render-state-captures/form.select.default.medium','18:5':metadata/'render-state-captures/action.button.primary.medium','28:3':metadata/'table-native-capture-v2'}
    imported=json.loads((metadata/'icon-import-evidence.json').read_bytes());bindings=json.loads((metadata/'icon-bindings.json').read_bytes());results=[]
    outlines={}
    for name in ('native-text-outline-capture.json','native-text-outline-after-baseline-revision.json','native-current-text-outline.json','table-text-outline.json'):
        outlines.update({n['textReference']:n for n in json.loads((metadata/name).read_bytes())['observations']})
    proofs=json.loads((metadata/'fidelity-proof-bundles.json').read_bytes())
    need(current_sources['status']=='PASS' and current_sources['createdNodeIds']==current_sources['mutatedNodeIds']==[],'current_source_capture_missing')
    native={n['id']:n for n in capture['nodes']}
    for row in packet['observations']:
        spec=specs[row['uiIrId']];n=native[row['instanceReference']]
        need(n['type']=='INSTANCE' and n['component']==row['mainReference']==spec['componentReference'] and row['instanceReference']==execution['nodeMap'][spec['id']],'instance_not_genuine_admitted_copy')
        png=base64.b64decode(row['nativePngBase64'],validate=True);need(png==base64.b64decode(row['mainPngBase64'],validate=True),'instance_png_differs_from_current_master')
        if spec['type']=='ComponentInstance':
            source=sources[row['mainReference']];need(verify_saved_capture(source)['status']=='PASS','admitted_source_capture_changed')
            current=next(s for s in current_sources['sources'] if s['componentReference']==row['mainReference'])
            historical=json.loads((source/'native-evidence.json').read_bytes());observed=current['nativeEvidence']
            need(len(historical['nodes'])==len(observed['nodes']),'current_source_inventory_changed')
            for old,new in zip(historical['nodes'],observed['nodes']):
                for key,value in old.items():
                    if key=='properties':
                        need(all(new['properties'].get(k)==v for k,v in value.items()),'current_source_style_changed')
                        extra=set(new['properties'])-set(value)
                        need(extra<=set(('strokeTopWeight','strokeRightWeight','strokeBottomWeight','strokeLeftWeight')) and all(new['properties'][k]==value['strokeWeight'] for k in extra),'current_source_new_render_property')
                    else:need(new.get(key)==value,'current_source_geometry_changed')
            need(len(current['textOutlines'])==sum(n['type']=='TEXT' for n in historical['nodes']),'current_source_glyph_inventory_changed')
            for glyph in current['textOutlines']:
                old=outlines[glyph['reference']];need(glyph['characters']==old['characters'] and glyph['svg']==old['svg'],'current_source_glyph_outline_changed')
            need(png==base64.b64decode(current['nativePngBase64'],validate=True) and row['editableTextCount']>0,'instance_differs_from_independently_captured_source')
            logical=current['logicalId'];policy_dir=metadata/'pipeline-acceptance/source-edge-policy';policy=json.loads((policy_dir/(logical+'.json')).read_bytes());vector=policy_dir/(logical+'.vector.png')
            need(policy['capture']['proofBundleSha256']==digest(proofs[logical]) and policy['vectorRasterSha256']==sha256(vector.read_bytes()).hexdigest(),'historical_edge_proof_binding_changed')
            def white(image):
                image=image.convert('RGBA');background=Image.new('RGBA',image.size,'white');background.alpha_composite(image);return background
            a=white(Image.open(source/'native.png'));b=white(Image.open(BytesIO(png)));v=Image.open(vector).convert('RGBA')
            need(a.size==b.size==v.size,'source_raster_dimensions_changed');band=edge_band(v)
            permitted=[s['region'] for s in policy['glyphPaintSamples']]+policy['allowedCornerRegions'];changed=outside=unpermitted=0
            for y in range(a.height):
                for x in range(a.width):
                    if a.getpixel((x,y))!=b.getpixel((x,y)):
                        changed+=1;outside+=(x,y) not in band;unpermitted+=not any(r['x']<=x+.5<r['x']+r['width'] and r['y']<=y+.5<r['y']+r['height'] for r in permitted)
            retention=glyph_retention(a,b,policy['glyphPaintSamples'])
            need(outside==unpermitted==0 and all(r['status']=='PASS' for r in retention),'historical_native_raster_difference_outside_approved_edges')
            results.append({'uiIrId':spec['id'],'status':'PASS','admittedNativePngBytesExact':png==(source/'native.png').read_bytes(),'currentSourceNativePngBytesExact':True,'admittedSourceGeometryStyleAndGlyphOutlinesExact':True,'historicalChangedPixels':changed,'outsideVerifiedEdges':outside,'outsidePermittedTextOrCorners':unpermitted,'glyphRetention':retention,'editableTextCount':row['editableTextCount'],'nativePngSha256':sha256(png).hexdigest()})
        else:
            icon_id=next(k for k,v in bindings['bindings'].items() if v['componentReference']==row['mainReference'])
            need(bindings['registrySha256']==plan['iconsSha256']==imported['registrySha256'],'icon_registry_mismatch')
            master=next(m for m in imported['masters'] if m['componentReference']==row['mainReference'])
            need(row['vectorPaths']==row['mainVectorPaths']==[c['vectorPaths'] for c in master['vectorEvidence'] if c['type']=='VECTOR'],'icon_vector_source_changed')
            need(master['svgSha256']==bindings['bindings'][icon_id]['svgSha256']==spec['svgSha256'],'icon_source_svg_changed')
            results.append({'uiIrId':spec['id'],'iconId':icon_id,'status':'PASS','importedSourceVectorPathsExact':True,'currentMasterNativePngBytesExact':True,'nativePngSha256':sha256(png).hexdigest()})
    return {'scope':'figma-static-pipeline-instance-fidelity','status':'PASS','uiIrSha256':plan['uiIrSha256'],'instances':results,'issues':[]}
