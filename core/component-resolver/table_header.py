"""Source-column header primitives above an unchanged admitted Table Body."""
from copy import deepcopy


def compose(cell_id, box, node, headers, style, geometry, tokens):
    metrics=geometry.table_metrics(node['componentId'],node['variant'])
    if len(headers)!=len(metrics['widths']):raise ValueError('Header count differs from measured source columns')
    width=node['layout']['width']['value'];body_height=node['layout']['height']['value'];height=metrics['height']
    if width>box['width'] or height+body_height>box['height']:raise ValueError('Table header and original body exceed Cell envelope')
    fixed=lambda w,h:{'width':{'mode':'fixed','value':w},'height':{'mode':'fixed','value':h}}
    source=node['sourceIds'];columns=[]
    for index,(text,w) in enumerate(zip(headers,metrics['widths'])):
        identifier=cell_id+'.header.column.'+str(index)
        if w<=tokens.resolve('spacing.md'):raise ValueError('Source column cannot fit declared header padding')
        columns.append({'id':identifier,'type':'Frame','sourceIds':source,
            'layout':{**fixed(w,height),'direction':'horizontal','gap':{'token':'spacing.none'},
                      'padding':{'top':0,'right':0,'bottom':0,'left':{'token':'spacing.md'}},
                      'alignment':{'main':'start','cross':'center'}},
            'children':[{'id':identifier+'.text','type':'Text','sourceIds':source,'text':text,'style':deepcopy(style),
                         'layout':{'width':{'mode':'hug'},'height':{'mode':'hug'}}}]})
    header={'id':cell_id+'.header','type':'Row','sourceIds':source,
            'layout':{**fixed(width,height),'direction':'horizontal','gap':{'token':'spacing.none'}},'children':columns}
    return {'id':cell_id,'type':'Frame','sourceIds':source,
            'layout':{**fixed(box['width'],box['height']),'direction':'vertical','gap':{'token':'spacing.none'}},
            'children':[header,deepcopy(node)]},height
