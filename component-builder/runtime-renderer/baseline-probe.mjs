import {mkdir,readFile,writeFile} from 'node:fs/promises';
import {resolve,join,sep} from 'node:path';
import {pathToFileURL} from 'node:url';
import {extractRuntime} from './extract.mjs';
import {ROOT,hash,jsonFile} from '../source-reader/source-lock.mjs';

// A temporary zero-size inline-block's bottom edge reports its aligned baseline.
// Instrumentation is removed in finally; original geometry must remain identical.
export async function observeBaselines(page) {
  return page.evaluate(()=>{
    const rows=[];
    for(const container of document.querySelectorAll('[data-runtime-case]')) {
      const logicalId=container.getAttribute('data-runtime-case'),root=container.firstElementChild;
      const selected=root.querySelector('.ivu-select-selected-value');
      const element=selected??root.querySelector('span');
      if((!selected&&root.querySelector('input'))||!element) {rows.push({logicalId,status:'UNSUPPORTED',reason:'placeholder_baseline_not_exposed_by_standard_dom'});continue;}
      if(element.childElementCount||element.childNodes.length!==1||element.firstChild.nodeType!==Node.TEXT_NODE)throw new Error('baseline_probe_unsupported_text_structure');
      const rect=node=>{const b=node.getBoundingClientRect();return {x:b.x,y:b.y,width:b.width,height:b.height};};
      const range=document.createRange();range.selectNodeContents(element);
      const before={root:rect(root),element:rect(element),text:rect(range),html:element.innerHTML};
      const marker=document.createElement('span');
      marker.style.cssText='all:initial;display:inline-block;width:0;height:0;margin:0;padding:0;border:0;line-height:0;font-size:0;vertical-align:baseline;';
      let measurement;
      try {
        element.appendChild(marker);
        const textRange=document.createRange();textRange.selectNode(element.firstChild);
        const during={root:rect(root),element:rect(element),text:rect(textRange)};
        if(JSON.stringify(during)!==JSON.stringify({root:before.root,element:before.element,text:before.text}))throw new Error('baseline_marker_changed_geometry');
        const b=rect(marker);if(b.width!==0||b.height!==0)throw new Error('baseline_marker_nonzero_extent');
        measurement={logicalId,status:'OBSERVED',characters:element.firstChild.textContent,
          baselineDocumentY:b.y,baselineComponentY:b.y-before.root.y,baselineElementY:b.y-before.element.y,
          elementBounds:before.element,textRangeBounds:before.text,method:'temporary_zero_extent_inline_block_bottom_margin_edge'};
      } finally {marker.remove();}
      const after={root:rect(root),element:rect(element),text:rect(range),html:element.innerHTML};
      if(JSON.stringify(before)!==JSON.stringify(after))throw new Error('baseline_probe_restore_mismatch');
      rows.push({...measurement,originalGeometryAndMarkupRestored:true});
    }
    return rows;
  });
}

