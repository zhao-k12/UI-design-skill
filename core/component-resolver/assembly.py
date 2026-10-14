"""Source-bound instance payloads and Section-local replacement patches."""
from __future__ import annotations

import argparse
import copy
import importlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError
from validators.ui_ir import load_json, validate_document
from validators.structure.gate import builder

resolver = importlib.import_module('core.component-resolver.resolver')
primitive_mapping = importlib.import_module('core.component-resolver.primitive_mapping')
slot_layout = importlib.import_module('core.component-resolver.slot_layout')
table_header = importlib.import_module('core.component-resolver.table_header')
ROOT = Path(__file__).resolve().parents[2]
SLOTS = ('leading-icon', 'trailing-icon', 'label', 'control', 'content', 'actions')
PROPS = {'Input': {'placeholder', 'value'}, 'Select': {'placeholder', 'value'},
         'Button': set(), 'Table': {'headers'}, 'Text': {'text'}}


def normalize_fixed_native_content(node, scope, depth=0, *, table_records=None):
    if depth != 0:
        raise ValueError('unsupported_component: nested fixed-native-content is not admitted')
    if 'data' in scope:
        valid = (not node['props'] and not node['slots']
                 and table_records == scope['data'])
    elif table_records is not None:
        valid = False
    elif 'text' in scope:
        valid = (not node['props'] and set(node['slots']) == {'label'}
                 and len(node['slots']['label']) == 1
                 and node['slots']['label'][0].get('type') == 'Text'
                 and node['slots']['label'][0].get('text') == scope['text'])
    elif 'placeholder' in scope:
        valid = node['props'] == {'placeholder': scope['placeholder']} and not node['slots']
    elif 'selectedText' in scope:
        valid = node['props'] == {'value': scope['selectedText']} and not node['slots']
    else:
        raise ValueError('unsupported_component: unknown fixed-native-content scope')
    if not valid:
        raise ValueError('unsupported_component: content is outside the admitted fixed-native-content scope')
    result = copy.deepcopy(node)
    result['slots'] = {}
    result['props'] = {}
    return result


