// Test public Plugin API file scoping; no actual platform acceptance.
import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {readFileSync} from 'node:fs';

const cwd=fileURLToPath(new URL('../',import.meta.url));
const generated=spawnSync(`${cwd}.venv/Scripts/python.exe`,['-c',
  "from adapters.penpot.host.server import assets;print(assets('http://127.0.0.1:60000','test-target','test-nonce')['/plugin.js'][1])"],{cwd,encoding:'utf8'});
assert.equal(generated.status,0,generated.stderr);

test('diagnostic refuses another file before reading its fonts or components',()=>{
  let callback,result,opened;
  const api={currentFile:{id:'other-file'},ui:{open:(...args)=>opened=args,onMessage:fn=>callback=fn,sendMessage:r=>result=r},
    get fonts(){assert.fail('must not inspect another file');},get library(){assert.fail('must not inspect another file');}};
  vm.runInNewContext(generated.stdout,{penpot:api});
  callback({type:'task010-inspect'});
  assert.equal(result.status,'FAIL');assert.match(result.error,/target_file_mismatch/);
  assert.equal(opened[1],'http://127.0.0.1:60000/index.html');
});
test('unknown messages cannot trigger native reads or writes',()=>{
  let callback;
  const api={ui:{open:()=>{},onMessage:fn=>callback=fn,sendMessage:()=>assert.fail('unexpected response')},
    get currentFile(){assert.fail('unknown message must not access native data');}};
  vm.runInNewContext(generated.stdout,{penpot:api});callback({type:'execute-code',code:'anything'});
});

