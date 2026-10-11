"""Exact native glyph diagnostic; does not extend any approved admission scope."""
import json,math
from pathlib import Path
from decimal import Decimal
import xml.etree.ElementTree as ET
from fontTools.pens.recordingPen import RecordingPen
from fontTools.svgLib.path import parse_path
from adapters.figma.configurable_font_calibration import measure
from adapters.figma.font_outline_comparison import canonical_directed_contours
from adapters.figma.true_type_encoding_diagnostic import verify,runtime
from validators.ui_ir import ROOT,load_json
from validators.visual.fidelity import file_hash
from adapters.headed_table import require

BINDINGS={
    'Regular':('C:/Users/38442/AppData/Local/Microsoft/Windows/Fonts/PingFang SC-Regular.otf','0934ea94dea57d9ec12a401f44ad28b98c96f5ee9917df920279f58024de523a'),
    'Semibold':('C:/Users/38442/AppData/Local/Microsoft/Windows/Fonts/PingFang SC-Semibold.otf','ca115f4f17266f1ff5ead3ef1049814eafb4f61cc279134e0a8b3d817532fb78')}

def inspect(path):
    capture=load_json(path)
    require(capture['status']=='PASS' and capture['fileReference']=='0vGWSRoLxBiVPXiZ8xJAX9' and capture['pageReference']=='82:2' and not capture['createdNodeIds'] and not capture['mutatedNodeIds'],'invalid_headed_outline_context')
    expected=load_json(Path(path).parent/'creation.json')
    refs={ref for candidate in expected['candidates'] for ref in candidate['textReferences']}
    require(len(capture['observations'])==len(refs)==26 and {o['textReference'] for o in capture['observations']}==refs,'headed_outline_inventory')
    ft=runtime(ROOT/'artifacts/task-019/freetype-probe-deps');rows=[]
    for o in capture['observations']:
        if o['fontName']['family']=='Arial':
            result=verify(o,Path('C:/Windows/Fonts/arial.ttf'),ft)
        else:
            style=o['fontName']['style'];require(style in BINDINGS and o['fontName']['family']=='PingFang SC' and o['fontSize']==14 and o['lineHeight']=={'unit':'PIXELS','value':21} and o['fontWeight']==(600 if style=='Semibold' else 400),'unsupported_headed_cff_font')
            source,advance=measure(*BINDINGS[style],o['characters'],14)
            encoded=[(op,tuple((Decimal(format(p[0],'.6g')),Decimal(format(p[1]+16,'.6g'))) for p in points)) for op,points in source]
            paths=list(ET.fromstring(o['svg']));require(len(paths)==1 and paths[0].get('fill')=='#515A6E' and paths[0].get('fill-rule','nonzero')=='nonzero','unsupported_headed_cff_path')
            native=RecordingPen();parse_path(paths[0].attrib['d'],native)
            exact=canonical_directed_contours(encoded) in (canonical_directed_contours(native.value),canonical_directed_contours(native.value,reverse_all=True))
            minima=lambda commands:tuple(min(Decimal(str(p[i])) for _,points in commands for p in points) for i in (0,1))
            intrinsic=o['absoluteBounds']['width']==math.ceil(advance) and o['absoluteBounds']['height']==21
            result={'textReference':o['textReference'],'characters':o['characters'],'fontStyle':style,'sourceFontSha256':BINDINGS[style][1],'exactCffEncoding':exact,'fixedBaselinePx':16,'fixedBaselineEqual':minima(encoded)==minima(native.value),'intrinsicDimensionsEqual':intrinsic,'status':'PASS' if exact and intrinsic and minima(encoded)==minima(native.value) else 'FAIL'}
        rows.append(result)
    return {'scope':'task020_glyph_diagnostic','status':'OBSERVED' if all(r['status']=='PASS' for r in rows) else 'REVIEW','captureSha256':file_hash(path),'programSha256':file_hash(__file__),'observations':rows,'fontEncodingAdmission':'NOT_APPROVED','fidelityGate':'NOT_RUN','admissionEligible':False}

if __name__=='__main__':
    directory=ROOT/'adapters/figma/metadata/headed-table-native';report=inspect(directory/'text-outlines.json');(directory/'glyph-diagnostic.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({'status':report['status'],'count':len(report['observations']),'failures':[r['textReference'] for r in report['observations'] if r['status']!='PASS']}))
