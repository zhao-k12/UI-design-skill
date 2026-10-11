"""Strict static Table equivalence, using measured native paths and original PNG."""
from decimal import Decimal
import base64
import hashlib
from io import BytesIO
from pathlib import Path
import struct
import re
import xml.etree.ElementTree as ET
from fontTools.pens.recordingPen import RecordingPen
from fontTools.svgLib.path import parse_path
from PIL import Image
from adapters.figma.table_candidate import prepare
from adapters.figma.cross_renderer_normalization import require,bind_vector
from adapters.figma.font_outline_comparison import compare_font_files,measure_glyphs
from adapters.figma.native_capture import verify_saved_capture
from validators.ui_ir import load_json
from validators.visual.fidelity import file_hash,digest
from validators.visual.cross_renderer import compare,REQUIRED_PROOFS


def run(metadata,*,file_reference):
    metadata=Path(metadata);reference_directory=metadata/'table-reference'
    request,_=prepare(reference_directory,metadata,file_reference=file_reference,page_reference='0:1')
    reference=load_json(reference_directory/'component_ir.json')['components'][0]
    directory=metadata/'table-native-capture-v2';require(verify_saved_capture(directory)['status']=='PASS','table_capture_integrity_failed')
    manifest=load_json(directory/'capture_manifest.json');native=load_json(directory/'native-evidence.json')
    require(manifest['fileReference']==file_reference and manifest['componentReference']=='28:3' and manifest['logicalId']==reference['logicalComponentId'] and manifest['evidenceScope']=='production','table_capture_identity_mismatch')
    root=native['nodes'][0];nodes=native['nodes'];root_box=root['absoluteBounds']
    checks=[]
    def check(field,expected,actual):
        require(expected==actual,'table_mismatch:'+field);checks.append({'field':field,'expected':expected,'actual':actual,'status':'PASS'})
    def node(name):
        matches=[n for n in nodes if n['name']==name];require(len(matches)==1,'table_role_ambiguous');return matches[0]
    def bounds(n):
        b=n['absoluteBounds'];return {'x':b['x']-root_box['x'],'y':b['y']-root_box['y'],'width':b['width'],'height':b['height']}
    def paint(field,css,actual):
        m=re.fullmatch(r'rgb\((\d+), (\d+), (\d+)\)',css);require(m is not None,'unsupported_table_paint')
        require(len(actual)==1 and actual[0]['type']=='SOLID' and actual[0].get('opacity',1)==1 and actual[0].get('visible',True) is True,'table_paint_mismatch')
        for channel,value in zip(('r','g','b'),map(int,m.groups())):
            encoded=value/255;require(actual[0]['color'][channel] in (encoded,struct.unpack('f',struct.pack('f',encoded))[0]),'table_paint_mismatch')
        checks.append({'field':field,'source':css,'actual':actual,'status':'PASS'})
    check('root.size',reference['rootBounds'],{k:root_box[k] for k in ('width','height')});check('root.clips',True,root['properties']['clipsContent'])
    check('root.fills',[],root['properties']['fills']);check('root.strokes',[],root['properties']['strokes'])
    for n in nodes:
        for field,expected in [('visible',True),('opacity',1),('rotation',0),('effects',[]),('isMask',False)]:check(n['reference']+'.'+field,expected,n['properties'][field])
        if n['type']=='TEXT':require(n['properties']['blendMode'] in ('NORMAL','PASS_THROUGH'),'unsupported_table_blend')
        else:require(n['properties']['blendMode'] in ('NORMAL','PASS_THROUGH'),'unsupported_table_blend')
    texts=[]
    for row in request['rows']:
        tr=node('source/'+row['path']);check(row['path']+'.bounds',row['bounds'],bounds(tr));check(row['path']+'.parent',root['reference'],tr['parentReference'])
        for cell in row['cells']:
            td=node('source/'+cell['path']);check(cell['path']+'.bounds',cell['bounds'],bounds(td));check(cell['path']+'.parent',tr['reference'],td['parentReference'])
            check(cell['path']+'.strokes',[],td['properties']['strokes']);paint(cell['path']+'.fill',cell['style']['background-color'],td['properties']['fills'])
            text=node('source/'+cell['text']['path']);texts.append(text)
            check(text['name']+'.parent',td['reference'],text['parentReference'])
            for field,value in [('characters',cell['text']['characters']),('fontName',request['fontName']),('fontSize',14),('fontWeight',400),('lineHeight',{'unit':'PIXELS','value':21}),('textCase','ORIGINAL'),('textDecoration','NONE'),('paragraphIndent',0),('paragraphSpacing',0)]:check(text['name']+'.'+field,value,text['properties'][field])
            spacing=text['properties']['letterSpacing'];require(spacing in ({'unit':'PIXELS','value':0},{'unit':'PERCENT','value':0}),'table_nonzero_tracking');checks.append({'field':text['name']+'.tracking','actual':spacing,'normalizedPixels':0,'status':'PASS'})
            check(text['name']+'.position',{'x':cell['text']['x'],'y':cell['text']['y'],'width':cell['text']['width'],'height':21},text['localBounds'])
            paint(text['name']+'.fill',cell['text']['style']['color'],text['properties']['fills'])
        border=node('source/row-border/'+row['path']);check(border['name']+'.bounds',{'x':row['bounds']['x'],'y':row['bounds']['y']+row['bounds']['height']-row['bottomBorder']['height'],'width':row['bounds']['width'],'height':row['bottomBorder']['height']},bounds(border));paint(border['name']+'.fill',row['bottomBorder']['color'],border['properties']['fills']);check(border['name']+'.strokes',[],border['properties']['strokes'])
    pseudo=node('source/0.0::before');check('pseudo.bounds',{'x':0,'y':reference['rootBounds']['height']-request['bottomPseudo']['height'],'width':request['bottomPseudo']['width'],'height':request['bottomPseudo']['height']},bounds(pseudo));paint('pseudo.fill',request['bottomPseudo']['color'],pseudo['properties']['fills'])
    require(len(nodes)==26 and len(texts)==9,'table_native_inventory_mismatch')
    outline=load_json(metadata/'table-text-outline.json');identity=load_json(metadata/'font-file-identity.json')
    require(outline['fileReference']==file_reference and outline['createdNodeIds']==outline['mutatedNodeIds']==[],'invalid_table_outline_capture')
    glyphs=compare_font_files(outline,identity);font=next(r for r in identity['requirements'] if r['familyName']=='PingFang SC')['matches'][0]
    source=load_json(reference_directory/'table-observation.json');paints=[];baselines=[]
    for text,row,baseline in zip(texts,outline['observations'],source['baselines']):
        require(row['textReference']==text['reference'] and row['absoluteBounds']==text['absoluteBounds'] and row['characters']==text['properties']['characters']==baseline['characters'],'table_outline_context_mismatch')
        shape=next(g for g in glyphs['observations'] if g['textReference']==text['reference']);require(shape['contourComparison']['nonzeroWinding']['status']=='PASS','table_glyph_geometry_unverified')
        measured=measure_glyphs(font['path'],font['fileSha256'],row['characters'],14,include_commands=True)
        pen=RecordingPen();paths=list(ET.fromstring(row['svg']));require(len(paths)==1,'unsupported_table_glyph_group');parse_path(paths[0].get('d'),pen)
        translation=[min(Decimal(str(p[i])) for _,pts in pen.value for p in pts)-min(p[i] for _,pts in measured['_commands'] for p in pts) for i in (0,1)]
        require(translation[0]==0,'table_glyph_horizontal_offset')
        actual=Decimal(str(text['absoluteBounds']['y']))-Decimal(str(root_box['y']))+translation[1]
        require(actual==Decimal(str(baseline['baselineComponentY'])),'table_glyph_baseline_mismatch')
        require(bounds(text)['x']==baseline['range']['x'] and measured['advancePx']==baseline['range']['width']==text['absoluteBounds']['width'],'table_advance_mismatch')
        baselines.append({'textReference':text['reference'],'sourceBaseline':baseline['baselineComponentY'],'nativeBaseline':str(actual),'status':'PASS','proof':'Exact full directed path equivalence and common coordinate translation; no rounded extrema comparison.'})
        color=text['properties']['fills'][0]['color'];paints.append({'characters':row['characters'],'region':baseline['range'],'advances':[float(Decimal(g['advanceFontUnits'])*14/Decimal(measured['unitsPerEm'])) for g in measured['glyphs']],'foreground':[round(color[k]*255) for k in ('r','g','b')],'background':[255,255,255]})
    blend=load_json(metadata/'table-blend-experiment.json')
    require(blend['scope']=='figma_table_blend_bound_capture' and blend['status']=='PASS' and blend['fileReference']==file_reference and blend['componentReference']==manifest['componentReference'] and blend['createdNodeIds']==[] and blend['issues']==[] and blend['originalObservedStateRestored'] is True and blend['unrelatedPropertiesUnchanged'] is True,'invalid_table_blend_probe')
    require(blend['mutatedNodeIds']==blend['restoredNodeIds']==[t['reference'] for t in texts] and blend['nativeEvidenceSha256']==digest(native),'table_blend_observation_mismatch')
    require(all(blend['pngHashes'][stage]==manifest['nativePngSha256'] for stage in ('before','normal','restored')),'table_blend_pixels_changed')
    raster=blend['normalRaster'];require(raster['format']=='PNG' and raster['scale']==1 and raster['encoding']=='base64','invalid_table_blend_raster')
    data=base64.b64decode(raster['data'],validate=True);require(hashlib.sha256(data).hexdigest()==manifest['nativePngSha256'],'table_blend_png_binding_mismatch')
    with Image.open(BytesIO(data)) as image,Image.open(directory/'native.png') as baseline_png:require(image.convert('RGBA').tobytes()==baseline_png.convert('RGBA').tobytes(),'table_blend_independent_pixels_changed')
    font_probe=load_json(metadata/'table-font-file-binding.json');svg_probe=load_json(metadata/'table-svg-browser-evidence.json');vector=load_json(metadata/'table-component-svg-v2.json')
    for p in (font_probe,svg_probe):require(p['status']=='PASS' and p['referenceComponentIrSha256']==file_hash(reference_directory/'component_ir.json') and len(p['referenceMatches'])==1 and p['referenceMatches'][0]=={'logicalId':'data.table.default','screenshotMatches':True,'environmentMatches':True},'table_reference_not_reproduced')
    require(font_probe['fontFileSha256']==font['fileSha256'] and font_probe['ownerStatesRestored'] is True and font_probe['temporaryFontFaceRemoved'] is True and font_probe['observations'][0]['ownerBoundsUnchanged'] is True and font_probe['observations'][0]['pngSha256']==reference['screenshot']['sha256'],'table_font_file_effect_unverified')
    require(svg_probe['svgCaptureSha256']==file_hash(metadata/'table-component-svg-v2.json'),'table_vector_binding_mismatch')
    bind_vector(vector['observations'][0]['svg'],outline['observations'],native,text_fill='#515A6E')
    vector_png=metadata/'table-svg-browser.png';require(file_hash(vector_png)==svg_probe['samples'][0]['pngSha256'],'table_vector_raster_mismatch')
    def outside_text(left,right):
        boxes=[p['region'] for p in paints]
        return sum(a!=b and not any(r['x']<=i%left.width+.5<r['x']+r['width'] and r['y']<=i//left.width+.5<r['y']+r['height'] for r in boxes) for i,(a,b) in enumerate(zip(left.getdata(),right.getdata())))
    reference_png=reference_directory/reference['screenshot']['path'];native_png=directory/'comparison-white.png'
    with Image.open(reference_png) as a,Image.open(vector_png) as v,Image.open(native_png) as b:
        a,v,b=a.convert('RGBA'),v.convert('RGBA'),b.convert('RGBA');require(a.size==v.size==b.size,'table_raster_size_mismatch');require(outside_text(a,v)==outside_text(a,b)==0,'table_nontext_pixels_differ')
    proof={'geometryAndStyle':checks,'glyphGeometry':glyphs,'baselines':baselines,
        'inputHashes':{str(p.relative_to(metadata)):file_hash(p) for p in [reference_directory/'component_ir.json',reference_directory/'table-observation.json',metadata/'table-text-outline.json',metadata/'table-font-file-binding.json',metadata/'table-component-svg-v2.json',metadata/'table-svg-browser-evidence.json',metadata/'table-blend-experiment.json',directory/'native-evidence.json']},'nontextChangedPixels':0}
    candidate={**{k:reference[k] for k in ('logicalComponentId','variant','state','props','content','fixtureContext')},'normalizationVersion':'0.2.0','scope':'production','evidenceKind':'native-design-capture','sourceVersion':reference['provenance']['sourceVersion'],'componentIrSha256':digest(reference),'verification':dict.fromkeys(REQUIRED_PROOFS,'PASS'),'glyphPaintSamples':paints,'allowedCornerRegions':[],
        'rasterContext':{'deviceScaleFactor':1,'background':'white','scale':1,'resize':False,'crop':False},'screenshotSha256':file_hash(native_png),'vectorRasterSha256':file_hash(vector_png),
        'capture':{**{k:manifest[k] for k in ('captureId','exporterVersion','nativeEvidenceSha256')},'proofBundleSha256':digest(proof)}}
    return {'report':compare(reference,candidate,reference_png,native_png,vector_png),'candidate':candidate,'proof':proof}
