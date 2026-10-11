"""Strict source/path/paint/export evidence subcheck; not final icon admission."""
import base64
import hashlib
import io
import json
import xml.etree.ElementTree as ET
from PIL import Image,UnidentifiedImageError
from adapters.penpot.icon_precision import validate_approved_icon_encoding


def verify_icon_native_evidence(plan,receipt,probe,receipt_bytes):
    if json.loads(receipt_bytes)!=receipt:raise ValueError('icon_receipt_bytes_mismatch')
    native=receipt['result']
    if native.get('status')!='CAPTURED' or native.get('platform')!='penpot' or native.get('scope')!='production' or native.get('evidenceKind')!='native-platform-export' or native.get('createdNodeIds')!=[] or native.get('mutatedNodeIds')!=[]:
        raise ValueError('icon_native_capture_incomplete')
    for key in ('fileReference','pageReference','registrySha256','sourceVersion'):
        if native.get(key)!=plan.get(key):raise ValueError('icon_native_context_mismatch')
    if probe.get('nativeReceiptSha256')!=hashlib.sha256(receipt_bytes).hexdigest() or probe.get('completeNativeCapture') is not True:
        raise ValueError('icon_probe_not_bound_to_complete_capture')
    if len(native['icons'])!=2 or {i['iconId'] for i in native['icons']}!={i['iconId'] for i in plan['icons']}:
        raise ValueError('icon_native_inventory_mismatch')
    results=[]
    for source in plan['icons']:
        item=next(i for i in native['icons'] if i['iconId']==source['iconId'])
        observation=next(i for i in probe['observations'] if i['iconId']==source['iconId'])
        if item.get('status')!='CAPTURED' or item.get('exportIssues')!=[] or item.get('rasterScope') or item.get('svgSha256')!=source['svgSha256'] or observation.get('componentReference')!=item.get('componentReference'):
            raise ValueError('icon_native_export_identity_mismatch')
        nodes=item['nodes']
        if len(nodes)!=4 or len({n['reference'] for n in nodes})!=4 or [n['type'] for n in nodes]!=['board','group','rectangle','path']:
            raise ValueError('icon_native_node_inventory_mismatch')
        main,group,background,path=nodes
        if main['reference']!=item['mainReference'] or group['parentReference']!=main['reference'] or any(n['parentReference']!=group['reference'] for n in (background,path)):
            raise ValueError('icon_native_parent_mismatch')
        for n in nodes:
            if n['rotation']!=0 or n['flipX'] is not False or n['flipY'] is not False or n['blendMode']!='normal' or n['opacity'] not in (None,1) or n['strokes']!=[] or n['shadows']!=[] or n['blur'] is not None:
                raise ValueError('icon_native_effect_mismatch')
            hidden=n is background
            if n['hidden']!=hidden or n['visible']==hidden:raise ValueError('icon_native_visibility_mismatch')
        for n in (main,group,background):
            if [n[k] for k in ('x','y','width','height')]!=[0,0,24,24] or n['fills']!=[]:
                raise ValueError('icon_native_viewbox_mismatch')
        if len(path['fills'])!=1 or path['fills'][0].get('fillColor')!='#000000' or path['fills'][0].get('fillOpacity')!=1 or any(path['fills'][0].get(k) for k in ('fillColorGradient','fillImage','fillColorRefFile','fillColorRefId')):
            raise ValueError('icon_native_paint_mismatch')
        encoding=validate_approved_icon_encoding(source['iconId'],source['svg'].encode(),path['d'])
        svg=base64.b64decode(item['nativeSvgBase64'],validate=True)
        root=ET.fromstring(svg)
        if root.attrib.get('viewBox')!='0 0 24 24' or root.attrib.get('width')!='24' or root.attrib.get('height')!='24':raise ValueError('icon_svg_viewbox_mismatch')
        paths=list(root.iter('{http://www.w3.org/2000/svg}path'))
        if len(paths)!=1 or paths[0].attrib.get('d')!=path['d']:raise ValueError('icon_svg_path_mismatch')
        if observation['native']['svgSha256']!=hashlib.sha256(svg).hexdigest() or observation['source']['svgSha256']!=source['svgSha256'] or observation.get('sourceNativeVectorPngBytesEqual') is not True or observation['source']['pngSha256']!=observation['native']['pngSha256']:
            raise ValueError('icon_svg_source_reproduction_mismatch')
        for role in ('source','native'):
            rows=observation[role]['paths']
            if len(rows)!=1 or {k:rows[0].get(k) for k in ('fill','fillOpacity','opacity','transform','fillRule')}!={'fill':'rgb(0, 0, 0)','fillOpacity':'1','opacity':'1','transform':None,'fillRule':'nonzero'}:
                raise ValueError('icon_svg_paint_mismatch')
        png=base64.b64decode(item['nativePngBase64'],validate=True)
        try:
            with Image.open(io.BytesIO(png)) as im:
                im.load()
                if im.format!='PNG' or im.size!=(24,24):raise ValueError('icon_native_png_mismatch')
        except (UnidentifiedImageError,OSError) as exc:
            raise ValueError('icon_native_png_mismatch') from exc
        results.append({'iconId':source['iconId'],'componentReference':item['componentReference'],'mainReference':item['mainReference'],'encoding':encoding,'nativeSvgSha256':hashlib.sha256(svg).hexdigest(),'nativePngSha256':hashlib.sha256(png).hexdigest(),'sourceNativeVectorPngBytesEqual':True})
    return {'status':'PASS','scope':'native-icon-evidence-subcheck','nativeReceiptSha256':hashlib.sha256(receipt_bytes).hexdigest(),'results':results,'admissionEligible':False,'nativePngVisualAcceptance':'NOT_RUN','actualInstanceAcceptance':'NOT_RUN'}
