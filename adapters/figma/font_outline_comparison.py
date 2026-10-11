"""Read actual font glyph bounds and compare dimensions with captured SVG paths."""
import argparse
from decimal import Decimal
import hashlib
from io import BytesIO
import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path
import fontTools
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import DecomposingRecordingPen,RecordingPen
from fontTools.svgLib.path import parse_path
from adapters.figma.outline_geometry import inspect_capture
from validators.ui_ir import ROOT,load_json


def canonical_contours(commands):
    """Keep contour order and winding; remove only an explicit closing line."""
    contours=[];contour=None;start=None
    for operation,points in commands:
        if operation not in ('moveTo','lineTo','curveTo','closePath'):raise ValueError('unsupported_contour_operation')
        expected={'moveTo':1,'lineTo':1,'curveTo':3,'closePath':0}[operation]
        if len(points)!=expected:raise ValueError('unsupported_contour_point_count')
        if operation=='moveTo':
            if contour is not None:raise ValueError('open_contour')
            contour=[];start=points[0]
        elif contour is None:raise ValueError('contour_without_start')
        if operation=='closePath':
            if contour[-1][0]=='lineTo' and contour[-1][1][0]==start:contour.pop()
            contour.append((operation,()));contours.append(contour);contour=None
        else:contour.append((operation,points))
    if contour is not None or not contours:raise ValueError('open_or_empty_contours')
    origin=contours[0][0][1][0]
    normalized=[]
    for contour in contours:
        normalized.extend((operation,tuple((Decimal(str(x))-Decimal(str(origin[0])),Decimal(str(y))-Decimal(str(origin[1]))) for x,y in points)) for operation,points in contour)
    return normalized,(Decimal(str(origin[0])),Decimal(str(origin[1])))


def compare_contours(source_commands,native_commands):
    source,source_origin=canonical_contours(source_commands);native,native_origin=canonical_contours(native_commands)
    same_structure=len(source)==len(native) and all(a[0]==b[0] and len(a[1])==len(b[1]) for a,b in zip(source,native))
    differences=[]
    if same_structure:
        for a,b in zip(source,native):
            differences.extend(abs(c-d) for p,q in zip(a[1],b[1]) for c,d in zip(p,q))
    def digest(commands):return hashlib.sha256(json.dumps([(op,[[str(x),str(y)] for x,y in points]) for op,points in commands],separators=(',',':')).encode()).hexdigest()
    geometric=compare_unoriented_contours(source_commands,native_commands)
    return {'orderedContourStructureEqual':same_structure,'exactNormalizedCoordinatesEqual':source==native,
        'sourceCommandCount':len(source),'nativeCommandCount':len(native),
        'maximumCoordinateDeltaPx':float(max(differences,default=Decimal(0))) if same_structure else None,
        'sourceNormalizedSha256':digest(source),'nativeNormalizedSha256':digest(native),
        'alignmentTranslationSvgCoordinates':{'x':float(native_origin[0]-source_origin[0]),'y':float(native_origin[1]-source_origin[1])},
        'alignmentAppliedToCanvas':False,'admissionEligible':False,'unorientedGeometry':geometric}


def canonical_unoriented_contours(commands):
    normalized,_=canonical_contours(commands)
    points=[point for operation,items in normalized for point in items]
    origin=(min(p[0] for p in points),min(p[1] for p in points))
    contours=[];segments=[];start=None;current=None
    for operation,items in normalized:
        items=tuple((x-origin[0],y-origin[1]) for x,y in items)
        if operation=='moveTo':start=current=items[0];segments=[]
        elif operation=='closePath':
            if current!=start:segments.append(('L',(current,start)))
            if not segments:raise ValueError('degenerate_contour')
            reverse=[(op,tuple(reversed(pts))) for op,pts in reversed(segments)]
            contours.append(min(minimum_rotation(segments),minimum_rotation(reverse)))
        else:
            end=items[-1]
            if operation=='lineTo':
                if current!=end:segments.append(('L',(current,end)))
            else:segments.append(('C',(current,*items)))
            current=end
    return sorted(contours)


