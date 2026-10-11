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
