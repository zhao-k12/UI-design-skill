import {readFile,writeFile,mkdir,readdir} from 'node:fs/promises';
import {resolve,join} from 'node:path';
import {pathToFileURL} from 'node:url';
import {extractRuntime} from './extract.mjs';
import {ROOT,hash,jsonFile} from '../source-reader/source-lock.mjs';

export async function renderNativeSvg(page,row) {
  if(!Number.isInteger(row.width)||!Number.isInteger(row.height)||row.width<=0||row.height<=0||row.width>4096||row.height>4096||row.width*row.height>4000000||typeof row.svg!=='string'||row.svg.length>1000000||/<!|<\?/.test(row.svg))throw Error('invalid_native_svg_input');
  await page.setContent('<html><head><style>html,body{margin:0;background:white}svg{display:block}</style></head><body></body></html>');
  const bounds=await page.evaluate(({svg,width,height})=>{
    const doc=new DOMParser().parseFromString(svg,'image/svg+xml');
    const allowed={svg:['width','height','viewBox','fill','xmlns'],rect:['x','y','width','height','rx','fill','stroke','stroke-width','transform'],
      path:['d','fill','stroke','stroke-width','fill-rule','clip-rule','mask'],g:['clip-path'],defs:[],clipPath:['id'],mask:['id','fill']};
    for(const node of doc.querySelectorAll('*')) {
      if(node.namespaceURI!=='http://www.w3.org/2000/svg'||!allowed[node.localName])throw Error('unsupported_native_svg_element');
      for(const attr of node.attributes) {
        if(!allowed[node.localName].includes(attr.name))throw Error('unsupported_native_svg_attribute');
        if(['fill','stroke'].includes(attr.name)&&! /^(none|white|black|#[0-9a-fA-F]{3,8})$/.test(attr.value))throw Error('unsupported_native_svg_paint');
        if(['clip-path','mask'].includes(attr.name)&&!/^url\(#[a-zA-Z0-9_-]+\)$/.test(attr.value))throw Error('external_native_svg_resource');
        if(attr.name==='transform'&&!/^translate\([-+0-9.]+(?:[ ,]+[-+0-9.]+)?\)$/.test(attr.value))throw Error('unsupported_native_svg_transform');
      }
    }
    const ids=[...doc.querySelectorAll('[id]')].map(node=>node.id);if(new Set(ids).size!==ids.length)throw Error('duplicate_native_svg_resource');
    for(const node of doc.querySelectorAll('[clip-path],[mask]'))for(const key of ['clip-path','mask'])if(node.hasAttribute(key)&&!ids.includes(node.getAttribute(key).slice(5,-1)))throw Error('missing_native_svg_resource');
    const root=doc.documentElement;
    if(root.localName!=='svg'||root.getAttribute('width')!==String(width)||root.getAttribute('height')!==String(height)||root.getAttribute('viewBox')!==`0 0 ${width} ${height}`)throw Error('native_svg_geometry_changed');
    document.body.appendChild(document.importNode(root,true));
    const b=document.querySelector('svg').getBoundingClientRect();return {x:b.x,y:b.y,width:b.width,height:b.height};
  },row);
  if(bounds.x!==0||bounds.y!==0||bounds.width!==row.width||bounds.height!==row.height)throw Error('native_svg_browser_bounds_changed');
  return {bounds,png:await page.locator('svg').screenshot({animations:'disabled'})};
}

export async function probeNativeSvg(capturePath,referenceDirectory,outputDirectory,fixtureOptions={}) {
  const output=resolve(outputDirectory),reference=resolve(referenceDirectory),capture=resolve(capturePath);
  if(!output.startsWith(resolve(ROOT,'artifacts')+'/')&&!output.startsWith(resolve(ROOT,'artifacts')+'\\'))throw Error('native_svg_output_must_be_artifacts');
  if(output===reference||reference.startsWith(output)||output.startsWith(reference)||capture.startsWith(output))throw Error('native_svg_output_overlaps_inputs');
  const existing=await readdir(output).catch(error=>{if(error.code==='ENOENT')return [];throw error;});
  if(existing.length)throw Error('native_svg_requires_empty_new_output');
  const evidence=await jsonFile(capture),baseline=await jsonFile(join(reference,'component_ir.json'));
  if(evidence.scope!=='figma_native_component_svg_diagnostic'||evidence.status!=='PASS'||evidence.admissionEligible!==false||evidence.createdNodeIds.length||evidence.mutatedNodeIds.length)throw Error('invalid_native_svg_capture');
  if(evidence.observations.length!==baseline.components.length||new Set(evidence.observations.map(row=>row.logicalId)).size!==baseline.components.length||evidence.observations.some(row=>!/^[a-zA-Z0-9_.-]+$/.test(row.logicalId)||!baseline.components.some(c=>c.logicalComponentId===row.logicalId)))throw Error('invalid_native_svg_inventory');
  await mkdir(output,{recursive:true});const samples=[];
  const reportPath=join(output,'native-svg-raster-report.json');
  await writeFile(reportPath,JSON.stringify({scope:'browser_raster_of_native_svg_diagnostic',status:'RUNNING',admissionEligible:false})+'\n',{flag:'wx'});
  const {result}=await extractRuntime(output,{...fixtureOptions,observePage:async(page)=>{
    const sandbox=await page.context().newPage();await sandbox.route('**/*',route=>route.abort());
    try {
      for(const row of evidence.observations) {
        const rendered=await renderNativeSvg(sandbox,row),name='svg-raster-'+row.logicalId+'.png';
        await writeFile(join(output,name),rendered.png,{flag:'wx'});
        samples.push({logicalId:row.logicalId,componentReference:row.componentReference,svgSha256:hash(Buffer.from(row.svg)),
          browserBounds:rendered.bounds,pngPath:name,pngSha256:hash(rendered.png)});
      }
    } finally {await sandbox.close();}
  }}).catch(async error=>{await writeFile(reportPath,JSON.stringify({scope:'browser_raster_of_native_svg_diagnostic',status:'FAIL',admissionEligible:false,fidelityGate:'NOT_RUN',issues:[{code:error.message}]})+'\n');throw error;});
  const matches=result.components.map(row=>{const old=baseline.components.find(c=>c.logicalComponentId===row.logicalComponentId);return {logicalId:row.logicalComponentId,screenshotMatches:row.screenshot.sha256===old.screenshot.sha256,environmentMatches:JSON.stringify(row.environment)===JSON.stringify(old.environment)};});
  const report={scope:'browser_raster_of_native_svg_diagnostic',status:matches.every(row=>row.screenshotMatches&&row.environmentMatches)?'PASS':'REVIEW',
    svgCaptureSha256:hash(await readFile(capture)),referenceComponentIrSha256:hash(await readFile(join(reference,'component_ir.json'))),
    probeScriptSha256:hash(await readFile(new URL(import.meta.url))),
    referenceMatches:matches,environment:result.components[0].environment,samples,admissionEligible:false,fidelityGate:'NOT_RUN',
    limitations:['Browser rendering of native outlined SVG is a diagnostic sample, not native Figma PNG or editable component admission.','Official DOM/CSS/reference images are preserved; font hinting in live text is not represented by outlined SVG.']};
  await writeFile(reportPath,JSON.stringify(report,null,2)+'\n');return report;
}
if(process.argv[1]&&import.meta.url===pathToFileURL(resolve(process.argv[1])).href) {
  const args=process.argv.slice(2);if(args.length!==3)throw Error('Usage: native-svg-probe.mjs <capture.json> <reference> <new artifacts>');
  const report=await probeNativeSvg(...args);console.log(JSON.stringify({status:report.status,samples:report.samples.map(row=>row.logicalId)}));
}
