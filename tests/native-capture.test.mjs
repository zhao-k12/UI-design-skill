// Native capture API model; never production platform evidence.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';
const context=vm.createContext({});
vm.runInContext(await readFile(new URL('../adapters/figma/native_capture.js',import.meta.url),'utf8'),context);
const capture=context.captureNativeComponent;
function fixture({exportFailure=false,mixed=false}={}) {
  const events=[];const page={id:'page',type:'PAGE'};
  const text={id:'text',type:'TEXT',name:'fixture text',x:1,y:2,width:29,height:21,
    absoluteBoundingBox:{x:81,y:82,width:29,height:21},fontName:{family:'Fixture Font',style:'Regular'},
    fontWeight:400,fontSize:14,lineHeight:{unit:'PIXELS',value:21},letterSpacing:{unit:'PIXELS',value:0},
    characters:'查询',textAutoResize:'WIDTH_AND_HEIGHT',textAlignHorizontal:'LEFT',textAlignVertical:'TOP',textCase:'ORIGINAL',textDecoration:'NONE',blendMode:'NORMAL',isMask:false,
    getStyledTextSegments(){events.push('segments');return [{fontName:this.fontName}];}};
  const root={id:'component',type:'COMPONENT',parent:page,name:'fixture',x:80,y:80,width:61,height:32,
    absoluteBoundingBox:{x:80,y:80,width:61,height:32},children:[text],
    findAllWithCriteria(){return [text];},exportAsync:async settings=>{
      events.push('export');assert.equal(settings.format,'PNG');assert.equal(settings.constraint.value,1);
      assert.equal(settings.useAbsoluteBounds,true);if(exportFailure)throw new Error('fixture export failure');
      return new Uint8Array([137,80,78,71]);}};
  const api={editorType:'figma',fileKey:'fixture',currentPage:page,mixed:Symbol('mixed'),
    getNodeByIdAsync:async id=>id==='page'?page:root,
    setCurrentPageAsync:async()=>{events.push('page');},
    loadFontAsync:async()=>{await Promise.resolve();events.push('font-loaded');}};
  if(mixed)text.fontSize=api.mixed;
  const request={fileReference:'fixture',pageReference:'page',componentReference:'component',logicalId:'fixture.button',captureId:'fixture-capture',evidenceScope:'test-fixture'};
  return {api,root,request,events};
}
test('capture reads real node properties, waits for existing fonts, then exports without canvas mutation',async()=>{
  const f=fixture();const result=await capture(f.api,f.request);
  assert.equal(result.status,'PASS');assert.equal(result.nativeEvidence.nodes[0].localBounds.width,61);
  assert.equal(result.nativeEvidence.nodes[1].properties.characters,'查询');
  assert.equal(result.nativeEvidence.nodes[1].properties.textDecoration,'NONE');
  assert.equal(result.nativeEvidence.nodes[1].properties.textCase,'ORIGINAL');
  assert.equal(result.nativeEvidence.nodes[1].properties.blendMode,'NORMAL');
  assert.ok(f.events.indexOf('font-loaded')<f.events.indexOf('export'));
  assert.equal(result.raster.bytes.join(','),'137,80,78,71');
  assert.equal(result.createdNodeIds.length,0);assert.equal(result.mutatedNodeIds.length,0);
  assert.equal(result.admissionEligible,false);assert.equal(result.fidelityGate,'NOT_RUN');
});
test('cross-file and cross-page component references cannot be exported',async()=>{
  const f=fixture();f.request.fileReference='other';assert.equal((await capture(f.api,f.request)).status,'FAIL');
  f.request.fileReference='fixture';f.root.parent.id='other';
  // Return a separate selected page so the parent mutation cannot disguise the mismatch.
  f.api.getNodeByIdAsync=async id=>id==='page'?{id:'page',type:'PAGE'}:f.root;
  assert.equal((await capture(f.api,f.request)).status,'FAIL');assert.ok(!f.events.includes('export'));
});
test('export failure stays FAIL with no admitted capture',async()=>{
  const f=fixture({exportFailure:true});const result=await capture(f.api,f.request);
  assert.equal(result.status,'FAIL');assert.equal(result.admissionEligible,false);assert.ok(!result.raster);
});
test('native mixed values are explicitly recorded rather than invented',async()=>{
  const f=fixture({mixed:true});const result=await capture(f.api,f.request);
  assert.equal(result.status,'PASS');assert.equal(result.nativeEvidence.nodes[1].properties.fontSize.nativeMixed,true);
});
test('successful builder captures in the selected page without a second page switch',async()=>{
  const f=fixture();const built={status:'PASS',issues:[],createdNodeIds:['component','text'],mutatedNodeIds:[],
    nativeObservation:{componentReference:'component'},admissionEligible:false,fidelityGate:'NOT_RUN'};
  const result=await context.finishCandidateCapture(f.api,built,f.request);
  assert.equal(result.status,'PASS');assert.equal(result.nativeCapture.status,'PASS');
  assert.ok(!f.events.includes('page'));assert.equal(result.createdNodeIds.length,2);
});
test('capture failure retains builder ledger and a failed builder never exports',async()=>{
  const f=fixture({exportFailure:true});const built={status:'PASS',issues:[],createdNodeIds:['component'],
    nativeObservation:{componentReference:'component'}};
  const result=await context.finishCandidateCapture(f.api,built,f.request);
  assert.equal(result.status,'FAIL');assert.equal(result.createdNodeIds.length,1);
  assert.ok(result.issues.length>0);
  const empty=fixture();const failed={status:'FAIL',createdNodeIds:[]};
  assert.equal(await context.finishCandidateCapture(empty.api,failed,empty.request),failed);
  assert.equal(empty.events.length,0);
});
