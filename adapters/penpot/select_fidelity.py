"""Independent AD-017 evidence checks for the one locked Penpot Select fixture."""
import base64
import json
from pathlib import Path
import re
from PIL import Image
from adapters.penpot.pdf_glyph_geometry import extract_type3_glyphs, compare_glyphs
from adapters.penpot.pdf_embedded_glyph import compare_embedded_glyph
from validators.visual.fidelity import digest, file_hash
from validators.visual.cross_renderer import compare, REQUIRED_PROOFS

SOURCE_BUNDLE='3b19ae988759787d668550ad0253139b5b3813c9421f4a76917ed05b309b7245'
SOURCE_FONT='0934ea94dea57d9ec12a401f44ad28b98c96f5ee9917df920279f58024de523a'


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def validate_geometry(native, reference, font_binding, arrow_binding):
    require(native['status']=='CAPTURED' and native['platform']=='penpot' and
            native['scope']=='production' and not native['createdNodeIds'] and not native['mutatedNodeIds'], 'invalid_native_capture')
    require(native['logicalId']==reference['logicalComponentId'] and native['componentIrSha256']==digest(reference), 'native_source_mismatch')
    require(len(native['nodes'])==4, 'native_node_inventory_mismatch')
    root,paint,arrow,text=native['nodes']
    require(root['reference']==native['mainReference'] and root['type']=='board' and paint['type']=='rectangle' and text['type']=='text', 'native_topology_mismatch')
    require(paint['parentReference']==text['parentReference']==root['reference'], 'native_parent_mismatch')
    source_root=next(n for n in reference['nodes'] if n['path']=='0.0')
    source_label=next(n for n in reference['nodes'] if n['path']=='0.0.1.0')
    source_arrow=next(n for n in reference['nodes'] if n['path']=='0.0.1.1')
    style=source_root['computedStyle'];rb=source_root['bounds'];tb=source_label['textRuns'][0]['bounds']
    require((root['width'],root['height'])==(rb['width'],rb['height']) and root['borderRadius']==4 and root['fills']==root['strokes']==[], 'root_geometry_mismatch')
    require(all(style['border-'+side+'-width']=='1px' and style['border-'+side+'-color']=='rgb(220, 222, 226)' for side in ('top','right','bottom','left')), 'unsupported_source_border')
    require((paint['x']-root['x'],paint['y']-root['y'],paint['width'],paint['height'],paint['borderRadius'])==(.5,.5,rb['width']-1,rb['height']-1,3.5), 'border_centerline_mismatch')
    require(len(paint['fills'])==len(paint['strokes'])==len(text['fills'])==1 and not text['strokes'], 'unsupported_native_paints')
    fill=paint['fills'][0];stroke=paint['strokes'][0]
    require(fill['fillColor']=='#ffffff' and stroke['strokeColor']=='#dcdee2' and fill['fillOpacity']==stroke['strokeOpacity']==1 and
            stroke['strokeWidth']==1 and stroke['strokeAlignment']=='center' and stroke['strokeStyle']=='solid', 'native_border_paint_mismatch')
    require(all(not fill.get(k) for k in ('fillColorGradient','fillImage','fillColorRefId')) and
            all(not stroke.get(k) for k in ('strokeColorGradient','strokeImage','strokeColorRefId')), 'unsupported_native_paint_reference')
    require((text['x']-root['x'],text['y']-root['y'],text['width'],text['height'])==(tb['x'],tb['y'],tb['width'],tb['height']), 'native_text_geometry_mismatch')
    require(text['characters']==source_label['textRuns'][0]['text'] and text['fontFamily']=='PingFang SC' and text['fontId']==font_binding['fontId'] and
            text['fontVariantId']==font_binding['fontVariantId'] and float(text['fontSize'])==14 and float(text['fontWeight'])==400 and
            text['fontStyle']=='normal' and float(text['lineHeight'])==16/14 and float(text['letterSpacing'])==0 and text['growType']=='fixed', 'native_text_style_mismatch')
    require(text['fills'][0]['fillColor']=='#515a6e' and text['fills'][0]['fillOpacity']==1, 'native_text_paint_mismatch')
    require(all(not text['fills'][0].get(k) for k in ('fillColorGradient','fillImage','fillColorRefId','fillColorRefFile')), 'unsupported_native_text_paint_reference')
    ab=source_arrow['bounds'];ap=source_arrow['pseudoElements']['::before']
    require(arrow['type']=='text' and arrow['reference']==native['arrowReference'] and arrow['parentReference']==root['reference'],'native_arrow_topology_mismatch')
    require((arrow['x']-root['x'],arrow['y']-root['y'],arrow['width'],arrow['height'])==(ab['x'],ab['y'],ab['width'],ab['height']),'native_arrow_geometry_mismatch')
    require(arrow['characters']==json.loads(ap['content']) and arrow['fontFamily']=='Ionicons' and arrow['fontId']==arrow_binding['fontId'] and arrow['fontVariantId']==arrow_binding['fontVariantId'] and float(arrow['fontSize'])==14 and float(arrow['fontWeight'])==400 and arrow['fontStyle']=='normal' and float(arrow['lineHeight'])==1 and float(arrow['letterSpacing'])==0 and arrow['growType']=='fixed' and arrow['align']=='left' and arrow['verticalAlign']=='top','native_arrow_style_mismatch')
    require(len(arrow['fills'])==1 and not arrow['strokes'] and arrow['fills'][0]['fillColor']=='#808695' and arrow['fills'][0]['fillOpacity']==1 and all(not arrow['fills'][0].get(k) for k in ('fillColorGradient','fillImage','fillColorRefId','fillColorRefFile')),'native_arrow_paint_mismatch')
    for node in native['nodes']:
        require(node['opacity']==1 and node['blendMode']=='normal' and node['visible'] is True and node['hidden'] is False and
                node['rotation']==0 and not node['flipX'] and not node['flipY'] and node['shadows']==[] and node['blur'] is None, 'unsupported_native_render_state')
    require(root['clipContent'] is False and text['align']=='left' and text['verticalAlign']=='top', 'native_clip_or_alignment_mismatch')
    return {'status':'PASS','nativeTextReference':text['reference'],'textRegion':tb,
            'borderNormalization':'Uniform inner border represented by its exact centerline, preserving outer bounds/radius.',
            'textAlignmentNormalization':'The observed 28px selected label and 14px arrow preserve source glyph advances.'}


