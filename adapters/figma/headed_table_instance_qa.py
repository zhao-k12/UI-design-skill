"""Actual linked instance equality; IDs and root placement alone may differ."""
import hashlib
from adapters.headed_table import require
from validators.ui_ir import ROOT
META=ROOT/'adapters/figma/metadata/headed-table-native'
from validators.ui_ir import load_json


def validate(receipt,case):
    expected=load_json(META/(case+'-readback.json'))['nativeEvidence']
    main=receipt['mainNativeEvidence'];instance=receipt['instanceNativeCapture']
    require(receipt['status']=='PASS' and receipt['fileReference']=='0vGWSRoLxBiVPXiZ8xJAX9' and receipt['pageReference']=='82:2' and not receipt['createdNodeIds'] and not receipt['mutatedNodeIds'],'instance_readback_context')
    require(main==expected and receipt['mainReference']==main['rootReference'] and receipt['instanceReference']==instance['nativeEvidence']['rootReference'] and instance['status']=='PASS','instance_source_binding')
    a=main['nodes'];b=instance['nativeEvidence']['nodes'];require(len(a)==len(b),'instance_node_inventory')
    mapping={x['reference']:y['reference'] for x,y in zip(a,b)};require(len(set(mapping.values()))==len(b),'instance_duplicate_node')
    for i,(x,y) in enumerate(zip(a,b)):
        require(y['parentReference']==mapping.get(x['parentReference']) and y['type']==('INSTANCE' if i==0 else x['type']) and y['properties']==x['properties'] and (i==0 or x['name']==y['name']),'instance_content_style_or_link')
        for key in ('absoluteBounds','localBounds'):
            if i==0 and key=='localBounds':
                require((x[key]['width'],x[key]['height'])==(y[key]['width'],y[key]['height']),'instance_root_size');continue
            origin_a=a[0]['absoluteBounds'] if key=='absoluteBounds' else {'x':0,'y':0}
            origin_b=b[0]['absoluteBounds'] if key=='absoluteBounds' else {'x':0,'y':0}
            require({**x[key],'x':x[key]['x']-origin_a['x'],'y':x[key]['y']-origin_a['y']}=={**y[key],'x':y[key]['x']-origin_b['x'],'y':y[key]['y']-origin_b['y']},'instance_geometry')
    png=bytes(instance['raster']['bytes']);expected_png=(META/(case+'-native.png')).read_bytes()
    require(png==expected_png and receipt['mainPngSha256']==hashlib.sha256(png).hexdigest(),'instance_native_png_mismatch')
    return {'status':'PASS','mainReference':receipt['mainReference'],'instanceReference':receipt['instanceReference'],'nativeNodeCount':len(b),'mainUnchanged':True,'nativePngBytesEqual':True,'nativePngSha256':hashlib.sha256(png).hexdigest()}
