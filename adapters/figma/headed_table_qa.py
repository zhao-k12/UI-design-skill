"""Independent headed candidate geometry/style diagnostics, without admission."""
from decimal import Decimal
from pathlib import Path
import math
import xml.etree.ElementTree as ET
from fontTools.pens.recordingPen import RecordingPen
from fontTools.svgLib.path import parse_path
from adapters.headed_table import require
from adapters.figma.configurable_table_fidelity import paint
from adapters.figma.configurable_font_calibration import measure
from adapters.figma.font_outline_comparison import canonical_directed_contours
from adapters.figma.headed_table_glyph_diagnostic import BINDINGS

def geometry(native,plan,observations,arial):
    nodes=native['nodes'];root=nodes[0];by_name={n['name']:n for n in nodes}
    require(len(by_name)==len(nodes) and native['rootReference']==root['reference'] and native['pageReference']=='82:2','native_inventory_or_page')
    expected={'candidate/'+plan['logicalId']:('COMPONENT',None,{'x':0,'y':0,**plan['rootBounds']},plan['rootFill'])}
    texts=[]
    for row in plan['rows']:
        row_name='source/'+row['path'];expected[row_name]=('FRAME',root['name'],row['bounds'],None)
        for cell in row['cells']:
            name='source/'+cell['path'];expected[name]=('FRAME',row_name,cell['bounds'],cell['fill'])
            t=cell['text'];o=observations[next(n['reference'] for n in nodes if n['name']=='source/'+t['path'])]
            require(o['characters']==t['characters'] and o['fontName']=={'family':t['fontFamily'],'style':t['fontStyle']} and o['absoluteBounds']==by_name['source/'+t['path']]['absoluteBounds'],'outline_text_binding')
            if t['fontFamily']=='Arial':
                encoded=next(r for r in arial['observations'] if r['textReference']==o['textReference']);width=o['absoluteBounds']['width'];baseline=15
                require(encoded['status']=='PASS','arial_cell_encoding')
            else:
                source,advance=measure(*BINDINGS[t['fontStyle']],t['characters'],14);baseline=16;width=math.ceil(advance)
                encoded=[(op,tuple(tuple(Decimal(format(v+(baseline if i==1 else 0),'.6g')) for i,v in enumerate(p)) for p in points)) for op,points in source]
                paths=list(ET.fromstring(o['svg']));require(len(paths)==1 and paths[0].get('fill')=='#515A6E' and paths[0].get('fill-rule','nonzero')=='nonzero','chinese_outline_paint')
                actual=RecordingPen();parse_path(paths[0].attrib['d'],actual)
                a=canonical_directed_contours(encoded)
                require(a==canonical_directed_contours(actual.value) or a==canonical_directed_contours(actual.value,reverse_all=True),'chinese_exact_encoding')
                minimum=lambda commands:tuple(min(Decimal(str(p[i])) for _,points in commands for p in points) for i in (0,1))
                require(minimum(encoded)==minimum(actual.value),'chinese_fixed_baseline')
            bounds={'x':t['sourceTextBounds']['x'],'y':t['sourceBaselineY']-baseline,'width':width,'height':21}
            expected['source/'+t['path']]=('TEXT',name,bounds,t['fill']);texts.append({**t,'textReference':o['textReference'],'nativeBaselineOffset':baseline})
        expected['source/row-border/'+row['path']]=('RECTANGLE',row_name,{'x':row['bounds']['x'],'y':row['bounds']['y']+row['bounds']['height']-row['bottomBorder']['height'],'width':row['bounds']['width'],'height':row['bottomBorder']['height']},row['bottomBorder']['fill'])
    pseudo=plan['bottomPseudo'];expected['source/0.0::before']=('RECTANGLE',root['name'],{'x':0,'y':plan['rootBounds']['height']-pseudo['height'],'width':pseudo['width'],'height':pseudo['height']},pseudo['fill'])
    require(set(expected)==set(by_name),'source_path_inventory')
    for name,(kind,parent,bounds,fill) in expected.items():
        n=by_name[name];p=n['properties'];b=n['absoluteBounds'];r=root['absoluteBounds']
        require(n['type']==kind and n['parentReference']==(by_name[parent]['reference'] if parent else None),'native_parent_or_type')
        require({'x':b['x']-r['x'],'y':b['y']-r['y'],'width':b['width'],'height':b['height']}==bounds,'native_source_geometry')
        require(p['visible'] is True and p['opacity']==1 and p['rotation']==0 and p['effects']==[] and p['strokes']==[] and p['isMask'] is False and p['blendMode']=='PASS_THROUGH' and paint(p['fills'],fill),'native_render_state')
        if kind in ('FRAME','COMPONENT'):
            require(p['clipsContent'] is (parent is None) and p['cornerRadius']==0 and p['layoutMode']==('VERTICAL' if kind=='COMPONENT' else 'HORIZONTAL') and p['itemSpacing']==0 and all(p[k]==0 for k in ('paddingTop','paddingRight','paddingBottom','paddingLeft')) and p['primaryAxisAlignItems']==p['counterAxisAlignItems']=='MIN' and p['layoutSizingHorizontal']==p['layoutSizingVertical']=='FIXED','native_layout_state')
        elif kind=='RECTANGLE':require(p['cornerRadius']==0 and p['layoutPositioning']=='ABSOLUTE','native_border_state')
        else:
            t=next(t for t in texts if t['textReference']==n['reference'])
            require(p['characters']==t['characters'] and p['fontName']=={'family':t['fontFamily'],'style':t['fontStyle']} and p['fontWeight']==t['fontWeight'] and p['fontSize']==14 and p['lineHeight']=={'unit':'PIXELS','value':21} and p['letterSpacing']['value']==0 and p['textAutoResize']=='WIDTH_AND_HEIGHT' and p['layoutPositioning']=='ABSOLUTE' and p['textAlignHorizontal']=='LEFT' and p['textAlignVertical']=='TOP' and p['textCase']=='ORIGINAL' and p['textDecoration']=='NONE' and p['paragraphIndent']==p['paragraphSpacing']==0 and p['textTruncation']=='DISABLED' and p['maxLines'] is None and isinstance(p['textStyleId'],str) and p['textStyleId'].startswith('S:'),'native_text_style')
    return {'status':'PASS','textSamples':texts,'sourcePaths':list(expected),'sourceAutoSizingPreserved':True}