const candidate=vm.runInNewContext(readFileSync(new URL('../adapters/penpot/component_candidate.js',import.meta.url),'utf8')+';buildPenpotButtonCandidate');
const iconBuild=vm.runInNewContext(readFileSync(new URL('../adapters/penpot/icon_library.js',import.meta.url),'utf8')+';buildPenpotIcons');
const iconCapture=vm.runInNewContext(readFileSync(new URL('../adapters/penpot/icon_library.js',import.meta.url),'utf8')+';capturePenpotIcons',{btoa:s=>Buffer.from(s,'binary').toString('base64')});
test('Official icon import refuses a foreign file before SVG creation',async()=>{
  const api={currentFile:{id:'other'},currentPage:{id:'page'},createShapeFromSvg(){assert.fail('must not import');}};
  await assert.rejects(iconBuild(api,{fileReference:'file',pageReference:'page'}),/icon_context_mismatch/);
});
test('Icon PNG timeout retains SVG and remains partial without admission',async()=>{
  const main={id:'main',width:24,height:24,type:'board',children:[],isComponentMainInstance:()=>true,isComponentRoot:()=>true,export:async config=>{if(config.type==='png')throw Error('test-only-timeout');return new Uint8Array([1]);}};
  const api={currentFile:{id:'file',revn:1},currentPage:{id:'page'},library:{local:{components:[{id:'component',mainInstance:()=>main}]}}};
  const result=await iconCapture(api,{fileReference:'file',pageReference:'page',masters:[{iconId:'test-only',mainReference:'main',componentReference:'component'}]});
  assert.equal(result.status,'PARTIAL');assert.equal(result.icons[0].nativeSvgBase64,'AQ==');assert.equal(result.icons[0].exportIssues[0].format,'png');assert.equal(result.admissionEligible,false);
});
const inputCandidate=vm.runInNewContext(readFileSync(new URL('../adapters/penpot/component_candidate.js',import.meta.url),'utf8')+';buildPenpotInputCandidate');
test('content raster preserves its actual scope and refuses a painted wrapper',async()=>{
  const group={id:'group',type:'group',width:24,height:24,x:0,y:0,children:[],export:async()=>new Uint8Array([2])};
  const main={id:'main',type:'board',width:24,height:24,x:0,y:0,children:[group],fills:[],strokes:[],opacity:1,rotation:0,shadows:[],blur:null,hidden:false,visible:true,flipX:false,flipY:false,blendMode:'normal',isComponentMainInstance:()=>true,isComponentRoot:()=>true,export:async()=>new Uint8Array([1])};
  const api={currentFile:{id:'file',revn:1},currentPage:{id:'page'},library:{local:{components:[{id:'component',mainInstance:()=>main}]}}};
  const request={fileReference:'file',pageReference:'page',masters:[{mainReference:'main',componentReference:'component'}]};
  const result=await iconCapture(api,request,{contentRaster:true});
  assert.equal(result.status,'CAPTURED');assert.equal(result.admissionEligible,false);
  assert.equal(result.icons[0].rasterShapeReference,'group');assert.equal(result.icons[0].nativeRasterSvgBase64,'Ag==');
  for(const change of [{fills:[{fillColor:'#fff'}]},{opacity:null},{hidden:true},{x:1},{blendMode:'multiply'}]){
    const saved={...main};Object.assign(main,change);
    await assert.rejects(iconCapture(api,request,{contentRaster:true}),/not_equivalent/);Object.assign(main,saved);
  }
});
const selectCandidate=vm.runInNewContext(readFileSync(new URL('../adapters/penpot/component_candidate.js',import.meta.url),'utf8')+readFileSync(new URL('../adapters/penpot/select_candidate.js',import.meta.url),'utf8')+';buildPenpotSelectCandidate');
const tableCandidate=vm.runInNewContext(readFileSync(new URL('../adapters/penpot/component_candidate.js',import.meta.url),'utf8')+readFileSync(new URL('../adapters/penpot/table_candidate.js',import.meta.url),'utf8')+';buildPenpotTableCandidate');
test('Table refuses foreign files and absent exact fonts before creation',async()=>{
  const api={currentFile:{id:'other'},currentPage:{id:'page',root:{children:[]}},library:{local:{components:[]}},fonts:{all:[]},createBoard(){assert.fail('must not create');}};
  const spec={fileReference:'file',pageReference:'page',logicalId:'data.table.default',fontFamily:'PingFang SC'};
  await assert.rejects(tableCandidate(api,spec),/candidate_context_mismatch/);api.currentFile.id='file';
  await assert.rejects(tableCandidate(api,spec),/candidate_exact_font_missing/);
});
test('Select preflights both fonts before creating nodes',async()=>{
  const spec={fileReference:'file',pageReference:'page',logicalId:'form.select.default.medium',labelRole:'selected-value',nativeTextBounds:null,
    fontFamily:'PingFang SC',fontWeight:400,arrow:{fontFamily:'Ionicons',fontWeight:400}};
  const api={currentFile:{id:'file'},currentPage:{id:'page',root:{children:[]}},library:{local:{components:[]}},
    fonts:{all:[{fontFamily:'PingFang SC',variants:[{fontWeight:400,fontStyle:'normal',fontVariantId:'normal-400'}]}]},createBoard(){assert.fail('missing arrow font must stop creation');}};
  await assert.rejects(selectCandidate(api,spec),/candidate_exact_font_missing/);
  api.currentPage.root.children=[{name:'candidate / form.select.default.medium / penpot-v1'}];
  await assert.rejects(selectCandidate(api,spec),/candidate_requires_recovery/);
  api.currentFile.id='other';await assert.rejects(selectCandidate(api,spec),/candidate_context_mismatch/);
});
test('Input refuses foreign context, missing fonts and duplicate masters before writing',async()=>{
  const spec={fileReference:'file',pageReference:'page',logicalId:'form.input.default.medium',labelRole:'placeholder',nativeTextBounds:null,fontFamily:'PingFang SC'};
  const api={currentFile:{id:'other'},currentPage:{id:'page',root:{children:[]}},library:{local:{components:[]}},fonts:{all:[]},createBoard(){assert.fail('must not create');}};
  await assert.rejects(inputCandidate(api,spec),/candidate_context_mismatch/);
  api.currentFile.id='file';await assert.rejects(inputCandidate(api,spec),/candidate_exact_font_missing/);
  api.currentPage.root.children=[{name:'candidate / form.input.default.medium / penpot-v1'}];
  await assert.rejects(inputCandidate(api,spec),/candidate_requires_recovery/);
});
const inputOrder=vm.runInNewContext(readFileSync(new URL('../adapters/penpot/component_candidate.js',import.meta.url),'utf8')+';orderPenpotInputPaint');
test('Input recovery reorders only the identified source background',async()=>{
  let moved=false;
  const paint={id:'paint',type:'rectangle',name:'official-source / form.input.default.medium / border-centerline',x:80.5,y:160.5,width:239,height:31,fills:[{fillColor:'#ffffff'}],setParentIndex:i=>{assert.equal(i,0);moved=true;}};
  const main={id:'main',width:240,height:32,x:80,y:160,isComponentMainInstance:()=>true,children:[]};
  const text={id:'text',parent:main,characters:'请输入姓名'};main.children=[text,paint];
  const api={currentFile:{id:'file'},currentPage:{id:'page',getShapeById:()=>text},library:{local:{components:[{id:'component',mainInstance:()=>main}]}},waitForLayoutUpdate:async()=>{}};
  const request={fileReference:'file',pageReference:'page',componentReference:'component',mainReference:'main',textReference:'text'},spec={logicalId:'form.input.default.medium',characters:'请输入姓名',fill:'#ffffff'};
  paint.width=238;await assert.rejects(inputOrder(api,request,spec),/input_order_paint_mismatch/);assert.equal(moved,false);
  paint.width=239;const result=await inputOrder(api,request,spec);assert.equal(moved,true);assert.equal(result.status,'PAINT_ORDERED');assert.equal(result.admissionEligible,false);
});
test('candidate cannot write when its exact font is unavailable',async()=>{
  const api={currentFile:{id:'file'},currentPage:{id:'page',root:{children:[]}},library:{local:{components:[]}},
    fonts:{all:[]},createBoard(){assert.fail('missing font must prevent creation');}};
  await assert.rejects(candidate(api,{fileReference:'file',pageReference:'page',fontFamily:'PingFang SC',name:'test-only'}),/candidate_exact_font_missing/);
});
test('candidate refuses duplicate native masters before any creation',async()=>{
  const api={currentFile:{id:'file'},currentPage:{id:'page',root:{children:[{name:'same'}]}},library:{local:{components:[]}},
    createBoard(){assert.fail('must not duplicate');}};
  await assert.rejects(candidate(api,{fileReference:'file',pageReference:'page',name:'same'}),/candidate_requires_recovery/);
});

