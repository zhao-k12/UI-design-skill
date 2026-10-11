"""Independent complete native capture comparison for Figma text updates."""
import base64
import hashlib
from io import BytesIO
import json
import math
from PIL import Image, ImageChops


def digest(nodes):
    return hashlib.sha256(json.dumps(nodes,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def verify(execution,patch,before,after,request,*,visual_review=None,platform='figma'):
    issues=[]
    def require(condition,message):
        if not condition:issues.append(message)
    for record in (patch,before,after):
        require(all(record.get(k)==execution.get(k) for k in ('fileReference','pageReference','rootReference')),'native context mismatch')
    require(patch.get('status')=='PATCHED','content patch was not executed')
    require(before.get('status')==after.get('status')=='CAPTURED','independent captures required')
    require(platform in ('figma','penpot'),'unsupported native platform')
    if platform=='figma':
        require(patch.get('beforeSha256')==digest(before.get('nodes',[])) and patch.get('afterSha256')==digest(after.get('nodes',[])),'capture differs from execution snapshot hash')
    else:
        require(patch.get('before')==before.get('nodes') and patch.get('after')==after.get('nodes'),'capture differs from execution snapshots')
        require(patch.get('beforeRevision')==before.get('fileRevision'),'stale before capture')
        require(type(after.get('fileRevision')) is int and type(patch.get('afterRevision')) is int and after['fileRevision']>=patch['afterRevision'],'stale after capture')
    old={n['id']:n for n in before.get('nodes',[])};new={n['id']:n for n in after.get('nodes',[])}
    require(len(old)==len(before.get('nodes',[])) and len(new)==len(after.get('nodes',[])) and list(old)==list(new),'native identity/order changed')
    targets=request.get('targets',[]);ids=[t['textReference'] for t in targets]
    require(bool(ids) and len(set(ids))==len(ids) and set(ids)==set(patch.get('mutatedNodeIds',[])),'content mutation ledger mismatch')
    require(patch.get('createdNodeIds')==[] and patch.get('removedNodeIds')==[],'content update created or removed nodes')
    require(set(t['sectionReference'] for t in targets)==set(patch.get('changedSections',[])),'changed Section ledger mismatch')
    for identifier,n in old.items():
        if identifier not in ids:require(n==new.get(identifier),'unrelated native node changed')
    for target in targets:
        a=old.get(target['textReference'],{});b=new.get(target['textReference'],{});owner=new.get(target['ownerReference'],{})
        require(a.get('type')==b.get('type')==('TEXT' if platform=='figma' else 'text') and a.get('name')==b.get('name')==target['name'],'content target identity mismatch')
        require(a.get('characters')==target['expectedText'] and b.get('characters')==target['text'],'content does not match source request')
        permitted={'characters','x','y','width','height'}
        require({k:v for k,v in a.items() if k not in permitted}=={k:v for k,v in b.items() if k not in permitted},'content font/style/topology changed')
        require(all(b.get(k)==v for k,v in target['style'].items()),'native content differs from declared source style')
        if target.get('componentReference'):
            genuine=owner.get('type')=='INSTANCE' if platform=='figma' else owner.get('isCopy') is True and not owner.get('isMain')
            require(genuine and owner.get('component')==target['componentReference'],'content owner is not the declared genuine instance')
        require(owner.get('id') in execution.get('createdNodeIds',[]),'content owner is not in owned ledger')
    png_hash=None
    try:
        raw=base64.b64decode(after['nativePngBase64'],validate=True);old_raw=base64.b64decode(before['nativePngBase64'],validate=True)
        with Image.open(BytesIO(raw)) as im,Image.open(BytesIO(old_raw)) as prior:
            im.load();prior.load();root=new[execution['rootReference']]
            require(im.format==prior.format=='PNG' and im.size==prior.size==(round(root['width']),round(root['height'])),'incomplete native PNG')
            require(im.convert('RGB').getcolors(maxcolors=2) is None,'empty native PNG')
            diff=ImageChops.difference(im.convert('RGB'),prior.convert('RGB'));require(diff.getbbox() is not None,'no changed native pixels')
            for t in targets:
                if t.get('componentReference'):box=new[t['ownerReference']]
                else:
                    a=old[t['textReference']];b=new[t['textReference']]
                    box=dict(x=min(a['x'],b['x']),y=min(a['y'],b['y']),width=max(a['x']+a['width'],b['x']+b['width'])-min(a['x'],b['x']),height=max(a['y']+a['height'],b['y']+b['height'])-min(a['y'],b['y']))
                region=(math.floor(box['x']-root['x']),math.floor(box['y']-root['y']),math.ceil(box['x']+box['width']-root['x']),math.ceil(box['y']+box['height']-root['y']))
                diff.paste((0,0,0),region)
            require(diff.getbbox() is None,'native PNG changed outside explicit content bounds')
        png_hash=hashlib.sha256(raw).hexdigest()
    except (ValueError,KeyError,TypeError,OSError) as exc:issues.append('invalid native content PNG: '+str(exc))
    reviewed=isinstance(visual_review,dict) and visual_review.get('status')=='PASS' and visual_review.get('nativePngSha256')==png_hash and bool(visual_review.get('reviewedBy'))
    return {'scope':platform+'-native-section-content-qa','status':'FAIL' if issues else 'PASS' if reviewed else 'Review',
            'nativeStructure':'FAIL' if issues else 'PASS','visualReview':'PASS' if reviewed else 'Review',
            'nativePngSha256':png_hash,'unchangedNativeNodeCount':sum(old[k]==new.get(k) for k in old),
            'issues':issues,'fullTask015Acceptance':False}
