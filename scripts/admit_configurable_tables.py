"""Re-run both platform gates and genuine instances before an explicit release."""
from copy import deepcopy
from importlib import import_module
import importlib.util
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from adapters.configurable_table import require
from adapters.figma.configurable_table_fidelity import evaluate as figma_gate,META as FMETA,SOURCE,FONTS,APPROVED_DECISION_SHA,transport
from adapters.figma.configurable_table_instance_qa import validate as figma_instances
from adapters.penpot.configurable_table_fidelity import evaluate as penpot_gate
from adapters.penpot.configurable_table_instance_qa import validate as penpot_instances,META as PMETA
from adapters.component_bindings import ComponentBindings
from validators.ui_ir import load_json
from validators.visual.fidelity import digest,file_hash

CASES=('two-column','four-column')
RELEASE=ROOT/'releases/component-library-0.2.1'


def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')


def runtime_source():
    source=(ROOT/'core/component-resolver/registry.py').read_text(encoding='utf-8')
    marker='    def __init__(self, data, evidence=None, *, allow_test_fixtures=False):\n'
    require(source.count(marker)==1,'registry_constructor_migration_source_changed')
    source=source.replace(marker,marker+'        if data.get("libraryVersion") != "0.2.1":\n            raise ComponentError("library_version_mismatch", "", "Explicit component library 0.2.1 required")\n')
    source=source.replace("report.get('gateVersion')=='0.2.0'", "report.get('gateVersion') in ('0.2.0','0.2.1')")
    source=source.replace("screenshot.get('policy')=='evidence-bound-edges-0.2.0'", "screenshot.get('policy')=='evidence-bound-edges-'+report['gateVersion']")
    scoped=tuple(load_json(SOURCE/case/'component_ir.json')['components'][0]['logicalComponentId'] for case in CASES)
    marker='                    if (not policy_pass or report.get("admissionEligible") is not True or'
    guard="                    if report.get('gateVersion')=='0.2.1':\n                        policy_pass=policy_pass and entry['componentType']=='Table' and logical_id in "+repr(scoped)+" and report.get('pixelRegionPolicy')=='positive-area-intersection'\n"
    require(source.count(marker)==1,'registry_runtime_migration_source_changed')
    return source.replace(marker,guard+marker)


