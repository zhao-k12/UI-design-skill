import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {resolve,join,sep} from 'node:path';
import {pathToFileURL} from 'node:url';
import {extractRuntime} from './extract.mjs';
import {ROOT,hash,jsonFile} from '../source-reader/source-lock.mjs';

// Actual post-layout text boxes, including browser shadow/pseudo content.
// These rectangles are layout boxes, never per-glyph ink outlines.
export function decodeTextBoxes(snapshot) {
  const rows=[];
  for (const [documentIndex,document] of snapshot.documents.entries()) {
    const {nodes,layout,textBoxes}=document;
    for (let index=0;index<textBoxes.layoutIndex.length;index++) {
      const layoutIndex=textBoxes.layoutIndex[index];
      const nodeIndex=layout.nodeIndex[layoutIndex];
      const bounds=textBoxes.bounds[index];
      const start=textBoxes.start[index],length=textBoxes.length[index];
      if (!Number.isInteger(nodeIndex) || !Array.isArray(bounds) || bounds.length!==4 || !bounds.every(Number.isFinite) || bounds[2]<0 || bounds[3]<0 || !Number.isInteger(start) || start<0 || !Number.isInteger(length) || length<0) throw new Error('invalid_snapshot_text_box');
      const fullText=snapshot.strings[layout.text[layoutIndex]];
      if(typeof fullText!=='string' || start+length>fullText.length) throw new Error('invalid_snapshot_text_slice');
      const ancestry=[];let ancestor=nodeIndex;const visited=new Set();
      while(ancestor>=0) {
        if(visited.has(ancestor) || ancestor>=nodes.nodeName.length)throw new Error('invalid_snapshot_ancestry');
        visited.add(ancestor);
        const attributes=nodes.attributes[ancestor]??[];const attrs={};
        for(let a=0;a<attributes.length;a+=2)attrs[snapshot.strings[attributes[a]]]=snapshot.strings[attributes[a+1]];
        ancestry.push({nodeName:snapshot.strings[nodes.nodeName[ancestor]],attributes:attrs});
        ancestor=nodes.parentIndex[ancestor];
      }
      const logicalId=ancestry.find(node=>node.attributes['data-runtime-case'])?.attributes['data-runtime-case'];
      if(logicalId) rows.push({logicalId,documentIndex,backendNodeId:nodes.backendNodeId[nodeIndex],text:fullText.slice(start,start+length),startUtf16:start,lengthUtf16:length,documentBounds:{x:bounds[0],y:bounds[1],width:bounds[2],height:bounds[3]},ancestry});
    }
  }
  return rows;
}

export function decodeShadowTextBoxes(snapshot) {
  const parents=new Map(),rows=[];
  snapshot.domNodes.forEach((node,index)=>{for(const child of node.childNodeIndexes??[]) {
    if(parents.has(child))throw new Error('ambiguous_shadow_parent');parents.set(child,index);
  }});
  for(const layout of snapshot.layoutTreeNodes) {
    const node=snapshot.domNodes[layout.domNodeIndex];
    if(node?.shadowRootType!=='user-agent')continue;
    const ancestry=[];let index=layout.domNodeIndex;const visited=new Set();
    while(index!==undefined) {
      if(visited.has(index)||!snapshot.domNodes[index])throw new Error('invalid_shadow_ancestry');
      visited.add(index);const item=snapshot.domNodes[index];
      ancestry.push({nodeName:item.nodeName,attributes:Object.fromEntries((item.attributes??[]).map(attr=>[attr.name,attr.value]))});
      index=parents.get(index);
    }
    const logicalId=ancestry.find(item=>item.attributes['data-runtime-case'])?.attributes['data-runtime-case'];
    if(!logicalId)continue;
    for(const box of layout.inlineTextNodes??[]) {
      const bounds=box.boundingBox,start=box.startCharacterIndex,length=box.numCharacters;
      if(!bounds||!['x','y','width','height'].every(key=>Number.isFinite(bounds[key]))||bounds.width<0||bounds.height<0||!Number.isInteger(start)||start<0||!Number.isInteger(length)||length<0||typeof layout.layoutText!=='string'||start+length>layout.layoutText.length)throw new Error('invalid_shadow_text_box');
      rows.push({logicalId,backendNodeId:node.backendNodeId,surface:'user-agent-shadow',text:layout.layoutText.slice(start,start+length),startUtf16:start,lengthUtf16:length,documentBounds:bounds,ancestry});
    }
  }
  return rows;
}

