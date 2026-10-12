"""Build and verify self-contained evidence bytes, never grant native admission."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import shutil
import tempfile

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = Path(__file__).with_name('evidence-package.schema.json')
NATIVE_ROLES = frozenset(('source', 'component-ir', 'registry', 'tokens', 'rules', 'program',
                          'license', 'font-identity', 'ui-ir', 'execution', 'readback',
                          'native-png', 'visual-review', 'fidelity'))
VERSION_KEYS = frozenset(('skill_version', 'ui_ir_version', 'component_library_version',
                         'component_source_version', 'remix_icon_version', 'design_token_version',
                         'design_rule_version', 'figma_adapter_version', 'penpot_adapter_version'))


def load_json(path):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError('Duplicate JSON key: ' + key)
            value[key] = item
        return value
    def reject(value):
        raise ValueError('Nonfinite JSON value: ' + value)
    return json.loads(Path(path).read_text(encoding='utf-8'), object_pairs_hook=unique,
                      parse_constant=reject)


def issue(code, path, detail, status='FAIL'):
    return {'code': code, 'path': str(path), 'status': status, 'detail': detail}


def report(issues, **extra):
    status = 'FAIL' if any(i['status'] == 'FAIL' for i in issues) else 'MISSING' if issues else 'PASS'
    return {'scope': 'portable-evidence-integrity', 'status': status, 'issues': issues,
            'nativeExecution': 'NOT_RUN', 'nativeAcceptance': 'NOT_RUN', 'releaseReady': False, **extra}


def validate_relative(relative, *, portable=False):
    if (not isinstance(relative, str) or not relative or '\\' in relative
            or PureWindowsPath(relative).drive or PurePosixPath(relative).is_absolute()
            or any(part in ('', '.', '..') for part in relative.split('/'))):
        raise ValueError('Expected a canonical relative POSIX path')
    if portable:
        for part in relative.split('/'):
            if (not re.fullmatch('[A-Za-z0-9_-][A-Za-z0-9._-]*', part) or part.endswith('.')
                    or re.fullmatch(r'(?i:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])', part.split('.')[0])):
                raise ValueError('Path is not portable across Windows/POSIX')
    return relative.split('/')


def safe_path(root, relative, *, portable=False):
    """Reject traversal, aliases, links and Windows names before reading/copying."""
    parts = validate_relative(relative, portable=portable)
    root = Path(root).resolve()
    current = root
    for part in parts:
        current /= part
        if current.is_symlink():
            raise ValueError('Evidence symlinks are forbidden')
    path = current.resolve()
    if not path.is_relative_to(root):
        raise ValueError('Path escapes the evidence root')
    return path


def manifest_issues(manifest):
    schema = load_json(SCHEMA)
    errors = sorted(Draft202012Validator(schema).iter_errors(manifest), key=lambda e: str(list(e.path)))
    if errors:
        return [issue('schema_invalid', '/'.join(map(str, e.path)), e.message) for e in errors]
    issues = []
    artifacts = {}
    paths = {'manifest.json'}
    for item in manifest['artifacts']:
        identifier, path = item['id'], item['path']
        if identifier in artifacts:
            issues.append(issue('duplicate_artifact_id', identifier, 'Artifact IDs must be unique'))
        artifacts[identifier] = item
        try:
            validate_relative(path, portable=True)
        except ValueError as exc:
            issues.append(issue('invalid_artifact_path', path, str(exc)))
        key = path.casefold()
        if key in paths:
            issues.append(issue('duplicate_artifact_path', path, 'Paths must be unique and cannot replace manifest.json'))
        paths.add(key)
    for path in sorted(paths):
        if any(parent.as_posix() in paths for parent in PurePosixPath(path).parents if parent.as_posix() != '.'):
            issues.append(issue('artifact_path_overlap', path, 'A file cannot also be a directory'))
    coverage = {}
    configurations = set()
    for item in manifest['coverage']:
        if item['id'] in coverage:
            issues.append(issue('duplicate_coverage_id', item['id'], 'Coverage IDs must be unique'))
        configuration = (item['logicalId'], item['configurationId'])
        if configuration in configurations:
            issues.append(issue('duplicate_configuration', item['id'], 'Declare each configuration once'))
        configurations.add(configuration)
        coverage[item['id']] = item
    pairs = set()
    for packet in manifest['evidenceSets']:
        pair = (packet['coverageId'], packet['platform'])
        if pair in pairs:
            issues.append(issue('duplicate_evidence_set', str(pair), 'One evidence set per coverage/platform'))
        pairs.add(pair)
        if pair[0] not in coverage or pair[1] not in coverage[pair[0]]['platforms']:
            issues.append(issue('undeclared_coverage', str(pair), 'Evidence set is outside declared coverage'))
        for role, identifier in packet['artifacts'].items():
            if identifier not in artifacts or artifacts[identifier]['role'] != role:
                issues.append(issue('invalid_evidence_reference', identifier, 'Evidence role and artifact ID must match'))
        if manifest['purpose'] == 'native-acceptance':
            for role in sorted(NATIVE_ROLES - packet['artifacts'].keys()):
                issues.append(issue('missing_evidence_role', str(pair), role, 'MISSING'))
    if manifest['purpose'] == 'native-acceptance':
        if not coverage:
            issues.append(issue('missing_coverage', 'coverage', 'Native packages must declare configurations', 'MISSING'))
        for key in sorted(VERSION_KEYS - manifest['versions'].keys()):
            issues.append(issue('missing_version_lock', 'versions', key, 'MISSING'))
        for identifier, item in coverage.items():
            for platform in item['platforms']:
                if (identifier, platform) not in pairs:
                    issues.append(issue('missing_evidence_set', identifier, platform, 'MISSING'))
    return issues


def verify(bundle):
    bundle = Path(bundle).resolve()
    try:
        manifest_path = safe_path(bundle, 'manifest.json')
        manifest = load_json(manifest_path)
    except FileNotFoundError as exc:
        return report([issue('missing_manifest', 'manifest.json', str(exc), 'MISSING')])
    except (OSError, ValueError) as exc:
        return report([issue('invalid_manifest', 'manifest.json', str(exc))])
    issues = manifest_issues(manifest)
    if any(i['code'] == 'schema_invalid' for i in issues):
        return report(issues)
    listed = {'manifest.json'}
    for item in manifest['artifacts']:
        listed.add(item['path'])
        try:
            path = safe_path(bundle, item['path'], portable=True)
            if not path.is_file():
                issues.append(issue('missing_artifact', item['path'], 'Artifact file is unavailable', 'MISSING'))
                continue
            data = path.read_bytes()
            if len(data) != item['bytes'] or sha256(data).hexdigest() != item['sha256']:
                issues.append(issue('artifact_changed', item['path'], 'Raw size or SHA256 differs'))
        except (OSError, ValueError) as exc:
            issues.append(issue('invalid_artifact', item['path'], str(exc)))
    # Unlisted payload and links cannot travel unnoticed with a distributable bundle.
    for path in sorted(bundle.rglob('*')):
        relative = path.relative_to(bundle).as_posix()
        if path.is_symlink():
            issues.append(issue('untrusted_link', relative, 'Symlinks are forbidden'))
        elif path.is_file() and relative not in listed:
            issues.append(issue('unlisted_artifact', relative, 'Every payload file must be declared'))
    return report(issues, packageId=manifest['packageId'], artifactCount=len(manifest['artifacts']))


def build(plan_path, source_root, output, *, artifact_root=ROOT / 'artifacts'):
    source_root = Path(source_root).resolve()
    output = Path(output).resolve()
    artifact_root = Path(artifact_root).resolve()
    if output == artifact_root or not output.is_relative_to(artifact_root) or output.exists():
        return report([issue('invalid_output', output, 'Use a new child directory inside artifacts')])
    try:
        plan = load_json(plan_path)
        if not isinstance(plan, dict) or not isinstance(plan.get('artifacts'), list):
            raise ValueError('Expected a plan object and artifacts array')
        manifest = {key: value for key, value in plan.items() if key != 'artifacts'}
        manifest['artifacts'] = []
        inputs = []
        issues = []
        for item in plan['artifacts']:
            if not isinstance(item, dict):
                issues.append(issue('invalid_plan_artifact', 'artifacts', 'Expected an artifact object'))
                continue
            entry = {key: value for key, value in item.items() if key != 'source'}
            if 'sha256' in entry or 'bytes' in entry:
                issues.append(issue('invalid_plan_artifact', entry.get('id', ''), 'Hashes/sizes are computed, not supplied'))
            try:
                source = safe_path(source_root, item.get('source'))
                if source.is_relative_to(output) or output.is_relative_to(source):
                    raise ValueError('Output overlaps an input')
                data = source.read_bytes()
                entry.update(sha256=sha256(data).hexdigest(), bytes=len(data))
                inputs.append((entry, data))
            except FileNotFoundError as exc:
                issues.append(issue('missing_source', item.get('source', ''), str(exc), 'MISSING'))
                entry.update(sha256='0' * 64, bytes=0)
            except (OSError, ValueError) as exc:
                issues.append(issue('invalid_source', item.get('source', ''), str(exc)))
                entry.update(sha256='0' * 64, bytes=0)
            manifest['artifacts'].append(entry)
        issues.extend(manifest_issues(manifest))
        if issues:
            return report(issues)
        output.parent.mkdir(parents=True, exist_ok=True)
        # Own one fresh temporary child, inspect it fully, then publish by rename.
        stage = Path(tempfile.mkdtemp(prefix='.evidence-', dir=output.parent)).resolve()
        try:
            if not stage.is_relative_to(artifact_root):
                raise ValueError('Staging directory escapes artifacts')
            for entry, data in inputs:
                target = safe_path(stage, entry['path'], portable=True)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            (stage / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n',
                                               encoding='utf-8', newline='\n')
            checked = verify(stage)
            if checked['status'] != 'PASS':
                return checked
            if output.exists():
                raise ValueError('Output appeared during build; refusing replacement')
            stage.rename(output)
            return report([], packageId=manifest['packageId'], artifactCount=len(inputs), output=str(output))
        finally:
            if stage.exists() and stage.parent == output.parent and stage.is_relative_to(artifact_root):
                shutil.rmtree(stage)
    except (OSError, ValueError, TypeError) as exc:
        return report([issue('build_failed', plan_path, str(exc))])


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    commands = cli.add_subparsers(dest='command', required=True)
    pack = commands.add_parser('build')
    pack.add_argument('--plan', type=Path, required=True)
    pack.add_argument('--source-root', type=Path, required=True)
    pack.add_argument('--output-dir', type=Path, required=True)
    check = commands.add_parser('verify')
    check.add_argument('bundle', type=Path)
    for command in (pack, check):
        command.add_argument('--report', type=Path)
    args = cli.parse_args()
    if args.report and not args.report.resolve().is_relative_to((ROOT / 'artifacts').resolve()):
        cli.error('Reports must be inside artifacts')
    if args.report and args.command == 'verify' and args.report.resolve().is_relative_to(args.bundle.resolve()):
        cli.error('Save verification reports outside the immutable bundle')
    if args.report and args.command == 'build' and args.report.resolve().is_relative_to(args.output_dir.resolve()):
        cli.error('Save build reports outside the immutable bundle')
    packet = build(args.plan, args.source_root, args.output_dir) if args.command == 'build' else verify(args.bundle)
    payload = json.dumps(packet, ensure_ascii=False, indent=2) + '\n'
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(payload, encoding='utf-8', newline='\n')
    print(payload, end='')
    return 0 if packet['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
