"""Same-permission installed-plugin host for a single native component swap."""
from copy import deepcopy
from importlib import import_module
import json

from adapters.penpot.host import section_server as host
from adapters.penpot.host.section_server import ROOT, validation_plans
from adapters.penpot.host.server import assets
from adapters.penpot.compiler import prepare
from adapters.component_bindings import ComponentBindings


def swap_plans(target_file):
    read=lambda name:json.loads((ROOT/name).read_bytes())
    baseline=validation_plans(target_file)['updatedUiIr']
    updated=deepcopy(baseline)
    def walk(node):
        if node['id']=='input.name':
            node['componentId']='form.select.default.medium'
        for child in node.get('children',[]):walk(child)
    walk(updated['pages'][0])
    tokens=import_module('core.design-rules.tokens').TokenRegistry(read('registries/tokens/default.json'))
    components=import_module('core.component-resolver.registry').ComponentRegistry(read('registries/components/catalog.json'),read('registries/components/fidelity-reports.json'))
    bindings=ComponentBindings(read('adapters/penpot/metadata/component-bindings.json'),components,platform='penpot')
    icons=import_module('core.icon-resolver.registry').IconRegistry(import_module('icon-manager.remix-sync.manager').current())
    result=prepare(updated,tokens,components,bindings,icons,
        read('adapters/penpot/metadata/icon-bindings.json'),read('adapters/penpot/metadata/font-bindings.json'),
        file_reference=target_file,native_fidelity=read('adapters/penpot/metadata/native-fidelity.json'))
    if result['status']!='PASS':raise ValueError('swap_preflight_failed: '+str(result['issues']))
    ledger=read('adapters/penpot/metadata/section-content-acceptance/execution.json')['result']
    content_plan=validation_plans(target_file)['updated']
    # This explicit checkpoint advance is bound to the independent accepted content
    # snapshot, checked again by the plugin before any swap.
    ledger['uiIrSha256']=content_plan['uiIrSha256']
    return {'baselineUiIr':baseline,'updatedUiIr':updated,'baseline':content_plan,
            'updated':result['plan'],'execution':ledger,
            'acceptedNodes':read('adapters/penpot/metadata/section-content-acceptance/after-capture.json')['result']['nodes']}


def swap_assets(base,target_file,nonce,readback=None):
    plans=swap_plans(target_file)
    expected_reference='b17404b9-592b-8074-8008-c0cd36551084'
    if readback is not None:
        ledger=plans['execution']
        if readback.get('status')!='CAPTURED' or any(readback.get(k)!=ledger[k] for k in ('fileReference','pageReference','rootReference')):
            raise ValueError('swap_resume_capture_context_mismatch')
        copy_id=ledger['nodeMap']['input.name']
        target=next((n for n in readback['nodes'] if n['id']==copy_id),{})
        if target.get('name')!='input.name' or not target.get('isCopy') or target.get('isMain'):
            raise ValueError('swap_resume_target_mismatch')
        if target.get('component')=='b17404b9-592b-8074-8008-c0d00dc30929':
            plans['baselineUiIr'],plans['updatedUiIr']=plans['updatedUiIr'],plans['baselineUiIr']
            plans['baseline'],plans['updated']=plans['updated'],plans['baseline']
            expected_reference=target['component']
        elif target.get('component')!=expected_reference:raise ValueError('swap_resume_component_mismatch')
        ledger['uiIrSha256']=plans['baseline']['uiIrSha256']
        plans['acceptedNodes']=readback['nodes']
    served=assets(base,target_file,nonce)
    manifest=json.loads(served['/manifest.json'][1])
    manifest['permissions']=['content:write','library:write']
    served['/manifest.json']=('application/json',json.dumps(manifest,ensure_ascii=False))
    plugin=served['/plugin.js'][1]
    for name in ('section_patch.js','section_swap.js'):
        plugin+='\n'+(ROOT/'adapters/penpot'/name).read_text(encoding='utf-8')
    payload={**{k:v for k,v in plans['updated'].items() if k!='pages'},'page':plans['updated']['pages'][0]}
    plugin+='\nconst swapPayload='+json.dumps(payload,ensure_ascii=False)+';\nconst swapExecution='+json.dumps(plans['execution'])+';\nconst acceptedNodes='+json.dumps(plans['acceptedNodes'],ensure_ascii=False)+';\nlet swapBefore=null;let swapDone=false;\n'
    plugin+='\nconst swapExpectedReference='+json.dumps(expected_reference)+';\n'
    plugin+='''penpot.ui.onMessage(async message=>{
      if(!['task015-swap-before','task015-swap','task015-swap-after'].includes(message?.type))return;
      try{let result;
        if(message.type==='task015-swap-before'){
          result=swapBefore=await capturePenpotSectionPatch(penpot,swapExecution);
          if(!swapDone&&JSON.stringify(result.nodes)!==JSON.stringify(acceptedNodes))throw new Error('accepted_content_checkpoint_changed');
        }else if(message.type==='task015-swap-after'){
          result=await capturePenpotSectionPatch(penpot,swapExecution);
        }else{
          if(!swapBefore||swapDone)throw new Error('swap_requires_fresh_before_and_single_execution');
          swapDone=true;
          result=await swapPenpotSectionComponent(penpot,swapPayload,swapExecution,{
            baseUiIrSha256:swapExecution.uiIrSha256,updatedUiIrSha256:swapPayload.uiIrSha256,
            uiIrId:'input.name',sectionIds:['query'],expectedComponentReference:swapExpectedReference},swapBefore);
        }
        penpot.ui.sendMessage({type:'task010-result',status:'CAPTURED',result});
      }catch(error){penpot.ui.sendMessage({type:'task010-result',status:'FAIL',error:String(error)});}
    });'''
    served['/plugin.js']=('text/javascript',plugin)
    client=served['/client.js'][1].replace("`读取完成：${result.fonts.length} 个字体系列，${result.components.length} 个本地组件。原生验收尚未执行。`","`结果：${result.status}；原生验收待检查。`")
    for action in ('before','swap','after'):
        client+=f"\ndocument.getElementById('{action}').onclick=()=>parent.postMessage({{type:'task015-{'swap' if action=='swap' else 'swap-'+action}'}},'https://design.penpot.app');"
    served['/client.js']=('text/javascript',client)
    served['/index.html']=('text/html','''<!doctype html><html lang="zh"><meta charset="utf-8"><title>组件替换验收</title><style>body{font:15px sans-serif;padding:20px}button{padding:10px;margin:4px}</style><h3>组件替换验收</h3><p>仅将独立验收页的姓名输入框换为登记的选择框，保留现有位置和其余区块。</p><button id="before">读取替换前</button><button id="swap">仅替换姓名控件</button><button id="after">独立读取替换后</button><button id="inspect">读取环境</button><p id="status">等待执行</p><script src="client.js"></script></html>''')
    return served


if __name__=='__main__':
    host.section_assets=swap_assets
    host.main()
