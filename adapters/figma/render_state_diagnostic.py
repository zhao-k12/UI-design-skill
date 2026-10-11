"""Compare observed render state, without claiming full CSS normalization."""
import hashlib
from pathlib import Path
from adapters.figma.native_capture import verify_saved_capture
from validators.component_ir import verify_artifacts
from validators.ui_ir import load_json


def compare_render_state(reference, native, settings):
    roles={}
    kind=reference['componentType']
    for row in settings['rows']:
        roles[(row['path'],row['surface'])]=row['properties']
    checks=[];unverified=[]
    for index,node in enumerate(native['nodes']):
        name=node['name'];surface='element'
        if index==0:path='0'
        elif name=='source/placeholder':path='0.1';surface='::placeholder'
        elif name=='source/selected-value-text':path='0.0.1.0'
        elif name=='source/selected-value':path='0.0.1.0'
        elif name=='source/ionicons-arrow':path='0.0.1.1';surface='::before'
        elif name.startswith('source/'):path=name[7:]
        elif kind=='Button' and node['type']=='TEXT':path='0.0'
        else:unverified.append({'reference':node['reference'],'reason':'source_role_unresolved'});continue
        style=roles.get((path,surface))
        if style is None:unverified.append({'reference':node['reference'],'reason':'source_state_missing'});continue
        props=node['properties']
        def check(field,expected,equal):
            if field not in props:
                unverified.append({'reference':node['reference'],'field':field,'reason':'native_property_missing'});return
            if isinstance(props[field],dict) and props[field].get('nativeMixed') is True:
                unverified.append({'reference':node['reference'],'field':field,'reason':'native_mixed_property'});return
            checks.append({'reference':node['reference'],'sourcePath':path,'surface':surface,
                'field':field,'expected':expected,'actual':props[field],'status':'PASS' if equal else 'FAIL'})
        if style.get('opacity')=='1':check('opacity',1,type(props.get('opacity')) in (int,float) and props['opacity']==1)
        else:unverified.append({'reference':node['reference'],'field':'opacity','reason':'source_opacity_unsupported'})
        if all(style.get(key)=='none' for key in ('box-shadow','text-shadow','filter')):
            check('effects',[],props.get('effects')==[])
        else:unverified.append({'reference':node['reference'],'field':'effects','reason':'source_effects_unsupported'})
        if style.get('mix-blend-mode')=='normal' and style.get('opacity')=='1':
            allowed=['NORMAL'] if node['type']=='TEXT' else ['NORMAL','PASS_THROUGH']
            if node['type']=='TEXT' and props.get('blendMode')=='PASS_THROUGH':
                unverified.append({'reference':node['reference'],'field':'blendMode','actual':'PASS_THROUGH','reason':'native_passthrough_text_not_css_normalized'})
            else:check('blendMode',allowed,props.get('blendMode') in allowed)
        else:unverified.append({'reference':node['reference'],'field':'blendMode','reason':'source_blending_unsupported'})
        if node['type']=='TEXT':
            for css,field,source_value,native_value in [('text-transform','textCase','none','ORIGINAL'),
                    ('text-decoration-line','textDecoration','none','NONE')]:
                if style.get(css)==source_value:check(field,native_value,props.get(field)==native_value)
                else:unverified.append({'reference':node['reference'],'field':field,'reason':'source_text_style_unsupported'})
            if style.get('letter-spacing') in ('normal','0px'):
                check('letterSpacing',{'unit':'PIXELS','value':0},props.get('letterSpacing')=={'unit':'PIXELS','value':0})
            else:unverified.append({'reference':node['reference'],'field':'letterSpacing','reason':'source_tracking_unsupported'})
    return {'scope':'figma_observed_render_state_diagnostic','logicalId':reference['logicalComponentId'],
        'status':'FAIL' if any(row['status']=='FAIL' for row in checks) else 'REVIEW' if unverified or not checks else 'PASS',
        'checks':checks,'unverified':unverified,'admissionEligible':False,'fidelityGate':'NOT_RUN',
        'limitations':['PASS covers only listed observed properties, not all CSS or pixel equality.',
            'Normal/pass-through containers are compared only at unit opacity; masks, clipping, font shaping and rasterization remain independent.']}


def run(reference_directory, source_evidence, capture_directories, *, file_reference):
    reference_directory=Path(reference_directory)
    if verify_artifacts(reference_directory):raise ValueError('invalid_reference_artifacts')
    bundle=load_json(reference_directory/'component_ir.json')
    if source_evidence.get('status')!='PASS' or source_evidence.get('scope')!='official_runtime_text_box_diagnostic' or source_evidence.get('referenceComponentIrSha256')!=hashlib.sha256((reference_directory/'component_ir.json').read_bytes()).hexdigest():raise ValueError('render_state_source_identity_mismatch')
    matches=source_evidence.get('referenceMatches',[])
    expected={row['logicalComponentId'] for row in bundle['components']}
    if len(matches)!=len(expected) or {row.get('logicalId') for row in matches}!=expected or any(row.get('screenshotMatches') is not True or row.get('environmentMatches') is not True for row in matches):raise ValueError('render_state_reference_not_reproduced')
    reports=[]
    for reference in bundle['components']:
        provenance_keys=('sourceVersion','sourceLockSha256','packageVersion','officialCssSha256','officialRuntimeSha256','casesSha256','harnessBundleSha256','extractorSha256','assemblySha256')
        if reference['environment']!=source_evidence.get('environment') or any(not reference['provenance'].get(key) or reference['provenance'][key]!=source_evidence.get('provenance',{}).get(key) for key in provenance_keys):raise ValueError('render_state_source_environment_mismatch')
        logical_id=reference['logicalComponentId'];directory=Path(capture_directories[logical_id])
        if verify_saved_capture(directory)['status']!='PASS':raise ValueError('render_state_capture_integrity_failed')
        manifest=load_json(directory/'capture_manifest.json')
        if manifest['logicalId']!=logical_id or manifest['evidenceScope']!='production' or manifest['fileReference']!=file_reference:raise ValueError('render_state_capture_identity_mismatch')
        settings=[row for row in source_evidence['renderingSettings'] if row['logicalId']==logical_id]
        if len(settings)!=1:raise ValueError('render_state_source_role_ambiguous')
        reports.append(compare_render_state(reference,load_json(directory/'native-evidence.json'),settings[0]))
    return {'scope':'figma_render_state_diagnostic_batch','status':'FAIL' if any(row['status']=='FAIL' for row in reports) else 'REVIEW' if any(row['status']=='REVIEW' for row in reports) else 'PASS',
        'components':reports,'admissionEligible':False,'fidelityGate':'NOT_RUN'}
