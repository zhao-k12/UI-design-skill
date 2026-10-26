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
   content:{sourceSha256,title:'Full Tree workflow fixture',root:{id:'layout',kind:'container',layout:{direction:'vertical'},children:[{id:'records',kind:'component',component:'Table',sourceGroups:['rows'],
     props:{columns:[{title:'名称',key:'name',width:40}],data:[{name:'A'},{name:'B'}]}},{id:'unchanged',kind:'component',component:'Button',children:[{id:'action-label',kind:'text',value:'固定操作'}],sourceGroups:['action']}] }},
   observation:{sourceSha256,groups:[{id:'rows',prefix:'row-',count:2,region:'table',traits,decision:'include',treeRef:'records',sourceEvidence:'两条记录A/B'},
     {id:'action',ids:['action'],region:'footer',traits,decision:'include',treeRef:'unchanged',sourceEvidence:'固定操作'}]},
   scan:{sourceSha256,groups:[{id:'rows',prefix:'row-',count:2,region:'table',traits,visual:'独立开发样例计数为2，内容A/B'},
     {id:'action',ids:['action'],region:'footer',traits,visual:'固定操作按钮'}]}};
 const input=join(dir,'job.json');await writeFile(input,JSON.stringify(job));command('start');
 command('render',input);const active=JSON.parse(await readFile(join(dir,'active-run.json')));
 const qa=JSON.parse(await readFile(join(active.runDir,'html/qa.json')));
 assert.equal(qa.status,'PASS');assert.equal(qa.stages.delivery.tableRows,2);
 assert.ok(qa.reviewSheetSha256);assert.ok((await readFile(join(active.runDir,'html/review-sheet.png'))).length>1000);
 assert.ok(qa.layoutSizing[0].columns[0].measuredMinimum>40);
 const review={runId:active.runId,sourceSha256,reviewMode:'batched-v2',
   stageChecks:{tree:'PASS',skeleton:'PASS',component:'PASS',delivery:'PASS'},
   variantRules:[{id:'table',component:'Table',variantReason:'Developer fixture native cells',officialEvidence:'node_modules/view-ui-plus/src/components/table/table.vue'},
     {id:'button',component:'Button',variantReason:'Developer fixture official action',officialEvidence:'node_modules/view-ui-plus/src/components/button/button.vue'}],
   groups:[{sourceGroups:['rows'],status:'PASS',variantRef:'table',renderedTraits:traits,renderedEvidence:'Developer fixture screenshots and row metrics checked; A and B present.'},
     {sourceGroups:['action'],status:'PASS',variantRef:'button',renderedTraits:traits,renderedEvidence:'Developer fixture fixed action checked.'}],relationChecks:[]};
 const reviewFile=join(dir,'review.json');await writeFile(reviewFile,JSON.stringify(review));command('finalize',reviewFile);
 const receipt=JSON.parse(await readFile(join(dir,'delivery-receipt.json')));
 assert.equal(receipt.status,'PASS');assert.equal(receipt.timing.scope,'request-start');
 assert.ok(receipt.timing.elapsedSeconds>=receipt.timing.runs[0].machineSeconds);
 assert.ok(!(await readFile(join(dir,'page.html'),'utf8')).includes('<script'));
 // Configuration-only revision keeps all source facts and reuses sealed, unchanged groups.
 const patch=join(dir,'patch.json');await writeFile(patch,JSON.stringify({content:{title:'Renamed fixture'}}));command('revise',patch);
 const revised=JSON.parse(await readFile(join(dir,'active-run.json')));
 const plan=JSON.parse(await readFile(join(revised.runDir,'review-plan.json')));
 assert.deepEqual(plan.reusableGroups,['rows','action']);
 const delta={reviewMode:'delta-v1',runId:revised.runId,sourceSha256,checkedStages:['tree','skeleton','component','delivery'],confirmedGroups:[],issues:[],relationChecks:[]};
 const deltaFile=join(dir,'delta.json');await writeFile(deltaFile,JSON.stringify(delta));
 const sealedFile=join(active.runDir,'visual-review.json'),sealedBytes=await readFile(sealedFile);
 await writeFile(sealedFile,Buffer.concat([sealedBytes,Buffer.from(' ')]));assert.throws(()=>command('finalize',deltaFile));
 await writeFile(sealedFile,sealedBytes);command('finalize',deltaFile);
 const revisedJob=JSON.parse(await readFile(join(revised.runDir,'job.json')));
 revisedJob.content.root.children[0].props.data[0].name='C';
 await writeFile(patch,JSON.stringify({content:{root:{children:revisedJob.content.root.children}}}));command('revise',patch);
 const changed=JSON.parse(await readFile(join(dir,'active-run.json')));
 assert.deepEqual(JSON.parse(await readFile(join(changed.runDir,'review-plan.json'))).reusableGroups,['action']);
 delta.runId=changed.runId;await writeFile(deltaFile,JSON.stringify(delta));assert.throws(()=>command('finalize',deltaFile));
 delta.confirmedGroups=['rows'];await writeFile(deltaFile,JSON.stringify(delta));command('finalize',deltaFile);
 // A viewport change invalidates geometric context even when row data is identical.
 await writeFile(patch,JSON.stringify({viewport:{width:1600}}));command('revise',patch);
 const shifted=JSON.parse(await readFile(join(dir,'active-run.json')));
 assert.deepEqual(JSON.parse(await readFile(join(shifted.runDir,'review-plan.json'))).reusableGroups,[]);
 // Restore the original active receipt to exercise original stale/tampered-image gates.
 await writeFile(join(dir,'active-run.json'),JSON.stringify(active));
 review.runId='previous-run';await writeFile(reviewFile,JSON.stringify(review));
 assert.throws(()=>command('finalize',reviewFile),/Command failed/);
 review.runId=active.runId;await writeFile(reviewFile,JSON.stringify(review));
 await writeFile(join(active.runDir,'html/delivery.png'),'changed screenshot');
 assert.throws(()=>command('finalize',reviewFile),/Command failed/);
});
