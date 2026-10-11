"""TASK-019 Table pixel ownership policy; frozen AD-017 helpers remain unchanged."""
from PIL import Image
from pathlib import Path
from validators.visual.cross_renderer import POLICY_VERSION, REQUIRED_PROOFS, edge_band, glyph_retention
from validators.visual.fidelity import digest,file_hash
TABLE_PIXEL_COVERAGE_VERSION="0.2.1"

def compare(reference,candidate,reference_png,native_png,vector_png,*,scope='production'):
    if scope not in ('production','test-fixture'):raise ValueError('invalid_cross_renderer_scope')
    version=candidate.get('normalizationVersion')
    coverage=version==TABLE_PIXEL_COVERAGE_VERSION
    report={'gateVersion':version if version in (POLICY_VERSION,TABLE_PIXEL_COVERAGE_VERSION) else POLICY_VERSION,'scope':scope,'logicalComponentId':reference['logicalComponentId'],
        'componentType':reference['componentType'],'variants':[reference['variant']],
        'sourceVersion':reference['provenance']['sourceVersion'],'componentIrSha256':digest(reference),
        'status':'FAIL','admissionEligible':False,'issues':[],'checks':{}}
    if coverage: report['pixelRegionPolicy']='positive-area-intersection'
    def fail(code):report['issues'].append({'code':code,'severity':'FAIL'})
    if candidate.get('scope')!=scope or candidate.get('evidenceKind')!='native-design-capture' or version not in (POLICY_VERSION,TABLE_PIXEL_COVERAGE_VERSION):fail('invalid_normalized_native_capture')
    if coverage and (reference['componentType']!='Table' or candidate.get('pixelRegionPolicy')!='positive-area-intersection'):fail('unsupported_pixel_region_policy')
    if candidate.get('rasterContext')!={'deviceScaleFactor':1,'background':'white','scale':1,'resize':False,'crop':False}:fail('unsupported_raster_context')
    for key,value in [('logicalComponentId',reference['logicalComponentId']),('variant',reference['variant']),
        ('state',reference['state']),('props',reference['props']),('content',reference['content']),
        ('fixtureContext',reference['fixtureContext']),('sourceVersion',reference['provenance']['sourceVersion']),('componentIrSha256',digest(reference))]:
        if candidate.get(key)!=value:fail('native_context_mismatch:'+key)
    proofs=candidate.get('verification',{})
    for name in REQUIRED_PROOFS:
        if proofs.get(name)!='PASS':fail('unverified:'+name)
    capture=candidate.get('capture',{});report['capture']=capture
    if not all(isinstance(capture.get(k),str) and capture[k] for k in ('captureId','exporterVersion','nativeEvidenceSha256')):fail('missing_native_capture_identity')
    for key in ('nativeEvidenceSha256','proofBundleSha256'):
        value=capture.get(key)
        if not isinstance(value,str) or len(value)!=64 or any(c not in '0123456789abcdef' for c in value):fail('invalid_capture_hash:'+key)
    if candidate.get('screenshotSha256')!=file_hash(native_png) or candidate.get('vectorRasterSha256')!=file_hash(vector_png):fail('raster_binding_mismatch')
    if reference['screenshot']['sha256']!=file_hash(reference_png):fail('reference_raster_binding_mismatch')
    if len({Path(p).resolve() for p in (reference_png,native_png,vector_png)})!=3:fail('reused_raster_input')
    report.update(candidateSha256=digest(candidate),referenceScreenshotSha256=file_hash(reference_png),
        candidateScreenshotSha256=file_hash(native_png),candidateEvidenceKind=candidate.get('evidenceKind'))
    report['checks']['geometryAndStyle']='PASS' if not report['issues'] else 'FAIL'
    with Image.open(reference_png) as a,Image.open(native_png) as b,Image.open(vector_png) as v:
        a,b,v=a.convert('RGBA'),b.convert('RGBA'),v.convert('RGBA')
        if any(img.getextrema()[3]!=(255,255) for img in (a,b,v)):fail('unverified_transparent_comparison_context')
        if a.size!=b.size or a.size!=v.size:fail('raster_size_mismatch')
        else:
            band=edge_band(v);changed=outside=unpermitted=0;maximum=0
            permitted=[row['region'] for row in candidate.get('glyphPaintSamples',[])]+candidate.get('allowedCornerRegions',[])
            for y in range(a.height):
                for x in range(a.width):
                    delta=max(abs(c-d) for c,d in zip(a.getpixel((x,y)),b.getpixel((x,y))))
                    if delta:
                        changed+=1;outside+=(x,y) not in band;maximum=max(maximum,delta)
                        # A fractional text rectangle can cover part of a pixel
                        # whose center lies outside. This classifies ownership;
                        # every difference still requires the unchanged edge band.
                        unpermitted+=not any((r['x']<x+1 and x<r['x']+r['width'] and r['y']<y+1 and y<r['y']+r['height']) if coverage else (r['x']<=x+.5<r['x']+r['width'] and r['y']<=y+.5<r['y']+r['height']) for r in permitted)
            if outside:fail('difference_outside_verified_edge_band')
            if unpermitted:fail('difference_outside_verified_text_or_corners')
            try:retention=glyph_retention(a,b,candidate.get('glyphPaintSamples',[]))
            except (ValueError,KeyError,TypeError):retention=[];fail('invalid_glyph_retention_evidence')
            if any(row['status']!='PASS' for row in retention):fail('glyph_retention_failed')
            report['checks']['screenshot']={'changedPixels':changed,'changedPixelsOutsideEdgeBand':outside,
                'changedPixelsOutsidePermittedRegions':unpermitted,
                'maxChannelDelta':maximum,'policy':'evidence-bound-edges-'+report['gateVersion'],
                'vectorRasterSha256':file_hash(vector_png),'edgeBandPixelCount':len(band)}
            report['checks']['glyphRetention']=retention
    report['checks']['normalizationProofs']=proofs
    if not report['issues']:report.update(status='PASS',admissionEligible=scope=='production')
    return report
