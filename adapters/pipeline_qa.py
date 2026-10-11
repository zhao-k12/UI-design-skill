"""Independent full-page readback checks for the static pipeline, after execution."""
import base64
from collections import Counter
from hashlib import sha256
from io import BytesIO
import math
import importlib
import json

from PIL import Image
from validators.ui_ir import validate_document,ROOT
from adapters.component_bindings import ComponentBindings
from validators.structure.gate import builder


def verify(document, plan, execution, capture, content, platform):
    issues=[]
    def need(ok,code,identifier=''):
        if not ok:issues.append({'code':code,'uiIrId':identifier})
    def equal(a,b):return type(a) in (int,float) and type(b) in (int,float) and math.isfinite(a) and math.isfinite(b) and abs(a-b)<=1e-6
    digest=builder.fingerprint(document)
    need(not validate_document(document),'invalid_ui_ir')
    registry_module=importlib.import_module('core.component-resolver.registry')
    registry=registry_module.ComponentRegistry(json.loads((ROOT/'registries/components/catalog.json').read_bytes()),json.loads((ROOT/'registries/components/fidelity-reports.json').read_bytes()))
    tokens=importlib.import_module('core.design-rules.tokens').TokenRegistry(json.loads((ROOT/'registries/tokens/default.json').read_bytes()))
    need(plan.get('tokensSha256')==tokens.fingerprint,'token_registry_changed')
    bindings=ComponentBindings(json.loads((ROOT/f'adapters/{platform}/metadata/component-bindings.json').read_bytes()),registry,platform=platform)
    icon_bindings=json.loads((ROOT/f'adapters/{platform}/metadata/icon-bindings.json').read_bytes())
    need(plan.get('componentsSha256')==registry.fingerprint and plan.get('iconsSha256')==icon_bindings['registrySha256'],'registry_input_hash_mismatch')
    source_nodes={}
    def admitted(n):
        source_nodes[n['id']]=n
        if n['type']=='ComponentInstance':
            try:registry.resolve(n['componentId'],n.get('variant'))
            except ValueError:need(False,'illegal_component_variant_or_type',n['id'])
        if n['type']=='IconInstance':need(n['iconId'] in icon_bindings['bindings'],'icon_not_in_registry',n['id'])
        for child in n.get('children',[]):admitted(child)
        for children in n.get('slots',{}).values():
            for child in children:admitted(child)
    for page in document['pages']:admitted(page)
    need((plan.get('platform')==platform if platform=='penpot' else plan.get('platform') in (None,'figma')) and plan.get('uiIrSha256')==digest==execution.get('uiIrSha256'),'input_hash_mismatch')
    need(execution.get('status')=='EXECUTED' and capture.get('status')=='CAPTURED','native_execution_or_capture_missing')
    for key in ('fileReference','pageReference','rootReference'):
        need(bool(execution.get(key)) and execution.get(key)==capture.get(key),'capture_context_mismatch',key)
    need(execution.get('fileReference')==plan.get('fileReference'),'wrong_file')
    rows=capture.get('nodes',[]) if platform=='figma' else capture.get('contentNodes',[])
    nodes={n['id']:n for n in rows};need(len(nodes)==len(rows)>0,'duplicate_or_empty_native_nodes')
    mapping=execution.get('nodeMap',{});need(len(set(mapping.values()))==len(mapping),'duplicate_logical_binding')
    created=execution.get('createdNodeIds',[])
    need(len(set(created))==len(created) and set(created)-{execution.get('pageReference')}==set(nodes),'creation_ledger_incomplete')
    specs={}
    def index(n):
        need(n['id'] not in specs,'duplicate_plan_id',n['id']);specs[n['id']]=n
        for child in n.get('children',[]):index(child)
    for page in plan['pages']:index(page)
    need(set(mapping)==set(specs),'logical_inventory_mismatch')
    penpot_evidence={n['uiIrId']:n for n in capture.get('evidence',[])}
    logical={k:nodes.get(v) for k,v in mapping.items()}
    root=nodes.get(execution.get('rootReference'));need(root is not None,'missing_root')
    if not root:return {'status':'FAIL','issues':issues}
    for n in rows:
        need(all(type(n.get(k)) in (int,float) and math.isfinite(n[k]) for k in ('x','y','width','height')),'invalid_native_geometry',n['id'])
        # Admitted component internals include a deliberately hidden empty icon
        # background and SDK opacity=null. Their exact source state is verified
        # by the separate instance fidelity gate, never normalized into evidence.
        if n['id'] in mapping.values():
            need(n.get('visible',True) is not False and not n.get('hidden',False) and n.get('opacity',1)==1,'hidden_or_transparent_native_content',n['id'])
    def descendant(node,ancestor):
        seen=set()
        while node and node['id']!=ancestor:
            if node['id'] in seen:return False
            seen.add(node['id']);node=nodes.get(node.get('parent'))
        return node is not None
    def hex_color(n):
        fills=n.get('fills',[])
        if not fills:return None
        f=fills[0]
        if platform=='penpot':return f.get('fillColor','').lower() if f.get('fillOpacity',1)==1 else None
        if f.get('type')!='SOLID' or f.get('opacity',1)!=1 or f.get('visible',True) is False:return None
        c=f.get('color',{});return '#'+''.join(f'{round(c.get(k,-1)*255):02x}' for k in ('r','g','b'))
    for uid,spec in specs.items():
        declared=source_nodes.get(uid)
        need(declared is not None and declared['type']==spec['type'],'plan_ui_ir_type_mismatch',uid)
        if declared and declared['type']=='ComponentInstance':
            try:need(bindings.resolve(declared['componentId'],declared.get('variant'))['componentReference']==spec['componentReference'],'component_binding_mismatch',uid)
            except ValueError:need(False,'illegal_component_variant_or_type',uid)
        if declared and declared['type']=='IconInstance':
            b=icon_bindings['bindings'].get(declared['iconId'],{})
            need(b.get('componentReference')==spec.get('componentReference') and b.get('svgSha256')==spec.get('svgSha256'),'icon_source_binding_mismatch',uid)
        n=logical.get(uid)
        if n is None:need(False,'missing_native_node',uid);continue
        need(descendant(n,root['id']),'foreign_native_node',uid)
        is_instance=spec['type'] in ('ComponentInstance','IconInstance')
        expected='TEXT' if spec['type']=='Text' else 'INSTANCE' if is_instance else 'FRAME'
        need(n['type']==expected if platform=='figma' else n['type']==('text' if expected=='TEXT' else 'board'),'native_type_mismatch',uid)
        for axis in ('width','height'):
            size=spec['layout'][axis]
            if size['mode']=='fixed':need(equal(n[axis],size['value']),'native_size_mismatch',uid)
        need(n['x']>=root['x']-1e-6 and n['y']>=root['y']-1e-6 and n['x']+n['width']<=root['x']+root['width']+1e-6 and n['y']+n['height']<=root['y']+root['height']+1e-6,'logical_node_overflows_page',uid)
        if is_instance:
            need((n['type']=='INSTANCE' if platform=='figma' else n.get('isCopy') is True and n.get('isMain') is False) and n.get('component')==spec['componentReference'],'wrong_or_flattened_instance',uid)
            for binding in spec.get('nativeContent',[]):
                matches=[t for t in rows if t.get('characters') is not None and t['name']==binding['name'] and descendant(t,n['id'])]
                need(len(matches)==1 and matches[0]['characters']==binding['text'],'instance_content_missing',uid)
        elif spec['type']=='Text':
            need(n.get('characters')==spec['text'],'text_content_mismatch',uid)
            typography=spec['style']['typographyToken']
            try:font_size=float(n.get('fontSize'))
            except (ValueError,TypeError):font_size=None
            need(equal(font_size,typography['fontSize']),'text_font_size_mismatch',uid)
            if platform=='figma':
                font=n.get('fontName',{});axes=font.get('variationSettings',{})
                expected_axes=spec['fontName'].get('variationSettings',{})
                need(font.get('family')==spec['fontName']['family'] and font.get('style')==spec['fontName']['style'] and (axes==expected_axes or not expected_axes and axes=={'wght':typography['fontWeight']}),'text_font_mismatch',uid)
                need(n.get('lineHeight')=={'unit':'PIXELS','value':typography['lineHeight']} and n.get('letterSpacing')=={'unit':'PIXELS','value':typography['letterSpacing']},'text_line_height_or_spacing_mismatch',uid)
            else:
                need(n.get('fontFamily')==typography['fontFamily'] and str(n.get('fontWeight'))==str(typography['fontWeight']),'text_font_mismatch',uid)
                try:need(equal(float(n.get('lineHeight'))*font_size,typography['lineHeight']) and equal(float(n.get('letterSpacing')),typography['letterSpacing']),'text_line_height_or_spacing_mismatch',uid)
                except (TypeError,ValueError):need(False,'invalid_native_typography',uid)
            need(hex_color(n)==spec['style']['colorToken'].lower(),'text_color_mismatch',uid)
            p=nodes.get(n['parent']);need(p and n['x']>=p['x']-1e-6 and n['y']>=p['y']-1e-6 and n['x']+n['width']<=p['x']+p['width']+1e-6 and n['y']+n['height']<=p['y']+p['height']+1e-6,'text_overflows_container',uid)
        else:
            layout=spec['layout'];direction='vertical' if spec['type']=='Grid' else layout['direction']
            if platform=='figma':
                need(n.get('layoutMode')==direction.upper() and equal(n.get('itemSpacing'),layout['gap']),'layout_direction_or_spacing_mismatch',uid)
                for side,value in layout['padding'].items():need(equal(n.get('padding'+side.title()),value),'layout_padding_mismatch',uid)
            else:
                f=penpot_evidence.get(uid,{}).get('flex',{})
                need(f.get('dir')==('column' if direction=='vertical' else 'row'),'layout_direction_mismatch',uid)
                need(equal(f.get('rowGap'),layout['gap']) and equal(f.get('columnGap'),layout['gap']),'layout_spacing_mismatch',uid)
                for side,value in layout['padding'].items():need(equal(f.get(side+'Padding'),value),'layout_padding_mismatch',uid)
            if 'fill' in spec['style']:need(hex_color(n)==spec['style']['fill'].lower(),'region_fill_mismatch',uid)
    # Every final container is checked using declared flow, including Grid24 rows.
    def flow(parent,children,layout,uid):
        if any(c is None for c in children):return
        main='x' if layout['direction']=='horizontal' else 'y';cross='y' if main=='x' else 'x';size='width' if main=='x' else 'height';cs='height' if size=='width' else 'width'
        pad=layout['padding'];start=pad['left' if main=='x' else 'top'];end=pad['right' if main=='x' else 'bottom'];cstart=pad['top' if cross=='y' else 'left'];cend=pad['bottom' if cross=='y' else 'right'];gap=layout['gap']
        remaining=parent[size]-start-end-sum(c[size] for c in children)-gap*max(len(children)-1,0)
        alignment=layout['alignment'];cursor=parent[main]+start
        if alignment['main']=='space-between' and len(children)>1:gap+=remaining/(len(children)-1)
        elif alignment['main']=='center':cursor+=remaining/2
        elif alignment['main']=='end':cursor+=remaining
        for child in children:
            offset=cstart
            if alignment['cross']=='center':offset+=(parent[cs]-cstart-cend-child[cs])/2
            elif alignment['cross']=='end':offset=parent[cs]-cend-child[cs]
            need(equal(child[main],cursor) and equal(child[cross],parent[cross]+offset),'native_flow_position_mismatch',uid)
            need(child[main]+child[size]<=parent[main]+parent[size]-end+1e-6 and child[cross]+child[cs]<=parent[cross]+parent[cs]-cend+1e-6,'component_or_container_overflow',uid)
            cursor+=child[size]+gap
    for uid,spec in specs.items():
        if not spec.get('children') or not logical.get(uid):continue
        parent=logical[uid];layout=spec['layout']
        if spec['type']=='Grid':
            cursor=parent['x']+layout['padding']['left'];row=0;cy=parent['y']+layout['padding']['top'];height=0
            for cell in spec['gridCells']:
                if cell['row']!=row:cy+=height+layout['gap'];height=0;row=cell['row'];cursor=parent['x']+layout['padding']['left']
                child=logical.get(cell['id'])
                if child:
                    need(equal(child['width'],cell['width']) and equal(child['x'],cursor) and equal(child['y'],cy),'grid24_span_or_position_mismatch',cell['id']);height=max(height,child['height'])
                cursor+=cell['width']+layout['gap']
        else:flow(parent,[logical.get(c['id']) for c in spec['children']],layout,uid)
    # Source-approved primitives, controls, and all nine table values must remain editable.
    texts=Counter(n['characters'] for n in rows if 'characters' in n)
    claims=[]
    for item in content['items']:
        claims.extend(v['text'] for v in item['props'].values() if isinstance(v,dict) and 'text' in v)
        claims.extend(v['text'] for v in item['props'].get('headers',[]))
        claims.extend(c['text'] for record in item.get('tableRecords',[]) for c in record.values())
        claims.extend(c['text'] for role in item.get('cellSlots',{}).values() for c in role if c['type']=='Text')
    for text,count in Counter(claims).items():need(texts[text]>=count,'missing_editable_prototype_content',text)
    try:
        png=base64.b64decode(capture['nativePngBase64'],validate=True)
        with Image.open(BytesIO(png)) as image:
            need(image.format=='PNG' and image.size==(round(root['width']),round(root['height'])),'native_png_incomplete')
            alpha=image.convert('RGBA').getchannel('A');need(alpha.getextrema()==(255,255),'native_page_background_transparent')
    except (ValueError,KeyError,OSError):png=b'';need(False,'native_png_missing')
    return {'scope':'independent-static-pipeline-native-qa','platform':platform,'status':'FAIL' if issues else 'PASS','uiIrSha256':digest,'logicalNodes':len(specs),'nativeNodes':len(rows),'genuineInstances':sum(s['type'] in ('ComponentInstance','IconInstance') for s in specs.values()),'nativePngSha256':sha256(png).hexdigest(),'issues':issues,'fidelityGate':'NOT_RUN','visualReview':'NOT_RUN'}
