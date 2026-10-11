// Read-only host discovery. No native writes, network, credentials or user profile.
function discoverPenpotHost(api) {
  if (!api.currentFile || !api.currentPage) throw new Error('open_design_file_required');
  return {platform:'penpot', fileReference:api.currentFile.id, fileRevision:api.currentFile.revn,
    pageReference:api.currentPage.id, pages:api.currentFile.pages.map(p => ({id:p.id,name:p.name})),
    fonts:api.fonts.all.map(f => ({fontId:f.fontId,family:f.fontFamily,
      variants:f.variants.map(v => ({fontVariantId:v.fontVariantId,weight:Number(v.fontWeight),style:v.fontStyle}))})),
    components:api.library.local.components.map(c => {
      const main = c.mainInstance();
      return {componentReference:c.id,name:c.name,mainReference:main?.id,width:main?.width,height:main?.height};
    })};
}

const targetFile = "91396aad-60c8-808b-8008-c0885ca79899";
penpot.ui.open('TASK-010 实际环境检查',"http://127.0.0.1:57831/index.html",{width:440,height:280});
penpot.ui.onMessage(message => {
      if (message?.type !== 'task010-inspect') return;
      try {
        if (penpot.currentFile?.id !== targetFile) throw new Error('target_file_mismatch');
        penpot.ui.sendMessage({type:'task010-result',status:'CAPTURED',result:discoverPenpotHost(penpot)});
      } catch (error) { penpot.ui.sendMessage({type:'task010-result',status:'FAIL',error:String(error)}); }
    });
    
// First source-derived candidate only. No platform fidelity or Registry admission claim.
async function buildPenpotButtonCandidate(api, spec) {
  if (api.currentFile?.id!==spec.fileReference || api.currentPage?.id!==spec.pageReference) throw new Error('candidate_context_mismatch');
  const existingName=name=>name===spec.name || (typeof name==='string' && name.includes(spec.logicalId) && name.replace(/\s*\/\s*/g,'/').endsWith('/penpot-v1'));
  if (api.currentPage.root.children.some(n=>existingName(n.name)) || api.library.local.components.some(c=>existingName(c.name)||existingName(c.mainInstance()?.name))) throw new Error('candidate_requires_recovery');
  const fonts=api.fonts.all.filter(f=>f.fontFamily===spec.fontFamily);
  if(fonts.length!==1)throw new Error('candidate_exact_font_missing_or_ambiguous');
  const font=fonts[0],variant=selectExactPenpotVariant(font,spec.fontWeight);
  const created=[],record=n=>{if(!created.includes(n.id))created.push(n.id);return n;};
  let root,text,component;
  try {
    root=record(api.createBoard());api.currentPage.root.appendChild(root);root.name=spec.name;
    root.resize(spec.rootBounds.width,spec.rootBounds.height);root.x=80;root.y=80;root.clipContent=false;root.opacity=1;
    root.fills=[{fillColor:spec.fill,fillOpacity:1}];root.borderRadius=spec.radius;
    root.strokes=spec.fill===spec.stroke?[]:[{strokeColor:spec.stroke,strokeOpacity:1,strokeWidth:spec.strokeWidth,strokeAlignment:'inner',strokeStyle:'solid'}];
    text=api.createText(spec.characters);if(!text)throw new Error('candidate_text_creation_failed');record(text);
    font.applyToText(text,variant);text.fontSize=String(spec.fontSize);text.lineHeight=String(spec.lineHeight/spec.fontSize);
    text.letterSpacing='0';text.growType='fixed';text.verticalAlign='top';text.align='left';
    text.fills=[{fillColor:spec.textFill,fillOpacity:1}];text.opacity=1;root.appendChild(text);
    text.resize(spec.labelBounds.width,spec.labelBounds.height);text.x=root.x+spec.labelBounds.x;text.y=root.y+spec.labelBounds.y;
    text.name='official-source/'+spec.logicalId+'/0.0';
    if(text.fontFamily!==spec.fontFamily || Number(text.fontWeight)!==spec.fontWeight)throw new Error('candidate_font_readback_mismatch');
    component=api.library.local.createComponent([root]);component.name='penpot-v1';component.path='candidate/'+spec.logicalId;
    const main=component.mainInstance();
    if(spec.fill===spec.stroke){
      const normalized=await normalizePenpotButtonBorder(api,{fileReference:spec.fileReference,pageReference:spec.pageReference,
        componentReference:component.id,mainReference:main.id,textReference:text.id},spec);
      for(const id of normalized.createdNodeIds||[])if(!created.includes(id))created.push(id);
      if(normalized.status!=='BORDER_NORMALIZED')throw new Error('candidate_border_normalization_failed');
    }
    function inventory(n){record(n);for(const child of n.children||[])inventory(child);}inventory(main);
    return {status:'CANDIDATE_CREATED',platform:'penpot',fileReference:spec.fileReference,pageReference:api.currentPage.id,
      componentReference:component.id,mainReference:main.id,textReference:text.id,logicalId:spec.logicalId,componentIrSha256:spec.componentIrSha256,
      createdNodeIds:created,mutatedNodeIds:[],admissionEligible:false,baselineCalibration:'NOT_RUN',fidelityGate:'NOT_RUN'};
  } catch(error){return {status:'FAIL',platform:'penpot',fileReference:spec.fileReference,pageReference:api.currentPage.id,
    createdNodeIds:created,mutatedNodeIds:[],componentReference:component?.id,issues:[{code:'candidate_write_failed',detail:String(error)}],admissionEligible:false};}
}

function selectExactPenpotVariant(font,weight) {
  const matches=font.variants.filter(v=>Number(v.fontWeight)===weight && v.fontStyle==='normal');
  // Multiple uploaded containers can expose the same public native variant ID.
  // Collapse only identical public identities; different IDs remain ambiguous.
  if(matches.some(v=>typeof v.fontVariantId!=='string'||!v.fontVariantId))throw new Error('candidate_font_variant_missing_or_ambiguous');
  const unique=new Map(matches.map(v=>[v.fontVariantId,v]));
  if(unique.size!==1)throw new Error('candidate_font_variant_missing_or_ambiguous');
  return matches[0];
}

