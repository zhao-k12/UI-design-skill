"""Exact, bounded TASK-019 Arial encoding checks; not a full fidelity gate."""
from decimal import Decimal
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
from fontTools.pens.recordingPen import RecordingPen
from fontTools.svgLib.path import parse_path
from adapters.figma.configurable_font_calibration import ExactCubicPen
from adapters.figma.font_outline_comparison import canonical_directed_contours
from adapters.figma.outline_geometry import inspect_capture
from validators.ui_ir import ROOT

FONT_SHA = 'c9b76220a5be42ead4733611e417cd65c5fd8aeaa33eb56576ac378a37d130a1'
DLL_SHA = '090038852d6eb0dc75569f31fb92d6c98e829ca2639c9b6e8d8808032f9a7003'
WRAPPER_SHA = 'aa2baf011511f89f04e8a135e6d398cd46bf86a3892add185177fccb88e66470'
CHARACTERS = '.01234@acehilmnopqxz'
CELL_TEXTS = {'zhao@example.com', 'qian@example.com', '001', '002', '003', '004'}
REFERENCES = {**{f'68:{i+2}':char for i,char in enumerate(CHARACTERS)},
    '69:9':'zhao@example.com','69:15':'qian@example.com',
    '69:21':'001','69:31':'002','69:41':'003','69:51':'004'}


def runtime(directory):
    directory = Path(directory).resolve()
    if hashlib.sha256((directory/'freetype/libfreetype.dll').read_bytes()).hexdigest() != DLL_SHA:
        raise ValueError('freetype_binary_hash_mismatch')
    if hashlib.sha256((directory/'freetype/__init__.py').read_bytes()).hexdigest() != WRAPPER_SHA:
        raise ValueError('freetype_wrapper_hash_mismatch')
    sys.path.insert(0, str(directory))
    import freetype
    if Path(freetype.__file__).resolve().parent != directory/'freetype' or freetype.version() != (2,13,2):
        raise ValueError('freetype_runtime_mismatch')
    if Path(freetype.raw._lib._name).resolve() != directory/'freetype/libfreetype.dll':
        raise ValueError('freetype_loaded_binary_mismatch')
    return freetype


def encoded(text, font_path, ft):
    if text not in CELL_TEXTS and (len(text)!=1 or text not in CHARACTERS):
        raise ValueError('text_outside_approved_scope')
    if hashlib.sha256(Path(font_path).read_bytes()).hexdigest()!=FONT_SHA:
        raise ValueError('source_font_file_hash_mismatch')
    face=ft.Face(str(font_path));face.set_pixel_sizes(0,1024)
    cursor=Fraction(0);commands=[]
    for char in text:
        face.load_char(char,ft.FT_LOAD_DEFAULT)
        advance=Fraction(face.glyph.advance.x,64)*face.units_per_EM/1024
        face.load_char(char,ft.FT_LOAD_NO_SCALE|ft.FT_LOAD_NO_HINTING)
        pen=ExactCubicPen(None,cursor,Fraction(14,face.units_per_EM));opened=False
        def point(v): return (v.x,v.y)
        def move(v,context):
            nonlocal opened
            if opened: pen.closePath()
            pen.moveTo(point(v));opened=True
        face.glyph.outline.decompose(move_to=move,line_to=lambda v,c:pen.lineTo(point(v)),
            conic_to=lambda a,b,c:pen.qCurveTo(point(a),point(b)),
            cubic_to=lambda a,b,c,d:pen.curveTo(point(a),point(b),point(c)))
        if opened: pen.closePath()
        commands.extend(pen.commands);cursor+=advance
    # Fixed baseline from independent period calibration, never fitted to this SVG.
    values=[(op,tuple(tuple(Decimal(format(Decimal(v.numerator)/Decimal(v.denominator)+(15 if i==1 else 0),'.6g'))
        for i,v in enumerate(p)) for p in points)) for op,points in commands]
    return values, Fraction(cursor)*14/face.units_per_EM


