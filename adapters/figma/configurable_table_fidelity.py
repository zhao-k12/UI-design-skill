"""Independent full TASK-019 Figma Table checks, using native evidence only."""
import base64
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import struct
import xml.etree.ElementTree as ET
from PIL import Image
from fontTools.pens.recordingPen import RecordingPen
from fontTools.svgLib.path import parse_path
from adapters.configurable_table import prepare_source, require
from adapters.figma.configurable_font_calibration import measure
from adapters.figma.font_outline_comparison import canonical_directed_contours
from adapters.figma.outline_geometry import inspect_capture
from adapters.figma.true_type_encoding_diagnostic import inspect as inspect_arial, runtime
from adapters.penpot.configurable_table_fidelity import FONT_HASHES
from adapters.penpot.table_pixel_coverage import compare, REQUIRED_PROOFS
from validators.ui_ir import ROOT, load_json
from validators.visual.fidelity import digest, file_hash

META=ROOT/'adapters/figma/metadata/configurable-table-native'
SOURCE=ROOT/'component-builder/runtime-renderer/metadata/configurable-table-source'
FONTS={'Arial':Path('C:/Windows/Fonts/arial.ttf'),'PingFang SC':Path('C:/Users/38442/AppData/Local/Microsoft/Windows/Fonts/PingFang SC-Regular.otf')}
COMPONENTS={'two-column':'69:4','four-column':'69:18'}
APPROVED_DECISION_SHA='ca43541c9b0015f99a8982c8acc64830cb46efe0ae7a3f7d9931f94377bae349'


def transport(path):
    receipt=load_json(path);pieces=receipt['pieces']
    require(pieces and len(pieces)==pieces[0]['count'],'capture_piece_inventory')
    for i,piece in enumerate(pieces):
        require(piece['scope']=='figma_capture_transport_piece' and piece['status']=='PASS' and piece['index']==i and all(piece[k]==pieces[0][k] for k in ('count','totalCharacters','captureSha256')),'capture_piece_binding')
    text=''.join(p['chunk'] for p in pieces)
    require(len(text)==pieces[0]['totalCharacters'] and hashlib.sha256(text.encode()).hexdigest()==pieces[0]['captureSha256'],'capture_transport_hash')
    return json.loads(text)


def outlines():
    singles=[load_json(META/f'arial-glyph-readback-{i}.json') for i in range(1,5)]
    tables=[capture for i in (0,1) for capture in load_json(META/f'table-text-outlines-{i}.json')]
    for capture in tables: inspect_capture(capture)
    arial=inspect_arial(singles+tables,FONTS['Arial'],runtime(ROOT/'artifacts/task-019/freetype-probe-deps'))
    require(arial['status']=='PASS','arial_encoding_failed')
    observations={o['textReference']:o for c in tables for o in c['observations']}
    require(len(observations)==20,'table_outline_inventory')
    return observations,arial


def paint(actual,hex_color):
    if hex_color is None: return actual==[]
    if len(actual)!=1: return False
    p=actual[0];rgb={k:struct.unpack('f',struct.pack('f',int(hex_color[i:i+2],16)/255))[0] for k,i in zip(('r','g','b'),(1,3,5))}
    return p=={'type':'SOLID','color':rgb,'opacity':1,'visible':True,'blendMode':'NORMAL','boundVariables':{}}


