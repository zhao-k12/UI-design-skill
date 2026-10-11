import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFile} from 'node:fs/promises';
const context=vm.createContext({});vm.runInContext(await readFile(new URL('../adapters/figma/blend_mode_probe.js',import.meta.url),'utf8'),context);
function fixture({failNormalExport=false}={}) {
  const page={id:'page',type:'PAGE'};let exports=0;
  const text={id:'text',type:'TEXT',parent:{id:'component'},blendMode:'PASS_THROUGH',opacity:1,effects:[],isMask:false,
    absoluteBoundingBox:{x:0,y:0,width:28,height:21},absoluteTransform:[[1,0,0],[0,1,0]],
    getStyledTextSegments:()=>[{fontName:{family:'Fixture',style:'Regular'}}]};
  const root={id:'component',type:'COMPONENT',parent:page,children:[text],absoluteBoundingBox:{x:0,y:0,width:60,height:32},absoluteTransform:[[1,0,0],[0,1,0]],
    findAllWithCriteria:()=>[text],exportAsync:async()=>{exports++;if(exports===2&&failNormalExport)throw new Error('fixture export failure');return new Uint8Array([137,80,78,71]);}};
  const api={editorType:'figma',fileKey:'file',getNodeByIdAsync:async id=>id==='page'?page:root,
    setCurrentPageAsync:async()=>{},loadFontAsync:async()=>{},base64Encode:value=>Buffer.from(value).toString('base64')};
  return {api,text,request:{fileReference:'file',pageReference:'page',componentReference:'component',logicalId:'fixture',textReferences:['text']}};
}
test('records reversible mutation and actual three-stage raster observations',async()=>{
  const f=fixture();const r=await context.probeTextBlendMode(f.api,f.request);
  assert.equal(r.status,'PASS');assert.equal(f.text.blendMode,'PASS_THROUGH');
  assert.equal(r.originalObservedStateRestored,true);assert.deepEqual(Array.from(r.mutatedNodeIds),['text']);
  assert.deepEqual(Array.from(r.restoredNodeIds),['text']);assert.equal(Object.keys(r.rasters).length,3);
  assert.equal(r.admissionEligible,false);
});
test('export failure after mutation still restores and keeps failure ledger',async()=>{
  const f=fixture({failNormalExport:true});const r=await context.probeTextBlendMode(f.api,f.request);
  assert.equal(r.status,'FAIL');assert.equal(f.text.blendMode,'PASS_THROUGH');
  assert.equal(r.originalObservedStateRestored,true);assert.equal(r.restoredNodeIds.length,1);
});
test('changed inventory is rejected before any mutation',async()=>{
  const f=fixture();f.request.textReferences=['other'];const r=await context.probeTextBlendMode(f.api,f.request);
  assert.equal(r.status,'FAIL');assert.equal(r.mutatedNodeIds.length,0);assert.equal(Object.keys(r.rasters).length,0);
});
