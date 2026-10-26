"""Compile a declarative content tree without selecting a business-page template."""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / 'node_modules/view-ui-plus'
VERSION = 'html-composition-v1'
SPACING = {'none': 0, 'xs': 8, 'sm': 12, 'md': 16, 'lg': 24}

def digest(path): return sha256(path.read_bytes()).hexdigest()
def read(path): return json.loads(path.read_text(encoding='utf-8'))
def save(path, value): path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

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
    nodes, covered, components, icons, layouts = {}, set(), set(), set(content.get('icons', [])), {}
    def record_icon(value):
        if isinstance(value, str): icons.add(value)
        elif not isinstance(value, dict) or not isinstance(value.get('bind'), str) or not content.get('icons'):
            raise ValueError('bound_icon_requires_declared_source_icons')
    def visit(node):
        if not isinstance(node, dict) or not isinstance(node.get('id'), str) or not node['id']:
            raise ValueError('node_id_required')
        key = node['id']
        if key in nodes: raise ValueError(f'duplicate_node_id:{key}')
        nodes[key] = node
        for source_id in node.get('sourceIds', []):
            if source_id not in first or first[source_id]['decision'] != 'include':
                raise ValueError(f'unknown_source_id:{source_id}')
            covered.add(source_id)
        kind = node.get('kind')
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
        elif kind == 'repeat':
            if not isinstance(node.get('items'), (list,dict)): raise ValueError('repeat_items_required')
            visit(node['template'])
        elif kind != 'text': raise ValueError(f'unsupported_node_kind:{kind}')
        for child in node.get('children', []): visit(child)
        for children in node.get('slots', {}).values():
            for child in children: visit(child)
    visit(content['root'])
    included = {key for key, item in first.items() if item['decision'] == 'include'}
    if covered != included: raise ValueError(f'page_tree_source_coverage:{sorted(included-covered)}')
    mapping = {key: node.get('component', node['kind']) for key,node in nodes.items()}
    layout_tree = {'gridColumns': 24, 'spacingSource': 'src/styles/custom.less @padding-*', 'nodes': layouts}
    ir = {'schemaVersion': VERSION, 'sourceSha256': source_hash, 'officialSource': catalog,
          'root': content['root'], 'layout': layout_tree, 'requiredIcons': sorted(icons),
          'usedComponents': sorted(components), 'title': content.get('title','页面')}
    return {'page_tree': content, 'layout_tree': layout_tree, 'component_mapping': mapping, 'ui_ir': ir,
            'qa_report': {'status': 'PASS', 'sourceSha256': source_hash, 'nodeCount': len(nodes),
                          'mappedItemCount': len(covered), 'usedComponents': sorted(components)}}

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
