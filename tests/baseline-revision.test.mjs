import {test} from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFile} from 'node:fs/promises';
const context=vm.createContext({});vm.runInContext(await readFile(new URL('../adapters/figma/baseline_revision.js',import.meta.url),'utf8'),context);
function fixture(){
  const events=[],page={id:'page',type:'PAGE'};
  const root={id:'root',type:'COMPONENT',parent:page,width:60,height:32,absoluteTransform:[[1,0,80],[0,1,80]],children:[],appendChild(node){this.children.push(node);node.parent=this;}};
  const text={id:'text',type:'TEXT',parent:root,x:16,y:5.5,width:28,height:21,characters:'查询',fontName:{family:'Fixture',style:'Regular'},fontWeight:400,fontSize:14,lineHeight:{unit:'PIXELS',value:21},absoluteTransform:[[1,0,96],[0,1,85.5]],getStyledTextSegments(){return [{fontName:this.fontName}]}};root.children=[text];
  const slot={id:'slot',x:16,y:5.5,resize(w,h){this.width=w;this.height=h},appendChild(node){root.children=root.children.filter(child=>child!==node);node.parent=this;}};
  const api={editorType:'figma',fileKey:'fixture',getNodeByIdAsync:async id=>id==='page'?page:id==='root'?root:text,setCurrentPageAsync:async()=>{},loadFontAsync:async()=>events.push('font'),createAutoLayout:()=>{events.push('create');return slot}};
  const request={fileReference:'fixture',pageReference:'page',componentReference:'root',textReference:'text',evidenceHashes:Object.fromEntries(['official-runtime-baseline-evidence.json','native-text-outline-capture.json','font-file-identity.json'].map(name=>[name,'a'.repeat(64)])),source:{rootBounds:{width:60,height:32},spanBounds:{x:16,y:5.5,width:28,height:21},baselineComponentY:20.5,nativeSvgBaseline:16,text:'查询',fontName:text.fontName,fontWeight:400,fontSize:14,lineHeight:21}};
  return {api,request,root,text,slot,events};
}
test('preserves source span geometry and applies measured glyph baseline offset after font load',async()=>{
  const f=fixture(),r=await context.reviseButtonBaseline(f.api,f.request);
  assert.equal(r.status,'PASS');assert.equal(f.text.y,-1);assert.equal(r.nativeObservation.baselineComponentY,20.5);
  assert.deepEqual(f.events,['font','create']);assert.equal(r.createdNodeIds.length,1);assert.equal(r.mutatedNodeIds.length,2);assert.equal(r.admissionEligible,false);
});
test('source evidence, current font and existing inventory are guarded before creation',async()=>{
  const f=fixture();f.text.fontSize=15;
  assert.equal((await context.reviseButtonBaseline(f.api,f.request)).status,'FAIL');assert.equal(f.events.length,0);
  f.text.fontSize=14;f.request.evidenceHashes={};
  assert.equal((await context.reviseButtonBaseline(f.api,f.request)).status,'FAIL');assert.equal(f.events.length,0);
});
test('post-write mismatch retains precise recovery IDs',async()=>{
  const f=fixture();f.slot.x=17;
  const r=await context.reviseButtonBaseline(f.api,f.request);
  assert.equal(r.status,'FAIL');assert.equal(r.createdNodeIds[0],'slot');assert.ok(r.mutatedNodeIds.includes('text'));
});
