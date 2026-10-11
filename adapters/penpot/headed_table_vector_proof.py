"""Independent SVG rectangles and exact source raster outside horizontal edges."""
import base64
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from PIL import Image
from adapters.headed_table import prepare_penpot,require
from adapters.headed_table_policy import header_background_union
from adapters.penpot.headed_table_qa import validate_geometry
from adapters.penpot.headed_table_repair_diagnostic import FONTS,intersects
from validators.visual.fidelity import file_hash

def own_elements(element):
    for child in element:
        if child.get('id','').startswith('shape-'): continue
        yield child
        yield from own_elements(child)

def evaluate(receipt_path,source_dir,probe_dir):
    native=json.loads(Path(receipt_path).read_text(encoding='utf8'))['result']
    plan=prepare_penpot(source_dir,native['fileReference'],native['pageReference'])
    plan['headerBackgroundUnion']=header_background_union(plan)
    validate_geometry(native,plan,FONTS)
    probe=json.loads((Path(probe_dir)/'svg-probe.json').read_text(encoding='utf8'))
    require(probe['status']=='OBSERVED' and probe['scope']=='penpot-headed-native-svg-browser-diagnostic' and probe['nativeReceiptSha256']==file_hash(receipt_path) and probe['referenceComponentIrSha256']==file_hash(Path(source_dir)/'component_ir.json') and probe['probeScriptSha256']==file_hash(Path(__file__).with_name('headed_table_svg_probe.mjs')),'headed_vector_probe_binding_mismatch')
    raw=base64.b64decode(native['nativeSvgBase64'],validate=True)
    require(sha256(raw).hexdigest()==probe['sample']['svgSha256'],'headed_native_svg_binding_mismatch')
    require(file_hash(Path(probe_dir)/'native-svg.png')==probe['sample']['pngSha256'] and probe['sample']['fontLoadStatus'],'headed_vector_png_binding_mismatch')
    locked={'Arial':('Arial',400,'2035b173b6273ac11ffb25fd61d271753cca918bcc325dfdd7eebd636a0ea6d3'),
            'PingFang SC':('PingFang SC',400,'7ce5d241353a41d6c9fd02b905967ad800f19d534abd3d46eb67e46b0d18099a'),
            'PingFang SC Semibold':('PingFang SC',600,'7b5dffa57f71e3de21fc332144e11ec3a7066f03bbcd100ae7a7b73ebda1bb0f')}
    resources=probe['sample']['fontResources'];require(set(resources)==set(locked),'headed_vector_font_inventory_mismatch')
    for key,(family,weight,digest) in locked.items():
        item=resources[key]
        require((item['family'],item['weight'],item['sha256'])==(family,weight,digest) and file_hash(item['path'])==digest,'headed_vector_font_container_mismatch')
    root=ET.fromstring(raw)
    require(root.get('width')==str(plan['rootBounds']['width']) and Decimal(root.get('height'))==Decimal(str(plan['rootBounds']['height'])),'headed_vector_root_mismatch')
    groups={e.get('id')[6:]:e for e in root.iter() if e.get('id','').startswith('shape-')}
    require(set(groups)=={n['reference'] for n in native['nodes']},'headed_vector_shape_inventory_mismatch')
    rectangles=[]
    for node in native['nodes']:
        if node['type']=='text': continue
        elements=list(own_elements(groups[node['reference']]))
        paints=[e for e in elements if e.tag.endswith('}rect') and 'fill:' in e.get('style','')]
        if not node['fills']:
            require(not paints,'headed_vector_transparent_wrapper_changed');continue
        require(len(paints)==1,'headed_vector_paint_inventory_mismatch')
        rectangle=paints[0];origin=native['nodes'][0]
        for key,value in {'x':node['x']-origin['x'],'y':node['y']-origin['y'],'width':node['width'],'height':node['height']}.items():
            require(Decimal(rectangle.get(key,'0'))==Decimal(str(value)),'headed_vector_rectangle_mismatch')
        fill=node['fills'][0]['fillColor'];rgb=[int(fill[i:i+2],16) for i in (1,3,5)]
        require(rectangle.get('style')==f'fill: rgb({rgb[0]}, {rgb[1]}, {rgb[2]}); fill-opacity: 1;','headed_vector_fill_mismatch')
        require(rectangle.get('rx','0')==rectangle.get('ry','0')=='0','headed_vector_corner_mismatch')
        rectangles.append({'reference':node['reference'],'bounds':{k:rectangle.get(k,'0') for k in ('x','y','width','height')},'fill':fill})
    lines=[{'x':r['bounds']['x'],'y':r['bounds']['y']+r['bounds']['height']-1,'width':r['bounds']['width'],'height':1} for r in plan['rows']]
    lines.append({'x':0,'y':plan['rootBounds']['height']-1,'width':plan['rootBounds']['width'],'height':1})
    source=json.loads((Path(source_dir)/'component_ir.json').read_text(encoding='utf8'))['components'][0]
    a=Image.open(Path(source_dir)/source['screenshot']['path']).convert('RGBA')
    b=Image.open(Path(probe_dir)/'native-svg.png').convert('RGBA')
    require(a.size==b.size and a.getextrema()[3]==b.getextrema()[3]==(255,255),'headed_vector_raster_context_mismatch')
    changed=outside=0
    for y in range(a.height):
        for x in range(a.width):
            if a.getpixel((x,y))!=b.getpixel((x,y)):
                changed+=1;outside+=not any(intersects(r,x,y) for r in lines)
    require(outside==0,'headed_vector_difference_outside_horizontal_regions')
    return {'status':'PASS','scope':'headed-table-native-vector-geometry-and-source-raster-only','productionAdmission':False,'fidelityGate':'NOT_RUN',
            'nativeReceiptSha256':file_hash(receipt_path),'probeSha256':file_hash(Path(probe_dir)/'svg-probe.json'),
            'rectangles':rectangles,'changedPixels':changed,'outsideExactHorizontalRegions':outside,
            'wholeTextAndNonHorizontalPixelsExactlyMatchSource':True}
