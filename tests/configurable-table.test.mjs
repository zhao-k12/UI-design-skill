import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,readFile,writeFile,rm} from 'node:fs/promises';
import {join} from 'node:path';
import {ROOT,hash} from '../component-builder/source-reader/source-lock.mjs';
import {compileTableRequest} from '../component-builder/runtime-renderer/table-request.mjs';
import {extractTableRequest} from '../component-builder/runtime-renderer/configurable-table-extract.mjs';

const request=()=>({version:'0.1.0',containerWidth:720,columns:[{key:'name',title:'姓名',width:240},{key:'email',title:'邮箱',width:480}],records:[{name:'赵六',email:'zhao@example.com'},{name:'钱七',email:'qian@example.com'}]});

test('column and record order produce a stable isolated fixture without mutating input',()=>{
  const input=request(),before=structuredClone(input),first=compileTableRequest(input);
  assert.deepEqual(input,before);assert.deepEqual(compileTableRequest({...input,records:input.records.map(r=>({email:r.email,name:r.name}))}),first);
  assert.equal(first.cases.cases[0].props.showHeader,false);
  const changed=structuredClone(input);changed.columns.reverse();assert.notEqual(compileTableRequest(changed).requestSha256,first.requestSha256);
  changed.records[0].name='孙八';assert.notEqual(compileTableRequest(changed).requestSha256,first.requestSha256);
});

test('incomplete, duplicate, executable and unsupported table inputs are rejected',()=>{
  const changes=[r=>r.columns.push({...r.columns[0]}),r=>delete r.records[0].email,r=>r.records[0].extra='hidden',r=>r.columns[0].render='function',r=>r.columns[0].width++,r=>r.columns[0].width=NaN,r=>r.columns[0].key='constructor',r=>r.records=[],r=>r.records[0].name=123,r=>r.records[0].name='\n',r=>r.style={},r=>r.containerWidth=Infinity,r=>r.columns=[],r=>r.records=Array(51).fill(r.records[0])];
  for(const change of changes){const input=request();change(input);assert.throws(()=>compileTableRequest(input));}
});

test('real official runtime captures two distinct column/data configurations; never admits them',async()=>{
  const directory=await mkdtemp(join(ROOT,'artifacts','table-request-test-'));
  try{
    const input=request(),first=await extractTableRequest(input,join(directory,'first'));
    assert.equal(first.status,'PASS');assert.equal(first.fidelityGate,'NOT_RUN');assert.equal(first.nativeExecution,'NOT_RUN');assert.equal(first.productionAdmission,false);
    assert.equal(hash(await readFile(join(directory,'first/request.json'))),first.requestFileSha256);
    assert.equal(hash(await readFile(join(directory,'first/cases.json'))),first.casesFileSha256);
    const bundle=JSON.parse(await readFile(join(directory,'first/component_ir.json'),'utf8'));
    assert.deepEqual(bundle.components[0].resolvedProps.data,input.records);
    assert.equal(hash(await readFile(join(directory,'first',first.screenshot.path))),first.screenshot.sha256);
    await assert.rejects(()=>extractTableRequest(input,join(directory,'first')),/EEXIST/);
    assert.equal(hash(await readFile(join(directory,'first/component_ir.json'))),first.componentIrSha256);
    const secondInput={version:'0.1.0',containerWidth:960,columns:[{key:'code',title:'编号',width:160},{key:'name',title:'姓名',width:240},{key:'department',title:'部门',width:320},{key:'status',title:'状态',width:240}],records:[{code:'001',name:'张三',department:'研发',status:'启用'},{code:'002',name:'李四',department:'财务',status:'停用'},{code:'003',name:'王五',department:'运营',status:'启用'},{code:'004',name:'赵六',department:'客服',status:'启用'}]};
    const second=await extractTableRequest(secondInput,join(directory,'second'));
    assert.equal(second.status,'PASS');assert.equal(second.observation.rows.length,4);assert.equal(second.observation.rows[0].length,4);
    assert.notEqual(first.componentId,second.componentId);assert.notEqual(first.screenshot.sha256,second.screenshot.sha256);
    const repeated=await extractTableRequest(input,join(directory,'repeat'));
    assert.equal(repeated.screenshot.sha256,first.screenshot.sha256);
    const repeatBundle=JSON.parse(await readFile(join(directory,'repeat/component_ir.json'),'utf8'));
    // Official table.vue generates random(6) column CSS identities. Preserve
    // them in raw evidence; compare geometry/style/content and association
    // after renaming ONLY these generated classes by first occurrence.
    const canonical=value=>{const clone=structuredClone(value),ids=new Map();for(const node of clone.components[0].nodes){
      if(node.attributes.class)node.attributes.class=node.attributes.class.split(' ').map(name=>{
        if(!/^ivu-table-column-[A-Za-z0-9]{6}$/.test(name))return name;
        if(!ids.has(name))ids.set(name,'generated-column-'+ids.size);return ids.get(name);
      }).join(' ');
    }return clone;};
    assert.deepEqual(canonical(repeatBundle),canonical(bundle));
  }finally{await rm(directory,{recursive:true,force:true});}
});

test('protected sources and existing output files cannot be overwritten',async()=>{
  await assert.rejects(()=>extractTableRequest(request(),join(ROOT,'component-builder','unexpected')),/table_output_must/);
  const directory=await mkdtemp(join(ROOT,'artifacts','table-output-test-'));
  try{const file=join(directory,'existing');await writeFile(file,'preserve');await assert.rejects(()=>extractTableRequest(request(),file),/EEXIST/);assert.equal(await readFile(file,'utf8'),'preserve');}
  finally{await rm(directory,{recursive:true,force:true});}
});
