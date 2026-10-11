"""Source plans with independently measured font baselines; no admission."""
from decimal import Decimal
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from fontTools.pens.recordingPen import RecordingPen
from fontTools.svgLib.path import parse_path
from adapters.configurable_table import prepare_source,require
from adapters.figma.configurable_font_calibration import measure
from adapters.figma.font_outline_comparison import compare_font_files,canonical_directed_contours
from validators.ui_ir import ROOT,load_json
from validators.visual.fidelity import file_hash

ARIAL_HASH='c9b76220a5be42ead4733611e417cd65c5fd8aeaa33eb56576ac378a37d130a1'


def prepare(directory,file_reference,*,arial_path,metadata_directory):
    metadata=Path(metadata_directory);capture=load_json(metadata/'arial-glyph-readback-1.json')
    require(capture['status']=='PASS' and capture['fileReference']==file_reference and not capture['createdNodeIds'] and not capture['mutatedNodeIds'],'invalid_arial_baseline_capture')
    period=next(row for row in capture['observations'] if row['characters']=='.')
    require(period['fontName']=={'family':'Arial','style':'Regular'} and period['fontSize']==14 and period['lineHeight']=={'unit':'PIXELS','value':21},'unsupported_arial_baseline_font')
    source,_=measure(arial_path,ARIAL_HASH,'.',14);paths=list(ET.fromstring(period['svg']));native=RecordingPen()
    require(len(paths)==1 and paths[0].get('fill-rule','nonzero')=='nonzero','unsupported_period_svg')
    parse_path(paths[0].attrib['d'],native)
    require(source[0][0]==native.value[0][0]=='moveTo' and source[0][1][0][1]==0,'unsupported_period_baseline_point')
    offset=Decimal(str(native.value[0][1][0][1]))
    encoded=[(op,tuple(tuple(Decimal(format(v+(offset if i==1 else 0),'.6g')) for i,v in enumerate(p)) for p in points)) for op,points in source]
    require(canonical_directed_contours(encoded)==canonical_directed_contours(native.value),'period_baseline_contour_mismatch')
    extrema=lambda commands:tuple(min(Decimal(str(p[i])) for _,points in commands for p in points) for i in (0,1))
    require(extrema(encoded)==extrema(native.value),'period_baseline_position_mismatch')
    # The already verified Chinese calibration is read, never copied into the canvas.
    old_metadata=ROOT/'adapters/figma/metadata';current=load_json(old_metadata/'native-current-text-outline.json')
    require(current['fileReference']==file_reference,'chinese_calibration_file_mismatch')
    observation=next(row for row in compare_font_files(current,load_json(old_metadata/'font-file-identity.json'))['observations'] if row['textReference']=='18:3')
    require(observation['contourComparison']['nonzeroWinding']['status']=='PASS','unverified_chinese_calibration')
    chinese_offset=observation['nativeSvg']['pathBoundsSvgCoordinates']['y']-observation['source']['unshapedInkBoundsBaselineCoordinates']['y']
    plan=prepare_source(directory)
    return {**plan,'fileReference':file_reference,'fontBaselineOffsets':{'Arial':float(offset),'PingFang SC':chinese_offset},'fontCalibrationCaptureHashes':{'Arial':file_hash(metadata/'arial-glyph-readback-1.json'),'PingFang SC':file_hash(old_metadata/'native-current-text-outline.json')},'name':'candidate/'+plan['logicalId'],'fontEncodingAdmission':'NOT_APPROVED','fidelityGate':'NOT_RUN'}


def program(specs):
    return (ROOT/'adapters/figma/configurable_table_candidate.js').read_text(encoding='utf8')+'\nreturn await buildConfigurableFigmaTables(figma,'+json.dumps(specs,ensure_ascii=False,separators=(',',':'))+');\n'
