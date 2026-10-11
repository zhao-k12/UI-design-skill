"""Bounded full TASK-020 evidence evaluation; legacy admissions remain unchanged."""
import base64
from copy import deepcopy
from decimal import Decimal
from pathlib import Path
import json
from adapters.headed_table import prepare_source,prepare_penpot,require
from adapters.headed_table_policy import require_scope,header_background_union,DECISION_SHA256
from adapters.headed_table_raster import check_raster
from adapters.penpot.headed_table_repair_diagnostic import FONTS
from adapters.penpot.headed_table_qa import validate_geometry
from adapters.penpot.headed_table_pdf_proof import evaluate as pdf_proof
from adapters.penpot.headed_table_vector_proof import evaluate as pp_vector
from adapters.penpot.headed_table_instance_qa import validate as pp_instance
from adapters.figma.headed_table_instance_qa import validate as fg_instance
from adapters.figma.headed_table_vector_proof import evaluate as fg_vector
from adapters.figma.headed_table_qa import geometry
from adapters.figma.headed_table_glyph_diagnostic import inspect as glyphs
from adapters.figma.configurable_table_fidelity import outlines as old_arial_proof
from validators.ui_ir import ROOT,load_json
from validators.visual.fidelity import file_hash,digest

SOURCE=ROOT/'component-builder/runtime-renderer/metadata/headed-table-source'
FG=ROOT/'adapters/figma/metadata/headed-table-native'
PP=ROOT/'adapters/penpot/metadata/headed-table-native'

def paints(plan,case):
    receipt=load_json(PP/'header-union'/('discovery-2.json' if case=='two-column' else 'discovery-3.json'))['result']
    probe=load_json(PP/(case+'-svg-proof')/'svg-probe.json')['sample']
    samples=[]
    for row in plan['rows']:
        for cell in row['cells']:
            text=cell['text'];bounds=text['sourceTextBounds']
            node=next(n for n in receipt['nodes'] if n['name'].replace(' / ','/')=='official-source/'+text['path'])
            observed=[t for t in probe['texts'] if t['textReference']==node['reference'] and t['characters']==text['characters']]
            require(len(observed)==1,'headed_retention_vector_inventory')
            actual=observed[0]
            require(actual['length']==bounds['width'] and actual['start'][0]['x']==bounds['x'] and actual['fontWeight']==str(text['fontWeight']),'headed_retention_vector_style')
            ends=actual['start'][1:]+[actual['end'][-1]]
            advances=[float(Decimal(str(b['x']))-Decimal(str(a['x']))) for a,b in zip(actual['start'],ends)]
            fill=cell['fill'];background=[int(fill[i:i+2],16) for i in (1,3,5)]
            samples.append({'characters':text['characters'],'region':bounds,'advances':advances,'foreground':[81,90,110],'background':background})
    return samples

