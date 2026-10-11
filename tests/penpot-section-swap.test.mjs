// API doubles verify guards only; they are not native acceptance evidence.
import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFileSync} from 'node:fs';
const code=['section_patch.js','section_swap.js'].map(n=>readFileSync(new URL(`../adapters/penpot/${n}`,import.meta.url),'utf8')).join('\n');
const {swap,snapshot}=vm.runInNewContext(`${code};({swap:swapPenpotSectionComponent,snapshot:snapshotPenpotPatchRoot})`);
function fixture(){
  const shape=id=>({id,type:'board',name:id,x:0,y:0,width:240,height:32,children:[],
    isComponentCopyInstance(){return id==='copy';},isComponentMainInstance(){return id==='main';},component(){return {id:this.ref};}});
  const root=shape('root'),section=shape('section'),copy=shape('copy'),old=shape('old'),other=shape('other'),main=shape('main');
  root.parent={id:'page-root'};root.children=[section,other];section.parent=root;section.children=[copy];copy.parent=section;copy.children=[old];old.parent=copy;copy.ref='old-component';main.ref='new-component';
  const all=new Map([root,section,copy,old,other].map(n=>[n.id,n]));
  let calls=0;
  copy.swapComponent=c=>{calls++;copy.ref=c.id;const child=shape('new');child.parent=copy;copy.children=[child];all.delete('old');all.set('new',child);};
  const api={currentFile:{id:'file',revn:1},currentPage:{id:'page',root:{id:'page-root'},getShapeById:id=>all.get(id)},
    library:{local:{components:[{id:'new-component',mainInstance:()=>main}]}},async waitForLayoutUpdate(){this.currentFile.revn++;}};
  const execution={status:'EXECUTED',fileReference:'file',pageReference:'page',rootReference:'root',uiIrSha256:'old',createdNodeIds:[...all.keys()],nodeMap:{page:'root',input:'copy'}};
  const target={id:'input',type:'ComponentInstance',componentReference:'new-component',layout:{width:{mode:'fixed',value:240},height:{mode:'fixed',value:32}}};
  const payload={fileReference:'file',uiIrSha256:'new',page:{id:'page',type:'Page',children:[{id:'filters',type:'Section',children:[target]}]}};
  const request={baseUiIrSha256:'old',updatedUiIrSha256:'new',uiIrId:'input',expectedComponentReference:'old-component'};
  const capture={status:'CAPTURED',fileReference:'file',pageReference:'page',rootReference:'root',fileRevision:1,nodes:snapshot(root)};
  return {api,execution,payload,request,capture,copy,main,other,target,calls:()=>calls};
}
test('public component swap preserves copy root and reports changed descendants',async()=>{
  const f=fixture(),r=await swap(f.api,f.payload,f.execution,f.request,f.capture);
  assert.equal(r.status,'SWAPPED');assert.equal(r.swappedCopyId,'copy');
  assert.deepEqual(Array.from(r.createdNodeIds),['new']);assert.deepEqual(Array.from(r.removedNodeIds),['old']);
  assert.deepEqual(Array.from(r.changedSections),['filters']);assert.equal(r.finalAcceptance,'NOT_RUN');
});
test('context, checkpoint, ownership, reference and source-size failures precede all writes',async()=>{
  for(const alter of [f=>f.api.currentFile.id='foreign',f=>f.capture.fileRevision=0,f=>f.capture.nodes[0].width=1,
    f=>f.execution.createdNodeIds=[],f=>f.request.expectedComponentReference='wrong',f=>f.main.width=241,
    f=>f.target.layout.width.mode='fill',f=>f.copy.swapComponent=undefined,f=>f.target.nativeContent=[{}]]){
    const f=fixture();alter(f);await assert.rejects(swap(f.api,f.payload,f.execution,f.request,f.capture));assert.equal(f.calls(),0);
  }
});
test('post-write unrelated mutation explicitly requires recovery',async()=>{
  const f=fixture();f.api.waitForLayoutUpdate=async()=>{f.other.width++;};
  const r=await swap(f.api,f.payload,f.execution,f.request,f.capture);
  assert.equal(r.status,'FAIL');assert.equal(r.nativeExecution,'PARTIAL');assert.equal(r.recoveryRequired,true);
  assert.match(r.issues[0].detail,/unrelated_nodes/);assert.equal(f.calls(),1);
});
test('post-write broken link or moved root never passes',async()=>{
  for(const alter of [f=>f.copy.ref='broken',f=>f.copy.x=1,f=>f.copy.name='changed']){
    const f=fixture();f.api.waitForLayoutUpdate=async()=>alter(f);
    const r=await swap(f.api,f.payload,f.execution,f.request,f.capture);assert.equal(r.status,'FAIL');assert.equal(r.recoveryRequired,true);
  }
});
test('source master mutation rejects success',async()=>{
  const f=fixture();f.api.waitForLayoutUpdate=async()=>{f.main.name='mutated';};
  const r=await swap(f.api,f.payload,f.execution,f.request,f.capture);
  assert.equal(r.status,'FAIL');assert.match(r.issues[0].detail,/source_master/);
});
test('SDK exception after mutation keeps snapshots and a recovery flag',async()=>{
  const f=fixture();f.copy.swapComponent=()=>{f.copy.ref='new-component';throw new Error('SDK interrupted');};
  const r=await swap(f.api,f.payload,f.execution,f.request,f.capture);
  assert.equal(r.status,'FAIL');assert.equal(r.recoveryRequired,true);
  assert.ok(r.before.length);assert.ok(r.after.length);assert.match(r.issues[0].detail,/SDK interrupted/);
});
