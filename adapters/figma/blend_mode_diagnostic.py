"""Validate restored instrumentation and compare its independent PNG pixels."""
import base64
from copy import deepcopy
import hashlib
from io import BytesIO
from pathlib import Path
from PIL import Image
from adapters.figma.native_capture import verify_saved_capture
from validators.ui_ir import load_json


def compare_experiment(experiment, baseline_evidence, baseline_png, manifest):
    identity={'scope':'figma_text_blend_mode_experiment','status':'PASS','admissionEligible':False,
        'fidelityGate':'NOT_RUN','createdNodeIds':[],'issues':[],'originalObservedStateRestored':True}
    if any(experiment.get(key)!=value for key,value in identity.items()):raise ValueError('blend_experiment_not_successful')
    for key in ('fileReference','logicalId','componentReference'):
        if experiment.get(key)!=manifest.get(key):raise ValueError('blend_experiment_identity_mismatch')
    if manifest.get('evidenceScope')!='production' or experiment.get('pageReference')!=baseline_evidence.get('pageReference'):raise ValueError('blend_experiment_scope_mismatch')
    before=experiment['observations']['before'];normal=experiment['observations']['normal'];restored=experiment['observations']['restored']
    refs=experiment['mutatedNodeIds']
    if not refs or len(refs)!=len(set(refs)) or refs!=experiment['restoredNodeIds'] or restored!=before:raise ValueError('blend_experiment_state_not_restored')
    if len(before)!=len(baseline_evidence['nodes']) or len({row['reference'] for row in before})!=len(before):raise ValueError('blend_experiment_inventory_mismatch')
    expected=deepcopy(before)
    observed_texts={row['reference'] for row in before if row['type']=='TEXT'}
    if observed_texts!=set(refs):raise ValueError('blend_experiment_text_inventory_mismatch')
    for row,saved in zip(before,baseline_evidence['nodes']):
        if row['reference']!=saved['reference'] or row['type']!=saved['type'] or row['absoluteBounds']!=saved['absoluteBounds']:
            raise ValueError('blend_experiment_baseline_geometry_changed')
        if any(value!=saved['properties'].get(key) for key,value in row['properties'].items() if key!='name'):
            raise ValueError('blend_experiment_baseline_properties_changed')
    for row in expected:
        if row['reference'] in refs:
            if row['properties'].get('blendMode')!='PASS_THROUGH':raise ValueError('blend_experiment_original_mode_changed')
            row['properties']['blendMode']='NORMAL'
    if normal!=expected:raise ValueError('blend_experiment_unrelated_state_changed')
    images={};hashes={};raw={}
    for stage in ('before','normal','restored'):
        raster=experiment['rasters'][stage]
        if raster.get('format')!='PNG' or raster.get('scale')!=1 or raster.get('encoding')!='base64' or not isinstance(raster.get('data'),str) or len(raster['data'])>4*1024*1024:raise ValueError('blend_experiment_invalid_raster')
        data=base64.b64decode(raster['data'],validate=True)
        with Image.open(BytesIO(data)) as image:
            if image.format!='PNG' or image.width*image.height>65536:raise ValueError('blend_experiment_invalid_png')
            images[stage]=image.convert('RGBA');raw[stage]=data;hashes[stage]=hashlib.sha256(data).hexdigest()
    if raw['before']!=baseline_png:raise ValueError('blend_experiment_baseline_png_changed')
    if any(image.size!=images['before'].size for image in images.values()):raise ValueError('blend_experiment_raster_size_changed')
    def changed(stage):return sum(a!=b for a,b in zip(images['before'].getdata(),images[stage].getdata()))
    normal_changed=changed('normal');restored_changed=changed('restored')
    if restored_changed:raise ValueError('blend_experiment_pixels_not_restored')
    return {'scope':'figma_text_blend_mode_pixel_diagnostic','status':'PASS','logicalId':manifest['logicalId'],
        'fileReference':manifest['fileReference'],'componentReference':manifest['componentReference'],
        'mutatedNodeIds':refs,'restoredNodeIds':experiment['restoredNodeIds'],'nativePngHashes':hashes,
        'normalVsBeforeChangedPixels':normal_changed,'restoredVsBeforeChangedPixels':restored_changed,
        'observedEffect':'NO_PIXEL_CHANGE_IN_CURRENT_STATIC_COMPONENT' if normal_changed==0 else 'PIXEL_CHANGE_OBSERVED',
        'admissionEligible':False,'fidelityGate':'NOT_RUN',
        'limitations':['Only current static component/content/background is tested; no general CSS blend-mode equivalence is certified.',
            'This experiment does not compare with official browser pixels or admit a component.']}


def evaluate_saved(experiment_path, capture_directory):
    capture_directory=Path(capture_directory)
    if verify_saved_capture(capture_directory)['status']!='PASS':raise ValueError('blend_experiment_baseline_capture_invalid')
    report=compare_experiment(load_json(experiment_path),load_json(capture_directory/'native-evidence.json'),
        (capture_directory/'native.png').read_bytes(),load_json(capture_directory/'capture_manifest.json'))
    report['experimentSha256']=hashlib.sha256(Path(experiment_path).read_bytes()).hexdigest()
    return report
