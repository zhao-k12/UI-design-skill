"""Installed-plugin host for the five declared content categories on a new fixture."""
from importlib import import_module
import json
from adapters.penpot.host import section_server as host
from adapters.penpot.host.section_server import ROOT,validation_plans
from adapters.penpot.host.server import assets


def details_assets(base,target_file,nonce,readback=None):
    plans=validation_plans(target_file)
    plan=plans['baseline'];document=plans['baselineUiIr']
    document['documentId']='task015-native-content-details'
    plan['documentId']=document['documentId']
    plan['uiIrSha256']=import_module('validators.structure.gate').builder.fingerprint(document)
    payload={**{k:v for k,v in plan.items() if k!='pages'},'page':plan['pages'][0],'pageReference':None}
    if readback is not None and (readback.get('status')!='EXECUTED' or readback.get('fileReference')!=target_file or readback.get('uiIrSha256')!=plan['uiIrSha256']):raise ValueError('details_resume_context_mismatch')
    served=assets(base,target_file,nonce)
    manifest=json.loads(served['/manifest.json'][1]);manifest['permissions']=['content:write','library:write']
    served['/manifest.json']=('application/json',json.dumps(manifest,ensure_ascii=False))
    plugin=served['/plugin.js'][1]
    for name in ('runtime.js','section_patch.js','primitive_content_patch.js'):plugin+='\n'+(ROOT/'adapters/penpot'/name).read_text(encoding='utf-8')
    plugin+='\nconst detailsPayload='+json.dumps(payload,ensure_ascii=False)+';\nlet detailsExecution='+json.dumps(readback)+';let detailsBefore=null;let detailsRequest=null;let detailsPatched=false;\n'
    plugin+='''penpot.ui.onMessage(async message=>{
      if(!['task015-details-baseline','task015-details-before','task015-details-patch','task015-details-after'].includes(message?.type))return;
      try{let result;
        if(penpot.currentFile?.id!==targetFile)throw new Error('details_file_mismatch');
        if(message.type==='task015-details-baseline'){
          if(detailsExecution)throw new Error('details_baseline_already_exists');
          result=detailsExecution=await executePenpotAdapter(penpot,detailsPayload);
        }else{
          if(detailsExecution?.status!=='EXECUTED')throw new Error('details_baseline_required');
          if(message.type==='task015-details-before'){
            result=detailsBefore=await capturePenpotSectionPatch(penpot,detailsExecution);
            const targets=[];
            const recipes=[['input.name','official-source / form.input.default.medium / 0.1::placeholder','姓名','query'],
              ['select.status','official-source / form.select.default.medium / 0.0.1.0','停用','query'],
              ['button.query','official-source / action.button.primary.medium / 0.0','导出','query'],
              ['column.role.label','column.role.label','范围','list'],['filter.description','filter.description','用户列表','query']];
            const nodes=new Map(result.nodes.map(n=>[n.id,n]));
            for(const [uiId,name,text,section] of recipes){
              const owner=nodes.get(detailsExecution.nodeMap[uiId]);
              const found=result.nodes.filter(n=>n.type==='text'&&n.name===name);
              if(!owner||found.length!==1)throw new Error('details_target_ambiguous');
              const n=found[0],style={};for(const k of ['fontId','fontVariantId','fontFamily','fontWeight','fontStyle','fontSize','lineHeight','letterSpacing','growType'])style[k]=n[k];
              targets.push({ownerReference:owner.id,textReference:n.id,name,expectedText:n.characters,text,
                sectionReference:detailsExecution.nodeMap[section],componentReference:owner.isCopy?owner.component:null,style});
            }detailsRequest={targets};result={...result,request:detailsRequest};
          }else if(message.type==='task015-details-after')result=await capturePenpotSectionPatch(penpot,detailsExecution);
          else{
            if(!detailsBefore||detailsPatched)throw new Error('details_requires_independent_before');
            detailsPatched=true;
            result=await patchPenpotPrimitiveContent(penpot,detailsExecution,detailsRequest,detailsBefore);
          }
        }
        penpot.ui.sendMessage({type:'task010-result',status:'CAPTURED',result});
      }catch(error){penpot.ui.sendMessage({type:'task010-result',status:'FAIL',error:String(error)});}
    });'''
    served['/plugin.js']=('text/javascript',plugin)
    client=served['/client.js'][1].replace("`读取完成：${result.fonts.length} 个字体系列，${result.components.length} 个本地组件。原生验收尚未执行。`","`结果：${result.status}；内容验收待检查。`")
    for action in ('baseline','before','patch','after'):client+=f"\ndocument.getElementById('{action}').onclick=()=>parent.postMessage({{type:'task015-details-{action}'}},'https://design.penpot.app');"
    served['/client.js']=('text/javascript',client)
    served['/index.html']=('text/html','''<!doctype html><html lang="zh"><meta charset="utf-8"><title>五类内容验收</title><style>body{font:15px sans-serif;padding:20px}button{padding:10px;margin:4px}</style><h3>五类内容验收</h3><p>独立页：更新占位文字、选中内容、按钮、表头和静态文字。</p><button id="baseline">建立独立内容验收页</button><button id="before">读取更新前</button><button id="patch">仅更新五项内容</button><button id="after">独立读取更新后</button><button id="inspect">读取环境</button><p id="status">等待执行</p><script src="client.js"></script></html>''')
    return served


if __name__=='__main__':
    host.section_assets=details_assets;host.main()
