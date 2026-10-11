"""Execute one passed locked pipeline UI-IR and independently capture its native page."""
import json
import argparse
import sys
from pathlib import Path
from adapters.penpot.host import section_server as host
from adapters.penpot.host.server import assets,ROOT
RUN_DIRECTORY=ROOT/'artifacts/task-017/pipeline-final'
PREVIOUS_INSTANCES=None


def pipeline_assets(base,target_file,nonce,readback=None):
    run=RUN_DIRECTORY
    qa=json.loads((run/'qa_report.json').read_bytes());report=json.loads((run/'penpot_preflight.json').read_bytes())
    if not qa['readyForAdapter'] or report['status']!='PASS':raise ValueError('pipeline_preflight_required')
    plan=report['plan']
    if plan['fileReference']!=target_file or plan['uiIrSha256']!=qa['uiIrSha256']:raise ValueError('pipeline_context_mismatch')
    payload={**{k:v for k,v in plan.items() if k!='pages'},'page':plan['pages'][0],'pageReference':None}
    served=assets(base,target_file,nonce)
    manifest=json.loads(served['/manifest.json'][1]);manifest['permissions']=['content:write','library:write']
    served['/manifest.json']=('application/json',json.dumps(manifest,ensure_ascii=False))
    plugin=served['/plugin.js'][1]
    for name in ('runtime.js','content_runtime.js','page_recovery.js','section_patch.js','capture.js','page_instances.js'):plugin+='\n'+(ROOT/'adapters/penpot'/name).read_text(encoding='utf-8')
    if readback and (readback.get('status')!='EXECUTED' or readback.get('fileReference')!=target_file):raise ValueError('pipeline_resume_context_mismatch')
    plugin+='\nconst pipelinePayload='+json.dumps(payload,ensure_ascii=False)+';let pipelineExecution='+json.dumps(readback,ensure_ascii=False)+';let previousInstances='+json.dumps(PREVIOUS_INSTANCES,ensure_ascii=False)+';\n'
    plugin+='''penpot.ui.onMessage(async message=>{
      if(!['pipeline-create','pipeline-capture','pipeline-style','pipeline-instances'].includes(message?.type))return;
      try{let result;
        if(message.type==='pipeline-create'){
          if(pipelineExecution)throw new Error('pipeline_existing_execution_requires_readback');
          pipelineExecution=await executePenpotContentAdapter(penpot,pipelinePayload);
          if(pipelineExecution.status!=='EXECUTED'){result=pipelineExecution;}
          else{
            const defaults=await restorePenpotPageDefaults(penpot,pipelinePayload,pipelineExecution);
            const icons=await resetPenpotIconCopies(penpot,pipelinePayload,pipelineExecution);
            result={...pipelineExecution,defaults,icons,finalAcceptance:'NOT_RUN'};
          }
        }else if(message.type==='pipeline-style'){
          if(pipelineExecution?.status!=='EXECUTED'||penpot.currentFile.id!==pipelineExecution.fileReference||penpot.currentPage.id!==pipelineExecution.pageReference)throw new Error('pipeline_style_context');
          if(pipelineExecution.uiIrSha256!=='b36ce0869f3d44ee6ffb8d2d3819f0f023f22840c86a621361400de74606c05e')throw new Error('pipeline_style_stale_baseline');
          const root=penpot.currentPage.getShapeById(pipelineExecution.rootReference),before=snapshotPenpotPatchRoot(root);
          const specs=[pipelinePayload.page,...pipelinePayload.page.children];const ids=specs.map(s=>pipelineExecution.nodeMap[s.id]);
          for(const spec of specs){const shape=penpot.currentPage.getShapeById(pipelineExecution.nodeMap[spec.id]);if(!before.some(n=>n.id===shape.id)||shape.type!=='board')throw new Error('pipeline_style_unowned_region');shape.fills=[{fillColor:spec.style.fill,fillOpacity:1}];}
          const after=snapshotPenpotPatchRoot(root),normalize=n=>{const v={...n};if(ids.includes(n.id))delete v.fills;return v;};
          if(JSON.stringify(before.map(normalize))!==JSON.stringify(after.map(normalize)))throw new Error('pipeline_style_unrelated_mutation');
          const old=pipelineExecution.uiIrSha256;pipelineExecution={...pipelineExecution,uiIrSha256:pipelinePayload.uiIrSha256};
          result={status:'PATCHED',fileReference:pipelineExecution.fileReference,createdNodeIds:[],removedNodeIds:[],mutatedNodeIds:ids,baseUiIrSha256:old,updatedUiIrSha256:pipelinePayload.uiIrSha256,beforeRegions:before.filter(n=>ids.includes(n.id)),afterRegions:after.filter(n=>ids.includes(n.id)),unchangedNodes:before.length-ids.length,execution:pipelineExecution};
        }else if(message.type==='pipeline-instances'){
          if(pipelineExecution?.uiIrSha256!==pipelinePayload.uiIrSha256)throw new Error('pipeline_final_plan_required');
          result=previousInstances=await capturePenpotPageInstances(penpot,pipelinePayload,pipelineExecution,previousInstances);
        }else{
          if(pipelineExecution?.status!=='EXECUTED')throw new Error('pipeline_execution_required');
          if(pipelineExecution.uiIrSha256!==pipelinePayload.uiIrSha256)throw new Error('pipeline_final_plan_required');
          const content=await capturePenpotSectionPatch(penpot,pipelineExecution);
          result={...await capturePenpotOutput(penpot,pipelineExecution),contentNodes:content.nodes};
        }
        penpot.ui.sendMessage({type:'task010-result',status:'CAPTURED',result});
      }catch(error){penpot.ui.sendMessage({type:'task010-result',status:'FAIL',error:String(error),execution:pipelineExecution});}
    });'''
    served['/plugin.js']=('text/javascript',plugin)
    client=served['/client.js'][1].replace("`读取完成：${result.fonts.length} 个字体系列，${result.components.length} 个本地组件。原生验收尚未执行。`","`端到端执行：${result.status}，最终验收待检查。`")
    for action in ('create','capture','style','instances'):client+=f"\ndocument.getElementById('{action}').onclick=()=>parent.postMessage({{type:'pipeline-{action}'}},'https://design.penpot.app');"
    served['/client.js']=('text/javascript',client)
    served['/index.html']=('text/html','''<!doctype html><html lang="zh"><meta charset="utf-8"><title>端到端列表验收</title><h3>端到端列表验收</h3><p>已冻结姓名／状态／角色；仅建立本次独立结果。</p><button id="create">生成本次静态列表</button><button id="capture">独立读取及导出</button><button id="style">应用锁定区域背景</button><button id="instances">独立组件保真导出</button><button id="inspect">读取环境</button><p id="status">等待执行</p><script src="client.js"></script></html>''')
    return served


if __name__=='__main__':
    options=argparse.ArgumentParser(add_help=False)
    options.add_argument('--pipeline-dir',type=Path,default=RUN_DIRECTORY)
    options.add_argument('--previous-instances',type=Path)
    args,remaining=options.parse_known_args()
    RUN_DIRECTORY=args.pipeline_dir.resolve()
    if not RUN_DIRECTORY.is_relative_to((ROOT/'artifacts').resolve()):raise ValueError('Use a project artifact pipeline directory')
    if args.previous_instances:
        PREVIOUS_INSTANCES=json.loads(args.previous_instances.read_bytes())['result']
        if PREVIOUS_INSTANCES.get('status') not in ('PARTIAL','CAPTURED') or PREVIOUS_INSTANCES.get('scope')!='production-native-instance-capture' or PREVIOUS_INSTANCES.get('createdNodeIds')!=[] or PREVIOUS_INSTANCES.get('mutatedNodeIds')!=[]:raise ValueError('Invalid native export recovery packet')
    sys.argv=[sys.argv[0],*remaining]
    host.section_assets=pipeline_assets;host.main()
