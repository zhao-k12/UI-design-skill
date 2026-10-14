// Local API doubles test failure semantics. Never native execution evidence.
import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFileSync} from 'node:fs';

const runtime = readFileSync(new URL('../adapters/penpot/runtime.js', import.meta.url), 'utf8');
const execute = vm.runInNewContext(`${runtime}; executePenpotAdapter`);
const layout = {direction:'vertical',gap:0,padding:{top:0,right:0,bottom:0,left:0},alignment:{main:'start',cross:'start'},
  width:{mode:'fixed',value:100},height:{mode:'hug'}};
const payload = () => ({platform:'penpot',fileReference:'test-only-file',documentId:'test-only',page:{id:'page',name:'page',type:'Page',layout,style:{},children:[]}});
function host() {
  let writes = 0;
  return {currentFile:{id:'test-only-file',pages:[]},fonts:{findById:() => null},library:{local:{components:[]}},
    createPage() { writes++; return {id:'test-only-page',root:{children:[]}}; },
    async openPage() {},createBoard() { throw new Error('deliberate local test failure'); },
    writes:() => writes};
}
test('wrong target stops before writing', async () => {
  const api = host(), p = payload(); p.fileReference = 'other-file';
  await assert.rejects(execute(api,p), /file_reference_mismatch/); assert.equal(api.writes(),0);
});
test('unavailable exact font stops before page creation', async () => {
  const api = host(), p = payload(); p.page.children = [{id:'text',type:'Text',fontBinding:{fontId:'missing'},layout,style:{}}];
  await assert.rejects(execute(api,p), /missing_exact_font/); assert.equal(api.writes(),0);
});
test('missing component stops before page creation', async () => {
  const api = host(), p = payload(); p.page.children = [{id:'button',type:'ComponentInstance',componentReference:'missing',layout,style:{}}];
  await assert.rejects(execute(api,p), /missing_native_component/); assert.equal(api.writes(),0);
});
test('accepted main-instance reference resolves to its exact local component', async () => {
  const api = host(), p = payload();
  const main = {id:'main-id',width:100,height:10,children:[],isComponentMainInstance:()=>true,isComponentRoot:()=>true};
  api.library.local.components = [{id:'library-id',mainInstance:()=>main}];
  p.page.children = [{id:'native',type:'ComponentInstance',componentReference:'main-id',
    layout:{...layout,height:{mode:'fixed',value:10}},style:{}}];
  const result = await execute(api,p);
  assert.equal(result.status,'FAIL');
  assert.match(result.issues[0].detail,/deliberate local test failure/);
  assert.equal(api.writes(),1);
});
test('ambiguous main-instance reference stops before writing', async () => {
  const api = host(), p = payload();
  const main = {id:'same-main',width:100,height:10,isComponentMainInstance:()=>true,isComponentRoot:()=>true};
  api.library.local.components = [{id:'one',mainInstance:()=>main},{id:'two',mainInstance:()=>main}];
  p.page.children = [{id:'native',type:'ComponentInstance',componentReference:'same-main',layout,style:{}}];
  await assert.rejects(execute(api,p),/missing_native_component/);
  assert.equal(api.writes(),0);
});
test('duplicate page needs explicit ledger and creates nothing', async () => {
  const api = host(); api.currentFile.pages.push({id:'existing',name:'test-only/page'});
  await assert.rejects(execute(api,payload()), /existing_page_requires_ledger/); assert.equal(api.writes(),0);
});
test('partial failure returns created page ledger without acceptance', async () => {
  const api = host(), result = await execute(api,payload());
  assert.equal(result.status,'FAIL'); assert.equal(result.nativeExecution,'PARTIAL'); assert.equal(result.finalAcceptance,'NOT_RUN');
  assert.deepEqual(Array.from(result.createdNodeIds),['test-only-page']); assert.equal(api.writes(),1);
});