def geometry(native,plan,observations,arial):
    nodes=native['nodes'];root=nodes[0];by_name={n['name']:n for n in nodes}
    require(len(by_name)==len(nodes) and native['rootReference']==root['reference'] and native['pageReference']=='69:2','native_inventory_or_page')
    expected={'candidate/'+plan['logicalId']:('COMPONENT',None,{'x':0,'y':0,**plan['rootBounds']},plan['rootFill'])}
    texts=[]
    for row in plan['rows']:
        row_name='source/'+row['path'];expected[row_name]=('FRAME',root['name'],row['bounds'],None)
        for cell in row['cells']:
            name='source/'+cell['path'];expected[name]=('FRAME',row_name,cell['bounds'],cell['fill'])
            t=cell['text'];o=observations[next(n['reference'] for n in nodes if n['name']=='source/'+t['path'])]
            require(o['characters']==t['characters'] and o['fontName']=={'family':t['fontFamily'],'style':'Regular'} and o['absoluteBounds']==by_name['source/'+t['path']]['absoluteBounds'],'outline_text_binding')
            if t['fontFamily']=='Arial':
                encoded=next(r for r in arial['observations'] if r['textReference']==o['textReference']);width=o['absoluteBounds']['width'];baseline=15
                require(encoded['status']=='PASS','arial_cell_encoding')
            else:
                source,advance=measure(FONTS['PingFang SC'],FONT_HASHES['PingFang SC'],t['characters'],14);baseline=16;width=math.ceil(advance)
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
            require(p['characters']==t['characters'] and p['fontName']=={'family':t['fontFamily'],'style':'Regular'} and p['fontWeight']==400 and p['fontSize']==14 and p['lineHeight']=={'unit':'PIXELS','value':21} and p['letterSpacing']['value']==0 and p['textAutoResize']=='WIDTH_AND_HEIGHT' and p['layoutPositioning']=='ABSOLUTE' and p['textAlignHorizontal']=='LEFT' and p['textAlignVertical']=='TOP' and p['textCase']=='ORIGINAL' and p['textDecoration']=='NONE' and p['paragraphIndent']==p['paragraphSpacing']==0 and p['textTruncation']=='DISABLED' and p['maxLines'] is None and isinstance(p['textStyleId'],str) and p['textStyleId'].startswith('S:'),'native_text_style')
    return {'status':'PASS','textSamples':texts,'sourcePaths':list(expected),'sourceAutoSizingPreserved':True}


