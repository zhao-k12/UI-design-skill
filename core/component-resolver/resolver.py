"""Evidence-bound component decisions and a diagnostic annotation view."""
from __future__ import annotations

import argparse
import html
import importlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError
from core.layout.builder import generate, tokens
from validators.structure.gate import builder
from validators.ui_ir import load_json

registry_module = importlib.import_module('core.component-resolver.registry')
ROOT = Path(__file__).resolve().parents[2]
CAPABILITIES = {'text': ('Input',), 'choice': ('Select',), 'hierarchy': ('TreeSelect',),
                'location': ('Cascader',), 'date-range': ('DateRangePicker',),
                'action': ('Button',), 'records': ('Table',), 'static': ('Text',)}
CATEGORIES = {'fields': {'text', 'choice', 'hierarchy', 'location', 'date-range'},
              'buttons': {'action'}, 'dataRegions': {'records'}, 'staticContent': {'static'}}


def resolve(analysis, page_tree, source_root, review, layout_plan, decisions, registry,
            token_registry, *, allow_test_fixtures=False):
    tree, layout_report = generate(analysis, page_tree, source_root, review, layout_plan,
                                  token_registry, allow_test_fixtures=allow_test_fixtures)
    diagnostic = (allow_test_fixtures and layout_report.get('testFixture') is True
                  and layout_report['status'] == 'PASS')
    result = {'version': '0.1.0', 'stage': 'component-mapping', 'status': 'Review',
              'readyForAssembly': False, 'diagnosticOnly': diagnostic,
              'layoutReport': layout_report, 'registrySha256': registry.fingerprint,
              'registryScope': registry.scope, 'decisionsSha256': None,
              'rows': [], 'issues': []}
    if not layout_report['readyForMapping'] and not diagnostic:
        result['status'] = layout_report['status'] if layout_report['status'] != 'PASS' else 'Review'
        return result
    try:
        result['decisionsSha256'] = builder.fingerprint(decisions)
        Draft202012Validator(load_json(ROOT / 'schemas/component-decisions.schema.json')).validate(decisions)
        if decisions['layoutTreeSha256'] != builder.fingerprint(tree):
            raise ValueError('Decisions belong to another Layout Tree')
        if decisions['registrySha256'] != registry.fingerprint:
            raise ValueError('Component registry changed')
        semantic = {item['id']: (section['id'], item)
                    for section in page_tree['page']['children'] for item in section['children']}
        by_id = {entry['sourceId']: entry for entry in decisions['items']}
        if len(by_id) != len(decisions['items']) or set(by_id) != set(semantic):
            raise ValueError('Every source item needs exactly one decision')
        cells = []
        def walk(node):
            if node['type'] == 'Cell':
                cells.append(node)
            for child in node.get('children', []):
                walk(child)
        walk(tree['page'])
        valid_refs = {e['id'] for e in analysis['evidence']}
        for cell in cells:
            source_id = cell['sourceIds'][0]
            section_id, source = semantic[source_id]
            decision = by_id[source_id]
            if not set(decision['evidence']).issubset(valid_refs) or not set(decision['evidence']).intersection(source['description']['evidence']):
                raise ValueError('Decision must cite the source item evidence')
            if decision['intent'] not in CATEGORIES[source['kind']]:
                raise ValueError('Component intent conflicts with semantic item category')
            row = {'cellId': cell['id'], 'sourceId': source_id, 'sectionId': section_id,
                   'label': source['description']['text'], 'intent': decision['intent'],
                   'confidence': decision['confidence'], 'rationale': decision['rationale'],
                   'evidence': decision['evidence'], 'status': 'Review',
                   'requestedTypes': list(CAPABILITIES[decision['intent']]),
                   'componentId': None, 'componentType': None, 'variant': None, 'fallbackUsed': False}
            if decision['confidence'] != 'low':
                allowed = CAPABILITIES[decision['intent']]
                preferred = decision['preferredId']
                candidates = []
                if preferred:
                    try:
                        chosen = registry.resolve(preferred, decision['variant'])
                        if chosen['descriptor']['componentType'] not in allowed:
                            raise ValueError('Preferred component is incompatible with semantic intent')
                        candidates = [chosen]
                    except registry_module.ComponentError:
                        if decision['confidence'] == 'high':
                            row['status'] = 'Missing'
                if not candidates and row['status'] != 'Missing':
                    # Medium confidence falls back only to a standard admitted base
                    # component with the SAME semantic capability, never a lossy type.
                    for logical_id, entry in registry.snapshot['components'].items():
                        if entry['status'] != 'active' or entry['componentType'] not in allowed:
                            continue
                        if decision['confidence'] == 'medium' and entry['tier'] != 'base':
                            continue
                        try:
                            candidates.append(registry.resolve(logical_id, decision['variant']))
                        except registry_module.ComponentError:
                            continue
                    if candidates:
                        ranks = {'block': 0, 'composite': 1, 'base': 2}
                        rank = min(ranks[c['descriptor']['tier']] for c in candidates)
                        candidates = [c for c in candidates if ranks[c['descriptor']['tier']] == rank]
                    row['fallbackUsed'] = decision['confidence'] == 'medium' and bool(candidates)
                if len(candidates) == 1:
                    chosen = candidates[0]
                    row.update(status='Resolved', componentId=chosen['logicalId'], variant=chosen['variant'],
                               componentType=chosen['descriptor']['componentType'])
                elif not candidates and row['status'] != 'Missing':
                    row['status'] = 'Missing'
            row['reasonCode'] = ('missing_component' if row['status'] == 'Missing' else
                                 'review_required' if row['status'] == 'Review' else
                                 'standard_fallback' if row['fallbackUsed'] else 'matched')
            result['rows'].append(row)
        statuses = {row['status'] for row in result['rows']}
        result['status'] = 'Missing' if 'Missing' in statuses else 'Review' if 'Review' in statuses else 'PASS'
        result['readyForAssembly'] = (result['status'] == 'PASS' and not diagnostic and registry.scope == 'production')
        result['layoutTreeSha256'] = builder.fingerprint(tree)
    except (ValueError, TypeError, KeyError, ValidationError) as exc:
        result.update(status='FAIL', rows=[], issues=[{'code': 'invalid_component_decisions', 'message': str(exc)}])
    return result


