import {mkdir,readFile,writeFile,realpath} from 'node:fs/promises';
import {resolve,join,sep} from 'node:path';
import {pathToFileURL} from 'node:url';
import {ROOT,hash} from '../source-reader/source-lock.mjs';
import {compileTableRequest} from './table-request.mjs';
import {extractRuntime} from './extract.mjs';

export async function extractTableRequest(request,outputDirectory){
  const compiled=compileTableRequest(request),output=resolve(outputDirectory),artifacts=await realpath(join(ROOT,'artifacts'));
  if(!output.startsWith(artifacts+sep))throw Error('table_output_must_be_new_artifact_directory');
  // Check real ancestors before creation, including junctions outside artifacts.
  let ancestor=resolve(output,'..');
  while(true){try{const actual=await realpath(ancestor);if(actual!==artifacts&&!actual.startsWith(artifacts+sep))throw Error('table_output_escapes_artifacts');break;}catch(error){if(error.code!=='ENOENT')throw error;ancestor=resolve(ancestor,'..');}}
  await mkdir(resolve(output,'..'),{recursive:true});await mkdir(output);
  const writeJson=(name,value)=>writeFile(join(output,name),JSON.stringify(value,null,2)+'\n','utf8');
  await writeJson('request.json',compiled.request);await writeJson('cases.json',compiled.cases);
  const programs={};for(const name of ['table-request.mjs','configurable-table-extract.mjs','configurable-table-harness.js','extract.mjs'])programs[name]=hash(await readFile(join(ROOT,'component-builder/runtime-renderer',name)));
  const base={version:'0.1.0',scope:'configurable_official_table_source',requestSha256:compiled.requestSha256,casesSha256:hash(JSON.stringify(compiled.cases)),
    requestFileSha256:hash(await readFile(join(output,'request.json'))),casesFileSha256:hash(await readFile(join(output,'cases.json'))),programs,
    nativeExecution:'NOT_RUN',fidelityGate:'NOT_RUN',productionAdmission:false};
  await writeJson('table-source-report.json',{...base,status:'RUNNING'});
  try{
    let observation;
    const extracted=await extractRuntime(output,{casesData:compiled.cases,harnessPath:join(ROOT,'component-builder/runtime-renderer/configurable-table-harness.js'),observePage:async page=>{
      observation=await page.evaluate(()=>{
        const root=document.querySelector('[data-runtime-case] > :first-child');
        return {rows:[...root.querySelectorAll('tbody tr')].filter(row=>row.getBoundingClientRect().height>0&&getComputedStyle(row).visibility==='visible').map(row=>[...row.querySelectorAll('td')].map(cell=>cell.textContent)),rootWidth:root.getBoundingClientRect().width};
      });
      const expected=compiled.request.records.map(record=>compiled.request.columns.map(column=>record[column.key]));
      await writeJson('table-observation.json',{...observation,expectedRows:expected});
      if(JSON.stringify(observation.rows)!==JSON.stringify(expected)||observation.rootWidth!==compiled.request.containerWidth)throw Error('official_table_content_or_width_mismatch');
    }});
    const component=extracted.result.components[0];
    if(JSON.stringify(component.resolvedProps.data)!==JSON.stringify(compiled.request.records)||JSON.stringify(component.resolvedProps.columns)!==JSON.stringify(compiled.request.columns))throw Error('official_table_props_mismatch');
    const report={...base,status:'PASS',observation,componentId:component.logicalComponentId,componentIrSha256:hash(await readFile(join(output,'component_ir.json'))),runtimeManifestSha256:hash(await readFile(join(output,'runtime_manifest.json'))),screenshot:component.screenshot};
    await writeJson('table-source-report.json',report);return report;
  }catch(error){await writeJson('table-source-report.json',{...base,status:'FAIL',issues:[String(error.message)]});throw error;}
}

if(process.argv[1]&&import.meta.url===pathToFileURL(resolve(process.argv[1])).href){
  const args=process.argv.slice(2);
  if(args.length!==4||args[0]!=='--request'||args[2]!=='--output')throw Error('Usage: configurable-table-extract.mjs --request <json> --output <new artifacts directory>');
  console.log(JSON.stringify(await extractTableRequest(JSON.parse(await readFile(args[1],'utf8')),args[3]),null,2));
}
