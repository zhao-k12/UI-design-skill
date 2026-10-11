"""Independent source geometry checks for unadmitted configurable Table captures."""
import re
from adapters.configurable_table import require
def validate_geometry(native,plan,font_bindings):
    require(native['status']=='CAPTURED' and native['scope']=='production' and native['platform']=='penpot' and native['evidenceKind']=='native-platform-export' and not native['createdNodeIds'] and not native['mutatedNodeIds'],'invalid_table_capture')
    require(native['logicalId']==plan['logicalId'] and native['componentIrSha256']==plan['componentIrSha256'] and native['fileReference']==plan['fileReference'] and native['pageReference']==plan['pageReference'],'table_context_or_source_mismatch')
    nodes=native['nodes'];root=nodes[0];count=2+2*len(plan['rows'])+2*sum(len(row['cells']) for row in plan['rows']);require(len(nodes)==count and len({n['reference'] for n in nodes})==count and root['reference']==native['mainReference'],'table_node_inventory_mismatch')
    expected={plan['name']:('board',None,{'x':0,'y':0,**plan['rootBounds']},plan['rootFill'])}
    texts=[]
    for row in plan['rows']:
        row_name='official-source/'+row['path'];expected[row_name]=('board',plan['name'],row['bounds'],None)
        for cell in row['cells']:
            cell_name='official-source/'+cell['path'];expected[cell_name]=('board',row_name,cell['bounds'],cell['fill'])
            text=cell['text'];text_name='official-source/'+text['path'];expected[text_name]=('text',cell_name,text['sourceTextBounds'],text['fill']);texts.append((text_name,text))
        bounds={'x':row['bounds']['x'],'y':row['bounds']['y']+row['bounds']['height']-row['bottomBorder']['height'],'width':row['bounds']['width'],'height':row['bottomBorder']['height']}
        expected['official-source/row-border/'+row['path']]=('rectangle',row_name,bounds,row['bottomBorder']['fill'])
    pseudo=plan['bottomPseudo'];expected['official-source/0.0::before']=('rectangle',plan['name'],{'x':0,'y':plan['rootBounds']['height']-pseudo['height'],'width':pseudo['width'],'height':pseudo['height']},pseudo['fill'])
    by_name={re.sub(r'\s*/\s*','/',n['name']):n for n in nodes}
    require(set(by_name)==set(expected),'table_source_path_inventory_mismatch')
    for name,(kind,parent,bounds,fill) in expected.items():
        node=by_name[name]
        require(node['type']==kind and (parent is None or node['parentReference']==by_name[parent]['reference']),'table_parent_mismatch')
        require((node['x']-root['x'],node['y']-root['y'],node['width'],node['height'])==(bounds['x'],bounds['y'],bounds['width'],bounds['height']),'table_geometry_mismatch')
        require(node['opacity']==1 and node['blendMode']=='normal' and node['visible'] is True and node['hidden'] is False and node['rotation']==0 and not node['flipX'] and not node['flipY'] and node['shadows']==[] and node['blur'] is None and not node['strokes'],'table_render_state_mismatch')
        if kind!='text':require(node['borderRadius']==0,'table_corner_mismatch')
        if kind=='board':require(node['clipContent'] is (parent is None),'table_clip_mismatch')
        if fill is None:require(node['fills']==[],'table_transparent_wrapper_mismatch')
        else:
            require(len(node['fills'])==1 and node['fills'][0]['fillColor']==fill and node['fills'][0]['fillOpacity']==1 and all(not node['fills'][0].get(k) for k in ('fillColorGradient','fillImage','fillColorRefId','fillColorRefFile')),'table_fill_mismatch')
    for name,item in texts:
        text=by_name[name];font=font_bindings[item['fontFamily']]
        require(text['characters']==item['characters'] and text['fontFamily']==item['fontFamily'] and text['fontId']==font['fontId'] and text['fontVariantId']==font['fontVariantId'] and float(text['fontSize'])==14 and float(text['fontWeight'])==400 and text['fontStyle']=='normal' and float(text['lineHeight'])==item['sourceTextBounds']['height']/14 and float(text['letterSpacing'])==0 and text['growType']=='fixed' and text['align']=='left' and text['verticalAlign']=='top' and text['direction']=='ltr' and text['textTransform']=='none' and text['textDecoration']=='none','table_text_style_mismatch')
    return {'status':'PASS','fidelityGate':'NOT_RUN','productionAdmission':False,'textSamples':[item for name,item in texts],'sourcePaths':list(expected),
        'borderNormalization':'Contiguous same-color cell borders form one row region; independent bottom pseudo and outer clipping are preserved.'}
