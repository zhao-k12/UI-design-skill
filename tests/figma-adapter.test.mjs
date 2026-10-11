// Plugin API contract simulation only. This suite never claims native Figma acceptance.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';

const runtime = await readFile(new URL('../adapters/figma/runtime.js', import.meta.url), 'utf8');
const execute = new Function('api', 'payload', runtime + '\nreturn executeFigmaAdapter(api,payload);');
const layout = (width = {mode:'hug'}, height = {mode:'hug'}, direction = 'vertical') => ({width,height,direction,gap:16,
  padding:{top:0,right:0,bottom:0,left:0},wrap:false,alignment:{main:'start',cross:'start'}});
const text = {id:'title',name:'Title',type:'Text',text:'Editable',fontName:{family:'Test Font',style:'Regular'},
  layout:layout({mode:'fixed',value:300}),style:{typographyToken:{fontSize:14,fontWeight:400,lineHeight:22,letterSpacing:0},colorToken:'#11223380'}};
const payload = () => ({adapterVersion:'0.1.0',documentId:'fixture',uiIrSha256:'fixture',tokensSha256:'fixture',componentsSha256:'fixture',iconsSha256:'fixture',
  fileReference:'test-file',pageReference:null,page:{id:'page',name:'List',type:'Page',layout:layout({mode:'fixed',value:1440}),style:{},children:[structuredClone(text)]}});

function mockHost() {
  let serial = 0;
  const nodes = new Map(), loaded = new Set(), created = [];
  class Node {
    constructor(type, direction = 'NONE') {
      this.id = `mock:${++serial}`; this.type = type; this.name = ''; this.children = []; this.parent = null;
      this.width = 100; this.height = 20; this.x = 0; this.y = 0; this.layoutMode = direction; this.fills = [];
      this.fontName = {family:'Test Font',style:'Regular'}; this._h = 'FIXED'; this._v = 'FIXED'; nodes.set(this.id,this);
    }
    appendChild(node) {
      if (node.type === 'TEXT' && !loaded.has(node.fontName.family+'|'+node.fontName.style)) throw new Error('font was not awaited');
      if (node.parent) node.parent.children = node.parent.children.filter(n => n !== node);
      this.children.push(node); node.parent = this;
    }
    resize(w,h) { this.width=w;this.height=h;this._h='FIXED';this._v='FIXED'; }
    set characters(value) {
      if (!loaded.has(this.fontName.family+'|'+this.fontName.style)) throw new Error('unloaded font');
      this._characters=value;
    }
    get characters() { return this._characters; }
    get fontWeight() {return 400;}
    setMode(axis,value) {
      if (value === 'FILL' && (!this.parent || this.parent.layoutMode === 'NONE')) throw new Error('FILL before parenting');
      if (value === 'HUG' && this.layoutMode === 'NONE' && this.type !== 'TEXT') throw new Error('invalid HUG');
      if (value === 'FILL' && axis === 'h') this.width = this.parent.width;
      this[axis === 'h' ? '_h' : '_v'] = value;
    }
    set layoutSizingHorizontal(v) {this.setMode('h',v);} get layoutSizingHorizontal(){return this._h;}
    set layoutSizingVertical(v) {this.setMode('v',v);} get layoutSizingVertical(){return this._v;}
    findAll(fn) {return this.children.flatMap(n=>[...(fn(n)?[n]:[]),...n.findAll(fn)]);}
    findOne(fn) {return this.findAll(fn)[0] || null;}
    findAllWithCriteria({types}) {return this.findAll(n=>types.includes(n.type));}
    createInstance() { const n = create('INSTANCE'); n.mainComponent=this; return n; }
  }
  const root = new Node('DOCUMENT'), initial = new Node('PAGE'); root.appendChild(initial);
  const api = {editorType:'figma',fileKey:'test-file',root,currentPage:initial,
    listAvailableFontsAsync: async()=>[{fontName:{family:'Test Font',style:'Regular'}}],
    getFontFamilyVariationAxes:()=>['wght'],
    loadFontAsync: async(font)=>{await Promise.resolve();loaded.add(font.family+'|'+font.style);},
    getNodeByIdAsync: async(id)=>nodes.get(id)||null,
    setCurrentPageAsync: async(page)=>{api.currentPage=page;},
    createPage:()=>{const n=create('PAGE',false);root.appendChild(n);return n;},
    createAutoLayout:(direction)=>create('FRAME',true,direction),createText:()=>create('TEXT')};
  function create(type, append = true, direction = 'NONE') {
    const n = new Node(type,direction); created.push(n.id); if (append) api.currentPage.appendChild(n); return n;
  }
  // Figma text creation itself is allowed before font load; later edits/reparenting require it.
  api.createText=()=>{const n=new Node('TEXT');created.push(n.id);api.currentPage.children.push(n);n.parent=api.currentPage;return n;};
  return {api,nodes,created,loaded,Node};
}