def evaluate(capture_path, probe_directory, reference_directory, source_font, font_binding, output_directory, arrow_font, arrow_binding):
    from pypdf import PdfReader
    output_directory=Path(output_directory)
    require(not output_directory.exists() or not any(output_directory.iterdir()), 'fidelity_output_not_empty')
    reference_directory=Path(reference_directory);probe_directory=Path(probe_directory)
    require(file_hash(reference_directory/'component_ir.json')==SOURCE_BUNDLE, 'source_bundle_mismatch')
    reference=next(c for c in json.loads((reference_directory/'component_ir.json').read_text(encoding='utf-8'))['components'] if c['logicalComponentId']=='form.select.default.medium')
    receipt=json.loads(Path(capture_path).read_text(encoding='utf-8'));native=receipt['result']
    require(receipt['status']=='CAPTURED', 'host_capture_failed')
    geometry=validate_geometry(native,reference,font_binding,arrow_binding)
    probe=json.loads((probe_directory/'svg-probe.json').read_text(encoding='utf-8'));sample=probe['sample']
    require(probe['scope']=='penpot-native-svg-browser-diagnostic' and probe['status']=='OBSERVED' and
            probe['probeScriptSha256']==file_hash(Path(__file__).with_name('select_svg_probe.mjs')) and
            probe['nativeReceiptSha256']==file_hash(capture_path) and probe['referenceComponentIrSha256']==SOURCE_BUNDLE and
            len(probe['referenceMatches'])==3 and {r['logicalId'] for r in probe['referenceMatches']}==
            {'action.button.primary.medium','form.input.default.medium','form.select.default.medium'} and
            all(r['screenshotMatches'] and r['environmentMatches'] for r in probe['referenceMatches']), 'probe_provenance_mismatch')
    require({(r['family'],r['sha256']) for r in sample['fontResources']}=={('PingFang SC','7ce5d241353a41d6c9fd02b905967ad800f19d534abd3d46eb67e46b0d18099a'),('Ionicons','9879ad9ccfc0640e6ba98ab85c3bbca11545baf7a0060efb2502498bc17e4f30')} and len(sample['fontResources'])==2,'vector_font_container_mismatch')
    texts=sample['texts'];label_sample=next(t for t in texts if t['characters']==native['nodes'][-1]['characters']);arrow_sample=next(t for t in texts if t['characters']==native['nodes'][2]['characters'])
    require(sample['fontLoadStatus'] is True and len(texts)==2 and label_sample['length']==28 and label_sample['start']==[{'x':9,'y':26},{'x':23,'y':26}] and arrow_sample['length']==14 and arrow_sample['start']==[{'x':217,'y':23}],'native_svg_text_binding_mismatch')
    svg=base64.b64decode(native['nativeSvgBase64'],validate=True)
    import hashlib
    require(hashlib.sha256(svg).hexdigest()==sample['svgSha256'] and
            file_hash(probe_directory/'native-svg.png')==sample['pngSha256'], 'vector_raster_binding_mismatch')
    require(sample['pngSha256']==reference['screenshot']['sha256'], 'whole_vector_source_raster_mismatch')
    output_directory.mkdir(parents=True,exist_ok=True)
    for field,name in [('nativePngBase64','native.png'),('nativeSvgBase64','native.svg')]:
        (output_directory/name).write_bytes(base64.b64decode(native[field],validate=True))
    require(native['nativePdf']['status']=='CAPTURED', 'native_pdf_missing')
    pdf_path=output_directory/'native.pdf';pdf_path.write_bytes(base64.b64decode(native['nativePdf']['base64'],validate=True))
    text_glyphs=compare_glyphs(Path(source_font),SOURCE_FONT,extract_type3_glyphs(pdf_path,allowed_type0_names=('Ionicons',)),native['nodes'][-1]['characters'])
    arrow_glyph=compare_embedded_glyph(pdf_path,Path(arrow_font),'13d29fa1b804cd295603d17a7c9296c425af2724feaac7ce621f7cad43d8a31d',native['nodes'][2]['characters'],'Ionicons')
    glyphs={'status':'PASS' if text_glyphs['status']==arrow_glyph['status']=='PASS' else 'FAIL','label':text_glyphs,'arrow':arrow_glyph}
    require(glyphs['status']=='PASS','native_glyph_geometry_mismatch')
    data=PdfReader(pdf_path).pages[0].get_contents().get_data().decode('ascii')
    positions=re.findall(r'1 0 0 -1 ([-\d.]+) ([-\d.]+) Tm',data)
    source_baseline_path=reference_directory.parent/'official-runtime-complete-baseline-evidence.json'
    source_baseline=json.loads(source_baseline_path.read_text(encoding='utf-8'))
    require(source_baseline['scope']=='official_runtime_baseline_diagnostic' and source_baseline['status']=='PASS' and source_baseline['referenceComponentIrSha256']==SOURCE_BUNDLE,'source_baseline_provenance_mismatch')
    rows=[r for r in source_baseline['observations'] if r['logicalId']==native['logicalId']]
    require(len(rows)==2 and all(r['originalGeometryAndMarkupRestored'] is True for r in rows) and {r['characters'] for r in rows}=={native['nodes'][-1]['characters'],native['nodes'][2]['characters']},'source_baseline_missing_or_unrestored')
    source_label_baseline=next(r for r in rows if r['characters']==native['nodes'][-1]['characters'])
    source_arrow_baseline=next(r for r in rows if r['characters']==native['nodes'][2]['characters'])
    require(len(positions)==2 and {(float(x),float(y)) for x,y in positions}=={(geometry['textRegion']['x'],source_label_baseline['baselineComponentY']),(217,source_arrow_baseline['baselineComponentY'])},'native_pdf_baseline_mismatch')
    # The original PNG is kept byte-for-byte. Only the declared white comparison
    # context is composited, without resizing, crop, or geometric adjustment.
    with Image.open(output_directory/'native.png') as image:
        require(image.size==(240,32), 'native_png_dimensions_mismatch')
        white=Image.new('RGBA',image.size,'white');white.alpha_composite(image.convert('RGBA'))
        white.save(output_directory/'comparison-white.png')
    proof={'platform':'penpot','nativeEvidenceSha256':digest(native),'geometryAndStyle':geometry,
        'content':{'status':'PASS','characters':native['nodes'][-1]['characters'],'arrow':native['nodes'][2]['characters']},
        'fontBinding':{'status':'PASS','nativeBinding':font_binding,'arrowNativeBinding':arrow_binding,'actualPdfGlyphIdentity':glyphs},
        'glyphGeometry':glyphs,'baselines':{'status':'PASS','actualNativePdfTextMatrices':positions,'sourceObservedBaselines':rows,'sourceEvidenceSha256':file_hash(source_baseline_path)},
        'renderState':{'status':'PASS','nativeNodes':native['nodes']},'sourceReproduction':probe['referenceMatches'],
        'vectorBinding':{'status':'PASS','probe':probe,'wholeVectorPngExactlyMatchesSource':True},
        'nativePngSha256':file_hash(output_directory/'native.png'),
        'comparisonContext':{'background':'white','resize':False,'crop':False}}
    candidate={'normalizationVersion':'0.2.0','scope':'production','evidenceKind':'native-design-capture',
        **{k:reference[k] for k in ('logicalComponentId','variant','state','props','content','fixtureContext')},
        'sourceVersion':reference['provenance']['sourceVersion'],'componentIrSha256':digest(reference),
        'verification':dict.fromkeys(REQUIRED_PROOFS,'PASS'),
        'glyphPaintSamples':[{'characters':native['nodes'][-1]['characters'],'region':geometry['textRegion'],'advances':[14,14],
            'foreground':[81,90,110],'background':[255,255,255]},{'characters':native['nodes'][2]['characters'],'region':{'x':217,'y':9,'width':14,'height':14},'advances':[14],'foreground':[128,134,149],'background':[255,255,255]}],
        'allowedCornerRegions':[{'x':x,'y':y,'width':4,'height':4} for x in (0,236) for y in (0,28)],
        'rasterContext':{'deviceScaleFactor':1,'background':'white','scale':1,'resize':False,'crop':False},
        'screenshotSha256':file_hash(output_directory/'comparison-white.png'),'vectorRasterSha256':sample['pngSha256'],
        'capture':{'captureId':'penpot-select-'+file_hash(capture_path),'exporterVersion':'penpot-select-normalization-0.2.0',
            'nativeEvidenceSha256':digest(native),'proofBundleSha256':digest(proof)}}
    report=compare(reference,candidate,reference_directory/reference['screenshot']['path'],output_directory/'comparison-white.png',probe_directory/'native-svg.png')
    for name,value in [('proof.json',proof),('candidate.json',candidate),('gate-report.json',report)]:
        (output_directory/name).write_bytes((json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode())
    return report,proof,candidate