def verify(observation,font_path,ft):
    if observation['fontName']!={'family':'Arial','style':'Regular'} or observation['fontWeight']!=400 or observation['fontSize']!=14 or observation['lineHeight']!={'unit':'PIXELS','value':21}:
        raise ValueError('unsupported_arial_typography')
    source,advance=encoded(observation['characters'],font_path,ft)
    paths=list(ET.fromstring(observation['svg']))
    if len(paths)!=1 or paths[0].get('fill')!='#515A6E' or paths[0].get('fill-rule','nonzero')!='nonzero':
        raise ValueError('unexpected_arial_path_paint')
    native=RecordingPen();parse_path(paths[0].attrib['d'],native)
    def minima(commands):
        return tuple(min(Decimal(str(p[i])) for _,points in commands for p in points) for i in (0,1))
    equal=canonical_directed_contours(source)==canonical_directed_contours(native.value) and minima(source)==minima(native.value)
    bounds=observation['absoluteBounds']
    intrinsic=bounds['width']==math.ceil(advance) and bounds['height']==21
    return {'textReference':observation['textReference'],'characters':observation['characters'],
        'exactDirectedEncodingEqual':equal,'intrinsicDimensionsEqual':intrinsic,
        'encodedAdvancePx':str(advance),'fixedBaselinePx':15,
        'svgSha256':hashlib.sha256(observation['svg'].encode()).hexdigest(),
        'status':'PASS' if equal and intrinsic else 'FAIL'}


def inspect(captures,font_path,ft):
    rows=[];seen=set()
    for capture in captures:
        inspect_capture(capture)
        if capture['fileReference']!='0vGWSRoLxBiVPXiZ8xJAX9' or capture['pageReference'] not in ('64:2','69:2'):
            raise ValueError('capture_outside_approved_context')
        for observation in capture['observations']:
            if observation['fontName']['family']!='Arial': continue
            reference=observation['textReference']
            if REFERENCES.get(reference)!=observation['characters'] or capture['pageReference']!=('64:2' if reference.startswith('68:') else '69:2'):
                raise ValueError('capture_outside_approved_references')
            if observation['textReference'] in seen: raise ValueError('duplicate_arial_observation')
            seen.add(observation['textReference']);rows.append(verify(observation,font_path,ft))
    singles={r['characters'] for r in rows if len(r['characters'])==1}
    cells={r['characters'] for r in rows if len(r['characters'])>1}
    complete=len(rows)==26 and singles==set(CHARACTERS) and cells==CELL_TEXTS
    return {'scope':'task019_exact_arial_encoding','status':'PASS' if complete and all(r['status']=='PASS' for r in rows) else 'FAIL',
        'fontSha256':FONT_SHA,'freetypeVersion':'2.13.2','freetypeBinarySha256':DLL_SHA,'freetypeWrapperSha256':WRAPPER_SHA,
        'programSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'observations':rows,'admissionEligible':False,'fidelityGate':'NOT_RUN'}


if __name__=='__main__':
    metadata=ROOT/'adapters/figma/metadata/configurable-table-native'
    capture_paths=[metadata/f'arial-glyph-readback-{i}.json' for i in range(1,5)]
    captures=[json.loads(path.read_text(encoding='utf-8')) for path in capture_paths]
    for i in (0,1):
        path=metadata/f'table-text-outlines-{i}.json';capture_paths.append(path)
        captures.extend(json.loads(path.read_text(encoding='utf-8')))
    report=inspect(captures,Path('C:/Windows/Fonts/arial.ttf'),runtime(ROOT/'artifacts/task-019/freetype-probe-deps'))
    report['captureFileHashes']={path.name:hashlib.sha256(path.read_bytes()).hexdigest() for path in capture_paths}
    report['approvedDecisionSha256']=hashlib.sha256((ROOT/'.dev/TASK-019_ARIAL_ENCODING_DECISION.md').read_bytes()).hexdigest()
    output=ROOT/'artifacts/task-019/arial-complete-encoding.json'
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':report['status'],'observations':len(report['observations']),'failed':[r['textReference'] for r in report['observations'] if r['status']!='PASS']}))
    raise SystemExit(0 if report['status']=='PASS' else 1)