def evaluate(case,platform,output):
    require(case in ('two-column','four-column') and platform in ('figma','penpot'),'headed_fidelity_scope')
    output=Path(output).resolve();require(output.is_relative_to((ROOT/'artifacts').resolve()) and not output.exists(),'headed_fidelity_new_output_required')
    source=SOURCE/(case+'-typography');plan=prepare_source(source);require_scope(plan)
    reference=load_json(source/'component_ir.json')['components'][0];output.mkdir(parents=True)
    vector_proof=pp_vector(PP/'header-union'/('discovery-2.json' if case=='two-column' else 'discovery-3.json'),source,PP/(case+'-svg-proof'))
    if platform=='penpot':
        native_path=PP/'header-union'/('discovery-2.json' if case=='two-column' else 'discovery-3.json');capture=load_json(native_path);native=capture['result']
        native_plan=prepare_penpot(source,native['fileReference'],native['pageReference']);native_plan['headerBackgroundUnion']=header_background_union(plan)
        geom=validate_geometry(native,native_plan,FONTS)
        font=pdf_proof(native_path,source,Path('C:/Users/38442/AppData/Local/Microsoft/Windows/Fonts'),Path('C:/Windows/Fonts/arial.ttf'),output/'pdf')
        instance=pp_instance(load_json(PP/'instances'/('discovery-2.json' if case=='two-column' else 'discovery-3.json')),case)
        raw=base64.b64decode(native['nativePngBase64'],validate=True);vector=PP/(case+'-svg-proof')/'native-svg.png'
    else:
        native_path=FG/(case+'-readback.json');capture=load_json(native_path);native=capture['nativeEvidence']
        require(capture['status']=='PASS' and not capture['createdNodeIds'] and not capture['mutatedNodeIds'],'headed_native_capture_invalid')
        font=glyphs(FG/'text-outlines.json');require(font['status']=='OBSERVED' and all(r['status']=='PASS' for r in font['observations']),'headed_glyph_encoding_failed')
        _,arial=old_arial_proof();require(arial['status']=='PASS','headed_locked_arial_glyphs_failed')
        spec=load_json(FG/'candidate-specs.json')[0 if case=='two-column' else 1]
        expected=deepcopy(plan)
        for row in expected['rows']:
            for cell in row['cells']:cell['text']['fontStyle']='Semibold' if cell['text']['fontWeight']==600 else 'Regular'
        require(all(spec[k]==expected[k] for k in plan) and spec['fontBaselineOffsets']=={'Arial':15,'PingFang SC':16,'PingFang SC/Semibold':16},'headed_candidate_source_binding')
        geom=geometry(native,spec,{o['textReference']:o for o in load_json(FG/'text-outlines.json')['observations']},font)
        instance=fg_instance(load_json(FG/(case+'-instance.json')),case)
        vector_proof,vector=fg_vector(case)
        effect_path=FG/(case+'-font-probe')/'font-file-probe.json';effect=load_json(effect_path)
        require(effect['status']=='OBSERVED' and effect['referenceComponentIrSha256']==file_hash(source/'component_ir.json') and effect['probeScriptSha256']==file_hash(ROOT/'adapters/figma/headed_table_probes.mjs') and effect['ownerStatesRestored'] and effect['temporaryFontFacesRemoved'] and effect['observation']['ownerBoundsUnchanged'] and effect['observation']['fontLoadStatus']==['loaded','loaded','loaded'] and effect['observation']['pngSha256']==reference['screenshot']['sha256']==file_hash(effect_path.parent/'file-bound.png'),'headed_source_font_effect_mismatch')
        font={'glyphs':font,'lockedArialCalibration':arial,'sourceFontEffect':effect,'status':'PASS'}
        raw=(FG/(case+'-native.png')).read_bytes()
        require(raw==base64.b64decode(capture['nativePngBase64'],validate=True),'headed_png_native_readback_binding')
    raster=check_raster(source,platform,raw,vector,paints(plan,case))
    proof={'decisionSha256':DECISION_SHA256,'nativeCaptureSha256':file_hash(native_path),'componentIrSha256':plan['componentIrSha256'],
           'geometryAndStyle':geom,'fontsGlyphsBaselines':font,'vectorBinding':vector_proof,'raster':raster,'realInstance':instance,
           'normalizerSha256':file_hash(__file__),'rasterCheckerSha256':file_hash(ROOT/'adapters/headed_table_raster.py')}
    proof['nativeEvidenceSha256']=digest(native)
    candidate={'normalizationVersion':'0.3.0','scope':'production','logicalComponentId':plan['logicalId'],'componentIrSha256':plan['componentIrSha256'],'decisionSha256':DECISION_SHA256,'nativeEvidenceSha256':digest(native),'proofBundleSha256':digest(proof)}
    required=('geometryAndStyle','content','fontBinding','glyphGeometry','baselines','renderState','sourceReproduction','vectorBinding')
    checks={'geometryAndStyle':'PASS','normalizationProofs':dict.fromkeys(required,'PASS'),'glyphRetention':raster['glyphRetention'],
            'horizontalCoverage':raster['horizontalCoverage'],'pngContext':raster['pixelOwnership']['pngContext'],
            'screenshot':{'policy':'evidence-bound-edges-0.3.0','changedPixels':raster['pixelOwnership']['differentPixels'],'changedPixelsOutsideEdgeBand':0,'changedPixelsOutsidePermittedRegions':0,'vectorRasterSha256':file_hash(vector)}}
    report={'status':'PASS','scope':'production','variants':[reference['variant']],'issues':[],'candidateEvidenceKind':'native-design-capture',
            'candidateSha256':digest(candidate),'referenceScreenshotSha256':reference['screenshot']['sha256'],'candidateScreenshotSha256':raster['pixelOwnership']['pngContext']['nativePngSha256'],
            'capture':{'captureId':'task020-'+platform+'-'+case,'exporterVersion':platform+'-headed-table-0.3.0','nativeEvidenceSha256':digest(native),'proofBundleSha256':digest(proof)},
            'admissionEligible':True,'gateVersion':'0.3.0','platform':platform,'logicalComponentId':plan['logicalId'],'componentType':'Table',
            'sourceVersion':plan['sourceVersion'],'componentIrSha256':plan['componentIrSha256'],'nativePngSha256':raster['pixelOwnership']['pngContext']['nativePngSha256'],
            'decisionSha256':DECISION_SHA256,'proofBundleSha256':digest(proof),'pixelRegionPolicy':'positive-area-intersection-no-padding','checks':checks}
    (output/'native.png').write_bytes(raw)
    for name,data in (('proof.json',proof),('candidate.json',candidate),('gate-report.json',report)):(output/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    return report

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('case');parser.add_argument('platform');parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();report=evaluate(args.case,args.platform,args.output);print(json.dumps({k:v for k,v in report.items() if k!='checks'}))
