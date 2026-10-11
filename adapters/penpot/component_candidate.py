"""Source-bound first Button candidate. Native baseline/fidelity remain unverified."""
from importlib import import_module
from pathlib import Path
import re
import hashlib

from validators.component_ir import validate_bundle
from validators.ui_ir import ROOT, load_json

digest = import_module("core.component-resolver.registry").digest


def px(value):
    if not isinstance(value,str) or not re.fullmatch(r"\d+(?:\.\d+)?px",value): raise ValueError("Unsupported CSS length")
    return float(value[:-2])


def color(value):
    match=re.fullmatch(r"rgb\((\d+), (\d+), (\d+)\)",value)
    if not match or any(int(v)>255 for v in match.groups()): raise ValueError("Unsupported CSS paint")
    return '#'+''.join(f'{int(v):02x}' for v in match.groups())


def prepare_button_candidate(reference, file_reference, page_reference):
    bundle=load_json(Path(reference)/'component_ir.json')
    if validate_bundle(bundle): raise ValueError("Component IR did not validate")
    source=next(c for c in bundle['components'] if c['logicalComponentId']=='action.button.primary.medium')
    catalog=load_json(ROOT/'registries/components/catalog.json')
    if digest(source)!=catalog['components'][source['logicalComponentId']]['fidelity']['componentIrSha256']:
        raise ValueError("Source differs from admitted official Component IR")
    if source['provenance']['sourceVersion']!=catalog['sourceVersion']: raise ValueError("Source version mismatch")
    nodes=source['nodes']
    if len(nodes)!=2 or nodes[0]['tag']!='button' or nodes[1]['tag']!='span' or source['iconMetrics']:
        raise ValueError("Unsupported Button structure")
    root,label=nodes; style=root['computedStyle']; typ=label['computedStyle']
    if len(label['textRuns'])!=1 or label['textRuns'][0]['text']!=source['content']['text']: raise ValueError("Unsupported label content")
    widths=[px(style[f'border-{side}-width']) for side in ('top','right','bottom','left')]
    colors=[style[f'border-{side}-color'] for side in ('top','right','bottom','left')]
    radii=[px(style[f'border-{corner}-radius']) for corner in ('top-left','top-right','bottom-right','bottom-left')]
    if len(set(widths))!=1 or len(set(colors))!=1 or len(set(radii))!=1:raise ValueError("Nonuniform border unsupported")
    if any(style[f'border-{side}-style']!='solid' for side in ('top','right','bottom','left')):raise ValueError("Unsupported border")
    if any(n['computedStyle']['box-shadow']!='none' or n['computedStyle']['transform']!='none' or n['computedStyle']['opacity']!='1' for n in nodes):raise ValueError("Unsupported rendering state")
    return {'fileReference':file_reference,'pageReference':page_reference,'logicalId':source['logicalComponentId'],
        'name':'candidate/'+source['logicalComponentId']+'/penpot-v1','sourceVersion':catalog['sourceVersion'],
        'componentIrSha256':digest(source),'rootBounds':source['rootBounds'],'fill':color(style['background-color']),
        'stroke':color(colors[0]),'strokeWidth':widths[0],'radius':radii[0],'labelBounds':label['bounds'],
        'characters':source['content']['text'],'fontFamily':'PingFang SC','fontWeight':int(typ['font-weight']),
        'fontSize':px(typ['font-size']),'lineHeight':px(typ['line-height']),'textFill':color(typ['color']),
        'baselineCalibration':'NOT_RUN','fidelityGate':'NOT_RUN'}


