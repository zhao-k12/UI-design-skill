"""Deterministic TASK-009 fixture: fixed list skeleton, admitted default content."""
import json
from pathlib import Path


def token(name):return {'token':name}
def fixed(value):return {'mode':'fixed','value':value}
def text(id,value,heading=False):return {'id':id,'type':'Text','text':value,'style':{'typographyToken':token('typography.heading' if heading else 'typography.body'),'colorToken':token('color.text')}}
def instance(id,component,width,height):return {'id':id,'type':'ComponentInstance','componentId':component,'layout':{'width':fixed(width),'height':fixed(height)}}
def icon(id,name):return {'id':id,'type':'IconInstance','iconId':name,'layout':{'width':fixed(24),'height':fixed(24)}}
def container(id,children,*,type='Frame',direction='vertical',width=None,height=None,gap=0,padding=None,fill=None,alignment=None):
    layout={'direction':direction,'gap':gap}
    if width is not None:layout['width']=width
    if height is not None:layout['height']=height
    if padding is not None:layout['padding']={side:padding for side in ('top','right','bottom','left')}
    if alignment is not None:layout['alignment']=alignment
    node={'id':id,'type':type,'layout':layout,'children':children}
    if fill is not None:node['style']={'fill':fill}
    return node


def document():
    fill={'mode':'fill'};center={'main':'start','cross':'center'}
    header=container('header',[text('title','用户管理',True),container('header.space',[],width=fill,height=fixed(24)),icon('header.settings','remix.settings-3-line')],type='Row',direction='horizontal',width=fill,gap=16,alignment=center)
    columns=[container('filter.name',[text('label.name','姓名'),instance('input.name','form.input.default.medium',240,32)],width=fill,gap=8),
        container('filter.status',[text('label.status','状态'),instance('select.status','form.select.default.medium',240,32)],width=fill,gap=8),
        container('filter.summary',[text('label.summary','范围'),text('filter.description','查看用户信息')],width=fill,gap=8),
        container('filter.action',[text('label.action','操作'),instance('button.query','action.button.primary.medium',60,32)],width=fill,gap=8)]
    for column in columns:column['layout']['span']=6
    grid=container('query.grid',columns,type='Grid',direction='horizontal',width=fill,gap=token('spacing.md'));grid['layout']['gridColumns']=24
    query=container('query',[grid],width=fill,padding=token('spacing.md'),fill=token('color.surface'))
    toolbar=container('list.toolbar',[text('list.title','用户列表'),container('list.space',[],width=fill,height=fixed(24)),icon('list.export','remix.download-line'),text('list.export.label','导出')],type='Row',direction='horizontal',width=fill,height=fixed(40),gap=8,alignment=center)
    headers=[container('column.'+key,[text('column.'+key+'.label',label)],direction='horizontal',width=fixed(width),height=fixed(48),padding=0,alignment=center) for key,label,width in [('name','姓名',464.328125),('status','状态',464.328125),('role','角色',463.34375)]]
    for cell in headers:cell['layout']['padding']['left']=token('spacing.md')
    table_header=container('list.columns',headers,type='Row',direction='horizontal',width=fill,fill=token('color.surface'))
    table=container('list',[toolbar,table_header,instance('table.body','data.table.default',1392,144)],width=fill,fill=token('color.surface'))
    page=container('acceptance-page',[header,query,table,text('list.count','共 3 位用户')],type='Page',width=fixed(1440),gap=token('spacing.section'),padding=token('spacing.page'),fill=token('color.page'))
    page['name']='用户管理列表 · TASK-009 验收'
    return {'uiIrVersion':'0.1.0','documentId':'adapter-fidelity-acceptance','pages':[page]}


if __name__=='__main__':
    Path(__file__).with_name('adapter-fidelity-acceptance.ui-ir.json').write_text(json.dumps(document(),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
