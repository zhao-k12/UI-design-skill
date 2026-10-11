"""Independent completeness, hierarchy, source-integrity and freeze gate."""
from __future__ import annotations

import argparse
import copy
import importlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError
from core.prototype.parser import parse
from validators.ui_ir import load_json

builder = importlib.import_module('core.page-tree.builder')
ROOT = Path(__file__).resolve().parents[2]
OBSERVATION_KEYS = ('version', 'documentId', 'sources', 'evidence', 'page', 'unknowns')


def check(analysis, tree, source_root, review=None):
    issues = []
    def issue(code, path, message):
        issues.append({'code': code, 'path': path, 'message': message})
    try:
        Draft202012Validator(load_json(ROOT / 'schemas/prototype-analysis.schema.json')).validate(analysis)
        observations = {key: copy.deepcopy(analysis[key]) for key in OBSERVATION_KEYS}
        if parse(observations, source_root) != analysis:
            issue('analysis_changed', '/', 'Analysis differs from its validated source observations')
    except (ValueError, OSError, KeyError, TypeError, UnicodeError, ValidationError) as exc:
        issue('invalid_analysis', '/', str(exc))
    tree_errors = list(Draft202012Validator(load_json(ROOT / 'schemas/page-tree.schema.json')).iter_errors(tree))
    for error in tree_errors:
        issue('invalid_tree', '/' + '/'.join(map(str, error.absolute_path)), error.message)
    if not issues:
        if tree['analysisSha256'] != builder.fingerprint(analysis):
            issue('stale_analysis', '/analysisSha256', 'Tree belongs to another analysis')
        if tree['documentId'] != analysis['documentId'] or tree['page']['id'] != analysis['documentId']:
            issue('page_mismatch', '/page', 'Page missing or replaced')
        for key in ('identity', 'primaryTask'):
            if tree['page'][key] != analysis['page'][key]:
                issue('page_content_changed', '/page/' + key, 'Page semantics or evidence changed')
        expected = analysis['page']['blocks']
        actual = tree['page']['children']
        if [b['id'] for b in actual] != [b['id'] for b in expected]:
            issue('section_sequence', '/page/children', 'Sections missing, extra, duplicated or reordered')
        by_id = {b['id']: b for b in expected}
        seen = {tree['page']['id']}
        for section in actual:
            if section['id'] in seen:
                issue('duplicate_id', '/page/children', section['id'])
            seen.add(section['id'])
            origin = by_id.get(section['id'])
            if origin is None:
                continue
            if section['purpose'] != origin['purpose']:
                issue('section_changed', section['id'], 'Section purpose or evidence changed')
            wanted = []
            for category in ('fields', 'buttons', 'dataRegions', 'staticContent'):
                wanted.extend((i['id'], category, i['description']) for i in origin[category])
            got = [(i['id'], i['kind'], i['description']) for i in section['children']]
            if got != wanted:
                issue('item_coverage', section['id'], 'Items missing, extra, reordered, moved or changed')
            for item in section['children']:
                if item['id'] in seen:
                    issue('duplicate_id', section['id'], item['id'])
                seen.add(item['id'])
    status = 'FAIL' if issues else 'Review'
    reasons = []
    if not issues:
        if analysis['unknowns']:
            reasons.append('Unresolved prototype questions')
        if review is None:
            reasons.append('Human semantic review receipt required')
        else:
            try:
                Draft202012Validator(load_json(ROOT / 'schemas/prototype-review.schema.json')).validate(review)
                if review['analysisSha256'] != builder.fingerprint(analysis):
                    raise ValueError('Review belongs to another analysis')
                if review['decision'] != 'approved':
                    reasons.append('Semantic review rejected')
            except (ValueError, TypeError, ValidationError) as exc:
                issue('invalid_review', '/review', str(exc))
                status = 'FAIL'
        if not reasons and not issues:
            status = 'PASS'
    tree_hash = builder.fingerprint(tree)
    report = {'version': '0.1.0', 'stage': 'structure-qa', 'status': status,
              'readyForLayout': status == 'PASS', 'analysisSha256': builder.fingerprint(analysis),
              'pageTreeSha256': tree_hash, 'reviewSha256': builder.fingerprint(review) if review else None,
              'issues': issues, 'reviewReasons': reasons}
    if status == 'PASS':
        report['freeze'] = {'pageTreeSha256': tree_hash, 'analysisSha256': builder.fingerprint(analysis)}
    return report


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('analysis', type=Path)
    cli.add_argument('--source-root', type=Path, required=True)
    cli.add_argument('--output-dir', type=Path, required=True)
    cli.add_argument('--review', type=Path)
    args = cli.parse_args()
    analysis = load_json(args.analysis)
    # Validate before constructing so malformed input cannot leave a partial tree.
    Draft202012Validator(load_json(ROOT / 'schemas/prototype-analysis.schema.json')).validate(analysis)
    tree = builder.build(analysis)
    report = check(analysis, tree, args.source_root, load_json(args.review) if args.review else None)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, value in (('page_tree.json', tree), ('structure_qa_report.json', report)):
        (args.output_dir / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Structure QA: ' + report['status'])
    return 0 if report['readyForLayout'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