def evaluate(case,output):
    require(case in COMPONENTS,'unsupported_table_case');output=Path(output).resolve()
    require(file_hash(ROOT/'.dev/TASK-019_ARIAL_ENCODING_DECISION.md')==APPROVED_DECISION_SHA,'arial_decision_binding')
    require(output.is_relative_to(ROOT/'artifacts') and not output.exists(),'independent_new_output_required')
    plan=prepare_source(SOURCE/case);reference=load_json(SOURCE/case/'component_ir.json')['components'][0]
    capture=transport(META/f'table-capture-after-sizing-pieces-{0 if case=="two-column" else 1}.json')
    require(capture['status']=='PASS' and capture['evidenceKind']=='native-platform-export' and capture['evidenceScope']=='production' and capture['fileReference']=='0vGWSRoLxBiVPXiZ8xJAX9' and capture['componentReference']==COMPONENTS[case] and capture['logicalId']==plan['logicalId'],'capture_context')
    native=capture['nativeEvidence'];saved=META/(case+'-native-after-sizing')
    require(native==load_json(saved/'native-evidence.json'),'native_saved_evidence_mismatch')
    require(capture['raster']['format']=='PNG' and capture['raster']['scale']==1 and not capture['createdNodeIds'] and not capture['mutatedNodeIds'],'native_export_format_or_writes')
    png=bytes(capture['raster']['bytes'])
    require(png==(saved/'native.png').read_bytes(),'native_saved_png_mismatch')
    observation,arial=outlines();geom=geometry(native,plan,observation,arial)
    svg_path=META/(case+'-component-svg.json');svg=load_json(svg_path);svgrow=svg['observations'][0]
    require(svg['status']=='PASS' and not svg['createdNodeIds'] and not svg['mutatedNodeIds'] and svg['fileReference']==capture['fileReference'] and svg['pageReference']==native['pageReference'] and svg['nativePngSha256']==hashlib.sha256(png).hexdigest() and svg['nativeEvidenceJsonSha256']==hashlib.sha256(json.dumps(native,ensure_ascii=False,separators=(',',':')).encode()).hexdigest() and svgrow['componentReference']==COMPONENTS[case] and svgrow['logicalId']==plan['logicalId'],'whole_svg_binding')
    probe_dir=META/(case+'-svg-probe');probe=load_json(probe_dir/'native-svg-raster-report.json');sample=probe['samples'][0];vector=probe_dir/sample['pngPath']
    require(probe['status']=='PASS' and probe['svgCaptureSha256']==file_hash(svg_path) and probe['referenceComponentIrSha256']==file_hash(SOURCE/case/'component_ir.json') and probe['probeScriptSha256']==file_hash(ROOT/'component-builder/runtime-renderer/native-svg-probe.mjs') and sample['svgSha256']==hashlib.sha256(svgrow['svg'].encode()).hexdigest() and sample['pngSha256']==file_hash(vector) and probe['referenceMatches']==[{'logicalId':plan['logicalId'],'screenshotMatches':True,'environmentMatches':True}],'vector_probe_binding')
    font_dir=META/(case+'-font-probe');font=load_json(font_dir/'font-file-probe.json');effect=font['observation']
    require(font['status']=='OBSERVED' and font['referenceComponentIrSha256']==file_hash(SOURCE/case/'component_ir.json') and font['probeScriptSha256']==file_hash(Path(__file__).with_name('configurable_table_probes.mjs')) and font['ownerStatesRestored'] and font['temporaryFontFacesRemoved'] and effect['ownerBoundsUnchanged'] and effect['fontLoadStatus']==['loaded','loaded'] and effect['pngSha256']==file_hash(font_dir/'file-bound.png')==reference['screenshot']['sha256'] and all(font['fontFiles'][family]['sha256']==file_hash(FONTS[family])==FONT_HASHES[family] for family in FONTS),'source_font_effect_binding')
    # Source-identical independent Penpot SVG supplies observed source character
    # positions for the retention guard; no positions are written into Figma.
    penpot_meta=ROOT/'adapters/penpot/metadata/configurable-table-native'
    source_probe=load_json(penpot_meta/case/'after-background/svg-probe.json')
    source_capture=load_json(penpot_meta/(case+'-capture-after-background.json'))
    require(source_probe['nativeReceiptSha256']==file_hash(penpot_meta/(case+'-capture-after-background.json')) and source_probe['sample']['pngSha256']==reference['screenshot']['sha256'],'retention_source_vector_binding')
    paints=[]
    for t in geom['textSamples']:
        b=t['sourceTextBounds'];source_nodes=[n for n in source_capture['result']['nodes'] if n['name'].replace(' / ','/')=='official-source/'+t['path']]
        require(len(source_nodes)==1,'retention_source_node_binding')
        matches=[s for s in source_probe['sample']['texts'] if s['textReference']==source_nodes[0]['reference'] and s['characters']==t['characters'] and s['start'][0]['x']==b['x'] and s['length']==b['width']]
        require(len(matches)==1,'retention_source_text_binding');s=matches[0];ends=s['start'][1:]+[s['end'][-1]]
        advances=[float(Decimal(str(end['x']))-Decimal(str(start['x']))) for start,end in zip(s['start'],ends)]
        paints.append({'characters':t['characters'],'region':b,'advances':advances,'foreground':[81,90,110],'background':[255,255,255]})
    output.mkdir(parents=True);(output/'native.png').write_bytes(png)
    with Image.open(output/'native.png') as image: require(image.size==(plan['rootBounds']['width'],plan['rootBounds']['height']) and image.convert('RGBA').getextrema()[3]==(255,255),'native_png_size_or_alpha')
    proof={'platform':'figma','approvedArialDecisionSha256':APPROVED_DECISION_SHA,'geometryAndStyle':geom,'fontBinding':font,'glyphGeometry':{'status':'PASS','Arial':arial,'PingFang SC':'exact fixed-baseline directed CFF encoding'},'baselines':{'status':'PASS','textSamples':geom['textSamples']},'vectorBinding':{'status':'PASS','captureSha256':file_hash(svg_path),'probe':probe},'content':{'status':'PASS'},'renderState':{'status':'PASS','nativeEvidenceSha256':digest(native)},'sourceReproduction':probe['referenceMatches'],'retentionSourceProbe':digest(source_probe)}
    candidate={'normalizationVersion':'0.2.1','pixelRegionPolicy':'positive-area-intersection','scope':'production','evidenceKind':'native-design-capture',**{k:reference[k] for k in ('logicalComponentId','variant','state','props','content','fixtureContext')},'sourceVersion':reference['provenance']['sourceVersion'],'componentIrSha256':digest(reference),'verification':dict.fromkeys(REQUIRED_PROOFS,'PASS'),'glyphPaintSamples':paints,'allowedCornerRegions':[],'rasterContext':{'deviceScaleFactor':1,'background':'white','scale':1,'resize':False,'crop':False},'screenshotSha256':file_hash(output/'native.png'),'vectorRasterSha256':file_hash(vector),'capture':{'captureId':capture['captureId'],'exporterVersion':'figma-configurable-table-normalization-0.2.1','nativeEvidenceSha256':digest(native),'proofBundleSha256':digest(proof)}}
    report=compare(reference,candidate,SOURCE/case/reference['screenshot']['path'],output/'native.png',vector)
    for name,data in [('proof.json',proof),('candidate.json',candidate),('gate-report.json',report)]: (output/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return report


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('case',choices=COMPONENTS);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    report=evaluate(args.case,args.output);print(json.dumps(report));raise SystemExit(0 if report['status']=='PASS' else 1)
