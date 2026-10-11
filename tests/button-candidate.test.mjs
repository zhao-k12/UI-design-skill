import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';
const code = await readFile(new URL('../adapters/figma/button_candidate.js', import.meta.url),'utf8');
const context = vm.createContext({}); vm.runInContext(code,context);
const build = context.buildButtonCandidate;
function fixture({missing=false, wrongWeight=false, duplicate=false, calibrated=false}={}) {
  let counter=0; const nodes=[]; const loaded=new Set();
  const font={family:'Fixture Source',style:'Regular'};
  const page={type:'PAGE',children:duplicate?[{name:'candidate/fixture',x:0,width:60}]:[],appendChild(node){this.children.push(node);}};
  const api={editorType:'figma',fileKey:'fixture',
    listAvailableFontsAsync:async()=>missing?[]:[{fontName:font}],loadFontAsync:async f=>{loaded.add(f.family);},
    getNodeByIdAsync:async()=>page,setCurrentPageAsync:async()=>{},
    createAutoLayout(){const isSpan=nodes.length>0;const n={id:String(++counter),type:'FRAME',children:[],resize(w,h){this.width=w+(isSpan?0:1);this.height=h;},appendChild(t){this.children.push(t);t.x=17;t.y=6;}};nodes.push(n);return n;},
    createText(){const n={id:String(++counter),type:'TEXT',fontName:{family:'Default',style:'Regular'},fontWeight:wrongWeight?700:400,width:29,height:21,exportAsync:async()=>'<svg>fixture</svg>'};nodes.push(n);return n;},
    createComponentFromNode(frame){return Object.assign({},frame,{id:String(++counter),type:'COMPONENT'});}};
  const payload={fileReference:'fixture',pageReference:'page',spec:{name:'candidate/fixture',logicalId:'fixture',sourceVersion:'fixture',
    fontName:font,width:60,height:32,strokeWidth:1,radius:4,padding:{top:0,right:15,bottom:0,left:15},
    fontSize:14,fontWeight:400,lineHeight:21,text:'查询',fill:{},stroke:{},textFill:{}}};
  if(calibrated)payload.spec.sourceSpan={bounds:{x:17,y:6,width:29,height:21},textOffsetY:-1,nativeSvgBaseline:16,sourceBaselineComponentY:21,verifiedNativeSvg:'<svg>fixture</svg>',evidenceHashes:{a:'a'.repeat(64),b:'b'.repeat(64),c:'c'.repeat(64),d:'d'.repeat(64)}};
  return {api,payload,nodes,loaded};
}
test('missing source fonts create no native nodes',async()=>{
  const f=fixture({missing:true});const result=await build(f.api,f.payload);
  assert.equal(result.status,'FAIL');assert.equal(f.nodes.length,0);assert.equal(result.createdNodeIds.length,0);
});
test('candidate is editable and measurements read native values rather than source bounds',async()=>{
  const f=fixture();const r=await build(f.api,f.payload);
  assert.equal(r.status,'PASS');assert.equal(r.nativeObservation.component.type,'COMPONENT');
  assert.equal(r.nativeObservation.component.width,61);assert.equal(r.nativeObservation.text.width,29);
  assert.equal(r.nativeObservation.text.characters,'查询');assert.equal(r.createdNodeIds.length,3);
  assert.ok(f.loaded.has('Default'));assert.ok(f.loaded.has('Fixture Source'));
  assert.equal(r.admissionEligible,false);assert.equal(r.fidelityGate,'NOT_RUN');
});
test('font weight mismatch preserves the exact partial ledger',async()=>{
  const f=fixture({wrongWeight:true});const r=await build(f.api,f.payload);
  assert.equal(r.status,'FAIL');assert.equal(r.createdNodeIds.length,2);assert.ok(!r.nativeObservation);
});
test('duplicate candidates require recovery rather than replacement',async()=>{
  const f=fixture({duplicate:true});const r=await build(f.api,f.payload);
  assert.equal(r.status,'FAIL');assert.equal(f.nodes.length,0);
});
test('calibrated builder retains editable text inside the measured span',async()=>{
  const f=fixture({calibrated:true});const r=await build(f.api,f.payload);
  assert.equal(r.status,'PASS');assert.equal(r.createdNodeIds.length,4);
  const span=f.nodes.find(node=>node.name==='source/0.0');
  assert.equal(span.clipsContent,false);assert.equal(span.children[0].layoutPositioning,'ABSOLUTE');
  assert.equal(r.nativeObservation.text.y,-1);assert.equal(r.nativeObservation.spanBounds.y,6);
});
test('bad calibration is rejected before creation and changed native dimensions stop conversion',async()=>{
  const bad=fixture({calibrated:true});bad.payload.spec.sourceSpan.textOffsetY=NaN;
  assert.equal((await build(bad.api,bad.payload)).status,'FAIL');assert.equal(bad.nodes.length,0);
  const changed=fixture({calibrated:true});changed.payload.spec.sourceSpan.bounds.width=28;
  const r=await build(changed.api,changed.payload);
  assert.equal(r.status,'FAIL');assert.equal(r.createdNodeIds.length,2);
  assert.equal(r.issues[0].code,'button_baseline_native_text_dimensions_changed');
});
test('same size with changed native outline cannot reuse a calibrated baseline',async()=>{
  const f=fixture({calibrated:true});f.payload.spec.sourceSpan.verifiedNativeSvg='<svg>changed</svg>';
  const r=await build(f.api,f.payload);assert.equal(r.status,'FAIL');
  assert.equal(r.createdNodeIds.length,2);assert.equal(r.issues[0].code,'button_baseline_native_outline_changed');
});
