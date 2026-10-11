"""Bind official runtime inputs to candidate preparation, without admitting designs."""
import argparse
import hashlib
import json
from pathlib import Path

from adapters.figma.font_preflight import preflight_source_fonts
from validators.component_ir import verify_artifacts
from validators.ui_ir import ROOT, load_json


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def prepare_candidates(reference, font_evidence, discovery, *, logical_ids=None, bindings=None, file_reference=None):
    report = {'scope': 'figma_official_candidate_preflight', 'status': 'FAIL',
        'nativeExecution': 'NOT_RUN', 'fidelityGate': 'NOT_RUN', 'admissionEligible': False,
        'preparation': None, 'issues': []}
    try:
        reference = Path(reference).resolve()
        bundle = load_json(reference / 'component_ir.json')
        # Verify local paths before following screenshot references.
        for component in bundle.get('components', []):
            screenshot = (reference / component['screenshot']['path']).resolve()
            if not screenshot.is_relative_to(reference):
                raise ValueError('screenshot_outside_reference')
        issues = verify_artifacts(reference)
        if issues:
            report['issues'] = issues
            return report
        if font_evidence.get('referenceComponentIrSha256') != file_hash(reference / 'component_ir.json'):
            raise ValueError('font_evidence_reference_hash_mismatch')
        if file_reference is None or discovery.get('fileReference') != file_reference:
            raise ValueError('font_discovery_file_mismatch')
        available = {item['logicalComponentId']: item for item in bundle['components']}
        requested = list(logical_ids) if logical_ids is not None else list(available)
        if not requested or len(requested) != len(set(requested)) or any(item not in available for item in requested):
            raise ValueError('invalid_candidate_selection')
        reference_ids = [item['logicalId'] for item in font_evidence.get('referenceMatches', [])]
        if len(reference_ids) != len(set(reference_ids)) or set(reference_ids) != set(available):
            raise ValueError('font_evidence_component_inventory_mismatch')
        for item in font_evidence.get('observations', []):
            if item.get('logicalId') not in available:
                raise ValueError('font_observation_unknown_component')
        for component in available.values():
            if component['environment'] != font_evidence.get('environment'):
                raise ValueError('font_environment_mismatch')
            # The supplemental observer changes renderer provenance only.
            for key in ('sourceVersion', 'sourceLockSha256', 'officialCssSha256', 'casesSha256', 'harnessBundleSha256', 'extractorSha256', 'assemblySha256'):
                if component['provenance'].get(key) != font_evidence.get('provenance', {}).get(key):
                    raise ValueError('font_source_provenance_mismatch: ' + key)
        selected_fonts = dict(font_evidence)
        selected_fonts['referenceMatches'] = [item for item in font_evidence['referenceMatches'] if item['logicalId'] in requested]
        selected_fonts['observations'] = [item for item in font_evidence['observations'] if item['logicalId'] in requested]
        fonts = preflight_source_fonts(selected_fonts, discovery, bindings)
        report['fontPreflight'] = fonts
        report['inputHashes'] = {'componentIrSha256': file_hash(reference / 'component_ir.json'),
            'runtimeManifestSha256': file_hash(reference / 'runtime_manifest.json')}
        if fonts['status'] != 'PASS':
            report['status'] = 'REVIEW'
            report['issues'] = fonts['issues']
            return report
        report['status'] = 'PASS'
        # These are source inputs for a future native builder, never capture measurements.
        report['preparation'] = {'fileReference': file_reference, 'sourceDirectory': str(reference),
            'components': [{'logicalId': item, 'componentType': available[item]['componentType'],
                'variant': available[item]['variant'], 'state': available[item]['state'],
                'sourceVersion': available[item]['provenance']['sourceVersion'],
                'referenceScreenshotSha256': available[item]['screenshot']['sha256']} for item in requested],
            'fontBindings': bindings, 'nativeBuilder': 'NOT_IMPLEMENTED'}
    except (OSError, ValueError, TypeError, KeyError) as exc:
        report['issues'] = [{'code': 'invalid_candidate_source', 'detail': str(exc)}]
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--font-evidence', type=Path, required=True)
    parser.add_argument('--discovery', type=Path, required=True)
    parser.add_argument('--bindings', type=Path)
    parser.add_argument('--file-reference', required=True)
    parser.add_argument('--logical-id', action='append')
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    inputs = [args.reference.resolve(), args.font_evidence.resolve().parent, args.discovery.resolve().parent]
    if not output.is_relative_to((ROOT / 'artifacts').resolve()) or any(output == item or output.is_relative_to(item) for item in inputs):
        parser.error('Output must be separate project artifacts, outside source inputs')
    output.mkdir(parents=True, exist_ok=True)
    target = output / 'candidate_preflight_report.json'
    target.write_text(json.dumps({'status': 'RUNNING', 'preparation': None}) + '\n', encoding='utf-8')
    try:
        report = prepare_candidates(args.reference, load_json(args.font_evidence), load_json(args.discovery),
            logical_ids=args.logical_id, bindings=load_json(args.bindings) if args.bindings else None,
            file_reference=args.file_reference)
    except (OSError, ValueError) as exc:
        report = {'scope': 'figma_official_candidate_preflight', 'status': 'FAIL', 'preparation': None,
            'nativeExecution': 'NOT_RUN', 'fidelityGate': 'NOT_RUN', 'admissionEligible': False,
            'issues': [{'code': 'invalid_candidate_input', 'detail': str(exc)}]}
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': report['status'], 'issues': report['issues']}, ensure_ascii=False))
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