test('container translation sets native flex and literal colors, without claiming acceptance', async () => {
  const api = host(), p = payload(); let count = 0;
  api.createBoard = () => ({id:`test-board-${count++}`,width:100,height:10,children:[],layoutChild:{},
    addFlexLayout() { return this.flex = {}; }, resize(w,h) { this.width=w; this.height=h; },
    appendChild(n) { this.children.push(n); n.parent=this; }});
  let page;
  api.createPage = () => page = {id:'test-only-page',root:{children:[],appendChild(n) { this.children.push(n); n.parent=this; }}};
  p.page.style = {fill:'#ffffff80'};
  p.page.children = [{id:'grid',name:'grid',type:'Grid',layout:{...layout,width:{mode:'fixed',value:100},gap:16},style:{},
    gridCells:[{id:'cell',row:0,width:42}],children:[{id:'cell',name:'cell',type:'Column',layout,style:{},children:[]}]}];
  const result = await execute(api,p);
  assert.equal(result.status,'EXECUTED'); assert.equal(result.finalAcceptance,'NOT_RUN');
  const root = page.root.children[0], grid = root.children[0];
  assert.equal(root.clipContent,false); assert.equal(root.flex.horizontalSizing,'fix');
  assert.equal(root.flex.verticalSizing,'auto'); assert.equal(root.fills[0].fillOpacity,128/255);
  assert.equal(grid.flex.dir,'column'); assert.equal(grid.children[0].flex.dir,'row');
  assert.equal(grid.children[0].children[0].width,42); assert.equal(result.helperNodeIds.length,2);
});

test('completed writes do not depend on Penpot layout waiter', async () => {
  const api = host(), p = payload(); let calls = 0;
  api.createBoard = () => ({id:'test-board',width:100,height:10,children:[],layoutChild:{},
    addFlexLayout() { return this.flex = {}; }, resize(w,h) { this.width=w; this.height=h; },
    appendChild(n) { this.children.push(n); n.parent=this; }});
  api.createPage = () => ({id:'test-only-page',root:{children:[],appendChild(n) { this.children.push(n); n.parent=this; }}});
  api.waitForLayoutUpdate = async () => { calls++; throw new Error('waitForLayoutUpdate timeout'); };
  const result = await execute(api,p);
  assert.equal(result.status,'EXECUTED'); assert.equal(result.finalAcceptance,'NOT_RUN');
  assert.equal(calls,0); assert.equal(result.createdNodeIds.length,2);
});

