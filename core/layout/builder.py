"""Source-bound semantic Page Tree to standard layout patterns (TASK-013)."""
from __future__ import annotations

import argparse
import copy
import importlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError
from validators.structure.gate import check, builder as semantic
from validators.ui_ir import load_json
from core.layout.patterns import instantiate, PATTERNS
from core.layout.engine import LayoutEngine

tokens = importlib.import_module('core.design-rules.tokens')
ROOT = Path(__file__).resolve().parents[2]
RULES = {'version': '0.1.0', 'fieldSpan': 6, 'gridColumns': 24,
         'fieldGap': 'spacing.md', 'buttonGap': 'spacing.sm',
         'sectionGap': 'spacing.section', 'pagePadding': 'spacing.page'}


def generate(analysis, page_tree, source_root, review, plan, registry, *, allow_test_fixtures=False):
    structure = check(analysis, page_tree, source_root, review)
    report = {'stage': 'layout-qa', 'status': 'Review', 'readyForMapping': False,
              'structureReport': structure, 'pageTreeSha256': semantic.fingerprint(page_tree),
              'planSha256': None, 'rulesSha256': semantic.fingerprint(RULES),
              'tokenRegistrySha256': registry.fingerprint, 'issues': [], 'testFixture': False}
    if structure['status'] != 'PASS':
        report['status'] = structure['status']
        return None, report
    try:
        report['planSha256'] = semantic.fingerprint(plan)
        Draft202012Validator(load_json(ROOT / 'schemas/layout-plan.schema.json')).validate(plan)
        if plan['pageTreeSha256'] != semantic.fingerprint(page_tree):
            raise ValueError('Layout plan belongs to another frozen Page Tree')
        if plan['tokenRegistrySha256'] != registry.fingerprint:
            raise ValueError('Layout plan token registry changed')
        sections = page_tree['page']['children']
        ids = [section['id'] for section in sections]
        if set(plan['sectionRegions']) != set(ids):
            raise ValueError('Every Section must have exactly one pattern region')
        if set(plan.get('sectionConfigs',{}))-set(ids):raise ValueError('Layout config refers to an unknown Section')
        regions = list(plan['sectionRegions'].values())
        if len(set(regions)) != len(regions) or any(r not in PATTERNS[plan['pattern']] for r in regions):
            raise ValueError('Unsupported, duplicate or ambiguous pattern region')
        items = [item for section in sections for item in section['children']]
        if set(plan['measurements']) != {item['id'] for item in items}:
            raise ValueError('Every semantic item needs exactly one source measurement')
        fixture = any(m['source']['kind'] == 'test-fixture' for m in plan['measurements'].values())
        if fixture and not allow_test_fixtures:
            raise ValueError('Test measurements are disabled for production')
        report['testFixture'] = fixture
        region_nodes = {role: [] for role in PATTERNS[plan['pattern']]}
        region_sources = {}
        def layout():
            return {'width': {'mode': 'fill'}, 'height': {'mode': 'hug'}}
        for index, section in enumerate(sections):
            role = plan['sectionRegions'][section['id']]
            config=plan.get('sectionConfigs',{}).get(section['id'],{})
            if 'inlineOrder' in config and not config.get('inlineGrid'):raise ValueError('Inline order requires inline Grid')
            if 'buttonAlignment' in config and config.get('inlineGrid'):
                raise ValueError('Button alignment requires a separate action row')
            groups = {'fields': [], 'buttons': [], 'content': []}
            for item in section['children']:
                category = item['kind']
                cell = {'id': f'layout.item.{len(region_sources)}.{len(groups["fields"])+len(groups["buttons"])+len(groups["content"])}',
                        'type': 'Cell', 'sourceIds': [item['id']],
                        'measurement': copy.deepcopy(plan['measurements'][item['id']]),
                        'layout': {'width': {'mode': 'fill' if category != 'buttons' else 'hug'}, 'height': {'mode': 'hug'}}}
                if category == 'fields':
                    cell['role'] = 'field'
                    cell['layout']['span'] = RULES['fieldSpan']
                groups[category if category in ('fields', 'buttons') else 'content'].append(cell)
            if 'contentOrder' in config:
                by_source={c['sourceIds'][0]:c for c in groups['content']}
                if set(config['contentOrder'])!=set(by_source):raise ValueError('Content order must cover exactly the source content')
                groups['content']=[by_source[i] for i in config['contentOrder']]
            nodes = []
            if config.get('inlineGrid'):
                if role not in ('query','form','metrics') or 'contentOrder' in config or config.get('contentRows'):
                    raise ValueError('Inline Grid requires an unambiguous standard Grid region')
                by_source={c['sourceIds'][0]:c for values in groups.values() for c in values}
                # Source categories stay intact; the visual order follows the explicit
                # semantic Section sequence, with fields/content/actions declared below.
                order=config.get('inlineOrder',[i['id'] for i in section['children']])
                if set(order)!=set(by_source):raise ValueError('Inline order must cover every Section item')
                ordered=[by_source[i] for i in order]
                for cell in ordered:
                    cell['layout']['width']={'mode':'fill'};cell['layout']['span']=RULES['fieldSpan']
                    cell['constraints']={'minWidth':cell['measurement']['width']}
                region_nodes[role]=ordered;region_sources[role]=section['id'];continue
            for category, node_type, gap in (('fields', 'Grid', RULES['fieldGap']), ('buttons', 'HorizontalStack', RULES['buttonGap'])):
                if groups[category]:
                    group_layout = {**layout(), 'gap': {'token': gap}, 'wrap': True}
                    if node_type == 'Grid':
                        group_layout['gridColumns'] = RULES['gridColumns']
                    elif 'buttonAlignment' in config:
                        group_layout['alignment'] = {'main': config['buttonAlignment'], 'cross': 'center'}
                    nodes.append({'id': f'layout.group.{index}.{category}', 'type': node_type,
                                  'layout': group_layout, 'children': groups[category],
                                  'sourceIds': [section['id']],
                                  'constraints': {'minWidth': max(c['measurement']['width'] for c in groups[category])}})
            content=groups['content'];row_groups=config.get('contentRows',[]);claimed=set();row_starts={}
            for row_index, row in enumerate(row_groups):
                positions=[next((i for i,c in enumerate(content) if c['sourceIds'][0]==identifier),-1) for identifier in row]
                if -1 in positions or positions!=list(range(positions[0],positions[0]+len(positions))) or claimed.intersection(row):
                    raise ValueError('Content row requires consecutive unique source items')
                claimed.update(row);row_starts[positions[0]]=(row_index,len(row))
            cursor=0
            while cursor<len(content):
                if cursor in row_starts:
                    row_index,length=row_starts[cursor];children=content[cursor:cursor+length]
                    for cell in children:cell['layout']['width']={'mode':'hug'}
                    nodes.append({'id':f'layout.group.{index}.content-row.{row_index}','type':'HorizontalStack',
                                  'sourceIds':[section['id']],'layout':{**layout(),'gap':{'token':RULES['buttonGap']},
                                  'alignment':{'main':'space-between','cross':'center'}},'children':children})
                    cursor+=length
                else:nodes.append(content[cursor]);cursor+=1
            for node in nodes:
                if node['type'] == 'Cell':
                    node['constraints'] = {'minWidth': node['measurement']['width']}
            # Standard query/form/metrics template wraps its children in a 24 Grid.
            # Full-width groups preserve their inner field Grid and button Stack.
            if role in ('query', 'form', 'metrics'):
                for node in nodes:
                    node['layout']['span'] = 24
            region_nodes[role] = nodes
            region_sources[role] = section['id']
        canvas_policy = '0.2.0-static-grow' if registry.version == '0.2.2' else '0.1.0'
        tree = instantiate(plan['pattern'], region_nodes, canvas_policy=canvas_policy)
        if 'canvasWidth' in plan:
            tree['page']['layout']['width'] = {'mode': 'fixed', 'value': plan['canvasWidth']}
        tree['page']['sourceIds'] = [page_tree['page']['id']]
        holders = tree['page']['children']
        if plan['pattern'] == 'sidebar-content':
            holders = holders[0]['children']
        holders[:] = [node for node in holders if node['role'] in region_sources]
        for node in holders:
            node['sourceIds'] = [region_sources[node['role']]]
            config=plan.get('sectionConfigs',{}).get(region_sources[node['role']],{})
            if 'padding' in config:node['layout']['padding']=copy.deepcopy(config['padding'])
        qa = LayoutEngine(registry).run(tree)
        report.update(status=qa['status'], readyForMapping=qa['status'] == 'PASS', engineReport=qa,
                      layoutTreeSha256=semantic.fingerprint(tree))
        if fixture:
            report['readyForMapping'] = False
        return tree, report
    except (ValueError, TypeError, KeyError, ValidationError) as exc:
        report.update(status='FAIL', issues=[{'code': 'invalid_layout_plan', 'message': str(exc)}])
        return None, report


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ('analysis', 'page_tree', 'plan'):
        cli.add_argument(name, type=Path)
    cli.add_argument('--source-root', type=Path, required=True)
    cli.add_argument('--review', type=Path)
    cli.add_argument('--tokens', type=Path, default=ROOT / 'registries/tokens/default.json')
    cli.add_argument('--output-dir', type=Path, required=True)
    cli.add_argument('--allow-test-fixtures', action='store_true')
    args = cli.parse_args()
    outputs = [args.output_dir / name for name in ('layout_tree.json', 'layout_qa_report.json')]
    inputs = [args.analysis, args.page_tree, args.plan, args.tokens]
    if args.review:
        inputs.append(args.review)
    analysis_input = load_json(args.analysis)
    inputs.extend(args.source_root / source['path'] for source in analysis_input.get('sources', []))
    if any(output.resolve() in {path.resolve() for path in inputs} for output in outputs):
        cli.error('Output files must not overwrite source, analysis, tree, review, plan or tokens')
    tree, report = generate(analysis_input, load_json(args.page_tree), args.source_root,
                            load_json(args.review) if args.review else None, load_json(args.plan),
                            tokens.TokenRegistry(load_json(args.tokens)), allow_test_fixtures=args.allow_test_fixtures)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / 'layout_qa_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    # Replace any stale successful output with null when the current gate blocks.
    (args.output_dir / 'layout_tree.json').write_text(json.dumps(tree, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('Layout QA: ' + report['status'])
    return 0 if report['readyForMapping'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
