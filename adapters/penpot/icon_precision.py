"""Diagnostic only: identify exact Float32 encoding of official SVG coordinates."""
import hashlib
import json
import math
import struct
from fontTools.svgLib.path import parse_path
from fontTools.pens.recordingPen import RecordingPen
import xml.etree.ElementTree as ET

APPROVED_ICON_ENCODING_RULE='task-010-source-derived-float32/0.1.0'
APPROVED_SOURCES={
    'remix.settings-3-line':'f2e1fd30e6eadb8d5636f5037cf477f38ef81b235757d3ed290b92b2c002fec1',
    'remix.download-line':'ad83ac7dc9d4c6af651a53068e928d82f9402cfd05a924742388549846032f43',
}


def validate_approved_icon_encoding(icon_id,source_svg,native_d):
    """Only the approved geometry subcheck; never a complete native admission."""
    expected=APPROVED_SOURCES.get(icon_id)
    if not expected or hashlib.sha256(source_svg).hexdigest()!=expected:
        raise ValueError('icon_encoding_unapproved_source')
    root=ET.fromstring(source_svg)
    paths=list(root.iter('{http://www.w3.org/2000/svg}path'))
    if root.attrib.get('viewBox')!='0 0 24 24' or len(paths)!=1:
        raise ValueError('icon_encoding_source_inventory_mismatch')
    result=compare_path_encoding(paths[0].attrib['d'],native_d)
    if not result['sourceFloat32EncodingExact']:
        raise ValueError('icon_encoding_not_exact_source_float32')
    return {**result,'status':'PASS','scope':'approved-icon-path-encoding-subcheck',
        'ruleVersion':APPROVED_ICON_ENCODING_RULE,'iconId':icon_id,'sourceSvgSha256':expected,
        'limitations':['Geometry subcheck only: native paint, SVG/PNG capture and real instances remain mandatory.']}


def compare_path_encoding(source_d,native_d):
    source,native=RecordingPen(),RecordingPen()
    parse_path(source_d,source);parse_path(native_d,native)
    allowed={'moveTo','lineTo','curveTo','closePath'}
    if any(op not in allowed for op,points in source.value+native.value):raise ValueError('unsupported_icon_path_operator')
    def f32(value):
        if not math.isfinite(value):raise ValueError('invalid_icon_coordinate')
        return struct.unpack('f',struct.pack('f',value))[0]
    encoded=[(op,tuple((f32(x),f32(y)) for x,y in points)) for op,points in source.value]
    errors=[abs(a-b) for (op,points),(native_op,native_points) in zip(source.value,native.value) for p,q in zip(points,native_points) for a,b in zip(p,q)]
    canonical=lambda value:hashlib.sha256(json.dumps(value,separators=(',',':')).encode()).hexdigest()
    return {'status':'OBSERVED','scope':'source-derived-float32-path-diagnostic',
        'sourceCoordinatesExact':source.value==native.value,'sourceFloat32EncodingExact':encoded==native.value,
        'sourceCommandCount':len(source.value),'nativeCommandCount':len(native.value),
        'maxObservedCoordinateDelta':max(errors,default=0),'sourceCommandsSha256':canonical(source.value),
        'encodedSourceCommandsSha256':canonical(encoded),'nativeCommandsSha256':canonical(native.value),
        'admissionEligible':False,'limitations':['Float32 identification is diagnostic, not approval to change strict geometry acceptance.']}
