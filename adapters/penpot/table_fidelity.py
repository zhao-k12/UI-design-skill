"""Evidence-bound acceptance for the one immutable native Table fixture."""
import base64
import json
from pathlib import Path
from decimal import Decimal,ROUND_HALF_UP
import re
from PIL import Image
from validators.visual.fidelity import digest,file_hash
from validators.visual.cross_renderer import compare,REQUIRED_PROOFS
from adapters.penpot.table_candidate import prepare_table_candidate,require
from adapters.penpot.pdf_glyph_geometry import extract_type3_glyphs,compare_glyphs

SOURCE_FONT='0934ea94dea57d9ec12a401f44ad28b98c96f5ee9917df920279f58024de523a'


def validate_geometry(native,plan,font):
    require(native['status']=='CAPTURED' and native['scope']=='production' and native['platform']=='penpot' and native['evidenceKind']=='native-platform-export' and not native['createdNodeIds'] and not native['mutatedNodeIds'],'invalid_table_capture')
    require(native['logicalId']==plan['logicalId'] and native['componentIrSha256']==plan['componentIrSha256'] and native['fileReference']==plan['fileReference'] and native['pageReference']==plan['pageReference'],'table_context_or_source_mismatch')
    nodes=native['nodes'];root=nodes[0];require(len(nodes)==26 and len({n['reference'] for n in nodes})==26 and root['reference']==native['mainReference'],'table_node_inventory_mismatch')
    expected={plan['name']:('board',None,{'x':0,'y':0,**plan['rootBounds']},None)}
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
        text=by_name[name]
        require(text['characters']==item['characters'] and text['fontFamily']=='PingFang SC' and text['fontId']==font['fontId'] and text['fontVariantId']==font['fontVariantId'] and float(text['fontSize'])==14 and float(text['fontWeight'])==400 and text['fontStyle']=='normal' and float(text['lineHeight'])==16/14 and float(text['letterSpacing'])==0 and text['growType']=='fixed' and text['align']=='left' and text['verticalAlign']=='top' and text['direction']=='ltr' and text['textTransform']=='none' and text['textDecoration']=='none','table_text_style_mismatch')
    return {'status':'PASS','textSamples':[item for name,item in texts],'sourcePaths':list(expected),
        'borderNormalization':'Contiguous same-color cell borders form one row region; independent bottom pseudo and outer clipping are preserved.'}


