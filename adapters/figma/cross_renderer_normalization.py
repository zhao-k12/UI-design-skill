"""AD-017 equivalence proofs for the three locked, static official fixtures.

Native measurements are read from immutable capture files. Browser observations
are comparison evidence; they are never substituted into native measurements.
This module deliberately rejects unsupported components and changed fixtures.
"""
from decimal import Decimal
import hashlib
from pathlib import Path
import xml.etree.ElementTree as ET
from fontTools.pens.recordingPen import RecordingPen
from fontTools.svgLib.path import parse_path
from PIL import Image
from adapters.figma import candidate_diagnostic, render_state_diagnostic
from adapters.figma.baseline_alignment import compare_baseline_alignment
from adapters.figma.blend_mode_diagnostic import compare_experiment
from adapters.figma.font_outline_comparison import compare_font_files,measure_glyphs,canonical_directed_contours
from adapters.figma.native_capture import verify_saved_capture
from adapters.figma.served_font_comparison import compare_served_glyph
from validators.ui_ir import ROOT,load_json
from validators.visual.fidelity import digest,file_hash
from validators.visual.cross_renderer import compare,REQUIRED_PROOFS

FIXTURE_HASH='3b19ae988759787d668550ad0253139b5b3813c9421f4a76917ed05b309b7245'
LOGICAL_IDS={'action.button.primary.medium','form.input.default.medium','form.select.default.medium'}


def require(value,reason):
    if not value:raise ValueError(reason)


def path_commands(svg,*,fill=None):
    root=ET.fromstring(svg);paths=[node for node in root.iter() if node.tag.endswith('}path') and (fill is None or node.get('fill')==fill)]
    commands=[]
    for node in paths:
        require(node.get('fill-rule','nonzero')=='nonzero' and 'transform' not in node.attrib,'unsupported_vector_path')
        pen=RecordingPen();parse_path(node.attrib['d'],pen);commands.append(pen.value)
    return commands


def bind_vector(svg,rows,native,*,text_fill=None):
    """Bind whole-component paths to actual Text exports at observed positions."""
    exported=path_commands(svg,fill=text_fill);texts=[node for node in native['nodes'] if node['type']=='TEXT']
    require(len(exported)==len(texts)==len(rows),'vector_text_inventory_mismatch')
    root=native['nodes'][0]['absoluteBounds']
    for node,actual in zip(texts,exported):
        row=next(item for item in rows if item['textReference']==node['reference'])
        observed=path_commands(row['svg']);require(len(observed)==1,'unsupported_text_fill_group')
        translation=(Decimal(str(node['absoluteBounds']['x']))-Decimal(str(root['x'])),Decimal(str(node['absoluteBounds']['y']))-Decimal(str(root['y'])))
        expected=[(op,tuple(tuple(Decimal(format(Decimal(str(v))+translation[i],'.6g')) for i,v in enumerate(point)) for point in points)) for op,points in observed[0]]
        require(canonical_directed_contours(expected)==canonical_directed_contours(actual),'vector_text_shape_mismatch')
        for i in (0,1):require(min(p[i] for _,pts in expected for p in pts)==min(Decimal(str(p[i])) for _,pts in actual for p in pts),'vector_text_position_mismatch')


