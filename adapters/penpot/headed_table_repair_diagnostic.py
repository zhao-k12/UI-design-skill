"""Independent repair readback and raw pixel classification, not admission."""
import argparse
import base64
import json
from io import BytesIO
from pathlib import Path
from PIL import Image
from adapters.headed_table import prepare_penpot
from adapters.headed_table_policy import header_background_union
from adapters.penpot.headed_table_qa import validate_geometry
from validators.ui_ir import ROOT

FONTS = {
    'Arial/400': {'fontId':'custom-b65bc280-c7a5-8006-8008-c4950e2dd987','fontVariantId':'normal-400'},
    'PingFang SC/400': {'fontId':'custom-5ad61700-1d7d-8066-8008-c08a8bdbd70d','fontVariantId':'normal-400'},
    'PingFang SC/600': {'fontId':'custom-5ad61700-1d7d-8066-8008-c08a8bdbd70d','fontVariantId':'normal-600'},
}

def intersects(rect, x, y):
    return rect['x'] < x+1 and x < rect['x']+rect['width'] and rect['y'] < y+1 and y < rect['y']+rect['height']

def diagnose(receipt, source_dir):
    native=json.loads(Path(receipt).read_text(encoding='utf8'))['result']
    plan=prepare_penpot(source_dir,native['fileReference'],native['pageReference'])
    plan['headerBackgroundUnion']=header_background_union(plan)
    geometry=validate_geometry(native,plan,FONTS)
    source=json.loads((Path(source_dir)/'component_ir.json').read_text(encoding='utf8'))['components'][0]
    reference=Image.open(Path(source_dir)/source['screenshot']['path']).convert('RGBA')
    raw=base64.b64decode(native['nativePngBase64'],validate=True)
    actual=Image.open(BytesIO(raw)).convert('RGBA')
    if actual.size!=reference.size or actual.getextrema()[3]!=(255,255): raise ValueError('headed_raw_png_context_mismatch')
    texts=[c['text']['sourceTextBounds'] for row in plan['rows'] for c in row['cells']]
    lines=[{'x':r['bounds']['x'],'y':r['bounds']['y']+r['bounds']['height']-r['bottomBorder']['height'],
            'width':r['bounds']['width'],'height':r['bottomBorder']['height']} for r in plan['rows']]
    lines.append({'x':0,'y':plan['rootBounds']['height']-plan['bottomPseudo']['height'],'width':plan['bottomPseudo']['width'],'height':plan['bottomPseudo']['height']})
    changed=outside=0
    for y in range(actual.height):
        for x in range(actual.width):
            if reference.getpixel((x,y))!=actual.getpixel((x,y)):
                changed+=1
                outside+=not any(intersects(r,x,y) for r in texts+lines)
    return {'status':'OBSERVED','fidelityGate':'NOT_RUN','productionAdmission':False,
            'logicalId':plan['logicalId'],'geometry':geometry,'differentPixels':changed,
            'outsideTextAndExactHorizontalRegions':outside,'nativeAlpha':[255,255]}, raw

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--receipt',type=Path,required=True)
    parser.add_argument('--source',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();report,raw=diagnose(args.receipt,args.source)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    args.output.with_suffix('.png').write_bytes(raw)
    print(json.dumps({k:v for k,v in report.items() if k!='geometry'},ensure_ascii=False))
