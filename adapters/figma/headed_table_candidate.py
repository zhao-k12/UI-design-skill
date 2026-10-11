"""Derive candidate baseline from independently exported uploaded CFF glyph."""
import json
from decimal import Decimal
from pathlib import Path
import xml.etree.ElementTree as ET
from fontTools.pens.recordingPen import RecordingPen
from fontTools.svgLib.path import parse_path
from adapters.headed_table import prepare_source,require
from adapters.figma.configurable_font_calibration import measure
from adapters.figma.font_outline_comparison import compare_six_digit_serialization
from adapters.figma.configurable_table_candidate import prepare as prepare_body
from validators.ui_ir import ROOT,load_json
from validators.visual.fidelity import file_hash

SEMIBOLD_HASH='ca115f4f17266f1ff5ead3ef1049814eafb4f61cc279134e0a8b3d817532fb78'

def prepare(directory,file_reference,semibold_path):
    metadata=ROOT/'adapters/figma/metadata/headed-table-native'
    capture=load_json(metadata/'semibold-readback.json')
    require(capture['status']=='PASS' and capture['fileReference']==file_reference and not capture['createdNodeIds'] and not capture['mutatedNodeIds'],'invalid_semibold_calibration')
    require(capture['characters']=='一' and capture['fontName']=={'family':'PingFang SC','style':'Semibold'} and capture['fontSize']==14 and capture['lineHeight']=={'unit':'PIXELS','value':21},'invalid_semibold_calibration_font')
    source,advance=measure(semibold_path,SEMIBOLD_HASH,'一',14)
    paths=list(ET.fromstring(capture['svg']));native=RecordingPen()
    require(len(paths)==1,'ambiguous_semibold_outline')
    parse_path(paths[0].attrib['d'],native)
    # Compare lower extrema of both encodings; no geometric fitting.
    source_y=min(p[1] for _,points in source for p in points)
    native_y=min(Decimal(str(p[1])) for _,points in native.value for p in points)
    offset=native_y-source_y
    shifted=[(op,tuple((p[0],p[1]+offset) for p in points)) for op,points in source]
    comparison=compare_six_digit_serialization(shifted,native.value,native_fill_rule=paths[0].get('fill-rule','nonzero'),native_path_count=1)
    require(comparison['status']=='PASS' and capture['absoluteBounds']['width']==advance and capture['absoluteBounds']['height']==21,'semibold_calibration_outline_mismatch')
    base=prepare_body(ROOT/'component-builder/runtime-renderer/metadata/configurable-table-source/two-column',file_reference,arial_path='C:/Windows/Fonts/arial.ttf',metadata_directory=ROOT/'adapters/figma/metadata/configurable-table-native')
    plan=prepare_source(directory)
    for row in plan['rows']:
        for cell in row['cells']:
            cell['text']['fontStyle']='Semibold' if cell['text']['role']=='header' else 'Regular'
    return {**plan,'fileReference':file_reference,'name':'candidate/'+plan['logicalId'],
            'fontBaselineOffsets':{**base['fontBaselineOffsets'],'PingFang SC/Semibold':float(offset)},
            'fontCalibrationCaptureHashes':{**base['fontCalibrationCaptureHashes'],'PingFang SC/Semibold':file_hash(metadata/'semibold-readback.json')},
            'semiboldFontSha256':SEMIBOLD_HASH,'semiboldContourCalibration':comparison,'fontEncodingAdmission':'NOT_APPROVED'}
