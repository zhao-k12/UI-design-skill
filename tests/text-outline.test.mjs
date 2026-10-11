import {test} from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFile} from 'node:fs/promises';
const ctx=vm.createContext({});vm.runInContext(await readFile(new URL('../adapters/figma/text_outline.js',import.meta.url),'utf8'),ctx);
function fixture() {
  const events=[],page={id:'page',type:'PAGE'},text={id:'text',type:'TEXT',parent:page,characters:'fixture',fontName:{family:'Fixture',style:'Regular'},fontWeight:400,fontSize:14,lineHeight:{unit:'AUTO'},absoluteBoundingBox:{x:1,y:2,width:20,height:20},absoluteRenderBounds:{x:2,y:3,width:18,height:17},getStyledTextSegments(){return [{fontName:this.fontName}]},async exportAsync(settings){assert.equal(settings.svgOutlineText,true);assert.equal(settings.format,'SVG_STRING');events.push('export');return '<svg><path d="M0 0L1 1"/></svg>';}};
  const api={editorType:'figma',fileKey:'fixture',mixed:Symbol('mixed'),getNodeByIdAsync:async id=>id==='page'?page:text,setCurrentPageAsync:async()=>events.push('page'),loadFontAsync:async()=>events.push('font')};
  return {api,text,events,request:{fileReference:'fixture',pageReference:'page',textReferences:['text']}};
}
test('reads actual render bounds and awaits font before outline export without writes',async()=>{
  const f=fixture(),r=await ctx.captureTextOutlines(f.api,f.request);
  assert.equal(r.status,'PASS');assert.equal(r.observations[0].absoluteRenderBounds.width,18);
  assert.deepEqual(f.events,['page','font','export']);assert.equal(r.createdNodeIds.length,0);assert.equal(r.admissionEligible,false);
});
test('wrong file or cross-page text cannot be exported',async()=>{
  const f=fixture();f.request.fileReference='other';assert.equal((await ctx.captureTextOutlines(f.api,f.request)).status,'FAIL');assert.equal(f.events.length,0);
  f.request.fileReference='fixture';f.text.parent={type:'PAGE',id:'foreign'};
  assert.equal((await ctx.captureTextOutlines(f.api,f.request)).status,'FAIL');assert.ok(!f.events.includes('export'));
});
test('export failure is explicit and mixed source properties are preserved',async()=>{
  const f=fixture();f.text.fontSize=f.api.mixed;
  assert.equal((await ctx.captureTextOutlines(f.api,f.request)).observations[0].fontSize.nativeMixed,true);
  f.text.exportAsync=async()=>{throw new Error('export failed')};
  const r=await ctx.captureTextOutlines(f.api,f.request);assert.equal(r.status,'FAIL');assert.equal(r.issues[0].code,'export failed');
});
