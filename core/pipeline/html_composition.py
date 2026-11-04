"""Compile a declarative content tree without selecting a business-page template."""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import base64
import binascii
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / 'node_modules/view-ui-plus'
VERSION = 'html-composition-v1'
SPACING = {'none': 0, 'xs': 8, 'sm': 12, 'md': 16, 'lg': 24}
DESIGN_ROLES = {'page-shell', 'sidebar', 'brand', 'topbar', 'topbar-tool', 'topbar-tool-large', 'topbar-user',
                'breadcrumb', 'search-panel', 'search-grid', 'search-field', 'search-label', 'search-actions',
                'table-panel', 'table-toolbar', 'table-actions', 'toolbar-notice', 'light-tag', 'row-actions', 'row-actions-left', 'row-action', 'tab-label', 'tab-count', 'pagination', 'form-section', 'form-section-title', 'form-grid', 'form-grid-three', 'detail-add', 'detail-action', 'summary-header', 'summary-title', 'summary-meta', 'progress-steps', 'page-actions'}


def validate_project_logo(uri):
    if not isinstance(uri,str): raise ValueError('project_logo_data_required')
    match=re.fullmatch(r'data:(image/(?:png|jpeg|webp|svg\+xml));base64,([A-Za-z0-9+/=]+)',uri)
    if not match: raise ValueError('project_logo_data_invalid')
    try: raw=base64.b64decode(match.group(2),validate=True)
    except (ValueError,binascii.Error): raise ValueError('project_logo_data_invalid') from None
    if not raw or len(raw)>5*1024*1024: raise ValueError('project_logo_size_invalid')
    mime=match.group(1)
    if mime=='image/png' and not raw.startswith(b'\x89PNG\r\n\x1a\n'): raise ValueError('project_logo_format_invalid')
    if mime=='image/jpeg' and not raw.startswith(b'\xff\xd8\xff'): raise ValueError('project_logo_format_invalid')
    if mime=='image/webp' and not (raw.startswith(b'RIFF') and raw[8:12]==b'WEBP'): raise ValueError('project_logo_format_invalid')
    if mime=='image/svg+xml':
        if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper(): raise ValueError('project_logo_svg_unsafe')
        try: root=ET.fromstring(raw)
        except ET.ParseError: raise ValueError('project_logo_format_invalid') from None
        if root.tag.split('}')[-1]!='svg': raise ValueError('project_logo_format_invalid')
        for node in root.iter():
            if node.tag.split('}')[-1].lower() in ('script','foreignobject','style','image','use'):
                raise ValueError('project_logo_svg_unsafe')
            for key,value in node.attrib.items():
                name=key.split('}')[-1].lower()
                if name.startswith('on') or name in ('href','style') or 'url(' in value.lower():
                    raise ValueError('project_logo_svg_unsafe')
    return mime

def digest(path): return sha256(path.read_bytes()).hexdigest()
def read(path): return json.loads(path.read_text(encoding='utf-8'))
def save(path, value): path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def table_column_coverage(nodes, observation, scan):
    """Compare independently supplied visible table headings with the compiled tree.

    This verifies agreement among supplied facts, not their provenance or any
    unlabelled selection columns, row values, grouped headings, or pixels.
    """
    tables = {key: node for key, node in nodes.items()
              if node.get('kind') == 'component' and node.get('component') == 'Table'}
    first_present, second_present = 'tableColumns' in observation, 'tableColumns' in scan
    if first_present != second_present:
        raise ValueError('table_columns_both_observations_required')
    first = observation.get('tableColumns', {})
    second = scan.get('tableColumns', {})
    if not isinstance(first, dict) or not isinstance(second, dict):
        raise ValueError('table_columns_inventory_must_be_object')
    if set(first) != set(second):
        raise ValueError('table_columns_inventory_coverage_mismatch')
    if set(first) - set(tables):
        raise ValueError('table_columns_inventory_unknown_table')
    for key in first:
        headings, scanned = first[key], second[key]
        if (not isinstance(headings, list) or not headings
                or any(not isinstance(v, str) or not v.strip() for v in headings)
                or not isinstance(scanned, list) or not scanned
                or any(not isinstance(v, str) or not v.strip() for v in scanned)):
            raise ValueError(f'table_columns_inventory_invalid:{key}')
        if headings != scanned:
            raise ValueError(f'table_columns_observation_disagrees:{key}')
        columns = tables[key].get('props', {}).get('columns', [])
        if not isinstance(columns, list) or any(
                not isinstance(col, dict) or 'children' in col for col in columns):
            raise ValueError(f'table_columns_grouped_or_invalid:{key}')
        actual = [col['title'] for col in columns if 'title' in col]
        if any(not isinstance(title, str) for title in actual) or headings != actual:
            raise ValueError(f'table_columns_tree_mismatch:{key}')
    unchecked = sorted(set(tables) - set(first))
    checked = sorted(first)
    return {'status': ('not_applicable' if not tables else 'partial' if checked and unchecked
                       else 'not_checked' if unchecked else 'checked'),
            'checkedTables': checked, 'uncheckedTables': unchecked,
            'scope': 'visible titled table columns only; source accuracy and visual review are not verified'}

