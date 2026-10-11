"""Prepare scoped official Button/Input/Select candidates without executing Figma."""
import argparse
import hashlib
import json
from pathlib import Path
import re

from adapters.figma.button_candidate import prepare_button
from adapters.figma.form_candidate import prepare_form
from validators.ui_ir import ROOT, load_json


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def invalidate_owned_scripts(output):
    ledger_path = output / 'candidate_scripts.json'
    if not ledger_path.exists():
        return
    ledger = load_json(ledger_path)
    stale = []
    for name, expected in ledger.get('preservedScripts', ledger.get('scripts', {})).items():
        if not re.fullmatch(r'candidate-[a-zA-Z0-9_.-]+\.js', name):
            raise ValueError('invalid_candidate_script_ledger')
        path = output / name
        if path.exists():
            if sha256(path) != expected:
                raise ValueError('modified_candidate_script_preserved: ' + name)
            stale.append(path)
    # Verify the entire ledger before removing any old script.
    for path in stale:
        path.unlink()


def run(reference, font_evidence_path, discovery_path, *, output, file_reference, page_reference,
        logical_ids=None, bindings_path=None, button_baseline_directory=None):
    output = Path(output).resolve()
    inputs = [Path(reference).resolve(), Path(font_evidence_path).resolve().parent, Path(discovery_path).resolve().parent]
    if bindings_path:
        inputs.append(Path(bindings_path).resolve().parent)
    if button_baseline_directory:
        inputs.append(Path(button_baseline_directory).resolve())
    if not output.is_relative_to((ROOT / 'artifacts').resolve()) or any(output == item or output.is_relative_to(item) for item in inputs):
        raise ValueError('candidate_output_must_be_separate_artifacts')
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / 'candidate_build_report.json'
    report_path.write_text(json.dumps({'status':'RUNNING','nativeExecution':'NOT_RUN','components':[]}) + '\n', encoding='utf-8')
    report = {'scope':'figma_candidate_script_preparation','status':'FAIL','nativeExecution':'NOT_RUN',
        'fidelityGate':'NOT_RUN','admissionEligible':False,'components':[],'issues':[]}
    scripts = {}
    previous_scripts = {}
    ownership_verified = False
    ledger_path = output / 'candidate_scripts.json'
    try:
        if ledger_path.exists():
            previous_ledger = load_json(ledger_path)
            previous_scripts = previous_ledger.get('preservedScripts', previous_ledger.get('scripts', {}))
        invalidate_owned_scripts(output)
        ownership_verified = True
        # Prior script eligibility is revoked even if later input loading fails.
        ledger_path.write_text(json.dumps({'status':'RUNNING','scripts':{}}) + '\n', encoding='utf-8')
        bundle = load_json(Path(reference) / 'component_ir.json')
        evidence = load_json(font_evidence_path)
        discovery = load_json(discovery_path)
        bindings = load_json(bindings_path) if bindings_path else None
        available = {item['logicalComponentId']:item for item in bundle['components']}
        selected = list(logical_ids) if logical_ids is not None else list(available)
        if not selected or len(selected) != len(set(selected)) or any(item not in available for item in selected):
            raise ValueError('invalid_candidate_selection')
        planned = {}
        for logical_id in selected:
            if not re.fullmatch(r'[a-zA-Z][a-zA-Z0-9_.-]*', logical_id):
                raise ValueError('invalid_candidate_script_identity')
            kind = available[logical_id]['componentType']
            if kind not in ('Button','Input','Select'):
                raise ValueError('unsupported_candidate_component: ' + kind)
            prepare = prepare_button if kind == 'Button' else prepare_form
            component_report = prepare(reference,evidence,discovery,logical_id=logical_id,bindings=bindings,
                file_reference=file_reference,page_reference=page_reference,
                **({'baseline_directory':button_baseline_directory} if kind == 'Button' else {}))
            script = component_report.pop('script')
            component_report['logicalId'] = logical_id
            report['components'].append(component_report)
            if component_report['status'] == 'PASS' and script:
                planned['candidate-' + logical_id + '.js'] = script
        statuses = {item['status'] for item in report['components']}
        report['status'] = 'FAIL' if 'FAIL' in statuses else 'REVIEW' if 'REVIEW' in statuses else 'PASS'
        report['inputHashes'] = {'componentIr':sha256(Path(reference)/'component_ir.json'),
            'fontEvidence':sha256(font_evidence_path),'fontDiscovery':sha256(discovery_path),
            'fontBindings':sha256(bindings_path) if bindings_path else None}
        # Emit nothing if any requested component is blocked; select one explicitly to isolate it.
        if report['status'] == 'PASS':
            for name in planned:
                if (output/name).exists():
                    raise ValueError('unowned_candidate_script_preserved: ' + name)
            for name, script in planned.items():
                path = output / name
                path.write_text(script,encoding='utf-8')
                scripts[name] = sha256(path)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        report.update(status='FAIL',issues=[{'code':'invalid_candidate_preparation','detail':str(exc)}])
    report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    ledger = {'status':report['status'],'scripts':scripts}
    if previous_scripts and not ownership_verified:
        ledger['preservedScripts'] = previous_scripts
    ledger_path.write_text(json.dumps(ledger,indent=2)+'\n',encoding='utf-8')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference',type=Path,required=True)
    parser.add_argument('--font-evidence',type=Path,required=True)
    parser.add_argument('--discovery',type=Path,required=True)
    parser.add_argument('--bindings',type=Path)
    parser.add_argument('--button-baseline-evidence',type=Path,
        help='Explicit measured source/native evidence directory for calibrated Button candidates')
    parser.add_argument('--file-reference',required=True)
    parser.add_argument('--page-reference',required=True)
    parser.add_argument('--logical-id',action='append')
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    try:
        report=run(args.reference,args.font_evidence,args.discovery,output=args.output_dir,
            file_reference=args.file_reference,page_reference=args.page_reference,
            logical_ids=args.logical_id,bindings_path=args.bindings,
            button_baseline_directory=args.button_baseline_evidence)
    except (OSError,ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps({'status':report['status'],'components':[{'logicalId':item['logicalId'],
        'status':item['status'],'issues':item['issues']} for item in report['components']], 'issues':report['issues']},ensure_ascii=False))
    return 0 if report['status']=='PASS' else 1


if __name__=='__main__':
    raise SystemExit(main())
