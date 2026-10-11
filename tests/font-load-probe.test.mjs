import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';
const context=vm.createContext({});vm.runInContext(await readFile(new URL('../adapters/figma/font_load_probe.js',import.meta.url),'utf8'),context);
const probe=context.probeSourceFontLoading;
const request={fileReference:'fixture',fonts:[{fontName:{family:'FixtureSource',style:'Regular'},postScriptName:'FixtureSource-Regular',sourceFileSha256:'a'.repeat(64)}]};
test('absent source font is explicitly missing and never substituted',async()=>{
  const api={editorType:'figma',fileKey:'fixture',listAvailableFontsAsync:async()=>[],loadFontAsync:async font=>{assert.equal(font.family,'FixtureSource');throw new Error('fixture missing');}};
  const r=await probe(api,request);assert.equal(r.status,'REVIEW');assert.equal(r.fonts[0].loadSucceeded,false);
  assert.equal(r.createdNodeIds.length,0);assert.equal(r.mutatedNodeIds.length,0);
});
test('listed source font loads before success and remains unadmitted',async()=>{
  let loaded=false;const api={editorType:'figma',fileKey:'fixture',listAvailableFontsAsync:async()=>[{fontName:request.fonts[0].fontName}],loadFontAsync:async()=>{await Promise.resolve();loaded=true;}};
  const r=await probe(api,request);assert.ok(loaded);assert.equal(r.status,'PASS');assert.equal(r.admissionEligible,false);
});
test('successful unlisted loading stays review and cannot bypass discovery guards',async()=>{
  const api={editorType:'figma',fileKey:'fixture',listAvailableFontsAsync:async()=>[],loadFontAsync:async()=>{}};
  const r=await probe(api,request);assert.equal(r.status,'REVIEW');assert.equal(r.fonts[0].status,'LOAD_SUCCEEDED_NOT_LISTED');
});
test('incorrect file or missing source identity fail before loading',async()=>{
  let calls=0;const api={editorType:'figma',fileKey:'other',listAvailableFontsAsync:async()=>{calls++;return [];}};
  assert.equal((await probe(api,request)).status,'FAIL');assert.equal(calls,0);
  api.fileKey='fixture';assert.equal((await probe(api,{fileReference:'fixture',fonts:[{fontName:request.fonts[0].fontName}]})).status,'FAIL');assert.equal(calls,0);
});
