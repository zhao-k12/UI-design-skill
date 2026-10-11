"""Independent before/after native-readback verification of local content patches."""
import base64
from hashlib import sha256
from io import BytesIO
import math
from PIL import Image, ImageChops


def verify(execution, patch, before, after, *, expected_content=None, visual_review=None):
    issues=[]
    def require(condition, message):
        if not condition:issues.append(message)
    for capture in (before,after):
        require(capture.get('status')=='CAPTURED' and capture.get('scope')=='penpot-native-section-patch-capture', 'not an independent native capture')
        for field in ('fileReference','pageReference','rootReference'):
            require(capture.get(field)==execution.get(field),'capture context mismatch: '+field)
    require(patch.get('status')=='PATCHED','patch was not executed')
    for field in ('fileReference','pageReference','rootReference'):
        require(patch.get(field)==execution.get(field),'patch context mismatch: '+field)
    require(patch.get('before')==before.get('nodes'),'before execution snapshot differs from independent capture')
    require(patch.get('after')==after.get('nodes'),'after execution snapshot differs from independent capture')
    require(patch.get('createdNodeIds')==[] and patch.get('removedNodeIds')==[],'patch created or deleted nodes')
    require(patch.get('beforeRevision')==before.get('fileRevision'),'stale before capture')
    require(type(patch.get('afterRevision')) is int and type(after.get('fileRevision')) is int and
            after['fileRevision']>=patch['afterRevision'],'stale after capture')
    require(isinstance(patch.get('changedSections'),list) and bool(patch['changedSections']), 'missing changed Sections')
    old={n['id']:n for n in before.get('nodes',[])}
    new={n['id']:n for n in after.get('nodes',[])}
    require(len(old)==len(before.get('nodes',[])) and len(new)==len(after.get('nodes',[])), 'duplicate native IDs')
    require(list(old)==list(new),'native IDs/order changed')
    copies=patch.get('patchedCopyIds',[])
    require(isinstance(copies,list) and bool(copies) and len(set(copies))==len(copies),'missing or duplicate patched copies')
    changed=[]
    for copy_id in copies:
        a,b=old.get(copy_id,{}),new.get(copy_id,{})
        require(a.get('isCopy') is True and b.get('isCopy') is True and not a.get('isMain') and not b.get('isMain'),'not genuine linked copies')
        require(a==b,'component root/link/style/position changed')
    for identifier,a in old.items():
        b=new.get(identifier,{})
        if a==b:continue
        parent=identifier;visited=set()
        while parent not in copies and parent in old and parent not in visited:
            visited.add(parent);parent=old[parent].get('parent')
        require(parent in copies,'unrelated native node changed')
        require(a.get('type')=='text' and b.get('type')=='text','non-text component descendant changed')
        allowed={'characters','x','y','width','height'}
        require({k:v for k,v in a.items() if k not in allowed}=={k:v for k,v in b.items() if k not in allowed},'text font/style/topology changed')
        require(a.get('characters')!=b.get('characters') and bool(b.get('characters')),'missing changed text content')
        changed.append(identifier)
    require(bool(changed),'patch did not change any text')
    require(isinstance(expected_content,dict) and bool(expected_content),'expected compiled content bindings required')
    if isinstance(expected_content,dict):
        expected_copy_ids=[]
        for ui_ir_id,spec in expected_content.items():
            copy_id=execution.get('nodeMap',{}).get(ui_ir_id)
            expected_copy_ids.append(copy_id)
            require(new.get(copy_id,{}).get('component')==spec.get('componentReference'),'compiled component reference mismatch')
            for mapping in spec.get('nativeContent',[]):
                found=[]
                for node in new.values():
                    parent=node.get('parent');visited=set()
                    while parent!=copy_id and parent in new and parent not in visited:
                        visited.add(parent);parent=new[parent].get('parent')
                    if parent==copy_id and node.get('type')=='text' and node.get('name')==mapping['name']:found.append(node)
                require(len(found)==1,'compiled content target is missing or ambiguous')
                if len(found)==1:
                    require(found[0].get('characters')==mapping['text'],'injected native text differs from source payload')
                    require(all(found[0].get(key)==value for key,value in mapping['style'].items()),'native text differs from admitted source style')
        require(set(expected_copy_ids)==set(copies),'patched copies differ from compiled requests')
    png_hash=None
    try:
        raw=base64.b64decode(after['nativePngBase64'],validate=True)
        with Image.open(BytesIO(raw)) as im:
            im.load();require(im.format=='PNG','native export is not PNG')
            root=new[execution['rootReference']]
            require(im.size==(round(root['width']),round(root['height'])),'native PNG dimensions mismatch')
            require(len(im.convert('RGB').getcolors(maxcolors=2) or [])!=1,'empty native PNG')
            old_raw=base64.b64decode(before['nativePngBase64'],validate=True)
            with Image.open(BytesIO(old_raw)) as old_image:
                old_image.load();require(old_image.size==im.size,'before/after PNG dimensions differ')
                if old_image.size==im.size:
                    diff=ImageChops.difference(old_image.convert('RGBA'),im.convert('RGBA')).convert('RGB')
                    for copy_id in copies:
                        box=old[copy_id]
                        region=(math.floor(box['x']-root['x']),math.floor(box['y']-root['y']),
                                math.ceil(box['x']+box['width']-root['x']),math.ceil(box['y']+box['height']-root['y']))
                        diff.paste((0,0,0),region)
                    require(diff.getbbox() is None,'native PNG changed outside patched copy bounds')
        png_hash=sha256(raw).hexdigest()
    except (ValueError,KeyError,OSError,TypeError) as exc:issues.append('invalid native PNG: '+str(exc))
    reviewed=(isinstance(visual_review,dict) and visual_review.get('status')=='PASS' and
              visual_review.get('nativePngSha256')==png_hash and bool(visual_review.get('reviewedBy')))
    return {'scope':'native-section-content-patch-qa','status':'FAIL' if issues else 'PASS' if reviewed else 'Review',
            'nativeStructure':'FAIL' if issues else 'PASS','visualReview':'PASS' if reviewed else 'Review',
            'nativePngSha256':png_hash,'changedTextIds':changed,'unchangedNativeNodeCount':sum(old[k]==new.get(k) for k in old),
            'issues':issues,'fullTask015Acceptance':False}
