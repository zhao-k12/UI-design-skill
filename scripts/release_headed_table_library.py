"""Freeze explicit 0.3.0 from completed, independently validated TASK-020 gates."""
from copy import deepcopy
import json
from pathlib import Path
from shutil import copytree,copy2
from adapters.component_library_versions import load as load_base
from adapters.headed_table_policy import SCOPE,DECISION_SHA256
from adapters.headed_table import require
from validators.ui_ir import ROOT,load_json
from validators.visual.fidelity import file_hash,digest

def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

def release():
    base,base_bindings=load_base('0.2.1')
    directory=ROOT/'releases/component-library-0.3.0';require(not directory.exists(),'headed_release_requires_new_directory')
    directory.mkdir(parents=True)
    old=ROOT/'releases/component-library-0.2.1'
    copytree(old/'schemas',directory/'schemas')
    code=(old/'core/component-resolver/registry.py').read_text(encoding='utf8')
    code=code.replace('data.get("libraryVersion") != "0.2.1"','data.get("libraryVersion") != "0.3.0"').replace('Explicit component library 0.2.1 required','Explicit component library 0.3.0 required')
    code=code.replace("in ('0.2.0','0.2.1')","in ('0.2.0','0.2.1','0.3.0')")
    guard="""                    if report.get('gateVersion')=='0.3.0':
                        approved_scope=APPROVED_SCOPE
                        context=checks.get('pngContext',{})
                        coverage=checks.get('horizontalCoverage',[])
                        expected=approved_scope.get(logical_id)
                        dual=report.get('dualPlatformReports',{})
                        policy_pass=(policy_pass and expected is not None and entry['componentType']=='Table' and
                            report.get('componentIrSha256')==expected[0] and report.get('decisionSha256')=='DECISION_HASH' and
                            report.get('pixelRegionPolicy')=='positive-area-intersection-no-padding' and
                            context.get('status')=='PASS' and context.get('dimensions')==list(expected[1:]) and
                            context.get('lastRowAlpha') in (223,255) and context.get('otherRowsAlpha')==255 and
                            context.get('nativePngSha256')==report.get('candidateScreenshotSha256') and
                            isinstance(coverage,list) and len(coverage)==(4 if expected[1]==720 else 6) and
                            all(c.get('status')=='PASS' and c.get('rows') and all(r.get('coveredPixels')==expected[1] for r in c['rows']) for c in coverage) and
                            isinstance(dual,dict) and set(dual)=={'figma','penpot'} and
                            all(d.get('status')=='PASS' and d.get('admissionEligible') is True and d.get('gateVersion')=='0.3.0' and
                                d.get('logicalComponentId')==logical_id and d.get('componentIrSha256')==expected[0] and
                                d.get('decisionSha256')==report.get('decisionSha256') and d.get('issues')==[] and
                                d.get('checks',{}).get('screenshot',{}).get('changedPixelsOutsidePermittedRegions')==0 and
                                d.get('checks',{}).get('screenshot',{}).get('changedPixelsOutsideEdgeBand')==0 and
                                all(d.get('checks',{}).get('normalizationProofs',{}).get(k)=='PASS' for k in required)
                                for d in dual.values()))
"""
    approved={key:(value[0],value[1],135 if value[1]==720 else 231) for key,value in SCOPE.items()}
    guard=guard.replace('APPROVED_SCOPE',repr(approved)).replace('DECISION_HASH',DECISION_SHA256)
    code=code.replace('                    if (not policy_pass',guard+'                    if (not policy_pass')
    path=directory/'core/component-resolver/registry.py';path.parent.mkdir(parents=True);path.write_text(code,encoding='utf8',newline='\n')
    catalog=base.snapshot;catalog['libraryVersion']='0.3.0'
    reports=load_json(old/'fidelity-reports.json');new_bindings={};native_records={}
    for platform in ('figma','penpot'):
        new_bindings[platform]=load_json(ROOT/f'adapters/{platform}/metadata/component-library-0.2.1/component-bindings.json')
        new_bindings[platform]['libraryVersion']='0.3.0'
        native_records[platform]=load_json(ROOT/f'adapters/{platform}/metadata/component-library-0.2.1/native-fidelity.json')
    for case,logical in zip(('two-column','four-column'),SCOPE):
        gates={};proofs={}
        for platform in ('figma','penpot'):
            source=ROOT/f'artifacts/task-020/full-{case}-{platform}-v4'
            gate=load_json(source/'gate-report.json');proof=load_json(source/'proof.json')
            require(gate['status']=='PASS' and gate['admissionEligible'] and gate['logicalComponentId']==logical and digest(proof)==gate['capture']['proofBundleSha256'],'headed_release_gate_binding')
            copytree(source,directory/'evidence'/platform/case);gates[platform]=gate;proofs[platform]=proof
        aggregate=deepcopy(gates['penpot']);aggregate['dualPlatformReports']=gates
        report_id=logical+'.native-0.3.0';reports[report_id]=aggregate
        descriptor={'componentType':'Table','tier':'base','status':'active','variants':['default'],'defaultVariant':'default','slots':[],
                    'fidelity':{'reportId':report_id,'reportSha256':digest(aggregate),'componentIrSha256':SCOPE[logical][0]}}
        catalog['components'][logical]=descriptor
        for platform in ('figma','penpot'):
            meta=ROOT/f'adapters/{platform}/metadata/headed-table-native'
            if platform=='figma':
                main='82:4' if case=='two-column' else '82:24';file='0vGWSRoLxBiVPXiZ8xJAX9';native=load_json(meta/(case+'-readback.json'))['nativeEvidence']
            else:
                native=load_json(meta/'header-union'/('discovery-2.json' if case=='two-column' else 'discovery-3.json'))['result'];main=native['componentReference'];file=native['fileReference']
            new_bindings[platform]['bindings'][logical]={'variants':{'default':{'kind':'component','fileReference':file,'componentReference':main,'fidelityReportSha256':digest(aggregate)}}}
            gate=aggregate if platform=='penpot' else gates[platform];proof=proofs[platform]
            native_records[platform][main]={'platform':platform,'status':'PASS','fileReference':file,'componentReference':main,'logicalId':logical,'variant':'default','sourceIrSha256':SCOPE[logical][0],'registryReportSha256':digest(aggregate),'nativeEvidence':native,'nativeEvidenceSha256':digest(native),'gateReport':gate,'verifiedReportSha256':digest(gate),'proofBundle':proof,'proofBundleSha256':digest(proof),'nativePngSha256':gate['nativePngSha256']}
    write(directory/'catalog.json',catalog);write(directory/'fidelity-reports.json',reports)
    for platform in ('figma','penpot'):
        new_bindings[platform]['registrySha256']=digest(catalog)
        path=ROOT/f'adapters/{platform}/metadata/component-library-0.3.0'
        write(path/'component-bindings.json',new_bindings[platform]);write(path/'native-fidelity.json',native_records[platform])
    files={}
    dependencies=[ROOT/'.dev/TASK-020_FIDELITY_DECISION.md',ROOT/'registries/components/catalog.json',ROOT/'adapters/headed_component_library.py']
    dependencies+=list(directory.rglob('*'))
    for platform in ('figma','penpot'):
        dependencies+=list((ROOT/f'adapters/{platform}/metadata/component-library-0.3.0').rglob('*'))
        dependencies+=list((ROOT/f'adapters/{platform}/metadata/headed-table-native').rglob('*'))
        dependencies+=list((ROOT/f'adapters/{platform}').glob('headed_table*'))
    dependencies+=list((ROOT/'adapters').glob('headed_table*.py'))
    dependencies+=list((ROOT/'component-builder/runtime-renderer/metadata/headed-table-source').rglob('*'))
    for path in dependencies:
        if path.is_file():files[path.relative_to(ROOT).as_posix()]=file_hash(path)
    write(directory/'manifest.json',{'scope':'explicit-component-library-release','status':'PASS','libraryVersion':'0.3.0','registrySha256':digest(catalog),'baseManifestSha256':file_hash(old/'manifest.json'),'decisionSha256':DECISION_SHA256,'files':files})
    print(json.dumps({'status':'PASS','libraryVersion':'0.3.0','componentsAdded':2,'registrySha256':digest(catalog)}))

if __name__=='__main__':release()
