"""Read-only environment and evidence diagnostics; never a native release gate."""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import importlib.metadata
import json
import os
from pathlib import Path, PureWindowsPath
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
GROUPS = ('core', 'runtime', 'historical', 'native')


def result(identifier, status, detail, **extra):
    return {'id': identifier, 'status': status, 'detail': detail, **extra}


def status_of(checks):
    return next((s for s in ('FAIL', 'MISSING', 'NOT_RUN')
                 if any(c['status'] == s for c in checks)), 'PASS')


def evidence_check(root, manifest):
    """List every missing or changed manifest-bound file without modifying bytes."""
    root = Path(root).resolve()
    identifier = str(manifest).replace('\\', '/')
    path = (root / manifest).resolve()
    if not path.is_relative_to(root):
        return result(identifier, 'FAIL', 'Manifest escapes repository root')
    if not path.is_file():
        return result(identifier, 'MISSING', 'Manifest is unavailable')
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(data, dict):
            raise ValueError('Expected a manifest object')
        files = data['files']
        if data.get('status') != 'PASS' or not isinstance(files, dict) or not files:
            raise ValueError('Expected a PASS manifest with nonempty files mapping')
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return result(identifier, 'FAIL', 'Invalid manifest: ' + str(exc))
    issues = []
    for relative, expected in files.items():
        if (not isinstance(expected, str) or not re.fullmatch('[0-9a-f]{64}', expected)
                or Path(relative).is_absolute() or PureWindowsPath(relative).drive):
            issues.append(result(relative, 'FAIL', 'Invalid path or SHA256'))
            continue
        target = (root / relative).resolve()
        if not target.is_relative_to(root):
            issues.append(result(relative, 'FAIL', 'Evidence escapes repository root'))
            continue
        if not target.is_file():
            issues.append(result(relative, 'MISSING', 'Manifest-bound evidence is unavailable'))
            continue
        try:
            actual = sha256(target.read_bytes()).hexdigest()
            if actual != expected:
                issues.append(result(relative, 'FAIL', 'Evidence SHA256 differs',
                                     expectedSha256=expected, actualSha256=actual))
        except OSError as exc:
            issues.append(result(relative, 'FAIL', str(exc)))
    return result(identifier, status_of(issues), 'Byte integrity only; native acceptance is NOT_RUN',
                  checkedFileCount=len(files), issues=issues)


def requirements(root, filename, seen=None):
    seen = set() if seen is None else seen
    path = (root / filename).resolve()
    if not path.is_relative_to(root) or path in seen:
        raise ValueError('Invalid or recursive requirements include: ' + filename)
    seen.add(path)
    pins = {}
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.split('#', 1)[0].strip()
        if not line:
            continue
        if line.startswith('-r '):
            pins.update(requirements(root, (path.parent / line[3:].strip()).relative_to(root).as_posix(), seen))
        else:
            name, version = line.split('==', 1)
            pins[name] = version
    seen.remove(path)
    return pins


def runtime_reference(root):
    base = root / 'artifacts/task-006'
    needed = ('component_ir.json', 'runtime_manifest.json', 'extraction_report.json')
    missing = [name for name in needed if not (base / name).is_file()]
    if missing:
        return result('runtime-reference', 'MISSING', 'Run the official extractor first', missing=missing)
    try:
        report = json.loads((base / 'extraction_report.json').read_text(encoding='utf-8'))
        bundle = json.loads((base / 'component_ir.json').read_text(encoding='utf-8'))
        manifest = json.loads((base / 'runtime_manifest.json').read_text(encoding='utf-8'))
        if not all(isinstance(value, dict) for value in (report, bundle, manifest)):
            raise ValueError('Expected extraction JSON objects')
        if report['status'] != 'PASS' or bundle['status'] != 'PASS':
            raise ValueError('Official extraction is not PASS')
        for name, key in [('component_ir.json', 'componentIrSha256'),
                          ('runtime_manifest.json', 'runtimeManifestSha256')]:
            if sha256((base / name).read_bytes()).hexdigest() != report[key]:
                raise ValueError('Extraction artifact changed: ' + name)
        lock_bytes = (root / 'component-builder/source-reader/source-lock.json').read_bytes()
        lock = json.loads(lock_bytes)
        if (manifest['provenance']['sourceLockSha256'] != sha256(lock_bytes).hexdigest()
                or report['sourceVersion'] != lock['sourceVersion']):
            raise ValueError('Reference belongs to another official source lock')
        renderer = root / 'component-builder/runtime-renderer/extract.mjs'
        if manifest['provenance']['rendererSha256'] != sha256(renderer.read_bytes()).hexdigest():
            raise ValueError('Reference belongs to another renderer')
        if sha256((base / 'official-runtime-gallery.png').read_bytes()).hexdigest() != manifest['gallerySha256']:
            raise ValueError('Reference gallery changed')
        if {c['componentType'] for c in bundle['components']} != {'Button', 'Input', 'Select'}:
            raise ValueError('Default reference must contain Button/Input/Select')
        for component in bundle['components']:
            screenshot = component['screenshot']
            path = (base / screenshot['path']).resolve()
            if not path.is_relative_to(base.resolve()):
                raise ValueError('Screenshot escapes reference directory')
            if sha256(path.read_bytes()).hexdigest() != screenshot['sha256']:
                raise ValueError('Reference screenshot changed')
    except FileNotFoundError as exc:
        return result('runtime-reference', 'MISSING', str(exc))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return result('runtime-reference', 'FAIL', str(exc))
    return result('runtime-reference', 'PASS', 'Extraction artifact hashes verified; fidelity NOT_RUN')


