"""TASK-020 approval scope; never a substitute for native fidelity evidence."""
from validators.ui_ir import ROOT
from validators.visual.fidelity import file_hash

DECISION_SHA256 = '16ccb7f958dda5f6e8933e081d893080b0d924785ee8e3de8d87d9e8cb1e97aa'
SCOPE = {
    'data.table.headed.613acb453dafc1629920ac3d697c42918bef2d556cc6f7e61648523f1f7f24aa':
        ('b71439e9d1ee3c80b61c21d8ed864bbcb7ff462d9fee9e8dc298b5ee53a002c1', 720, 134.875),
    'data.table.headed.5eca5bc513698ad31a2d57d0660cebee6ef0536e196c5ed468f8153f52b90c25':
        ('8b14f33d3468b3372046aa2a533824173cc26bd1e9e3990af1b8c202dbd10771', 960, 230.875),
}

def require_scope(plan):
    if file_hash(ROOT/'.dev/TASK-020_FIDELITY_DECISION.md') != DECISION_SHA256:
        raise ValueError('headed_approval_binding_mismatch')
    expected = SCOPE.get(plan['logicalId'])
    actual = (plan['componentIrSha256'], plan['rootBounds']['width'], plan['rootBounds']['height'])
    if expected is None or actual != expected:
        raise ValueError('headed_approval_scope_mismatch')

def header_background_union(plan):
    """Prove an exact contiguous opaque union; do not infer or expand bounds."""
    require_scope(plan)
    row = plan['rows'][0]
    cells = row['cells']
    bounds = row['bounds']
    if not cells:
        raise ValueError('headed_union_empty')
    fill = cells[0]['fill']
    if fill != '#f8f8f9':
        raise ValueError('headed_union_fill_mismatch')
    cursor = bounds['x']
    for cell in cells:
        rectangle = cell['bounds']
        if (cell['text']['role'] != 'header' or cell['fill'] != fill or
            rectangle['x'] != cursor or rectangle['y'] != bounds['y'] or
            rectangle['height'] != bounds['height'] or rectangle['width'] <= 0):
            raise ValueError('headed_union_not_contiguous')
        cursor += rectangle['width']
    if cursor != bounds['x'] + bounds['width']:
        raise ValueError('headed_union_incomplete')
    return {'decisionSha256': DECISION_SHA256, 'rowPath': row['path'],
            'bounds': dict(bounds), 'fill': fill, 'opacity': 1,
            'cellPaths': [cell['path'] for cell in cells],
            'fidelityGate': 'NOT_RUN', 'productionAdmission': False}
