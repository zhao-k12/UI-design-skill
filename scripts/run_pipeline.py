"""Run the approved source package through Core and prepare both native adapters."""
import argparse
import importlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from validators.ui_ir import load_json
from adapters.component_bindings import ComponentBindings
from adapters.figma.content_compiler import prepare as prepare_f
from adapters.penpot.compiler import prepare as prepare_p


PROFILES = {
    'v0.1': {
        'tokens': 'registries/tokens/default.json',
        'components': 'registries/components/catalog.json',
        'fidelity': 'registries/components/fidelity-reports.json',
        'componentBindings': 'component-bindings.json',
        'fontBindings': 'font-bindings.json',
    },
    'v0.2': {
        'tokens': 'registries/tokens/v0.2.2/default.json',
        'components': 'registries/components/v0.2.3/catalog.json',
        'fidelity': 'registries/components/v0.2.3/fidelity-reports.json',
        'componentBindings': 'component-bindings-0.2.3.json',
        'fontBindings': 'page-default-font-bindings-0.2.0.json',
    },
}


def profile_resources(profile):
    return PROFILES[profile].copy()


def main():
    cli=argparse.ArgumentParser(description=__doc__);cli.add_argument('input_dir',type=Path)
    cli.add_argument('--output-dir',type=Path,required=True);cli.add_argument('--figma-file',required=True);cli.add_argument('--penpot-file',required=True)
    cli.add_argument('--profile', choices=tuple(PROFILES), default='v0.1')
    args=cli.parse_args();base=args.input_dir.resolve();output=args.output_dir.resolve()
    if not output.is_relative_to((ROOT/'artifacts').resolve()):cli.error('Use an artifact task directory')
    read=lambda p:load_json(ROOT/p)
    paths=profile_resources(args.profile)
    resolver=importlib.import_module('core.component-resolver.resolver')
    tokens=resolver.tokens.TokenRegistry(read(paths['tokens']))
    components=resolver.registry_module.ComponentRegistry(read(paths['components']),read(paths['fidelity']))
    versions=load_json(base/'versions.json')
    if versions['component_library_version']!=components.library_version or versions['design_token_version']!=tokens.version:
        cli.error('Input versions do not match the selected profile; use an independent migrated input package')
    lock=read('registries/icons/current.json')
    icons=importlib.import_module('core.icon-resolver.registry').IconRegistry(read('registries/icons/snapshots/'+lock['snapshotSha256']+'/registry.json'))
    assets=importlib.import_module('core.asset-resolver.registry').AssetRegistry(read('registries/assets/catalog.json'),ROOT/'registries/assets')
    geometry=importlib.import_module('core.component-resolver.placement').SourceGeometry(load_json(base/'source-geometry.json'),components)
    content=load_json(base/'content.json');ids=set()
    for item in content['items']:
        for children in item.get('cellSlots',{}).values():
            ids.update(n['iconId'] for n in children if n['type']=='IconInstance')
    svg={i:(ROOT/'registries/icons/objects'/(icons.resolve(i)['descriptor']['svgSha256']+'.svg')).read_bytes() for i in ids}
    runner=importlib.import_module('core.pipeline.runner')
    try:
        qa=runner.run(load_json(base/'observations.json'),base,load_json(base/'review.json'),load_json(base/'layout-plan.json'),
                      load_json(base/'decisions.json'),content,components,tokens,icons,assets,geometry,svg,versions,output,
                      measurement_evidence=load_json(base/'runtime-measurements.json'),evidence_root=ROOT)
        if not qa['readyForAdapter']:print(json.dumps(qa,ensure_ascii=False));return 1
        document=load_json(output/'final_ui_ir.json');preflights={}
        for platform,target in (('figma',args.figma_file),('penpot',args.penpot_file)):
            binding=ComponentBindings(read('adapters/'+platform+'/metadata/'+paths['componentBindings']),components,platform=platform)
            common=[document,tokens,components,binding,icons,read('adapters/'+platform+'/metadata/icon-bindings.json'),read('adapters/'+platform+'/metadata/'+paths['fontBindings'])]
            report=prepare_f(*common,file_reference=target) if platform=='figma' else prepare_p(*common,file_reference=target,native_fidelity=read('adapters/penpot/metadata/native-fidelity.json') if args.profile=='v0.1' else None)
            if report['status']=='PASS' and report['plan']['adapterVersion']!=versions[platform+'_adapter_version']:
                report={'status':'FAIL','plan':None,'issues':[{'code':'adapter_version_changed','message':'Native plan differs from locked adapter version'}]}
            runner.write(output/(platform+'_preflight.json'),report);preflights[platform]=report['status']
        qa['adapterPreflights']=preflights;qa['readyForAdapter']=all(s=='PASS' for s in preflights.values())
        if not qa['readyForAdapter']:qa['status']='FAIL'
        runner.write(output/'qa_report.json',qa);print(json.dumps(qa,ensure_ascii=False));return 0 if qa['readyForAdapter'] else 1
    except (ValueError,OSError) as exc:
        output.mkdir(parents=True,exist_ok=True);runner.write(output/'final_ui_ir.json',None)
        runner.write(output/'qa_report.json',{'status':'FAIL','readyForAdapter':False,'v01Ready':False,'issues':[str(exc)]})
        print('Pipeline blocked: '+str(exc));return 1


if __name__=='__main__':raise SystemExit(main())
