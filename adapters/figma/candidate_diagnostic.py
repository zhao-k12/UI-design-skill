"""Compare known native properties/raster with official evidence; never grants fidelity."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import math

from PIL import Image, ImageChops
from adapters.figma.native_capture import verify_saved_capture
from validators.component_ir import verify_artifacts
from validators.ui_ir import ROOT, load_json


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def locate_raster_differences(left, right, reference):
    """Locate exact differences; observed text boxes are regions, not glyph masks."""
    if left.size != right.size:
        raise ValueError('raster_location_size_mismatch')
    regions=[];unresolved=[]
    for node in reference['nodes']:
        if not node['visible']:
            continue
        for index, run in enumerate(node.get('textRuns', [])):
            box=run.get('bounds')
            if box is None:
                unresolved.append({'path':node['path'],'textRunIndex':index,'reason':'missing_observed_text_bounds'})
                continue
            if not isinstance(box,dict) or any(isinstance(box.get(key),bool) or not isinstance(box.get(key),(int,float)) or not math.isfinite(box[key]) for key in ('x','y','width','height')) or box['width']<0 or box['height']<0:
                raise ValueError('invalid_observed_text_region')
            regions.append({'path':node['path'],'textRunIndex':index,'bounds':box,'changedPixels':0})
    left=left.convert('RGBA');right=right.convert('RGBA')
    changed=[];inside=0;maximum=0;small=0
    for y in range(left.height):
        for x in range(left.width):
            a=left.getpixel((x,y));b=right.getpixel((x,y))
            delta=max(abs(c-d) for c,d in zip(a,b))
            if not delta:
                continue
            changed.append((x,y));maximum=max(maximum,delta);small+=delta<=16
            matched=False
            for region in regions:
                box=region['bounds']
                if box['x']<=x+.5<box['x']+box['width'] and box['y']<=y+.5<box['y']+box['height']:
                    region['changedPixels']+=1;matched=True
            inside+=matched
    box=([min(x for x,y in changed),min(y for x,y in changed),max(x for x,y in changed)+1,max(y for x,y in changed)+1] if changed else None)
    return {'changedPixels':len(changed),'changedPixelBounds':box,'maximumChannelDelta':maximum,
        'pixelsWithMaximumDeltaAtMost16':small,'insideObservedTextRunUnion':inside,
        'outsideObservedTextRunUnion':len(changed)-inside,'observedTextRegions':regions,'unresolvedTextRegions':unresolved,
        'classification':'Pixel-center containment in observed reference text boxes only. Outside does not imply nontext; missing placeholder/pseudo glyph boxes remain unknown.',
        'cause':'UNDETERMINED','admissionEligible':False}


def compare_candidate(reference, font_evidence, capture_directory, reference_png, *, file_reference, bindings=None, scope='production', supplemental_regions=None):
    report={'scope':'figma_candidate_diagnostic','status':'REVIEW','logicalId':reference['logicalComponentId'],
        'componentType':reference['componentType'],'evidenceScope':scope,'admissionEligible':False,'fidelityGate':'NOT_RUN',
        'checks':[],'issues':[],'unverified':['Per-glyph bounds and complete CSS-normalized visible-node observations.']}
    def check(field, expected, actual, *, equal=None):
        if actual is None or (isinstance(actual,dict) and actual.get('nativeMixed')):
            status='REVIEW'
        else:
            status='PASS' if (equal if equal is not None else expected==actual) else 'FAIL'
        report['checks'].append({'field':field,'status':status,'expected':expected,'actual':actual})
    def issue(code, detail):
        report['issues'].append({'code':code,'detail':detail})
    if capture_directory is None or not (Path(capture_directory)/'capture_manifest.json').exists():
        issue('missing_native_candidate','Independent native capture is required')
        return report
    try:
        directory=Path(capture_directory)
        integrity=verify_saved_capture(directory)
        if integrity['status']!='PASS':
            raise ValueError('invalid_native_capture_artifacts: '+str(integrity['issues']))
        manifest=load_json(directory/'capture_manifest.json')
        if scope not in ('production','test-fixture') or manifest['evidenceScope']!=scope or manifest['logicalId']!=reference['logicalComponentId'] or manifest['fileReference']!=file_reference:
            raise ValueError('native_candidate_identity_mismatch')
        evidence=load_json(directory/'native-evidence.json')
        native=evidence['nodes'];root=native[0]
        kind=reference['componentType']
        if kind not in ('Button','Input','Select'):
            raise ValueError('unsupported_component_diagnostic')
        expected_count={'Button':2,'Input':3,'Select':6}[kind]
        if len(native)!=expected_count and not (kind=='Button' and len(native)==3):
            raise ValueError('native_candidate_inventory_mismatch')
        source={node['path']:node for node in reference['nodes'] if node['visible']}
        if reference['environment']['deviceScaleFactor']!=1:
            raise ValueError('unsupported_reference_raster_scale')
        def role(name, node_type):
            matches=[node for node in native if node.get('name')==name and node['type']==node_type]
            if len(matches)!=1: raise ValueError('native_role_unresolved: '+name)
            return matches[0]
        def bounds(node):
            absolute=node['absoluteBounds'];origin=root['absoluteBounds']
            if absolute is None: return None
            return {'x':absolute['x']-origin['x'],'y':absolute['y']-origin['y'],
                'width':absolute['width'],'height':absolute['height']}
        def css_px(value):
            if not isinstance(value,str) or not re.fullmatch(r'[0-9]+(?:\.[0-9]+)?px',value):
                raise ValueError('unsupported_diagnostic_css_length')
            return float(value[:-2])
        def paint(field, css, paints):
            match=re.fullmatch(r'rgb\(([0-9]+), ([0-9]+), ([0-9]+)\)',css)
            if not match: raise ValueError('unsupported_diagnostic_css_paint')
            rgb=dict(zip(('r','g','b'),(int(value)/255 for value in match.groups())))
            valid=isinstance(paints,list) and len(paints)==1 and isinstance(paints[0],dict) and isinstance(paints[0].get('color'),dict) and paints[0].get('type')=='SOLID' and paints[0].get('opacity',1)==1 and paints[0].get('visible',True) is True
            if valid:
                for key,value in rgb.items():
                    # Exact floating-point storage representations, not a color tolerance.
                    allowed=(value,struct.unpack('f',struct.pack('f',value))[0])
                    if paints[0].get('color',{}).get(key) not in allowed: valid=False
            check(field,{'cssRgb':css,'opacity':1},paints,equal=valid)
        def surface(node, source_node, prefix):
            check(prefix+'.bounds',source_node['bounds'],bounds(node))
            style=source_node['computedStyle'];props=node['properties']
            paint(prefix+'.fill',style['background-color'],props.get('fills'))
            paint(prefix+'.stroke',style['border-top-color'],props.get('strokes'))
            check(prefix+'.strokeWeight',css_px(style['border-top-width']),props.get('strokeWeight'))
            check(prefix+'.strokeAlign','INSIDE',props.get('strokeAlign'))
            check(prefix+'.radius',css_px(style['border-top-left-radius']),props.get('cornerRadius'))
            for side in ('top','right','bottom','left'):
                check(prefix+'.padding.'+side,css_px(style['padding-'+side]),props.get('padding'+side.title()))
        def text(node, style, expected_text, path, observation_surface, prefix):
            props=node['properties']
            check(prefix+'.characters',expected_text,props.get('characters'))
            check(prefix+'.fontSize',css_px(style['font-size']),props.get('fontSize'))
            check(prefix+'.fontWeight',int(style['font-weight']),props.get('fontWeight'))
            paint(prefix+'.color',style['color'],props.get('fills'))
            fonts={font['familyName'] for item in font_evidence['observations']
                if item['logicalId']==reference['logicalComponentId'] and item['path']==path and item['surface']==observation_surface
                for font in item['fonts'] if font['glyphCount']>0}
            if len(fonts)!=1: raise ValueError('source_font_role_unresolved')
            family=next(iter(fonts));font_name=props.get('fontName')
            check(prefix+'.fontFamily',family,font_name.get('family') if isinstance(font_name,dict) else None)
            if bindings and family in bindings:
                check(prefix+'.fontBinding',bindings[family],font_name)
            else:
                report['unverified'].append(prefix+': exact approved native font style binding is absent.')
            if style['line-height']=='normal':
                report['unverified'].append(prefix+': CSS normal line-height requires actual font metrics; native AUTO does not establish equivalence.')
            else:
                check(prefix+'.lineHeight',{'unit':'PIXELS','value':css_px(style['line-height'])},props.get('lineHeight'))
        check('root.width',reference['rootBounds']['width'],root['localBounds']['width'])
        check('root.height',reference['rootBounds']['height'],root['localBounds']['height'])
        if kind=='Button':
            labels=[node for node in native if node['type']=='TEXT']
            if len(labels)!=1: raise ValueError('native_button_label_unresolved')
            surface(root,source['0'],'button')
            if len(native)==3:
                span=role('source/0.0','FRAME')
                check('button.sourceSpanParent',root['reference'],span['parentReference'])
                check('button.labelParent',span['reference'],labels[0]['parentReference'])
                check('button.labelLayoutBounds',source['0.0']['bounds'],bounds(span))
                check('button.sourceSpanFill',[],span['properties'].get('fills'))
                check('button.sourceSpanStroke',[],span['properties'].get('strokes'))
                check('button.sourceSpanClips',False,span['properties'].get('clipsContent'))
                check('button.labelOffsetX',0,labels[0]['localBounds']['x'])
                report['unverified'].append('Button glyph baseline alignment is a separate measured diagnostic, not inferred from its source span bounds.')
            else:
                check('button.labelLayoutBounds',source['0.0']['bounds'],bounds(labels[0]))
            text(labels[0],source['0.0']['computedStyle'],reference['content']['text'],'0.0','element','label')
        else:
            check('root.transparentFill',[],root['properties'].get('fills'))
            check('root.noStroke',[],root['properties'].get('strokes'))
            field_path='0.1' if kind=='Input' else '0.0'
            field=role('source/'+field_path,'FRAME')
            check('field.parent',root['reference'],field['parentReference'])
            surface(field,source[field_path],'field')
            if kind=='Input':
                label=role('source/placeholder','TEXT')
                check('placeholder.parent',field['reference'],label['parentReference'])
                text(label,source['0.1']['pseudoElements']['::placeholder'],
                    reference['props']['placeholder'],'0.1','element','placeholder')
            else:
                label=role('source/selected-value-text','TEXT')
                content=role('source/0.0.1','FRAME');slot=role('source/selected-value','FRAME')
                check('content.parent',field['reference'],content['parentReference'])
                check('selectedSlot.parent',content['reference'],slot['parentReference'])
                check('selected.parent',slot['reference'],label['parentReference'])
                text(label,source['0.0.1.0']['computedStyle'],source['0.0.1.0']['textRuns'][0]['text'],'0.0.1.0','element','selected')
                for name,path in [('source/0.0.1','0.0.1'),('source/selected-value','0.0.1.0')]:
                    check(name+'.bounds',source[path]['bounds'],bounds(role(name,'FRAME')))
                arrow=role('source/ionicons-arrow','TEXT');pseudo=source['0.0.1.1']['pseudoElements']['::before']
                check('arrow.parent',content['reference'],arrow['parentReference'])
                text(arrow,pseudo,json.loads(pseudo['content']),'0.0.1.1','pseudo:before','arrow')
                check('arrow.bounds',source['0.0.1.1']['bounds'],bounds(arrow))
                check('arrow.positioning','ABSOLUTE',arrow['properties'].get('layoutPositioning'))
        reference_png=Path(reference_png)
        if reference_png.resolve()==(directory/'comparison-white.png').resolve():
            raise ValueError('reference_reused_as_candidate')
        if file_hash(reference_png)!=reference['screenshot']['sha256']:
            raise ValueError('reference_screenshot_hash_mismatch')
        with Image.open(reference_png) as left,Image.open(directory/'comparison-white.png') as right:
            left,right=left.convert('RGBA'),right.convert('RGBA')
            check('raster.size',list(left.size),list(right.size))
            if left.size==right.size:
                pixels=ImageChops.difference(left,right).getdata()
                changed=sum(any(value) for value in pixels)
                check('raster.changedPixels',0,changed)
                report['raster']={'changedPixels':changed,'totalPixels':left.width*left.height,
                    'referenceSha256':reference['screenshot']['sha256'],'candidateSha256':manifest['comparisonPngSha256']}
                report['raster']['locations']=locate_raster_differences(left,right,reference)
                if supplemental_regions is not None:
                    region_reference={'nodes':[{'visible':True,'path':f"supplemental:{index}:{row['surface']}",'textRuns':[{'bounds':row['componentBounds']}]} for index,row in enumerate(supplemental_regions)]}
                    report['raster']['supplementalLocations']=locate_raster_differences(left,right,region_reference)
                    report['raster']['surfacePartition']=partition_surface_differences(left,right,reference,supplemental_regions)
        report['captureId']=manifest['captureId']
        report['status']='FAIL' if any(item['status']=='FAIL' for item in report['checks']) else 'REVIEW'
    except (OSError,ValueError,KeyError,TypeError) as exc:
        report['status']='FAIL';issue('invalid_candidate_comparison',str(exc))
    return report


def partition_surface_differences(left, right, reference, text_regions):
    """Disjoint observed text / source corner rectangle / unclassified counts."""
    if left.size!=right.size:raise ValueError('surface_partition_size_mismatch')
    kind=reference['componentType'];path={'Button':'0','Input':'0.1','Select':'0.0'}.get(kind)
    source=[node for node in reference['nodes'] if node.get('visible') and node['path']==path]
    if len(source)!=1:raise ValueError('surface_partition_source_missing')
    surface=source[0];box=surface['bounds'];style=surface['computedStyle'];radii=[]
    for corner in ('top-left','top-right','bottom-left','bottom-right'):
        value=style.get('border-'+corner+'-radius')
        if not isinstance(value,str) or not re.fullmatch(r'[0-9]+(?:\.[0-9]+)?px',value):raise ValueError('surface_partition_radius_unsupported')
        radii.append(float(value[:-2]))
    if len(set(radii))!=1 or radii[0]>min(box['width'],box['height'])/2:raise ValueError('surface_partition_radius_unsupported')
    radius=radii[0]
    corners=[{'x':x,'y':y,'width':radius,'height':radius} for x in (box['x'],box['x']+box['width']-radius) for y in (box['y'],box['y']+box['height']-radius)]
    regions=[row['componentBounds'] for row in text_regions]
    # Reuse numeric validation without deriving missing glyph rectangles.
    locate_raster_differences(left,right,{'nodes':[{'visible':True,'path':str(i),'textRuns':[{'bounds':region}]} for i,region in enumerate(regions)]})
    counts={name:{'changedPixels':0,'maximumChannelDelta':0} for name in ('observedText','sourceCornerRectangles','unclassified')}
    def contains(region,x,y):return region['x']<=x+.5<region['x']+region['width'] and region['y']<=y+.5<region['y']+region['height']
    left=left.convert('RGBA');right=right.convert('RGBA')
    for y in range(left.height):
        for x in range(left.width):
            delta=max(abs(a-b) for a,b in zip(left.getpixel((x,y)),right.getpixel((x,y))))
            if not delta:continue
            category='observedText' if any(contains(region,x,y) for region in regions) else 'sourceCornerRectangles' if any(contains(region,x,y) for region in corners) else 'unclassified'
            counts[category]['changedPixels']+=1;counts[category]['maximumChannelDelta']=max(counts[category]['maximumChannelDelta'],delta)
    return {'sourcePath':path,'sourceRadiusPx':radius,'cornerRectangles':corners,'categories':counts,
        'membershipRule':'Pixel centers; text takes priority over corner rectangles. Rectangles are not glyph or curve masks.',
        'cause':'UNDETERMINED','admissionEligible':False}


def validate_text_box_evidence(bundle, evidence, reference_hash):
    if not isinstance(evidence,dict) or evidence.get('scope')!='official_runtime_text_box_diagnostic' or evidence.get('status')!='PASS' or evidence.get('referenceComponentIrSha256')!=reference_hash or evidence.get('admissionEligible') is not False:
        raise ValueError('invalid_supplemental_text_evidence')
    ids={item['logicalComponentId'] for item in bundle['components']}
    matched=evidence.get('referenceMatches',[])
    if len(matched)!=len(ids) or {row.get('logicalId') for row in matched}!=ids or any(row.get('screenshotMatches') is not True or row.get('environmentMatches') is not True for row in matched):
        raise ValueError('supplemental_text_reference_not_reproduced')
    for reference in bundle['components']:
        if reference['environment']!=evidence.get('environment'):
            raise ValueError('supplemental_text_environment_mismatch')
        for key,value in reference['provenance'].items():
            if key!='rendererSha256' and evidence.get('provenance',{}).get(key)!=value:
                raise ValueError('supplemental_text_provenance_mismatch')
    rows=evidence.get('observations')
    if not isinstance(rows,list):raise ValueError('supplemental_text_observations_missing')
    grouped={logical_id:[] for logical_id in ids}
    for row in rows:
        if not isinstance(row,dict) or row.get('logicalId') not in ids or row.get('surface') not in ('snapshot-layout','user-agent-shadow') or not isinstance(row.get('text'),str) or not row['text']:
            raise ValueError('invalid_supplemental_text_observation')
        box=row.get('componentBounds')
        if not isinstance(box,dict) or any(isinstance(box.get(key),bool) or not isinstance(box.get(key),(float,int)) or not math.isfinite(box[key]) for key in ('x','y','width','height')) or box['width']<0 or box['height']<0:
            raise ValueError('invalid_supplemental_text_bounds')
        grouped[row['logicalId']].append(row)
    return grouped


def run(reference_directory, font_evidence, *, file_reference, candidate_directory=None, bindings=None, text_box_evidence=None):
    reference_directory=Path(reference_directory)
    issues=verify_artifacts(reference_directory)
    if issues: raise ValueError('invalid_official_runtime_reference: '+str(issues))
    bundle=load_json(reference_directory/'component_ir.json')
    if not isinstance(font_evidence,dict) or font_evidence.get('scope')!='official_runtime_font_diagnostic' or font_evidence.get('status')!='PASS' or font_evidence.get('referenceComponentIrSha256')!=file_hash(reference_directory/'component_ir.json'):
        raise ValueError('invalid_reference_font_evidence')
    if bindings is not None and not isinstance(bindings,dict):
        raise ValueError('invalid_diagnostic_font_bindings')
    matched=font_evidence.get('referenceMatches',[])
    expected_ids={item['logicalComponentId'] for item in bundle['components']}
    if not isinstance(matched,list) or any(not isinstance(item,dict) for item in matched) or len(matched)!=len(expected_ids) or {item.get('logicalId') for item in matched}!=expected_ids or any(item.get('screenshotMatches') is not True or item.get('environmentMatches') is not True for item in matched):
        raise ValueError('reference_font_reproduction_unverified')
    reports=[]
    supplemental=validate_text_box_evidence(bundle,text_box_evidence,file_hash(reference_directory/'component_ir.json')) if text_box_evidence is not None else None
    for reference in bundle['components']:
        if reference['environment']!=font_evidence.get('environment'):
            raise ValueError('reference_font_environment_mismatch')
        directory=Path(candidate_directory)/reference['logicalComponentId'] if candidate_directory else None
        if directory and not directory.resolve().is_relative_to(Path(candidate_directory).resolve()):
            raise ValueError('candidate_directory_escape')
        reports.append(compare_candidate(reference,font_evidence,directory,reference_directory/reference['screenshot']['path'],
            file_reference=file_reference,bindings=bindings,supplemental_regions=supplemental[reference['logicalComponentId']] if supplemental is not None else None))
    return {'scope':'figma_candidate_diagnostic_batch','status':'FAIL' if any(item['status']=='FAIL' for item in reports) else 'REVIEW',
        'admissionEligible':False,'fidelityGate':'NOT_RUN','components':reports}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference',type=Path,required=True)
    parser.add_argument('--font-evidence',type=Path,required=True)
    parser.add_argument('--candidates',type=Path)
    parser.add_argument('--bindings',type=Path)
    parser.add_argument('--text-box-evidence',type=Path)
    parser.add_argument('--file-reference',required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    output=args.output_dir.resolve()
    inputs=[args.reference.resolve(),args.font_evidence.resolve().parent]
    if args.candidates: inputs.append(args.candidates.resolve())
    if args.bindings: inputs.append(args.bindings.resolve().parent)
    if args.text_box_evidence: inputs.append(args.text_box_evidence.resolve().parent)
    if not output.is_relative_to((ROOT/'artifacts').resolve()) or any(output==path or output.is_relative_to(path) for path in inputs):
        parser.error('Output must be separate project artifacts')
    output.mkdir(parents=True,exist_ok=True)
    target=output/'native_comparison_report.json'
    target.write_text(json.dumps({'status':'RUNNING','admissionEligible':False})+'\n',encoding='utf-8')
    try:
        report=run(args.reference,load_json(args.font_evidence),file_reference=args.file_reference,
            candidate_directory=args.candidates,bindings=load_json(args.bindings) if args.bindings else None,
            text_box_evidence=load_json(args.text_box_evidence) if args.text_box_evidence else None)
    except (OSError,ValueError,KeyError,TypeError) as exc:
        report={'scope':'figma_candidate_diagnostic_batch','status':'FAIL','admissionEligible':False,
            'fidelityGate':'NOT_RUN','issues':[{'code':'invalid_comparison_inputs','detail':str(exc)}]}
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':report['status'],'fidelityGate':'NOT_RUN'},ensure_ascii=False))
    return 1


if __name__=='__main__':
    raise SystemExit(main())