def minimum_rotation(sequence):
    """Lexicographically minimal cyclic start in linear time (Booth)."""
    size=len(sequence)
    if not size:raise ValueError('empty_contour_segments')
    doubled=sequence+sequence;i=0;j=1;k=0
    while i<size and j<size and k<size:
        left,right=doubled[i+k],doubled[j+k]
        if left==right:k+=1;continue
        if left>right:
            i=i+k+1
            if i<=j:i=j+1
        else:
            j=j+k+1
            if j<=i:j=i+1
        k=0
    start=min(i,j)
    return tuple(doubled[start:start+size])


def canonical_directed_contours(commands, *, reverse_all=False):
    """Normalize translation/order/start without discarding contour winding."""
    normalized,_=canonical_contours(commands)
    points=[point for _,items in normalized for point in items]
    origin=(min(point[0] for point in points),min(point[1] for point in points))
    contours=[];segments=[];start=current=None
    for operation,items in normalized:
        items=tuple((x-origin[0],y-origin[1]) for x,y in items)
        if operation=='moveTo':start=current=items[0];segments=[]
        elif operation=='closePath':
            if current!=start:segments.append(('L',(current,start)))
            if not segments:raise ValueError('degenerate_contour')
            if reverse_all:segments=[(op,tuple(reversed(pts))) for op,pts in reversed(segments)]
            contours.append(minimum_rotation(segments))
        else:
            end=items[-1]
            if operation=='lineTo':
                if current!=end:segments.append(('L',(current,end)))
            else:segments.append(('C',(current,*items)))
            current=end
    return sorted(contours)


def compare_nonzero_winding(source_commands,native_commands,*,native_fill_rule='nonzero',native_path_count=1):
    source=canonical_directed_contours(source_commands)
    native=canonical_directed_contours(native_commands)
    same=source==native
    reversed_all=source==canonical_directed_contours(native_commands,reverse_all=True)
    supported=native_fill_rule=='nonzero' and native_path_count==1
    equivalent=supported and (same or reversed_all)
    return {'scope':'nonzero_path_winding_diagnostic','status':'PASS' if equivalent else 'REVIEW',
        'contourCount':len(source),'nativeFillRule':native_fill_rule,'nativePathCount':native_path_count,
        'directionRelationship':'SAME' if same else 'ALL_CONTOURS_REVERSED' if reversed_all else 'UNRESOLVED',
        'nonzeroPathFilledRegionEquivalent':equivalent,
        'proof':'Exact directed segments after common translation, contour ordering and cyclic starts; uniform reversal changes winding sign everywhere but preserves its zero set.',
        'admissionEligible':False,
        'limitations':['This compares paths under nonzero fill, not font renderer behavior, hinting or pixels.',
            'Individual contour reversal, multiple native fill paths, evenodd or inexact coordinates are not certified.']}


def compare_six_digit_serialization(source_commands,native_commands,*,native_fill_rule='nonzero',native_path_count=1):
    """Verify a fixed six-significant-digit serializer, rather than a tolerance.

    Restricted to line contours. Translation is derived from extrema; it must
    itself be exact and is checked separately by the measured baseline proof.
    Every resulting point must match, including winding and contour topology.
    """
    supported=native_fill_rule=='nonzero' and native_path_count==1
    if any(op not in ('moveTo','lineTo','closePath') for op,_ in source_commands+native_commands):supported=False
    source_points=[p for _,points in source_commands for p in points]
    native_points=[p for _,points in native_commands for p in points]
    if not source_points or not native_points:raise ValueError('empty_serialization_geometry')
    translation=tuple(min(Decimal(str(p[i])) for p in native_points)-min(Decimal(str(p[i])) for p in source_points) for i in (0,1))
    encoded=[(op,tuple(tuple(Decimal(format(Decimal(str(value))+translation[i],'.6g')) for i,value in enumerate(point)) for point in points)) for op,points in source_commands]
    same=canonical_directed_contours(encoded)==canonical_directed_contours(native_commands)
    reversed_all=canonical_directed_contours(encoded)==canonical_directed_contours(native_commands,reverse_all=True)
    # Canonicalization removes common translation; require the actual extrema too.
    encoded_min=tuple(min(p[i] for _,points in encoded for p in points) for i in (0,1))
    native_min=tuple(min(Decimal(str(p[i])) for p in native_points) for i in (0,1))
    valid=supported and (same or reversed_all) and encoded_min==native_min
    return {'status':'PASS' if valid else 'REVIEW','serializer':'six-significant-decimal-digits',
        'translation':dict(zip(('x','y'),map(str,translation))),
        'exactSerializedDirectedGeometryEqual':valid,'nativeFillRule':native_fill_rule,
        'nativePathCount':native_path_count,'admissionEligible':False}