def font_reference(root, identity_path=None):
    path = Path(identity_path) if identity_path else root / 'adapters/figma/metadata/font-file-identity.json'
    try:
        identity = json.loads(path.read_text(encoding='utf-8'))
        if identity.get('status') != 'PASS' or identity.get('scope') != 'source_font_file_metadata':
            raise ValueError('Passed font metadata required')
        rows = [r for r in identity['requirements'] if r['familyName'] == 'PingFang SC']
        if len(rows) != 1 or len(rows[0]['matches']) != 1:
            raise ValueError('Ambiguous PingFang file identity')
        match = rows[0]['matches'][0]
        if sha256(Path(match['path']).read_bytes()).hexdigest() != match['fileSha256']:
            raise ValueError('Font file hash differs; no substitution permitted')
    except FileNotFoundError as exc:
        return result('runtime-font-file', 'MISSING', str(exc))
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        return result('runtime-font-file', 'FAIL', str(exc))
    return result('runtime-font-file', 'PASS', 'Raw file SHA256 matches supplied metadata', identity=str(path))


def diagnose(group='core', root=ROOT, node=None, font_identity=None):
    root = Path(root).resolve()
    checks = [result('python', 'PASS' if sys.version_info >= (3, 11) else 'FAIL',
                     sys.version.split()[0], executable=sys.executable)]
    try:
        pins = requirements(root, 'requirements-dev.txt')
        if group in ('historical', 'native'):
            pins.update(requirements(root, 'requirements-diagnostics.txt'))
        for name, expected in pins.items():
            try:
                actual = importlib.metadata.version(name)
                checks.append(result('python-package:' + name, 'PASS' if actual == expected else 'FAIL',
                                     actual, expectedVersion=expected))
            except importlib.metadata.PackageNotFoundError:
                checks.append(result('python-package:' + name, 'MISSING', 'Install pinned requirements',
                                     expectedVersion=expected))
    except (OSError, ValueError) as exc:
        checks.append(result('requirements', 'FAIL', str(exc)))
    if group in ('runtime', 'native'):
        executable = node or shutil.which('node')
        if executable:
            try:
                process = subprocess.run([executable, str(root / 'scripts/environment.mjs')],
                                         cwd=root, capture_output=True, text=True, encoding='utf-8',
                                         timeout=45, check=False)
                packet = json.loads(process.stdout)
                if not isinstance(packet.get('checks'), list) or process.returncode:
                    raise ValueError(process.stderr or 'Environment probe failed')
                checks.extend(packet['checks'])
            except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
                checks.append(result('node-probe', 'FAIL', str(exc)))
        else:
            checks.append(result('node', 'MISSING', 'Node.js 24+ required'))
        # The existing Node host test invokes this exact Windows venv path.
        host_python = root / '.venv/Scripts/python.exe'
        checks.append(result('host-test-python', 'PASS' if host_python.is_file() else 'MISSING',
                             str(host_python)))
        checks.append(runtime_reference(root))
        checks.append(font_reference(root, font_identity or os.environ.get('UI_DESIGN_FONT_IDENTITY')))
    if group in ('historical', 'native'):
        for version in ('0.2.1', '0.3.0'):
            checks.append(evidence_check(root, f'releases/component-library-{version}/manifest.json'))
    if group == 'native':
        checks.append(result('live-platform-and-fonts', 'NOT_RUN',
                             'Platform access, legal fonts, independent readback, PNG and visual review '
                             'must be verified in the actual target session'))
    return {'scope': 'development-environment', 'reportVersion': '0.1.0', 'group': group,
            'status': status_of(checks), 'checks': checks,
            'counts': dict(Counter(c['status'] for c in checks)),
            'limitations': ['Prerequisites and byte integrity only; not proof of test success, '
                            'font identity, FreeType calibration or live platform access'],
            'nativeExecution': 'NOT_RUN', 'releaseReady': False}


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--group', choices=GROUPS, default='core')
    cli.add_argument('--node', help='Explicit Node executable')
    cli.add_argument('--font-identity', type=Path, help='Explicit identity with unchanged font file hashes')
    cli.add_argument('--output', type=Path, help='Save a report only inside artifacts')
    args = cli.parse_args()
    if args.output and not args.output.resolve().is_relative_to((ROOT / 'artifacts').resolve()):
        cli.error('Reports must be saved inside artifacts')
    report = diagnose(args.group, node=args.node, font_identity=args.font_identity)
    payload = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding='utf-8', newline='\n')
    print(payload, end='')
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