def assemble(analysis, page_tree, source_root, review, layout_plan, decisions, registry,
             token_registry, content, *, previous=None, icon_registry=None, source_geometry=None,
             icon_sources=None, allow_text_primitives=False, allow_test_fixtures=False):
    mapping = primitive_mapping.resolve(analysis, page_tree, source_root, review, layout_plan, decisions,
                               registry, token_registry, allow_text_primitives=allow_text_primitives,
                               allow_test_fixtures=allow_test_fixtures)
    result = {'version': '0.1.0', 'stage': 'component-assembly', 'status': mapping['status'],
              'readyForAdapter': False, 'nativeInstancesCreated': False,
              'sourcePlacementVerified': False,
              'mappingSha256': builder.fingerprint(mapping), 'mapping': mapping,
              'operations': [], 'sections': {}, 'issues': [], 'changedSections': []}
    if mapping['status'] != 'PASS':
        return result
    try:
        Draft202012Validator(load_json(ROOT / 'schemas/component-content.schema.json')).validate(content)
        if content['mappingSha256'] != result['mappingSha256']:
            raise ValueError('Content belongs to another component mapping')
        result['iconRegistrySha256'] = icon_registry.fingerprint if icon_registry else None
        result['sourceGeometrySha256'] = source_geometry.fingerprint if source_geometry else None
        if source_geometry and source_geometry.registry_sha256 != registry.fingerprint:
            raise ValueError('Source geometry belongs to another registry')
        entries = {entry['sourceId']: entry for entry in content['items']}
        rows = {row['sourceId']: row for row in mapping['rows']}
        if len(entries) != len(content['items']) or set(entries) != set(rows):
            raise ValueError('Exactly one content record per semantic item is required')
        evidence = {e['id']: e for e in analysis['evidence']}
        skeleton = mapping['layoutReport']['engineReport']['skeleton']
        result['skeletonSha256'] = builder.fingerprint(skeleton)
        result['pageTreeSha256'] = builder.fingerprint(page_tree)
        if previous is not None:
            if previous.get('sourceGeometrySha256') != result['sourceGeometrySha256']:
                raise ValueError('Source geometry migration requires a new assembly baseline')
            if previous.get('status') != 'PASS' or previous.get('skeletonSha256') != result['skeletonSha256'] or previous.get('pageTreeSha256') != result['pageTreeSha256']:
                raise ValueError('Previous assembly is not PASS for this exact existing skeleton')
            if previous.get('stateSha256') != state_digest(previous):
                raise ValueError('Previous assembly state was modified')
            if previous['mapping']['registrySha256'] != mapping['registrySha256'] or previous.get('iconRegistrySha256') != result['iconRegistrySha256']:
                raise ValueError('Registry migration requires an explicit new assembly baseline')
        def claim_value(claim, row):
            if not set(claim['evidence']).intersection(row['evidence']):
                raise ValueError('Injected content must cite the item source evidence')
            quotes = [evidence[ref]['quote'] for ref in claim['evidence']]
            if not any(claim['text'] in quote for quote in quotes):
                raise ValueError('Injected text is not present in the original source')
            return claim['text']
        def payload(spec, row, identifier, depth=0):
            if depth > 12:
                raise ValueError('Slot nesting exceeds the V0.1 limit')
            if source_geometry is not None and depth > 0:
                raise ValueError('Nested source placement requires an explicit slot envelope')
            chosen = registry.resolve(spec['componentId'], spec['variant'])
            descriptor = chosen['descriptor']
            node = {'id': identifier, 'type': 'ComponentInstance',
                    'componentId': chosen['logicalId'], 'variant': chosen['variant'],
                    'sourceIds': [row['sourceId']], 'props': {}, 'slots': {}}
            for key, claim in spec['props'].items():
                if key not in PROPS.get(descriptor['componentType'], set()):
                    raise ValueError('Unsupported content property for component type')
                node['props'][key] = ([claim_value(c, row) for c in claim] if isinstance(claim, list)
                                      else claim_value(claim, row))
            for slot, children in spec['slots'].items():
                if slot not in descriptor['slots']:
                    raise ValueError('Slot is not declared by the admitted component')
                nodes = []
                for index, child in enumerate(children):
                    child_id = identifier + '.' + slot + '.' + str(index)
                    expected = {'leading-icon': {'icon'}, 'trailing-icon': {'icon'},
                                'label': {'text'}, 'control': {'instance'},
                                'content': {'text', 'instance'}, 'actions': {'instance'}}
                    if child['kind'] not in expected[slot]:
                        raise ValueError('Slot child kind is incompatible with slot role')
                    if child['kind'] == 'text':
                        nodes.append({'id': child_id, 'type': 'Text', 'sourceIds': [row['sourceId']],
                                      'text': claim_value(child['claim'], row)})
                    elif child['kind'] == 'icon':
                        if icon_registry is None:
                            raise ValueError('missing_icon: no loaded official icon registry')
                        icon_registry.resolve(child['iconId'])
                        nodes.append({'id': child_id, 'type': 'IconInstance',
                                      'iconId': child['iconId'], 'sourceIds': [row['sourceId']]})
                    else:
                        nodes.append(payload(child['instance'], row, child_id, depth+1))
                node['slots'][slot] = nodes
            scope = descriptor.get('contentScope')
            if scope and 'data' not in scope:
                # claim_value already verified the label against source evidence.
                node = normalize_fixed_native_content(node, scope, depth)
            return node
        boxes = {}
        def walk(node):
            boxes[node['id']] = node['box']
            for child in node.get('children', []):
                walk(child)
        walk(skeleton)
        for source_id, row in rows.items():
            entry = entries[source_id]
            if 'tableRecords' in entry and row['componentType']!='Table':raise ValueError('Static records belong only to a Table')
            if 'cellDirection' in entry and 'cellSlots' not in entry:
                raise ValueError('Cell direction requires an explicit Cell slot composition')
            if any(k in entry for k in ('cellMain','cellOrder')) and 'cellSlots' not in entry:
                raise ValueError('Cell alignment/order requires explicit Cell slots')
            spec = {'componentId': row['componentId'], 'variant': row['variant'],
                    'props': entry['props'], 'slots': entry['slots']}
            identifier=row['cellId'] + '.instance' if source_geometry else row['cellId']
            if row.get('primitive')=='Text':
                if set(entry['props'])!={'text'} or entry['slots'] or 'textStyle' not in entry:
                    raise ValueError('Text primitive requires one source claim, no slots, and explicit token style')
                node={'id':identifier,'type':'Text','sourceIds':[source_id],
                      'text':claim_value(entry['props']['text'],row),'style':copy.deepcopy(entry['textStyle'])}
            else:
                if 'textStyle' in entry:raise ValueError('Primitive style cannot override an admitted component')
                node = payload(spec, row, identifier)
                scope = registry.inspect(row['componentId']).get('contentScope')
                table_headers = None
                if scope and 'data' in scope:
                    if 'tableHeaderStyle' in entry:
                        table_headers = node['props'].pop('headers', None)
                        if not table_headers:
                            raise ValueError('Table header composition needs source-bound header claims')
                    if source_geometry is None or 'tableRecords' not in entry:
                        raise ValueError('unsupported_component: fixed Table requires admitted source geometry and records')
                    source = source_geometry.source_component(row['componentId'], row['variant'])
                    expected = {key: scope[key] for key in ('showHeader', 'border', 'stripe', 'columns', 'data')}
                    if source['props'] != expected:
                        raise ValueError('unsupported_component: Table source configuration is outside admitted scope')
                    records = [{key: claim_value(claim, row) for key, claim in record.items()}
                               for record in entry['tableRecords']]
                    node = normalize_fixed_native_content(node, scope, table_records=records)
            box = copy.deepcopy(boxes[row['cellId']])
            node['layout'] = {axis: {'mode': 'fixed', 'value': box[axis]} for axis in ('width', 'height')}
            if 'textSize' in entry:
                if row.get('primitive')!='Text':raise ValueError('Text size cannot override admitted component geometry')
                if any(entry['textSize'][axis]>box[axis] for axis in ('width','height')):raise ValueError('Measured Text exceeds Cell envelope')
                node['layout']={axis:{'mode':'fixed','value':entry['textSize'][axis]} for axis in ('width','height')}
            placement = (source_geometry.place(node, box) if row.get('primitive')!='Text' else
                         {'instance':node,'instanceBox':{'x':box['x'],'y':box['y'],**{a:node['layout'][a]['value'] for a in ('width','height')}}}) if source_geometry else None
            if placement:
                node = placement['instance']
            if row.get('primitive') != 'Text':
                scope = registry.inspect(row['componentId']).get('contentScope')
                if scope and (node['layout']['width'] != {'mode': 'fixed', 'value': scope['width']}
                              or node['layout']['height'] != {'mode': 'fixed', 'value': scope['height']}):
                    raise ValueError('unsupported_component: geometry is outside the admitted fixed-native-content scope')
            issues = validate_document({'uiIrVersion': '0.1.0', 'documentId': 'assembly-validation',
                                        'pages': [{'id': 'assembly-page', 'type': 'Page', 'children': [node]}]})
            if issues:
                raise ValueError('Instance payload violates UI-IR: '+str(issues))
            references=resolver.tokens.check_references({'uiIrVersion':'0.1.0','documentId':'assembly-validation',
                'pages':[{'id':'assembly-page','type':'Page','children':[node]}]},token_registry)
            if references:raise ValueError('Content token references are invalid: '+str(references))
            section = result['sections'].setdefault(row['sectionId'], [])
            section.append({'operation': 'replace-cell', 'targetCellId': row['cellId'],
                            'sourceId': source_id, 'box': box, 'instance': node})
            if placement:
                section[-1]['instanceBox'] = placement['instanceBox']
                section[-1]['replacement'] = {
                    'id': row['cellId'], 'type': 'Frame', 'sourceIds': [source_id],
                    'layout': {axis: {'mode': 'fixed', 'value': box[axis]} for axis in ('width', 'height')},
                    'children': [copy.deepcopy(node)]}
            if 'cellSlots' in entry:
                if not source_geometry:
                    raise ValueError('Cell slots require admitted source geometry')
                role = ('content' if row.get('primitive') == 'Text' or row['componentType'] == 'Table'
                        else 'actions' if row['componentType'] == 'Button' else 'control')
                slots = copy.deepcopy(entry['cellSlots'])
                if role in slots:
                    raise ValueError('Cell slots cannot replace the mapped primary role')
                slots[role] = [copy.deepcopy(node)]
                quotes = [evidence[ref]['quote'] for ref in row['evidence']]
                section[-1]['replacement'] = slot_layout.compose(
                    row['cellId'], box, source_id, slots, source_geometry, registry,
                    icon_registry, token_registry, quotes, icon_sources or {},
                    direction=entry.get('cellDirection', 'horizontal'),main=entry.get('cellMain','start'),order=entry.get('cellOrder'))
                # Role layout determines the actual child position; it is verified
                # through native readback rather than a stale Cell-origin box.
                section[-1]['instanceBox']=None
                section[-1]['placementMode']='role-layout'
            if 'tableHeaderStyle' in entry:
                if not source_geometry or row['componentType']!='Table' or 'cellSlots' in entry:
                    raise ValueError('Table header composition requires a measured Table without competing Cell slots')
                headers=(table_headers if table_headers is not None else
                         section[-1]['instance'].get('props',{}).pop('headers',None))
                if not headers:raise ValueError('Table header composition needs source-bound header claims')
                replacement,offset=table_header.compose(row['cellId'],box,section[-1]['instance'],headers,
                    entry['tableHeaderStyle'],source_geometry,token_registry)
                section[-1]['replacement']=replacement;section[-1]['instanceBox']['y']+=offset
                document={'uiIrVersion':'0.1.0','documentId':'header-validation','pages':[{'id':'header-page','type':'Page','children':[replacement]}]}
                if validate_document(document) or resolver.tokens.check_references(document,token_registry):
                    raise ValueError('Invalid table header primitives or tokens')
        for section_id, operations in result['sections'].items():
            if previous is None or previous['sections'].get(section_id) != operations:
                result['changedSections'].append(section_id)
                result['operations'].extend(copy.deepcopy(operations))
        result['status'] = 'PASS'
        result['sourcePlacementVerified'] = source_geometry is not None
        # These payloads are logical instances, never a claim that a platform ran them.
        result['readyForAdapter'] = mapping['readyForAssembly'] and source_geometry is not None
        result['contentSha256'] = builder.fingerprint(content)
        result['stateSha256'] = state_digest(result)
    except (ValueError, KeyError, TypeError, ValidationError) as exc:
        code = getattr(exc, 'code', 'invalid_component_content')
        if str(exc).startswith('missing_icon:'):
            code = 'missing_icon'
        result.update(status='Missing' if code in ('missing_icon', 'missing_component') else 'FAIL',
                      operations=[], sections={}, changedSections=[],
                      issues=[{'code': code, 'message': str(exc)}])
    return result


