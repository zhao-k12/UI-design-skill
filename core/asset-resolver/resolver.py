"""Resolve explicit existing resources and preserve missing UI-IR diagnostics."""
from copy import deepcopy
from importlib import import_module
import argparse
import json
from pathlib import Path
from jsonschema.exceptions import ValidationError
from validators.ui_ir import validate_document, load_json, ROOT

registry_module=import_module('core.asset-resolver.registry')


def resolve(document, assets, *, prototype_assets=None, prototype_root=None,
            components=None, icons=None, unsupported_components=()):
    issues=validate_document(document)
    result={'scope':'resource-resolution','status':'FAIL','readyForAdapter':False,
            'assetRegistrySha256':assets.fingerprint,'resolvedAssets':{},'issues':issues,'document':None}
    if issues:return result
    resource_issues=[];invalid=[]
    def missing(code,node,logical,message):
        resource_issues.append({'code':code,'nodeId':node['id'],'logicalId':logical,'message':message})
    def walk(node):
        if node['type']=='Image':
            try:
                resolved=assets.resolve(node['assetId'],prototype_assets=prototype_assets,prototype_root=prototype_root)
                result['resolvedAssets'][node['id']]=resolved
            except (registry_module.AssetError,ValidationError,KeyError,TypeError) as exc:
                if getattr(exc,'code',None)=='missing_asset':missing('missing_asset',node,node['assetId'],str(exc))
                else:invalid.append({'code':'invalid_asset','nodeId':node['id'],'message':str(exc)})
        elif node['type']=='ComponentInstance':
            logical=node['componentId']
            if logical in unsupported_components:missing('unsupported_component',node,logical,'Declared target capability cannot execute this registered component')
            elif components is None:missing('missing_component',node,logical,'No current component registry supplied')
            else:
                try:components.resolve(logical,node.get('variant'))
                except ValueError as exc:missing('missing_component',node,logical,str(exc))
        elif node['type']=='IconInstance':
            if icons is None:missing('missing_icon',node,node['iconId'],'No current official icon registry supplied')
            else:
                try:icons.resolve(node['iconId'])
                except ValueError as exc:missing('missing_icon',node,node['iconId'],str(exc))
        for child in node.get('children',[]):walk(child)
        for children in node.get('slots',{}).values():
            for child in children:walk(child)
    for page in document['pages']:walk(page)
    output=deepcopy(document)
    if resource_issues:output['resourceIssues']=resource_issues
    result.update(status='FAIL' if invalid else 'Unsupported' if any(i['code']=='unsupported_component' for i in resource_issues) else 'Missing' if resource_issues else 'PASS',
                  readyForAdapter=not invalid and not resource_issues,issues=invalid+resource_issues,
                  document=output if not invalid else None)
    return result


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('document',type=Path);cli.add_argument('--catalog',type=Path,default=ROOT/'registries/assets/catalog.json')
    cli.add_argument('--asset-root',type=Path,required=True);cli.add_argument('--prototype-assets',type=Path)
    cli.add_argument('--prototype-root',type=Path);cli.add_argument('--output',type=Path,required=True)
    args=cli.parse_args()
    try:
        catalog=load_json(args.catalog);prototype=load_json(args.prototype_assets) if args.prototype_assets else []
        inputs={args.document.resolve(),args.catalog.resolve()}
        if args.prototype_assets:inputs.add(args.prototype_assets.resolve())
        for root,entries in ((args.asset_root,catalog['assets']),(args.prototype_root,prototype)):
            if root is not None:inputs.update((root/a['path']).resolve() for a in entries)
        if args.output.resolve() in inputs:cli.error('Output cannot overwrite a resource or input')
        components=import_module('core.component-resolver.registry').ComponentRegistry(load_json(ROOT/'registries/components/catalog.json'),load_json(ROOT/'registries/components/fidelity-reports.json'))
        lock=load_json(ROOT/'registries/icons/current.json')
        icons=import_module('core.icon-resolver.registry').IconRegistry(load_json(ROOT/'registries/icons/snapshots'/lock['snapshotSha256']/'registry.json'))
        result=resolve(load_json(args.document),registry_module.AssetRegistry(catalog,args.asset_root),
                       prototype_assets=prototype,prototype_root=args.prototype_root,components=components,icons=icons)
    except (OSError,ValueError,KeyError,TypeError,ValidationError) as exc:
        result={'scope':'resource-resolution','status':'FAIL','readyForAdapter':False,'document':None,'issues':[{'code':'invalid_resource_input','message':str(exc)}]}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print('Resource resolution: '+result['status'])
    return 0 if result['readyForAdapter'] else 1


if __name__=='__main__':raise SystemExit(main())