def official_catalog():
    if read(PACKAGE / 'package.json')['version'] != '1.3.24':
        raise ValueError('official_package_version_mismatch')
    index = PACKAGE / 'src/components/index.js'
    exports = dict(re.findall(r"export \{ default as (\w+) \} from '\./([^']+)';", index.read_text(encoding='utf-8')))
    # Lock the package's actual source, including child components and imported styles.
    source = sha256()
    for path in sorted((PACKAGE / 'src').rglob('*')):
        if path.is_file():
            source.update(path.relative_to(PACKAGE).as_posix().encode())
            source.update(path.read_bytes())
    return {'sourceVersion': 'view-ui-plus@1.3.24', 'sourceSha256': source.hexdigest(),
            'exportIndexSha256': digest(index), 'exports': exports}

def compile_tree(source, content, observation, scan):
    source_hash = digest(source)
    if any(value.get('sourceSha256') != source_hash for value in (content, observation, scan)):
        raise ValueError('source_hash_mismatch')
    first = {item['id']: item for item in observation['items']}
    second = {item['id']: item for item in scan['items']}
    if not first or len(first) != len(observation['items']) or len(second) != len(scan['items']) or first.keys() != second.keys():
        raise ValueError('independent_scan_coverage_mismatch')
    for key, item in first.items():
        if item.get('region') != second[key].get('region') or item.get('traits') != second[key].get('traits'):
            raise ValueError(f'independent_scan_disagrees:{key}')
        if not item.get('sourceEvidence') or not second[key].get('visual'):
            raise ValueError(f'source_evidence_missing:{key}')
        if item.get('decision') == 'include':
            if not item.get('treeRef'): raise ValueError(f'tree_binding_missing:{key}')
        elif item.get('decision') != 'exclude' or not item.get('reason'):
            raise ValueError(f'observation_unresolved:{key}')
    catalog = official_catalog()
    nodes, covered, components, icons, layouts, assets = {}, set(), set(), set(content.get('icons', [])), {}, set()
    def record_icon(value):
        if isinstance(value, str): icons.add(value)
        elif not isinstance(value, dict) or not isinstance(value.get('bind'), str) or not content.get('icons'):
            raise ValueError('bound_icon_requires_declared_source_icons')
    def visit(node):
        if not isinstance(node, dict) or not isinstance(node.get('id'), str) or not node['id']:
            raise ValueError('node_id_required')
        key = node['id']
        if 'designRole' in node and (node.get('kind') not in ('container', 'component') or not isinstance(node['designRole'], str) or node['designRole'] not in DESIGN_ROLES):
            raise ValueError('unsupported_design_role')
        if node.get('designRole') == 'pagination':
            if node.get('component') != 'Page': raise ValueError('pagination_role_requires_page')
            icons.update(('arrow-left-s-line', 'arrow-right-s-line', 'arrow-down-s-line'))
        if node.get('designRole') in ('search-panel', 'form-section'):
            icons.update(('arrow-down-s-line', 'calendar-line'))
        if 'semantic' in node and (node.get('kind') != 'container' or node['semantic'] != 'navigation'):
            raise ValueError('unsupported_semantic_landmark')
        if 'ariaLabel' in node and (node.get('semantic') != 'navigation' or not isinstance(node['ariaLabel'], str) or not node['ariaLabel'].strip()):
            raise ValueError('invalid_navigation_label')
        if 'current' in node and (node.get('kind') != 'component' or node.get('component') != 'Link' or node['current'] is not True):
            raise ValueError('invalid_current_link')
        if key in nodes: raise ValueError(f'duplicate_node_id:{key}')
        nodes[key] = node
        for source_id in node.get('sourceIds', []):
            if source_id not in first or first[source_id]['decision'] != 'include':
                raise ValueError(f'unknown_source_id:{source_id}')
            covered.add(source_id)
        kind = node.get('kind')
        if 'equalGapColumns' in node:
            if node.get('component') != 'Table' or not isinstance(node['equalGapColumns'], bool):
                raise ValueError('equal_gap_requires_table_boolean')
            columns=node.get('props',{}).get('columns',[])
            if node['equalGapColumns'] and (not columns or any(col.get('width') or col.get('minWidth') or col.get('fitContent') is False or col.get('children') for col in columns)):
                raise ValueError('equal_gap_incompatible_with_fixed_columns')
            if node['equalGapColumns']:
                keys=[col.get('key',col.get('type')) for col in columns]
                if any(not isinstance(key,str) or not key for key in keys) or len(set(keys))!=len(keys):
                    raise ValueError('equal_gap_requires_unique_column_keys')
        if kind == 'component':
            name = node.get('component')
            if name not in catalog['exports']:
                raise ValueError(f'official_component_unavailable:{name}')
            components.add(name)
            for props in (node.get('props', {}), node.get('defaultProps', {})):
                if any(k in ('style', 'class', 'innerHTML') or k.lower().startswith('on') for k in props):
                    raise ValueError(f'component_visual_or_event_override:{key}')
                if name == 'Table':
                    for col in props.get('columns', []):
                        if 'render' in col: raise ValueError('use_declarative_column_cell')
                        if col.get('cell'): visit(col['cell'])
            if node.get('icon'): record_icon(node['icon'])
        elif kind == 'container':
            layout = node.get('layout', {})
            allowed = {'direction','gap','padding','justify','align','wrap','fill','span','minHeight'}
            if set(layout) - allowed: raise ValueError(f'unsupported_layout_property:{key}')
            if 'minHeight' in layout and layout['minHeight'] != 'viewport': raise ValueError('unsupported_min_height')
            if layout.get('direction', 'vertical') not in ('horizontal','vertical'):
                raise ValueError('invalid_layout_direction')
            for part in ('gap','padding'):
                if layout.get(part, 'none') not in SPACING: raise ValueError('use_official_spacing_token')
            if layout.get('justify', 'start') not in ('start','end','center','space-between') or layout.get('align', 'stretch') not in ('start','end','center','stretch'):
                raise ValueError('invalid_layout_alignment')
            if 'span' in layout and (not isinstance(layout['span'], int) or not 1 <= layout['span'] <= 24):
                raise ValueError('invalid_grid_span')
            layouts[key] = layout
        elif kind == 'icon': record_icon(node['name'])
        elif kind == 'asset':
            if node.get('name') in ('default-logo', 'default-avatar'): assets.add(node['name'])
            elif node.get('name') == 'project-logo': validate_project_logo(node.get('dataUri'))
            else: raise ValueError('unknown_design_asset')
        elif kind == 'repeat':
            if not isinstance(node.get('items'), (list,dict)): raise ValueError('repeat_items_required')
            visit(node['template'])
        elif kind != 'text': raise ValueError(f'unsupported_node_kind:{kind}')
        if 'tabLabel' in node:
            if node.get('component') != 'TabPane': raise ValueError('tab_label_requires_tab_pane')
            visit(node['tabLabel'])
        for child in node.get('children', []): visit(child)
        for children in node.get('slots', {}).values():
            for child in children: visit(child)
    visit(content['root'])
    column_coverage = table_column_coverage(nodes, observation, scan)
    relations = content.get('layoutRelations', [])
    if not isinstance(relations, list): raise ValueError('layout_relations_must_be_list')
    relation_ids = set()
    for relation in relations:
        if not isinstance(relation, dict) or not relation.get('id') or relation['id'] in relation_ids:
            raise ValueError('layout_relation_id_invalid')
        relation_ids.add(relation['id'])
        kind = relation.get('kind')
        keys = {'surface-cover': ('surface','extent'), 'edge-align': ('first','second'), 'minimum-gap': ('first','second'),
                'vertical-center': ('first','second')}.get(kind)
        if keys is None: raise ValueError('unknown_layout_relation_kind')
        if not relation.get('sourceEvidence'): raise ValueError('layout_relation_source_required')
        if any(relation.get(key) not in nodes for key in keys): raise ValueError('layout_relation_node_missing')
        if kind == 'surface-cover' and relation.get('axis','both') not in ('both','vertical'):
            raise ValueError('layout_relation_axis_invalid')
        if kind == 'edge-align' and relation['first'] == relation['second']:
            raise ValueError('boundary_requires_distinct_regions')
        if kind == 'edge-align' and any(relation.get(key) not in ('left','right') for key in ('firstEdge','secondEdge')):
            raise ValueError('layout_relation_edge_required')
        if kind == 'minimum-gap' and (relation['first'] == relation['second'] or relation.get('axis') not in ('horizontal','vertical') or relation.get('minimum') not in SPACING):
            raise ValueError('layout_relation_minimum_gap_invalid')
    # A recognizable header + horizontal navigation + side menu needs explicit
    # surface/boundary contracts. This is component composition, not page naming.
    menus = [n for n in nodes.values() if n.get('component') == 'Menu']
    shell = ('Header' in components and any(n.get('props',{}).get('mode') == 'horizontal' for n in menus)
             and any(n.get('props',{}).get('mode','vertical') == 'vertical' for n in menus))
    # Alignment depends on the selected official combination. Equal centers
    # are enforced only when explicitly declared, not inferred from components.
    if shell and not {'surface-cover','edge-align'}.issubset({r['kind'] for r in relations}):
        raise ValueError('shell_surface_and_boundary_relations_required')
    included = {key for key, item in first.items() if item['decision'] == 'include'}
    if covered != included: raise ValueError(f'page_tree_source_coverage:{sorted(included-covered)}')
    mapping = {key: node.get('component', node['kind']) for key,node in nodes.items()}
    layout_tree = {'gridColumns': 24, 'spacingSource': 'src/styles/custom.less @padding-*', 'nodes': layouts,
                   'tableSizing': 'official-content-fit-before-screenshots'}
    ir = {'schemaVersion': VERSION, 'sourceSha256': source_hash, 'officialSource': catalog,
          'root': content['root'], 'layout': layout_tree, 'requiredIcons': sorted(icons),
          'usedComponents': sorted(components), 'requiredAssets': sorted(assets), 'title': content.get('title','页面'), 'layoutRelations': relations}
    return {'page_tree': content, 'layout_tree': layout_tree, 'component_mapping': mapping, 'ui_ir': ir,
            'qa_report': {'status': 'PASS', 'statusMeaning': 'structural compile only; not source completeness or visual acceptance',
                          'sourceSha256': source_hash, 'nodeCount': len(nodes),
                          'mappedItemCount': len(covered), 'usedComponents': sorted(components),
                          'tableColumnCoverage': column_coverage}}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('source','content','observation','independent-scan','output-dir'):
        p.add_argument('--'+key,required=True,type=Path)
    args=p.parse_args(); out=args.output_dir.resolve()
    if not out.is_relative_to((ROOT/'artifacts').resolve()): p.error('output_must_be_in_artifacts')
    result=compile_tree(args.source,read(args.content),read(args.observation),read(args.independent_scan))
    manifest={'schemaVersion':VERSION,'sourceSha256':result['ui_ir']['sourceSha256'],
              'contentSha256':digest(args.content),'compilerSha256':digest(Path(__file__)),
              'officialSourceSha256':result['ui_ir']['officialSource']['sourceSha256']}
    if (out/'manifest.json').exists() and read(out/'manifest.json') != manifest:
        p.error('manifest_changed_use_new_revision')
    out.mkdir(parents=True,exist_ok=True)
    for name,value in result.items(): save(out/(name+'.json'),value)
    result['qa_report']['uiIrSha256'] = digest(out/'ui_ir.json')
    save(out/'qa_report.json', result['qa_report'])
    save(out/'manifest.json',manifest)
    print(json.dumps(result['qa_report'],ensure_ascii=False))

if __name__=='__main__': main()
