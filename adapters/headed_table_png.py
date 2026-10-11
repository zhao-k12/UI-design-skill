"""Exact TASK-020 raw PNG dimensions and alpha subgate, without normalization."""
from hashlib import sha256
from io import BytesIO
from math import ceil
from PIL import Image
from adapters.headed_table_policy import require_scope, DECISION_SHA256

def verify_raw_png(plan, platform, raw):
    require_scope(plan)
    if platform not in ('figma','penpot'):
        raise ValueError('headed_png_platform_unsupported')
    with Image.open(BytesIO(raw)) as original:
        if original.format!='PNG' or getattr(original,'n_frames',1)!=1:
            raise ValueError('headed_native_single_png_required')
        size=(plan['rootBounds']['width'],ceil(plan['rootBounds']['height']))
        if original.size!=size:
            raise ValueError('headed_png_dimensions_mismatch')
        pixels=original.convert('RGBA')
        for y in range(pixels.height):
            expected=223 if platform=='figma' and y==pixels.height-1 else 255
            if pixels.crop((0,y,pixels.width,y+1)).getextrema()[3]!=(expected,expected):
                raise ValueError('headed_png_alpha_mismatch')
    return {'status':'PASS','scope':'raw-native-png-dimensions-and-alpha-only',
            'platform':platform,'logicalId':plan['logicalId'],
            'decisionSha256':DECISION_SHA256,'nativePngSha256':sha256(raw).hexdigest(),
            'dimensions':list(size),'lastRowAlpha':223 if platform=='figma' else 255,
            'otherRowsAlpha':255,'productionAdmission':False,'fidelityGate':'NOT_RUN',
            'limitations':['Exact root clipping and independent vector evidence remain required.',
                           'This subgate does not verify PNG colors, content or edge coverage.']}
