"""AD-017: strict semantic proofs plus independently bound raster edge bands."""
from pathlib import Path
from decimal import Decimal
import math
from PIL import Image
from validators.visual.fidelity import digest,file_hash

POLICY_VERSION='0.2.0'
REQUIRED_PROOFS=('geometryAndStyle','content','fontBinding','glyphGeometry','baselines','renderState','sourceReproduction','vectorBinding')


def edge_band(image):
    """One-pixel neighborhoods of color transitions, then one-pixel coverage support.

    The vector raster is an independent native-outline observation, never the
    reference or the candidate PNG; geometry proofs remain mandatory.
    """
    image=image.convert('RGBA');edges=set()
    for y in range(image.height):
        for x in range(image.width):
            color=image.getpixel((x,y))
            if any(image.getpixel((xx,yy))!=color for yy in range(max(0,y-1),min(image.height,y+2)) for xx in range(max(0,x-1),min(image.width,x+2))):edges.add((x,y))
    return {(xx,yy) for x,y in edges for yy in range(max(0,y-1),min(image.height,y+2)) for xx in range(max(0,x-1),min(image.width,x+2))}


def glyph_retention(source,native,samples):
    rows=[]
    for sample in samples:
        box=sample['region'];advances=sample['advances'];text=sample['characters'];fg=sample['foreground'];bg=sample['background']
        if not text or len(text)!=len(advances) or any(type(v) not in (int,float) or not math.isfinite(v) or v<=0 for v in advances) or any(type(box[k]) not in (int,float) or not math.isfinite(box[k]) for k in ('x','y','width','height')) or sum(Decimal(str(v)) for v in advances)!=Decimal(str(box['width'])):raise ValueError('invalid_verified_glyph_regions')
        if box['x']<0 or box['y']<0 or box['height']<=0 or box['x']+box['width']>source.width or box['y']+box['height']>source.height:raise ValueError('glyph_region_out_of_bounds')
        if any(len(color)!=3 or any(type(v) is not int or not 0<=v<=255 for v in color) for color in (fg,bg)):raise ValueError('invalid_glyph_paint')
        direction=[f-b for f,b in zip(fg,bg)];denominator=sum(v*v for v in direction)
        if not denominator:raise ValueError('invisible_glyph_paint')
        cursor=box['x']
        for char,advance in zip(text,advances):
            masses=[]
            for image in (source,native):
                mass=0
                for y in range(image.height):
                    for x in range(image.width):
                        if cursor<=x+.5<cursor+advance and box['y']<=y+.5<box['y']+box['height']:
                            pixel=image.getpixel((x,y));mass+=max(0,min(1,sum((p-b)*d for p,b,d in zip(pixel[:3],bg,direction))/denominator))
                masses.append(mass)
            ratio=masses[1]/masses[0] if masses[0] else None
            # This is a missing/solid-glyph guard, never an aggregate admission budget.
            rows.append({'character':char,'sourceInkProxy':masses[0],'nativeInkProxy':masses[1],
                'retentionRatio':ratio,'status':'PASS' if ratio is not None and .5<=ratio<=2 else 'FAIL'})
            cursor+=advance
    if not rows:raise ValueError('missing_verified_glyph_regions')
    return rows


def compare(reference,candidate,reference_png,native_png,vector_png,*,scope='production'):
    if scope not in ('production','test-fixture'):raise ValueError('invalid_cross_renderer_scope')
    report={'gateVersion':POLICY_VERSION,'scope':scope,'logicalComponentId':reference['logicalComponentId'],
        'componentType':reference['componentType'],'variants':[reference['variant']],
        'sourceVersion':reference['provenance']['sourceVersion'],'componentIrSha256':digest(reference),
        'status':'FAIL','admissionEligible':False,'issues':[],'checks':{}}
    def fail(code):report['issues'].append({'code':code,'severity':'FAIL'})
    if candidate.get('scope')!=scope or candidate.get('evidenceKind')!='native-design-capture' or candidate.get('normalizationVersion')!=POLICY_VERSION:fail('invalid_normalized_native_capture')
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
                        unpermitted+=not any(r['x']<=x+.5<r['x']+r['width'] and r['y']<=y+.5<r['y']+r['height'] for r in permitted)
            if outside:fail('difference_outside_verified_edge_band')
            if unpermitted:fail('difference_outside_verified_text_or_corners')
            try:retention=glyph_retention(a,b,candidate.get('glyphPaintSamples',[]))
            except (ValueError,KeyError,TypeError):retention=[];fail('invalid_glyph_retention_evidence')
            if any(row['status']!='PASS' for row in retention):fail('glyph_retention_failed')
            report['checks']['screenshot']={'changedPixels':changed,'changedPixelsOutsideEdgeBand':outside,
                'changedPixelsOutsidePermittedRegions':unpermitted,
                'maxChannelDelta':maximum,'policy':'evidence-bound-edges-0.2.0',
                'vectorRasterSha256':file_hash(vector_png),'edgeBandPixelCount':len(band)}
            report['checks']['glyphRetention']=retention
    report['checks']['normalizationProofs']=proofs
    if not report['issues']:report.update(status='PASS',admissionEligible=scope=='production')
    return report
