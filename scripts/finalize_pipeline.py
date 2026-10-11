"""Revalidate saved independent native evidence; never manufacture execution proof."""
import argparse
import base64
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from adapters.pipeline_qa import verify as native_qa
from adapters.figma.pipeline_fidelity import verify as figma_fidelity
from adapters.penpot.pipeline_fidelity import verify_instances
from validators.structure.gate import builder
from validators.ui_ir import load_json


def finalize(run,source,figma,penpot):
    read=lambda p:load_json(p)
    qa=read(run/'qa_report.json');document=read(run/'final_ui_ir.json');content=read(source/'content.json')
    if qa.get('scope')!='static-core-pipeline' or qa.get('status')!='PASS' or not qa.get('readyForAdapter'):raise ValueError('Current pure Core PASS required')
    digest=builder.fingerprint(document);reports={};plans={};executions={};captures={}
    for platform,base in [('figma',figma),('penpot',penpot)]:
        report=read(run/(platform+'_preflight.json'))
        if report['status']!='PASS':raise ValueError('Adapter preflight failed')
        plan=report['plan'];execution=read(base/'execution.json');capture=read(base/'capture.json')
        if plan['uiIrSha256']!=digest or qa['uiIrSha256']!=digest:raise ValueError('UI-IR differs from current native plan')
        native=native_qa(document,plan,execution,capture,content,platform)
        if native['status']!='PASS':raise ValueError(str(native['issues']))
        packet=read(base/'instances-capture.json')
        if platform=='figma':fidelity=figma_fidelity(plan,execution,capture,packet,read(base/'current-source-capture.json'))
        else:
            probe=read(base/'icon-svg-probe.json')
            if probe['nativeReceiptSha256']!=sha256((base/'instances-capture.json').read_bytes()).hexdigest() or probe['probeScriptSha256']!=sha256((ROOT/'adapters/penpot/pipeline_icon_probe.mjs').read_bytes()).hexdigest():raise ValueError('Icon probe execution binding differs')
            rows=verify_instances(plan,execution,capture,packet['result'],probe,base,read(base/'previous-instances-capture.json')['result'])
            fidelity={'status':'PASS','instances':rows,'uiIrSha256':digest,'scope':'penpot-static-pipeline-instance-fidelity','issues':[]}
        review=read(base/'visual-review.json')
        png=base64.b64decode(capture['nativePngBase64'],validate=True)
        if review.get('status')!='PASS' or review.get('reviewedBy')!='codex-visual-inspection' or review.get('nativePngSha256')!=sha256(png).hexdigest() or (base/'native-page.png').read_bytes()!=png:raise ValueError('Actual visual review or native PNG binding missing')
        native.update(fidelityGate=fidelity['status'],visualReview=review['status'])
        reports[platform]={'native':native,'fidelity':fidelity,'review':review}
        plans[platform]=plan;executions[platform]=execution;captures[platform]=capture
    # Both platforms consume the identical final tree, including all declared labels.
    fm=executions['figma']['nodeMap'];pm=executions['penpot']['nodeMap']
    fn={n['id']:n for n in captures['figma']['nodes']};pn={n['id']:n for n in captures['penpot']['contentNodes']}
    if set(fm)!=set(pm):raise ValueError('Cross-platform logical inventory differs')
    for uid in fm:
        f,p=fn[fm[uid]],pn[pm[uid]]
        if any(abs(f[k]-p[k])>1e-6 for k in ('x','y','width','height')) or f.get('characters')!=p.get('characters'):raise ValueError('Cross-platform geometry/content differs: '+uid)
    checkpoint=read(run/'checkpoint.json');manifest=read(run/'manifest.json')
    programs=[p for directory in ('core','schemas','validators') for p in (ROOT/directory).rglob('*') if p.is_file() and p.suffix in ('.py','.json')]
    current_program=builder.fingerprint({p.relative_to(ROOT).as_posix():sha256(p.read_bytes().replace(b'\r\n',b'\n')).hexdigest() for p in sorted(programs)})
    if manifest['programSha256']!=current_program or manifest['versions']['skill_version']!=(ROOT/'VERSION').read_text().strip():raise ValueError('Current release/program differs from locked pipeline')
    if checkpoint['manifestSha256']!=builder.fingerprint(manifest) or qa['manifestSha256']!=builder.fingerprint(manifest):raise ValueError('Manifest/checkpoint mismatch')
    for record in checkpoint['stages'].values():
        if sha256((run/record['artifact']).read_bytes()).hexdigest()!=record['artifactSha256']:raise ValueError('Stage checkpoint bytes differ')
    gates={
        'pageTreeComplete':qa['semanticItemCount']==len(content['items']),
        'deterministicLayout':qa['layoutRepeatable'],
        'ruleBasedLayoutWithoutFreeCoordinates':read(run/'layout_qa_report.json')['status']=='PASS',
        'platformNeutralUiIr':True,
        'figmaConsumesUiIr':reports['figma']['native']['status']=='PASS',
        'penpotConsumesSameUiIr':reports['penpot']['native']['status']=='PASS',
        'genuineUiInstances':all(reports[p]['native']['genuineInstances']==qa['instanceCount']+qa['iconCount'] for p in reports),
        'genuineIconInstances':all(sum('iconId' in row or 'exactMasterAffineFloat32' in row for row in reports[p]['fidelity']['instances'])==qa['iconCount'] for p in reports),
        'registeredComponentsOnly':all(reports[p]['fidelity']['status']=='PASS' for p in reports),
        'officialRuntimeExtraction':all(reports[p]['fidelity']['status']=='PASS' for p in reports),
        'officialComponentFidelity':all(reports[p]['fidelity']['status']=='PASS' for p in reports),
        'remixRegistryAndVersionLock':bool(manifest['versions']['remix_icon_version']),
        'savedIntermediateJson':len(checkpoint['stages'])==9,
        'checkpointRecovery':len(qa['reusedStages'])==9,
        'missingResourcesBlock':read(run/'resource_report.json')['status']=='PASS',
        'completenessQa':all(reports[p]['native']['status']=='PASS' for p in reports),
        'nativeEditablePage':all(reports[p]['fidelity']['status']=='PASS' for p in reports),
        'actualVisualQa':all(reports[p]['review']['status']=='PASS' for p in reports)}
    if not all(gates.values()):raise ValueError('Release gate incomplete')
    return {'scope':'task017-static-end-to-end-acceptance','status':'PASS','v01Ready':True,'version':manifest['versions']['skill_version'],'uiIrSha256':digest,'manifestSha256':builder.fingerprint(manifest),'crossPlatformLogicalGeometryAndContent':'PASS','semanticItemCount':qa['semanticItemCount'],'releaseGates':gates,'platforms':reports,'issues':[],
        'limits':['Frozen static user list with admitted Input, Select, Button and Table body; arbitrary table record overrides remain Unsupported.','AI observations, semantic review and component decisions are explicit inputs; no automatic OCR or interaction generation.','Image resources are validated but native Image generation is not admitted.','Historical Figma native raster changes use the existing approved source/outline/edge policy; native screenshots are retained.']}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('run-dir','source-dir','figma-evidence','penpot-evidence'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();out=args.run_dir.resolve()
    try:report=finalize(out,args.source_dir.resolve(),args.figma_evidence.resolve(),args.penpot_evidence.resolve())
    except (ValueError,KeyError,TypeError,OSError) as exc:report={'status':'FAIL','v01Ready':False,'issues':[str(exc)]}
    (out/'final_qa_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:report.get(k) for k in ('status','v01Ready','uiIrSha256','issues')},ensure_ascii=False));return 0 if report['status']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
