"""Exact four-corner pixel observations, with no geometric or raster tolerance."""
import hashlib
import math
from pathlib import Path
from PIL import Image
from adapters.figma.candidate_diagnostic import partition_surface_differences
from adapters.figma.native_capture import verify_saved_capture
from validators.component_ir import verify_artifacts
from validators.ui_ir import load_json


def diagnose_corners(left,right,reference):
    partition=partition_surface_differences(left,right,reference,[])
    surface=next(row for row in reference['nodes'] if row['path']==partition['sourcePath'])
    box=surface['bounds'];radius=partition['sourceRadiusPx']
    values=[box[key] for key in ('x','y','width','height')]+[radius]
    if any(isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value!=int(value) for value in values):raise ValueError('corner_integer_pixel_grid_unsupported')
    x,y,w,h,r=map(int,values)
    if x<0 or y<0 or w<=0 or h<=0 or x+w>left.width or y+h>left.height:raise ValueError('corner_surface_outside_raster')
    left=left.convert('RGBA');right=right.convert('RGBA');rows=[]
    for name,flip_x,flip_y in [('top-left',False,False),('top-right',True,False),('bottom-left',False,True),('bottom-right',True,True)]:
        pixels=[]
        for dy in range(r):
            for dx in range(r):
                px=x+w-1-dx if flip_x else x+dx;py=y+h-1-dy if flip_y else y+dy
                a=left.getpixel((px,py));b=right.getpixel((px,py))
                delta=[second-first for first,second in zip(a,b)]
                pixels.append({'distanceFromOuterEdges':[dx,dy],'pixel':[px,py],
                    'sourceRgba':list(a),'nativeRgba':list(b),'signedDeltaRgba':delta})
        changed=[row for row in pixels if any(row['signedDeltaRgba'])]
        rows.append({'corner':name,'changedPixels':len(changed),
            'maximumChannelDelta':max((abs(value) for row in changed for value in row['signedDeltaRgba']),default=0),
            'pixels':pixels})
    def symmetric(field):return all([row[field] for row in corner['pixels']]==[row[field] for row in rows[0]['pixels']] for corner in rows[1:])
    return {'scope':'figma_four_corner_raster_diagnostic','status':'REVIEW',
        'logicalId':reference['logicalComponentId'],'sourcePath':partition['sourcePath'],'sourceRadiusPx':radius,
        'corners':rows,'cornerChangedPixels':sum(row['changedPixels'] for row in rows),
        'sourceCornerPixelsExactlySymmetric':symmetric('sourceRgba'),
        'nativeCornerPixelsExactlySymmetric':symmetric('nativeRgba'),
        'cornerDeltaPatternsExactlySymmetric':symmetric('signedDeltaRgba'),
        'admissionEligible':False,'fidelityGate':'NOT_RUN','cause':'UNDETERMINED',
        'limitations':['Mirrored pixel positions within observed source radius rectangles; no curve fitting or glyph masks.',
            'Symmetry or channel differences do not prove radius error, positional offset or engine behavior.']}


def run(reference_directory,capture_directories,*,file_reference):
    reference_directory=Path(reference_directory)
    if verify_artifacts(reference_directory):raise ValueError('corner_reference_integrity_failed')
    reports=[]
    for reference in load_json(reference_directory/'component_ir.json')['components']:
        logical=reference['logicalComponentId'];directory=Path(capture_directories[logical])
        if verify_saved_capture(directory)['status']!='PASS':raise ValueError('corner_native_integrity_failed')
        manifest=load_json(directory/'capture_manifest.json')
        if manifest['fileReference']!=file_reference or manifest['logicalId']!=logical or manifest['evidenceScope']!='production':raise ValueError('corner_native_identity_mismatch')
        source_path=reference_directory/reference['screenshot']['path'];native_path=directory/'comparison-white.png'
        with Image.open(source_path) as left,Image.open(native_path) as right:report=diagnose_corners(left,right,reference)
        report['sourcePngSha256']=hashlib.sha256(source_path.read_bytes()).hexdigest()
        report['nativePngSha256']=hashlib.sha256(native_path.read_bytes()).hexdigest()
        reports.append(report)
    return {'scope':'figma_corner_raster_diagnostic_batch','status':'REVIEW','components':reports,
        'admissionEligible':False,'fidelityGate':'NOT_RUN'}
