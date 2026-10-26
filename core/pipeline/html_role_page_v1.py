"""Compile the source-bound role-permissions composition using HTML v1 roles."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from html_page_v1 import ROOT, fingerprint, read, save

CATALOG = ROOT / 'registries/components/html-v1/role-catalog.json'


def compile_page(source, content, observation, second):
    digest = sha256(source.read_bytes()).hexdigest()
    if any(value.get('sourceSha256') != digest for value in (content, observation, second)):
        raise ValueError('source_hash_mismatch')
    catalog = read(CATALOG)
    if catalog['registryVersion'] != 'html-role-v1.0':
        raise ValueError('registry_version_mismatch')
    if content.get('pattern') != 'role-permissions-v1':
        raise ValueError('unsupported_page_pattern')
    first = {item['id']: item for item in observation['items']}
    scan = {item['id']: item for item in second['items']}
    if len(first) != len(observation['items']) or len(scan) != len(second['items']) or set(first) != set(scan):
        raise ValueError('independent_scan_coverage_mismatch')
    for key, item in first.items():
        other = scan[key]
        if item['region'] != other['region'] or item['traits'] != other['traits']:
            raise ValueError(f'independent_scan_disagrees:{key}')
        if item['decision'] == 'include':
            if not item.get('treeRef') or not item.get('sourceEvidence'):
                raise ValueError(f'source_binding_missing:{key}')
        elif item['decision'] != 'exclude' or not item.get('reason'):
            raise ValueError(f'observation_unresolved:{key}')
    # Every semantic leaf is registered explicitly; a new screenshot cannot inherit old coverage.
    leaves = content['leaves']
    if {item['id'] for item in leaves} != {key for key, item in first.items() if item['decision'] == 'include'}:
        raise ValueError('page_tree_source_coverage')
    mapping = {}
    source_hashes = {role: sha256((ROOT / 'node_modules/view-ui-plus' / value['source']).read_bytes()).hexdigest()
                     for role, value in catalog['components'].items()}
    for leaf in leaves:
        key = leaf['id']
        if first[key]['treeRef'] != leaf['ref']:
            raise ValueError(f'tree_binding_disagrees:{key}')
        for role in leaf['roles']:
            descriptor = catalog['components'].get(role)
            if not descriptor:
                raise ValueError(f'unregistered_component:{role}')
            path = ROOT / 'node_modules/view-ui-plus' / descriptor['source']
            source_hashes[role] = sha256(path.read_bytes()).hexdigest()
        mapping[key] = leaf['roles']
    menus = content['sidebar']
    if len({item['key'] for item in menus}) != len(menus):
        raise ValueError('duplicate_menu_key')
    if sum(item['key'] == content['activeMenu'] for item in menus) != 1:
        raise ValueError('selected_menu_missing')
    for index, item in enumerate(menus):
        if first[f'menu-{index}']['traits']['trailing'] != 'none':
            raise ValueError('flat_menu_has_unobserved_chevron')
        if item['label'] not in scan[f'menu-{index}']['visual']:
            raise ValueError('menu_not_source_bound')
    if len(content['columns']) != 5 or sum(col['span'] for col in content['columns']) != 24:
        raise ValueError('role_table_grid_invalid')
    for index, row in enumerate(content['rows']):
        for col in content['columns']:
            key = col['key']
            if key == 'actions':
                for action_index, action in enumerate(row[key]):
                    claim = f"{action['label']}"
                    if claim not in scan[f'row-{index}-action-{action_index}']['visual']:
                        raise ValueError('row_action_not_source_bound')
            elif str(row[key]) not in scan[f'row-{index}-{key}']['visual']:
                raise ValueError('row_cell_not_source_bound')
    installed = read(ROOT / 'node_modules/view-ui-plus/package.json')
    if catalog['sourceVersion'] != f"view-ui-plus@{installed['version']}":
        raise ValueError('official_package_version_mismatch')
    layout = {'gridColumns': 24, 'shell': 'sider-main-horizontal', 'mainFlow': ['header', 'card'],
              'brandHeaderAlignment': 'official-horizontal-menu-natural-height',
              'toolbar': {'left': ['create', 'search', 'help'], 'right': ['manual-sort', 'alphabetic-sort'], 'wrap': True},
              'table': {'width': 'fill-card', 'columnSpans': [c['span'] for c in content['columns']]},
              'containerPadding': {'value': 24, 'source': 'src/styles/custom.less @padding-lg: containers'}}
    plan = {'sidebar': {'theme': 'dark', 'activeName': content['activeMenu']},
            'header': {'mode': 'horizontal', 'theme': 'light'},
            'brand': {'mode': 'horizontal', 'theme': 'dark'},
            'table': {'stripe': True, 'border': True, 'size': 'default'},
            'buttonIconComposition': 'official-customIcon-prop-and-label-slot',
            'rowActions': {'type': 'text', 'size': 'small'}, 'search': {'search': True, 'readonly': True}}
    tree = {'schemaVersion': 'html-role-v1.0', 'sourceSha256': digest, 'leaves': leaves}
    component_map = {'registryVersion': catalog['registryVersion'], 'sourceRoles': mapping, 'officialSourceSha256': source_hashes}
    ir = {'schemaVersion': 'html-role-v1.0', 'registryVersion': catalog['registryVersion'],
          'registrySha256': fingerprint(catalog), 'sourceSha256': digest,
          'layout': layout, 'componentPlan': plan, 'content': content}
    return {'page_tree': tree, 'layout_tree': layout, 'component_mapping': component_map, 'ui_ir': ir,
            'qa_report': {'status': 'PASS', 'sourceSha256': digest, 'mappedItemCount': len(mapping),
                          'rowCount': len(content['rows']), 'uiIrSha256': fingerprint(ir)}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'content', 'observation', 'independent-scan', 'output-dir'):
        parser.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if not output.is_relative_to((ROOT / 'artifacts').resolve()):
        parser.error('output_must_be_in_artifacts')
    result = compile_page(args.source, read(args.content), read(args.observation), read(args.independent_scan))
    output.mkdir(parents=True, exist_ok=True)
    manifest = {'schemaVersion': 'html-role-v1.0', 'sourceSha256': result['ui_ir']['sourceSha256'],
                'registrySha256': fingerprint(read(CATALOG)), 'compilerSha256': sha256(Path(__file__).read_bytes()).hexdigest()}
    if (output / 'manifest.json').exists() and read(output / 'manifest.json') != manifest:
        parser.error('manifest_changed_use_new_revision')
    save(output / 'manifest.json', manifest)
    for name, value in result.items():
        save(output / f'{name}.json', value)
    print(json.dumps(result['qa_report'], ensure_ascii=False))


if __name__ == '__main__':
    main()
