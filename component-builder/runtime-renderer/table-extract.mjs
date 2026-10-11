import {readFile,writeFile,mkdir,readdir} from 'node:fs/promises';
import {join,resolve} from 'node:path';
import {extractRuntime} from './extract.mjs';
import {ROOT,hash} from '../source-reader/source-lock.mjs';
const output=resolve(ROOT,'artifacts/task-009/table-reference');
if((await readdir(output).catch(error=>{if(error.code==='ENOENT')return [];throw error;})).length)throw Error('table_reference_requires_new_output');
await mkdir(output,{recursive:true});
let observation;
await extractRuntime(output,{casesPath:join(ROOT,'component-builder/runtime-renderer/table-cases.json'),harnessPath:join(ROOT,'component-builder/runtime-renderer/table-harness.js'),observePage:async(page,context)=>{
  const baselines=await page.evaluate(()=>{
    const root=document.querySelector('[data-runtime-case] > :first-child'),origin=root.getBoundingClientRect();
    const rect=node=>{const b=node.getBoundingClientRect();return{x:b.x-origin.x,y:b.y-origin.y,width:b.width,height:b.height};};
    return [...root.querySelectorAll('td .ivu-table-cell span')].filter(element=>element.childNodes.length===1&&element.firstChild.nodeType===Node.TEXT_NODE&&element.textContent.trim()).map(element=>{
      const range=document.createRange();range.selectNodeContents(element);const before={root:rect(root),element:rect(element),text:rect(range),html:element.innerHTML};
      const marker=document.createElement('span');marker.style.cssText='all:initial;display:inline-block;width:0;height:0;margin:0;padding:0;border:0;line-height:0;font-size:0;vertical-align:baseline;';
      let baseline;
      try{element.appendChild(marker);const actual=document.createRange();actual.selectNode(element.firstChild);if(JSON.stringify({root:rect(root),element:rect(element),text:rect(actual)})!==JSON.stringify({root:before.root,element:before.element,text:before.text}))throw new Error('table_marker_changed_geometry');baseline=rect(marker).y;}finally{marker.remove();}
      if(JSON.stringify(before)!==JSON.stringify({root:rect(root),element:rect(element),text:rect(range),html:element.innerHTML}))throw new Error('table_marker_restore_failure');
      return {characters:element.textContent,range:before.text,baselineComponentY:baseline,restored:true};
    });
  });
  const cdp=await page.context().newCDPSession(page);await cdp.send('DOM.enable');await cdp.send('CSS.enable');
  const {root}=await cdp.send('DOM.getDocument');const {nodeIds}=await cdp.send('DOM.querySelectorAll',{nodeId:root.nodeId,selector:'td .ivu-table-cell span'});
  const fonts=[];for(const nodeId of nodeIds){const result=await cdp.send('CSS.getPlatformFontsForNode',{nodeId});fonts.push(result.fonts);}await cdp.detach();
  observation={scope:'official_table_runtime_supplement',status:'PASS',...context,baselines,fonts};
}});
observation.referenceComponentIrSha256=hash(await readFile(join(output,'component_ir.json')));
await writeFile(join(output,'table-observation.json'),JSON.stringify(observation,null,2)+'\n');
console.log(JSON.stringify({status:observation.status,baselines:observation.baselines.length,fonts:observation.fonts}));
