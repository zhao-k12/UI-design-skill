"""Owned empty Cell roles followed by local native filling, on a separate fixture."""
from importlib import import_module
import json
from adapters.penpot.host import section_server as host
from adapters.penpot.host.server import assets, ROOT
from adapters.penpot.compiler import prepare
from adapters.component_bindings import ComponentBindings


def slot_assets(base,target_file,nonce,readback=None):
    read=lambda p:json.loads((ROOT/p).read_bytes())
    tokens=import_module('core.design-rules.tokens').TokenRegistry(read('registries/tokens/default.json'))
    components=import_module('core.component-resolver.registry').ComponentRegistry(read('registries/components/catalog.json'),read('registries/components/fidelity-reports.json'))
    bindings=ComponentBindings(read('adapters/penpot/metadata/component-bindings.json'),components,platform='penpot')
    icons=import_module('core.icon-resolver.registry').IconRegistry(import_module('icon-manager.remix-sync.manager').current())
    plans=[]
    for name in ('skeleton','filled'):
        result=prepare(read('examples/cell-slot-contract/'+name+'.ui-ir.json'),tokens,components,bindings,icons,
            read('adapters/penpot/metadata/icon-bindings.json'),read('adapters/penpot/metadata/font-bindings.json'),
            file_reference=target_file,native_fidelity=read('adapters/penpot/metadata/native-fidelity.json'))
        if result['status']!='PASS':raise ValueError(result['issues'])
        plans.append(result['plan'])
    plan=plans[0];payload={**{k:v for k,v in plan.items() if k!='pages'},'page':plan['pages'][0],'pageReference':None}
    request={'items':[{'roleId':r['id'],'width':r['layout']['width']['value'],'height':r['layout']['height']['value'],'children':r['children']}
                      for r in plans[1]['pages'][0]['children'][0]['children']]}
    served=assets(base,target_file,nonce)
    manifest=json.loads(served['/manifest.json'][1]);manifest['permissions']=['content:write','library:write']
    served['/manifest.json']=('application/json',json.dumps(manifest,ensure_ascii=False))
    plugin=served['/plugin.js'][1]
    for name in ('runtime.js','section_patch.js','cell_slots.js'):plugin+='\n'+(ROOT/'adapters/penpot'/name).read_text(encoding='utf-8')
    plugin+='\nconst slotsPayload='+json.dumps(payload,ensure_ascii=False)+';const slotsRequest='+json.dumps(request,ensure_ascii=False)+';let slotsExecution=null,slotsBefore=null,slotsFilled=false;\n'
    plugin+='''penpot.ui.onMessage(async message=>{
      if(!['slots-baseline','slots-before','slots-fill','slots-after'].includes(message?.type))return;
      try{let result;
        if(message.type==='slots-baseline'){
          if(slotsExecution)throw new Error('slots_baseline_already_exists');
          result=slotsExecution=await executePenpotAdapter(penpot,slotsPayload);
        }else{
          if(slotsExecution?.status!=='EXECUTED')throw new Error('slots_baseline_required');
          if(message.type==='slots-before')result=slotsBefore=await capturePenpotSectionPatch(penpot,slotsExecution);
          else if(message.type==='slots-fill'){
            if(slotsFilled||!slotsBefore)throw new Error('slots_before_required');slotsFilled=true;
            result=await fillPenpotCellSlots(penpot,slotsExecution,slotsRequest,slotsBefore);
          }else result=await capturePenpotSectionPatch(penpot,slotsExecution);
        }
        penpot.ui.sendMessage({type:'task010-result',status:'CAPTURED',result});
      }catch(error){penpot.ui.sendMessage({type:'task010-result',status:'FAIL',error:String(error)});}
    });'''
    served['/plugin.js']=('text/javascript',plugin)
    client=served['/client.js'][1].replace("`读取完成：${result.fonts.length} 个字体系列，${result.components.length} 个本地组件。原生验收尚未执行。`", "`执行结果：${result.status}；独立验收待检查。`")
    for action in ('baseline','before','fill','after'):client+=f"\ndocument.getElementById('{action}').onclick=()=>parent.postMessage({{type:'slots-{action}'}},'https://design.penpot.app');"
    served['/client.js']=('text/javascript',client)
    served['/index.html']=('text/html','''<!doctype html><html lang="zh"><meta charset="utf-8"><title>六类槽位验收</title><h3>六类槽位验收</h3><p>先建立空布局，再只填充现有槽位。</p><button id="baseline">建立空槽位</button><button id="before">读取填充前</button><button id="fill">填充六类槽位</button><button id="after">独立读取填充后</button><button id="inspect">读取环境</button><p id="status">等待执行</p><script src="client.js"></script></html>''')
    return served


if __name__=='__main__':
    host.section_assets=slot_assets;host.main()
