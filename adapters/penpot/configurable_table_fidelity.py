"""Full evidence gate for the source-bound mixed-font Table body candidates."""
import base64
from decimal import Decimal, ROUND_HALF_UP
import json
from pathlib import Path
import re
from PIL import Image
from validators.ui_ir import ROOT,load_json
from validators.visual.fidelity import digest,file_hash
from adapters.penpot.table_pixel_coverage import compare,REQUIRED_PROOFS
from adapters.configurable_table import prepare_penpot,require
from adapters.penpot.configurable_table_qa import validate_geometry
from adapters.penpot.pdf_glyph_geometry import extract_type3_glyphs,compare_glyphs
from adapters.penpot.pdf_truetype_geometry import compare_embedded_truetype

FONT_HASHES={'Arial':'c9b76220a5be42ead4733611e417cd65c5fd8aeaa33eb56576ac378a37d130a1','PingFang SC':'0934ea94dea57d9ec12a401f44ad28b98c96f5ee9917df920279f58024de523a'}
WOFF_HASHES={'Arial':'2035b173b6273ac11ffb25fd61d271753cca918bcc325dfdd7eebd636a0ea6d3','PingFang SC':'7ce5d241353a41d6c9fd02b905967ad800f19d534abd3d46eb67e46b0d18099a'}


