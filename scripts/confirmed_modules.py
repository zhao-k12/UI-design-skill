"""Build explicit full Tree nodes from caller-supplied page facts.

These functions return ordinary nodes, not a second input format or references.
Callers remain responsible for independent source observations and bindings.
"""
from copy import deepcopy
import base64
from pathlib import Path
import re


def _id(prefix):
    if not isinstance(prefix, str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*', prefix):
        raise ValueError('module_prefix_invalid')
    return prefix


def project_logo(identifier, path):
    """Embed this task's project logo; compiler validates the asset before export."""
    identifier=_id(identifier)
    path=Path(path)
    mime={'.svg':'image/svg+xml','.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.webp':'image/webp'}.get(path.suffix.lower())
    if not mime: raise ValueError('unsupported_project_logo_format')
    data=base64.b64encode(path.read_bytes()).decode('ascii')
    return {'id':identifier,'kind':'asset','name':'project-logo','dataUri':'data:'+mime+';base64,'+data,'alt':'项目 Logo'}


def _text(identifier, value):
    if not isinstance(value, str): raise ValueError('explicit_text_required')
    return {'id': identifier, 'kind': 'text', 'value': value}


def _box(identifier, role, children, source_ids=(), *, layout=None):
    result = {'id': identifier, 'kind': 'container', 'designRole': role,
              'children': children, 'sourceIds': list(source_ids)}
    if layout is not None: result['layout'] = layout
    return result


def _button(identifier, label, icon=None, primary=False, source_ids=()):
    node = {'id': identifier, 'kind': 'component', 'component': 'Button',
            'props': {'type': 'primary' if primary else 'default'},
            'children': [_text(identifier + '-label', label)], 'sourceIds': list(source_ids)}
    if icon: node['icon'] = icon
    return node


def light_tag(identifier, label, *, color='blue', source_ids=()):
    """Official View UI Plus light palette; explicit custom variants remain available."""
    identifier = _id(identifier)
    palette = {'pink','magenta','red','volcano','orange','yellow','gold','cyan',
               'lime','green','blue','geekblue','purple','default'}
    if color not in palette: raise ValueError('unsupported_light_tag_color')
    return {'id':identifier,'kind':'component','component':'Tag','designRole':'light-tag','props':{'color':color},
            'sourceIds':list(source_ids),'children':[_text(identifier+'-label',label)]}


def sidebar(prefix, entries, *, source_ids=(), active_name=None, open_names=None, brand_node=None):
    """Menu entries require explicit name, label, optional icon and children."""
    prefix = _id(prefix)
    if not isinstance(entries, list): raise ValueError('menu_entries_required')
    def entry(item, path):
        if not isinstance(item, dict) or not item.get('name') or not isinstance(item.get('label'), str):
            raise ValueError('explicit_menu_entry_required')
        title = []
        if item.get('icon'): title.append({'id': path+'-icon', 'kind': 'icon', 'name': item['icon']})
        title.append(_text(path+'-label', item['label']))
        kids = item.get('children', [] if item.get('expandable') else None)
        if kids is not None:
            if not isinstance(kids, list): raise ValueError('menu_children_must_be_list')
            return {'id': path, 'kind': 'component', 'component': 'Submenu', 'props': {'name': item['name']}, 'sourceIds': list(item.get('sourceIds',())),
                    'slots': {'title': title}, 'children': [entry(child, path+'-'+str(i)) for i,child in enumerate(kids)]}
        return {'id': path, 'kind': 'component', 'component': 'MenuItem', 'props': {'name': item['name']}, 'children': title, 'sourceIds': list(item.get('sourceIds',()))}
    brand = deepcopy(brand_node) if brand_node is not None else {'id': prefix+'-default-logo', 'kind': 'asset', 'name': 'default-logo'}
    logo = _box(prefix+'-brand', 'brand', [brand], layout={'direction': 'horizontal', 'align': 'center'})
    def active_ancestors(items):
        for item in items:
            if item.get('name') == active_name: return []
            children = item.get('children') or []
            found = active_ancestors(children)
            if found is not None: return [item['name'], *found]
        return None
    if open_names is None: open_names = active_ancestors(entries) or []
    props = {'theme': 'light', 'width': '100%', 'openNames': list(open_names)}
    if active_name is not None: props['activeName'] = active_name
    menu = {'id': prefix+'-menu', 'kind': 'component', 'component': 'Menu', 'props': props,
            'children': [entry(item,prefix+'-entry-'+str(i)) for i,item in enumerate(entries)]}
    return _box(prefix, 'sidebar', [logo, menu], source_ids, layout={'direction':'vertical'})


def topbar(prefix, *, source_ids=(), username='钱多多', avatar_node=None, tools=None):
    prefix = _id(prefix)
    if tools is None:
        tools = [('收起菜单','indent-decrease','left'), ('刷新','reset-right-line','left'),
                 ('大屏','slideshow-line','right'), ('全屏','fullscreen-line','right'),
                 ('消息','notification-3-line','right')]
    groups = {'left': [], 'right': []}
    for index, item in enumerate(tools):
        if not isinstance(item, (tuple,list)) or len(item)!=3 or item[2] not in groups:
            raise ValueError('toolbar_tool_requires_label_icon_and_side')
        label, icon, side = item
        groups[side].append(_box(prefix+'-tool-'+str(index), 'topbar-tool-large' if icon == 'indent-decrease' else 'topbar-tool',
                            [{'id':prefix+'-icon-'+str(index),'kind':'icon','name':icon}],
                            layout={'direction':'horizontal','align':'center'}))
        groups[side][-1]['ariaLabel'] = label
    # ariaLabel is accepted only on semantic navigation containers by the compiler.
    for group in groups.values():
        for item in group: item.pop('ariaLabel', None)
    if username is not None:
        if not isinstance(username,str) or not username: raise ValueError('username_must_be_nonempty_text')
        avatar = deepcopy(avatar_node) if avatar_node is not None else {'id':prefix+'-avatar','kind':'asset',
                 'name':'default-avatar','alt':'风景头像'}
        groups['right'].append(_box(prefix+'-user','topbar-user',[avatar,_text(prefix+'-username',username)],
                              layout={'direction':'horizontal','align':'center'}))
    left = {'id':prefix+'-left','kind':'container','layout':{'direction':'horizontal'},'children':groups['left']}
    right = {'id':prefix+'-right','kind':'container','layout':{'direction':'horizontal'},'children':groups['right']}
    return _box(prefix,'topbar',[left,right],source_ids,layout={'direction':'horizontal','justify':'space-between','align':'center'})


def breadcrumb(prefix, labels, *, source_ids=()):
    prefix = _id(prefix)
    if not isinstance(labels,list) or not labels: raise ValueError('breadcrumb_labels_required')
    children=[]
    for i,item in enumerate(labels):
        label=item['label'] if isinstance(item,dict) else item
        refs=item.get('sourceIds',()) if isinstance(item,dict) else ()
        children.append({'id':prefix+'-item-'+str(i),'kind':'component','component':'BreadcrumbItem',
                         'sourceIds':list(refs),'children':[_text(prefix+'-label-'+str(i),label)]})
    node={'id':prefix,'kind':'component','component':'Breadcrumb','designRole':'breadcrumb','children':children,
          'sourceIds':list(source_ids)}
    return node


def search_panel(prefix, fields, *, source_ids=(), show_reset=True):
    prefix = _id(prefix)
    if not isinstance(fields,list): raise ValueError('explicit_fields_required')
    children=[]
    for i,field in enumerate(fields):
        if not isinstance(field,dict) or field.get('component') not in ('Input','Select','DatePicker'):
            raise ValueError('unsupported_search_field')
        field_id=prefix+'-field-'+str(i)
        label=_box(field_id+'-label','search-label',[_text(field_id+'-text',field['label'])])
        control={'id':field_id+'-control','kind':'component','component':field['component'],
                 'props':deepcopy(field.get('props',{})),'children':deepcopy(field.get('children',[]))}
        children.append(_box(field_id,'search-field',[label,control],field.get('sourceIds',()),
                        layout={'direction':'horizontal','align':'center'}))
    buttons=[_button(prefix+'-query','查询','search-line',True)]
    if show_reset: buttons.append(_button(prefix+'-reset','重置','refresh-line'))
    children.append(_box(prefix+'-actions','search-actions',buttons,layout={'direction':'horizontal'}))
    grid=_box(prefix+'-grid','search-grid',children)
    return _box(prefix,'search-panel',[grid],source_ids)


def action_column(prefix, *, title='操作', key='actions', source_ids=()):
    """Column rows supply a list of {label, icon, tone}; declare icons in content.icons."""
    prefix = _id(prefix)
    item={'id':prefix+'-item','kind':'component','component':'Link','designRole':'row-action',
          'props':{'type':{'bind':'item.tone'}},'children':[
              {'id':prefix+'-icon','kind':'icon','name':{'bind':'item.icon'}},
              {'id':prefix+'-text','kind':'text','value':{'bind':'item.label'}}]}
    repeat={'id':prefix+'-repeat','kind':'repeat','items':{'bind':'row.'+key},'template':item}
    return {'title':title,'key':key,'align':'center','cell':_box(prefix+'-cell','row-actions',[repeat],source_ids)}

def toolbar_notice(prefix, text, *, source_ids=()):
    prefix = _id(prefix)
    return _box(prefix, 'toolbar-notice', [{'id':prefix+'-icon','kind':'icon','name':'information-line'},
                _text(prefix+'-text', text)], source_ids, layout={'direction':'horizontal','align':'center'})


def table_panel(prefix, columns, rows, *, source_ids=(), table_source_ids=(), page_source_ids=(), tabs=None, active_tab=None, buttons=(), notice=None, page=True, equal_gaps=None):
    prefix = _id(prefix)
    if not isinstance(columns,list) or not isinstance(rows,list): raise ValueError('explicit_columns_and_rows_required')
    columns = deepcopy(columns)
    for col in columns:
        cell = col.get('cell', {}) if isinstance(col, dict) else {}
        values = [row.get(col.get('key')) for row in rows if isinstance(row, dict)]
        if cell.get('designRole') == 'row-actions' and any(isinstance(v, list) and len(v) > 1 for v in values):
            cell['designRole'] = 'row-actions-left'
    if equal_gaps is None:
        equal_gaps=bool(columns) and all(isinstance(col,dict) and not (col.get('width') or col.get('minWidth') or col.get('fitContent') is False or col.get('children')) for col in columns)
    if not isinstance(equal_gaps,bool): raise ValueError('equal_gaps_must_be_boolean')
    toolbar=[]
    if notice is not None: toolbar.append(deepcopy(notice))
    if tabs is not None:
        if not isinstance(tabs,list): raise ValueError('tabs_must_be_list')
        if active_tab is not None and active_tab not in [item['name'] for item in tabs]:
            raise ValueError('active_tab_not_found')
        panes=[]
        for i,item in enumerate(tabs):
            tab_id=prefix+'-tab-'+str(i)
            pane={'id':tab_id,'kind':'component','component':'TabPane',
                  'props':{'name':item['name']},'sourceIds':list(item.get('sourceIds',()))}
            if 'count' in item:
                pane['tabLabel']=_box(tab_id+'-label','tab-label',[_text(tab_id+'-text',item['label']),
                    _box(tab_id+'-badge','tab-count',[_text(tab_id+'-count',str(item['count']))])],layout={'direction':'horizontal'})
            else: pane['props']['label']=item['label']
            panes.append(pane)
        tab_node={'id':prefix+'-tabs','kind':'component','component':'Tabs','children':panes}
        if active_tab is not None: tab_node['props']={'modelValue':active_tab}
        toolbar.append(tab_node)
    elif active_tab is not None: raise ValueError('active_tab_requires_tabs')
    if buttons:
        toolbar.append(_box(prefix+'-buttons','table-actions',[
            _button(prefix+'-button-'+str(i),item['label'],item.get('icon'),item.get('primary',False),item.get('sourceIds',()))
            for i,item in enumerate(buttons)],layout={'direction':'horizontal'}))
    children=[]
    if toolbar: children.append(_box(prefix+'-toolbar','table-toolbar',toolbar,layout={'direction':'horizontal'}))
    children.append({'id':prefix+'-table','kind':'component','component':'Table','equalGapColumns':equal_gaps,'sourceIds':list(table_source_ids),
                     'props':{'stripe':True,'columns':deepcopy(columns),'data':deepcopy(rows)}})
    if page is True: page={'modelValue':1,'pageSize':10,'total':100,'showSizer':True,'showTotal':True}
    if page is not None:
        if not isinstance(page,dict): raise ValueError('page_must_be_mapping_or_none')
        children.append({'id':prefix+'-page-wrap','kind':'container','layout':{'direction':'horizontal','justify':'end'},
                         'children':[{'id':prefix+'-page','kind':'component','component':'Page','designRole':'pagination','sourceIds':list(page_source_ids),'props':deepcopy(page)}]})
    return _box(prefix,'table-panel',children,source_ids)


def page_shell(prefix, *, sidebar_node=None, topbar_node=None, breadcrumb_node=None,
               sections=(), source_ids=()):
    """Compose independently configured complete nodes without adding business content."""
    prefix=_id(prefix)
    main=[]
    if topbar_node is not None: main.append(deepcopy(topbar_node))
    if breadcrumb_node is not None: main.append(deepcopy(breadcrumb_node))
    main.extend(deepcopy(list(sections)))
    main_node={'id':prefix+'-main','kind':'container','layout':{'direction':'vertical','fill':True},'children':main}
    children=[]
    if sidebar_node is not None: children.append(deepcopy(sidebar_node))
    children.append(main_node)
    return _box(prefix,'page-shell',children,source_ids,layout={'direction':'horizontal','minHeight':'viewport'})