export async function probeTextBoxes(outputDirectory,referenceDirectory) {
  const output=resolve(outputDirectory),reference=resolve(referenceDirectory);
  if(!output.startsWith(join(ROOT,'artifacts')+sep) || output===reference || output.startsWith(reference+sep))throw new Error('invalid_text_probe_output');
  await mkdir(output,{recursive:true});
  const reportPath=join(output,'text_box_report.json');
  await writeFile(reportPath,JSON.stringify({status:'RUNNING',admissionEligible:false})+'\n');
  try {
    const baseline=await jsonFile(join(reference,'component_ir.json'));
    if(baseline.status!=='PASS')throw new Error('invalid_text_probe_reference');
    let observed;
    const {result}=await extractRuntime(output,{observePage:async(page,context)=>{
      const session=await page.context().newCDPSession(page);
      try {
        const snapshot=await session.send('DOMSnapshot.captureSnapshot',{computedStyles:[],includeDOMRects:true});
        // captureSnapshot omits some user-agent placeholder layout text.
        // Keep deprecated shadow-inclusive API evidence separate, never guess boxes.
        const shadowSnapshot=await session.send('DOMSnapshot.getSnapshot',{computedStyleWhitelist:[],includeUserAgentShadowTree:true});
        await writeFile(join(output,'shadow_dom_snapshot.json'),JSON.stringify(shadowSnapshot)+'\n');
        const origins=await page.evaluate(()=>Object.fromEntries([...document.querySelectorAll('[data-runtime-case]')].map(element=>{
          const b=element.firstElementChild.getBoundingClientRect();return [element.getAttribute('data-runtime-case'),{x:b.x,y:b.y}];
        })));
        const observations=[...decodeTextBoxes(snapshot).map(row=>({...row,surface:'snapshot-layout'})),...decodeShadowTextBoxes(shadowSnapshot)].map(row=>({...row,componentBounds:{...row.documentBounds,x:row.documentBounds.x-origins[row.logicalId].x,y:row.documentBounds.y-origins[row.logicalId].y}}));
        const renderingSettings=await page.evaluate(()=>[...document.querySelectorAll('[data-runtime-case]')].map(container=>{
          const properties=['font-family','font-weight','font-style','font-size','font-synthesis','font-kerning','font-feature-settings','font-variation-settings','text-rendering','-webkit-font-smoothing','-moz-osx-font-smoothing','opacity','box-shadow','text-shadow','filter','mix-blend-mode','text-transform','text-decoration-line','letter-spacing'];
          const root=container.firstElementChild;
          const rows=[];
          function walk(element,path) {
            for(const surface of ['element','::before','::placeholder']) {
              if(surface==='::placeholder'&&element.tagName!=='INPUT')continue;
              const style=getComputedStyle(element,surface==='element'?null:surface);
              rows.push({path,surface,tag:element.tagName.toLowerCase(),properties:Object.fromEntries(properties.map(key=>[key,style.getPropertyValue(key)]))});
            }
            [...element.children].forEach((child,index)=>walk(child,path+'.'+index));
          }
          walk(root,'0');return {logicalId:container.getAttribute('data-runtime-case'),rows};
        }));
        const canvasMetrics=await page.evaluate(()=>{
          const output=[];
          for(const container of document.querySelectorAll('[data-runtime-case]')) {
            const root=container.firstElementChild;
            const targets=[...root.querySelectorAll('*'),root];
            for(const element of targets) {
              const elementBounds=element.getBoundingClientRect(),elementStyle=getComputedStyle(element);
              if(elementBounds.width<=0||elementBounds.height<=0||elementStyle.visibility!=='visible')continue;
              const samples=[];
              if(element.tagName==='INPUT'&&element.getAttribute('placeholder'))samples.push({surface:'::placeholder',text:element.getAttribute('placeholder')});
              if(element.childElementCount===0&&element.textContent.trim())samples.push({surface:'element',text:element.textContent});
              const before=getComputedStyle(element,'::before');
              if(before.content.startsWith('"')&&before.content!=='""'&&before.display!=='none')samples.push({surface:'::before',text:JSON.parse(before.content)});
              for(const sample of samples) {
                const style=getComputedStyle(element,sample.surface==='element'?null:sample.surface);
                const ctx=document.createElement('canvas').getContext('2d');
                ctx.font=style.font;ctx.fontKerning=style.fontKerning;
                const metric=ctx.measureText(sample.text);
                output.push({logicalId:container.getAttribute('data-runtime-case'),...sample,requestedFont:style.font,canvasFont:ctx.font,
                  metrics:Object.fromEntries(['width','actualBoundingBoxLeft','actualBoundingBoxRight','actualBoundingBoxAscent','actualBoundingBoxDescent','fontBoundingBoxAscent','fontBoundingBoxDescent'].map(key=>[key,metric[key]]))});
              }
            }
          }
          return output;
        });
        observed={environment:context.environment,provenance:context.provenance,observations,renderingSettings,canvasMetrics};
        await writeFile(join(output,'dom_snapshot.json'),JSON.stringify(snapshot)+'\n');
      } finally {await session.detach();}
    }});
    const referenceMatches=result.components.map(component=>{const expected=baseline.components.find(item=>item.logicalComponentId===component.logicalComponentId);return {logicalId:component.logicalComponentId,screenshotMatches:expected?.screenshot.sha256===component.screenshot.sha256,environmentMatches:JSON.stringify(expected?.environment)===JSON.stringify(component.environment)};});
    const report={scope:'official_runtime_text_box_diagnostic',status:referenceMatches.length===baseline.components.length && referenceMatches.every(row=>row.screenshotMatches&&row.environmentMatches)?'PASS':'REVIEW',referenceComponentIrSha256:hash(await readFile(join(reference,'component_ir.json'))),referenceMatches,...observed,admissionEligible:false,fidelityGate:'NOT_RUN',limitations:['Post-layout UTF-16 text boxes are not per-glyph ink outlines or native Figma measurements.','CDP backend node identities remain supplemental browser evidence, outside Core/Component IR.','Canvas metrics are separate browser text samples; their ink bounds do not establish DOM baseline, glyph outline equality, or native font-file identity.']};
    await writeFile(reportPath,JSON.stringify(report,null,2)+'\n');return report;
  } catch(error) {await writeFile(reportPath,JSON.stringify({scope:'official_runtime_text_box_diagnostic',status:'FAIL',admissionEligible:false,issues:[{code:error.message}]})+'\n');throw error;}
}

if(process.argv[1] && import.meta.url===pathToFileURL(resolve(process.argv[1])).href) {
  const out=process.argv.indexOf('--output'),ref=process.argv.indexOf('--reference');
  if(out<0||ref<0||!process.argv[out+1]||!process.argv[ref+1])throw new Error('Usage: text-box-probe.mjs --output <new artifacts> --reference <reference>');
  const report=await probeTextBoxes(process.argv[out+1],process.argv[ref+1]);
  console.log(JSON.stringify({status:report.status,observations:report.observations.map(({logicalId,text,componentBounds})=>({logicalId,text,componentBounds}))}));
}
