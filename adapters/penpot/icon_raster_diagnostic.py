"""Read-only icon raster evidence. No new raster policy or registry admission."""
import base64
import hashlib
import io
import json
from pathlib import Path
from PIL import Image
from validators.visual.cross_renderer import edge_band
from adapters.penpot.icon_native_evidence import verify_icon_native_evidence


def regions(points):
    """Eight-connected foreground regions; record topology, not pixel tolerance."""
    remaining=set(points);result=[]
    while remaining:
        seed=min(remaining);stack=[seed];remaining.remove(seed);part={seed}
        while stack:
            x,y=stack.pop()
            for dy in (-1,0,1):
                for dx in (-1,0,1):
                    p=(x+dx,y+dy)
                    if p in remaining:remaining.remove(p);part.add(p);stack.append(p)
        result.append({'bounds':[min(x for x,y in part),min(y for x,y in part),max(x for x,y in part)+1,max(y for x,y in part)+1],'pixelCount':len(part)})
    return sorted(result,key=lambda r:r['bounds'])


def observe_pixels(source,native,vector):
    if source.size!=native.size or source.size!=vector.size or source.size!=(24,24):raise ValueError('icon_raster_dimensions_mismatch')
    source,vector=source.convert('RGBA'),vector.convert('RGBA');raw=native.convert('RGBA')
    native=Image.new('RGBA',raw.size,'white');native.alpha_composite(raw)
    if source.tobytes()!=vector.tobytes():raise ValueError('icon_source_vector_pixels_mismatch')
    band=edge_band(vector);changed=[];source_ink=set();native_ink=set();bad_paint=[]
    for y in range(24):
        for x in range(24):
            p=(x,y);a,b,c=source.getpixel(p),native.getpixel(p),raw.getpixel(p)
            if a[3]!=255:raise ValueError('icon_source_background_not_opaque')
            if a[:3]!=(255,255,255):source_ink.add(p)
            if c[3]:
                native_ink.add(p)
                if c[:3]!=(0,0,0):bad_paint.append(p)
            if a!=b:changed.append({'pixel':list(p),'sourceRgba':list(a),'nativeWhiteRgba':list(b),'nativeRawRgba':list(c),'inVerifiedEdgeBand':p in band})
    source_regions,native_regions=regions(source_ink),regions(native_ink)
    all_pixels={(x,y) for x in range(24) for y in range(24)}
    source_voids,native_voids=regions(all_pixels-source_ink),regions(all_pixels-native_ink)
    topology_equal=([r['bounds'] for r in source_regions]==[r['bounds'] for r in native_regions] and [r['bounds'] for r in source_voids]==[r['bounds'] for r in native_voids])
    ink_bounds_equal=[r['bounds'] for r in source_regions]==[r['bounds'] for r in native_regions]
    region_counts_equal=len(source_regions)==len(native_regions) and len(source_voids)==len(native_voids)
    outside=[p['pixel'] for p in changed if not p['inVerifiedEdgeBand']]
    return {'status':'OBSERVED','sourcePixelsExact':not changed,'changedPixels':len(changed),'changedPixelsOutsideVerifiedEdgeBand':len(outside),'edgeBandPixelCount':len(band),'pixels':changed,'sourceInkRegions':source_regions,'nativeInkRegions':native_regions,'sourceVoidRegions':source_voids,'nativeVoidRegions':native_voids,'inkAndVoidRegionBoundsExact':topology_equal,'inkRegionBoundsExact':ink_bounds_equal,'inkAndVoidRegionCountsExact':region_counts_equal,'wrongNativePaintPixels':bad_paint,'nonEmptyNativeInk':bool(native_ink),'proposedEvidenceConditionsMet':bool(native_ink) and not bad_paint and not outside and ink_bounds_equal and region_counts_equal,'acceptance':'PENDING_DECISION','admissionEligible':False}


def run(metadata_directory):
    base=Path(metadata_directory);raw=(base/'latest-main-capture.json').read_bytes();receipt=json.loads(raw)
    plan_path=base.parent/'icon-source-plan/plan.json';plan=json.loads(plan_path.read_bytes());probe_path=base/'latest-svg-probe.json';probe=json.loads(probe_path.read_bytes())
    evidence=verify_icon_native_evidence(plan,receipt,probe,raw)
    repeat_path=base/'content-capture.json';repeat=json.loads(repeat_path.read_bytes())['result']
    if any(repeat.get(k)!=receipt['result'].get(k) for k in ('fileReference','pageReference','fileRevision','registrySha256','sourceVersion')) or repeat.get('createdNodeIds')!=[] or repeat.get('mutatedNodeIds')!=[]:raise ValueError('icon_repeat_context_mismatch')
    rows=[]
    for item in receipt['result']['icons']:
        icon=item['iconId'];row=next(i for i in repeat['icons'] if i['iconId']==icon)
        if row.get('rasterScope')!='original-content-group-under-transparent-component-board' or row['nodes']!=item['nodes'] or row['componentReference']!=item['componentReference'] or row['mainReference']!=item['mainReference'] or row.get('nativeSvgBase64')!=item.get('nativeSvgBase64'):raise ValueError('icon_repeat_geometry_mismatch')
        png=base64.b64decode(item['nativePngBase64'],validate=True);repeat_png=base64.b64decode(row['nativePngBase64'],validate=True)
        if png!=repeat_png:raise ValueError('icon_independent_native_png_not_identical')
        observation=next(i for i in probe['observations'] if i['iconId']==icon)
        paths=[base/(icon+'.source.png'),base/(icon+'.native.png')]
        if any(hashlib.sha256(path.read_bytes()).hexdigest()!=observation[role]['pngSha256'] for path,role in zip(paths,('source','native'))):raise ValueError('icon_raster_probe_binding_mismatch')
        with Image.open(paths[0]) as source,Image.open(io.BytesIO(png)) as native,Image.open(paths[1]) as vector:
            result=observe_pixels(source,native,vector)
        rows.append({'iconId':icon,'componentReference':item['componentReference'],'nativePngSha256':hashlib.sha256(png).hexdigest(),'independentContentGroupPngBytesExact':True,'repeatCaptureStatus':repeat['status'],'repeatCaptureComplete':repeat['status']=='CAPTURED',**result})
    return {'status':'OBSERVED','scope':'locked-icons-native-raster-diagnostic','nativeEvidenceSubcheckStatus':evidence['status'],'receiptSha256':hashlib.sha256(raw).hexdigest(),'repeatReceiptSha256':hashlib.sha256(repeat_path.read_bytes()).hexdigest(),'sourcePlanSha256':hashlib.sha256(plan_path.read_bytes()).hexdigest(),'svgProbeSha256':hashlib.sha256(probe_path.read_bytes()).hexdigest(),'diagnosticScriptSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'normalization':'white-alpha-composite-only-no-crop-resize-shift','edgeBandDefinition':'existing-AD-017-edge_band-diagnostic-only','rasterPolicy':'PENDING_DECISION','admissionEligible':False,'results':rows,'limitations':['Edge localization and repeatability do not alone prove the cause of raster differences.','No new tolerance or icon raster allowance is approved by this diagnostic.','Original main PNG remains the production screenshot; partial group SVG export is not a complete repeat capture.']}