def prepare_input_candidate(reference, text_box_evidence, file_reference, page_reference):
    """Lock the empty Input source; browser text boxes are not native layout boxes."""
    source_path = Path(reference) / 'component_ir.json'
    bundle = load_json(source_path)
    if validate_bundle(bundle):
        raise ValueError('Component IR did not validate')
    logical_id = 'form.input.default.medium'
    source = next(c for c in bundle['components'] if c['logicalComponentId'] == logical_id)
    catalog = load_json(ROOT / 'registries/components/catalog.json')
    if digest(source) != catalog['components'][logical_id]['fidelity']['componentIrSha256'] or source['provenance']['sourceVersion'] != catalog['sourceVersion']:
        raise ValueError('Source differs from admitted official Component IR')
    visible = {n['path']: n for n in source['nodes'] if n['visible']}
    if {p:n['tag'] for p,n in visible.items()} != {'0':'div','0.1':'input'}:
        raise ValueError('Unsupported Input structure')
    wrapper, control = visible['0'], visible['0.1']
    props = source['props']
    if set(props) != {'size','modelValue','placeholder','elementId'} or props['size'] != 'default' or props['modelValue'] != '':
        raise ValueError('Unsupported Input props')
    if control['parentPath'] != '0' or wrapper['parentPath'] is not None or control['value'] != '' or control['textRuns'] or control['attributes']['type'] != 'text' or control['attributes']['placeholder'] != props['placeholder']:
        raise ValueError('Input placeholder mismatch')
    if set(control['pseudoElements']) != {'::placeholder'} or wrapper['pseudoElements'] or any(i['visible'] for i in source['iconMetrics']):
        raise ValueError('Unsupported Input pseudo or icon')
    style = control['computedStyle']
    placeholder = control['pseudoElements']['::placeholder']
    for state in (wrapper['computedStyle'], style, placeholder):
        if state['opacity'] != '1' or state['visibility'] != 'visible' or state['transform'] != 'none' or state['box-shadow'] != 'none':
            raise ValueError('Unsupported Input rendering state')
    widths = [px(style[f'border-{s}-width']) for s in ('top','right','bottom','left')]
    colors = [style[f'border-{s}-color'] for s in ('top','right','bottom','left')]
    radii = [px(style[f'border-{c}-radius']) for c in ('top-left','top-right','bottom-right','bottom-left')]
    if len(set(widths)) != 1 or len(set(colors)) != 1 or len(set(radii)) != 1 or any(style[f'border-{s}-style'] != 'solid' for s in ('top','right','bottom','left')):
        raise ValueError('Unsupported Input border')
    evidence = load_json(Path(text_box_evidence))
    evidence_sha = hashlib.sha256(Path(text_box_evidence).read_bytes()).hexdigest()
    if evidence_sha != 'bf0364c877bf840a28f343151fa0488f1235b4b9f5e325f085961cd5c8236171':
        raise ValueError('Input text evidence differs from locked browser observation')
    source_sha = hashlib.sha256(source_path.read_bytes()).hexdigest()
    if evidence['scope'] != 'official_runtime_text_box_diagnostic' or evidence['status'] != 'PASS' or evidence['referenceComponentIrSha256'] != source_sha:
        raise ValueError('Input text evidence source mismatch')
    matches = [m for m in evidence['referenceMatches'] if m['logicalId'] == logical_id]
    observations = [o for o in evidence['observations'] if o['logicalId'] == logical_id]
    if len(matches) != 1 or not matches[0]['screenshotMatches'] or not matches[0]['environmentMatches'] or evidence['environment'] != source['environment'] or len(observations) != 1:
        raise ValueError('Input text evidence incomplete')
    observation = observations[0]
    if observation['surface'] != 'user-agent-shadow' or observation['text'] != props['placeholder']:
        raise ValueError('Input text evidence content mismatch')
    return {'fileReference':file_reference,'pageReference':page_reference,'logicalId':logical_id,
        'name':'candidate/'+logical_id+'/penpot-v1','sourceVersion':catalog['sourceVersion'],
        'componentIrSha256':digest(source),'rootBounds':source['rootBounds'],
        'fill':color(style['background-color']),'stroke':color(colors[0]),'strokeWidth':widths[0],'radius':radii[0],
        'characters':props['placeholder'],'labelRole':'placeholder','fontFamily':'PingFang SC',
        'fontWeight':int(placeholder['font-weight']),'fontSize':px(placeholder['font-size']),
        'textFill':color(placeholder['color']),'sourceTextBounds':observation['componentBounds'],
        'sourceTextEvidenceSha256':evidence_sha,
        'ignoredHiddenPaths':[n['path'] for n in source['nodes'] if not n['visible']],
        'nativeTextBounds':None,'baselineCalibration':'NOT_RUN','fidelityGate':'NOT_RUN'}