const defaults=vm.runInNewContext(readFileSync(new URL('../adapters/penpot/page_recovery.js',import.meta.url),'utf8')+';restorePenpotPageDefaults');
const resetCopies=vm.runInNewContext(readFileSync(new URL('../adapters/penpot/page_recovery.js',import.meta.url),'utf8')+';resetPenpotIconCopies');
test('linked icon reset validates all references before resetting any copy',async()=>{
  let resets=0;
  const copy={id:'copy',x:1,y:2,width:24,height:24,children:[],layoutChild:{},parent:{id:'root'},isComponentCopyInstance:()=>true,component:()=>({id:'component'}),resetOverrides:()=>resets++};
  const api={currentFile:{id:'file'},currentPage:{id:'page',getShapeById:()=>copy},waitForLayoutUpdate:async()=>{}};
  const payload={fileReference:'file',page:{children:[{id:'icon',name:'icon',type:'IconInstance',componentReference:'foreign'}]}};
  const execution={status:'EXECUTED',fileReference:'file',pageReference:'page',rootReference:'root',nodeMap:{icon:'copy'}};
  await assert.rejects(resetCopies(api,payload,execution),/identity_mismatch/);assert.equal(resets,0);
  payload.page.children[0].componentReference='component';assert.equal((await resetCopies(api,payload,execution)).status,'LINKED_ICON_COPIES_RESET');assert.equal(resets,1);assert.equal(copy.layoutChild.horizontalSizing,'fix');
});
const instanceCapture=vm.runInNewContext(readFileSync(new URL('../adapters/penpot/page_instances.js',import.meta.url),'utf8')+';capturePenpotPageInstances',{btoa:s=>Buffer.from(s,'binary').toString('base64')});
test('instance capture refuses wrong contexts and preserves partial PNG failures',async()=>{
  const component={id:'component'},main={id:'main',children:[],isComponentMainInstance:()=>true,isComponentRoot:()=>true};component.mainInstance=()=>main;
  const copy={id:'copy',parent:{id:'root'},children:[],isComponentCopyInstance:()=>true,isComponentRoot:()=>true,component:()=>component,export:async options=>{if(options.type==='png')throw Error('test-only-timeout');return new Uint8Array([1]);}};
  const api={currentFile:{id:'file',revn:1},currentPage:{id:'page',getShapeById:()=>copy},library:{local:{components:[component]}}};
  const payload={fileReference:'file',page:{id:'page',children:[{id:'icon',componentReference:'component'}]}};
  const execution={status:'EXECUTED',pageReference:'page',rootReference:'root',nodeMap:{icon:'copy'}};
  const result=await instanceCapture(api,payload,execution);assert.equal(result.status,'PARTIAL');assert.equal(result.instances[0].nativeSvgBase64,'AQ==');assert.equal(result.instances[0].exportIssues[0].format,'png');assert.equal(result.mutatedNodeIds.length,0);
  copy.export=async options=>{assert.equal(options.type,'png');return new Uint8Array([2]);};
  const resumed=await instanceCapture(api,payload,execution,result);assert.equal(resumed.status,'CAPTURED');assert.equal(resumed.instances[0].nativeSvgBase64,'AQ==');assert.equal(resumed.instances[0].reusedFormats[0],'svg');
  await assert.rejects(instanceCapture(api,payload,execution,{...result,fileRevision:2}),/previous_context_mismatch/);
  copy.width=11;await assert.rejects(instanceCapture(api,payload,execution,result),/previous_geometry_mismatch/);delete copy.width;
  api.currentPage.id='foreign';await assert.rejects(instanceCapture(api,payload,execution),/context_mismatch/);
});
test('explicit defaults repair only owned output nodes after all identity checks',async()=>{
  const root={id:'root',name:'UI-IR / doc / page',opacity:null,parent:{id:'zero'},isComponentCopyInstance:()=>false,isComponentMainInstance:()=>false};
  const text={id:'text',name:'text',opacity:null,parent:root,isComponentCopyInstance:()=>false,isComponentMainInstance:()=>false};
  const api={currentFile:{id:'file'},currentPage:{id:'page',root:{id:'zero'},getShapeById:id=>({root,text})[id]},waitForLayoutUpdate:async()=>{}};
  const payload={fileReference:'file',documentId:'doc',uiIrSha256:'hash',page:{id:'page',type:'Page',style:{},children:[{id:'text',name:'text',style:{}}]}};
  const ledger={status:'EXECUTED',fileReference:'file',pageReference:'page',rootReference:'root',uiIrSha256:'hash',createdNodeIds:['root','text'],nodeMap:{page:'root',text:'text'},helperNodeIds:[]};
  text.opacity=.5;await assert.rejects(defaults(api,payload,ledger),/identity_mismatch/);assert.equal(root.opacity,null);
  text.opacity=null;const result=await defaults(api,payload,ledger);assert.equal(result.status,'SOURCE_DEFAULTS_RESTORED');assert.equal(root.opacity,1);assert.equal(text.opacity,1);assert.equal(result.createdNodeIds.length,0);
  api.currentPage.id='foreign';await assert.rejects(defaults(api,payload,ledger),/context_mismatch/);
});

