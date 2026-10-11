// Public API doubles are unit checks, never native acceptance evidence.
import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFileSync} from 'node:fs';
const code=['runtime.js','content_runtime.js','section_patch.js'].map(n=>readFileSync(new URL(`../adapters/penpot/${n}`,import.meta.url),'utf8')).join('\n');
const {patch,apply}=vm.runInNewContext(`${code};({patch:patchPenpotSectionContent,apply:applyPenpotNativeContent})`);
function fixture(){
  const shape=(id,type='board')=>({id,type,name:id,x:0,y:0,width:100,height:32,children:[],
    isComponentCopyInstance(){return id==='copy';},isComponentMainInstance(){return false;},component(){return {id:'master'};}});
  const root=shape('root'),section=shape('section'),copy=shape('copy'),text=shape('text','text'),other=shape('other');
  root.parent={id:'page-root'};root.children=[section,other];section.parent=root;section.children=[copy];copy.parent=section;copy.children=[text];text.parent=copy;
  Object.assign(text,{name:'declared-label',characters:'before',fontSize:'14',width:40,height:20,x:10,y:5});
  const byId=new Map([root,section,copy,text,other].map(n=>[n.id,n]));
  const api={currentFile:{id:'file',revn:1},currentPage:{id:'page',root:{id:'page-root'},getShapeById:id=>byId.get(id)},async waitForLayoutUpdate(){this.currentFile.revn++;}};
  const execution={status:'EXECUTED',fileReference:'file',pageReference:'page',rootReference:'root',uiIrSha256:'old',createdNodeIds:['root','section','copy','text','other'],nodeMap:{page:'root',button:'copy'}};
  const mapping={name:'declared-label',originalText:'before',text:'after',style:{fontSize:'14'}};
  const payload={fileReference:'file',uiIrSha256:'new',page:{id:'page',type:'Page',children:[{id:'query',type:'Section',children:[{id:'button',type:'ComponentInstance',componentReference:'master',nativeContent:[mapping]}]}]}};
  const request={baseUiIrSha256:'old',updatedUiIrSha256:'new',expectedRevision:1,uiIrIds:['button'],expectedCharacters:{button:{'declared-label':'before'}}};
  return {api,execution,payload,request,root,section,copy,text,other,mapping};
}
test('patch only genuine linked text and keep identities/topology',async()=>{
  const f=fixture(),r=await patch(f.api,f.payload,f.execution,f.request);
  assert.equal(r.status,'PATCHED');assert.equal(f.text.characters,'after');
  assert.deepEqual(Array.from(r.changedSections),['query']);assert.equal(r.createdNodeIds.length,0);
  assert.equal(r.removedNodeIds.length,0);assert.equal(r.finalAcceptance,'NOT_RUN');
});
test('wrong file/page/revision/reference/ownership reject before text mutation',async()=>{
  for(const alter of [f=>f.api.currentFile.id='other',f=>f.api.currentPage.id='other',f=>f.request.expectedRevision=2,
    f=>f.execution.createdNodeIds=[],f=>f.payload.page.children[0].children[0].componentReference='other',
    f=>f.request.expectedCharacters.button['declared-label']='stale']){
    const f=fixture();alter(f);await assert.rejects(patch(f.api,f.payload,f.execution,f.request));assert.equal(f.text.characters,'before');
  }
});
test('masters, duplicate target names and wrong font never receive overrides',async()=>{
  const f=fixture();f.copy.isComponentMainInstance=()=>true;
  await assert.rejects(apply(f.api,f.copy,[f.mapping]),/linked_copy/);
  const g=fixture();g.text.fontSize='15';await assert.rejects(apply(g.api,g.copy,[g.mapping]),/style_changed/);
  const h=fixture();h.copy.children.push({...h.text,id:'duplicate'});await assert.rejects(apply(h.api,h.copy,[h.mapping]),/invalid_content_target/);
});
test('overflow restores original text and creates no nodes',async()=>{
  const f=fixture();f.text.width=200;await assert.rejects(apply(f.api,f.copy,[f.mapping]),/overflow/);assert.equal(f.text.characters,'before');
});
test('unrelated mutation detected and target text rolled back',async()=>{
  const f=fixture();f.api.waitForLayoutUpdate=async()=>{f.other.width=101;};
  await assert.rejects(patch(f.api,f.payload,f.execution,f.request),/unrelated_nodes/);assert.equal(f.text.characters,'before');
});
test('content entry refuses foreign file before reading any master',async()=>{
  const entry=vm.runInNewContext(`${code};executePenpotContentAdapter`);
  const api={currentFile:{id:'foreign'},get library(){assert.fail('foreign library read');}};
  await assert.rejects(entry(api,{platform:'penpot',fileReference:'expected'}),/file_reference_mismatch/);
});
test('content entry preflights stale master before native page execution',async()=>{
  let executed=false;
  const context={mark:()=>{executed=true;}};
  const entry=vm.runInNewContext(`${code};executePenpotAdapter=async()=>{mark();return {status:'EXECUTED'};};executePenpotContentAdapter`,context);
  const f=fixture();f.api.library={local:{components:[{id:'master',mainInstance:()=>({isComponentMainInstance:()=>true,children:[{...f.text,characters:'changed master'}]})}]}};
  f.payload.platform='penpot';
  await assert.rejects(entry(f.api,f.payload),/content_master_changed/);assert.equal(executed,false);
});
