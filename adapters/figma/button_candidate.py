"""Compile the supported official static Button sample into a native candidate."""
import json
import hashlib
import math
import re
from pathlib import Path

from adapters.figma.candidate_preflight import prepare_candidates
from validators.ui_ir import load_json
from adapters.figma.baseline_alignment import compare_baseline_alignment


def calibrated_span(reference, component, spec, directory, file_reference):
    """Resolve an explicit source/native baseline bundle, never a guessed offset."""
    names = ['official-runtime-complete-baseline-evidence.json',
        'native-text-outline-after-baseline-revision.json', 'font-file-identity.json',
        'official-native-candidate-execution.json']
    paths = {name: Path(directory)/name for name in names}
    source, native, identity, inventory = [load_json(paths[name]) for name in names]
    digest = hashlib.sha256((Path(reference)/'component_ir.json').read_bytes()).hexdigest()
    if source.get('referenceComponentIrSha256') != digest or native.get('fileReference') != file_reference:
        raise ValueError('button_baseline_reference_mismatch')
    report = compare_baseline_alignment(source, native, identity, inventory)
    rows = [row for row in report['observations'] if row['logicalId'] == component['logicalComponentId']]
    if len(rows) != 1 or not rows[0].get('exactContourCoordinatesEqual'):
        raise ValueError('button_baseline_geometry_unverified')
    row = rows[0]
    texts = [item for item in native['observations'] if item['textReference'] == row['textReference']]
    if len(texts) != 1: raise ValueError('button_baseline_text_missing')
    text = texts[0]
    if any(text.get(key) != spec[key] for key in ('fontName','fontSize','fontWeight')) or text['characters'] != spec['text'] or text['lineHeight'] != {'unit':'PIXELS','value':spec['lineHeight']}:
        raise ValueError('button_baseline_font_binding_mismatch')
    bounds = component['nodes'][1]['bounds']
    if text['absoluteBounds']['width'] != bounds['width'] or text['absoluteBounds']['height'] != bounds['height']:
        raise ValueError('button_baseline_text_dimensions_mismatch')
    baseline = row['sourceBaselineComponentY']; native_baseline = row['nativeSvgBaselineOffset']
    offset = baseline - bounds['y'] - native_baseline
    if not math.isfinite(offset) or abs(offset) > bounds['height']:
        raise ValueError('button_baseline_offset_invalid')
    return {'bounds':bounds, 'textOffsetY':offset, 'nativeSvgBaseline':native_baseline,
        'verifiedNativeSvg':text['svg'],
        'sourceBaselineComponentY':baseline,
        'evidenceHashes':{name:hashlib.sha256(path.read_bytes()).hexdigest() for name,path in paths.items()}}


def px(value):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9]+(?:\.[0-9]+)?px', value):
        raise ValueError('unsupported_css_length: ' + str(value))
    return float(value[:-2])


def paint(value):
    match = re.fullmatch(r'rgb\(([0-9]+), ([0-9]+), ([0-9]+)\)', value)
    if not match or any(int(channel) > 255 for channel in match.groups()):
        raise ValueError('unsupported_css_color: ' + str(value))
    return {'type': 'SOLID', 'color': dict(zip(('r', 'g', 'b'), (int(channel) / 255 for channel in match.groups())))}


