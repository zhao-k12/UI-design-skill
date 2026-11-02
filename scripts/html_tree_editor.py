"""Mechanical editing of the canonical full content Tree, without a shorthand IR.

Call in one Python batch. The caller supplies every semantic/layout decision.
Only identifiers, JSON formatting and explicitly requested attachments are automatic.
"""
from copy import deepcopy
import json
from pathlib import Path

from html_compact import require_full_tree


def child_links(node):
    for index, child in enumerate(node.get('children', [])):
        yield node['children'], index, child
    for children in node.get('slots', {}).values():
        for index, child in enumerate(children): yield children, index, child
    if 'template' in node: yield node, 'template', node['template']
    if 'tabLabel' in node: yield node, 'tabLabel', node['tabLabel']
    for column in node.get('props', {}).get('columns', []):
        if 'cell' in column: yield column, 'cell', column['cell']


class FullTreeEditor:
    def __init__(self, source_sha256, title, root, *, icons=None):
        self._counter = 0
        self._used = set()
        self._content = {'sourceSha256': source_sha256, 'title': title,
                         'root': self._prepare(deepcopy(root))}
        if icons is not None: self._content['icons'] = deepcopy(icons)

    def _prepare(self, node):
        # Reserve caller IDs before generating any, including later siblings.
        pending = []
        def collect(value):
            if not isinstance(value, dict) or not value.get('kind'):
                raise ValueError('explicit_node_kind_required')
            pending.append(value)
            identifier = value.get('id')
            if identifier is not None:
                if not isinstance(identifier, str) or not identifier or identifier in self._used:
                    raise ValueError('duplicate_or_invalid_node_id')
                self._used.add(identifier)
            for _, _, child in child_links(value): collect(child)
        collect(node)
        for value in pending:
            if 'id' not in value:
                while True:
                    self._counter += 1
                    identifier = f'node-{self._counter:04d}'
                    if identifier not in self._used: break
                self._used.add(identifier); value['id'] = identifier
        require_full_tree({'root': node})
        return node

    def _entry(self, identifier):
        def visit(node, owner=None, key=None):
            if node['id'] == identifier: return node, owner, key
            for container, index, child in child_links(node):
                found = visit(child, container, index)
                if found: return found
        result = visit(self._content['root'])
        if not result: raise ValueError('node_not_found:' + identifier)
        return result

    def add(self, parent_id, kind, *, slot=None, index=None, **fields):
        """Add an explicitly specified canonical node, optionally with full children."""
        parent, _, _ = self._entry(parent_id)
        if parent['kind'] not in ('container', 'component'): raise ValueError('parent_cannot_have_children')
        if slot is not None and (parent['kind'] != 'component' or not isinstance(slot, str) or not slot):
            raise ValueError('named_slot_requires_component')
        children = parent.get('children', []) if slot is None else parent.get('slots', {}).get(slot, [])
        position = len(children) if index is None else index
        if not isinstance(position, int) or isinstance(position, bool) or not 0 <= position <= len(children):
            raise ValueError('invalid_child_position')
        # Prepare on a temporary ID reservation so a rejected add leaves no edits.
        reserved, counter = self._used.copy(), self._counter
        try: value = self._prepare({'kind': kind, **deepcopy(fields)})
        except Exception:
            self._used, self._counter = reserved, counter
            raise
        if slot is None: destination = parent.setdefault('children', [])
        else: destination = parent.setdefault('slots', {}).setdefault(slot, [])
        destination.insert(position, value)
        return value['id']

    def set_properties(self, identifier, properties):
        node, _, _ = self._entry(identifier)
        if node['kind'] != 'component' or not isinstance(properties, dict):
            raise ValueError('component_properties_required')
        if 'columns' in properties: raise ValueError('structural_columns_use_complete_nodes')
        candidate = deepcopy(node)
        candidate.setdefault('props', {}).update(deepcopy(properties))
        require_full_tree({'root': candidate})
        node.clear(); node.update(candidate)

    def set_rows(self, identifier, rows):
        node, _, _ = self._entry(identifier)
        if node.get('component') != 'Table' or not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise ValueError('table_requires_complete_row_objects')
        self.set_properties(identifier, {'data': rows})

    def move(self, identifier, parent_id, *, index=None, slot=None):
        node, owner, key = self._entry(identifier)
        parent, _, _ = self._entry(parent_id)
        if owner is None: raise ValueError('cannot_move_root')
        def contains(value):
            return value is parent or any(contains(child) for _, _, child in child_links(value))
        if contains(node): raise ValueError('cannot_move_into_descendant')
        if parent['kind'] not in ('container', 'component'): raise ValueError('parent_cannot_have_children')
        if slot is not None and (parent['kind'] != 'component' or not isinstance(slot, str) or not slot):
            raise ValueError('named_slot_requires_component')
        children = parent.get('children', []) if slot is None else parent.get('slots', {}).get(slot, [])
        size = len(children) - int(children is owner)
        position = size if index is None else index
        if not isinstance(position, int) or isinstance(position, bool) or not 0 <= position <= size:
            raise ValueError('invalid_child_position')
        if isinstance(owner, list): owner.pop(key)
        else: del owner[key]
        if slot is None: destination = parent.setdefault('children', [])
        else: destination = parent.setdefault('slots', {}).setdefault(slot, [])
        destination.insert(position, node)

    def content(self):
        return require_full_tree(self._content)

    def set_layout_relations(self, relations):
        """Record caller-specified node relationships, without deciding geometry."""
        if not isinstance(relations, list): raise ValueError('layout_relations_must_be_list')
        self._content['layoutRelations'] = deepcopy(relations)

    def write_job(self, path, *, source, observation, scan, viewport=None):
        """Save the existing job format directly; observations remain caller-authored."""
        for document in (observation, scan):
            if document.get('sourceSha256') != self._content['sourceSha256']:
                raise ValueError('source_hash_mismatch')
        result = {'source': str(source), 'content': self.content(),
                  'observation': deepcopy(observation), 'scan': deepcopy(scan)}
        if viewport is not None: result['viewport'] = deepcopy(viewport)
        payload = (json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
        target = Path(path); target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        return target
