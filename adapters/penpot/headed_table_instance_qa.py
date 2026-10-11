"""Strict Penpot instance equality after normalizing only root translation/IDs."""
import base64
import hashlib
from adapters.headed_table import require
from validators.ui_ir import ROOT,load_json

META=ROOT/'adapters/penpot/metadata/headed-table-native'


def validate(receipt,case):
    require(receipt['status']=='CAPTURED','instance_receipt_status');r=receipt['result']
    old=load_json(META/'header-union'/('discovery-2.json' if case=='two-column' else 'discovery-3.json'))['result']
    require(r['status']=='CAPTURED' and r['scope']=='task020_penpot_instance_readback' and r['fileReference']==old['fileReference'] and r['pageReference']==old['pageReference'] and r['componentReference']==old['componentReference'] and r['mainReference']==old['mainReference'] and r['logicalId']==old['logicalId'] and not r['createdNodeIds'] and not r['mutatedNodeIds'],'instance_identity')
    main=r['mainNodes'];instance=r['instanceNodes'];require(main==old['nodes'],'instance_source_changed')
    require(len(main)==len(instance) and instance[0]['reference']==r['instanceReference'],'instance_inventory')
    mapping={a['reference']:b['reference'] for a,b in zip(main,instance)};require(len(set(mapping.values()))==len(instance),'instance_duplicate_nodes')
    def normalized(node,root):
        result={k:v for k,v in node.items() if k not in ('reference','parentReference')}
        if node is root:result.pop('name')
        result['x']-=root['x'];result['y']-=root['y']
        if isinstance(result.get('textBounds'),dict):
            bounds=result['textBounds'];result['textBounds']={**bounds,'x':bounds['x']-root['x'],'y':bounds['y']-root['y']}
        return result
    for i,(a,b) in enumerate(zip(main,instance)):
        require(b['parentReference']==(mapping[a['parentReference']] if i else a['parentReference']),'instance_parent')
        require(normalized(a,main[0])==normalized(b,instance[0]),'instance_geometry_content_style')
    expected=base64.b64decode(old['nativePngBase64'],validate=True)
    require(base64.b64decode(r['mainPngBase64'],validate=True)==base64.b64decode(r['instancePngBase64'],validate=True)==expected,'instance_png_changed')
    require(instance[0]['y']>=max(n['y']+n['height'] for n in main)+128,'instance_canvas_overlap')
    return {'status':'PASS','componentReference':r['componentReference'],'mainReference':r['mainReference'],'instanceReference':r['instanceReference'],'nativeNodeCount':len(instance),'mainUnchanged':True,'nativePngBytesEqual':True,'nativePngSha256':hashlib.sha256(expected).hexdigest()}
