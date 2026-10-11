"""Evaluate actual captures, then register only complete PASS evidence."""
import argparse
from importlib import import_module
import json
from pathlib import Path
from adapters.figma.cross_renderer_normalization import run as normalize
from adapters.figma.table_fidelity import run as table_run
from adapters.component_bindings import ComponentBindings
from validators.ui_ir import ROOT,load_json
from validators.visual.fidelity import digest


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--file-reference',required=True);parser.add_argument('--register',action='store_true');args=parser.parse_args()
    metadata=ROOT/'adapters/figma/metadata';output=ROOT/'artifacts/task-009/fidelity-acceptance'
    output.mkdir(parents=True,exist_ok=True);target=output/'acceptance-report.json'
    target.write_text('{"status":"RUNNING","admissionEligible":false}\n',encoding='utf-8')
    try:
        result=normalize(metadata/'official-fixture-reference',metadata,file_reference=args.file_reference);table=table_run(metadata,file_reference=args.file_reference)
        reports=result['components']+[table['report']];proofs=result['proofs']+[table['proof']];candidates=result['candidates']+[table['candidate']]
        if any(r['status']!='PASS' or r['admissionEligible'] is not True for r in reports):raise ValueError('actual_component_fidelity_not_passed')
        reports_by_id={r['logicalComponentId']+'.native-0.2.0':r for r in reports}
        for r,p,c in zip(reports,proofs,candidates):
            if digest(p)!=c['capture']['proofBundleSha256']:raise ValueError('proof_bundle_binding_failed')
            (output/(r['logicalComponentId']+'.proof.json')).write_text(json.dumps(p,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            (output/(r['logicalComponentId']+'.candidate.json')).write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        if args.register:
            module=import_module('core.component-resolver.registry');catalog=load_json(ROOT/'registries/components/catalog.json')
            catalog['sourceVersion']=reports[0]['sourceVersion'];refs={'action.button.primary.medium':'18:5','form.input.default.medium':'12:8','form.select.default.medium':'12:15','data.table.default':'28:3'}
            for report_id,r in reports_by_id.items():
                entry=catalog['components'][r['logicalComponentId']];entry['status']='active';entry['fidelity']={'reportId':report_id,'reportSha256':digest(r),'componentIrSha256':r['componentIrSha256']}
            registry=module.ComponentRegistry(catalog,reports_by_id)
            bindings=load_json(metadata/'component-bindings.json');bindings.update(sourceVersion=registry.source_version,registrySha256=registry.fingerprint)
            bindings['bindings']={logical:{'variants':{'default':{'kind':'component','fileReference':args.file_reference,'componentReference':ref,'fidelityReportSha256':registry.inspect(logical)['fidelity']['reportSha256']}}} for logical,ref in refs.items()}
            ComponentBindings(bindings,registry,platform='figma')
            for path,data in [(ROOT/'registries/components/fidelity-reports.json',reports_by_id),(ROOT/'registries/components/catalog.json',catalog),(metadata/'component-bindings.json',bindings),(metadata/'fidelity-proof-bundles.json',{r['logicalComponentId']:p for r,p in zip(reports,proofs)})]:path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        report={'scope':'task009_actual_component_fidelity','status':'PASS','registered':args.register,'components':reports,'pageAcceptance':'NOT_RUN'}
    except Exception as exc:report={'scope':'task009_actual_component_fidelity','status':'FAIL','registered':False,'issues':[{'code':type(exc).__name__,'detail':str(exc)}]}
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({'status':report['status'],'registered':report['registered'],'issues':report.get('issues',[])}));return 0 if report['status']=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