export async function observeShadowAndArrowBaselines(page) {
  const session=await page.context().newCDPSession(page);
  try {
    await session.send('DOM.enable');
    const {root}=await session.send('DOM.getDocument',{depth:-1,pierce:true});
    const targets=[];
    function walk(node,logicalId) {
      const attributes=Object.fromEntries(Array.from({length:(node.attributes??[]).length/2},(_,i)=>[node.attributes[i*2],node.attributes[i*2+1]]));
      logicalId=attributes['data-runtime-case']??logicalId;
      if(logicalId==='form.input.default.medium'&&attributes.pseudo==='-webkit-input-placeholder')targets.push({logicalId,surface:'user-agent-shadow',backendNodeId:node.backendNodeId});
      for(const child of [...(node.children??[]),...(node.shadowRoots??[])])walk(child,logicalId);
    }
    walk(root);
    const {nodeId}=await session.send('DOM.querySelector',{nodeId:root.nodeId,selector:'[data-runtime-case="form.select.default.medium"] .ivu-select-arrow'});
    if(nodeId)targets.push({logicalId:'form.select.default.medium',surface:'pseudo:before',nodeId});
    const origins=await page.evaluate(()=>Object.fromEntries([...document.querySelectorAll('[data-runtime-case]')].map(container=>[container.getAttribute('data-runtime-case'),container.firstElementChild.getBoundingClientRect().y])));
    async function textGeometry() {
      const snapshot=await session.send('DOMSnapshot.getSnapshot',{computedStyleWhitelist:[],includeUserAgentShadowTree:true});
      return snapshot.layoutTreeNodes.flatMap(node=>(node.inlineTextNodes??[]).map(box=>({text:node.layoutText,bounds:box.boundingBox,start:box.startCharacterIndex,length:box.numCharacters}))).sort((a,b)=>JSON.stringify(a).localeCompare(JSON.stringify(b)));
    }
    const observations=[];
    for(const target of targets) {
      let objectId,markerId;
      try {
        const {object}=await session.send('DOM.resolveNode',target.backendNodeId?{backendNodeId:target.backendNodeId}:{nodeId:target.nodeId});objectId=object.objectId;
        if(!objectId)throw new Error('baseline_target_object_missing');
        async function call(id,functionDeclaration) {
          const result=await session.send('Runtime.callFunctionOn',{objectId:id,functionDeclaration,returnByValue:true});
          if(result.exceptionDetails)throw new Error('baseline_shadow_runtime_exception');return result.result.value;
        }
        const read='function(){const b=this.getBoundingClientRect();return {html:this.innerHTML,characters:this.textContent,pseudoContent:getComputedStyle(this,"::before").content,bounds:{x:b.x,y:b.y,width:b.width,height:b.height}};}';
        const before=await call(objectId,read),beforeText=await textGeometry();
        const created=await session.send('Runtime.callFunctionOn',{objectId,functionDeclaration:'function(){const marker=document.createElement("span");marker.style.cssText="all:initial;display:inline-block;width:0;height:0;margin:0;padding:0;border:0;line-height:0;font-size:0;vertical-align:baseline;";this.appendChild(marker);return marker;}',returnByValue:false});
        if(created.exceptionDetails||!created.result.objectId)throw new Error('baseline_marker_create_failed');markerId=created.result.objectId;
        let measurement;
        try {
          const marker=await call(markerId,'function(){const b=this.getBoundingClientRect();return {x:b.x,y:b.y,width:b.width,height:b.height};}');
          const during=await call(objectId,read),duringText=await textGeometry();
          if(marker.width!==0||marker.height!==0||JSON.stringify(before.bounds)!==JSON.stringify(during.bounds)||JSON.stringify(beforeText)!==JSON.stringify(duringText))throw new Error('baseline_marker_changed_shadow_geometry');
          measurement={logicalId:target.logicalId,surface:target.surface,status:'OBSERVED',characters:target.surface==='pseudo:before'?JSON.parse(before.pseudoContent):before.characters,baselineDocumentY:marker.y,baselineComponentY:marker.y-origins[target.logicalId],baselineElementY:marker.y-before.bounds.y,method:'zero_extent_baseline_marker_on_resolved_actual_dom_owner'};
        } finally {await call(markerId,'function(){this.remove();return true;}');}
        const after=await call(objectId,read),afterText=await textGeometry();
        if(JSON.stringify(before)!==JSON.stringify(after)||JSON.stringify(beforeText)!==JSON.stringify(afterText))throw new Error('baseline_shadow_restore_mismatch');
        observations.push({...measurement,originalGeometryAndMarkupRestored:true});
      } finally {
        if(markerId)await session.send('Runtime.releaseObject',{objectId:markerId});
        if(objectId)await session.send('Runtime.releaseObject',{objectId});
      }
    }
    return observations;
  } finally {await session.detach();}
}

export async function probeBaselines(outputDirectory,referenceDirectory) {
  const output=resolve(outputDirectory),reference=resolve(referenceDirectory);
  if(!output.startsWith(join(ROOT,'artifacts')+sep)||output===reference||output.startsWith(reference+sep))throw new Error('invalid_baseline_probe_output');
  await mkdir(output,{recursive:true});const target=join(output,'baseline_report.json');
  await writeFile(target,'{"status":"RUNNING","admissionEligible":false}\n');
  try {
    const baseline=await jsonFile(join(reference,'component_ir.json'));if(baseline.status!=='PASS')throw new Error('invalid_baseline_reference');
    let observed;
    const {result}=await extractRuntime(output,{observePage:async(page,context)=>{
      const ordinary=await observeBaselines(page),extra=await observeShadowAndArrowBaselines(page);
      const observations=ordinary.filter(row=>!(row.status==='UNSUPPORTED'&&extra.some(other=>other.logicalId===row.logicalId&&other.surface==='user-agent-shadow'))).concat(extra);
      observed={environment:context.environment,provenance:context.provenance,observations};
    }});
    const referenceMatches=result.components.map(c=>{const r=baseline.components.find(item=>item.logicalComponentId===c.logicalComponentId);return {logicalId:c.logicalComponentId,screenshotMatches:r?.screenshot.sha256===c.screenshot.sha256,environmentMatches:JSON.stringify(r?.environment)===JSON.stringify(c.environment)};});
    const report={scope:'official_runtime_baseline_diagnostic',status:referenceMatches.every(row=>row.screenshotMatches&&row.environmentMatches)?'PASS':'REVIEW',referenceComponentIrSha256:hash(await readFile(join(reference,'component_ir.json'))),referenceMatches,...observed,admissionEligible:false,fidelityGate:'NOT_RUN',limitations:['Instrumentation is temporary and checks original geometry/markup before, during and after.','Shadow/pseudo observations use actual resolved DOM owners with all rendered text boxes unchanged; only the declared default source fixtures are covered.']};
    await writeFile(target,JSON.stringify(report,null,2)+'\n');return report;
  } catch(error) {await writeFile(target,JSON.stringify({scope:'official_runtime_baseline_diagnostic',status:'FAIL',admissionEligible:false,issues:[{code:error.message}]})+'\n');throw error;}
}

if(process.argv[1]&&import.meta.url===pathToFileURL(resolve(process.argv[1])).href){
  const out=process.argv.indexOf('--output'),ref=process.argv.indexOf('--reference');
  if(out<0||ref<0||!process.argv[out+1]||!process.argv[ref+1])throw new Error('Usage: baseline-probe.mjs --output <new artifacts> --reference <reference>');
  const report=await probeBaselines(process.argv[out+1],process.argv[ref+1]);console.log(JSON.stringify({status:report.status,observations:report.observations}));
}
