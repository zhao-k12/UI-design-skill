import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile,mkdtemp,rm} from 'node:fs/promises';
import {join} from 'node:path';
import {ROOT,hash} from '../component-builder/source-reader/source-lock.mjs';
import {compileTableRequest} from '../component-builder/runtime-renderer/table-request.mjs';
import {compileHeadedTableRequest} from '../component-builder/runtime-renderer/headed-table-request.mjs';
import {extractHeadedTableRequest} from '../component-builder/runtime-renderer/headed-table-extract.mjs';

test('headed identities isolate body admissions and preserve strict input validation',async()=>{
  const request=JSON.parse(await readFile(join(ROOT,'examples/table-source-request.json'),'utf8'));
  const before=structuredClone(request),body=compileTableRequest(request),headed=compileHeadedTableRequest(request);
  assert.deepEqual(request,before);
  assert.notEqual(headed.requestSha256,body.requestSha256);
  assert.notEqual(headed.cases.cases[0].logicalId,body.cases.cases[0].logicalId);
  assert.equal(body.cases.cases[0].props.showHeader,false);
  assert.equal(headed.cases.cases[0].props.showHeader,true);
  assert.deepEqual(compileHeadedTableRequest(request),headed);
  assert.throws(()=>compileHeadedTableRequest({...request,showHeader:true}));
  request.columns[0].title='';assert.throws(()=>compileHeadedTableRequest(request));
});

test('real headed runtime preserves ordered titles/data and binds screenshots without admission',async()=>{
  const directory=await mkdtemp(join(ROOT,'artifacts','headed-table-test-'));
  try{
    for(const [index,fixture] of ['table-source-request.json','table-source-request-four-columns.json'].entries()){
      const request=JSON.parse(await readFile(join(ROOT,'examples',fixture),'utf8')),output=join(directory,String(index));
      const report=await extractHeadedTableRequest(request,output);
      assert.equal(report.status,'PASS');assert.equal(report.productionAdmission,false);
      assert.equal(report.nativeExecution,'NOT_RUN');assert.equal(report.fidelityGate,'NOT_RUN');
      assert.deepEqual(report.observation.headers,request.columns.map(column=>column.title));
      assert.deepEqual(report.observation.rows,request.records.map(row=>request.columns.map(column=>row[column.key])));
      assert.equal(hash(await readFile(join(output,report.screenshot.path))),report.screenshot.sha256);
      const ir=JSON.parse(await readFile(join(output,'component_ir.json'),'utf8'));
      assert.equal(ir.components[0].resolvedProps.showHeader,true);
      assert.deepEqual(ir.components[0].resolvedProps.columns,compileHeadedTableRequest(request).request.columns);
      await assert.rejects(()=>extractHeadedTableRequest(request,output),/EEXIST/);
      assert.equal(hash(await readFile(join(output,'component_ir.json'))),report.componentIrSha256);
    }
    await assert.rejects(async()=>extractHeadedTableRequest(JSON.parse(await readFile(join(ROOT,'examples/table-source-request.json'),'utf8')),join(ROOT,'examples','bad-headed-output')),/table_output_must_be_new_artifact_directory/);
  }finally{await rm(directory,{recursive:true,force:true});}
});

