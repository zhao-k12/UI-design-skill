import {readFile,writeFile,mkdir,realpath} from 'node:fs/promises';
import {join,resolve,sep} from 'node:path';
import {extractRuntime} from './extract.mjs';
import {ROOT,hash} from '../source-reader/source-lock.mjs';
import {compileTableRequest} from './table-request.mjs';
const args=process.argv.slice(2);
if(args.length!==4||args[0]!=='--request'||args[2]!=='--output')throw Error('Usage: table-typography-extract.mjs --request <json> --output <new artifacts directory>');
const input=JSON.parse(await readFile(args[1],'utf8')),compiled=compileTableRequest(input);
const output=resolve(args[3]);
const artifacts=await realpath(join(ROOT,'artifacts'));
if(!output.startsWith(artifacts+sep))throw Error('invalid_table_output');
let ancestor=resolve(output,'..');
while(true){try{const actual=await realpath(ancestor);if(actual!==artifacts&&!actual.startsWith(artifacts+sep))throw Error('table_output_escapes_artifacts');break;}catch(error){if(error.code!=='ENOENT')throw error;ancestor=resolve(ancestor,'..');}}
await mkdir(resolve(output,'..'),{recursive:true});await mkdir(output);
let observation;
await extractRuntime(output,{casesData:compiled.cases,harnessPath:join(ROOT,'component-builder/runtime-renderer/configurable-table-harness.js'),observePage:async(page,context)=>{
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
await writeFile(join(output,'source-extractor.mjs'),await readFile(new URL(import.meta.url)));
await writeFile(join(output,'request.json'),JSON.stringify(compiled.request,null,2)+'\n');
await writeFile(join(output,'configurable-source.json'),JSON.stringify({status:'PASS',requestSha256:compiled.requestSha256,requestFileSha256:hash(await readFile(join(output,'request.json'))),componentIrSha256:observation.referenceComponentIrSha256,observationSha256:hash(await readFile(join(output,'table-observation.json'))),scriptSha256:hash(await readFile(new URL(import.meta.url))),fidelityGate:'NOT_RUN',productionAdmission:false},null,2)+'\n');
console.log(JSON.stringify({status:observation.status,baselines:observation.baselines.length,fonts:observation.fonts}));
