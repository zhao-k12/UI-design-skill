"""Lossless authoring aliases and explicit difference-review input.

Generated expectations are a checklist, never proof that somebody viewed it.
"""
from copy import deepcopy
import hashlib
import json


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def expand_tree(content):
    result = deepcopy(content)
    definitions = result.pop('definitions', {})

    def node(value, path, chain=()):
        if isinstance(value, str):
            value = {'text': value}
        value = deepcopy(value)
        if 'ref' in value:
            ref = value.pop('ref')
            if ref not in definitions or ref in chain:
                raise ValueError('tree_reference_missing_or_cyclic:' + ref)
            base = deepcopy(definitions[ref]); base.update(value)
            return node(base, path, chain + (ref,))
        if 'use' in value:
            value['kind'] = 'component'; value['component'] = value.pop('use')
        if 'stack' in value:
            value['kind'] = 'container'
            layout = deepcopy(value.get('layout', {})); layout['direction'] = value.pop('stack')
            for key in ('gap', 'padding', 'justify', 'align', 'wrap', 'fill', 'span', 'minHeight'):
                if key in value: layout[key] = value.pop(key)
            value['layout'] = layout
        if 'p' in value:
            if 'props' in value: raise ValueError('ambiguous_tree_props')
            value['props'] = value.pop('p')
        if 'from' in value:
            if 'sourceGroups' in value: raise ValueError('ambiguous_tree_sources')
            value['sourceGroups'] = value.pop('from')
        if 'text' in value:
            text = value.pop('text')
            if value.get('kind') == 'component':
                if 'children' in value: raise ValueError('ambiguous_tree_children')
                value['children'] = [{'text': text}]
            elif 'kind' not in value:
                value.update(kind='text', value=text)
        if 'default' in value: value['defaultValue'] = value.pop('default')
        value.setdefault('id', path)
        for key in ('children',):
            if key in value: value[key] = [node(item, f'{path}.{key}.{i}', chain) for i, item in enumerate(value[key])]
        if 'slots' in value:
            value['slots'] = {key: [node(item, f'{path}.slot.{key}.{i}', chain) for i, item in enumerate(items)] for key, items in value['slots'].items()}
        if 'template' in value: value['template'] = node(value['template'], path + '.template', chain)
        for i, col in enumerate(value.get('props', {}).get('columns', [])):
            if 'cell' in col: col['cell'] = node(col['cell'], f'{path}.column.{i}', chain)
        return value

    result['root'] = node(result['root'], 'root')
    return result


def merge_patch(target, patch):
    """Recursive configuration update; arrays replace explicitly, false is data."""
    if not isinstance(target, dict) or not isinstance(patch, dict): return deepcopy(patch)
    result = deepcopy(target)
    for key, value in patch.items():
        result[key] = merge_patch(result.get(key), value)
    return result


def delta_review(document, plan):
    if document.get('reviewMode') != 'delta-v1': return document
    if document.get('issues') != []: raise ValueError('review_issues_unresolved')
    if set(document.get('checkedStages', [])) != {'tree', 'skeleton', 'component', 'delivery'}:
        raise ValueError('stage_visual_confirmation_required')
    confirmed = document.get('confirmedGroups', [])
    if len(confirmed) != len(set(confirmed)) or set(confirmed) - set(plan['groups']):
        raise ValueError('review_group_unknown_or_duplicate')
    reusable = set(plan.get('reusableGroups', []))
    if set(confirmed) | reusable != set(plan['groups']): raise ValueError('review_group_confirmation_required')
    items = []; rules = []
    for key, group in plan['groups'].items():
        for item in group['items']:
            identifier = item['id']
            if item['decision'] == 'exclude': items.append({'id': identifier, 'exclusionStatus': 'PASS'})
            else:
                rule = group['rules'][identifier]; rules.append(rule)
                items.append({'id': identifier, 'variantRef': rule['id'], 'renderedTraits': item['traits']})
    relations = document.get('relationChecks', [])
    return {**document, 'reviewMode': 'batched-v2', 'items': items, 'variantRules': rules,
            'stageChecks': {key: 'PASS' for key in document['checkedStages']}, 'relationChecks': relations,
            'confirmationMeaning': 'Reviewer matched current source and screenshots, including group exceptions; expectations alone do not pass.'}
