"""Scoped, source-driven static Input/Select candidates, pending native fidelity."""
import json
import math
from pathlib import Path

from adapters.figma.button_candidate import paint, px
from adapters.figma.candidate_preflight import prepare_candidates
from validators.ui_ir import load_json


def geometry(bounds):
    for key in ('x', 'y', 'width', 'height'):
        value = bounds.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError('invalid_source_geometry')
    if bounds['width'] <= 0 or bounds['height'] <= 0:
        raise ValueError('empty_source_geometry')
    return dict(bounds)


def simple_style(style, *, transform='none'):
    expected = {'transform': transform, 'box-shadow': 'none', 'opacity': '1',
        'font-style': 'normal', 'text-transform': 'none', 'visibility': 'visible'}
    if any(style.get(key) != value for key, value in expected.items()):
        raise ValueError('unsupported_form_style')
    if style.get('letter-spacing') not in ('normal', '0px'):
        raise ValueError('unsupported_form_letter_spacing')


def surface(node):
    style = node['computedStyle']
    simple_style(style)
    sides = ('top', 'right', 'bottom', 'left')
    widths = [px(style[f'border-{side}-width']) for side in sides]
    colors = [style[f'border-{side}-color'] for side in sides]
    radii = [px(style[f'border-{corner}-radius']) for corner in ('top-left', 'top-right', 'bottom-right', 'bottom-left')]
    if len(set(widths)) != 1 or len(set(colors)) != 1 or len(set(radii)) != 1:
        raise ValueError('unsupported_form_border')
    if any(style[f'border-{side}-style'] != 'solid' for side in sides) or style['box-sizing'] != 'border-box':
        raise ValueError('unsupported_form_border')
    return {'bounds': geometry(node['bounds']), 'fill': paint(style['background-color']),
        'stroke': paint(colors[0]), 'strokeWidth': widths[0], 'radius': radii[0],
        'padding': {side: px(style['padding-' + side]) for side in sides}, 'sourcePath': node['path']}


def transparent_wrapper(node):
    style = node['computedStyle']
    simple_style(style)
    if style['background-color'] != 'rgba(0, 0, 0, 0)' or any(px(style['border-' + side + '-width']) or px(style['padding-' + side]) for side in ('top', 'right', 'bottom', 'left')):
        raise ValueError('unsupported_form_wrapper')
    geometry(node['bounds'])


def font_for_path(requirements, path, surface_name):
    matches = [item for item in requirements if any(use['path'] == path and use['surface'] == surface_name for use in item['uses'])]
    if len(matches) != 1 or not isinstance(matches[0].get('binding'), dict):
        raise ValueError('source_font_usage_unresolved: ' + path)
    font = matches[0]['binding']
    if set(font) != {'family', 'style'} or font['family'] != matches[0]['family']:
        raise ValueError('unsupported_form_font_binding')
    return font


def undecorated_text(style, *, allow_padding=False):
    if style['background-color'] != 'rgba(0, 0, 0, 0)' or any(px(style['border-' + side + '-width']) for side in ('top', 'right', 'bottom', 'left')):
        raise ValueError('unsupported_form_text_decoration')
    if not allow_padding and any(px(style['padding-' + side]) for side in ('top', 'right', 'bottom', 'left')):
        raise ValueError('unsupported_form_text_padding')


def text_spec(text, style, font, path):
    simple_style(style)
    if not isinstance(text, str) or not text:
        raise ValueError('empty_form_text')
    line_height = {'unit': 'AUTO'} if style['line-height'] == 'normal' else {'unit': 'PIXELS', 'value': px(style['line-height'])}
    weight = int(style['font-weight'])
    if weight != 400:
        raise ValueError('unsupported_form_font_weight')
    return {'characters': text, 'fontName': font, 'fontSize': px(style['font-size']),
        'fontWeight': weight, 'lineHeight': line_height, 'fill': paint(style['color']), 'sourcePath': path}


