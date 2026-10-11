"""Own localhost host for source-bound, unadmitted mixed-font Table candidates."""
import argparse
import json
import sys
from pathlib import Path
from adapters.penpot.host import section_server as host
from adapters.penpot.host.server import assets,ROOT
from adapters.headed_table import prepare_penpot
from adapters.headed_table_policy import header_background_union

SOURCE_DIRECTORIES=[]

def table_assets(base,target_file,nonce,readback=None):
    specs=[prepare_penpot(directory,target_file,None) for directory in SOURCE_DIRECTORIES]
    for spec in specs: spec['headerBackgroundUnion']=header_background_union(spec)
    if len(specs)!=2 or len({s['logicalId'] for s in specs})!=2:raise ValueError('two_distinct_table_sources_required')
    if readback is not None and (readback.get('status')!='CREATED' or readback.get('fileReference')!=target_file or [s['componentIrSha256'] for s in readback['candidates']]!=[s['componentIrSha256'] for s in specs]):raise ValueError('table_readback_source_mismatch')
    served=assets(base,target_file,nonce)
    manifest=json.loads(served['/manifest.json'][1]);manifest.update(description='仅制作两份新表格候选并独立读取；不准入正式库',permissions=['content:write','library:write'])
    served['/manifest.json']=('application/json',json.dumps(manifest,ensure_ascii=False))
    plugin=served['/plugin.js'][1]
    for name in ('component_candidate.js','headed_table_candidate.js','headed_table_capture.js','headed_table_header_repair.js'):plugin+='\n'+(ROOT/'adapters/penpot'/name).read_text(encoding='utf8')
    plugin+='\nconst tableSpecs='+json.dumps(specs,ensure_ascii=False)+';let tableExecution='+json.dumps(readback,ensure_ascii=False)+';\n'
    plugin+='''penpot.ui.onMessage(async message=>{
      if(!['table-create','table-capture-0','table-capture-1','table-refresh-fonts','table-repair-header'].includes(message?.type))return;
      let created=[];let mutated=[];let candidates=[];
      try{
        if(penpot.currentFile?.id!==targetFile)throw new Error('target_file_mismatch');
        let result;
        if(message.type==='table-create'){
          if(tableExecution)throw new Error('table_existing_execution_requires_recovery');
          if(penpot.currentFile.pages.some(p=>p.name==='task020-headed-table-candidates'))throw new Error('table_existing_page_requires_recovery');
          for(const spec of tableSpecs)for(const family of spec.requiredFonts){
            const fonts=penpot.fonts.all.filter(f=>f.fontFamily===family);
            if(fonts.length!==1)throw new Error('missing_or_ambiguous_source_font:'+family);
            for(const weight of [...new Set(spec.rows.flatMap(r=>r.cells).filter(c=>c.text.fontFamily===family).map(c=>c.text.fontWeight))])selectExactPenpotVariant(fonts[0],weight);
          }
          const page=penpot.createPage();created.push(page.id);page.name='task020-headed-table-candidates';await penpot.openPage(page);
          for(const original of tableSpecs){const spec={...original,pageReference:page.id};
            const candidate=await buildHeadedPenpotTableCandidate(penpot,spec);candidates.push(candidate);created.push(...candidate.createdNodeIds);
            if(candidate.status!=='CANDIDATE_CREATED')throw new Error('candidate_creation_failed');
          }
          result=tableExecution={status:'CREATED',fileReference:targetFile,pageReference:page.id,candidates,createdNodeIds:created,createdComponentIds:candidates.map(c=>c.componentReference),mutatedNodeIds:[],admissionEligible:false,fidelityGate:'NOT_RUN'};
        }else if(message.type==='table-repair-header'){
          result=await repairHeadedTableHeaders(penpot,tableSpecs,tableExecution);
        }else if(message.type==='table-restore-background'){
          if(tableExecution?.status!=='CREATED'||penpot.currentPage.id!==tableExecution.pageReference)throw new Error('table_execution_required');
          const observations=[];
          // Preflight both exact main instances before the first mutation.
          for(let i=0;i<tableSpecs.length;i++){
            const spec=tableSpecs[i],candidate=tableExecution.candidates[i],main=penpot.currentPage.getShapeById(candidate.mainReference);
            if(!main?.isComponentMainInstance()||main.width!==spec.rootBounds.width||main.height!==spec.rootBounds.height||main.clipContent!==true||main.opacity!==1||main.strokes.length||main.borderRadius!==0)throw new Error('table_background_main_mismatch');
            if(main.fills.length && !(main.fills.length===1&&main.fills[0].fillColor===spec.rootFill&&main.fills[0].fillOpacity===1))throw new Error('table_background_requires_read');
            observations.push({mainReference:main.id,logicalId:spec.logicalId,sourcePath:spec.rootFillSourcePath,sourceFill:spec.rootFill,beforeFills:JSON.parse(JSON.stringify(main.fills))});
          }
          for(const row of observations){const main=penpot.currentPage.getShapeById(row.mainReference);main.fills=[{fillColor:row.sourceFill,fillOpacity:1}];mutated.push(main.id);}
          await penpot.waitForLayoutUpdate();
          for(const row of observations)row.afterFills=JSON.parse(JSON.stringify(penpot.currentPage.getShapeById(row.mainReference).fills));
          result={status:'SOURCE_BACKGROUND_RESTORED',fileReference:targetFile,pageReference:tableExecution.pageReference,observations,createdNodeIds:[],mutatedNodeIds:mutated,fidelityGate:'NOT_RUN',admissionEligible:false};
        }else if(message.type==='table-refresh-fonts'){
          if(tableExecution?.status!=='CREATED'||penpot.currentPage.id!==tableExecution.pageReference)throw new Error('table_execution_required');
          const observed=[];
          for(let i=0;i<tableSpecs.length;i++){
            const candidate=tableExecution.candidates[i],main=penpot.currentPage.getShapeById(candidate.mainReference);
            if(!main?.isComponentMainInstance())throw new Error('table_main_instance_required');
            for(const row of tableSpecs[i].rows)for(const cell of row.cells){
              const item=cell.text;
              const text=candidate.textReferences.map(id=>penpot.currentPage.getShapeById(id)).find(t=>t?.name.replace(/\\s*\\/\\s*/g,'/')==='official-source/'+item.path);
              if(!text||text.characters!==item.characters||text.fontFamily!==item.fontFamily)throw new Error('table_font_refresh_source_mismatch');
              const range=text.getRange(0,text.characters.length);
              observed.push({textReference:text.id,characters:text.characters,sourceFontFamily:item.fontFamily,sourceFontWeight:item.fontWeight,beforeRange:{fontId:range.fontId,fontFamily:range.fontFamily,fontVariantId:range.fontVariantId,fontSize:range.fontSize,fontWeight:range.fontWeight,lineHeight:range.lineHeight,letterSpacing:range.letterSpacing}});
            }
          }
          // Apply the same bound font to the complete public text range. No
          // geometry offsets, tracking changes or source text substitutions.
          for(const row of observed){const text=penpot.currentPage.getShapeById(row.textReference),font=penpot.fonts.findById(text.fontId);
            if(!font||font.fontFamily!==row.sourceFontFamily)throw new Error('table_exact_source_font_missing');
            font.applyToRange(text.getRange(0,text.characters.length),selectExactPenpotVariant(font,row.sourceFontWeight));
            mutated.push(text.id);
          }
          await penpot.waitForLayoutUpdate();
          for(const row of observed){const text=penpot.currentPage.getShapeById(row.textReference),range=text.getRange(0,text.characters.length);
            if(typeof text.waitForLayoutUpdate==='function')await text.waitForLayoutUpdate(15000);
            row.afterRange={fontId:range.fontId,fontFamily:range.fontFamily,fontVariantId:range.fontVariantId,fontSize:range.fontSize,fontWeight:range.fontWeight,lineHeight:range.lineHeight,letterSpacing:range.letterSpacing};
          }
          result={status:'FONT_RANGE_REAPPLIED',fileReference:targetFile,pageReference:tableExecution.pageReference,createdNodeIds:[],mutatedNodeIds:observed.map(r=>r.textReference),observations:observed,fidelityGate:'NOT_RUN',admissionEligible:false};
        }else{
          if(tableExecution?.status!=='CREATED')throw new Error('table_execution_required');
          const index=message.type.endsWith('0')?0:1;
          result=await captureHeadedPenpotTable(penpot,{...tableSpecs[index],...tableExecution.candidates[index]});
        }
        penpot.ui.sendMessage({type:'task010-result',status:result.status==='FAIL'?'FAIL':'CAPTURED',result});
      }catch(error){penpot.ui.sendMessage({type:'task010-result',status:'FAIL',error:String(error),result:{status:'FAIL',fileReference:targetFile,createdNodeIds:created,candidates,mutatedNodeIds:mutated,admissionEligible:false,fidelityGate:'NOT_RUN'}});}
    });'''
    served['/plugin.js']=('text/javascript',plugin)
    client=served['/client.js'][1].replace("`读取完成：${result.fonts.length} 个字体系列，${result.components.length} 个本地组件。原生验收尚未执行。`","`记录：${result.status}；正式准入尚未执行。`")
    for action,message in [('create','table-create'),('first','table-capture-0'),('second','table-capture-1'),('refresh','table-refresh-fonts'),('repair','table-repair-header')]:client+=f"\ndocument.getElementById('{action}').onclick=()=>parent.postMessage({{type:'{message}'}},'https://design.penpot.app');"
    served['/client.js']=('text/javascript',client)
    served['/index.html']=('text/html','''<!doctype html><html lang="zh"><meta charset="utf-8"><title>新表格候选</title><h3>新表格候选</h3><p>两列／四列；带表头，表头使用实际苹方中粗，正文使用 Arial 与苹方常规。仅创建独立候选页，不准入正式库。</p><button id="create">制作两个候选组件</button><button id="first">独立导出两列表格</button><button id="second">独立导出四列表格</button><button id="refresh">核对并重应用实际混合字体字符范围</button><button id="repair">修复来源绑定的表头背景并集</button><button id="inspect">读取实际环境</button><p id="status">等待执行</p><script src="client.js"></script></html>''')
    return served

if __name__=='__main__':
    options=argparse.ArgumentParser(add_help=False);options.add_argument('--source',action='append',type=Path,required=True)
    args,remaining=options.parse_known_args();SOURCE_DIRECTORIES=[p.resolve() for p in args.source]
    sys.argv=[sys.argv[0],*remaining];host.section_assets=table_assets;host.main()