test('missing fonts and missing native masters abort before canvas creation', async()=>{
  for (const missing of ['font','master']) {
    const host=mockHost(), input=payload();
    if (missing==='font') host.api.listAvailableFontsAsync=async()=>[];
    else input.page.children=[{id:'instance',name:'Missing',type:'ComponentInstance',componentReference:'absent',
      layout:layout({mode:'fixed',value:60},{mode:'fixed',value:32}),style:{}}];
    await assert.rejects(execute(host.api,input), /missing_/);
    assert.equal(host.created.length,0);
  }
});
test('text stays editable, font load awaited, color alpha and explicit sizes survive translation', async()=>{
  const host=mockHost(), result=await execute(host.api,payload());
  assert.equal(result.status,'PASS');
  const n=host.nodes.get(result.nodeMap.title);
  assert.equal(n.type,'TEXT'); assert.equal(n.characters,'Editable');
  assert.equal(n.width,300); assert.equal(n.layoutSizingHorizontal,'FIXED'); assert.equal(n.layoutSizingVertical,'HUG');
  assert.equal(n.lineHeight.value,22); assert.equal(n.fills[0].opacity,128/255);
  assert.deepEqual(new Set(result.createdNodeIds),new Set(host.created));
});
test('registered masters become real INSTANCE calls rather than geometric stand-ins', async()=>{
  const host=mockHost(), master=new host.Node('COMPONENT'), input=payload();
  input.page.children=[{id:'instance',name:'Button',type:'ComponentInstance',componentReference:master.id,
    layout:layout({mode:'fixed',value:60},{mode:'fixed',value:32}),style:{}}];
  const result=await execute(host.api,input), n=host.nodes.get(result.nodeMap.instance);
  assert.equal(n.type,'INSTANCE');assert.equal(n.mainComponent.id,master.id);
  assert.equal(result.evidence.find(e=>e.uiIrId==='instance').mainComponentReference,master.id);
});
test('Grid24 is translated into editable vertical rows, horizontal rows and fixed cells', async()=>{
  const host=mockHost(), input=payload();
  input.page.children=[{id:'grid',name:'Grid',type:'Grid',layout:layout({mode:'fill'}),style:{},
    gridCells:[{id:'a',row:0,width:348},{id:'b',row:1,width:348}],
    children:['a','b'].map(id=>({id,name:id,type:'Frame',layout:layout({mode:'fill'}),style:{},children:[]}))}];
  const result=await execute(host.api,input), grid=host.nodes.get(result.nodeMap.grid);
  assert.equal(grid.layoutMode,'VERTICAL');assert.equal(grid.children.length,2);
  for (const row of grid.children) {assert.equal(row.layoutMode,'HORIZONTAL');assert.equal(row.children[0].width,348);}
  assert.equal(result.helperNodeIds.length,4);assert.equal(host.nodes.get(result.nodeMap.a).layoutSizingHorizontal,'FILL');
});
test('retry requires exact ledger and never duplicates or removes prior work', async()=>{
  const host=mockHost(), input=payload(), first=await execute(host.api,input), count=host.created.length;
  await assert.rejects(execute(host.api,input),/existing_page_requires_ledger/);
  input.pageReference=first.pageReference;
  await assert.rejects(execute(host.api,input),/existing_output_requires_review/);
  assert.equal(host.created.length,count);
});
test('partial host failure returns exact created ledger for targeted recovery', async()=>{
  const host=mockHost();host.api.createText=()=>{throw new Error('injected host failure');};
  const result=await execute(host.api,payload());
  assert.equal(result.status,'FAIL');assert.equal(result.issues[0].code,'native_write_failed');
  assert.deepEqual(new Set(result.createdNodeIds),new Set(host.created));
  assert.ok(host.nodes.get(result.pageReference));
});
test('variable font weights preserve exact requested weight and reject unsupported axes before writing', async()=>{
  const host=mockHost(), input=payload();
  input.page.children[0].fontName.variationSettings={wght:600};
  input.page.children[0].style.typographyToken.fontWeight=600;
  const result=await execute(host.api,input);
  assert.equal(result.evidence.find(e=>e.uiIrId==='title').fontWeight,600);
  const unsupported=mockHost();unsupported.api.getFontFamilyVariationAxes=()=>[];
  await assert.rejects(execute(unsupported.api,input),/unsupported_font_axis/);
  assert.equal(unsupported.created.length,0);
});