def evaluate(capture_path,probe_directory,reference_directory,source_font,font_binding,output_directory):
    from pypdf import PdfReader
    capture_path=Path(capture_path);probe_directory=Path(probe_directory);reference_directory=Path(reference_directory);output=Path(output_directory)
    require(not output.exists() or not any(output.iterdir()),'fidelity_output_not_empty')
    receipt=json.loads(capture_path.read_text(encoding='utf-8'));require(receipt['status']=='CAPTURED','host_capture_failed');native=receipt['result']
    plan=prepare_table_candidate(reference_directory,native['fileReference'],native['pageReference']);geometry=validate_geometry(native,plan,font_binding)
    reference=json.loads((reference_directory/'component_ir.json').read_text(encoding='utf-8'))['components'][0]
    probe=json.loads((probe_directory/'svg-probe.json').read_text(encoding='utf-8'));sample=probe['sample']
    require(probe['status']=='OBSERVED' and probe['scope']=='penpot-native-svg-browser-diagnostic' and probe['nativeReceiptSha256']==file_hash(capture_path) and probe['referenceComponentIrSha256']==file_hash(reference_directory/'component_ir.json') and probe['probeScriptSha256']==file_hash(Path(__file__).with_name('table_svg_probe.mjs')) and probe['referenceMatches']==[{'logicalId':plan['logicalId'],'screenshotMatches':True,'environmentMatches':True}],'table_probe_provenance_mismatch')
    require(sample['fontLoadStatus'] is True and sample['fontSha256']=='7ce5d241353a41d6c9fd02b905967ad800f19d534abd3d46eb67e46b0d18099a' and len(sample['texts'])==9,'table_vector_font_mismatch')
    for item in geometry['textSamples']:
        tb=item['sourceTextBounds'];matches=[t for t in sample['texts'] if t['characters']==item['characters'] and t['start'][0]['x']==tb['x'] and t['start'][0]['y']==item['sourceBaselineY']+5]
        require(len(matches)==1 and matches[0]['length']==tb['width'] and matches[0]['start']==[{'x':tb['x']+14*i,'y':item['sourceBaselineY']+5} for i in range(len(item['characters']))],'table_vector_text_binding_mismatch')
    import hashlib
    require(hashlib.sha256(base64.b64decode(native['nativeSvgBase64'],validate=True)).hexdigest()==sample['svgSha256'] and file_hash(probe_directory/'native-svg.png')==sample['pngSha256']==reference['screenshot']['sha256'],'table_vector_source_mismatch')
    require(native['nativePdf']['status']=='CAPTURED','native_pdf_missing');output.mkdir(parents=True,exist_ok=True)
    for field,name in [('nativePngBase64','native.png'),('nativeSvgBase64','native.svg')]: (output/name).write_bytes(base64.b64decode(native[field],validate=True))
    pdf=output/'native.pdf';pdf.write_bytes(base64.b64decode(native['nativePdf']['base64'],validate=True))
    characters=''.join(dict.fromkeys(''.join(t['characters'] for t in geometry['textSamples'])))
    glyphs=compare_glyphs(Path(source_font),SOURCE_FONT,extract_type3_glyphs(pdf),characters);require(glyphs['status']=='PASS','table_glyph_mismatch')
    data=PdfReader(pdf).pages[0].get_contents().get_data().decode('ascii');positions=re.findall(r'1 0 0 -1 ([-\d.]+) ([-\d.]+) Tm',data)
    # PDF serializes x to five decimals. Exact native x is independently bound
    # by node geometry plus the complete source-identical native SVG raster.
    expected={(Decimal(str(t['sourceTextBounds']['x'])).quantize(Decimal('.00001'),rounding=ROUND_HALF_UP),Decimal(str(t['sourceBaselineY']))) for t in geometry['textSamples']}
    require(len(positions)==9 and {(Decimal(x),Decimal(y)) for x,y in positions}==expected,'table_pdf_baseline_mismatch')
    with Image.open(output/'native.png') as image:
        require(image.size==(1392,144),'table_png_dimensions_mismatch');white=Image.new('RGBA',image.size,'white');white.alpha_composite(image.convert('RGBA'));white.save(output/'comparison-white.png')
    proof={'platform':'penpot','nativeEvidenceSha256':digest(native),'geometryAndStyle':geometry,'content':{'status':'PASS','cells':[t['characters'] for t in geometry['textSamples']]},'fontBinding':{'status':'PASS','nativeBinding':font_binding,'actualPdfGlyphIdentity':glyphs},'glyphGeometry':glyphs,
        'baselines':{'status':'PASS','nativeTextMatrices':positions,'sourceObservationSha256':plan['sourceObservationSha256'],'sourceBaselines':[t['sourceBaselineY'] for t in geometry['textSamples']],'pdfXSerialization':'five decimal half-up; exact x separately bound by native nodes and whole SVG'},
        'renderState':{'status':'PASS','nativeNodes':native['nodes']},'sourceReproduction':probe['referenceMatches'],'vectorBinding':{'status':'PASS','probe':probe,'wholeVectorPngExactlyMatchesSource':True},'nativePngSha256':file_hash(output/'native.png'),'comparisonContext':{'background':'white','resize':False,'crop':False}}
    candidate={'normalizationVersion':'0.2.0','scope':'production','evidenceKind':'native-design-capture',**{k:reference[k] for k in ('logicalComponentId','variant','state','props','content','fixtureContext')},'sourceVersion':reference['provenance']['sourceVersion'],'componentIrSha256':digest(reference),'verification':dict.fromkeys(REQUIRED_PROOFS,'PASS'),
        'glyphPaintSamples':[{'characters':t['characters'],'region':t['sourceTextBounds'],'advances':[14]*len(t['characters']),'foreground':[81,90,110],'background':[255,255,255]} for t in geometry['textSamples']],
        'allowedCornerRegions':[],'rasterContext':{'deviceScaleFactor':1,'background':'white','scale':1,'resize':False,'crop':False},'screenshotSha256':file_hash(output/'comparison-white.png'),'vectorRasterSha256':sample['pngSha256'],
        'capture':{'captureId':'penpot-table-'+file_hash(capture_path),'exporterVersion':'penpot-table-normalization-0.2.0','nativeEvidenceSha256':digest(native),'proofBundleSha256':digest(proof)}}
    report=compare(reference,candidate,reference_directory/reference['screenshot']['path'],output/'comparison-white.png',probe_directory/'native-svg.png')
    for name,value in [('proof.json',proof),('candidate.json',candidate),('gate-report.json',report)]: (output/name).write_bytes((json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode())
    return report,proof,candidate
