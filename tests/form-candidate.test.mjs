// Plugin API contract fixtures. No assertion here proves native fidelity.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';
const context=vm.createContext({});
vm.runInContext(await readFile(new URL('../adapters/figma/form_candidate.js',import.meta.url),'utf8'),context);
const build=context.buildFormCandidate;
function fixture(kind='Input',{missingFamily=null,weightMismatch=false,duplicate=false}={}) {
  let counter=0; const nodes=[],loaded=new Set();
  const textFont={family:'FixtureText',style:'Regular'},iconFont={family:'FixtureIcons',style:'Regular'};
  const page={type:'PAGE',children:duplicate?[{name:'candidate/fixture',x:0,width:240}]:[],appendChild(n){this.children.push(n);n.parent=this;}};
  const api={editorType:'figma',fileKey:'fixture',listAvailableFontsAsync:async()=>[textFont,iconFont].filter(f=>f.family!==missingFamily).map(fontName=>({fontName})),
    loadFontAsync:async f=>{loaded.add(f.family);},getNodeByIdAsync:async()=>page,setCurrentPageAsync:async()=>{},
    createAutoLayout(){const node={id:String(++counter),type:'FRAME',children:[],x:0,y:0,
      resize(w,h){this.width=w;this.height=h;},appendChild(n){this.children.push(n);n.parent=this;n.x=1;n.y=2;}};nodes.push(node);return node;},
    createText(){const node={id:String(++counter),type:'TEXT',x:0,y:0,width:73,height:22,
      fontName:{family:'Default',style:'Regular'},fontWeight:weightMismatch?700:400,
      resize(w,h){this.width=w;this.height=h;}};nodes.push(node);return node;},
    createComponentFromNode(n){return Object.assign({},n,{id:String(++counter),type:'COMPONENT',width:n.width+1});}};
  const bounds={x:0,y:0,width:240,height:32};
  const label={characters:kind==='Input'?'请输入姓名':'启用',fontName:textFont,fontWeight:400,fontSize:14,
    lineHeight:kind==='Input'?{unit:'AUTO'}:{unit:'PIXELS',value:30},fill:{type:'SOLID',color:{r:197/255,g:200/255,b:206/255}},
    sourcePath:'label',padding:{top:0,right:24,bottom:0,left:8}};
  const spec={componentType:kind,logicalId:'fixture',name:'candidate/fixture',sourceVersion:'fixture',rootBounds:bounds,
    surface:{sourcePath:'field',bounds,fill:{},stroke:{},strokeWidth:1,radius:4,padding:{top:4,right:7,bottom:4,left:7}},
    content:kind==='Select'?{sourcePath:'content',bounds:{x:1,y:1,width:238,height:30}}:null,label,
    arrow:kind==='Select'?{...label,fontName:iconFont,characters:'\uf116',bounds:{x:217,y:9,width:14,height:14},sourcePath:'arrow'}:null};
  return {api,payload:{fileReference:'fixture',pageReference:'page',spec},nodes,loaded};
}
test('Input preserves editable placeholder and reads native text dimensions',async()=>{
  const f=fixture();const r=await build(f.api,f.payload);
  assert.equal(r.status,'PASS');assert.equal(r.nativeObservation.label.characters,'请输入姓名');
  assert.equal(r.nativeObservation.label.bounds.width,73);assert.equal(r.nativeObservation.root.bounds.width,241);
  assert.equal(r.nativeObservation.label.lineHeight.unit,'AUTO');assert.equal(r.nativeObservation.arrow,null);
  assert.equal(r.nativeObservation.field.paddingLeft,7);assert.equal(r.createdNodeIds.length,4);
  assert.ok(f.loaded.has('Default'));assert.equal(r.admissionEligible,false);
});
test('Select preserves Ionicons glyph and source absolute overlay without repeating transform',async()=>{
  const f=fixture('Select');const r=await build(f.api,f.payload);
  assert.equal(r.status,'PASS');assert.equal(r.nativeObservation.label.characters,'启用');
  assert.equal(r.nativeObservation.arrow.characters,'\uf116');assert.equal(r.nativeObservation.arrow.fontName.family,'FixtureIcons');
  assert.equal(r.nativeObservation.arrow.layoutPositioning,'ABSOLUTE');
  assert.equal(r.nativeObservation.arrow.bounds.x,216);assert.equal(r.nativeObservation.arrow.bounds.y,8);
  assert.equal(r.createdNodeIds.length,7);assert.equal(r.fidelityGate,'NOT_RUN');
});
test('missing text or arrow fonts abort the whole candidate before canvas writes',async()=>{
  for(const family of ['FixtureText','FixtureIcons']) {
    const f=fixture('Select',{missingFamily:family});const r=await build(f.api,f.payload);
    assert.equal(r.status,'FAIL');assert.equal(f.nodes.length,0);assert.equal(r.createdNodeIds.length,0);
  }
});
test('failed native font weight retains precise recovery ledger',async()=>{
  const f=fixture('Input',{weightMismatch:true});const r=await build(f.api,f.payload);
  assert.equal(r.status,'FAIL');assert.equal(r.createdNodeIds.length,3);assert.ok(!r.nativeObservation);
});
test('candidate retry never duplicates or replaces existing nodes',async()=>{
  const f=fixture('Select',{duplicate:true});const r=await build(f.api,f.payload);
  assert.equal(r.status,'FAIL');assert.equal(f.nodes.length,0);
});