def compare_unoriented_contours(source,native):
    a=canonical_unoriented_contours(source);b=canonical_unoriented_contours(native)
    same=len(a)==len(b) and all(len(x)==len(y) and all(p[0]==q[0] and len(p[1])==len(q[1]) for p,q in zip(x,y)) for x,y in zip(a,b))
    deltas=[abs(c-d) for x,y in zip(a,b) for p,q in zip(x,y) for point,other in zip(p[1],q[1]) for c,d in zip(point,other)] if same else []
    return {'contourCountSource':len(a),'contourCountNative':len(b),'structureEqual':same,'exactCoordinatesEqual':a==b,
        'maximumCoordinateDeltaPx':float(max(deltas,default=Decimal(0))) if same else None,
        'comparison':'Translation, contour order, cyclic starts and traversal direction are normalized; fill winding semantics remain unverified.',
        'admissionEligible':False}


def measure_glyphs(path,expected_hash,text,font_size,*,include_commands=False):
    if not isinstance(text,str) or not text or len(text)>128 or any(not (0x4e00<=ord(char)<=0x9fff or char=='\uf116') for char in text):raise ValueError('unsupported_unshaped_text')
    if isinstance(font_size,bool) or not isinstance(font_size,(int,float)) or not math.isfinite(font_size) or not 0<font_size<=512:raise ValueError('invalid_font_size')
    path=Path(path)
    if path.stat().st_size>64*1024*1024:raise ValueError('font_file_too_large')
    data=path.read_bytes();digest=hashlib.sha256(data).hexdigest()
    if digest!=expected_hash:raise ValueError('source_font_file_hash_mismatch')
    with TTFont(BytesIO(data),lazy=False,recalcBBoxes=False,recalcTimestamp=False) as font:
        if 'fvar' in font:raise ValueError('variable_glyph_instance_unresolved')
        upem=font['head'].unitsPerEm
        if not isinstance(upem,int) or upem<=0:raise ValueError('invalid_font_units')
        cmap=font.getBestCmap();glyphs=font.getGlyphSet();cursor=0;boxes=[];rows=[];commands=[]
        for char in text:
            name=cmap.get(ord(char)) if cmap else None
            if name is None:raise ValueError('source_font_glyph_missing')
            glyph=glyphs[name];pen=BoundsPen(glyphs);glyph.draw(pen)
            if pen.bounds is None:raise ValueError('source_font_glyph_bounds_missing')
            x0,y0,x1,y1=pen.bounds
            boxes.append((x0+cursor,y0,x1+cursor,y1))
            rows.append({'codepoint':f'U+{ord(char):04X}','glyphName':name,'boundsFontUnits':list(pen.bounds),'advanceFontUnits':glyph.width})
            if include_commands:
                recording=DecomposingRecordingPen(glyphs);glyph.draw(recording)
                factor=Decimal(str(font_size))/Decimal(upem)
                commands.extend((operation,tuple(((Decimal(str(x))+Decimal(str(cursor)))*factor,-Decimal(str(y))*factor) for x,y in points)) for operation,points in recording.value)
            cursor+=glyph.width
        x0=min(b[0] for b in boxes);y0=min(b[1] for b in boxes);x1=max(b[2] for b in boxes);y1=max(b[3] for b in boxes)
        def scale(value):return float(Decimal(str(value))*Decimal(str(font_size))/Decimal(upem))
        result={'fontFileSha256':digest,'unitsPerEm':upem,'glyphs':rows,'advancePx':scale(cursor),
            'unshapedInkBoundsBaselineCoordinates':{'x':scale(x0),'y':scale(-y1),'width':scale(x1-x0),'height':scale(y1-y0)},
            'shaping':'NONE: cmap glyphs with hmtx advances; no GSUB/GPOS, kerning, hinting or rasterization.'}
        if include_commands:result['_commands']=commands
        return result