def run(reference_directory,metadata_directory,*,file_reference):
    reference_directory=Path(reference_directory);metadata=Path(metadata_directory)
    require(file_hash(reference_directory/'component_ir.json')==FIXTURE_HASH,'unsupported_official_fixture_revision')
    bundle=load_json(reference_directory/'component_ir.json')
    require({r['logicalComponentId'] for r in bundle['components']}==LOGICAL_IDS,'unsupported_component_inventory')
    read=lambda name:load_json(metadata/name)
    font=read('official-runtime-font-evidence.json');bindings=read('official-source-font-bindings.json')
    source=read('official-runtime-render-state-evidence.json');identity=read('font-file-identity.json')
    outlines=read('native-current-text-outline.json');vectors=read('native-component-svg-capture.json')
    svg_probe=read('native-svg-browser-evidence.json');font_probe=read('browser-font-file-binding-evidence.json')
    require(all(r.get('fileReference')==file_reference and r.get('status')=='PASS' and r.get('createdNodeIds')==[] and r.get('mutatedNodeIds')==[] for r in (outlines,vectors)),'invalid_readonly_vector_capture')
    require(file_hash(metadata/'native-component-svg-capture.json')==svg_probe['svgCaptureSha256'],'vector_probe_input_mismatch')
    for proof in (svg_probe,font_probe):
        require(proof['status']=='PASS' and proof['referenceComponentIrSha256']==FIXTURE_HASH,'reference_probe_identity_mismatch')
        require({r['logicalId'] for r in proof['referenceMatches']}==LOGICAL_IDS and len(proof['referenceMatches'])==3 and all(r['screenshotMatches'] is True and r['environmentMatches'] is True for r in proof['referenceMatches']),'reference_not_reproduced')
    require(font_probe['temporaryFontFaceRemoved'] is True and font_probe['ownerStatesRestored'] is True,'font_probe_not_restored')
    pingfang=next(r for r in identity['requirements'] if r['familyName']=='PingFang SC')['matches'][0]
    require(font_probe['fontFileSha256']==pingfang['fileSha256'],'font_probe_file_mismatch')
    require(len(font_probe['observations'])==3 and {r['logicalId'] for r in font_probe['observations']}==LOGICAL_IDS and all(r['pngBytesExactlyMatchOfficialReference'] is True and r['ownerBoundsUnchanged'] is True and r['fontLoadStatus']=='loaded' for r in font_probe['observations']),'font_file_effect_unverified')
    captures=metadata/'render-state-captures'
    diagnostic=candidate_diagnostic.run(reference_directory,font,file_reference=file_reference,candidate_directory=captures,bindings=bindings,text_box_evidence=source)
    regions=candidate_diagnostic.validate_text_box_evidence(bundle,source,FIXTURE_HASH)
    inventory={'fileReference':file_reference,'components':[{'logicalId':r['logicalId'],'componentReference':r['componentReference']} for r in vectors['observations']]}
    baselines=compare_baseline_alignment(read('official-runtime-complete-baseline-evidence.json'),outlines,identity,inventory)
    require(len(baselines['observations'])==4 and all(r.get('positionStatus')=='ALIGNED' for r in baselines['observations']),'baseline_not_aligned')
    glyphs=compare_font_files(outlines,identity)
    served=read('served-ionicons-glyph-equivalence.json')
    served_manifest=metadata/'official-font-runtime-manifest.json'
    require(file_hash(served_manifest)==served['runtimeManifestSha256'],'served_font_manifest_mismatch')
    sibling=ROOT/'node_modules/view-ui-plus/dist/styles/fonts/ionicons.ttf'
    served_path=sibling.with_suffix('.woff2')
    verified=compare_served_glyph(load_json(served_manifest),served_path,served['servedSha256'],sibling,served['siblingSha256'])
    require(verified['status']=='PASS','served_glyph_mismatch')
    for row in glyphs['observations']:
        proof=row['contourComparison']
        require(row['dimensionEqual'] and (proof['nonzeroWinding']['status']=='PASS' or row['characters']=='\uf116' and proof['sixDigitSerialization']['status']=='PASS'),'glyph_geometry_unverified')
        native_row=next(r for r in outlines['observations'] if r['textReference']==row['textReference'])
        font_match=next(r for r in identity['requirements'] if r['familyName']==native_row['fontName']['family'])['matches'][0]
        actual=measure_glyphs(font_match['path'],font_match['fileSha256'],native_row['characters'],native_row['fontSize'],include_commands=True)
        native_commands=path_commands(native_row['svg']);require(len(native_commands)==1,'unsupported_glyph_group')
        require(min(p[0] for _,pts in actual['_commands'] for p in pts)==min(Decimal(str(p[0])) for _,pts in native_commands[0] for p in pts),'glyph_horizontal_origin_mismatch')
    proof_files=('official-runtime-font-evidence.json','official-source-font-bindings.json','official-runtime-render-state-evidence.json','font-file-identity.json','native-current-text-outline.json','native-component-svg-capture.json','native-svg-browser-evidence.json','browser-font-file-binding-evidence.json','official-runtime-complete-baseline-evidence.json','served-ionicons-glyph-equivalence.json')
    reports=[];candidates=[];proofs=[]
    for reference in bundle['components']:
        logical=reference['logicalComponentId'];directory=captures/logical
        require(verify_saved_capture(directory)['status']=='PASS','capture_integrity_failed')
        manifest=load_json(directory/'capture_manifest.json');native=load_json(directory/'native-evidence.json')
        geometry=next(r for r in diagnostic['components'] if r['logicalId']==logical)
        covered=[r for r in geometry['checks'] if not r['field'].startswith('raster.')]
        require(not geometry['issues'] and covered and all(r['status']=='PASS' for r in covered),'geometry_style_mismatch')
        require(all(node['properties'].get('visible') is True and node['properties'].get('rotation')==0 and node['properties'].get('isMask') is False for node in native['nodes']),'unsupported_native_render_state')
        require(all(node['properties'].get('paragraphIndent')==0 and node['properties'].get('paragraphSpacing')==0 and node['properties'].get('strokes')==[] for node in native['nodes'] if node['type']=='TEXT'),'unsupported_native_text_geometry')
        rendering=next(r for r in source['renderingSettings'] if r['logicalId']==logical)
        render=render_state_diagnostic.compare_render_state(reference,native,rendering)
        require(render['checks'] and all(r['status']=='PASS' for r in render['checks']) and all(r['reason']=='native_passthrough_text_not_css_normalized' for r in render['unverified']),'render_state_unverified')
        blend_path=metadata/'blend-mode-probes'/f'{logical}.json'
        blend=compare_experiment(load_json(blend_path),native,(directory/'native.png').read_bytes(),manifest)
        require(blend['status']=='PASS' and blend['normalVsBeforeChangedPixels']==0 and blend['restoredVsBeforeChangedPixels']==0,'static_blending_unverified')
        vector=next(r for r in vectors['observations'] if r['logicalId']==logical)
        sample=next(r for r in svg_probe['samples'] if r['logicalId']==logical)
        require(vector['componentReference']==sample['componentReference']==manifest['componentReference'] and manifest['fileReference']==file_reference,'vector_capture_identity_mismatch')
        require(hashlib.sha256(vector['svg'].encode()).hexdigest()==sample['svgSha256'],'vector_svg_hash_mismatch')
        vector_png=metadata/'native-svg-browser-rasters'/sample['pngPath']
        require(file_hash(vector_png)==sample['pngSha256'],'vector_raster_hash_mismatch')
        text_ids={node['reference'] for node in native['nodes'] if node['type']=='TEXT'}
        rows=[r for r in outlines['observations'] if r['textReference'] in text_ids]
        require({r['textReference'] for r in rows}==text_ids,'text_outline_inventory_mismatch')
        for row in rows:
            props=next(node['properties'] for node in native['nodes'] if node['reference']==row['textReference'])
            require(all(row[k]==props[k] for k in ('characters','fontName','fontWeight','fontSize','lineHeight')),'text_outline_capture_mismatch')
        bind_vector(vector['svg'],rows,native)
        with Image.open(reference_directory/reference['screenshot']['path']) as a,Image.open(vector_png) as b:
            partition=candidate_diagnostic.partition_surface_differences(a,b,reference,regions[logical])
        require(partition['categories']['sourceCornerRectangles']['changedPixels']==0 and partition['categories']['unclassified']['changedPixels']==0,'unproved_vector_surface_difference')
        require(geometry['raster']['surfacePartition']['categories']['unclassified']['changedPixels']==0,'unproved_native_surface_difference')
        paints=[];root=native['nodes'][0]['absoluteBounds']
        for row in rows:
            node=next(n for n in native['nodes'] if n['reference']==row['textReference'])
            shape=next(g for g in glyphs['observations'] if g['textReference']==row['textReference'])
            matched=[r['componentBounds'] for r in regions[logical] if r['text']==row['characters']]
            if row['characters']=='\uf116':matched=[n['bounds'] for n in reference['nodes'] if n['path']=='0.0.1.1']
            require(len(matched)==1,'glyph_source_region_unresolved')
            region=matched[0];bounds=node['absoluteBounds']
            require(bounds['x']-root['x']==region['x'] and bounds['width']==region['width']==shape['source']['advancePx'],'text_horizontal_geometry_mismatch')
            color=node['properties']['fills'][0]['color']
            paints.append({'characters':row['characters'],'region':region,
                'advances':[float(Decimal(str(g['advanceFontUnits']))*Decimal(str(row['fontSize']))/Decimal(shape['source']['unitsPerEm'])) for g in shape['source']['glyphs']],
                'foreground':[round(color[k]*255) for k in ('r','g','b')],
                'background':[45,140,240] if reference['componentType']=='Button' else [255,255,255]})
        proof={'logicalId':logical,'inputHashes':{name:file_hash(metadata/name) for name in proof_files},
            'blendExperimentSha256':file_hash(blend_path),'nativeEvidenceSha256':manifest['nativeEvidenceSha256'],
            'geometryAndStyle':covered,'renderState':render,'blendState':blend,
            'glyphGeometry':[r for r in glyphs['observations'] if r['textReference'] in text_ids],
            'baselines':[r for r in baselines['observations'] if r['logicalId']==logical],
            'vectorSurfaceComparison':partition,'vectorRasterSha256':sample['pngSha256']}
        candidate={'normalizationVersion':'0.2.0','scope':'production','evidenceKind':'native-design-capture',
            **{k:reference[k] for k in ('logicalComponentId','variant','state','props','content','fixtureContext')},
            'sourceVersion':reference['provenance']['sourceVersion'],'componentIrSha256':digest(reference),
            'verification':dict.fromkeys(REQUIRED_PROOFS,'PASS'),'glyphPaintSamples':paints,'allowedCornerRegions':partition['cornerRectangles'],
            'rasterContext':{'deviceScaleFactor':1,'background':'white','scale':1,'resize':False,'crop':False},
            'screenshotSha256':manifest['comparisonPngSha256'],'vectorRasterSha256':sample['pngSha256'],
            'capture':{k:manifest[k] for k in ('captureId','exporterVersion','nativeEvidenceSha256')}}
        candidate['capture']['proofBundleSha256']=digest(proof)
        reports.append(compare(reference,candidate,reference_directory/reference['screenshot']['path'],directory/'comparison-white.png',vector_png))
        candidates.append(candidate);proofs.append(proof)
    return {'status':'PASS' if all(r['status']=='PASS' for r in reports) else 'FAIL','components':reports,'candidates':candidates,'proofs':proofs}
