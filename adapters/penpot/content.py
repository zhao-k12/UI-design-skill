"""Declared native text mappings derived from admitted master readback."""
from copy import deepcopy


def prepare_content(node, native_receipt):
    logical_id = node['componentId']
    props, slots = node.get('props', {}), node.get('slots', {})
    if not props and not slots:
        return []
    names = {
        'action.button.primary.medium': 'official-source / action.button.primary.medium / 0.0',
        'form.input.default.medium': 'official-source / form.input.default.medium / 0.1::placeholder',
        'form.select.default.medium': 'official-source / form.select.default.medium / 0.0.1.0',
    }
    if logical_id not in names:
        raise ValueError('unsupported_component_content: no admitted native text mapping')
    if logical_id.startswith('action.button.'):
        if props or set(slots) != {'label'} or len(slots['label']) != 1:
            raise ValueError('unsupported_component_content: Button supports one text label')
        label = slots['label'][0]
        if label.get('type') != 'Text' or set(label) - {'id', 'type', 'text', 'sourceIds'}:
            raise ValueError('unsupported_component_content: styled/nested label is not mapped')
        text = label['text']
    else:
        prop = 'value' if logical_id == 'form.select.default.medium' else 'placeholder'
        if set(props) != {prop} or slots:
            raise ValueError('unsupported_component_content: only the admitted '+prop+' state is mapped')
        text = props[prop]
    if not isinstance(text, str) or not text or '\n' in text or '\r' in text:
        raise ValueError('unsupported_component_content: nonempty single-line text required')
    evidence = native_receipt.get('nativeEvidence', {})
    targets = [n for n in evidence.get('nodes', []) if n.get('type') == 'text' and n.get('name') == names[logical_id]]
    if len(targets) != 1:
        raise ValueError('missing_native_content_mapping: target must be unique in admitted master')
    target = targets[0]
    fields = ('fontId','fontVariantId','fontFamily','fontWeight','fontStyle','fontSize','lineHeight','letterSpacing','growType')
    if any(field not in target for field in fields) or not isinstance(target.get('characters'), str):
        raise ValueError('missing_native_content_mapping: incomplete text style evidence')
    return [{'name': target['name'], 'originalText': target['characters'], 'text': text,
             'style': {field: deepcopy(target[field]) for field in fields}}]
