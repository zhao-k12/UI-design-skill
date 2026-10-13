"""Run declared test groups only after their environment diagnostics pass."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.doctor import ROOT, GROUPS, diagnose

CORE_MODULES = (
    'tests.test_architecture', 'tests.test_ui_ir', 'tests.test_tokens',
    'tests.test_layout', 'tests.test_layout_builder', 'tests.test_component_registry',
    'tests.test_prototype_parser', 'tests.test_structure_gate', 'tests.test_pipeline',
    'tests.test_doctor',
    'tests.test_evidence_package',
    'tests.test_browser_archives',
    'tests.test_font_relocation',
    'tests.test_default_font_profile',
    'tests.test_font_source_compatibility',
    'tests.test_font_adaptation_manifest',
    'tests.test_button_candidate_audit_v02',
    'tests.test_penpot_button_candidate_audit_v02',
    'tests.test_font_adaptation_manifest_v021',
    'tests.test_button_fidelity_diagnostics_v02',
    'tests.test_default_font_button_gate_v02',
    'tests.test_default_font_button_admission',
)


def command_for(group, root=ROOT, python=sys.executable, node=None):
    if group == 'core':
        return [python, '-X', 'utf8', '-m', 'unittest', *CORE_MODULES]
    if group == 'runtime':
        return [node or shutil.which('node'), '--test',
                *[str(p) for p in sorted((root / 'tests').glob('*.test.mjs'))]]
    if group == 'historical':
        return [python, '-X', 'utf8', '-m', 'unittest', 'discover', '-s', 'tests']
    raise ValueError('Live native acceptance requires the actual target session')


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--group', choices=GROUPS, default='core')
    cli.add_argument('--node')
    cli.add_argument('--font-identity', type=Path)
    cli.add_argument('--output-dir', type=Path, required=True)
    args = cli.parse_args()
    output = args.output_dir.resolve()
    if not output.is_relative_to((ROOT / 'artifacts').resolve()):
        cli.error('Use an artifacts task directory')
    output.mkdir(parents=True, exist_ok=True)
    report = diagnose(args.group, node=args.node, font_identity=args.font_identity)
    write = lambda name, data: (output / name).write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    write('environment.json', report)
    summary = {'scope': 'development-checks', 'group': args.group, 'status': report['status'],
               'tests': 'NOT_RUN', 'nativeExecution': 'NOT_RUN', 'releaseReady': False}
    # Invalidate earlier success before attempting any subprocess.
    write('checks.json', summary)
    if report['status'] != 'PASS':
        print(json.dumps(summary)); return 1
    command = command_for(args.group, node=args.node)
    summary.update(status='RUNNING', tests='RUNNING', command=command)
    write('checks.json', summary)
    try:
        with (output / 'tests.log').open('w', encoding='utf-8') as log:
            environment = os.environ.copy()
            if args.font_identity:
                environment['UI_DESIGN_FONT_IDENTITY'] = str(args.font_identity.resolve())
            process = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, env=environment,
                                     check=False)
        summary.update(status='PASS' if process.returncode == 0 else 'FAIL',
                       tests='PASS' if process.returncode == 0 else 'FAIL',
                       exitCode=process.returncode, command=command, log='tests.log')
    except (OSError, KeyboardInterrupt) as exc:
        summary.update(status='FAIL', tests='PARTIAL', issues=[str(exc)])
    write('checks.json', summary)
    print(json.dumps(summary))
    return 0 if summary['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