// Initial placeholder frame follows the measured browser text box. Its native
// baseline must be observed separately before any fidelity admission.
async function buildPenpotInputCandidate(api,spec) {
  if(spec.logicalId!=='form.input.default.medium'||spec.labelRole!=='placeholder'||spec.nativeTextBounds!==null)throw new Error('unsupported_input_candidate');
  if(api.currentFile?.id!==spec.fileReference||api.currentPage?.id!==spec.pageReference)throw new Error('candidate_context_mismatch');
  const exists=name=>typeof name==='string'&&name.includes(spec.logicalId)&&name.replace(/\s*\/\s*/g,'/').endsWith('/penpot-v1');
  if(api.currentPage.root.children.some(n=>exists(n.name))||api.library.local.components.some(c=>exists(c.mainInstance()?.name)))throw new Error('candidate_requires_recovery');
  const fonts=api.fonts.all.filter(f=>f.fontFamily===spec.fontFamily);
  if(fonts.length!==1)throw new Error('candidate_exact_font_missing_or_ambiguous');
  const font=fonts[0],variant=selectExactPenpotVariant(font,spec.fontWeight),created=[];
  const record=n=>{created.push(n.id);return n;};let component;
  try {
    const root=record(api.createBoard());api.currentPage.root.appendChild(root);root.name=spec.name;
    root.resize(spec.rootBounds.width,spec.rootBounds.height);root.x=80;root.y=160;
    root.clipContent=false;root.opacity=1;root.fills=[];root.strokes=[];root.borderRadius=spec.radius;
    const paint=record(api.createRectangle());root.appendChild(paint);
    paint.name='official-source/'+spec.logicalId+'/border-centerline';
    paint.resize(root.width-spec.strokeWidth,root.height-spec.strokeWidth);
    paint.x=root.x+spec.strokeWidth/2;paint.y=root.y+spec.strokeWidth/2;paint.borderRadius=spec.radius-spec.strokeWidth/2;paint.opacity=1;
    paint.fills=[{fillColor:spec.fill,fillOpacity:1}];
    paint.strokes=[{strokeColor:spec.stroke,strokeOpacity:1,strokeWidth:spec.strokeWidth,strokeAlignment:'center',strokeStyle:'solid'}];
    const text=api.createText(spec.characters);if(!text)throw new Error('candidate_text_creation_failed');record(text);
    font.applyToText(text,variant);text.fontSize=String(spec.fontSize);text.lineHeight=String(spec.sourceTextBounds.height/spec.fontSize);
    text.letterSpacing='0';text.growType='fixed';text.verticalAlign='top';text.align='left';text.opacity=1;
    text.fills=[{fillColor:spec.textFill,fillOpacity:1}];root.appendChild(text);
    text.resize(spec.sourceTextBounds.width,spec.sourceTextBounds.height);
    text.x=root.x+spec.sourceTextBounds.x;text.y=root.y+spec.sourceTextBounds.y;
    text.name='official-source/'+spec.logicalId+'/0.1::placeholder';
    paint.setParentIndex(0);
    if(text.fontFamily!==spec.fontFamily||Number(text.fontWeight)!==spec.fontWeight)throw new Error('candidate_font_readback_mismatch');
    component=api.library.local.createComponent([root]);component.name='penpot-v1';component.path='candidate/'+spec.logicalId;
    await api.waitForLayoutUpdate();const main=component.mainInstance();
    if(!created.includes(main.id))created.push(main.id);
    return {status:'CANDIDATE_CREATED',platform:'penpot',fileReference:spec.fileReference,pageReference:spec.pageReference,
      componentReference:component.id,mainReference:main.id,textReference:text.id,logicalId:spec.logicalId,
      componentIrSha256:spec.componentIrSha256,createdNodeIds:created,mutatedNodeIds:[],
      admissionEligible:false,baselineCalibration:'NOT_RUN',fidelityGate:'NOT_RUN'};
  }catch(error){return {status:'FAIL',platform:'penpot',fileReference:spec.fileReference,pageReference:spec.pageReference,
    componentReference:component?.id,createdNodeIds:created,mutatedNodeIds:[],issues:[{code:'candidate_write_failed',detail:String(error)}],admissionEligible:false};}
}

async function orderPenpotInputPaint(api,request,spec) {
  if(api.currentFile?.id!==request.fileReference||api.currentPage?.id!==request.pageReference||spec.logicalId!=='form.input.default.medium')throw new Error('input_order_context_mismatch');
  const main=api.library.local.components.find(c=>c.id===request.componentReference)?.mainInstance();
  const text=api.currentPage.getShapeById(request.textReference);
  if(!main||main.id!==request.mainReference||!main.isComponentMainInstance()||main.width!==240||main.height!==32||main.children.length!==2||text?.parent?.id!==main.id||text.characters!==spec.characters)throw new Error('input_order_identity_mismatch');
  const paint=main.children.find(n=>n.id!==text.id);
  if(paint.type!=='rectangle'||paint.name.replace(/\s*\/\s*/g,'/')!=='official-source/'+spec.logicalId+'/border-centerline'||paint.fills.length!==1||paint.fills[0].fillColor!==spec.fill||paint.x!==main.x+.5||paint.y!==main.y+.5||paint.width!==239||paint.height!==31)throw new Error('input_order_paint_mismatch');
  paint.setParentIndex(0);await api.waitForLayoutUpdate();
  return {status:'PAINT_ORDERED',platform:'penpot',fileReference:request.fileReference,pageReference:request.pageReference,
    componentReference:request.componentReference,createdNodeIds:[],mutatedNodeIds:[paint.id],admissionEligible:false,fidelityGate:'NOT_RUN'};
}

// Opaque same-color fill and inner border have the same outer filled region.
// A clipped duplicate SVG stroke overdraws its antialiased corner boundary.
async function normalizePenpotButtonPaint(api,request,spec) {
  if(api.currentFile?.id!==request.fileReference||api.currentPage?.id!==request.pageReference)throw new Error('paint_context_mismatch');
  if(spec.fill!==spec.stroke||spec.strokeWidth!==1||spec.radius!==4)throw new Error('unsupported_paint_union');
  const component=api.library.local.components.find(c=>c.id===request.componentReference),main=component?.mainInstance();
  if(!main||main.id!==request.mainReference||!main.isComponentMainInstance()||main.width!==60||main.height!==32||main.borderRadius!==4)throw new Error('paint_identity_mismatch');
  const text=api.currentPage.getShapeById(request.textReference);
  if(main.children.length!==1||text?.parent?.id!==main.id||text.characters!==spec.characters||text.fontFamily!==spec.fontFamily)throw new Error('paint_content_mismatch');
  if(main.fills.length!==1||main.fills[0].fillColor!==spec.fill||main.fills[0].fillOpacity!==1)throw new Error('paint_fill_mismatch');
  if(main.strokes.length!==1||main.strokes[0].strokeColor!==spec.fill||main.strokes[0].strokeOpacity!==1||main.strokes[0].strokeWidth!==1||main.strokes[0].strokeAlignment!=='inner')throw new Error('paint_requires_original_stroke');
  main.strokes=[];main.opacity=1;text.opacity=1;
  await api.waitForLayoutUpdate();
  return {status:'PAINT_NORMALIZED',platform:'penpot',fileReference:request.fileReference,pageReference:request.pageReference,
    componentReference:request.componentReference,createdNodeIds:[],mutatedNodeIds:[main.id,text.id],
    reason:'opaque_same_color_fill_and_inner_border_union',admissionEligible:false,fidelityGate:'NOT_RUN'};
}

