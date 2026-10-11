// Independent source font-file effects and unmodified native SVG rasterization.
import {readFile,writeFile,mkdir,readdir} from 'node:fs/promises';
import {join,resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {ROOT,hash,jsonFile} from '../../component-builder/source-reader/source-lock.mjs';
import {extractRuntime} from '../../component-builder/runtime-renderer/extract.mjs';
import {compileTableRequest} from '../../component-builder/runtime-renderer/table-request.mjs';
import {probeNativeSvg} from '../../component-builder/runtime-renderer/native-svg-probe.mjs';

export async function probeTableSvg(capture,source,output){
  const compiled=compileTableRequest(await jsonFile(join(source,'request.json')));
  return probeNativeSvg(capture,source,output,{casesData:compiled.cases,harnessPath:join(ROOT,'component-builder/runtime-renderer/configurable-table-harness.js')});
}

export async function probeTableFonts(source,fontManifest,outputDirectory){
  const output=resolve(outputDirectory),reference=resolve(source);
  if(!output.startsWith(resolve(ROOT,'artifacts')+'\\')&&!output.startsWith(resolve(ROOT,'artifacts')+'/'))throw Error('font_probe_output_must_be_artifacts');
  if(reference.startsWith(output)||output.startsWith(reference)||(await readdir(output).catch(e=>{if(e.code==='ENOENT')return [];throw e;})).length)throw Error('font_probe_requires_new_independent_output');
  const manifest=await jsonFile(fontManifest),files={};
  const expectedHashes={Arial:'c9b76220a5be42ead4733611e417cd65c5fd8aeaa33eb56576ac378a37d130a1','PingFang SC':'0934ea94dea57d9ec12a401f44ad28b98c96f5ee9917df920279f58024de523a'};
  if(JSON.stringify(Object.keys(manifest).sort())!==JSON.stringify(Object.keys(expectedHashes).sort()))throw Error('font_inventory_mismatch');
  for(const [family,item] of Object.entries(manifest)){const bytes=await readFile(item.path);if(bytes.length>64*1024*1024||hash(bytes)!==expectedHashes[family]||item.sha256!==expectedHashes[family])throw Error('source_font_hash_mismatch');files[family]=bytes;}
  const baseline=await jsonFile(join(source,'component_ir.json')),compiled=compileTableRequest(await jsonFile(join(source,'request.json')));
  const logicalId=compiled.cases.cases[0].logicalId;let observation;
  await mkdir(output,{recursive:true});
  const {result}=await extractRuntime(output,{casesData:compiled.cases,harnessPath:join(ROOT,'component-builder/runtime-renderer/configurable-table-harness.js'),observePage:async page=>{
    await page.route('**/__task019_arial.ttf',route=>route.fulfill({body:files.Arial,contentType:'font/ttf'}));
    await page.route('**/__task019_pingfang.otf',route=>route.fulfill({body:files['PingFang SC'],contentType:'font/otf'}));
    const faces=await page.evaluate(async()=>{
      const a=new FontFace('Task019FileArial','url(/__task019_arial.ttf)',{style:'normal',weight:'400'}),b=new FontFace('Task019FilePingFang','url(/__task019_pingfang.otf)',{style:'normal',weight:'400'});
      await Promise.all([a.load(),b.load()]);document.fonts.add(a);document.fonts.add(b);window.__task019Faces=[a,b];return[a.status,b.status];
    });
    const selector=`[data-runtime-case="${logicalId}"] .ivu-table-tbody .ivu-table-cell > span`,owner=page.locator(selector);
    const read=nodes=>nodes.map(n=>({characters:n.textContent,style:n.getAttribute('style'),bounds:n.getBoundingClientRect().toJSON()}));
    const before=await owner.evaluateAll(read);const expected=compiled.request.records.flatMap(r=>compiled.request.columns.map(c=>r[c.key]));
    if(JSON.stringify(before.map(r=>r.characters))!==JSON.stringify(expected))throw Error('source_font_owner_inventory_mismatch');
    let restored;
    try{
      await page.evaluate(selector=>{const style=document.createElement('style');style.textContent=selector+'{font-family:Task019FileArial,Task019FilePingFang!important}';document.head.appendChild(style);window.__task019Style=style;},selector);
      const during=await owner.evaluateAll(read);const png=await page.locator(`[data-runtime-case="${logicalId}"] > :first-child`).screenshot({animations:'disabled'});
      await writeFile(join(output,'file-bound.png'),png,{flag:'wx'});
      observation={logicalId,fontLoadStatus:faces,ownerGeometry:{before,during},ownerBoundsUnchanged:JSON.stringify(before.map(r=>r.bounds))===JSON.stringify(during.map(r=>r.bounds)),pngSha256:hash(png)};
    }finally{
      await page.evaluate(()=>{window.__task019Style?.remove();delete window.__task019Style;});
      restored=await owner.evaluateAll(read);
      await page.evaluate(()=>{for(const f of window.__task019Faces)document.fonts.delete(f);delete window.__task019Faces;});
      await page.unroute('**/__task019_arial.ttf');await page.unroute('**/__task019_pingfang.otf');
    }
    if(JSON.stringify(before)!==JSON.stringify(restored))throw Error('source_font_owners_not_restored');
  }});
  const matches=result.components.map(row=>{const old=baseline.components.find(c=>c.logicalComponentId===row.logicalComponentId);return{logicalId:row.logicalComponentId,screenshotMatches:row.screenshot.sha256===old.screenshot.sha256,environmentMatches:JSON.stringify(row.environment)===JSON.stringify(old.environment)};});
  const report={scope:'mixed_source_font_file_effect_diagnostic',status:matches.every(r=>r.screenshotMatches&&r.environmentMatches)&&observation.ownerBoundsUnchanged&&observation.pngSha256===baseline.components[0].screenshot.sha256?'OBSERVED':'REVIEW',fontFiles:manifest,referenceComponentIrSha256:hash(await readFile(join(source,'component_ir.json'))),probeScriptSha256:hash(await readFile(new URL(import.meta.url))),referenceMatches:matches,observation,ownerStatesRestored:true,temporaryFontFacesRemoved:true,admissionEligible:false,fidelityGate:'NOT_RUN'};
  await writeFile(join(output,'font-file-probe.json'),JSON.stringify(report,null,2)+'\n',{flag:'wx'});return report;
}

if(process.argv[1]&&import.meta.url===pathToFileURL(resolve(process.argv[1])).href){
  const [mode,a,b,c]=process.argv.slice(2);const report=mode==='svg'?await probeTableSvg(a,b,c):mode==='fonts'?await probeTableFonts(a,b,c):null;if(!report)throw Error('unsupported_probe_mode');console.log(JSON.stringify({status:report.status,referenceMatches:report.referenceMatches}));
}