const captureSource = readFileSync(new URL('../adapters/penpot/capture.js', import.meta.url), 'utf8');
const capture = vm.runInNewContext(`${captureSource}; capturePenpotOutput`);
test('capture refuses the wrong page before exporting', async () => {
  await assert.rejects(capture({currentFile:{id:'file'},currentPage:{id:'wrong'}},
    {fileReference:'file',pageReference:'expected'}), /capture_context_mismatch/);
});
test('capture refuses oversized output before exporting', async () => {
  const root = {parent:{id:'page-root'},width:4097,height:1,export() { assert.fail('must not export'); }};
  const api = {currentFile:{id:'file'},currentPage:{id:'page',root:{id:'page-root'},getShapeById:()=>root}};
  await assert.rejects(capture(api,{fileReference:'file',pageReference:'page',rootReference:'root'}), /capture_geometry_out_of_bounds/);
});
test('capture refuses a mapped node outside the output root', async () => {
  const root = {id:'root',parent:{id:'page-root'},width:100,height:100,export() { assert.fail('must not export'); }};
  const stray = {id:'stray',parent:null};
  const api = {currentFile:{id:'file'},currentPage:{id:'page',root:{id:'page-root'},getShapeById:id=>id==='root'?root:stray}};
  await assert.rejects(capture(api,{fileReference:'file',pageReference:'page',rootReference:'root',nodeMap:{title:'stray'}}), /capture_node_outside_root/);
});
test('capture discards an export when the document revision changes', async () => {
  const api = {currentFile:{id:'file',revn:1},currentPage:{id:'page',root:{id:'page-root'}}};
  const root = {id:'root',parent:{id:'page-root'},type:'board',width:100,height:100,children:[],
    isComponentCopyInstance:()=>false, async export() { api.currentFile.revn=2; return new Uint8Array([1]); }};
  api.currentPage.getShapeById = () => root;
  await assert.rejects(capture(api,{fileReference:'file',pageReference:'page',rootReference:'root',nodeMap:{page:'root'}}), /capture_document_changed/);
});
test('capture refuses duplicate mapped IDs without exporting', async () => {
  const root={id:'root',parent:{id:'page-root'},width:100,height:100,children:[],export() { assert.fail('must not export'); }};
  const api={currentFile:{id:'file'},currentPage:{id:'page',root:{id:'page-root'},getShapeById:()=>root}};
  await assert.rejects(capture(api,{fileReference:'file',pageReference:'page',rootReference:'root',nodeMap:{a:'root',b:'root'}}), /capture_invalid_node_map/);
});

const recoverySource=readFileSync(new URL('../adapters/penpot/recovery.js',import.meta.url),'utf8');
const recover=vm.runInNewContext(`${recoverySource}; inspectPenpotRecovery`);
test('recovery inspects exact surviving IDs and leaves all nodes untouched', () => {
  const node={id:'node',type:'board',name:'partial',parent:{id:'page-root'},children:[{id:'user-added'}]};
  const api={currentFile:{id:'file'},currentPage:{id:'page',name:'partial-page',getShapeById:id=>id==='node'?node:null}};
  const result=recover(api,{status:'FAIL',nativeExecution:'PARTIAL',scope:'penpot_partial_translation',fileReference:'file',pageReference:'page',
    createdNodeIds:['page','node','missing'],mutatedNodeIds:[]});
  assert.equal(result.status,'REVIEW'); assert.equal(result.automaticResumeAllowed,false);
  assert.deepEqual(Array.from(result.missing),['missing']); assert.equal(result.unexpectedChildren[0].nodeId,'user-added');
  assert.equal(result.createdNodeIds.length,0); assert.equal(result.mutatedNodeIds.length,0); assert.equal(node.children[0].id,'user-added');
});
test('recovery rejects foreign contexts and duplicate ledgers', () => {
  const api={currentFile:{id:'file'},currentPage:{id:'page'}};
  const ledger={status:'FAIL',nativeExecution:'PARTIAL',scope:'penpot_partial_translation',fileReference:'foreign',pageReference:'page',createdNodeIds:[],mutatedNodeIds:[]};
  assert.throws(()=>recover(api,ledger),/recovery_context_mismatch/);
  ledger.fileReference='file'; ledger.createdNodeIds=['node','node'];
  assert.throws(()=>recover(api,ledger),/invalid_creation_ledger/);
});
