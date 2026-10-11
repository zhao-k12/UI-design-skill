"""Check independent repeated native exports; stable does not mean faithful."""
from pathlib import Path
from PIL import Image
from adapters.figma.native_capture import verify_saved_capture
from validators.ui_ir import load_json


def evaluate_repeatability(directories, *, scope='production'):
    if scope not in ('production','test-fixture'):raise ValueError('invalid_repeatability_scope')
    if not isinstance(directories,(list,tuple)) or not 3<=len(directories)<=8:raise ValueError('repeatability_requires_three_to_eight_captures')
    manifests=[];images=[]
    for directory in directories:
        directory=Path(directory)
        if verify_saved_capture(directory)['status']!='PASS':raise ValueError('repeatability_capture_integrity_failed')
        manifest=load_json(directory/'capture_manifest.json')
        if manifest['evidenceScope']!=scope:raise ValueError('repeatability_capture_scope_mismatch')
        manifests.append(manifest)
        with Image.open(directory/'native.png') as image:images.append(image.convert('RGBA'))
    first=manifests[0]
    if len({row['captureId'] for row in manifests})!=len(manifests):raise ValueError('repeatability_capture_ids_not_independent')
    for row in manifests:
        if any(row[key]!=first[key] for key in ('fileReference','componentReference','logicalId','exporterVersion','evidenceScope')):raise ValueError('repeatability_capture_identity_mismatch')
    comparisons=[]
    for manifest,image in zip(manifests[1:],images[1:]):
        same_size=image.size==images[0].size
        pixels=sum(a!=b for a,b in zip(images[0].getdata(),image.getdata())) if same_size else None
        comparisons.append({'captureId':manifest['captureId'],'sizeEqual':same_size,
            'changedPixels':pixels,'pngBytesEqual':manifest['nativePngSha256']==first['nativePngSha256'],
            'nativeObservationEqual':manifest['nativeEvidenceSha256']==first['nativeEvidenceSha256']})
    stable=all(row['sizeEqual'] and row['changedPixels']==0 and row['nativeObservationEqual'] for row in comparisons)
    return {'scope':'figma_native_export_repeatability','status':'PASS' if stable else 'REVIEW',
        'evidenceScope':scope,
        'logicalId':first['logicalId'],'fileReference':first['fileReference'],'componentReference':first['componentReference'],
        'captures':[{'captureId':row['captureId'],'nativePngSha256':row['nativePngSha256'],
            'nativeEvidenceSha256':row['nativeEvidenceSha256']} for row in manifests],
        'comparisons':comparisons,'admissionEligible':False,'fidelityGate':'NOT_RUN',
        'limitations':['Independent host exports are compared only within the observed sessions; future exports may differ.',
            'Repeatability does not establish official-browser pixel fidelity or a cause for differences.']}