def prepare_select_candidate(reference, file_reference, page_reference):
    """Translate only the locked closed, selected-value Select fixture."""
    bundle=load_json(Path(reference)/'component_ir.json')
    if validate_bundle(bundle):raise ValueError('Component IR did not validate')
    logical='form.select.default.medium'
    source=next(c for c in bundle['components'] if c['logicalComponentId']==logical)
    catalog=load_json(ROOT/'registries/components/catalog.json')
    if digest(source)!=catalog['components'][logical]['fidelity']['componentIrSha256'] or source['provenance']['sourceVersion']!=catalog['sourceVersion']:
        raise ValueError('Source differs from admitted official Component IR')
    nodes={n['path']:n for n in source['nodes'] if n['visible']}
    if {p:n['tag'] for p,n in nodes.items()}!={'0':'div','0.0':'div','0.0.1':'div','0.0.1.0':'span','0.0.1.1':'i'}:
        raise ValueError('Unsupported Select structure')
    props=source['props']
    if set(props)!={'size','modelValue','placeholder','elementId','transfer'} or props['size']!='default' or props['transfer'] is not False:
        raise ValueError('Unsupported Select props')
    selected=[o['label'] for o in source['content']['options'] if o['value']==props['modelValue']]
    label=nodes['0.0.1.0'];arrow=nodes['0.0.1.1'];style=nodes['0.0']['computedStyle'];typ=label['computedStyle']
    if len(selected)!=1 or len(label['textRuns'])!=1 or label['textRuns'][0]['text']!=selected[0]:raise ValueError('Select value mismatch')
    for path,node in nodes.items():
        if node['parentPath']!=(None if path=='0' else path.rsplit('.',1)[0]):raise ValueError('Select parent mismatch')
        if set(node['pseudoElements'])!=({'::before'} if path==arrow['path'] else set()):raise ValueError('Unsupported Select pseudo')
        state=node['computedStyle'];transform='matrix(1, 0, 0, 1, 0, -7)' if path==arrow['path'] else 'none'
        if state['opacity']!='1' or state['visibility']!='visible' or state['box-shadow']!='none' or state['transform']!=transform:raise ValueError('Unsupported Select rendering state')
    widths=[px(style[f'border-{s}-width']) for s in ('top','right','bottom','left')]
    colors=[style[f'border-{s}-color'] for s in ('top','right','bottom','left')]
    radii=[px(style[f'border-{c}-radius']) for c in ('top-left','top-right','bottom-right','bottom-left')]
    if len(set(widths))!=1 or len(set(colors))!=1 or len(set(radii))!=1 or any(style[f'border-{s}-style']!='solid' for s in ('top','right','bottom','left')):raise ValueError('Unsupported Select border')
    pseudo=arrow['pseudoElements']['::before']
    import json
    glyph=json.loads(pseudo['content'])
    if len(glyph)!=1 or pseudo['font-family']!='Ionicons':raise ValueError('Unsupported Select arrow')
    return {'fileReference':file_reference,'pageReference':page_reference,'logicalId':logical,
        'name':'candidate/'+logical+'/penpot-v1','sourceVersion':catalog['sourceVersion'],'componentIrSha256':digest(source),
        'rootBounds':source['rootBounds'],'fill':color(style['background-color']),'stroke':color(colors[0]),'strokeWidth':widths[0],'radius':radii[0],
        'characters':selected[0],'labelRole':'selected-value','fontFamily':'PingFang SC','fontWeight':int(typ['font-weight']),
        'fontSize':px(typ['font-size']),'textFill':color(typ['color']),'sourceTextBounds':label['textRuns'][0]['bounds'],
        'arrow':{'characters':glyph,'fontFamily':'Ionicons','fontWeight':int(pseudo['font-weight']),'fontSize':px(pseudo['font-size']),
            'lineHeight':px(pseudo['line-height']),'fill':color(pseudo['color']),'bounds':arrow['bounds']},
        'ignoredHiddenPaths':[n['path'] for n in source['nodes'] if not n['visible']],
        'nativeTextBounds':None,'baselineCalibration':'NOT_RUN','fidelityGate':'NOT_RUN'}
