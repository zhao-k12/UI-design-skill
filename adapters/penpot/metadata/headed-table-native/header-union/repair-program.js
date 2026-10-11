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
async function buildHeadedPenpotTableCandidate(api,spec) {
  if(api.currentFile?.id!==spec.fileReference||api.currentPage?.id!==spec.pageReference||!/^data\.table\.headed\.[a-f0-9]{64}$/.test(spec.logicalId))throw new Error('candidate_context_mismatch');
  const exists=name=>typeof name==='string'&&name.includes(spec.logicalId)&&name.replace(/\s*\/\s*/g,'/').endsWith('/penpot-v1');
  if(api.currentPage.root.children.some(n=>exists(n.name))||api.library.local.components.some(c=>exists(c.mainInstance()?.name)))throw new Error('candidate_requires_recovery');
  const fontMap=new Map();
  for(const family of spec.requiredFonts){const fonts=api.fonts.all.filter(f=>f.fontFamily===family);if(fonts.length!==1)throw new Error('candidate_exact_font_missing_or_ambiguous:'+family);const font=fonts[0];for(const weight of [...new Set(spec.rows.flatMap(r=>r.cells).filter(c=>c.text.fontFamily===family).map(c=>c.text.fontWeight))])fontMap.set(family+'/'+weight,{font,variant:selectExactPenpotVariant(font,weight)});}
  const created=[],textReferences=[];let component;
  const record=n=>{created.push(n.id);return n;};
  try {
    const root=record(api.createBoard());api.currentPage.root.appendChild(root);root.name=spec.name;
    root.resize(spec.rootBounds.width,spec.rootBounds.height);root.x=Math.max(0,...api.currentPage.root.children.filter(n=>n.id!==root.id).map(n=>n.x+n.width))+80;root.y=320;root.clipContent=true;root.opacity=1;root.fills=[{fillColor:spec.rootFill,fillOpacity:1}];root.strokes=[];root.borderRadius=0;
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
        const binding=fontMap.get(item.fontFamily+'/'+item.fontWeight);if(!binding)throw new Error('unplanned_table_font');binding.font.applyToText(text,binding.variant);text.fontSize=String(item.fontSize);text.lineHeight=String(item.sourceTextBounds.height/item.fontSize);
        text.letterSpacing='0';text.growType='fixed';text.verticalAlign='top';text.align='left';text.opacity=1;text.strokes=[];
        text.fills=[{fillColor:item.fill,fillOpacity:1}];cellNode.appendChild(text);text.resize(item.sourceTextBounds.width,item.sourceTextBounds.height);
        text.x=root.x+item.sourceTextBounds.x;text.y=root.y+item.sourceTextBounds.y;text.name='official-source/'+item.path;
        if(text.fontFamily!==item.fontFamily||Number(text.fontWeight)!==item.fontWeight)throw new Error('candidate_font_readback_mismatch');
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
async function captureHeadedPenpotTable(api, request) {
  if(api.currentFile?.id!==request.fileReference || api.currentPage?.id!==request.pageReference)throw new Error('candidate_capture_context_mismatch');
  const component=api.library.local.components.find(c=>c.id===request.componentReference);
  const main=component?.mainInstance(),text=api.currentPage.getShapeById(request.textReference);
  if(!main || main.id!==request.mainReference || !main.isComponentMainInstance() || !text || text.type!=='text')throw new Error('candidate_capture_identity_mismatch');
  let ancestor=text;while(ancestor && ancestor.id!==main.id)ancestor=ancestor.parent;
  if(!ancestor)throw new Error('candidate_capture_text_outside_component');
  const texts=request.textReferences?request.textReferences.map(id=>api.currentPage.getShapeById(id)):[text];
  if(/^data\.table\.headed\.[a-f0-9]{64}$/.test(request.logicalId)){
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


// The host supplies independently source-verified, approval-bound unions.
async function repairHeadedTableHeaders(api, specs, execution) {
  if(execution?.status!=='CREATED'||api.currentFile?.id!==execution.fileReference||api.currentPage?.id!==execution.pageReference)throw new Error('headed_repair_context_mismatch');
  const observations=[];
  for(let i=0;i<specs.length;i++){
    const spec=specs[i],candidate=execution.candidates[i],union=spec.headerBackgroundUnion;
    if(!union||candidate.logicalId!==spec.logicalId||candidate.componentIrSha256!==spec.componentIrSha256)throw new Error('headed_repair_source_mismatch');
    const main=api.currentPage.getShapeById(candidate.mainReference);
    if(!main?.isComponentMainInstance()||main.width!==spec.rootBounds.width||main.height!==spec.rootBounds.height||!main.clipContent)throw new Error('headed_repair_main_mismatch');
    const normalize=name=>name.replace(/\s*\/\s*/g,'/');
    const rows=main.children.filter(n=>normalize(n.name)==='official-source/'+union.rowPath);
    if(rows.length!==1)throw new Error('headed_repair_row_ambiguous');
    const row=rows[0],b=union.bounds;
    if(row.type!=='board'||row.x-main.x!==b.x||row.y-main.y!==b.y||row.width!==b.width||row.height!==b.height||row.opacity!==1||row.clipContent||row.strokes.length||row.borderRadius!==0)throw new Error('headed_repair_row_geometry_mismatch');
    const exactFill=n=>n.fills.length===1&&n.fills[0].fillColor===union.fill&&n.fills[0].fillOpacity===1&&!n.fills[0].fillColorGradient&&!n.fills[0].fillImage;
    if(row.fills.length&&!exactFill(row))throw new Error('headed_repair_existing_fill_mismatch');
    for(const cell of spec.rows[0].cells){
      const matches=row.children.filter(n=>normalize(n.name)==='official-source/'+cell.path);
      const n=matches[0],c=cell.bounds;
      if(matches.length!==1||n.type!=='board'||n.x-main.x!==c.x||n.y-main.y!==c.y||n.width!==c.width||n.height!==c.height||n.opacity!==1||!exactFill(n))throw new Error('headed_repair_cell_mismatch');
    }
    observations.push({logicalId:spec.logicalId,mainReference:main.id,rowReference:row.id,union,beforeFills:JSON.parse(JSON.stringify(row.fills))});
  }
  const mutated=[];
  for(const item of observations){const row=api.currentPage.getShapeById(item.rowReference);row.fills=[{fillColor:item.union.fill,fillOpacity:1}];mutated.push(row.id);}
  await api.waitForLayoutUpdate();
  for(const item of observations)item.afterFills=JSON.parse(JSON.stringify(api.currentPage.getShapeById(item.rowReference).fills));
  return {status:'HEADER_UNION_RESTORED',fileReference:execution.fileReference,pageReference:execution.pageReference,observations,createdNodeIds:[],mutatedNodeIds:mutated,fidelityGate:'NOT_RUN',admissionEligible:false};
}

const tableSpecs=[{"logicalId": "data.table.headed.613acb453dafc1629920ac3d697c42918bef2d556cc6f7e61648523f1f7f24aa", "sourceVersion": "view-ui-plus@1.3.24+23a8e5bd2c07143bebfbcadcfb30d6f5bd47834b", "componentIrSha256": "b71439e9d1ee3c80b61c21d8ed864bbcb7ff462d9fee9e8dc298b5ee53a002c1", "rootBounds": {"width": 720, "height": 134.875}, "rootFill": "#ffffff", "rootFillSourcePath": "0.0", "rows": [{"path": "0.0.0.0.1.0", "bounds": {"x": 0, "y": 0, "width": 721, "height": 38.875}, "cells": [{"path": "0.0.0.0.1.0.0", "bounds": {"x": 0, "y": 0, "width": 240.328125, "height": 38.875}, "fill": "#f8f8f9", "text": {"path": "0.0.0.0.1.0.0.0.0", "characters": "姓名", "sourceTextBounds": {"x": 18, "y": 10.875, "width": 28, "height": 16}, "sourceSizing": {"display": "inline", "width": "auto", "height": "auto"}, "fontSize": 14, "fontWeight": 600, "sourceCssFontWeight": 700, "role": "header", "fontFamily": "PingFang SC", "postScriptName": "PingFangSC-Semibold", "fill": "#515a6e", "sourceBaselineY": 23.875}, "bottomBorder": {"height": 1.0, "fill": "#e8eaec"}}, {"path": "0.0.0.0.1.0.1", "bounds": {"x": 240.328125, "y": 0, "width": 480.671875, "height": 38.875}, "fill": "#f8f8f9", "text": {"path": "0.0.0.0.1.0.1.0.0", "characters": "邮箱", "sourceTextBounds": {"x": 258.328125, "y": 10.875, "width": 28, "height": 16}, "sourceSizing": {"display": "inline", "width": "auto", "height": "auto"}, "fontSize": 14, "fontWeight": 600, "sourceCssFontWeight": 700, "role": "header", "fontFamily": "PingFang SC", "postScriptName": "PingFangSC-Semibold", "fill": "#515a6e", "sourceBaselineY": 23.875}, "bottomBorder": {"height": 1.0, "fill": "#e8eaec"}}], "bottomBorder": {"height": 1.0, "fill": "#e8eaec"}}, {"path": "0.0.1.0.1.0", "bounds": {"x": 0, "y": 38.875, "width": 721, "height": 48}, "cells": [{"path": "0.0.1.0.1.0.0", "bounds": {"x": 0, "y": 38.875, "width": 240.328125, "height": 48}, "fill": "#ffffff", "text": {"path": "0.0.1.0.1.0.0.0.0", "characters": "赵六", "sourceTextBounds": {"x": 18, "y": 53.875, "width": 28, "height": 16}, "sourceSizing": {"display": "inline", "width": "auto", "height": "auto"}, "fontSize": 14, "fontWeight": 400, "sourceCssFontWeight": 400, "role": "body", "fontFamily": "PingFang SC", "postScriptName": "PingFangSC-Regular", "fill": "#515a6e", "sourceBaselineY": 66.875}, "bottomBorder": {"height": 1.0, "fill": "#e8eaec"}}, {"path": "0.0.1.0.1.0.1", "bounds": {"x": 240.328125, "y": 38.875, "width": 480.671875, "height": 48}, "fill": "#ffffff", "text": {"path": "0.0.1.0.1.0.1.0.0", "characters": "zhao@example.com", "sourceTextBounds": {"x": 258.328125, "y": 53.875, "width": 127.828125, "height": 16}, "sourceSizing": {"display": "inline", "width": "auto", "height": "auto"}, "fontSize": 14, "fontWeight": 400, "sourceCssFontWeight": 400, "role": "body", "fontFamily": "Arial", "postScriptName": "ArialMT", "fill": "#515a6e", "sourceBaselineY": 66.875}, "bottomBorder": {"height": 1.0, "fill": "#e8eaec"}}], "bottomBorder": {"height": 1.0, "fill": "#e8eaec"}}, {"path": "0.0.1.0.1.1", "bounds": {"x": 0, "y": 86.875, "width": 721, "height": 48}, "cells": [{"path": "0.0.1.0.1.1.0", "bounds": {"x": 0, "y": 86.875, "width": 240.328125, "height": 48}, "fill": "#ffffff", "text": {"path": "0.0.1.0.1.1.0.0.0", "characters": "钱七", "sourceTextBounds": {"x": 18, "y": 101.875, "width": 28, "height": 16}, "sourceSizing": {"display": "inline", "width": "auto", "height": "auto"}, "fontSize": 14, "fontWeight": 400, "sourceCssFontWeight": 400, "role": "body", "fontFamily": "PingFang SC", "postScriptName": "PingFangSC-Regular", "fill": "#515a6e", "sourceBaselineY": 114.875}, "bottomBorder": {"height": 1.0, "fill": "#e8eaec"}}, {"path": "0.0.1.0.1.1.1", "bounds": {"x": 240.328125, "y": 86.875, "width": 480.671875, "height": 48}, "fill": "#ffffff", "text": {"path": "0.0.1.0.1.1.1.0.0", "characters": "qian@example.com", "sourceTextBounds": {"x": 258.328125, "y": 101.875, "width": 123.9375, "height": 16}, "sourceSizing": {"display": "inline", "width": "auto", "height": "auto"}, "fontSize": 14, "fontWeight": 400, "sourceCssFontWeight": 400, "role": "body", "fontFamily": "Arial", "postScriptName": "ArialMT", "fill": "#515a6e", "sourceBaselineY": 114.875}, "bottomBorder": {"height": 1.0, "fill": "#e8eaec"}}], "bottomBorder": {"height": 1.0, "fill": "#e8eaec"}}], "sourceObservationSha256": "ac3ca5d3358e6b052b6a1c60c8036f5fae98c5cf4a1c189ecea0b05d8ac1cdbc", "requiredFonts": ["Arial", "PingFang SC"], "bottomPseudo": {"height": 1.0, "width": 720.0, "fill": "#dcdee2", "sourceCssRule": ".ivu-table:before{content:'';width:100%;height:1px;position:absolute;left:0;bottom:0;background-color:#dcdee2;z-index:4}"}, "admissionEligible": false, "fidelityGate": "NOT_RUN", "fileReference": "91396aad-60c8-808b-8008-c0885ca79899", "pageReference": null, "name": "candidate/data.table.headed.613acb453dafc1629920ac3d697c42918bef2d556cc6f7e61648523f1f7f24aa/penpot-v1", "headerBackgroundUnion": {"decisionSha256": "16ccb7f958dda5f6e8933e081d893080b0d924785ee8e3de8d87d9e8cb1e97aa", "rowPath": "0.0.0.0.1.0", "bounds": {"x": 0, "y": 0, "width": 721, "height": 38.875}, "fill": "#f8f8f9", "opacity": 1, "cellPaths": ["0.0.0.0.1.0.0", "0.0.0.0.1.0.1"], "fidelityGate": "NOT_RUN", "productionAdmission": false}}, {"logicalId": "data.table.headed.5eca5bc513698ad31a2d57d0660cebee6ef0536e196c5ed468f8153f52b90c25", "sourceVersion": "view-ui-plus@1.3.24+23a8e5bd2c07143bebfbcadcfb30d6f5bd47834b", "componentIrSha256": "8b14f33d3468b3372046aa2a533824173cc26bd1e9e3990af1b8c202dbd10771", "rootBounds": {"width": 960, "height": 230.875}, "rootFill": "#ffffff", "rootFillSourcePath": "0.0", "rows": [{"path": "0.0.0.0.1.0", "bounds": {"x": 0, "y": 0, "width": 961, "height": 38.875}, "cells": [{"path": "0.0.0.0.1.0.0", "bounds": {"x": 0, "y": 0, "width": 160.15625, "height": 38.875}, "fill": "#f8f8f9", "text": {"path": "0.0.0.0.1.0.0.0.0", "characters": "编号", "sourceTextBounds": {"x": 18, "y": 10.875, "width": 28, "height": 16}, "sourceSizing": {"display": "inline", "width": "auto", "height": "auto"}, "fontSize": 14, "fontWeight": 600, "sourceCssFontWeight": 700, "role": "header", "fontFamily": "PingFang SC", "postScriptName": "PingFangSC-Semibold", "fill": "#515a6e", "sourceBaselineY": 23.875}, "bottomBorder": {"height": 1.0, "fill": "#e8eaec"}}, {"path": "0.0.0.0.1.0.1", "bounds": {"x": 160.15625, "y": 0, "width": 240.25, "height": 38.875}, "fill": "#f8f8f9", "text": {"path": "0.0.0.0.1.0.1.0.0", "characters": "姓名", "sourceTextBounds": {"x": 178.15625, "y": 10.875, "width": 28, "height": 16}, "sourceSizing": {"display": "inline", "width": "auto", "height": "auto"}, "fontSize": 14, "fontWeight": 600, "sourceCssFontWeight": 700, "role": "header", "fontFamily": "PingFang SC", "postScriptName": "PingFangSC-Semibold", "fill": "#515a6e", "sourceBaselineY": 23.875}, "bottomBorder": {"height": 1.0, "fill": "#e8eaec"}}, {"path": "0.0.0.0.1.0.2", "bounds": {"x": 400.40625, "y": 0, "width": 320.328125, "height": 38.875}, "fill": "#f8f8f9", "text": {"path": "0.0.0.0.1.0.2.0.0", "characters": "部门", "sourceTextBounds": {"x": 418.40625, "y": 10.875, "width": 28, "height": 16}, "sourceSizing": {"display": "inline", "width": "auto", "height": "auto"}, "fontSize": 14, "fontWeight": 600, "sourceCssFontWeight": 700, "role": "header", "fontFamily": "PingFang SC", "postScriptName": "PingFangSC-Semibold", "fill": "#515a6e", "sourceBaselineY": 23.875}, "bottomBorder": {"height": 1.0, "fill": "#e8eaec"}}, {"path": "0.0.0.0.1.0.3", "bounds": {"x": 720.734375, "y": 0, "width": 240.265625, "height": 38.875}, "fill": "#f8f8f9", "text": {"path": "0.0.0.0.1.0.3.0.0", "characters": "状态", "sourceTextBounds": {"x": 738.734375, "y": 10.875, "width": 28, "height": 16}, "sourceSizing": {"display": "inline", "width": "auto", "height": "auto"}, "fontSize": 14, "fontWeight": 600, "sourceCssFontWeight": 700, "role": "header", "fontFamily": "PingFang SC", "postScriptName": "PingFangSC-Semibold", "fill": "#515a6e", "sourceBaselineY": 23.875}, "bottomBorder": {"height": 1.0, "fill": "#e8eaec"}}], "bottomBorder": {"height": 1.0, "fill": "#e8eaec"}}, {"path": "0.0.1.0.1.0", "bounds": {"x": 0, "y": 38.875, "width": 961, "height": 48}, "cells": [{"path": "0.0.1.0.1.0.0", "bounds": {"x": 0, "y": 38.875, "width": 160.15625, "height": 48}, "fill": "#ffffff", "text": {"path": "0.0.1.0.1.0.0.0.0", "characters": "001", "sourceTextBounds": {"x": 18, "y": 53.875, "width": 23.359375, "height": 16}, "sourceSizing": {"display": "inline", "width": "auto", "height": "auto"}, "fontSize": 14, "fontWeight": 400, "sourceCssFontWeight": 400, "role": "body", "fontFamily": "Arial", "postScriptName": "ArialMT", "fill": "#515a6e", "sourceBaselineY": 66.875}, "bottomBorder": {"height": 1.0, "fill": "#e8eaec"}}, {"path": "0.0.1.0.1.0.1", "bounds": {"x": 160.15625, "y": 38.875, "width": 240.25, "height": 48}, "fill": "#ffffff", "text": {"path": "0.0.1.0.1.0.1.0.0", "characters": "张三", "sourceTextBounds": {"x": 178.15625, "y": 53.875, "width": 28, "height": 16}, "sourceSizing": {"display": "inline", "width": "auto", "height": "auto"}, "fontSize": 14, "fontWeight": 400, "sourceCssFontWeight": 400, "role": "body", "fontFamily": "PingFang SC", "postScriptName": "PingFangSC-Regular", "fill": "#515a6e", "sourceBaselineY": 66.875}, "bottomBorder": {"height": 1.0, "fill": "#e8eaec"}}, {"path": "0.0.1.0.1.0.2", "bounds": {"x": 400.40625, "y": 38.875, "width": 320.328125, "height": 48}, "fill": "#ffffff", "text": {"path": "0.0.1.0.1.0.2.0.0", "characters": "研发", "sourceTextBounds": {"x": 418.40625, "y": 53.875, "width": 28, "height": 16}, "sourceSizing": {"display": "inline", "width": "auto", "height": "auto"}, "fontSize": 14, "fontWeight": 400, "sourceCssFontWeight": 400, "role": "body", "fontFamily": "PingFang SC", "postScriptName": "PingFangSC-Regular", "fill": "#515a6e", "sourceBaselineY": 66.875}, "bottomBorder": {"height": 1.0, "fill": "#e8eaec"}}, {"path": "0.0.1.0.1.0.3", "bounds": {"x": 720.734375, "y": 38.875, "width": 240.265625, "height": 48}, "fill": "#ffffff", "text": {"path": "0.0.1.0.1.0.3.0.0", "characters": "启用", "sourceTextBounds": {"x": 738.734375, "y": 53.875, "width": 28, "height": 16}, "sourceSizing": {"display": "inline", "width": "auto", "height": "auto"}, "fontSize": 14, "fontWeight": 400, "sourceCssFontWeight": 400, "role": "body", "fontFamily": "PingFang SC", "postScriptName": "PingFangSC-Regular", "fill": "#515a6e", "sourceBaselineY": 66.875}, "bottomBorder": {"height": 1.0, "fill": "#e8eaec"}}], "bottomBorder": {"height": 1.0, "fill": "#e8eaec"}}, {"path": "0.0.1.0.1.1", "bounds": {"x": 0, "y": 86.875, "width": 961, "height": 48}, "cells": [{"path": "0.0.1.0.1.1.0", "bounds": {"x": 0, "y": 86.875, "width": 160.15625, "height": 48}, "fill": "#ffffff", "text": {"path": "0.0.1.0.1.1.0.0.0", "characters": "002", "sourceTextBounds": {"x": 18, "y": 101.875, "width": 23.359375, "height": 16}, "sourceSizing": {"display": "inline", "width": "auto", "height": "auto"}, "fontSize": 14, "fontWeight": 400, "sourceCssFontWeight": 400, "role": "body", "fontFamily": "Arial", "postScriptName": "ArialMT", "fill": "#515a6e", "sourceBaselineY": 114.875}, "bottomBorder": {"height": 1.0, "fill": "#e8eaec"}}, {"path": "0.0.1.0.1.1.1", "bounds": {"x": 160.15625, "y": 86.875, "width": 240.25, "height": 48}, "fill": "#ffffff", "text": {"path": "0.0.1.0.1.1.1.0.0", "characters": "李四", "sourceTextBounds": {"x": 178.15625, "y": 101.875, "width": 28, "height": 16}, "sourceSizing": {"display": "inline", "width": "auto", "height": "auto"}, "fontSize": 14, "fontWeight": 400, "sourceCssFontWeight": 400, "role": "body", "fontFamily": "PingFang SC", "postScriptName": "PingFangSC-Regular", "fill": "#515a6e", "sourceBaselineY": 114.875}, "bottomBorder": {"height": 1.0, "fill": "#e8eaec"}}, {"path": "0.0.1.0.1.1.2", "bounds": {"x": 400.40625, "y": 86.875, "width": 320.328125, "height": 48}, "fill": "#ffffff", "text": {"path": "0.0.1.0.1.1.2.0.0", "characters": "财务", "sourceTextBounds": {"x": 418.40625, "y": 101.875, "width": 28, "height": 16}, "sourceSizing": {"display": "inline", "width": "auto", "height": "auto"}, "fontSize": 14, "fontWeight": 400, "sourceCssFontWeight": 400, "role": "body", "fontFamily": "PingFang SC", "postScriptName": "PingFangSC-Regular", "fill": "#515a6e", "sourceBaselineY": 114.875}, "bottomBorder": {"height": 1.0, "fill": "#e8eaec"}}, {"path": "0.0.1.0.1.1.3", "bounds": {"x": 720.734375, "y": 86.875, "width": 240.265625, "height": 48}, "fill": "#ffffff", "text": {"path": "0.0.1.0.1.1.3.0.0", "characters": "停用", "sourceTextBounds": {"x": 738.734375, "y": 101.875, "width": 28, "height": 16}, "sourceSizing": {"display": "inline", "width": "auto", "height": "auto"}, "fontSize": 14, "fontWeight": 400, "sourceCssFontWeight": 400, "role": "body", "fontFamily": "PingFang SC", "postScriptName": "PingFangSC-Regular", "fill": "#515a6e", "sourceBaselineY": 114.875}, "bottomBorder": {"height": 1.0, "fill": "#e8eaec"}}], "bottomBorder": {"height": 1.0, "fill": "#e8eaec"}}, {"path": "0.0.1.0.1.2", "bounds": {"x": 0, "y": 134.875, "width": 961, "height": 48}, "cells": [{"path": "0.0.1.0.1.2.0", "bounds": {"x": 0, "y": 134.875, "width": 160.15625, "height": 48}, "fill": "#ffffff", "text": {"path": "0.0.1.0.1.2.0.0.0", "characters": "003", "sourceTextBounds": {"x": 18, "y": 149.875, "width": 23.359375, "height": 16}, "sourceSizing": {"display": "inline", "width": "auto", "height": "auto"}, "fontSize": 14, "fontWeight": 400, "sourceCssFontWeight": 400, "role": "body", "fontFamily": "Arial", "postScriptName": "ArialMT", "fill": "#515a6e", "sourceBaselineY": 162.875}, "bottomBorder": {"height": 1.0, "fill": "#e8eaec"}}, {"path": "0.0.1.0.1.2.1", "bounds": {"x": 160.15625, "y": 134.875, "width": 240.25, "height": 48}, "fill": "#ffffff", "text": {"path": "0.0.1.0.1.2.1.0.0", "characters": "王五", "sourceTextBounds": {"x": 178.15625, "y": 149.875, "width": 28, "height": 16}, "sourceSizing": {"display": "inline", "width": "auto", "height": "auto"}, "fontSize": 14, "fontWeight": 400, "sourceCssFontWeight": 400, "role": "body", "fontFamily": "PingFang SC", "postScriptName": "PingFangSC-Regular", "fill": "#515a6e", "sourceBaselineY": 162.875}, "bottomBorder": {"height": 1.0, "fill": "#e8eaec"}}, {"path": "0.0.1.0.1.2.2", "bounds": {"x": 400.40625, "y": 134.875, "width": 320.328125, "height": 48}, "fill": "#ffffff", "text": {"path": "0.0.1.0.1.2.2.0.0", "characters": "运营", "sourceTextBounds": {"x": 418.40625, "y": 149.875, "width": 28, "height": 16}, "sourceSizing": {"display": "inline", "width": "auto", "height": "auto"}, "fontSize": 14, "fontWeight": 400, "sourceCssFontWeight": 400, "role": "body", "fontFamily": "PingFang SC", "postScriptName": "PingFangSC-Regular", "fill": "#515a6e", "sourceBaselineY": 162.875}, "bottomBorder": {"height": 1.0, "fill": "#e8eaec"}}, {"path": "0.0.1.0.1.2.3", "bounds": {"x": 720.734375, "y": 134.875, "width": 240.265625, "height": 48}, "fill": "#ffffff", "text": {"path": "0.0.1.0.1.2.3.0.0", "characters": "启用", "sourceTextBounds": {"x": 738.734375, "y": 149.875, "width": 28, "height": 16}, "sourceSizing": {"display": "inline", "width": "auto", "height": "auto"}, "fontSize": 14, "fontWeight": 400, "sourceCssFontWeight": 400, "role": "body", "fontFamily": "PingFang SC", "postScriptName": "PingFangSC-Regular", "fill": "#515a6e", "sourceBaselineY": 162.875}, "bottomBorder": {"height": 1.0, "fill": "#e8eaec"}}], "bottomBorder": {"height": 1.0, "fill": "#e8eaec"}}, {"path": "0.0.1.0.1.3", "bounds": {"x": 0, "y": 182.875, "width": 961, "height": 48}, "cells": [{"path": "0.0.1.0.1.3.0", "bounds": {"x": 0, "y": 182.875, "width": 160.15625, "height": 48}, "fill": "#ffffff", "text": {"path": "0.0.1.0.1.3.0.0.0", "characters": "004", "sourceTextBounds": {"x": 18, "y": 197.875, "width": 23.359375, "height": 16}, "sourceSizing": {"display": "inline", "width": "auto", "height": "auto"}, "fontSize": 14, "fontWeight": 400, "sourceCssFontWeight": 400, "role": "body", "fontFamily": "Arial", "postScriptName": "ArialMT", "fill": "#515a6e", "sourceBaselineY": 210.875}, "bottomBorder": {"height": 1.0, "fill": "#e8eaec"}}, {"path": "0.0.1.0.1.3.1", "bounds": {"x": 160.15625, "y": 182.875, "width": 240.25, "height": 48}, "fill": "#ffffff", "text": {"path": "0.0.1.0.1.3.1.0.0", "characters": "赵六", "sourceTextBounds": {"x": 178.15625, "y": 197.875, "width": 28, "height": 16}, "sourceSizing": {"display": "inline", "width": "auto", "height": "auto"}, "fontSize": 14, "fontWeight": 400, "sourceCssFontWeight": 400, "role": "body", "fontFamily": "PingFang SC", "postScriptName": "PingFangSC-Regular", "fill": "#515a6e", "sourceBaselineY": 210.875}, "bottomBorder": {"height": 1.0, "fill": "#e8eaec"}}, {"path": "0.0.1.0.1.3.2", "bounds": {"x": 400.40625, "y": 182.875, "width": 320.328125, "height": 48}, "fill": "#ffffff", "text": {"path": "0.0.1.0.1.3.2.0.0", "characters": "客服", "sourceTextBounds": {"x": 418.40625, "y": 197.875, "width": 28, "height": 16}, "sourceSizing": {"display": "inline", "width": "auto", "height": "auto"}, "fontSize": 14, "fontWeight": 400, "sourceCssFontWeight": 400, "role": "body", "fontFamily": "PingFang SC", "postScriptName": "PingFangSC-Regular", "fill": "#515a6e", "sourceBaselineY": 210.875}, "bottomBorder": {"height": 1.0, "fill": "#e8eaec"}}, {"path": "0.0.1.0.1.3.3", "bounds": {"x": 720.734375, "y": 182.875, "width": 240.265625, "height": 48}, "fill": "#ffffff", "text": {"path": "0.0.1.0.1.3.3.0.0", "characters": "启用", "sourceTextBounds": {"x": 738.734375, "y": 197.875, "width": 28, "height": 16}, "sourceSizing": {"display": "inline", "width": "auto", "height": "auto"}, "fontSize": 14, "fontWeight": 400, "sourceCssFontWeight": 400, "role": "body", "fontFamily": "PingFang SC", "postScriptName": "PingFangSC-Regular", "fill": "#515a6e", "sourceBaselineY": 210.875}, "bottomBorder": {"height": 1.0, "fill": "#e8eaec"}}], "bottomBorder": {"height": 1.0, "fill": "#e8eaec"}}], "sourceObservationSha256": "8ac766de072c294b2a02523ce0920635609744de2902047022dad5d31ae5f388", "requiredFonts": ["Arial", "PingFang SC"], "bottomPseudo": {"height": 1.0, "width": 960.0, "fill": "#dcdee2", "sourceCssRule": ".ivu-table:before{content:'';width:100%;height:1px;position:absolute;left:0;bottom:0;background-color:#dcdee2;z-index:4}"}, "admissionEligible": false, "fidelityGate": "NOT_RUN", "fileReference": "91396aad-60c8-808b-8008-c0885ca79899", "pageReference": null, "name": "candidate/data.table.headed.5eca5bc513698ad31a2d57d0660cebee6ef0536e196c5ed468f8153f52b90c25/penpot-v1", "headerBackgroundUnion": {"decisionSha256": "16ccb7f958dda5f6e8933e081d893080b0d924785ee8e3de8d87d9e8cb1e97aa", "rowPath": "0.0.0.0.1.0", "bounds": {"x": 0, "y": 0, "width": 961, "height": 38.875}, "fill": "#f8f8f9", "opacity": 1, "cellPaths": ["0.0.0.0.1.0.0", "0.0.0.0.1.0.1", "0.0.0.0.1.0.2", "0.0.0.0.1.0.3"], "fidelityGate": "NOT_RUN", "productionAdmission": false}}];let tableExecution={"status": "CREATED", "fileReference": "91396aad-60c8-808b-8008-c0885ca79899", "pageReference": "60977a61-dfea-80ea-8008-c4e4eda0adb3", "candidates": [{"status": "CANDIDATE_CREATED", "platform": "penpot", "fileReference": "91396aad-60c8-808b-8008-c0885ca79899", "pageReference": "60977a61-dfea-80ea-8008-c4e4eda0adb3", "componentReference": "60977a61-dfea-80ea-8008-c4e4ee901de1", "mainReference": "60977a61-dfea-80ea-8008-c4e4edb93a37", "textReference": "60977a61-dfea-80ea-8008-c4e4edd79b63", "textReferences": ["60977a61-dfea-80ea-8008-c4e4edd79b63", "60977a61-dfea-80ea-8008-c4e4edf246cd", "60977a61-dfea-80ea-8008-c4e4ee18c2ed", "60977a61-dfea-80ea-8008-c4e4ee33e489", "60977a61-dfea-80ea-8008-c4e4ee584aaa", "60977a61-dfea-80ea-8008-c4e4ee6de2fe"], "logicalId": "data.table.headed.613acb453dafc1629920ac3d697c42918bef2d556cc6f7e61648523f1f7f24aa", "componentIrSha256": "b71439e9d1ee3c80b61c21d8ed864bbcb7ff462d9fee9e8dc298b5ee53a002c1", "createdNodeIds": ["60977a61-dfea-80ea-8008-c4e4edb93a37", "60977a61-dfea-80ea-8008-c4e4edc77a0a", "60977a61-dfea-80ea-8008-c4e4edcf9fb6", "60977a61-dfea-80ea-8008-c4e4edd79b63", "60977a61-dfea-80ea-8008-c4e4ede97654", "60977a61-dfea-80ea-8008-c4e4edf246cd", "60977a61-dfea-80ea-8008-c4e4ee00f2a4", "60977a61-dfea-80ea-8008-c4e4ee096d5c", "60977a61-dfea-80ea-8008-c4e4ee108951", "60977a61-dfea-80ea-8008-c4e4ee18c2ed", "60977a61-dfea-80ea-8008-c4e4ee2c2bee", "60977a61-dfea-80ea-8008-c4e4ee33e489", "60977a61-dfea-80ea-8008-c4e4ee4082f7", "60977a61-dfea-80ea-8008-c4e4ee48f529", "60977a61-dfea-80ea-8008-c4e4ee50e92b", "60977a61-dfea-80ea-8008-c4e4ee584aaa", "60977a61-dfea-80ea-8008-c4e4ee660224", "60977a61-dfea-80ea-8008-c4e4ee6de2fe", "60977a61-dfea-80ea-8008-c4e4ee7cebd6", "60977a61-dfea-80ea-8008-c4e4ee863964"], "mutatedNodeIds": [], "admissionEligible": false, "baselineCalibration": "NOT_RUN", "fidelityGate": "NOT_RUN"}, {"status": "CANDIDATE_CREATED", "platform": "penpot", "fileReference": "91396aad-60c8-808b-8008-c0885ca79899", "pageReference": "60977a61-dfea-80ea-8008-c4e4eda0adb3", "componentReference": "60977a61-dfea-80ea-8008-c4e4f19d879a", "mainReference": "60977a61-dfea-80ea-8008-c4e4eef45e14", "textReference": "60977a61-dfea-80ea-8008-c4e4ef0e119b", "textReferences": ["60977a61-dfea-80ea-8008-c4e4ef0e119b", "60977a61-dfea-80ea-8008-c4e4ef2c28d1", "60977a61-dfea-80ea-8008-c4e4ef49dcb8", "60977a61-dfea-80ea-8008-c4e4ef6a99a8", "60977a61-dfea-80ea-8008-c4e4ef9c5fa4", "60977a61-dfea-80ea-8008-c4e4efb96764", "60977a61-dfea-80ea-8008-c4e4efd63a6d", "60977a61-dfea-80ea-8008-c4e4eff493ff", "60977a61-dfea-80ea-8008-c4e4f023f23d", "60977a61-dfea-80ea-8008-c4e4f040db2b", "60977a61-dfea-80ea-8008-c4e4f05b7ff5", "60977a61-dfea-80ea-8008-c4e4f07661c5", "60977a61-dfea-80ea-8008-c4e4f0a8cd86", "60977a61-dfea-80ea-8008-c4e4f0c6c572", "60977a61-dfea-80ea-8008-c4e4f0e1fa58", "60977a61-dfea-80ea-8008-c4e4f0fa4774", "60977a61-dfea-80ea-8008-c4e4f1276b85", "60977a61-dfea-80ea-8008-c4e4f140f5ae", "60977a61-dfea-80ea-8008-c4e4f15b8b9e", "60977a61-dfea-80ea-8008-c4e4f175bfe3"], "logicalId": "data.table.headed.5eca5bc513698ad31a2d57d0660cebee6ef0536e196c5ed468f8153f52b90c25", "componentIrSha256": "8b14f33d3468b3372046aa2a533824173cc26bd1e9e3990af1b8c202dbd10771", "createdNodeIds": ["60977a61-dfea-80ea-8008-c4e4eef45e14", "60977a61-dfea-80ea-8008-c4e4eefd77c2", "60977a61-dfea-80ea-8008-c4e4ef04a0d4", "60977a61-dfea-80ea-8008-c4e4ef0e119b", "60977a61-dfea-80ea-8008-c4e4ef219627", "60977a61-dfea-80ea-8008-c4e4ef2c28d1", "60977a61-dfea-80ea-8008-c4e4ef3cac12", "60977a61-dfea-80ea-8008-c4e4ef49dcb8", "60977a61-dfea-80ea-8008-c4e4ef5d6cfa", "60977a61-dfea-80ea-8008-c4e4ef6a99a8", "60977a61-dfea-80ea-8008-c4e4ef7c8971", "60977a61-dfea-80ea-8008-c4e4ef8a3d36", "60977a61-dfea-80ea-8008-c4e4ef9314bc", "60977a61-dfea-80ea-8008-c4e4ef9c5fa4", "60977a61-dfea-80ea-8008-c4e4efac89b7", "60977a61-dfea-80ea-8008-c4e4efb96764", "60977a61-dfea-80ea-8008-c4e4efca984f", "60977a61-dfea-80ea-8008-c4e4efd63a6d", "60977a61-dfea-80ea-8008-c4e4efe985ea", "60977a61-dfea-80ea-8008-c4e4eff493ff", "60977a61-dfea-80ea-8008-c4e4f0042358", "60977a61-dfea-80ea-8008-c4e4f00f09ba", "60977a61-dfea-80ea-8008-c4e4f019f68a", "60977a61-dfea-80ea-8008-c4e4f023f23d", "60977a61-dfea-80ea-8008-c4e4f034d7dc", "60977a61-dfea-80ea-8008-c4e4f040db2b", "60977a61-dfea-80ea-8008-c4e4f05222d0", "60977a61-dfea-80ea-8008-c4e4f05b7ff5", "60977a61-dfea-80ea-8008-c4e4f06c65e8", "60977a61-dfea-80ea-8008-c4e4f07661c5", "60977a61-dfea-80ea-8008-c4e4f086ef55", "60977a61-dfea-80ea-8008-c4e4f0925fa4", "60977a61-dfea-80ea-8008-c4e4f09e8d0c", "60977a61-dfea-80ea-8008-c4e4f0a8cd86", "60977a61-dfea-80ea-8008-c4e4f0bc290b", "60977a61-dfea-80ea-8008-c4e4f0c6c572", "60977a61-dfea-80ea-8008-c4e4f0d8e8b2", "60977a61-dfea-80ea-8008-c4e4f0e1fa58", "60977a61-dfea-80ea-8008-c4e4f0f14283", "60977a61-dfea-80ea-8008-c4e4f0fa4774", "60977a61-dfea-80ea-8008-c4e4f10b44bb", "60977a61-dfea-80ea-8008-c4e4f116474f", "60977a61-dfea-80ea-8008-c4e4f11edf93", "60977a61-dfea-80ea-8008-c4e4f1276b85", "60977a61-dfea-80ea-8008-c4e4f13707cb", "60977a61-dfea-80ea-8008-c4e4f140f5ae", "60977a61-dfea-80ea-8008-c4e4f151d225", "60977a61-dfea-80ea-8008-c4e4f15b8b9e", "60977a61-dfea-80ea-8008-c4e4f16bb0f7", "60977a61-dfea-80ea-8008-c4e4f175bfe3", "60977a61-dfea-80ea-8008-c4e4f185d94f", "60977a61-dfea-80ea-8008-c4e4f191972f"], "mutatedNodeIds": [], "admissionEligible": false, "baselineCalibration": "NOT_RUN", "fidelityGate": "NOT_RUN"}], "createdNodeIds": ["60977a61-dfea-80ea-8008-c4e4eda0adb3", "60977a61-dfea-80ea-8008-c4e4edb93a37", "60977a61-dfea-80ea-8008-c4e4edc77a0a", "60977a61-dfea-80ea-8008-c4e4edcf9fb6", "60977a61-dfea-80ea-8008-c4e4edd79b63", "60977a61-dfea-80ea-8008-c4e4ede97654", "60977a61-dfea-80ea-8008-c4e4edf246cd", "60977a61-dfea-80ea-8008-c4e4ee00f2a4", "60977a61-dfea-80ea-8008-c4e4ee096d5c", "60977a61-dfea-80ea-8008-c4e4ee108951", "60977a61-dfea-80ea-8008-c4e4ee18c2ed", "60977a61-dfea-80ea-8008-c4e4ee2c2bee", "60977a61-dfea-80ea-8008-c4e4ee33e489", "60977a61-dfea-80ea-8008-c4e4ee4082f7", "60977a61-dfea-80ea-8008-c4e4ee48f529", "60977a61-dfea-80ea-8008-c4e4ee50e92b", "60977a61-dfea-80ea-8008-c4e4ee584aaa", "60977a61-dfea-80ea-8008-c4e4ee660224", "60977a61-dfea-80ea-8008-c4e4ee6de2fe", "60977a61-dfea-80ea-8008-c4e4ee7cebd6", "60977a61-dfea-80ea-8008-c4e4ee863964", "60977a61-dfea-80ea-8008-c4e4eef45e14", "60977a61-dfea-80ea-8008-c4e4eefd77c2", "60977a61-dfea-80ea-8008-c4e4ef04a0d4", "60977a61-dfea-80ea-8008-c4e4ef0e119b", "60977a61-dfea-80ea-8008-c4e4ef219627", "60977a61-dfea-80ea-8008-c4e4ef2c28d1", "60977a61-dfea-80ea-8008-c4e4ef3cac12", "60977a61-dfea-80ea-8008-c4e4ef49dcb8", "60977a61-dfea-80ea-8008-c4e4ef5d6cfa", "60977a61-dfea-80ea-8008-c4e4ef6a99a8", "60977a61-dfea-80ea-8008-c4e4ef7c8971", "60977a61-dfea-80ea-8008-c4e4ef8a3d36", "60977a61-dfea-80ea-8008-c4e4ef9314bc", "60977a61-dfea-80ea-8008-c4e4ef9c5fa4", "60977a61-dfea-80ea-8008-c4e4efac89b7", "60977a61-dfea-80ea-8008-c4e4efb96764", "60977a61-dfea-80ea-8008-c4e4efca984f", "60977a61-dfea-80ea-8008-c4e4efd63a6d", "60977a61-dfea-80ea-8008-c4e4efe985ea", "60977a61-dfea-80ea-8008-c4e4eff493ff", "60977a61-dfea-80ea-8008-c4e4f0042358", "60977a61-dfea-80ea-8008-c4e4f00f09ba", "60977a61-dfea-80ea-8008-c4e4f019f68a", "60977a61-dfea-80ea-8008-c4e4f023f23d", "60977a61-dfea-80ea-8008-c4e4f034d7dc", "60977a61-dfea-80ea-8008-c4e4f040db2b", "60977a61-dfea-80ea-8008-c4e4f05222d0", "60977a61-dfea-80ea-8008-c4e4f05b7ff5", "60977a61-dfea-80ea-8008-c4e4f06c65e8", "60977a61-dfea-80ea-8008-c4e4f07661c5", "60977a61-dfea-80ea-8008-c4e4f086ef55", "60977a61-dfea-80ea-8008-c4e4f0925fa4", "60977a61-dfea-80ea-8008-c4e4f09e8d0c", "60977a61-dfea-80ea-8008-c4e4f0a8cd86", "60977a61-dfea-80ea-8008-c4e4f0bc290b", "60977a61-dfea-80ea-8008-c4e4f0c6c572", "60977a61-dfea-80ea-8008-c4e4f0d8e8b2", "60977a61-dfea-80ea-8008-c4e4f0e1fa58", "60977a61-dfea-80ea-8008-c4e4f0f14283", "60977a61-dfea-80ea-8008-c4e4f0fa4774", "60977a61-dfea-80ea-8008-c4e4f10b44bb", "60977a61-dfea-80ea-8008-c4e4f116474f", "60977a61-dfea-80ea-8008-c4e4f11edf93", "60977a61-dfea-80ea-8008-c4e4f1276b85", "60977a61-dfea-80ea-8008-c4e4f13707cb", "60977a61-dfea-80ea-8008-c4e4f140f5ae", "60977a61-dfea-80ea-8008-c4e4f151d225", "60977a61-dfea-80ea-8008-c4e4f15b8b9e", "60977a61-dfea-80ea-8008-c4e4f16bb0f7", "60977a61-dfea-80ea-8008-c4e4f175bfe3", "60977a61-dfea-80ea-8008-c4e4f185d94f", "60977a61-dfea-80ea-8008-c4e4f191972f"], "createdComponentIds": ["60977a61-dfea-80ea-8008-c4e4ee901de1", "60977a61-dfea-80ea-8008-c4e4f19d879a"], "mutatedNodeIds": [], "admissionEligible": false, "fidelityGate": "NOT_RUN"};
penpot.ui.onMessage(async message=>{
      if(!['table-create','table-capture-0','table-capture-1','table-refresh-fonts','table-repair-header'].includes(message?.type))return;
      let created=[];let mutated=[];let candidates=[];
      try{
        if(penpot.currentFile?.id!==targetFile)throw new Error('target_file_mismatch');
        let result;
        if(message.type==='table-create'){
          if(tableExecution)throw new Error('table_existing_execution_requires_recovery');
          if(penpot.currentFile.pages.some(p=>p.name==='task020-headed-table-candidates'))throw new Error('table_existing_page_requires_recovery');
          for(const spec of tableSpecs)for(const family of spec.requiredFonts){
            const fonts=penpot.fonts.all.filter(f=>f.fontFamily===family);
            if(fonts.length!==1)throw new Error('missing_or_ambiguous_source_font:'+family);
            for(const weight of [...new Set(spec.rows.flatMap(r=>r.cells).filter(c=>c.text.fontFamily===family).map(c=>c.text.fontWeight))])selectExactPenpotVariant(fonts[0],weight);
          }
          const page=penpot.createPage();created.push(page.id);page.name='task020-headed-table-candidates';await penpot.openPage(page);
          for(const original of tableSpecs){const spec={...original,pageReference:page.id};
            const candidate=await buildHeadedPenpotTableCandidate(penpot,spec);candidates.push(candidate);created.push(...candidate.createdNodeIds);
            if(candidate.status!=='CANDIDATE_CREATED')throw new Error('candidate_creation_failed');
          }
          result=tableExecution={status:'CREATED',fileReference:targetFile,pageReference:page.id,candidates,createdNodeIds:created,createdComponentIds:candidates.map(c=>c.componentReference),mutatedNodeIds:[],admissionEligible:false,fidelityGate:'NOT_RUN'};
        }else if(message.type==='table-repair-header'){
          result=await repairHeadedTableHeaders(penpot,tableSpecs,tableExecution);
        }else if(message.type==='table-restore-background'){
          if(tableExecution?.status!=='CREATED'||penpot.currentPage.id!==tableExecution.pageReference)throw new Error('table_execution_required');
          const observations=[];
          // Preflight both exact main instances before the first mutation.
          for(let i=0;i<tableSpecs.length;i++){
            const spec=tableSpecs[i],candidate=tableExecution.candidates[i],main=penpot.currentPage.getShapeById(candidate.mainReference);
            if(!main?.isComponentMainInstance()||main.width!==spec.rootBounds.width||main.height!==spec.rootBounds.height||main.clipContent!==true||main.opacity!==1||main.strokes.length||main.borderRadius!==0)throw new Error('table_background_main_mismatch');
            if(main.fills.length && !(main.fills.length===1&&main.fills[0].fillColor===spec.rootFill&&main.fills[0].fillOpacity===1))throw new Error('table_background_requires_read');
            observations.push({mainReference:main.id,logicalId:spec.logicalId,sourcePath:spec.rootFillSourcePath,sourceFill:spec.rootFill,beforeFills:JSON.parse(JSON.stringify(main.fills))});
          }
          for(const row of observations){const main=penpot.currentPage.getShapeById(row.mainReference);main.fills=[{fillColor:row.sourceFill,fillOpacity:1}];mutated.push(main.id);}
          await penpot.waitForLayoutUpdate();
          for(const row of observations)row.afterFills=JSON.parse(JSON.stringify(penpot.currentPage.getShapeById(row.mainReference).fills));
          result={status:'SOURCE_BACKGROUND_RESTORED',fileReference:targetFile,pageReference:tableExecution.pageReference,observations,createdNodeIds:[],mutatedNodeIds:mutated,fidelityGate:'NOT_RUN',admissionEligible:false};
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
              observed.push({textReference:text.id,characters:text.characters,sourceFontFamily:item.fontFamily,sourceFontWeight:item.fontWeight,beforeRange:{fontId:range.fontId,fontFamily:range.fontFamily,fontVariantId:range.fontVariantId,fontSize:range.fontSize,fontWeight:range.fontWeight,lineHeight:range.lineHeight,letterSpacing:range.letterSpacing}});
            }
          }
          // Apply the same bound font to the complete public text range. No
          // geometry offsets, tracking changes or source text substitutions.
          for(const row of observed){const text=penpot.currentPage.getShapeById(row.textReference),font=penpot.fonts.findById(text.fontId);
            if(!font||font.fontFamily!==row.sourceFontFamily)throw new Error('table_exact_source_font_missing');
            font.applyToRange(text.getRange(0,text.characters.length),selectExactPenpotVariant(font,row.sourceFontWeight));
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
          result=await captureHeadedPenpotTable(penpot,{...tableSpecs[index],...tableExecution.candidates[index]});
        }
        penpot.ui.sendMessage({type:'task010-result',status:result.status==='FAIL'?'FAIL':'CAPTURED',result});
      }catch(error){penpot.ui.sendMessage({type:'task010-result',status:'FAIL',error:String(error),result:{status:'FAIL',fileReference:targetFile,createdNodeIds:created,candidates,mutatedNodeIds:mutated,admissionEligible:false,fidelityGate:'NOT_RUN'}});}
    });