def translate_form(component, requirements):
    kind = component['componentType']
    if kind not in ('Input', 'Select') or component['state'] != 'default-static' or component['variant'] != 'default':
        raise ValueError('unsupported_form_variant')
    nodes = {node['path']: node for node in component['nodes'] if node['visible']}
    expected = {'0': 'div', '0.1': 'input'} if kind == 'Input' else {
        '0': 'div', '0.0': 'div', '0.0.1': 'div', '0.0.1.0': 'span', '0.0.1.1': 'i'}
    if {path: node['tag'] for path, node in nodes.items()} != expected:
        raise ValueError('unsupported_form_structure')
    for path, node in nodes.items():
        if node['parentPath'] != (None if path == '0' else path.rsplit('.', 1)[0]):
            raise ValueError('invalid_form_parent')
        # Only the captured Input placeholder and Select arrow have visible pseudo roles.
        allowed = {'::placeholder'} if path == '0.1' and kind == 'Input' else {'::before'} if path == '0.0.1.1' else set()
        if set(node['pseudoElements']) != allowed:
            raise ValueError('unsupported_form_pseudo')
    root = nodes['0']
    transparent_wrapper(root)
    root_bounds = geometry(root['bounds'])
    if root_bounds != {'x': 0, 'y': 0, **component['rootBounds']}:
        raise ValueError('form_root_bounds_mismatch')
    spec = {'componentType': kind, 'logicalId': component['logicalComponentId'],
        'name': 'candidate/' + component['logicalComponentId'], 'sourceVersion': component['provenance']['sourceVersion'],
        'rootBounds': root_bounds, 'ignoredHiddenPaths': [node['path'] for node in component['nodes'] if not node['visible']]}
    props = component['props']
    if kind == 'Input':
        if set(props) != {'size', 'modelValue', 'placeholder', 'elementId'} or props['size'] != 'default' or props['modelValue'] != '':
            raise ValueError('unsupported_input_props')
        control = nodes['0.1']
        if control['value'] != '' or control['attributes'].get('type') != 'text' or control['attributes'].get('placeholder') != props['placeholder'] or control['textRuns']:
            raise ValueError('input_placeholder_mismatch')
        spec['surface'] = surface(control)
        placeholder = control['pseudoElements']['::placeholder']
        undecorated_text(placeholder)
        spec['label'] = text_spec(props['placeholder'], placeholder, font_for_path(requirements, '0.1', 'element'), '0.1::placeholder')
        spec['labelRole'] = 'placeholder'
        spec['content'] = None
        spec['arrow'] = None
    else:
        if set(props) != {'size', 'modelValue', 'placeholder', 'elementId', 'transfer'} or props['size'] != 'default' or props['transfer'] is not False:
            raise ValueError('unsupported_select_props')
        control, content, label, arrow = (nodes[path] for path in ('0.0', '0.0.1', '0.0.1.0', '0.0.1.1'))
        transparent_wrapper(content)
        simple_style(label['computedStyle'])
        undecorated_text(label['computedStyle'], allow_padding=True)
        selected = [item['label'] for item in component['content']['options'] if item['value'] == props['modelValue']]
        if len(selected) != 1 or [run['text'] for run in label['textRuns']] != selected:
            raise ValueError('select_value_mismatch')
        spec['surface'] = surface(control)
        spec['content'] = {'bounds': geometry(content['bounds']), 'sourcePath': content['path']}
        border = spec['surface']['strokeWidth']
        expected_content = {'x': border, 'y': border, 'width': root_bounds['width'] - 2 * border, 'height': root_bounds['height'] - 2 * border}
        if spec['content']['bounds'] != expected_content or geometry(label['bounds']) != expected_content:
            raise ValueError('unsupported_select_content_geometry')
        spec['label'] = text_spec(selected[0], label['computedStyle'], font_for_path(requirements, label['path'], 'element'), label['path'])
        spec['label']['padding'] = {side: px(label['computedStyle']['padding-' + side]) for side in ('top', 'right', 'bottom', 'left')}
        spec['labelRole'] = 'selected-value'
        simple_style(arrow['computedStyle'], transform='matrix(1, 0, 0, 1, 0, -7)')
        undecorated_text(arrow['computedStyle'])
        if arrow['computedStyle']['position'] != 'absolute':
            raise ValueError('unsupported_select_arrow_position')
        pseudo = arrow['pseudoElements']['::before']
        undecorated_text(pseudo)
        try:
            glyph = json.loads(pseudo['content'])
        except (ValueError, TypeError) as exc:
            raise ValueError('unsupported_select_glyph') from exc
        if not isinstance(glyph, str) or len(glyph) != 1:
            raise ValueError('unsupported_select_glyph')
        spec['arrow'] = text_spec(glyph, pseudo, font_for_path(requirements, arrow['path'], 'pseudo:before'), arrow['path'] + '::before')
        spec['arrow']['bounds'] = geometry(arrow['bounds'])
        arrow_bounds = spec['arrow']['bounds']
        if arrow_bounds['x'] < border or arrow_bounds['y'] < border or arrow_bounds['x'] + arrow_bounds['width'] > root_bounds['width'] - border or arrow_bounds['y'] + arrow_bounds['height'] > root_bounds['height'] - border:
            raise ValueError('unsupported_select_arrow_overflow')
        spec['arrow']['positioning'] = 'source-absolute-overlay'
    if spec['surface']['bounds'] != root_bounds:
        raise ValueError('unsupported_form_surface_geometry')
    return spec


def prepare_form(reference, font_evidence, discovery, *, logical_id, bindings, file_reference, page_reference):
    report = prepare_candidates(reference, font_evidence, discovery, logical_ids=[logical_id],
        bindings=bindings, file_reference=file_reference)
    report['script'] = None
    if report['status'] != 'PASS':
        return report
    try:
        component = next(item for item in load_json(Path(reference) / 'component_ir.json')['components'] if item['logicalComponentId'] == logical_id)
        spec = translate_form(component, report['fontPreflight']['requirements'])
        payload = {'fileReference': file_reference, 'pageReference': page_reference, 'spec': spec}
        runtime = Path(__file__).with_name('form_candidate.js').read_text(encoding='utf-8')
        capture_runtime = Path(__file__).with_name('native_capture.js').read_text(encoding='utf-8')
        capture_request = {'fileReference': file_reference, 'pageReference': page_reference,
            'logicalId': logical_id, 'evidenceScope': 'production'}
        report['script'] = runtime + '\n' + capture_runtime + '\nconst built = await buildFormCandidate(figma, ' + json.dumps(payload, ensure_ascii=False, allow_nan=False) + ');\nreturn await finishCandidateCapture(figma,built,' + json.dumps(capture_request,ensure_ascii=False) + ');\n'
        report['preparation']['nativeBuilder'] = spec['componentType'].lower() + '-static-v0.1.0'
    except (OSError, ValueError, KeyError, TypeError, StopIteration) as exc:
        report.update(status='FAIL', preparation=None, issues=[{'code': 'unsupported_form_candidate', 'detail': str(exc)}])
    return report