const frameCheck=vm.runInNewContext(readFileSync(new URL('../adapters/penpot/component_capture.js',import.meta.url),'utf8')+';isTextFrameOutline');
test('native flatten rectangle cannot count as a glyph outline',()=>{
  assert.equal(frameCheck({x:400,y:80,width:28,height:21,d:'M400,80L428,80L428,101L400,101L400,80'}),true);
  assert.equal(frameCheck({x:400,y:80,width:28,height:21,d:'M400,80Q410,70,428,80Z'}),false);
});

const variantCheck=vm.runInNewContext(readFileSync(new URL('../adapters/penpot/component_candidate.js',import.meta.url),'utf8')+';selectExactPenpotVariant');
test('duplicate font containers do not create a new public variant identity',()=>{
  const regular={fontVariantId:'normal-400',fontWeight:'400',fontStyle:'normal'};
  assert.equal(variantCheck({variants:[regular,{...regular}]},400),regular);
  assert.throws(()=>variantCheck({variants:[regular,{...regular,fontVariantId:'other'}]},400),/ambiguous/);
  assert.throws(()=>variantCheck({variants:[{...regular,fontVariantId:''}]},400),/ambiguous/);
});

const paintNormalize=vm.runInNewContext(readFileSync(new URL('../adapters/penpot/component_candidate.js',import.meta.url),'utf8')+';normalizePenpotButtonPaint');
test('paint normalization cannot remove a transparent or differently colored border',async()=>{
  const main={id:'main',isComponentMainInstance:()=>true,width:60,height:32,borderRadius:4,
    children:[{id:'text'}],fills:[{fillColor:'#2d8cf0',fillOpacity:1}],
    strokes:[{strokeColor:'#2d8cf0',strokeOpacity:0.5,strokeWidth:1,strokeAlignment:'inner'}]};
  const text={id:'text',parent:main,characters:'查询',fontFamily:'PingFang SC'};
  const api={currentFile:{id:'file'},currentPage:{id:'page',getShapeById:()=>text},
    library:{local:{components:[{id:'component',mainInstance:()=>main}]}},waitForLayoutUpdate:async()=>{}};
  const request={fileReference:'file',pageReference:'page',componentReference:'component',mainReference:'main',textReference:'text'};
  const spec={fill:'#2d8cf0',stroke:'#2d8cf0',strokeWidth:1,radius:4,characters:'查询',fontFamily:'PingFang SC'};
  await assert.rejects(paintNormalize(api,request,spec),/paint_requires_original_stroke/);
  assert.equal(main.strokes.length,1);
  await assert.rejects(paintNormalize(api,request,{...spec,stroke:'#ffffff'}),/unsupported_paint_union/);
  main.strokes[0].strokeOpacity=1;
  const result=await paintNormalize(api,request,spec);
  assert.equal(result.status,'PAINT_NORMALIZED');assert.equal(main.strokes.length,0);
  assert.equal(result.admissionEligible,false);assert.equal(text.opacity,1);
});

