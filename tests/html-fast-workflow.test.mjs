import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdir,writeFile,readFile} from 'node:fs/promises';
import {join,resolve} from 'node:path';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
const root=resolve(import.meta.dirname,'..');
const dir=join(root,'artifacts','task-145','smoke-'+Date.now());
const python=join(root,'.venv/Scripts/python.exe');
const command=(mode,input)=>execFileSync(python,['-X','utf8','scripts/html_fast_workflow.py',mode,'--task-dir',dir,...(input?['--input',input]:[])],{cwd:root,stdio:'pipe'});
test('compact input renders and finalizes with timing, intrinsic sizing, and stale-review rejection',async()=>{
 await mkdir(dir,{recursive:true});const source=join(dir,'fixture.txt');await writeFile(source,'development fixture only');
 const sourceSha256=createHash('sha256').update(await readFile(source)).digest('hex');
 const traits={leading:'none',trailing:'none',surface:'plain',shape:'rect',role:'record'};
 const job={source:'fixture.txt',viewport:{width:1440,height:1000},
   content:{sourceSha256,title:'Compact workflow fixture',root:{id:'records',kind:'component',component:'Table',sourceGroups:['rows'],
     props:{columns:[{title:'名称',key:'name',width:40}],data:[{name:'A'},{name:'B'}]}}},
   observation:{sourceSha256,groups:[{id:'rows',prefix:'row-',count:2,region:'table',traits,decision:'include',treeRef:'records',sourceEvidence:'两条记录A/B'}]},
   scan:{sourceSha256,groups:[{id:'rows',prefix:'row-',count:2,region:'table',traits,visual:'独立开发样例计数为2，内容A/B'}]}};
 const input=join(dir,'job.json');await writeFile(input,JSON.stringify(job));command('start');
 command('render',input);const active=JSON.parse(await readFile(join(dir,'active-run.json')));
 const qa=JSON.parse(await readFile(join(active.runDir,'html/qa.json')));
 assert.equal(qa.status,'PASS');assert.equal(qa.stages.delivery.tableRows,2);
 assert.ok(qa.layoutSizing[0].columns[0].measuredMinimum>40);
 const review={runId:active.runId,sourceSha256,reviewMode:'batched-v2',
   stageChecks:{tree:'PASS',skeleton:'PASS',component:'PASS',delivery:'PASS'},
   variantRules:[{id:'table',component:'Table',variantReason:'Developer fixture native cells',officialEvidence:'node_modules/view-ui-plus/src/components/table/table.vue'}],
   groups:[{sourceGroups:['rows'],status:'PASS',variantRef:'table',renderedTraits:traits,renderedEvidence:'Developer fixture screenshots and row metrics checked; A and B present.'}],relationChecks:[]};
 const reviewFile=join(dir,'review.json');await writeFile(reviewFile,JSON.stringify(review));command('finalize',reviewFile);
 const receipt=JSON.parse(await readFile(join(dir,'delivery-receipt.json')));
 assert.equal(receipt.status,'PASS');assert.equal(receipt.timing.scope,'request-start');
 assert.ok(receipt.timing.elapsedSeconds>=receipt.timing.runs[0].machineSeconds);
 assert.ok(!(await readFile(join(dir,'page.html'),'utf8')).includes('<script'));
 review.runId='previous-run';await writeFile(reviewFile,JSON.stringify(review));
 assert.throws(()=>command('finalize',reviewFile),/Command failed/);
 review.runId=active.runId;await writeFile(reviewFile,JSON.stringify(review));
 await writeFile(join(active.runDir,'html/delivery.png'),'changed screenshot');
 assert.throws(()=>command('finalize',reviewFile),/Command failed/);
});
