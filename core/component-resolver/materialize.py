"""Keep the frozen layout containers while filling their Cell envelopes."""
from copy import deepcopy
import importlib

from core.layout.engine import LayoutEngine
from validators.structure.gate import builder
from validators.ui_ir import validate_document

assembly_module=importlib.import_module('core.component-resolver.assembly')


def materialize(assembly,layout_tree,tokens,*,document_id):
    if assembly.get('status')!='PASS' or not assembly.get('sourcePlacementVerified'):
        raise ValueError('Source-sized PASS assembly is required')
    if assembly.get('stateSha256')!=assembly_module.state_digest(assembly):
        raise ValueError('Assembly checkpoint was modified')
    report=assembly['mapping']['layoutReport']
    if builder.fingerprint(layout_tree)!=report['layoutTreeSha256']:
        raise ValueError('Layout tree differs from assembly baseline')
    if tokens.fingerprint!=report['tokenRegistrySha256']:
        raise ValueError('Token registry differs from assembly baseline')
    checked=LayoutEngine(tokens).run(layout_tree)
    if checked['status']!='PASS' or builder.fingerprint(checked['skeleton'])!=assembly['skeletonSha256']:
        raise ValueError('Layout skeleton no longer matches assembly')
    boxes={}
    def index(n):
        boxes[n['id']]=n['box']
        for c in n.get('children',[]):index(c)
    index(checked['skeleton'])
    replacements={}
    for operations in assembly['sections'].values():
        for op in operations:
            key=op['targetCellId']
            if key in replacements or op['box']!=boxes.get(key) or 'replacement' not in op:
                raise ValueError('Invalid or duplicate Cell replacement')
            replacements[key]=op
    used=set()
    def translate(n):
        if n['type']=='Cell':
            if n['id'] not in replacements:raise ValueError('Unfilled layout Cell')
            used.add(n['id']);result=deepcopy(replacements[n['id']]['replacement'])
            if 'span' in n['layout']:result['layout']['span']=n['layout']['span']
            return result
        result={k:deepcopy(n[k]) for k in ('id','type','sourceIds') if k in n}
        result['layout']=deepcopy(n['layout'])
        box=boxes[n['id']]
        if box['width']<=0 or box['height']<=0:raise ValueError('Empty layout regions require explicit handling')
        result['layout']['width']={'mode':'fixed','value':box['width']}
        result['layout']['height']={'mode':'fixed','value':box['height']}
        if n['type']=='Grid':result['layout']['wrap']=False
        result['children']=[translate(c) for c in n.get('children',[])]
        return result
    document={'uiIrVersion':'0.1.0','documentId':document_id,'pages':[translate(layout_tree['page'])]}
    if used!=set(replacements):raise ValueError('Replacement references a nonexistent Cell')
    issues=validate_document(document)
    if issues:raise ValueError('Materialized UI-IR is invalid: '+str(issues))
    return {'status':'PASS','document':document,'uiIrSha256':builder.fingerprint(document),
            'skeletonSha256':assembly['skeletonSha256'],'assemblyStateSha256':assembly['stateSha256'],
            'readyForAdapter':assembly['readyForAdapter'],'nativeExecution':'NOT_RUN'}
