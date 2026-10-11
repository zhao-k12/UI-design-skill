"""Source-bound AI semantic observations; no visual design or image inference."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator
from validators.ui_ir import load_json

ROOT = Path(__file__).resolve().parents[2]


class AnalysisError(ValueError):
    pass


def parse(observations: dict, source_root: Path) -> dict:
    """Check AI judgments against immutable UTF-8 prototype transcripts.

    Quotes prove what was observed, not the correctness of an AI interpretation.
    Human semantic review remains required. Unknowns block downstream readiness.
    """
    schema = load_json(ROOT / 'schemas/prototype-observations.schema.json')
    errors = sorted(Draft202012Validator(schema).iter_errors(observations),
                    key=lambda e: str(list(e.absolute_path)))
    if errors:
        raise AnalysisError('; '.join(e.message for e in errors))
    sources = {}
    base = source_root.resolve()
    for source in observations['sources']:
        if source['id'] in sources:
            raise AnalysisError('Duplicate source ID')
        path = (base / source['path']).resolve()
        if not path.is_relative_to(base) or not path.is_file():
            raise AnalysisError('Source must be an existing file inside source root')
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != source['sha256']:
            raise AnalysisError('Source hash mismatch')
        sources[source['id']] = raw.decode('utf-8-sig')
    evidence = {}
    for entry in observations['evidence']:
        if entry['id'] in evidence:
            raise AnalysisError('Duplicate evidence ID')
        text = sources.get(entry['sourceId'])
        if text is None or not 0 <= entry['start'] < entry['end'] <= len(text):
            raise AnalysisError('Invalid evidence source or range')
        if text[entry['start']:entry['end']] != entry['quote']:
            raise AnalysisError('Evidence quote differs from source')
        evidence[entry['id']] = entry
    ids = set()

    def walk(value):
        if isinstance(value, dict):
            if 'id' in value:
                if value['id'] in ids:
                    raise AnalysisError('Duplicate semantic ID')
                ids.add(value['id'])
            if 'evidence' in value:
                if any(ref not in evidence for ref in value['evidence']):
                    raise AnalysisError('Unknown evidence reference')
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)
    walk(observations['page'])
    walk(observations['unknowns'])
    result = copy.deepcopy(observations)
    result['stage'] = 'prototype-analysis'
    result['status'] = 'Review'
    result['readyForStructure'] = False
    result['reviewReasons'] = ['Semantic interpretation requires human review']
    if result['unknowns']:
        result['reviewReasons'].append('Unresolved prototype questions')
    result['observationSha256'] = hashlib.sha256(json.dumps(
        observations, sort_keys=True, ensure_ascii=False, separators=(',', ':'),
        allow_nan=False).encode()).hexdigest()
    return result


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('observations', type=Path)
    cli.add_argument('--source-root', type=Path, required=True)
    cli.add_argument('--output', type=Path, required=True)
    args = cli.parse_args()
    try:
        result = parse(load_json(args.observations), args.source_root)
    except (ValueError, OSError, UnicodeError) as exc:
        cli.exit(1, f'Prototype analysis rejected: {exc}\n')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Prototype analysis saved: {result["status"]}')


if __name__ == '__main__':
    main()
