import {readFile,writeFile,mkdir,readdir} from 'node:fs/promises';
import {resolve,join} from 'node:path';
import {extractRuntime} from './extract.mjs';
import {ROOT,hash,jsonFile} from '../source-reader/source-lock.mjs';

export async function probeFontFile(referenceDirectory,identityPath,outputDirectory,fixtureOptions={}) {
  const reference=resolve(referenceDirectory),output=resolve(outputDirectory);
  if(!output.startsWith(resolve(ROOT,'artifacts')+'\\')&&!output.startsWith(resolve(ROOT,'artifacts')+'/'))throw Error('font_file_probe_output_invalid');
  if(output.startsWith(reference)||resolve(identityPath).startsWith(output))throw Error('font_file_probe_overlaps_input');
  if((await readdir(output).catch(error=>{if(error.code==='ENOENT')return [];throw error;})).length)throw Error('font_file_probe_requires_new_output');
  const identity=await jsonFile(identityPath),baseline=await jsonFile(join(reference,'component_ir.json'));
  const requirement=identity.requirements.find(row=>row.familyName==='PingFang SC');
  if(identity.status!=='PASS'||requirement?.matches?.length!==1)throw Error('font_file_identity_ambiguous');
  const font=await readFile(requirement.matches[0].path);
  if(hash(font)!==requirement.matches[0].fileSha256)throw Error('font_file_probe_hash_mismatch');
  await mkdir(output,{recursive:true});let observations;
  const reportPath=join(output,'font-file-probe-report.json');
  await writeFile(reportPath,JSON.stringify({scope:'browser_font_file_binding_diagnostic',status:'RUNNING',admissionEligible:false})+'\n',{flag:'wx'});
  const {result}=await extractRuntime(output,{...fixtureOptions,observePage:async(page)=>{
    await page.route('**/__diagnostic_pingfang.otf',route=>route.fulfill({body:font,contentType:'font/otf'}));
    const fontInfo=await page.evaluate(async()=>{
      const face=new FontFace('DiagnosticFilePingFang','url(/__diagnostic_pingfang.otf)',{style:'normal',weight:'400'});
      await face.load();document.fonts.add(face);window.__diagnosticFont=face;return {status:face.status};
    });
    const selectors={'action.button.primary.medium':'.ivu-btn > span',
      'form.input.default.medium':'input.ivu-input','form.select.default.medium':'.ivu-select-selected-value',
      'data.table.default':'.ivu-table-cell > span'};
    const rows=[];
    try {
      for(const component of baseline.components) {
        const logicalId=component.logicalComponentId,selector=selectors[logicalId];if(!selector)throw Error('unsupported_font_probe_component');
        const owner=page.locator(`[data-runtime-case="${logicalId}"] ${selector}`);
        const before=await owner.evaluateAll(nodes=>nodes.map(node=>({style:node.getAttribute('style'),bounds:JSON.stringify(node.getBoundingClientRect().toJSON())})));
        if(!before.length)throw Error('font_probe_owner_missing');
        const families=await owner.evaluateAll(nodes=>nodes.map(node=>getComputedStyle(node).fontFamily));
        if(new Set(families).size!==1||!families[0].includes('"PingFang SC"'))throw Error('unsupported_font_probe_fallback_stack');
        // Replace only the actual CJK fallback slot. Preserve the first Latin
        // family, which supplies the inline strut in an official Table cell.
        const diagnosticFamily=families[0].replace('"PingFang SC"','DiagnosticFilePingFang');
        try {
          await page.evaluate(({logicalId,selector,diagnosticFamily})=>{
            const style=document.createElement('style');style.textContent=`[data-runtime-case="${logicalId}"] ${selector}{font-family:${diagnosticFamily}!important}`;
            document.head.appendChild(style);window.__diagnosticFontStyle=style;
          },{logicalId,selector,diagnosticFamily});
          const during=await owner.evaluateAll(nodes=>nodes.map(node=>({bounds:JSON.stringify(node.getBoundingClientRect().toJSON()),family:getComputedStyle(node).fontFamily})));
          const png=await page.locator(`[data-runtime-case="${logicalId}"] > :first-child`).screenshot({animations:'disabled'});
          const name='file-bound-'+logicalId+'.png';await writeFile(join(output,name),png,{flag:'wx'});
          rows.push({logicalId,pngPath:name,pngSha256:hash(png),ownerBoundsUnchanged:before.length===during.length&&before.every((row,i)=>row.bounds===during[i].bounds),ownerGeometry:{before,during},computedFamily:during.map(row=>row.family),fontLoadStatus:fontInfo.status});
        } finally {
          await page.evaluate(()=>{window.__diagnosticFontStyle?.remove();delete window.__diagnosticFontStyle;});
          await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(resolve)));
          const restored=await owner.evaluateAll(nodes=>nodes.map(node=>({style:node.getAttribute('style'),bounds:JSON.stringify(node.getBoundingClientRect().toJSON())})));
          if(JSON.stringify(before)!==JSON.stringify(restored))throw Error('font_file_probe_owner_not_restored:'+JSON.stringify({before,restored}));
        }
      }
    } finally {
      await page.evaluate(()=>{document.fonts.delete(window.__diagnosticFont);delete window.__diagnosticFont;});
      await page.unroute('**/__diagnostic_pingfang.otf');
    }
    observations=rows;
  }}).catch(async error=>{await writeFile(reportPath,JSON.stringify({scope:'browser_font_file_binding_diagnostic',status:'FAIL',admissionEligible:false,issues:[{code:error.message}]})+'\n');throw error;});
  const matches=result.components.map(row=>{const old=baseline.components.find(c=>c.logicalComponentId===row.logicalComponentId);return {logicalId:row.logicalComponentId,screenshotMatches:row.screenshot.sha256===old.screenshot.sha256,environmentMatches:JSON.stringify(row.environment)===JSON.stringify(old.environment)};});
  const report={scope:'browser_font_file_binding_diagnostic',status:matches.every(row=>row.screenshotMatches&&row.environmentMatches)?'PASS':'REVIEW',
    fontFileSha256:hash(font),probeScriptSha256:hash(await readFile(new URL(import.meta.url))),referenceMatches:matches,observations,
    referenceComponentIrSha256:hash(await readFile(join(reference,'component_ir.json'))),
    temporaryFontFaceRemoved:true,ownerStatesRestored:true,admissionEligible:false,fidelityGate:'NOT_RUN',
    limitations:['Temporary explicit font-file binding is a diagnostic experiment, not an alteration of the official reference.','Native uploaded-file bytes and renderer behavior remain independent.']};
  await writeFile(reportPath,JSON.stringify(report,null,2)+'\n');return report;
}
if(process.argv[1]?.endsWith('font-file-probe.mjs')) {
  const report=await probeFontFile(...process.argv.slice(2));console.log(JSON.stringify({status:report.status,observations:report.observations}));
}
