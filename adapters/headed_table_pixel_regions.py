"""Source-derived positive-area pixel ownership; not a complete fidelity gate."""
from io import BytesIO
import json
from pathlib import Path
from PIL import Image
from adapters.headed_table import prepare_source, require
from adapters.headed_table_png import verify_raw_png
from adapters.headed_table_policy import require_scope, DECISION_SHA256
from validators.visual.fidelity import file_hash

def intersects(rect,x,y):
    return rect['x']<x+1 and x<rect['x']+rect['width'] and rect['y']<y+1 and y<rect['y']+rect['height']

def source_regions(source_dir):
    plan=prepare_source(source_dir);require_scope(plan)
    texts=[dict(c['text']['sourceTextBounds']) for r in plan['rows'] for c in r['cells']]
    lines=[]
    for row in plan['rows']:
        b=row['bounds'];border=row['bottomBorder']
        require(border['height']==1,'headed_horizontal_source_height_mismatch')
        lines.append({'sourcePath':row['path'],'region':{'x':b['x'],'y':b['y']+b['height']-border['height'],'width':b['width'],'height':border['height']},'fill':border['fill']})
    pseudo=plan['bottomPseudo'];require(pseudo['height']==1,'headed_horizontal_pseudo_height_mismatch')
    lines.append({'sourcePath':'0.0::before','region':{'x':0,'y':plan['rootBounds']['height']-pseudo['height'],'width':pseudo['width'],'height':pseudo['height']},'fill':pseudo['fill']})
    return plan,texts,lines

def compare_regions(source_dir,platform,raw):
    source_dir=Path(source_dir);plan,texts,lines=source_regions(source_dir)
    context=verify_raw_png(plan,platform,raw)
    source=json.loads((source_dir/'component_ir.json').read_text(encoding='utf8'))['components'][0]
    path=source_dir/source['screenshot']['path']
    require(file_hash(path)==source['screenshot']['sha256'],'headed_region_source_png_binding_mismatch')
    reference=Image.open(path).convert('RGBA');actual=Image.open(BytesIO(raw)).convert('RGBA')
    require(reference.size==actual.size,'headed_region_size_mismatch')
    counts={'text':0,'horizontal':0,'outside':0};total=0
    for y in range(actual.height):
        for x in range(actual.width):
            if actual.getpixel((x,y))==reference.getpixel((x,y)): continue
            total+=1
            category='text' if any(intersects(r,x,y) for r in texts) else 'horizontal' if any(intersects(row['region'],x,y) for row in lines) else 'outside'
            counts[category]+=1
    require(counts['outside']==0,'headed_difference_outside_source_regions')
    return {'status':'PASS','scope':'native-png-source-pixel-ownership-only','platform':platform,
            'logicalId':plan['logicalId'],'decisionSha256':DECISION_SHA256,'pngContext':context,
            'sourcePngSha256':file_hash(path),'differentPixels':total,'categories':counts,
            'horizontalRegions':lines,'pixelRegionPolicy':'positive-area-intersection-no-padding',
            'fidelityGate':'NOT_RUN','productionAdmission':False,
            'limitations':['Text requires independent glyph, baseline, paint and retention checks.',
                           'Horizontal regions require exact vector style, full coverage and edge checks.',
                           'Region ownership alone does not admit differences inside these regions.']}
