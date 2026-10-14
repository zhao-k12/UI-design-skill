"""Approved, source-bound native master icon admission. Instances need separate QA."""
import base64
import hashlib
import json
from pathlib import Path
from validators.ui_ir import ROOT
from adapters.penpot.icon_raster_diagnostic import run

POLICY_VERSION='task-010-locked-icon-raster-edges/0.1.0'
BASE=ROOT/'adapters/penpot/metadata/icons-native-v1'
REPORT=BASE/'gate-report.json'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build_gate(base=BASE):
    base=Path(base)
    diagnostic=run(base)
    probe=json.loads((base/'latest-svg-probe.json').read_bytes())
    if probe['probeScriptSha256']!=sha(ROOT/'adapters/penpot/icon_svg_probe.mjs') or probe['sourcePlanSha256']!=sha(base.parent/'icon-source-plan/plan.json'):
        raise ValueError('icon_probe_script_or_source_plan_mismatch')
    receipt=json.loads((base/'latest-main-capture.json').read_bytes())['result']
    rows=[]
    paths=[base/'latest-main-capture.json',base/'content-capture.json',base/'latest-svg-probe.json',base.parent/'icon-source-plan/plan.json']
    paths += [ROOT/'adapters/penpot'/name for name in ('icon_admission.py','icon_raster_diagnostic.py','icon_native_evidence.py','icon_precision.py','icon_svg_probe.mjs')]
    for item in receipt['icons']:
        row=next(r for r in diagnostic['results'] if r['iconId']==item['iconId'])
        if not row['proposedEvidenceConditionsMet']:raise ValueError('icon_native_raster_evidence_failed')
        for extension,key in [('png','nativePngBase64'),('svg','nativeSvgBase64')]:
            path=base/('latest.'+item['iconId']+'.'+extension)
            if path.read_bytes()!=base64.b64decode(item[key],validate=True):raise ValueError('icon_saved_native_export_mismatch')
            paths.append(path)
        paths += [base/(item['iconId']+suffix) for suffix in ('.source.png','.native.png')]
        rows.append({'iconId':item['iconId'],'componentReference':item['componentReference'],'mainReference':item['mainReference'],'sourceSvgSha256':item['svgSha256'],'status':'PASS','nativePngSha256':row['nativePngSha256'],'sourcePixelsExact':row['sourcePixelsExact'],'changedPixels':row['changedPixels'],'changedPixelsOutsideVerifiedEdgeBand':row['changedPixelsOutsideVerifiedEdgeBand'],'inkRegionBoundsExact':row['inkRegionBoundsExact'],'inkAndVoidRegionCountsExact':row['inkAndVoidRegionCountsExact'],'independentNativePngBytesExact':True})
    return {'status':'PASS','scope':'production-native-icon-master-admission','policyVersion':POLICY_VERSION,'platform':'penpot','fileReference':receipt['fileReference'],'pageReference':receipt['pageReference'],'registrySha256':receipt['registrySha256'],'sourceVersion':receipt['sourceVersion'],'admissionEligible':True,'actualInstanceAcceptance':'NOT_RUN','productionScreenshot':'original-complete-main-native-png','results':rows,'proofFiles':[{'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p)} for p in paths]}


def verify_binding(icon_id,binding,file_reference,registry_sha):
    if binding.get('fidelityReportPath')=='adapters/penpot/metadata/icons-native-v02/gate-report.json':
        from adapters.penpot.icon_admission_v02 import verify_binding as verify_v02
        return verify_v02(icon_id,binding,file_reference,registry_sha)
    if binding.get('fidelityReportPath')!='adapters/penpot/metadata/icons-native-v1/gate-report.json' or binding.get('fidelityReportSha256')!=sha(REPORT):raise ValueError('missing_or_unbound_penpot_icon_fidelity')
    report=json.loads(REPORT.read_bytes())
    if report!=build_gate():raise ValueError('penpot_icon_fidelity_proof_changed')
    if report['fileReference']!=file_reference or report['registrySha256']!=registry_sha:raise ValueError('penpot_icon_fidelity_context_mismatch')
    row=next((r for r in report['results'] if r['iconId']==icon_id),None)
    if not row or row['componentReference']!=binding.get('componentReference') or row['sourceSvgSha256']!=binding.get('svgSha256'):raise ValueError('penpot_icon_fidelity_identity_mismatch')
    return row