def translate_button(component, font_name):
    if component['componentType'] != 'Button' or component['state'] != 'default-static' or component['props'] != {'type': 'primary', 'size': 'default'}:
        raise ValueError('unsupported_button_variant')
    nodes = component['nodes']
    if len(nodes) != 2 or nodes[0]['tag'] != 'button' or nodes[1]['tag'] != 'span' or not all(n['visible'] for n in nodes):
        raise ValueError('unsupported_button_structure')
    root, label = nodes
    if root['path'] != '0' or label['path'] != '0.0' or label['parentPath'] != '0':
        raise ValueError('unsupported_button_paths')
    if component['iconMetrics'] or label['pseudoElements'] or len(label['textRuns']) != 1:
        raise ValueError('unsupported_button_content')
    text = label['textRuns'][0]['text']
    if text != component['content']['text'] or component['content']['options']:
        raise ValueError('button_content_mismatch')
    for node in nodes:
        style = node['computedStyle']
        for key, allowed in {'transform': ['none'], 'box-shadow': ['none'], 'opacity': ['1'],
                'font-style': ['normal'], 'text-transform': ['none'], 'letter-spacing': ['normal', '0px']}.items():
            if style.get(key) not in allowed:
                raise ValueError('unsupported_button_style: ' + key)
        if any(pseudo.get('display') != 'none' and pseudo.get('content') not in ('none', 'normal') for pseudo in node['pseudoElements'].values()):
            raise ValueError('unsupported_visible_pseudo')
    style = root['computedStyle']
    borders = [px(style[f'border-{side}-width']) for side in ('top', 'right', 'bottom', 'left')]
    colors = [style[f'border-{side}-color'] for side in ('top', 'right', 'bottom', 'left')]
    radii = [px(style[f'border-{corner}-radius']) for corner in ('top-left', 'top-right', 'bottom-right', 'bottom-left')]
    if len(set(borders)) != 1 or len(set(colors)) != 1 or len(set(radii)) != 1 or any(style[f'border-{side}-style'] != 'solid' for side in ('top', 'right', 'bottom', 'left')):
        raise ValueError('unsupported_nonuniform_border')
    if style['box-sizing'] != 'border-box' or style['text-align'] != 'center':
        raise ValueError('unsupported_button_box')
    width, height = component['rootBounds']['width'], component['rootBounds']['height']
    if not all(isinstance(v, (float, int)) and math.isfinite(v) and v > 0 for v in (width, height)):
        raise ValueError('invalid_button_geometry')
    if not isinstance(font_name, dict) or set(font_name) != {'family', 'style'}:
        raise ValueError('unsupported_font_binding')
    return {'logicalId': component['logicalComponentId'], 'name': 'candidate/' + component['logicalComponentId'],
        'sourceVersion': component['provenance']['sourceVersion'], 'width': width, 'height': height,
        'fill': paint(style['background-color']), 'stroke': paint(colors[0]), 'strokeWidth': borders[0],
        'radius': radii[0], 'padding': {side: px(style['padding-' + side]) for side in ('top', 'right', 'bottom', 'left')},
        'text': text, 'fontName': font_name, 'fontWeight': int(label['computedStyle']['font-weight']),
        'fontSize': px(label['computedStyle']['font-size']), 'lineHeight': px(label['computedStyle']['line-height']),
        'textFill': paint(label['computedStyle']['color'])}


def prepare_button(reference, font_evidence, discovery, *, logical_id, bindings, file_reference, page_reference, baseline_directory=None):
    report = prepare_candidates(reference, font_evidence, discovery, logical_ids=[logical_id],
        bindings=bindings, file_reference=file_reference)
    report['script'] = None
    if report['status'] != 'PASS':
        return report
    try:
        components = load_json(Path(reference) / 'component_ir.json')['components']
        component = next(item for item in components if item['logicalComponentId'] == logical_id)
        requirements = report['fontPreflight']['requirements']
        if len(requirements) != 1:
            raise ValueError('unsupported_button_font_mix')
        spec = translate_button(component, requirements[0]['binding'])
        if baseline_directory is not None:
            spec['sourceSpan'] = calibrated_span(reference, component, spec, baseline_directory, file_reference)
            spec['name'] += '/baseline-v1'
        payload = {'fileReference': file_reference, 'pageReference': page_reference, 'spec': spec}
        runtime = Path(__file__).with_name('button_candidate.js').read_text(encoding='utf-8')
        capture_runtime = Path(__file__).with_name('native_capture.js').read_text(encoding='utf-8')
        capture_request = {'fileReference': file_reference, 'pageReference': page_reference,
            'logicalId': logical_id, 'evidenceScope': 'production'}
        report['script'] = runtime + '\n' + capture_runtime + '\nconst built = await buildButtonCandidate(figma, ' + json.dumps(payload, ensure_ascii=False, allow_nan=False) + ');\nreturn await finishCandidateCapture(figma,built,' + json.dumps(capture_request,ensure_ascii=False) + ');\n'
        report['preparation']['nativeBuilder'] = 'button-static-baseline-v0.1.1' if baseline_directory is not None else 'button-static-v0.1.0'
        if baseline_directory is not None:
            report['preparation']['baselineEvidenceHashes'] = spec['sourceSpan']['evidenceHashes']
    except (OSError, ValueError, KeyError, TypeError, StopIteration) as exc:
        report.update(status='FAIL', preparation=None, issues=[{'code': 'unsupported_button_candidate', 'detail': str(exc)}])
    return report