def state_digest(result):
    state = {key: result[key] for key in ('skeletonSha256', 'pageTreeSha256', 'sections')}
    if result.get('sourceGeometrySha256') is not None:
        state['sourceGeometrySha256'] = result['sourceGeometrySha256']
    return builder.fingerprint(state)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ('analysis', 'page_tree', 'layout_plan', 'decisions', 'content'):
        cli.add_argument(name, type=Path)
    cli.add_argument('--source-root', type=Path, required=True)
    cli.add_argument('--review', type=Path)
    cli.add_argument('--previous', type=Path)
    cli.add_argument('--component-ir', type=Path, help='Exact admitted source geometry bundle')
    cli.add_argument('--allow-text-primitives',action='store_true',help='Explicitly enable source-bound static UI-IR Text')
    cli.add_argument('--output', type=Path, required=True)
    cli.add_argument('--allow-test-fixtures', action='store_true')
    args = cli.parse_args()
    a = load_json(args.analysis)
    inputs = [getattr(args, n) for n in ('analysis', 'page_tree', 'layout_plan', 'decisions', 'content')]
    inputs.extend(p for p in (args.review, args.previous, args.component_ir) if p)
    inputs.extend(args.source_root / s['path'] for s in a['sources'])
    if args.output.resolve() in {p.resolve() for p in inputs}:
        cli.error('Output cannot overwrite inputs or previous checkpoint')
    registry = resolver.registry_module.ComponentRegistry(load_json(ROOT / 'registries/components/catalog.json'),
                                                         load_json(ROOT / 'registries/components/fidelity-reports.json'))
    icon_module = importlib.import_module('core.icon-resolver.registry')
    icon_lock = load_json(ROOT / 'registries/icons/current.json')
    icons = icon_module.IconRegistry(load_json(ROOT / 'registries/icons/snapshots' / icon_lock['snapshotSha256'] / 'registry.json'))
    content = load_json(args.content)
    icon_sources = {}
    for item in content.get('items', []):
        for children in item.get('cellSlots', {}).values():
            for child in children:
                if child.get('type') == 'IconInstance':
                    identifier = child['iconId']
                    descriptor = icons.resolve(identifier)['descriptor']
                    icon_sources[identifier] = (ROOT / 'registries/icons/objects' / (descriptor['svgSha256']+'.svg')).read_bytes()
    geometry_module = importlib.import_module('core.component-resolver.placement')
    geometry = geometry_module.SourceGeometry(load_json(args.component_ir), registry) if args.component_ir else None
    result = assemble(a, load_json(args.page_tree), args.source_root,
                      load_json(args.review) if args.review else None, load_json(args.layout_plan),
                      load_json(args.decisions), registry,
                      resolver.tokens.TokenRegistry(load_json(ROOT / 'registries/tokens/default.json')),
                      content, previous=load_json(args.previous) if args.previous else None,
                      icon_registry=icons, icon_sources=icon_sources, source_geometry=geometry, allow_text_primitives=args.allow_text_primitives,
                      allow_test_fixtures=args.allow_test_fixtures)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print('Assembly: '+result['status'])
    return 0 if result['readyForAdapter'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
