"""Bounded inspection of native polygon SVG exports; no font or fidelity inference."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from validators.ui_ir import ROOT, load_json

NUMBER=r'[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?'
TOKEN=re.compile(r'[A-Za-z]|'+NUMBER)


def path_bounds(data):
    if not isinstance(data,str) or len(data)>1000000:raise ValueError('outline_path_size')
    tokens=TOKEN.findall(data)
    if len(tokens)>50000 or TOKEN.sub('',data).strip(' ,\t\r\n'):raise ValueError('invalid_outline_path_tokens')
    points=[];index=0;command=None;current=None;start=None
    while index<len(tokens):
        if tokens[index].isalpha():command=tokens[index];index+=1
        if command not in ('M','L','H','V','C','Z'):raise ValueError('unsupported_outline_path_command')
        if command=='Z':
            if start is None:raise ValueError('outline_close_without_start')
            current=start;points.append(current);command=None;continue
        count=6 if command=='C' else 2 if command in ('M','L') else 1
        if index+count>len(tokens):raise ValueError('incomplete_outline_path')
        try:values=[float(value) for value in tokens[index:index+count]]
        except ValueError as exc:raise ValueError('invalid_outline_coordinate') from exc
        if not all(math.isfinite(value) and abs(value)<=10000000 for value in values):raise ValueError('invalid_outline_coordinate')
        index+=count
        if command!='M' and current is None:raise ValueError('outline_draw_without_start')
        if command=='M':current=tuple(values);start=current;command='L'
        elif command=='L':current=tuple(values)
        elif command=='H':current=(values[0],current[1])
        elif command=='C':
            controls=[current,tuple(values[:2]),tuple(values[2:4]),tuple(values[4:])]
            times=set()
            for axis in (0,1):
                p0,p1,p2,p3=(point[axis] for point in controls)
                a=3*(-p0+3*p1-3*p2+p3);b=2*(3*p0-6*p1+3*p2);c=-3*p0+3*p1
                if a==0:
                    roots=[] if b==0 else [-c/b]
                else:
                    discriminant=b*b-4*a*c
                    roots=[] if discriminant<0 else [(-b+math.sqrt(discriminant))/(2*a),(-b-math.sqrt(discriminant))/(2*a)]
                times.update(t for t in roots if 0<t<1)
            for t in times:
                points.append(tuple((1-t)**3*controls[0][axis]+3*(1-t)**2*t*controls[1][axis]+3*(1-t)*t*t*controls[2][axis]+t**3*controls[3][axis] for axis in (0,1)))
            current=controls[3]
        else:current=(current[0],values[0])
        points.append(current)
    if not points:raise ValueError('empty_outline_path')
    x=[point[0] for point in points];y=[point[1] for point in points]
    return {'x':min(x),'y':min(y),'width':max(x)-min(x),'height':max(y)-min(y)}


def inspect_svg(svg):
    if not isinstance(svg,str) or len(svg.encode('utf-8'))>1000000 or re.search(r'<!|<\?',svg):raise ValueError('unsafe_or_large_outline_svg')
    root=ET.fromstring(svg);prefix='{http://www.w3.org/2000/svg}'
    if root.tag!=prefix+'svg' or set(root.attrib)-{'width','height','viewBox','fill'}:raise ValueError('unsupported_outline_svg_root')
    if root.get('fill') not in (None,'none'):raise ValueError('unsupported_outline_svg_background')
    boxes=[]
    for node in root:
        if node.tag!=prefix+'path' or list(node) or set(node.attrib)-{'d','fill','fill-rule'}:raise ValueError('unsupported_outline_svg_element')
        boxes.append(path_bounds(node.get('d')))
    if not boxes:raise ValueError('outline_svg_paths_missing')
    left=min(box['x'] for box in boxes);top=min(box['y'] for box in boxes)
    right=max(box['x']+box['width'] for box in boxes);bottom=max(box['y']+box['height'] for box in boxes)
    return {'svgSha256':hashlib.sha256(svg.encode('utf-8')).hexdigest(),'pathCount':len(boxes),
        'pathBoundsSvgCoordinates':{'x':left,'y':top,'width':right-left,'height':bottom-top},
        'viewBox':root.get('viewBox'),'exportWidth':root.get('width'),'exportHeight':root.get('height')}


def inspect_capture(capture):
    if capture.get('scope')!='figma_native_text_outline_diagnostic' or capture.get('status')!='PASS' or capture.get('createdNodeIds') or capture.get('mutatedNodeIds') or capture.get('admissionEligible') is not False:
        raise ValueError('invalid_native_outline_capture')
    rows=[];seen=set()
    for observation in capture['observations']:
        reference=observation['textReference']
        if reference in seen:raise ValueError('duplicate_outline_text')
        seen.add(reference)
        rows.append({'textReference':reference,'characters':observation['characters'],**inspect_svg(observation['svg'])})
    if not rows:raise ValueError('outline_observations_missing')
    return {'scope':'figma_native_outline_geometry','status':'PASS','fileReference':capture['fileReference'],
        'observations':rows,'admissionEligible':False,'fidelityGate':'NOT_RUN',
        'limitations':['Only absolute M/L/H/V/C/Z commands are supported; cubic extrema are solved analytically; other commands/transforms/strokes are not approximated.',
            'Bounds describe exported path coordinates, not original font curves or independent source glyph equality.',
            'SVG export precision and platform coordinate transforms remain unverified.']}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture',type=Path);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();output=args.output.resolve()
    if not output.is_relative_to(ROOT/'artifacts') or output==args.capture.resolve():parser.error('Output must be independent project artifacts')
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text('{"status":"RUNNING","admissionEligible":false}\n',encoding='utf-8')
    try:report=inspect_capture(load_json(args.capture))
    except (OSError,ValueError,KeyError,TypeError,ET.ParseError) as exc:report={'scope':'figma_native_outline_geometry','status':'FAIL','admissionEligible':False,'issues':[{'code':str(exc)}]}
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':report['status'],'observations':report.get('observations',[])},ensure_ascii=False))
    return 0 if report['status']=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