async function normalizePenpotButtonBorder(api,request,spec) {
  if(api.currentFile?.id!==request.fileReference||api.currentPage?.id!==request.pageReference)throw new Error('border_context_mismatch');
  if(spec.fill!==spec.stroke||spec.strokeWidth!==1||spec.radius!==4)throw new Error('unsupported_border_geometry');
  const main=api.library.local.components.find(c=>c.id===request.componentReference)?.mainInstance();
  const text=api.currentPage.getShapeById(request.textReference);
  if(!main||main.id!==request.mainReference||!main.isComponentMainInstance()||main.width!==60||main.height!==32||main.children.length!==1||text?.parent?.id!==main.id)throw new Error('border_identity_mismatch');
  if(main.strokes.length||main.fills.length!==1||main.fills[0].fillColor!==spec.fill||main.fills[0].fillOpacity!==1||main.opacity!==1)throw new Error('border_requires_normalized_paint');
  const created=[];
  try {
    const paint=api.createRectangle();created.push(paint.id);
    paint.name='official-source/'+spec.logicalId+'/border-centerline';main.appendChild(paint);paint.setParentIndex(0);
    paint.resize(main.width-spec.strokeWidth,main.height-spec.strokeWidth);
    paint.x=main.x+spec.strokeWidth/2;paint.y=main.y+spec.strokeWidth/2;
    paint.borderRadius=spec.radius-spec.strokeWidth/2;paint.opacity=1;
    paint.fills=[{fillColor:spec.fill,fillOpacity:1}];
    paint.strokes=[{strokeColor:spec.stroke,strokeOpacity:1,strokeWidth:spec.strokeWidth,strokeAlignment:'center',strokeStyle:'solid'}];
    main.fills=[];await api.waitForLayoutUpdate();
    return {status:'BORDER_NORMALIZED',platform:'penpot',fileReference:request.fileReference,pageReference:request.pageReference,
      componentReference:request.componentReference,createdNodeIds:created,mutatedNodeIds:[main.id],
      reason:'css_uniform_inner_border_centerline_geometry',admissionEligible:false,fidelityGate:'NOT_RUN'};
  }catch(error){return {status:'FAIL',platform:'penpot',fileReference:request.fileReference,createdNodeIds:created,
    mutatedNodeIds:[main.id],issues:[{code:'border_normalization_failed',detail:String(error)}],admissionEligible:false};}
}

// Native static row/cell structure from the locked official Table fixture.
async function buildConfigurablePenpotTableCandidate(api,spec) {
  if(api.currentFile?.id!==spec.fileReference||api.currentPage?.id!==spec.pageReference||!/^data\.table\.config\.[a-f0-9]{64}$/.test(spec.logicalId))throw new Error('candidate_context_mismatch');
  const exists=name=>typeof name==='string'&&name.includes(spec.logicalId)&&name.replace(/\s*\/\s*/g,'/').endsWith('/penpot-v1');
  if(api.currentPage.root.children.some(n=>exists(n.name))||api.library.local.components.some(c=>exists(c.mainInstance()?.name)))throw new Error('candidate_requires_recovery');
  const fontMap=new Map();
  for(const family of spec.requiredFonts){const fonts=api.fonts.all.filter(f=>f.fontFamily===family);if(fonts.length!==1)throw new Error('candidate_exact_font_missing_or_ambiguous:'+family);const font=fonts[0];fontMap.set(family,{font,variant:selectExactPenpotVariant(font,400)});}
  const created=[],textReferences=[];let component;
  const record=n=>{created.push(n.id);return n;};
  try {
    const root=record(api.createBoard());api.currentPage.root.appendChild(root);root.name=spec.name;
    root.resize(spec.rootBounds.width,spec.rootBounds.height);root.x=Math.max(0,...api.currentPage.root.children.filter(n=>n.id!==root.id).map(n=>n.x+n.width))+80;root.y=320;root.clipContent=true;root.opacity=1;root.fills=[];root.strokes=[];root.borderRadius=0;
    const board=(parent,bounds,name,fill)=>{
      const n=record(api.createBoard());parent.appendChild(n);n.name=name;n.resize(bounds.width,bounds.height);
      n.x=root.x+bounds.x;n.y=root.y+bounds.y;n.clipContent=false;n.opacity=1;n.borderRadius=0;n.strokes=[];n.fills=fill?[{fillColor:fill,fillOpacity:1}]:[];return n;
    };
    const rectangle=(parent,bounds,name,fill)=>{
      const n=record(api.createRectangle());parent.appendChild(n);n.name=name;n.resize(bounds.width,bounds.height);
      n.x=root.x+bounds.x;n.y=root.y+bounds.y;n.borderRadius=0;n.opacity=1;n.strokes=[];n.fills=[{fillColor:fill,fillOpacity:1}];n.setParentIndex(parent.children.length-1);return n;
    };
    for(const row of spec.rows){
      const rowNode=board(root,row.bounds,'official-source/'+row.path,null);
      for(const cell of row.cells){
        const cellNode=board(rowNode,cell.bounds,'official-source/'+cell.path,cell.fill),item=cell.text;
        const text=api.createText(item.characters);if(!text)throw new Error('candidate_text_creation_failed');record(text);textReferences.push(text.id);
        const binding=fontMap.get(item.fontFamily);if(!binding)throw new Error('unplanned_table_font');binding.font.applyToText(text,binding.variant);text.fontSize=String(item.fontSize);text.lineHeight=String(item.sourceTextBounds.height/item.fontSize);
        text.letterSpacing='0';text.growType='fixed';text.verticalAlign='top';text.align='left';text.opacity=1;text.strokes=[];
        text.fills=[{fillColor:item.fill,fillOpacity:1}];cellNode.appendChild(text);text.resize(item.sourceTextBounds.width,item.sourceTextBounds.height);
        text.x=root.x+item.sourceTextBounds.x;text.y=root.y+item.sourceTextBounds.y;text.name='official-source/'+item.path;
        if(text.fontFamily!==item.fontFamily||Number(text.fontWeight)!==400)throw new Error('candidate_font_readback_mismatch');
        // The initial position data can retain default-font advances after a
        // whole-shape update. Bind the full public range to the actual font.
        binding.font.applyToRange(text.getRange(0,text.characters.length),binding.variant);
      }
      rectangle(rowNode,{x:row.bounds.x,y:row.bounds.y+row.bounds.height-row.bottomBorder.height,width:row.bounds.width,height:row.bottomBorder.height},'official-source/row-border/'+row.path,row.bottomBorder.fill);
    }
    rectangle(root,{x:0,y:root.height-spec.bottomPseudo.height,width:spec.bottomPseudo.width,height:spec.bottomPseudo.height},'official-source/0.0::before',spec.bottomPseudo.fill);
    component=api.library.local.createComponent([root]);component.name='penpot-v1';component.path='candidate/'+spec.logicalId;
    await api.waitForLayoutUpdate();const main=component.mainInstance();if(!created.includes(main.id))created.push(main.id);
    return {status:'CANDIDATE_CREATED',platform:'penpot',fileReference:spec.fileReference,pageReference:spec.pageReference,
      componentReference:component.id,mainReference:main.id,textReference:textReferences[0],textReferences,logicalId:spec.logicalId,
      componentIrSha256:spec.componentIrSha256,createdNodeIds:created,mutatedNodeIds:[],admissionEligible:false,baselineCalibration:'NOT_RUN',fidelityGate:'NOT_RUN'};
  }catch(error){return {status:'FAIL',platform:'penpot',fileReference:spec.fileReference,pageReference:spec.pageReference,componentReference:component?.id,
    createdNodeIds:created,mutatedNodeIds:[],issues:[{code:'candidate_write_failed',detail:String(error)}],admissionEligible:false};}
}

