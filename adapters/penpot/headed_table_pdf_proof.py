"""Exact source-font paths and text baselines from TASK-020 native PDFs."""
import argparse
import base64
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256
import json
from pathlib import Path
import re
from fontTools.ttLib import TTFont
from pypdf import PdfReader
from adapters.headed_table import prepare_source, require
from adapters.headed_table_policy import require_scope
from adapters.penpot.pdf_glyph_geometry import extract_type3_glyphs, compare_glyphs
from adapters.penpot.pdf_truetype_geometry import compare_embedded_truetype
from validators.visual.fidelity import file_hash

FONTS={
    'PingFangSC-Regular':('PingFang SC-Regular.otf','0934ea94dea57d9ec12a401f44ad28b98c96f5ee9917df920279f58024de523a',400),
    'PingFangSC-Semibold':('PingFang SC-Semibold.otf','ca115f4f17266f1ff5ead3ef1049814eafb4f61cc279134e0a8b3d817532fb78',600),
}
ARIAL_HASH='c9b76220a5be42ead4733611e417cd65c5fd8aeaa33eb56576ac378a37d130a1'

def evaluate(receipt_path, source_dir, font_dir, arial_path, output):
    output=Path(output)
    require(not output.exists(),'pdf_proof_output_exists')
    plan=prepare_source(source_dir);require_scope(plan)
    receipt=json.loads(Path(receipt_path).read_text(encoding='utf8'));native=receipt['result']
    require(receipt['status']==native['status']=='CAPTURED' and native['logicalId']==plan['logicalId'] and native['componentIrSha256']==plan['componentIrSha256'],'pdf_source_binding_mismatch')
    require(native['nativePdf']['status']=='CAPTURED','native_pdf_missing')
    output.mkdir(parents=True)
    pdf=output/'native.pdf';pdf.write_bytes(base64.b64decode(native['nativePdf']['base64'],validate=True))
    observations=extract_type3_glyphs(pdf,allowed_type0_names=('ArialMT',))
    texts=[c['text'] for row in plan['rows'] for c in row['cells']]
    results=[];coverage={name:set() for name in FONTS};identities={}
    for name,(filename,digest,weight) in FONTS.items():
        path=Path(font_dir)/filename
        require(file_hash(path)==digest,'source_font_hash_mismatch')
        with TTFont(path) as font:
            cmap=font.getBestCmap()
            expected=set(''.join(t['characters'] for t in texts if t['postScriptName']==name))
            selected=[o for o in observations if o['postscriptName']==name]
            require(bool(selected),'pdf_source_font_missing')
            for observed in selected:
                require(observed['fontWeight']==weight,'pdf_source_weight_mismatch')
                aliases=[ch for ch in expected if cmap.get(ord(ch))==cmap.get(ord(observed['character'])) and cmap.get(ord(ch)) is not None]
                require(len(aliases)==1,'pdf_unexpected_or_ambiguous_glyph')
                character=aliases[0]
                proof=compare_glyphs(path,digest,[observed],character)
                require(proof['status']=='PASS','pdf_exact_cff_path_mismatch')
                results.append({'resource':observed['resource'],'postscriptName':name,**proof})
                coverage[name].add(character)
                identities[observed['resource']]=(name,weight)
            require(coverage[name]==expected,'pdf_cff_inventory_incomplete')
    require(len(results)==len(observations),'pdf_unexpected_type3_font')
    arial_characters=''.join(dict.fromkeys(''.join(t['characters'] for t in texts if t['postScriptName']=='ArialMT')))
    arial=compare_embedded_truetype(pdf,Path(arial_path),ARIAL_HASH,arial_characters)
    require(arial['status']=='PASS','pdf_arial_geometry_mismatch')
    page=PdfReader(pdf).pages[0]
    for resource,reference in page['/Resources']['/Font'].items():
        font=reference.get_object()
        if font['/Subtype']=='/Type0': identities[str(resource)]=('ArialMT',400)
    contents=page.get_contents().get_data().decode('ascii')
    blocks=re.findall(r'\bBT\b([\s\S]*?)\bET\b',contents)
    require(len(blocks)==len(texts),'pdf_text_block_inventory_mismatch')
    remaining=list(texts);baselines=[]
    for block in blocks:
        matrices=re.findall(r'1 0 0 -1 ([-\d.]+) ([-\d.]+) Tm',block)
        fonts=re.findall(r'(/F\d+) ([\d.]+) Tf',block)
        require(len(matrices)==1 and bool(fonts) and all(Decimal(size)==14 for _,size in fonts),'pdf_text_matrix_or_size_mismatch')
        x,y=map(Decimal,matrices[0]);identity=identities[fonts[0][0]]
        require(all(identities[resource]==identity for resource,_ in fonts),'pdf_mixed_source_font_in_text')
        matches=[t for t in remaining if Decimal(str(t['sourceTextBounds']['x'])).quantize(Decimal('.00001'),rounding=ROUND_HALF_UP)==x and Decimal(str(t['sourceBaselineY']))==y and (t['postScriptName'],t['fontWeight'])==identity]
        require(len(matches)==1,'pdf_source_baseline_or_font_mismatch')
        text=matches[0];remaining.remove(text)
        baselines.append({'sourcePath':text['path'],'characters':text['characters'],'postscriptName':identity[0],'fontWeight':identity[1],'x':str(x),'baselineY':str(y),'status':'PASS'})
    require(not remaining,'pdf_text_baseline_inventory_incomplete')
    report={'status':'PASS','scope':'headed-table-native-pdf-fonts-and-baselines-only','fidelityGate':'NOT_RUN','productionAdmission':False,
            'nativeReceiptSha256':file_hash(receipt_path),'nativePdfSha256':file_hash(pdf),'logicalId':plan['logicalId'],
            'sourceObservationSha256':plan['sourceObservationSha256'],'cffGlyphs':results,'Arial':arial,'baselines':baselines,
            'pdfXSerialization':'five decimal half-up; exact native node positions require separate geometry proof'}
    (output/'proof.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for name in ('receipt','source','fonts','arial','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();result=evaluate(args.receipt,args.source,args.fonts,args.arial,args.output)
    print(json.dumps({'status':result['status'],'glyphResources':len(result['cffGlyphs']),'textBaselines':len(result['baselines']),'fidelityGate':result['fidelityGate']}))