def evaluate(capture_path,probe_directory,reference_directory,font_paths,font_bindings,output_directory):
    from pypdf import PdfReader
    capture_path=Path(capture_path);probe_directory=Path(probe_directory);reference_directory=Path(reference_directory);output=Path(output_directory).resolve()
    require(output.is_relative_to((ROOT/'artifacts').resolve()) and not any(p.resolve().is_relative_to(output) for p in (capture_path,probe_directory,reference_directory)),'invalid_fidelity_output')
    require(not output.exists() or not any(output.iterdir()),'fidelity_output_not_empty')
    receipt=load_json(capture_path);require(receipt['status']=='CAPTURED','host_capture_failed');native=receipt['result']
    plan=prepare_penpot(reference_directory,native['fileReference'],native['pageReference']);geometry=validate_geometry(native,plan,font_bindings)
    reference=load_json(reference_directory/'component_ir.json')['components'][0];probe=load_json(probe_directory/'svg-probe.json');sample=probe['sample']
    require(probe['status']=='OBSERVED' and probe['scope']=='penpot-native-svg-browser-diagnostic' and probe['nativeReceiptSha256']==file_hash(capture_path) and probe['referenceComponentIrSha256']==file_hash(reference_directory/'component_ir.json') and probe['probeScriptSha256']==file_hash(Path(__file__).with_name('configurable_table_svg_probe.mjs')) and probe['referenceMatches']==[{'logicalId':plan['logicalId'],'screenshotMatches':True,'environmentMatches':True}],'table_probe_provenance_mismatch')
    require(sample['fontLoadStatus'] is True and set(sample['fontResources'])==set(FONT_HASHES) and all(sample['fontResources'][family]['sha256']==WOFF_HASHES[family] and file_hash(sample['fontResources'][family]['path'])==WOFF_HASHES[family] for family in FONT_HASHES),'table_vector_font_mismatch')
    require(len(sample['texts'])==len(geometry['textSamples']),'table_vector_text_inventory_mismatch')
    paint_samples=[];vector_rows=[]
    for text in geometry['textSamples']:
        bounds=text['sourceTextBounds'];nodes=[n for n in native['nodes'] if n['type']=='text' and re.sub(r'\s*/\s*','/',n['name'])=='official-source/'+text['path']]
        require(len(nodes)==1 and text['fill']=='#515a6e','table_text_node_or_paint_mismatch')
        matches=[t for t in sample['texts'] if t.get('textReference')==nodes[0]['reference'] and t['characters']==text['characters'] and t['start'][0]['x']==bounds['x']]
        require(len(matches)==1,'table_vector_text_binding_mismatch');actual=matches[0]
        require(actual['fontFamily'].strip('"')==text['fontFamily'] and actual['fontSize']=='14px' and actual['fontWeight']=='400' and actual['length']==bounds['width'] and len(actual['start'])==len(actual['end'])==len(text['characters']),'table_vector_font_or_advance_mismatch')
        require(all(p['y']==actual['start'][0]['y'] for p in actual['start']+actual['end']) and all(actual['start'][i]['x']<actual['start'][i+1]['x'] for i in range(len(text['characters'])-1)),'unordered_vector_text')
        # Character extents can overlap after the browser's subpixel rounding.
        # Partition at observed character starts and the actual final endpoint.
        endpoints=actual['start'][1:]+[actual['end'][-1]]
        advances=[float(Decimal(str(b['x']))-Decimal(str(a['x']))) for a,b in zip(actual['start'],endpoints)]
        require(sum(Decimal(str(v)) for v in advances)==Decimal(str(bounds['width'])),'table_vector_advance_sum_mismatch')
        paint_samples.append({'characters':text['characters'],'region':bounds,'advances':advances,'foreground':[81,90,110],'background':[255,255,255]})
        vector_rows.append({'sourceTextPath':text['path'],'nativeSvgObservation':actual})
    require(file_hash(probe_directory/'native-svg.png')==sample['pngSha256']==reference['screenshot']['sha256'],'table_vector_source_mismatch')
    svg=base64.b64decode(native['nativeSvgBase64'],validate=True)
    import hashlib
    require(hashlib.sha256(svg).hexdigest()==sample['svgSha256'],'native_svg_binding_mismatch')
    require(native['nativePdf']['status']=='CAPTURED','native_pdf_missing');output.mkdir(parents=True,exist_ok=True)
    (output/'native.svg').write_bytes(svg);(output/'native.png').write_bytes(base64.b64decode(native['nativePngBase64'],validate=True));pdf=output/'native.pdf';pdf.write_bytes(base64.b64decode(native['nativePdf']['base64'],validate=True))
    by_family={family:''.join(dict.fromkeys(''.join(t['characters'] for t in geometry['textSamples'] if t['fontFamily']==family))) for family in FONT_HASHES}
    arial=compare_embedded_truetype(pdf,Path(font_paths['Arial']),FONT_HASHES['Arial'],by_family['Arial'])
    chinese=compare_glyphs(Path(font_paths['PingFang SC']),FONT_HASHES['PingFang SC'],extract_type3_glyphs(pdf,allowed_type0_names=('ArialMT',)),by_family['PingFang SC'])
    require(arial['status']==chinese['status']=='PASS','table_glyph_geometry_mismatch')
    data=PdfReader(pdf).pages[0].get_contents().get_data().decode('ascii');positions=re.findall(r'1 0 0 -1 ([-\d.]+) ([-\d.]+) Tm',data)
    expected={(Decimal(str(t['sourceTextBounds']['x'])).quantize(Decimal('.00001'),rounding=ROUND_HALF_UP),Decimal(str(t['sourceBaselineY']))) for t in geometry['textSamples']}
    require(len(positions)==len(expected)==len(geometry['textSamples']) and {(Decimal(x),Decimal(y)) for x,y in positions}==expected,'table_pdf_baseline_mismatch')
    with Image.open(output/'native.png') as image:require(image.size==(plan['rootBounds']['width'],plan['rootBounds']['height']) and image.convert('RGBA').getextrema()[3]==(255,255),'table_png_dimensions_or_opaque_background_mismatch')
    proof={'platform':'penpot','nativeEvidenceSha256':digest(native),'geometryAndStyle':geometry,'fontBinding':{'status':'PASS','nativeBindings':font_bindings,'sourceFontHashes':FONT_HASHES},'glyphGeometry':{'status':'PASS','Arial':arial,'PingFang SC':chinese},'baselines':{'status':'PASS','nativeTextMatrices':positions,'sourceObservationSha256':plan['sourceObservationSha256'],'pdfXSerialization':'five decimal half-up; exact x bound by nodes and source-identical whole native SVG'},'vectorBinding':{'status':'PASS','observations':vector_rows,'probe':probe,'wholeVectorPngExactlyMatchesSource':True},'content':{'status':'PASS','texts':[t['characters'] for t in geometry['textSamples']]},'renderState':{'status':'PASS','nativeNodes':native['nodes']},'sourceReproduction':probe['referenceMatches']}
    proof['pixelRegionPolicy']={'version':'0.2.1','classification':'positive-area-intersection','sourceRectanglesUnchanged':True,'edgeBandUnchanged':True,'glyphRetentionUnchanged':True}
    candidate={'normalizationVersion':'0.2.1','pixelRegionPolicy':'positive-area-intersection','scope':'production','evidenceKind':'native-design-capture',**{k:reference[k] for k in ('logicalComponentId','variant','state','props','content','fixtureContext')},'sourceVersion':reference['provenance']['sourceVersion'],'componentIrSha256':digest(reference),'verification':dict.fromkeys(REQUIRED_PROOFS,'PASS'),'glyphPaintSamples':paint_samples,'allowedCornerRegions':[],'rasterContext':{'deviceScaleFactor':1,'background':'white','scale':1,'resize':False,'crop':False},'screenshotSha256':file_hash(output/'native.png'),'vectorRasterSha256':sample['pngSha256'],'capture':{'captureId':'penpot-configurable-table-'+file_hash(capture_path),'exporterVersion':'penpot-configurable-table-normalization-0.2.1','nativeEvidenceSha256':digest(native),'proofBundleSha256':digest(proof)}}
    report=compare(reference,candidate,reference_directory/reference['screenshot']['path'],output/'native.png',probe_directory/'native-svg.png')
    for name,value in [('proof.json',proof),('candidate.json',candidate),('gate-report.json',report)]: (output/name).write_bytes((json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode())
    return report,proof,candidate
