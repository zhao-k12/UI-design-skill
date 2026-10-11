"""Source-sized role frames inside a frozen Cell; official widgets stay unchanged."""
from copy import deepcopy
from hashlib import sha256
import math
import xml.etree.ElementTree as ET
from validators.ui_ir import validate_document

ORDER=('leading-icon','label','control','trailing-icon','content','actions')
KINDS={'leading-icon':{'IconInstance'},'trailing-icon':{'IconInstance'},'label':{'Text'},
       'control':{'ComponentInstance'},'content':{'Text','ComponentInstance'},'actions':{'ComponentInstance'}}


def compose(cell_id,box,source_id,slots,geometry,registry,icons,tokens,source_quotes,icon_sources,*,direction='horizontal',main='start',order=None):
    if direction not in ('horizontal','vertical') or main not in ('start','space-between'):
        raise ValueError('Unsupported Cell slot layout')
    if not slots or set(slots)-set(ORDER):raise ValueError('Unknown or empty Cell slots')
    sequence=ORDER if order is None else order
    if order is not None and (len(order)!=len(set(order)) or set(order)!=set(slots)):
        raise ValueError('Explicit Cell order must cover every role exactly once')
    if any(type(box.get(k)) not in (int,float) or not math.isfinite(box[k]) for k in ('x','y','width','height')):
        raise ValueError('Invalid Cell envelope')
    if box['width']<=0 or box['height']<=0:raise ValueError('Empty Cell envelope')
    if geometry.registry_sha256!=registry.fingerprint:raise ValueError('Slot geometry registry mismatch')
    gap=tokens.resolve('spacing.sm');frames=[];ids=set()
    def fixed(node):
        layout=node.get('layout',{})
        values=[]
        for axis in ('width','height'):
            s=layout.get(axis,{})
            if s.get('mode')!='fixed' or type(s.get('value')) not in (int,float) or not math.isfinite(s['value']) or s['value']<=0:
                raise ValueError('Slot children need positive measured fixed dimensions')
            values.append(s['value'])
        return values
    def source_content(n):
        if n.get('sourceIds')!=[source_id]:raise ValueError('Slot source identity mismatch')
        if n['id'] in ids:raise ValueError('Duplicate slot child ID')
        ids.add(n['id'])
        if n['type']=='Text' and not any(n['text'] in q for q in source_quotes):raise ValueError('Slot text is not present in source evidence')
        for value in n.get('props',{}).values():
            for text in value if isinstance(value,list) else [value]:
                if not isinstance(text,str) or not any(text in q for q in source_quotes):raise ValueError('Slot property is not present in source evidence')
        for children in n.get('slots',{}).values():
            for child in children:source_content(child)
    for role in sequence:
        if role not in slots:continue
        children=deepcopy(slots[role])
        if not children:raise ValueError('Empty declared slot')
        sizes=[]
        for node in children:
            if node.get('type') not in KINDS[role]:raise ValueError('Incompatible Cell slot role')
            source_content(node);w,h=fixed(node)
            if h>box['height']:raise ValueError('Slot child height exceeds Cell envelope')
            if node['type']=='ComponentInstance':
                registry.resolve(node['componentId'],node.get('variant'))
                placed=geometry.place(node,dict(x=0,y=0,width=w,height=h))
                if placed['instance']['layout']!=node['layout']:raise ValueError('Slot cannot stretch admitted source geometry')
            if node['type']=='IconInstance':
                entry=icons.resolve(node['iconId'])['descriptor'];raw=icon_sources[node['iconId']]
                raw=raw.encode() if isinstance(raw,str) else raw
                if sha256(raw).hexdigest()!=entry['svgSha256']:raise ValueError('Slot icon source hash mismatch')
                svg=ET.fromstring(raw);view=[float(v) for v in svg.attrib['viewBox'].replace(',',' ').split()]
                if len(view)!=4 or not all(math.isfinite(v) for v in view) or [w,h]!=view[2:]:raise ValueError('Slot icon cannot resize source viewBox')
            sizes.append((w,h))
        width=sum(w for w,h in sizes)+gap*(len(sizes)-1);height=max(h for w,h in sizes)
        frames.append({'id':cell_id+'.slot.'+role,'type':'Frame','sourceIds':[source_id],
                       'layout':{'width':{'mode':'fixed','value':width},'height':{'mode':'fixed','value':box['height'] if direction=='horizontal' else height},
                                 'direction':'horizontal','gap':{'token':'spacing.sm'},'alignment':{'main':'start','cross':'center'}},'children':children})
    width=sum(f['layout']['width']['value'] for f in frames)+gap*(len(frames)-1) if direction=='horizontal' else max(f['layout']['width']['value'] for f in frames)
    height=max(f['layout']['height']['value'] for f in frames) if direction=='horizontal' else sum(f['layout']['height']['value'] for f in frames)+gap*(len(frames)-1)
    if width>box['width'] or height>box['height']:raise ValueError('Cell slot content overflows existing envelope')
    cell={'id':cell_id,'type':'Frame','sourceIds':[source_id],
          'layout':{'width':{'mode':'fixed','value':box['width']},'height':{'mode':'fixed','value':box['height']},
                    'direction':direction,'gap':{'token':'spacing.sm'},'alignment':{'main':main,'cross':'start'}},'children':frames}
    if ids.intersection({cell_id,*[f['id'] for f in frames]}):raise ValueError('Slot IDs collide with envelope IDs')
    document={'uiIrVersion':'0.1.0','documentId':'cell-slot-validation','pages':[{'id':'slot-validation-page','type':'Page','children':[cell]}]}
    issues=validate_document(document)
    if issues:raise ValueError('Invalid Cell slot UI-IR: '+str(issues))
    from importlib import import_module
    if import_module('core.design-rules.tokens').check_references(document,tokens):raise ValueError('Unknown slot token')
    return cell
