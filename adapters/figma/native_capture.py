"""Validate and preserve native PNG/observations; this is not Fidelity Gate admission."""
import argparse
import hashlib
from io import BytesIO
import json
import math
from pathlib import Path
import struct

from PIL import Image
from validators.ui_ir import ROOT, load_json


def digest_bytes(value):
    return hashlib.sha256(value).hexdigest()


def package_capture(result, *, file_reference, component_reference, logical_id, scope='production'):
    if isinstance(result,dict) and result.get('scope') in ('figma_button_candidate','figma_form_candidate'):
        if result.get('status')!='PASS' or result.get('admissionEligible') is not False or result.get('fidelityGate')!='NOT_RUN' or result.get('issues')!=[]:
            raise ValueError('combined_candidate_not_successful')
        if result.get('nativeObservation',{}).get('componentReference')!=component_reference or component_reference not in result.get('createdNodeIds',[]):
            raise ValueError('combined_candidate_capture_reference_mismatch')
        result=result.get('nativeCapture')
    if scope not in ('production','test-fixture'):
        raise ValueError('invalid_capture_scope')
    expected={'scope':'figma_native_component_capture','status':'PASS','evidenceKind':'native-platform-export',
        'evidenceScope':scope,'fileReference':file_reference,'componentReference':component_reference,'logicalId':logical_id,
        'admissionEligible':False,'fidelityGate':'NOT_RUN'}
    if not isinstance(result,dict) or any(result.get(key)!=value for key,value in expected.items()):
        raise ValueError('capture_identity_or_status_mismatch')
    if result.get('createdNodeIds') != [] or result.get('mutatedNodeIds') != [] or result.get('issues') != []:
        raise ValueError('capture_must_be_successful_read_only')
    for key in ('captureId','exporterVersion'):
        if not isinstance(result.get(key),str) or not result[key].strip():
            raise ValueError('missing_native_capture_identity')
    evidence=result['nativeEvidence']
    if not isinstance(evidence,dict):
        raise ValueError('invalid_native_capture_evidence')
    if evidence.get('rootReference')!=component_reference or not evidence.get('pageReference'):
        raise ValueError('capture_root_mismatch')
    nodes=evidence['nodes']
    if not isinstance(nodes,list) or not nodes or any(not isinstance(node,dict) for node in nodes) or nodes[0].get('reference')!=component_reference or nodes[0].get('type')!='COMPONENT' or nodes[0].get('parentReference') is not None:
        raise ValueError('capture_root_mismatch')
    seen=set()
    for index,node in enumerate(nodes):
        if not isinstance(node.get('properties'),dict):
            raise ValueError('invalid_native_capture_properties')
        reference=node['reference']
        if not isinstance(reference,str) or not reference or reference in seen or (index and node['parentReference'] not in seen):
            raise ValueError('invalid_native_capture_tree')
        seen.add(reference)
        for bounds in (node['localBounds'],node['absoluteBounds']):
            if bounds is None:
                if index==0: raise ValueError('capture_root_bounds_unknown')
                continue
            if not isinstance(bounds,dict) or any(isinstance(bounds.get(key),bool) or not isinstance(bounds.get(key),(int,float)) or not math.isfinite(bounds[key]) for key in ('x','y','width','height')):
                raise ValueError('invalid_native_capture_bounds')
            if bounds['width']<0 or bounds['height']<0:
                raise ValueError('invalid_native_capture_bounds')
    root_bounds=nodes[0]['localBounds']
    if root_bounds['width']<=0 or root_bounds['height']<=0:
        raise ValueError('capture_empty_root')
    raster=result['raster']
    if not isinstance(raster,dict) or raster.get('format')!='PNG' or type(raster.get('scale')) not in (int,float) or raster.get('scale')!=1 or raster.get('background')!='native-transparent':
        raise ValueError('unsupported_native_raster_context')
    values=raster['bytes']
    if not isinstance(values,list) or not values or len(values)>16*1024*1024 or any(type(value) is not int or not 0<=value<=255 for value in values):
        raise ValueError('invalid_native_png_bytes')
    raw=bytes(values)
    if len(raw)<24 or raw[:8]!=b'\x89PNG\r\n\x1a\n' or raw[12:16]!=b'IHDR':
        raise ValueError('invalid_native_png_header')
    width,height=struct.unpack('>II',raw[16:24])
    if not width or not height or width>4096 or height>4096 or width*height>4_000_000:
        raise ValueError('native_png_exceeds_component_limits')
    with Image.open(BytesIO(raw)) as image:
        if image.format!='PNG': raise ValueError('native_raster_not_png')
        if image.width>4096 or image.height>4096 or image.width*image.height>4_000_000:
            raise ValueError('native_png_exceeds_component_limits')
        if image.width!=math.ceil(root_bounds['width']) or image.height!=math.ceil(root_bounds['height']):
            raise ValueError('native_png_size_mismatch')
        image.load()
        rgba=image.convert('RGBA')
        white=Image.new('RGBA',rgba.size,(255,255,255,255))
        white.alpha_composite(rgba)
        stream=BytesIO();white.save(stream,format='PNG');comparison=stream.getvalue()
    raw_evidence=(json.dumps(evidence,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode('utf-8')
    manifest={'scope':'figma_native_capture_artifacts','status':'PASS','evidenceScope':scope,
        'captureId':result['captureId'],'exporterVersion':result['exporterVersion'],
        'fileReference':file_reference,'componentReference':component_reference,'logicalId':logical_id,
        'nativeEvidenceSha256':digest_bytes(raw_evidence),'nativePngSha256':digest_bytes(raw),
        'comparisonPngSha256':digest_bytes(comparison),'pixelSize':[rgba.width,rgba.height],
        'normalization':{'operation':'alpha-composite-on-white','resize':False,'crop':False,'scale':1},
        'fidelityGate':'NOT_RUN','admissionEligible':False,
        'limitations':['Native transport validation does not establish CSS equivalence or platform authenticity.',
            'Per-glyph metrics and full independent Fidelity Capture mapping remain pending.']}
    return manifest, {'native-evidence.json':raw_evidence,'native.png':raw,'comparison-white.png':comparison}


def save_capture(result, output, **expected):
    output=Path(output).resolve()
    if not output.is_relative_to((ROOT/'artifacts').resolve()):
        raise ValueError('capture_output_must_be_project_artifacts')
    manifest,files=package_capture(result,**expected)
    # Immutable output: never overwrite an existing native artifact or modified evidence.
    output.mkdir(parents=True,exist_ok=True)
    targets=[output/name for name in (*files,'capture_manifest.json')]
    if any(path.exists() for path in targets):
        raise ValueError('capture_output_exists_choose_new_directory')
    manifest['files']={name:digest_bytes(content) for name,content in files.items()}
    for name,content in files.items():
        with (output/name).open('xb') as handle: handle.write(content)
    # Publish the manifest last; partial writes never have a passing manifest.
    with (output/'capture_manifest.json').open('x',encoding='utf-8') as handle:
        handle.write(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    return manifest


def verify_saved_capture(directory):
    directory=Path(directory)
    report={'scope':'figma_native_capture_integrity','status':'FAIL','admissionEligible':False,
        'fidelityGate':'NOT_RUN','issues':[]}
    try:
        manifest=load_json(directory/'capture_manifest.json')
        names={'native-evidence.json','native.png','comparison-white.png'}
        if not isinstance(manifest,dict) or manifest.get('scope')!='figma_native_capture_artifacts' or manifest.get('status')!='PASS' or not isinstance(manifest.get('files'),dict) or set(manifest['files'])!=names:
            raise ValueError('invalid_native_capture_manifest')
        files={name:(directory/name).read_bytes() for name in names}
        if any(digest_bytes(content)!=manifest['files'][name] for name,content in files.items()):
            raise ValueError('native_capture_artifact_hash_mismatch')
        result={'scope':'figma_native_component_capture','status':'PASS','evidenceKind':'native-platform-export',
            'evidenceScope':manifest['evidenceScope'],'captureId':manifest['captureId'],
            'exporterVersion':manifest['exporterVersion'],'fileReference':manifest['fileReference'],
            'componentReference':manifest['componentReference'],'logicalId':manifest['logicalId'],
            'createdNodeIds':[],'mutatedNodeIds':[],'issues':[],'admissionEligible':False,'fidelityGate':'NOT_RUN',
            'nativeEvidence':load_json(directory/'native-evidence.json'),
            'raster':{'format':'PNG','scale':1,'background':'native-transparent','bytes':list(files['native.png'])}}
        regenerated,reproduced=package_capture(result,file_reference=manifest['fileReference'],
            component_reference=manifest['componentReference'],logical_id=manifest['logicalId'],scope=manifest['evidenceScope'])
        if any(manifest.get(key)!=value for key,value in regenerated.items()) or any(files[name]!=content for name,content in reproduced.items()):
            raise ValueError('native_capture_manifest_or_normalization_mismatch')
        report.update(status='PASS',captureId=manifest['captureId'],evidenceScope=manifest['evidenceScope'])
    except (OSError,ValueError,KeyError,TypeError) as exc:
        report['issues']=[{'code':'invalid_saved_native_capture','detail':str(exc)}]
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture',type=Path)
    parser.add_argument('--file-reference',required=True)
    parser.add_argument('--component-reference',required=True)
    parser.add_argument('--logical-id',required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    try:
        manifest=save_capture(load_json(args.capture),args.output_dir,file_reference=args.file_reference,
            component_reference=args.component_reference,logical_id=args.logical_id)
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print(json.dumps({'scope':'figma_native_capture_import','status':'FAIL','fidelityGate':'NOT_RUN',
            'admissionEligible':False,'issues':[{'code':'invalid_native_capture','detail':str(exc)}]},ensure_ascii=False))
        return 1
    print(json.dumps({'status':manifest['status'],'logicalId':manifest['logicalId'],
        'nativePngSha256':manifest['nativePngSha256'],'fidelityGate':'NOT_RUN'},ensure_ascii=False))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