def compare_font_files(capture,identity):
    geometry=inspect_capture(capture)
    if identity.get('scope')!='source_font_file_metadata' or identity.get('status')!='PASS':raise ValueError('invalid_font_file_identity')
    families={}
    for row in identity['requirements']:
        if row.get('status')!='METADATA_IDENTIFIED' or len(row['matches'])!=1:raise ValueError('ambiguous_font_file_identity')
        families[row['familyName']]=row
    dimensions={row['textReference']:row for row in geometry['observations']};output=[]
    for row in capture['observations']:
        family=row['fontName']['family'];requirement=families.get(family)
        if requirement is None or row['fontName']!=requirement['fontNameForLoadProbe']:raise ValueError('outline_source_font_binding_mismatch')
        match=requirement['matches'][0]
        measured=measure_glyphs(match['path'],match['fileSha256'],row['characters'],row['fontSize'],include_commands=True)
        native_pen=RecordingPen();paths=list(ET.fromstring(row['svg']))
        for path in paths:parse_path(path.attrib['d'],native_pen)
        commands=measured.pop('_commands')
        contour_comparison=compare_contours(commands,native_pen.value)
        contour_comparison['nonzeroWinding']=compare_nonzero_winding(commands,native_pen.value,
            native_fill_rule=paths[0].get('fill-rule','nonzero') if len(paths)==1 else 'UNRESOLVED',native_path_count=len(paths))
        contour_comparison['sixDigitSerialization']=compare_six_digit_serialization(commands,native_pen.value,
            native_fill_rule=paths[0].get('fill-rule','nonzero') if len(paths)==1 else 'UNRESOLVED',native_path_count=len(paths))
        source=measured['unshapedInkBoundsBaselineCoordinates'];native=dimensions[row['textReference']]['pathBoundsSvgCoordinates']
        output.append({'textReference':row['textReference'],'characters':row['characters'],'sourceFileRole':match['role'],
            'source':measured,'nativeSvg':dimensions[row['textReference']],
            'dimensionDeltaPx':{key:native[key]-source[key] for key in ('width','height')},
            'dimensionEqual':all(native[key]==source[key] for key in ('width','height')),'contourComparison':contour_comparison})
    return {'scope':'figma_font_file_outline_dimension_diagnostic','status':'REVIEW','fontToolsVersion':fontTools.__version__,
        'fileReference':capture['fileReference'],'observations':output,'admissionEligible':False,'fidelityGate':'NOT_RUN',
        'limitations':['Dimension equality is not full contour equality, shaping equivalence or DOM baseline proof.',
            'Local name metadata does not prove browser-loaded file identity; official TTF sibling does not prove served WOFF2 equivalence.',
            'No positions, fonts, reference captures or admission tolerances are changed.']}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--capture',type=Path,required=True);parser.add_argument('--font-identity',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();output=args.output.resolve()
    if not output.is_relative_to(ROOT/'artifacts') or output in (args.capture.resolve(),args.font_identity.resolve()):parser.error('Output must be independent artifacts')
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text('{"status":"RUNNING","admissionEligible":false}\n',encoding='utf-8')
    try:report=compare_font_files(load_json(args.capture),load_json(args.font_identity))
    except Exception as exc:report={'scope':'figma_font_file_outline_dimension_diagnostic','status':'FAIL','admissionEligible':False,'issues':[{'code':type(exc).__name__,'detail':str(exc)}]}
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':report['status'],'observations':[{'text':r['characters'],'delta':r['dimensionDeltaPx']} for r in report.get('observations',[])]},ensure_ascii=False))
    return 1 if report['status']=='FAIL' else 0


if __name__=='__main__':raise SystemExit(main())