const candidateCapture=vm.runInNewContext(readFileSync(new URL('../adapters/penpot/component_capture.js',import.meta.url),'utf8')+';capturePenpotButtonCandidate',
  {btoa:s=>Buffer.from(s,'binary').toString('base64')});
test('Table capture refuses duplicate or foreign text inventory before exporting',async()=>{
  const main={id:'main',isComponentMainInstance:()=>true};
  const texts=Array.from({length:9},(_,i)=>({id:'text'+i,type:'text',parent:main}));
  const api={currentFile:{id:'file'},currentPage:{id:'page',getShapeById:id=>texts.find(t=>t.id===id)},library:{local:{components:[{id:'component',mainInstance:()=>main}]}},generateMarkup(){assert.fail('must not export');}};
  const request={fileReference:'file',pageReference:'page',logicalId:'data.table.default',componentReference:'component',mainReference:'main',textReference:'text0',textReferences:Array(9).fill('text0')};
  await assert.rejects(candidateCapture(api,request),/text_inventory_mismatch/);
  request.textReferences=texts.map(t=>t.id);texts[8].parent={id:'foreign'};
  await assert.rejects(candidateCapture(api,request),/text_outside_component/);
});
test('PNG service failure retains vector evidence and cannot claim complete capture',async()=>{
  const main={id:'main',width:60,height:32,children:[],isComponentMainInstance:()=>true,
    export:async config=>{if(config.type==='png')throw Error('fixture-export-timeout');return new Uint8Array([1,2,3]);}};
  const text={id:'text',type:'text',parent:main,children:[],export:async()=>new Uint8Array([4])};main.children=[text];
  const api={currentFile:{id:'file',revn:1},currentPage:{id:'page',getShapeById:()=>text},
    library:{local:{components:[{id:'component',mainInstance:()=>main}]}},
    generateMarkup:()=>'<svg/>',generateFontFaces:async()=>''};
  const result=await candidateCapture(api,{logicalId:'action.button.primary.medium',fileReference:'file',pageReference:'page',componentReference:'component',mainReference:'main',textReference:'text'});
  assert.equal(result.status,'PARTIAL');assert.equal(result.nativePngBase64,null);
  assert.equal(result.nativeSvgBase64,'AQID');assert.equal(result.exportIssues[0].type,'png');
  assert.equal(result.admissionEligible,false);
  api.generateMarkup=()=>{main.width=61;return '<svg/>';};
  await assert.rejects(candidateCapture(api,{logicalId:'action.button.primary.medium',fileReference:'file',pageReference:'page',componentReference:'component',mainReference:'main',textReference:'text'}),/candidate_capture_document_changed/);
});
