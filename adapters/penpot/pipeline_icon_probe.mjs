// Offline source/native SVG raster diagnostic; never substitutes a native PNG.
import {readFile,writeFile,mkdir,readdir} from 'node:fs/promises';
import {resolve,join} from 'node:path';
import {extractRuntime} from '../../component-builder/runtime-renderer/extract.mjs';
import {ROOT,hash,jsonFile} from '../../component-builder/source-reader/source-lock.mjs';

const [receiptPath,planPath,outputPath]=process.argv.slice(2),output=resolve(outputPath);
if(!output.startsWith(resolve(ROOT,'artifacts')+'/')&&!output.startsWith(resolve(ROOT,'artifacts')+'\\'))throw Error('icon_probe_output_scope');
if((await readdir(output).catch(e=>{if(e.code==='ENOENT')return [];throw e;})).length)throw Error('icon_probe_output_not_empty');
const receipt=await jsonFile(receiptPath),native=receipt.result,plan=await jsonFile(planPath);
if(native.status!=='CAPTURED'||native.scope!=='production-native-instance-capture'||native.platform!=='penpot'||native.createdNodeIds.length||native.mutatedNodeIds.length||native.fileReference!==plan.fileReference)throw Error('icon_probe_invalid_capture');
const bindings=await jsonFile(new URL('./metadata/icon-bindings.json',import.meta.url));
if(bindings.registrySha256!==plan.registrySha256)throw Error('icon_instance_source_registry_mismatch');
await mkdir(output,{recursive:true});const observations=[];
const {result}=await extractRuntime(output,{observePage:async page=>{
  const sandbox=await page.context().newPage();await sandbox.route('**/*',route=>route.abort());
  try{
    for(const item of plan.icons){
      const row=native.instances.find(i=>i.componentReference===bindings.bindings[item.iconId]?.componentReference);
      if(!row||row.componentReference!==bindings.bindings[item.iconId]?.componentReference||!row.isComponentCopy||!row.isRealMain||!row.nativeSvgBase64||hash(Buffer.from(item.svg))!==item.svgSha256)throw Error('icon_probe_source_mismatch');
      const nativeSvg=Buffer.from(row.nativeSvgBase64,'base64').toString('utf8'),samples={};
      for(const [role,svg] of [['source',item.svg],['native',nativeSvg]]){
        if(/<!|<\?|<script|<foreignObject|href=|url\(|\son\w+=/i.test(svg))throw Error('unsafe_icon_svg');
        await sandbox.setContent('<html><head><style>html,body{margin:0;background:white}svg{display:block;width:24px;height:24px;color:black}</style></head><body></body></html>');
        const observed=await sandbox.evaluate(({svg})=>{
          const doc=new DOMParser().parseFromString(svg,'image/svg+xml');
          const allowed=new Set(['svg','g','path','rect']);
          for(const el of doc.querySelectorAll('*'))if(el.namespaceURI!=='http://www.w3.org/2000/svg'||!allowed.has(el.localName))throw Error('unsupported_icon_svg_element');
          if(doc.documentElement.getAttribute('viewBox')!=='0 0 24 24')throw Error('icon_viewbox_mismatch');
          document.body.appendChild(document.importNode(doc.documentElement,true));
          return {paths:[...document.querySelectorAll('svg path')].map(p=>({d:p.getAttribute('d'),fill:getComputedStyle(p).fill,fillOpacity:getComputedStyle(p).fillOpacity,opacity:getComputedStyle(p).opacity,transform:p.getAttribute('transform'),fillRule:getComputedStyle(p).fillRule}))};
        },{svg});
        const png=await sandbox.locator('svg').screenshot({animations:'disabled'});await writeFile(join(output,item.iconId+'.'+role+'.png'),png,{flag:'wx'});
        samples[role]={...observed,svgSha256:hash(Buffer.from(svg)),pngSha256:hash(png)};
      }
      observations.push({iconId:item.iconId,componentReference:row.componentReference,...samples,sourceNativeVectorPngBytesEqual:samples.source.pngSha256===samples.native.pngSha256});
    }
  }finally{await sandbox.close();}
}});
const report={status:'OBSERVED',scope:'penpot-real-icon-instance-svg-diagnostic',completeNativeCapture:native.status==='CAPTURED',nativeReceiptSha256:hash(await readFile(receiptPath)),sourcePlanSha256:hash(await readFile(planPath)),probeScriptSha256:hash(await readFile(new URL(import.meta.url))),environment:result.components[0].environment,observations,admissionEligible:false};
await writeFile(join(output,'icon-svg-probe.json'),JSON.stringify(report,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify(report));
