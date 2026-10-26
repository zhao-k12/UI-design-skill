"""Full Tree input validation and explicit difference-review input.

Generated expectations are a checklist, never proof that somebody viewed it.
"""
from copy import deepcopy
import hashlib
import json


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def require_full_tree(content):
    if 'definitions' in content: raise ValueError('full_tree_required:definitions')

    def data(value):
        if isinstance(value, dict):
            if '$repeat' in value: raise ValueError('full_tree_required:explicit_row_data')
            for child in value.values(): data(child)
        elif isinstance(value, list):
            for child in value: data(child)

    def node(value):
        if not isinstance(value, dict): raise ValueError('full_tree_required:node_object')
        aliases = set(value) & {'use', 'p', 'text', 'from', 'stack', 'ref', 'default'}
        if aliases: raise ValueError('full_tree_required:' + ','.join(sorted(aliases)))
        if not isinstance(value.get('id'), str) or not value['id'] or not value.get('kind'):
            raise ValueError('full_tree_required:explicit_id_and_kind')
        for child in value.get('children', []): node(child)
        for children in value.get('slots', {}).values():
            for child in children: node(child)
        if 'template' in value: node(value['template'])
        for column in value.get('props', {}).get('columns', []):
            if 'cell' in column: node(column['cell'])

    data(content)
    node(content['root'])
    return deepcopy(content)


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