// Independent read-only candidate observation; raw native exports remain unmodified.
async function captureConfigurablePenpotTable(api, request) {
  if(api.currentFile?.id!==request.fileReference || api.currentPage?.id!==request.pageReference)throw new Error('candidate_capture_context_mismatch');
  const component=api.library.local.components.find(c=>c.id===request.componentReference);
  const main=component?.mainInstance(),text=api.currentPage.getShapeById(request.textReference);
  if(!main || main.id!==request.mainReference || !main.isComponentMainInstance() || !text || text.type!=='text')throw new Error('candidate_capture_identity_mismatch');
  let ancestor=text;while(ancestor && ancestor.id!==main.id)ancestor=ancestor.parent;
  if(!ancestor)throw new Error('candidate_capture_text_outside_component');
  const texts=request.textReferences?request.textReferences.map(id=>api.currentPage.getShapeById(id)):[text];
  if(/^data\.table\.config\.[a-f0-9]{64}$/.test(request.logicalId)){
    const count=request.rows.reduce((total,row)=>total+row.cells.length,0);
    if(texts.length!==count||new Set(texts.map(n=>n?.id)).size!==count)throw new Error('candidate_capture_text_inventory_mismatch');
    for(const node of texts){let parent=node;while(parent&&parent.id!==main.id)parent=parent.parent;if(!parent||node.type!=='text')throw new Error('candidate_capture_text_outside_component');}
  }
  const arrow=request.arrowReference?api.currentPage.getShapeById(request.arrowReference):null;
  if(request.logicalId==='form.select.default.medium'&&(!arrow||arrow.type!=='text'||arrow.parent?.id!==main.id))throw new Error('candidate_capture_arrow_identity_mismatch');
  const revision=api.currentFile.revn,nodes=[];
  function observe(n){
    const entry={reference:n.id,parentReference:n.parent?.id,type:n.type,name:n.name,x:n.x,y:n.y,width:n.width,height:n.height,
      fills:n.fills,strokes:n.strokes,opacity:n.opacity,blendMode:n.blendMode,borderRadius:n.borderRadius,clipContent:n.clipContent,
      rotation:n.rotation,hidden:n.hidden,visible:n.visible,flipX:n.flipX,flipY:n.flipY,shadows:n.shadows,blur:n.blur};
    if(n.type==='text')Object.assign(entry,{characters:n.characters,fontId:n.fontId,fontFamily:n.fontFamily,fontVariantId:n.fontVariantId,
      fontSize:n.fontSize,fontWeight:n.fontWeight,fontStyle:n.fontStyle,lineHeight:n.lineHeight,letterSpacing:n.letterSpacing,
      growType:n.growType,textBounds:n.textBounds,align:n.align,verticalAlign:n.verticalAlign,
      direction:n.direction,textTransform:n.textTransform,textDecoration:n.textDecoration});
    nodes.push(entry);for(const child of n.children||[])observe(child);
  }
  const expectedWidth=request.rootBounds.width,expectedHeight=request.rootBounds.height;
  if(expectedWidth===null||main.width!==expectedWidth || main.height!==expectedHeight)throw new Error('candidate_capture_geometry_mismatch');
  observe(main);const before=JSON.stringify(nodes);nodes.length=0;
  function encode(bytes){let value='';for(let i=0;i<bytes.length;i+=8192)value+=String.fromCharCode(...bytes.subarray(i,i+8192));return btoa(value);}
  const exportIssues=[];
  async function exported(shape,type){
    try {return await shape.export(type==='png'?{type,scale:1}:{type});}
    catch(error){exportIssues.push({code:'native_export_failed',shapeReference:shape.id,type,detail:String(error)});return null;}
  }
  const nativeSvgMarkup=api.generateMarkup([main],{type:'svg'});
  const svg=await exported(main,'svg'),textSvg=await exported(text,'svg'),png=await exported(main,'png');
  const arrowSvg=arrow?await exported(arrow,'svg'):null;
  let nativePdf;
  try { nativePdf={status:'CAPTURED',base64:encode(await main.export({type:'pdf'}))}; }
  catch(error){nativePdf={status:'FAIL',error:String(error)};}
  let nativeFontFaces;
  try { nativeFontFaces={status:'OBSERVED',css:await api.generateFontFaces(arrow?[text,arrow]:texts)}; }
  catch(error){nativeFontFaces={status:'FAIL',error:String(error)};}
  observe(main);
  if(JSON.stringify(nodes)!==before||api.currentFile.revn!==revision || api.currentFile.id!==request.fileReference || api.currentPage.id!==request.pageReference)throw new Error('candidate_capture_document_changed');
  return {status:png&&svg&&textSvg&&(!arrow||arrowSvg)?'CAPTURED':'PARTIAL',platform:'penpot',scope:'production',evidenceKind:'native-platform-export',exporterVersion:'penpot-configurable-table-capture-v0.1.0',
    fileReference:request.fileReference,pageReference:api.currentPage.id,fileRevision:revision,componentReference:component.id,
    mainReference:main.id,logicalId:request.logicalId,componentIrSha256:request.componentIrSha256,
    createdNodeIds:[],mutatedNodeIds:[],nodes,nativePngBase64:png?encode(png):null,nativeSvgBase64:svg?encode(svg):null,nativeTextSvgBase64:textSvg?encode(textSvg):null,
    ...(arrow?{arrowReference:arrow.id,nativeArrowSvgBase64:arrowSvg?encode(arrowSvg):null}:{}),nativeSvgMarkup,exportIssues,
    nativeFontFaces,nativePdf,penpotVersion:api.version,
    admissionEligible:false,fidelityGate:'NOT_RUN'};
}

