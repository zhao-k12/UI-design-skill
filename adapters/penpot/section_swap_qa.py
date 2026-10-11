"""Independent native snapshots and complete PNG verification for a component swap."""
import base64
from hashlib import sha256
from io import BytesIO
import math
from PIL import Image, ImageChops


def verify(execution, swap, before, after, *, expected_reference, reference_copy_id, visual_review=None):
    issues=[]
    def require(condition,message):
        if not condition:issues.append(message)
    for record in (swap,before,after):
        require(all(record.get(k)==execution.get(k) for k in ('fileReference','pageReference','rootReference')),'native context mismatch')
    require(swap.get('status')=='SWAPPED','swap was not executed successfully')
    require(before.get('status')==after.get('status')=='CAPTURED','independent captures required')
    require(swap.get('before')==before.get('nodes') and swap.get('after')==after.get('nodes'),'execution snapshots differ from independent captures')
    require(swap.get('beforeRevision')==before.get('fileRevision'),'stale before capture')
    require(type(after.get('fileRevision')) is int and type(swap.get('afterRevision')) is int and after['fileRevision']>=swap['afterRevision'],'stale after capture')
    old={n['id']:n for n in before.get('nodes',[])};new={n['id']:n for n in after.get('nodes',[])}
    require(len(old)==len(before.get('nodes',[])) and len(new)==len(after.get('nodes',[])),'duplicate native IDs')
    copy_id=swap.get('swappedCopyId');a=old.get(copy_id,{});b=new.get(copy_id,{})
    require(a.get('isCopy') is True and b.get('isCopy') is True and not a.get('isMain') and not b.get('isMain'),'genuine linked copies required')
    require(a.get('component')==swap.get('previousComponentReference') and b.get('component')==swap.get('componentReference')==expected_reference and a.get('component')!=b.get('component'),'component reference mismatch')
    for key in ('id','parent','name','x','y','width','height'):
        require(a.get(key)==b.get(key),'copy identity or world geometry changed: '+key)
    def subtree(nodes,identifier):
        found=[];visited=set()
        def walk(key):
            if key in visited or key not in nodes:raise ValueError('invalid native subtree')
            visited.add(key);n=nodes[key];found.append(n)
            for child in n.get('children',[]):
                if nodes.get(child,{}).get('parent')!=key:raise ValueError('native parent mismatch')
                walk(child)
        walk(identifier);return found
    unchanged=0;png_hash=None
    try:
        previous=subtree(old,copy_id);current=subtree(new,copy_id)
        old_ids={n['id'] for n in previous};new_ids={n['id'] for n in current}
        require([n for n in old.values() if n['id'] not in old_ids]==[n for n in new.values() if n['id'] not in new_ids],'unrelated native nodes changed')
        require(set(swap.get('createdNodeIds',[]))==new_ids-old_ids and set(swap.get('removedNodeIds',[]))==old_ids-new_ids,'descendant recovery ledger mismatch')
        reference=subtree(new,reference_copy_id)
        require(reference[0].get('component')==expected_reference and reference[0].get('isCopy') is True,'reference copy does not match admitted component')
        require(old.get(reference_copy_id)==new.get(reference_copy_id),'reference copy changed')
        def normalized(nodes):
            root=nodes[0];indices={n['id']:i for i,n in enumerate(nodes)};result=[]
            for i,n in enumerate(nodes):
                item={k:v for k,v in n.items() if k not in ('id','parent','children','x','y') and not (i==0 and k=='name')}
                item['x']=round(n['x']-root['x'],6);item['y']=round(n['y']-root['y'],6)
                item['parentIndex']=indices.get(n.get('parent'));item['childIndices']=[indices[k] for k in n.get('children',[])]
                result.append(item)
            return result
        require(normalized(current)==normalized(reference),'swapped geometry/content/fonts/styles differ from unchanged source-linked reference')
        require(bool(swap.get('sourceMasterBefore')) and swap.get('sourceMasterBefore')==swap.get('sourceMasterAfter'),'source master changed or evidence absent')
        raw=base64.b64decode(after['nativePngBase64'],validate=True);old_raw=base64.b64decode(before['nativePngBase64'],validate=True)
        with Image.open(BytesIO(raw)) as im,Image.open(BytesIO(old_raw)) as prior:
            im.load();prior.load();root=new[execution['rootReference']]
            require(im.format==prior.format=='PNG','native exports must be PNG')
            require(im.size==prior.size==(round(root['width']),round(root['height'])),'incomplete native PNG dimensions')
            require(im.convert('RGB').getcolors(maxcolors=2) is None,'empty native PNG')
            def region(node):return (math.floor(node['x']-root['x']),math.floor(node['y']-root['y']),math.ceil(node['x']+node['width']-root['x']),math.ceil(node['y']+node['height']-root['y']))
            diff=ImageChops.difference(im.convert('RGB'),prior.convert('RGB'))
            require(diff.getbbox() is not None,'swap PNG did not change')
            diff.paste((0,0,0),region(b));require(diff.getbbox() is None,'PNG changed outside swapped instance')
            require(ImageChops.difference(im.crop(region(b)).convert('RGB'),im.crop(region(reference[0])).convert('RGB')).getbbox() is None,'native swapped pixels differ from unchanged reference copy')
        png_hash=sha256(raw).hexdigest();unchanged=len(old)-len(old_ids)
    except (ValueError,KeyError,TypeError,OSError) as exc:issues.append('invalid native swap evidence: '+str(exc))
    reviewed=isinstance(visual_review,dict) and visual_review.get('status')=='PASS' and visual_review.get('nativePngSha256')==png_hash and bool(visual_review.get('reviewedBy'))
    return {'scope':'native-section-component-swap-qa','status':'FAIL' if issues else 'PASS' if reviewed else 'Review',
            'nativeStructure':'FAIL' if issues else 'PASS','visualReview':'PASS' if reviewed else 'Review',
            'nativePngSha256':png_hash,'unchangedNativeNodeCount':unchanged,'issues':issues,'fullTask015Acceptance':False}