def admit(output):
    output=Path(output).resolve();require(output.is_relative_to(ROOT/'artifacts') and not output.exists(),'new_admission_output_required')
    require(not RELEASE.exists(),'release_already_exists_requires_read')
    output.mkdir(parents=True)
    fonts=load_json(PMETA/'font-discovery.json')['result']['fonts']
    bindings={f['family']:{'fontId':f['fontId'],'fontVariantId':'normal-400'} for f in fonts if f['family'] in FONTS}
    reports={};proofs={};instances={};native={}
    for i,case in enumerate(CASES):
        f=figma_gate(case,output/'figma'/case)
        p,b,c=penpot_gate(PMETA/(case+'-capture-after-background.json'),PMETA/case/'after-background',SOURCE/case,FONTS,bindings,output/'penpot'/case)
        require(f['status']==p['status']=='PASS' and f['admissionEligible'] and p['admissionEligible'],'dual_platform_fidelity_required')
        instance_f=figma_instances(transport(FMETA/f'instance-readback-pieces-{i}.json'),case)
        instance_p=penpot_instances(load_json(PMETA/(case+'-instance-after-placement.json')),case)
        require(instance_f['status']==instance_p['status']=='PASS','dual_platform_instances_required')
        for platform,metadata,report in [('figma',FMETA,f),('penpot',PMETA,p)]:
            review=load_json(metadata/'visual-review.json')
            require(review['scope']=='task019_table_visual_review' and review['status']=='PASS' and review['reviewedBy']=='codex-visual-inspection' and review['nativePngHashes'][case]==report['candidateScreenshotSha256'],'actual_native_visual_review_required')
        reports[case]={'figma':f,'penpot':p};proofs[case]={'figma':load_json(output/'figma'/case/'proof.json'),'penpot':b};instances[case]={'figma':instance_f,'penpot':instance_p}
        native[case]=load_json(PMETA/(case+'-capture-after-background.json'))['result']
    catalog=deepcopy(load_json(ROOT/'registries/components/catalog.json'));old_hash=digest(catalog)
    catalog['libraryVersion']='0.2.1';fidelity=deepcopy(load_json(ROOT/'registries/components/fidelity-reports.json'))
    for case in CASES:
        report=reports[case]['figma'];logical=report['logicalComponentId'];report_id=logical+'.native-0.2.1'
        catalog['components'][logical]={'componentType':'Table','tier':'base','status':'active','variants':['default'],'defaultVariant':'default','slots':[],
            'fidelity':{'reportId':report_id,'reportSha256':digest(report),'componentIrSha256':report['componentIrSha256']}}
        fidelity[report_id]=report
    # A versioned neutral Core copy recognizes only these two new policy scopes.
    # The original Core, default catalog and all historical manifests stay intact.
    runtime=RELEASE/'core/component-resolver/registry.py';runtime.parent.mkdir(parents=True)
    runtime.write_text(runtime_source(),encoding='utf-8',newline='\n')
    schema=RELEASE/'schemas/component-registry.schema.json';schema.parent.mkdir(parents=True);schema.write_bytes((ROOT/'schemas/component-registry.schema.json').read_bytes())
    spec=importlib.util.spec_from_file_location('table_library_release_registry',runtime);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    registry=module.ComponentRegistry(catalog,fidelity)
    write(RELEASE/'catalog.json',catalog);write(RELEASE/'fidelity-reports.json',fidelity)
    release_paths=[runtime,schema,RELEASE/'catalog.json',RELEASE/'fidelity-reports.json']
    for platform in ('figma','penpot'):
        metadata=ROOT/f'adapters/{platform}/metadata/component-library-0.2.1';require(not metadata.exists(),'platform_release_already_exists')
        bound=deepcopy(load_json(ROOT/f'adapters/{platform}/metadata/component-bindings.json'))
        bound.update(libraryVersion='0.2.1',registrySha256=registry.fingerprint)
        bundles={};native_receipts=deepcopy(load_json(PMETA.parent/'native-fidelity.json')) if platform=='penpot' else {}
        for case in CASES:
            logical=reports[case]['figma']['logicalComponentId'];entry=catalog['components'][logical]['fidelity']
            reference=reports[case]['figma']['capture']['captureId'].split('/')[-1] if platform=='figma' else native[case]['componentReference']
            file='0vGWSRoLxBiVPXiZ8xJAX9' if platform=='figma' else native[case]['fileReference']
            bound['bindings'][logical]={'variants':{'default':{'kind':'component','fileReference':file,'componentReference':reference,'fidelityReportSha256':entry['reportSha256']}}}
            bundles[logical]={'gateReport':reports[case][platform],'proofBundle':proofs[case][platform],'instanceQa':instances[case][platform]}
            if platform=='penpot':
                report=reports[case][platform];bundle=proofs[case][platform]
                native_receipts[reference]={'platform':'penpot','status':'PASS','fileReference':file,'componentReference':reference,'logicalId':logical,'variant':'default','sourceIrSha256':entry['componentIrSha256'],'registryReportSha256':entry['reportSha256'],'nativeEvidence':native[case],'nativeEvidenceSha256':digest(native[case]),'gateReport':report,'verifiedReportSha256':digest(report),'proofBundle':bundle,'proofBundleSha256':digest(bundle),'nativePngSha256':report['candidateScreenshotSha256']}
        ComponentBindings(bound,registry,platform=platform)
        for name,data in [('component-bindings.json',bound),('fidelity-proof-bundles.json',bundles),('native-fidelity.json',native_receipts)]:
            write(metadata/name,data);release_paths.append(metadata/name)
    evidence=RELEASE/'evidence'
    for case in CASES:
        for platform in ('figma','penpot'):
            for name in ('proof.json','candidate.json','gate-report.json','native.png'):
                target=evidence/platform/case/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((output/platform/case/name).read_bytes());release_paths.append(target)
    decision=ROOT/'.dev/TASK-019_ARIAL_ENCODING_DECISION.md'
    require(file_hash(decision)==APPROVED_DECISION_SHA,'approved_decision_changed')
    inputs=[decision,Path(__file__)]+[ROOT/name for name in ('adapters/figma/configurable_table_fidelity.py','adapters/penpot/configurable_table_fidelity.py','adapters/penpot/table_pixel_coverage.py','adapters/figma/true_type_encoding_diagnostic.py','adapters/component_library_versions.py','adapters/figma/configurable_table_instance_qa.py','adapters/penpot/configurable_table_instance_qa.py','adapters/penpot/configurable_table_admission.py','adapters/penpot/configurable_table_compiler.py','adapters/configurable_table.py','adapters/figma/configurable_font_calibration.py','adapters/figma/font_outline_comparison.py','adapters/figma/outline_geometry.py','adapters/figma/configurable_table_probes.mjs','adapters/penpot/configurable_table_svg_probe.mjs','component-builder/runtime-renderer/native-svg-probe.mjs','requirements.txt','requirements-native-qa.txt')]
    for directory in (FMETA,PMETA,SOURCE):inputs.extend(p for p in directory.rglob('*') if p.is_file())
    manifest={'scope':'explicit-component-library-release','status':'PASS','libraryVersion':'0.2.1','registrySha256':registry.fingerprint,'baseRegistrySha256':old_hash,'defaultRegistryUnchanged':file_hash(ROOT/'registries/components/catalog.json'),'approvedDecisionSha256':APPROVED_DECISION_SHA,'instances':instances,'files':{p.relative_to(ROOT).as_posix():file_hash(p) for p in sorted(set(release_paths+inputs))},'capability':'Only the two frozen Table bodies; slots and data rewriting are unsupported. Explicit opt-in required; historical program locks are retained.'}
    write(RELEASE/'manifest.json',manifest)
    write(output/'admission.json',{'status':'PASS','release':RELEASE.relative_to(ROOT).as_posix(),'registrySha256':registry.fingerprint,'instances':instances})
    return manifest


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    result=admit(args.output);print(json.dumps({'status':result['status'],'libraryVersion':result['libraryVersion'],'registrySha256':result['registrySha256']}))