const tableSpecs=[{"logicalId": "data.table.config.4fe0393d9091c298f4469e4e95f43824af5373fe0552434be0ed2887e3857a72", "sourceVersion": "view-ui-plus@1.3.24+23a8e5bd2c07143bebfbcadcfb30d6f5bd47834b", "componentIrSha256": "3c3993bb4ca86b5d4686818e2312410e7d35e03531aa8f87ec8c0e340ab082f9", "rootBounds": {"width": 720, "height": 96}, "rows": [{"path": "0.0.0.0.1.0", "bounds": {"x": 0, "y": 0, "width": 721, "height": 48}, "cells": [{"path": "0.0.0.0.1.0.0", "bounds": {"x": 0, "y": 0, "width": 240.328125, "height": 48}, "fill": "#ffffff", "text": {"path": "0.0.0.0.1.0.0.0.0", "characters": "赵六", "sourceTextBounds": {"x": 18, "y": 15, "width": 28, "height": 16}, "fontSize": 14, "fontWeight": 400, "fontFamily": "PingFang SC", "postScriptName": "PingFangSC-Regular", "fill": "#515a6e", "sourceBaselineY": 28}, "bottomBorder": {"height": 1.0, "fill": "#e8eaec"}}, {"path": "0.0.0.0.1.0.1", "bounds": {"x": 240.328125, "y": 0, "width": 480.671875, "height": 48}, "fill": "#ffffff", "text": {"path": "0.0.0.0.1.0.1.0.0", "characters": "zhao@example.com", "sourceTextBounds": {"x": 258.328125, "y": 15, "width": 127.828125, "height": 16}, "fontSize": 14, "fontWeight": 400, "fontFamily": "Arial", "postScriptName": "ArialMT", "fill": "#515a6e", "sourceBaselineY": 28}, "bottomBorder": {"height": 1.0, "fill": "#e8eaec"}}], "bottomBorder": {"height": 1.0, "fill": "#e8eaec"}}, {"path": "0.0.0.0.1.1", "bounds": {"x": 0, "y": 48, "width": 721, "height": 48}, "cells": [{"path": "0.0.0.0.1.1.0", "bounds": {"x": 0, "y": 48, "width": 240.328125, "height": 48}, "fill": "#ffffff", "text": {"path": "0.0.0.0.1.1.0.0.0", "characters": "钱七", "sourceTextBounds": {"x": 18, "y": 63, "width": 28, "height": 16}, "fontSize": 14, "fontWeight": 400, "fontFamily": "PingFang SC", "postScriptName": "PingFangSC-Regular", "fill": "#515a6e", "sourceBaselineY": 76}, "bottomBorder": {"height": 1.0, "fill": "#e8eaec"}}, {"path": "0.0.0.0.1.1.1", "bounds": {"x": 240.328125, "y": 48, "width": 480.671875, "height": 48}, "fill": "#ffffff", "text": {"path": "0.0.0.0.1.1.1.0.0", "characters": "qian@example.com", "sourceTextBounds": {"x": 258.328125, "y": 63, "width": 123.9375, "height": 16}, "fontSize": 14, "fontWeight": 400, "fontFamily": "Arial", "postScriptName": "ArialMT", "fill": "#515a6e", "sourceBaselineY": 76}, "bottomBorder": {"height": 1.0, "fill": "#e8eaec"}}], "bottomBorder": {"height": 1.0, "fill": "#e8eaec"}}], "sourceObservationSha256": "12d56a523432b2b729ce59467c302df25275dda2a43e8534cac72ae9fbc4e414", "requiredFonts": ["Arial", "PingFang SC"], "bottomPseudo": {"height": 1.0, "width": 720.0, "fill": "#dcdee2", "sourceCssRule": ".ivu-table:before{content:'';width:100%;height:1px;position:absolute;left:0;bottom:0;background-color:#dcdee2;z-index:4}"}, "admissionEligible": false, "fidelityGate": "NOT_RUN", "fileReference": "91396aad-60c8-808b-8008-c0885ca79899", "pageReference": null, "name": "candidate/data.table.config.4fe0393d9091c298f4469e4e95f43824af5373fe0552434be0ed2887e3857a72/penpot-v1"}, {"logicalId": "data.table.config.b3eb343b6ad2c8cd567a53f7d65703db6627cb9e7e1bfaedfb3098baf7af8122", "sourceVersion": "view-ui-plus@1.3.24+23a8e5bd2c07143bebfbcadcfb30d6f5bd47834b", "componentIrSha256": "d2a59922bf0203a1fde62b376868d323cbc49f1954d41e44f113174412c8183e", "rootBounds": {"width": 960, "height": 192}, "rows": [{"path": "0.0.0.0.1.0", "bounds": {"x": 0, "y": 0, "width": 961, "height": 48}, "cells": [{"path": "0.0.0.0.1.0.0", "bounds": {"x": 0, "y": 0, "width": 160.15625, "height": 48}, "fill": "#ffffff", "text": {"path": "0.0.0.0.1.0.0.0.0", "characters": "001", "sourceTextBounds": {"x": 18, "y": 15, "width": 23.359375, "height": 16}, "fontSize": 14, "fontWeight": 400, "fontFamily": "Arial", "postScriptName": "ArialMT", "fill": "#515a6e", "sourceBaselineY": 28}, "bottomBorder": {"height": 1.0, "fill": "#e8eaec"}}, {"path": "0.0.0.0.1.0.1", "bounds": {"x": 160.15625, "y": 0, "width": 240.25, "height": 48}, "fill": "#ffffff", "text": {"path": "0.0.0.0.1.0.1.0.0", "characters": "张三", "sourceTextBounds": {"x": 178.15625, "y": 15, "width": 28, "height": 16}, "fontSize": 14, "fontWeight": 400, "fontFamily": "PingFang SC", "postScriptName": "PingFangSC-Regular", "fill": "#515a6e", "sourceBaselineY": 28}, "bottomBorder": {"height": 1.0, "fill": "#e8eaec"}}, {"path": "0.0.0.0.1.0.2", "bounds": {"x": 400.40625, "y": 0, "width": 320.328125, "height": 48}, "fill": "#ffffff", "text": {"path": "0.0.0.0.1.0.2.0.0", "characters": "研发", "sourceTextBounds": {"x": 418.40625, "y": 15, "width": 28, "height": 16}, "fontSize": 14, "fontWeight": 400, "fontFamily": "PingFang SC", "postScriptName": "PingFangSC-Regular", "fill": "#515a6e", "sourceBaselineY": 28}, "bottomBorder": {"height": 1.0, "fill": "#e8eaec"}}, {"path": "0.0.0.0.1.0.3", "bounds": {"x": 720.734375, "y": 0, "width": 240.265625, "height": 48}, "fill": "#ffffff", "text": {"path": "0.0.0.0.1.0.3.0.0", "characters": "启用", "sourceTextBounds": {"x": 738.734375, "y": 15, "width": 28, "height": 16}, "fontSize": 14, "fontWeight": 400, "fontFamily": "PingFang SC", "postScriptName": "PingFangSC-Regular", "fill": "#515a6e", "sourceBaselineY": 28}, "bottomBorder": {"height": 1.0, "fill": "#e8eaec"}}], "bottomBorder": {"height": 1.0, "fill": "#e8eaec"}}, {"path": "0.0.0.0.1.1", "bounds": {"x": 0, "y": 48, "width": 961, "height": 48}, "cells": [{"path": "0.0.0.0.1.1.0", "bounds": {"x": 0, "y": 48, "width": 160.15625, "height": 48}, "fill": "#ffffff", "text": {"path": "0.0.0.0.1.1.0.0.0", "characters": "002", "sourceTextBounds": {"x": 18, "y": 63, "width": 23.359375, "height": 16}, "fontSize": 14, "fontWeight": 400, "fontFamily": "Arial", "postScriptName": "ArialMT", "fill": "#515a6e", "sourceBaselineY": 76}, "bottomBorder": {"height": 1.0, "fill": "#e8eaec"}}, {"path": "0.0.0.0.1.1.1", "bounds": {"x": 160.15625, "y": 48, "width": 240.25, "height": 48}, "fill": "#ffffff", "text": {"path": "0.0.0.0.1.1.1.0.0", "characters": "李四", "sourceTextBounds": {"x": 178.15625, "y": 63, "width": 28, "height": 16}, "fontSize": 14, "fontWeight": 400, "fontFamily": "PingFang SC", "postScriptName": "PingFangSC-Regular", "fill": "#515a6e", "sourceBaselineY": 76}, "bottomBorder": {"height": 1.0, "fill": "#e8eaec"}}, {"path": "0.0.0.0.1.1.2", "bounds": {"x": 400.40625, "y": 48, "width": 320.328125, "height": 48}, "fill": "#ffffff", "text": {"path": "0.0.0.0.1.1.2.0.0", "characters": "财务", "sourceTextBounds": {"x": 418.40625, "y": 63, "width": 28, "height": 16}, "fontSize": 14, "fontWeight": 400, "fontFamily": "PingFang SC", "postScriptName": "PingFangSC-Regular", "fill": "#515a6e", "sourceBaselineY": 76}, "bottomBorder": {"height": 1.0, "fill": "#e8eaec"}}, {"path": "0.0.0.0.1.1.3", "bounds": {"x": 720.734375, "y": 48, "width": 240.265625, "height": 48}, "fill": "#ffffff", "text": {"path": "0.0.0.0.1.1.3.0.0", "characters": "停用", "sourceTextBounds": {"x": 738.734375, "y": 63, "width": 28, "height": 16}, "fontSize": 14, "fontWeight": 400, "fontFamily": "PingFang SC", "postScriptName": "PingFangSC-Regular", "fill": "#515a6e", "sourceBaselineY": 76}, "bottomBorder": {"height": 1.0, "fill": "#e8eaec"}}], "bottomBorder": {"height": 1.0, "fill": "#e8eaec"}}, {"path": "0.0.0.0.1.2", "bounds": {"x": 0, "y": 96, "width": 961, "height": 48}, "cells": [{"path": "0.0.0.0.1.2.0", "bounds": {"x": 0, "y": 96, "width": 160.15625, "height": 48}, "fill": "#ffffff", "text": {"path": "0.0.0.0.1.2.0.0.0", "characters": "003", "sourceTextBounds": {"x": 18, "y": 111, "width": 23.359375, "height": 16}, "fontSize": 14, "fontWeight": 400, "fontFamily": "Arial", "postScriptName": "ArialMT", "fill": "#515a6e", "sourceBaselineY": 124}, "bottomBorder": {"height": 1.0, "fill": "#e8eaec"}}, {"path": "0.0.0.0.1.2.1", "bounds": {"x": 160.15625, "y": 96, "width": 240.25, "height": 48}, "fill": "#ffffff", "text": {"path": "0.0.0.0.1.2.1.0.0", "characters": "王五", "sourceTextBounds": {"x": 178.15625, "y": 111, "width": 28, "height": 16}, "fontSize": 14, "fontWeight": 400, "fontFamily": "PingFang SC", "postScriptName": "PingFangSC-Regular", "fill": "#515a6e", "sourceBaselineY": 124}, "bottomBorder": {"height": 1.0, "fill": "#e8eaec"}}, {"path": "0.0.0.0.1.2.2", "bounds": {"x": 400.40625, "y": 96, "width": 320.328125, "height": 48}, "fill": "#ffffff", "text": {"path": "0.0.0.0.1.2.2.0.0", "characters": "运营", "sourceTextBounds": {"x": 418.40625, "y": 111, "width": 28, "height": 16}, "fontSize": 14, "fontWeight": 400, "fontFamily": "PingFang SC", "postScriptName": "PingFangSC-Regular", "fill": "#515a6e", "sourceBaselineY": 124}, "bottomBorder": {"height": 1.0, "fill": "#e8eaec"}}, {"path": "0.0.0.0.1.2.3", "bounds": {"x": 720.734375, "y": 96, "width": 240.265625, "height": 48}, "fill": "#ffffff", "text": {"path": "0.0.0.0.1.2.3.0.0", "characters": "启用", "sourceTextBounds": {"x": 738.734375, "y": 111, "width": 28, "height": 16}, "fontSize": 14, "fontWeight": 400, "fontFamily": "PingFang SC", "postScriptName": "PingFangSC-Regular", "fill": "#515a6e", "sourceBaselineY": 124}, "bottomBorder": {"height": 1.0, "fill": "#e8eaec"}}], "bottomBorder": {"height": 1.0, "fill": "#e8eaec"}}, {"path": "0.0.0.0.1.3", "bounds": {"x": 0, "y": 144, "width": 961, "height": 48}, "cells": [{"path": "0.0.0.0.1.3.0", "bounds": {"x": 0, "y": 144, "width": 160.15625, "height": 48}, "fill": "#ffffff", "text": {"path": "0.0.0.0.1.3.0.0.0", "characters": "004", "sourceTextBounds": {"x": 18, "y": 159, "width": 23.359375, "height": 16}, "fontSize": 14, "fontWeight": 400, "fontFamily": "Arial", "postScriptName": "ArialMT", "fill": "#515a6e", "sourceBaselineY": 172}, "bottomBorder": {"height": 1.0, "fill": "#e8eaec"}}, {"path": "0.0.0.0.1.3.1", "bounds": {"x": 160.15625, "y": 144, "width": 240.25, "height": 48}, "fill": "#ffffff", "text": {"path": "0.0.0.0.1.3.1.0.0", "characters": "赵六", "sourceTextBounds": {"x": 178.15625, "y": 159, "width": 28, "height": 16}, "fontSize": 14, "fontWeight": 400, "fontFamily": "PingFang SC", "postScriptName": "PingFangSC-Regular", "fill": "#515a6e", "sourceBaselineY": 172}, "bottomBorder": {"height": 1.0, "fill": "#e8eaec"}}, {"path": "0.0.0.0.1.3.2", "bounds": {"x": 400.40625, "y": 144, "width": 320.328125, "height": 48}, "fill": "#ffffff", "text": {"path": "0.0.0.0.1.3.2.0.0", "characters": "客服", "sourceTextBounds": {"x": 418.40625, "y": 159, "width": 28, "height": 16}, "fontSize": 14, "fontWeight": 400, "fontFamily": "PingFang SC", "postScriptName": "PingFangSC-Regular", "fill": "#515a6e", "sourceBaselineY": 172}, "bottomBorder": {"height": 1.0, "fill": "#e8eaec"}}, {"path": "0.0.0.0.1.3.3", "bounds": {"x": 720.734375, "y": 144, "width": 240.265625, "height": 48}, "fill": "#ffffff", "text": {"path": "0.0.0.0.1.3.3.0.0", "characters": "启用", "sourceTextBounds": {"x": 738.734375, "y": 159, "width": 28, "height": 16}, "fontSize": 14, "fontWeight": 400, "fontFamily": "PingFang SC", "postScriptName": "PingFangSC-Regular", "fill": "#515a6e", "sourceBaselineY": 172}, "bottomBorder": {"height": 1.0, "fill": "#e8eaec"}}], "bottomBorder": {"height": 1.0, "fill": "#e8eaec"}}], "sourceObservationSha256": "4899e5745ac282403599fc484fdf0542bfadd745d8338527b104a04ee43d623a", "requiredFonts": ["Arial", "PingFang SC"], "bottomPseudo": {"height": 1.0, "width": 960.0, "fill": "#dcdee2", "sourceCssRule": ".ivu-table:before{content:'';width:100%;height:1px;position:absolute;left:0;bottom:0;background-color:#dcdee2;z-index:4}"}, "admissionEligible": false, "fidelityGate": "NOT_RUN", "fileReference": "91396aad-60c8-808b-8008-c0885ca79899", "pageReference": null, "name": "candidate/data.table.config.b3eb343b6ad2c8cd567a53f7d65703db6627cb9e7e1bfaedfb3098baf7af8122/penpot-v1"}];let tableExecution={"status": "CREATED", "fileReference": "91396aad-60c8-808b-8008-c0885ca79899", "pageReference": "b65bc280-c7a5-8006-8008-c496888c78a0", "candidates": [{"status": "CANDIDATE_CREATED", "platform": "penpot", "fileReference": "91396aad-60c8-808b-8008-c0885ca79899", "pageReference": "b65bc280-c7a5-8006-8008-c496888c78a0", "componentReference": "b65bc280-c7a5-8006-8008-c496894279a2", "mainReference": "b65bc280-c7a5-8006-8008-c49688a06509", "textReference": "b65bc280-c7a5-8006-8008-c49688d9eaf7", "textReferences": ["b65bc280-c7a5-8006-8008-c49688d9eaf7", "b65bc280-c7a5-8006-8008-c49688efc657", "b65bc280-c7a5-8006-8008-c49689120844", "b65bc280-c7a5-8006-8008-c4968927a3dc"], "logicalId": "data.table.config.4fe0393d9091c298f4469e4e95f43824af5373fe0552434be0ed2887e3857a72", "componentIrSha256": "3c3993bb4ca86b5d4686818e2312410e7d35e03531aa8f87ec8c0e340ab082f9", "createdNodeIds": ["b65bc280-c7a5-8006-8008-c49688a06509", "b65bc280-c7a5-8006-8008-c49688c69e37", "b65bc280-c7a5-8006-8008-c49688d24973", "b65bc280-c7a5-8006-8008-c49688d9eaf7", "b65bc280-c7a5-8006-8008-c49688e89922", "b65bc280-c7a5-8006-8008-c49688efc657", "b65bc280-c7a5-8006-8008-c49688fbb3a9", "b65bc280-c7a5-8006-8008-c49689045759", "b65bc280-c7a5-8006-8008-c496890abd6a", "b65bc280-c7a5-8006-8008-c49689120844", "b65bc280-c7a5-8006-8008-c496891ef112", "b65bc280-c7a5-8006-8008-c4968927a3dc", "b65bc280-c7a5-8006-8008-c49689328148", "b65bc280-c7a5-8006-8008-c496893b684c"], "mutatedNodeIds": [], "admissionEligible": false, "baselineCalibration": "NOT_RUN", "fidelityGate": "NOT_RUN"}, {"status": "CANDIDATE_CREATED", "platform": "penpot", "fileReference": "91396aad-60c8-808b-8008-c0885ca79899", "pageReference": "b65bc280-c7a5-8006-8008-c496888c78a0", "componentReference": "b65bc280-c7a5-8006-8008-c4968b8d6f20", "mainReference": "b65bc280-c7a5-8006-8008-c49689998f9c", "textReference": "b65bc280-c7a5-8006-8008-c49689b1ac31", "textReferences": ["b65bc280-c7a5-8006-8008-c49689b1ac31", "b65bc280-c7a5-8006-8008-c49689c940d3", "b65bc280-c7a5-8006-8008-c49689e0f949", "b65bc280-c7a5-8006-8008-c49689f89154", "b65bc280-c7a5-8006-8008-c4968a1eb254", "b65bc280-c7a5-8006-8008-c4968a34b388", "b65bc280-c7a5-8006-8008-c4968a4caa14", "b65bc280-c7a5-8006-8008-c4968a626442", "b65bc280-c7a5-8006-8008-c4968a87f687", "b65bc280-c7a5-8006-8008-c4968a9d85ef", "b65bc280-c7a5-8006-8008-c4968ab1f665", "b65bc280-c7a5-8006-8008-c4968ad03107", "b65bc280-c7a5-8006-8008-c4968b207973", "b65bc280-c7a5-8006-8008-c4968b38b0d7", "b65bc280-c7a5-8006-8008-c4968b52cbc5", "b65bc280-c7a5-8006-8008-c4968b6d17e4"], "logicalId": "data.table.config.b3eb343b6ad2c8cd567a53f7d65703db6627cb9e7e1bfaedfb3098baf7af8122", "componentIrSha256": "d2a59922bf0203a1fde62b376868d323cbc49f1954d41e44f113174412c8183e", "createdNodeIds": ["b65bc280-c7a5-8006-8008-c49689998f9c", "b65bc280-c7a5-8006-8008-c49689a11fec", "b65bc280-c7a5-8006-8008-c49689a802ac", "b65bc280-c7a5-8006-8008-c49689b1ac31", "b65bc280-c7a5-8006-8008-c49689bfbaad", "b65bc280-c7a5-8006-8008-c49689c940d3", "b65bc280-c7a5-8006-8008-c49689d7f7da", "b65bc280-c7a5-8006-8008-c49689e0f949", "b65bc280-c7a5-8006-8008-c49689f13bbf", "b65bc280-c7a5-8006-8008-c49689f89154", "b65bc280-c7a5-8006-8008-c4968a057dae", "b65bc280-c7a5-8006-8008-c4968a0f2061", "b65bc280-c7a5-8006-8008-c4968a170736", "b65bc280-c7a5-8006-8008-c4968a1eb254", "b65bc280-c7a5-8006-8008-c4968a2beb80", "b65bc280-c7a5-8006-8008-c4968a34b388", "b65bc280-c7a5-8006-8008-c4968a43485c", "b65bc280-c7a5-8006-8008-c4968a4caa14", "b65bc280-c7a5-8006-8008-c4968a5b34ea", "b65bc280-c7a5-8006-8008-c4968a626442", "b65bc280-c7a5-8006-8008-c4968a6fbf36", "b65bc280-c7a5-8006-8008-c4968a775813", "b65bc280-c7a5-8006-8008-c4968a7fb84e", "b65bc280-c7a5-8006-8008-c4968a87f687", "b65bc280-c7a5-8006-8008-c4968a95bef5", "b65bc280-c7a5-8006-8008-c4968a9d85ef", "b65bc280-c7a5-8006-8008-c4968aaa284d", "b65bc280-c7a5-8006-8008-c4968ab1f665", "b65bc280-c7a5-8006-8008-c4968ac083c3", "b65bc280-c7a5-8006-8008-c4968ad03107", "b65bc280-c7a5-8006-8008-c4968af8e4f9", "b65bc280-c7a5-8006-8008-c4968b0ad9ea", "b65bc280-c7a5-8006-8008-c4968b160a56", "b65bc280-c7a5-8006-8008-c4968b207973", "b65bc280-c7a5-8006-8008-c4968b2f50b1", "b65bc280-c7a5-8006-8008-c4968b38b0d7", "b65bc280-c7a5-8006-8008-c4968b4941dd", "b65bc280-c7a5-8006-8008-c4968b52cbc5", "b65bc280-c7a5-8006-8008-c4968b620c74", "b65bc280-c7a5-8006-8008-c4968b6d17e4", "b65bc280-c7a5-8006-8008-c4968b7af8a2", "b65bc280-c7a5-8006-8008-c4968b84b44e"], "mutatedNodeIds": [], "admissionEligible": false, "baselineCalibration": "NOT_RUN", "fidelityGate": "NOT_RUN"}], "createdNodeIds": ["b65bc280-c7a5-8006-8008-c496888c78a0", "b65bc280-c7a5-8006-8008-c49688a06509", "b65bc280-c7a5-8006-8008-c49688c69e37", "b65bc280-c7a5-8006-8008-c49688d24973", "b65bc280-c7a5-8006-8008-c49688d9eaf7", "b65bc280-c7a5-8006-8008-c49688e89922", "b65bc280-c7a5-8006-8008-c49688efc657", "b65bc280-c7a5-8006-8008-c49688fbb3a9", "b65bc280-c7a5-8006-8008-c49689045759", "b65bc280-c7a5-8006-8008-c496890abd6a", "b65bc280-c7a5-8006-8008-c49689120844", "b65bc280-c7a5-8006-8008-c496891ef112", "b65bc280-c7a5-8006-8008-c4968927a3dc", "b65bc280-c7a5-8006-8008-c49689328148", "b65bc280-c7a5-8006-8008-c496893b684c", "b65bc280-c7a5-8006-8008-c49689998f9c", "b65bc280-c7a5-8006-8008-c49689a11fec", "b65bc280-c7a5-8006-8008-c49689a802ac", "b65bc280-c7a5-8006-8008-c49689b1ac31", "b65bc280-c7a5-8006-8008-c49689bfbaad", "b65bc280-c7a5-8006-8008-c49689c940d3", "b65bc280-c7a5-8006-8008-c49689d7f7da", "b65bc280-c7a5-8006-8008-c49689e0f949", "b65bc280-c7a5-8006-8008-c49689f13bbf", "b65bc280-c7a5-8006-8008-c49689f89154", "b65bc280-c7a5-8006-8008-c4968a057dae", "b65bc280-c7a5-8006-8008-c4968a0f2061", "b65bc280-c7a5-8006-8008-c4968a170736", "b65bc280-c7a5-8006-8008-c4968a1eb254", "b65bc280-c7a5-8006-8008-c4968a2beb80", "b65bc280-c7a5-8006-8008-c4968a34b388", "b65bc280-c7a5-8006-8008-c4968a43485c", "b65bc280-c7a5-8006-8008-c4968a4caa14", "b65bc280-c7a5-8006-8008-c4968a5b34ea", "b65bc280-c7a5-8006-8008-c4968a626442", "b65bc280-c7a5-8006-8008-c4968a6fbf36", "b65bc280-c7a5-8006-8008-c4968a775813", "b65bc280-c7a5-8006-8008-c4968a7fb84e", "b65bc280-c7a5-8006-8008-c4968a87f687", "b65bc280-c7a5-8006-8008-c4968a95bef5", "b65bc280-c7a5-8006-8008-c4968a9d85ef", "b65bc280-c7a5-8006-8008-c4968aaa284d", "b65bc280-c7a5-8006-8008-c4968ab1f665", "b65bc280-c7a5-8006-8008-c4968ac083c3", "b65bc280-c7a5-8006-8008-c4968ad03107", "b65bc280-c7a5-8006-8008-c4968af8e4f9", "b65bc280-c7a5-8006-8008-c4968b0ad9ea", "b65bc280-c7a5-8006-8008-c4968b160a56", "b65bc280-c7a5-8006-8008-c4968b207973", "b65bc280-c7a5-8006-8008-c4968b2f50b1", "b65bc280-c7a5-8006-8008-c4968b38b0d7", "b65bc280-c7a5-8006-8008-c4968b4941dd", "b65bc280-c7a5-8006-8008-c4968b52cbc5", "b65bc280-c7a5-8006-8008-c4968b620c74", "b65bc280-c7a5-8006-8008-c4968b6d17e4", "b65bc280-c7a5-8006-8008-c4968b7af8a2", "b65bc280-c7a5-8006-8008-c4968b84b44e"], "createdComponentIds": ["b65bc280-c7a5-8006-8008-c496894279a2", "b65bc280-c7a5-8006-8008-c4968b8d6f20"], "mutatedNodeIds": [], "admissionEligible": false, "fidelityGate": "NOT_RUN"};
penpot.ui.onMessage(async message=>{
      if(!['table-create','table-capture-0','table-capture-1','table-refresh-fonts'].includes(message?.type))return;
      let created=[];let mutated=[];let candidates=[];
      try{
        if(penpot.currentFile?.id!==targetFile)throw new Error('target_file_mismatch');
        let result;
        if(message.type==='table-create'){
          if(tableExecution)throw new Error('table_existing_execution_requires_recovery');
          if(penpot.currentFile.pages.some(p=>p.name==='task019-configurable-table-candidates'))throw new Error('table_existing_page_requires_recovery');
          for(const spec of tableSpecs)for(const family of spec.requiredFonts){
            const fonts=penpot.fonts.all.filter(f=>f.fontFamily===family);
            if(fonts.length!==1)throw new Error('missing_or_ambiguous_source_font:'+family);
            selectExactPenpotVariant(fonts[0],400);
          }
          const page=penpot.createPage();created.push(page.id);page.name='task019-configurable-table-candidates';await penpot.openPage(page);
          for(const original of tableSpecs){const spec={...original,pageReference:page.id};
            const candidate=await buildConfigurablePenpotTableCandidate(penpot,spec);candidates.push(candidate);created.push(...candidate.createdNodeIds);
            if(candidate.status!=='CANDIDATE_CREATED')throw new Error('candidate_creation_failed');
          }
          result=tableExecution={status:'CREATED',fileReference:targetFile,pageReference:page.id,candidates,createdNodeIds:created,createdComponentIds:candidates.map(c=>c.componentReference),mutatedNodeIds:[],admissionEligible:false,fidelityGate:'NOT_RUN'};
        }else if(message.type==='table-refresh-fonts'){
          if(tableExecution?.status!=='CREATED'||penpot.currentPage.id!==tableExecution.pageReference)throw new Error('table_execution_required');
          const observed=[];
          for(let i=0;i<tableSpecs.length;i++){
            const candidate=tableExecution.candidates[i],main=penpot.currentPage.getShapeById(candidate.mainReference);
            if(!main?.isComponentMainInstance())throw new Error('table_main_instance_required');
            for(const row of tableSpecs[i].rows)for(const cell of row.cells){
              const item=cell.text;
              const text=candidate.textReferences.map(id=>penpot.currentPage.getShapeById(id)).find(t=>t?.name.replace(/\s*\/\s*/g,'/')==='official-source/'+item.path);
              if(!text||text.characters!==item.characters||text.fontFamily!==item.fontFamily)throw new Error('table_font_refresh_source_mismatch');
              const range=text.getRange(0,text.characters.length);
              observed.push({textReference:text.id,characters:text.characters,sourceFontFamily:item.fontFamily,beforeRange:{fontId:range.fontId,fontFamily:range.fontFamily,fontVariantId:range.fontVariantId,fontSize:range.fontSize,fontWeight:range.fontWeight,lineHeight:range.lineHeight,letterSpacing:range.letterSpacing}});
            }
          }
          // Apply the same bound font to the complete public text range. No
          // geometry offsets, tracking changes or source text substitutions.
          for(const row of observed){const text=penpot.currentPage.getShapeById(row.textReference),font=penpot.fonts.findById(text.fontId);
            if(!font||font.fontFamily!==row.sourceFontFamily)throw new Error('table_exact_source_font_missing');
            font.applyToRange(text.getRange(0,text.characters.length),selectExactPenpotVariant(font,400));
            mutated.push(text.id);
          }
          await penpot.waitForLayoutUpdate();
          for(const row of observed){const text=penpot.currentPage.getShapeById(row.textReference),range=text.getRange(0,text.characters.length);
            if(typeof text.waitForLayoutUpdate==='function')await text.waitForLayoutUpdate(15000);
            row.afterRange={fontId:range.fontId,fontFamily:range.fontFamily,fontVariantId:range.fontVariantId,fontSize:range.fontSize,fontWeight:range.fontWeight,lineHeight:range.lineHeight,letterSpacing:range.letterSpacing};
          }
          result={status:'FONT_RANGE_REAPPLIED',fileReference:targetFile,pageReference:tableExecution.pageReference,createdNodeIds:[],mutatedNodeIds:observed.map(r=>r.textReference),observations:observed,fidelityGate:'NOT_RUN',admissionEligible:false};
        }else{
          if(tableExecution?.status!=='CREATED')throw new Error('table_execution_required');
          const index=message.type.endsWith('0')?0:1;
          result=await captureConfigurablePenpotTable(penpot,{...tableSpecs[index],...tableExecution.candidates[index]});
        }
        penpot.ui.sendMessage({type:'task010-result',status:result.status==='FAIL'?'FAIL':'CAPTURED',result});
      }catch(error){penpot.ui.sendMessage({type:'task010-result',status:'FAIL',error:String(error),result:{status:'FAIL',fileReference:targetFile,createdNodeIds:created,candidates,mutatedNodeIds:mutated,admissionEligible:false,fidelityGate:'NOT_RUN'}});}
    });