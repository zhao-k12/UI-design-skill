import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile,mkdtemp,rm} from 'node:fs/promises';
import {join} from 'node:path';
import vm from 'node:vm';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {ROOT,hash} from '../component-builder/source-reader/source-lock.mjs';

test('missing Arial, wrong native context and duplicate candidate abort before any shape writes',async()=>{
  const context=vm.createContext({});
  vm.runInContext(await readFile(join(ROOT,'adapters/penpot/component_candidate.js'),'utf8')+'\n'+await readFile(join(ROOT,'adapters/penpot/configurable_table_candidate.js'),'utf8'),context);
  const logical='data.table.config.'+'a'.repeat(64),spec={fileReference:'file',pageReference:'page',logicalId:logical,requiredFonts:['Arial','PingFang SC']};
  let writes=0;
  const api={currentFile:{id:'file'},currentPage:{id:'page',root:{children:[]}},library:{local:{components:[]}},fonts:{all:[{fontFamily:'PingFang SC',variants:[{fontWeight:'400',fontStyle:'normal',fontVariantId:'normal-400'}]}]},createBoard(){writes++;throw Error('unexpected write');}};
  await assert.rejects(()=>context.buildConfigurablePenpotTableCandidate(api,spec),/candidate_exact_font_missing_or_ambiguous:Arial/);
  await assert.rejects(()=>context.buildConfigurablePenpotTableCandidate(api,{...spec,fileReference:'other'}),/candidate_context_mismatch/);
  api.currentPage.root.children=[{name:'candidate / '+logical+' / penpot-v1'}];
  await assert.rejects(()=>context.buildConfigurablePenpotTableCandidate(api,spec),/candidate_requires_recovery/);
  assert.equal(writes,0);
});

test('actual typography extraction records Arial and CJK baselines, and refuses overwriting evidence',async()=>{
  const directory=await mkdtemp(join(ROOT,'artifacts','table-typography-test-'));
  const output=join(directory,'source'),script=join(ROOT,'component-builder/runtime-renderer/table-typography-extract.mjs');
  const run=promisify(execFile);
  try{
    const args=[script,'--request',join(ROOT,'examples/table-source-request.json'),'--output',output];
    await run(process.execPath,args,{cwd:ROOT});
    const observation=JSON.parse(await readFile(join(output,'table-observation.json'),'utf8'));
    assert.equal(observation.baselines.length,4);assert.ok(observation.baselines.every(r=>r.restored));
    assert.deepEqual(observation.fonts.map(f=>f[0].familyName),['PingFang SC','Arial','PingFang SC','Arial']);
    const receipt=JSON.parse(await readFile(join(output,'configurable-source.json'),'utf8'));
    assert.equal(receipt.scriptSha256,hash(await readFile(script)));
    assert.equal(receipt.scriptSha256,hash(await readFile(join(output,'source-extractor.mjs'))));
    const original=await readFile(join(output,'component_ir.json'));
    await assert.rejects(()=>run(process.execPath,args,{cwd:ROOT}),/EEXIST/);
    assert.deepEqual(await readFile(join(output,'component_ir.json')),original);
    await assert.rejects(()=>run(process.execPath,[...args.slice(0,-1),join(ROOT,'registries','forbidden')],{cwd:ROOT}),/invalid_table_output/);
  }finally{await rm(directory,{recursive:true,force:true});}
});
