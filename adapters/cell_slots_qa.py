"""Independent native readback for filling existing empty Cell roles."""
import base64
import json
from hashlib import sha256
from io import BytesIO
from PIL import Image, ImageChops, ImageDraw


def verify(execution, before, patch, after, request, *, visual_review=None, platform="penpot"):
    issues=[]
    def require(condition, message):
        if not condition: issues.append(message)
    for record in (before,patch,after):
        require(all(record.get(k)==execution.get(k) for k in ('fileReference','pageReference','rootReference')), 'native context mismatch')
    require(execution.get('status')=='EXECUTED' and patch.get('status')=='FILLED' and before.get('status')==after.get('status')=='CAPTURED', 'complete native execution required')
    if platform=='figma':
        digest=lambda nodes:sha256(json.dumps(nodes,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
        require(digest(before.get('nodes',[]))==patch.get('beforeSha256') and digest(after.get('nodes',[]))==patch.get('afterSha256'), 'independent capture differs from execution hash')
    else:
        require(before.get('nodes')==patch.get('before') and after.get('nodes')==patch.get('after'), 'independent capture differs from execution')
    old={n['id']:n for n in before.get('nodes',[])};new={n['id']:n for n in after.get('nodes',[])}
    require(len(old)==len(before.get('nodes',[])) and len(new)==len(after.get('nodes',[])), 'duplicate native IDs')
    roles={execution['nodeMap'].get(item['roleId']) for item in request['items']}
    require(len(roles)==6 and None not in roles and len(request['items'])==6, 'six distinct declared roles required')
    require(set(patch.get('mutatedNodeIds',[]))==roles and patch.get('removedNodeIds')==[], 'slot mutation ledger mismatch')
    created=patch.get('createdNodeIds',[])
    require(len(created)==len(set(created)) and set(new)-set(old)==set(created) and set(old)<=set(new), 'slot creation ledger mismatch')
    for identifier,node in old.items():
        a=dict(node);b=dict(new.get(identifier,{}))
        if identifier in roles:
            require(a.get('children')==[], 'baseline role was not empty');a.pop('children',None);b.pop('children',None)
        require(a==b, 'existing native container changed')
    for item in request['items']:
        parent=new.get(execution['nodeMap'][item['roleId']],{})
        children=[patch.get('nodeMap',{}).get(s['id']) for s in item['children']]
        require(set(parent.get('children',[]))==set(children), 'role children differ from declared plan')
        for spec,identifier in zip(item['children'],children):
            node=new.get(identifier,{})
            require(node.get('parent')==parent.get('id') and node.get('name')==spec['name'] and
                    node.get('width')==spec['layout']['width']['value'] and node.get('height')==spec['layout']['height']['value'], 'child identity or source size changed')
            if spec.get('componentReference'):
                require((node.get('type')=='INSTANCE' if platform=='figma' else node.get('isCopy') is True and node.get('isMain') is False) and node.get('component')==spec['componentReference'], 'child is not the declared genuine source instance')
            else:
                style=spec['style']['typographyToken']
                if platform=='figma':
                    expected=spec['fontName'];actual=node.get('fontName',{})
                    # Figma exposes the effective wght axis for an otherwise named
                    # Regular variable-font style. It must equal the requested weight.
                    font_match=(actual.get('family')==expected['family'] and actual.get('style')==expected['style'] and
                                actual.get('variationSettings',{}) in (expected.get('variationSettings',{}),{'wght':style['fontWeight']}))
                    require(node.get('type')=='TEXT' and node.get('characters')==spec['text'] and font_match and
                            node.get('fontSize')==style['fontSize'] and node.get('lineHeight')=={'unit':'PIXELS','value':style['lineHeight']}, 'editable text or native font changed')
                else:
                    binding=spec['fontBinding']
                    require(node.get('type')=='text' and node.get('characters')==spec['text'] and
                            node.get('fontId')==binding['fontId'] and node.get('fontVariantId')==binding['fontVariantId'] and
                            node.get('fontFamily')==binding['family'] and float(node.get('fontSize',0))==style['fontSize'] and
                            float(node.get('lineHeight',0))==style['lineHeight']/style['fontSize'], 'editable text or native font changed')
    png_sha=None
    try:
        raw=base64.b64decode(after['nativePngBase64'],validate=True);png_sha=sha256(raw).hexdigest()
        a=Image.open(BytesIO(base64.b64decode(before['nativePngBase64'],validate=True))).convert('RGBA')
        b=Image.open(BytesIO(raw)).convert('RGBA')
        require(a.size==b.size==(1440,80), 'complete native PNG dimensions mismatch')
        diff=ImageChops.difference(a,b).convert('RGB');mask=Image.new('L',a.size,0);draw=ImageDraw.Draw(mask)
        root=old[execution['rootReference']]
        for identifier in roles:
            n=old[identifier];x=n['x']-root['x'];y=n['y']-root['y']
            draw.rectangle((x,y,x+n['width']-1,y+n['height']-1),fill=255)
        require(ImageChops.multiply(diff,Image.merge('RGB',[ImageChops.invert(mask)]*3)).getbbox() is None, 'pixels outside existing role envelopes changed')
        require(diff.getbbox() is not None, 'slot PNG remained empty')
    except (ValueError,KeyError,TypeError,OSError) as exc:issues.append('invalid native PNG: '+str(exc))
    if visual_review is not None:require(visual_review.get('status')=='PASS' and visual_review.get('nativePngSha256')==png_sha, 'visual review is stale')
    return {'scope':platform+'-native-cell-slot-subtask','status':'FAIL' if issues else 'PASS' if visual_review else 'Review',
            'nativePngSha256':png_sha,'preservedContainerCount':len(old),'createdNodeCount':len(created),
            'fullTask015Acceptance':False,'issues':issues}