def annotation(mapping):
    """Diagnostic rectangles only: colors never enter mapping or design tokens."""
    colors = {'Input': '#dbeafe', 'Select': '#dcfce7', 'Button': '#fef3c7',
              'Table': '#ede9fe', 'Missing': '#fee2e2', 'Review': '#e5e7eb'}
    boxes = {}
    skeleton = mapping['layoutReport'].get('engineReport', {}).get('skeleton')
    def walk(node):
        boxes[node['id']] = node['box']
        for child in node.get('children', []):
            walk(child)
    if skeleton:
        walk(skeleton)
    parts = []
    for row in mapping['rows']:
        box = boxes[row['cellId']]
        label = f"{row['label']} · {row['componentType'] or row['status']}"
        detail = f"{row['sourceId']} → {row['componentId'] or row['status']} · {row['rationale']}"
        parts.append(f'<div class="cell" style="left:{box["x"]}px;top:{box["y"]}px;width:{box["width"]}px;height:{box["height"]}px;background:{colors.get(row["componentType"] or row["status"], "#e5e7eb")}" title="{html.escape(detail, quote=True)}">{html.escape(label)}</div>')
    width = skeleton['box']['width'] if skeleton else 900
    height = skeleton['box']['height'] if skeleton else 60
    rows = ''.join(f'<tr><td>{html.escape(r["sectionId"])}</td><td>{html.escape(r["label"])}</td><td>{html.escape(r["componentId"] or r["status"])}</td><td>{html.escape(r["rationale"])}</td></tr>' for r in mapping['rows'])
    return ('<!doctype html><html lang="zh"><meta charset="utf-8"><title>组件标注检查</title>'
            '<style>body{font:14px system-ui;margin:24px;background:#fafafa}.canvas{position:relative;border:1px solid #999;background:white}.cell{position:absolute;box-sizing:border-box;border:1px solid #666;padding:4px;overflow:hidden;white-space:nowrap}table{border-collapse:collapse;margin-top:20px}td,th{border:1px solid #ccc;padding:8px;text-align:left}</style>'
            '<h1>组件标注检查</h1><p>标识色仅用于检查。此视图不创建组件实例，也不是最终设计。</p>' +
            ('<p>测试样例：仅用于检查，不能进入正式组装。</p>' if mapping['diagnosticOnly'] else '') +
            f'<p>检查结果：{html.escape(mapping["status"])} · 正式组装：{"可进入" if mapping["readyForAssembly"] else "已阻止"}</p>'
            f'<div class="canvas" style="width:{width}px;height:{height}px">'+''.join(parts)+'</div>'
            '<table><tr><th>区块</th><th>内容</th><th>组件 ID / 状态</th><th>判断依据</th></tr>'+rows+'</table></html>')


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ('analysis', 'page_tree', 'layout_plan', 'decisions'):
        cli.add_argument(name, type=Path)
    cli.add_argument('--source-root', type=Path, required=True)
    cli.add_argument('--review', type=Path)
    cli.add_argument('--output-dir', type=Path, required=True)
    cli.add_argument('--allow-test-fixtures', action='store_true')
    args = cli.parse_args()
    registry = registry_module.ComponentRegistry(load_json(ROOT / 'registries/components/catalog.json'),
                                                load_json(ROOT / 'registries/components/fidelity-reports.json'))
    inputs = [getattr(args, name) for name in ('analysis', 'page_tree', 'layout_plan', 'decisions')]
    if args.review:
        inputs.append(args.review)
    a = load_json(args.analysis)
    inputs.extend(args.source_root / source['path'] for source in a['sources'])
    outputs = [args.output_dir / name for name in ('component_mapping.json', 'component_annotation.html')]
    if any(output.resolve() in {p.resolve() for p in inputs} for output in outputs):
        cli.error('Output must not overwrite an input')
    mapping = resolve(a, load_json(args.page_tree), args.source_root,
                      load_json(args.review) if args.review else None, load_json(args.layout_plan),
                      load_json(args.decisions), registry, tokens.TokenRegistry(load_json(ROOT / 'registries/tokens/default.json')),
                      allow_test_fixtures=args.allow_test_fixtures)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    outputs[0].write_text(json.dumps(mapping, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    outputs[1].write_text(annotation(mapping), encoding='utf-8')
    print('Component mapping: '+mapping['status'])
    return 0 if mapping['readyForAssembly'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
