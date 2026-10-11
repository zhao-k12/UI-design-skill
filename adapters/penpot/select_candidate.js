// Source-bound static Select. Candidate creation never implies fidelity PASS.
async function buildPenpotSelectCandidate(api,spec) {
  if(spec.logicalId!=='form.select.default.medium'||spec.labelRole!=='selected-value'||spec.nativeTextBounds!==null)throw new Error('unsupported_select_candidate');
  if(api.currentFile?.id!==spec.fileReference||api.currentPage?.id!==spec.pageReference)throw new Error('candidate_context_mismatch');
  const exists=name=>typeof name==='string'&&name.includes(spec.logicalId)&&name.replace(/\s*\/\s*/g,'/').endsWith('/penpot-v1');
  if(api.currentPage.root.children.some(n=>exists(n.name))||api.library.local.components.some(c=>exists(c.mainInstance()?.name)))throw new Error('candidate_requires_recovery');
  const exact=style=>{
    const fonts=api.fonts.all.filter(f=>f.fontFamily===style.fontFamily);
    if(fonts.length!==1)throw new Error('candidate_exact_font_missing_or_ambiguous');
    return {font:fonts[0],variant:selectExactPenpotVariant(fonts[0],style.fontWeight)};
  };
  const labelFont=exact(spec),arrowFont=exact(spec.arrow),created=[];let component;
  const record=n=>{created.push(n.id);return n;};
  try {
    const root=record(api.createBoard());api.currentPage.root.appendChild(root);root.name=spec.name;
    root.resize(spec.rootBounds.width,spec.rootBounds.height);root.x=80;root.y=240;
    root.clipContent=false;root.opacity=1;root.fills=[];root.strokes=[];root.borderRadius=spec.radius;
    const paint=record(api.createRectangle());root.appendChild(paint);paint.name='official-source/'+spec.logicalId+'/border-centerline';
    paint.resize(root.width-spec.strokeWidth,root.height-spec.strokeWidth);paint.x=root.x+spec.strokeWidth/2;paint.y=root.y+spec.strokeWidth/2;
    paint.borderRadius=spec.radius-spec.strokeWidth/2;paint.opacity=1;paint.fills=[{fillColor:spec.fill,fillOpacity:1}];
    paint.strokes=[{strokeColor:spec.stroke,strokeOpacity:1,strokeWidth:spec.strokeWidth,strokeAlignment:'center',strokeStyle:'solid'}];
    const textNode=(characters,bounds,style,binding,name)=>{
      const text=api.createText(characters);if(!text)throw new Error('candidate_text_creation_failed');record(text);
      binding.font.applyToText(text,binding.variant);text.fontSize=String(style.fontSize);text.lineHeight=String(style.lineHeight/style.fontSize);
      text.letterSpacing='0';text.growType='fixed';text.verticalAlign='top';text.align='left';text.opacity=1;
      text.fills=[{fillColor:style.fill,fillOpacity:1}];root.appendChild(text);text.resize(bounds.width,bounds.height);
      text.x=root.x+bounds.x;text.y=root.y+bounds.y;text.name=name;
      if(text.fontFamily!==style.fontFamily||Number(text.fontWeight)!==style.fontWeight)throw new Error('candidate_font_readback_mismatch');
      return text;
    };
    const text=textNode(spec.characters,spec.sourceTextBounds,{...spec,lineHeight:spec.sourceTextBounds.height,fill:spec.textFill},labelFont,'official-source/'+spec.logicalId+'/0.0.1.0');
    const arrow=textNode(spec.arrow.characters,spec.arrow.bounds,spec.arrow,arrowFont,'official-source/'+spec.logicalId+'/0.0.1.1::before');
    paint.setParentIndex(0);
    component=api.library.local.createComponent([root]);component.name='penpot-v1';component.path='candidate/'+spec.logicalId;
    await api.waitForLayoutUpdate();const main=component.mainInstance();if(!created.includes(main.id))created.push(main.id);
    return {status:'CANDIDATE_CREATED',platform:'penpot',fileReference:spec.fileReference,pageReference:spec.pageReference,
      componentReference:component.id,mainReference:main.id,textReference:text.id,arrowReference:arrow.id,logicalId:spec.logicalId,
      componentIrSha256:spec.componentIrSha256,createdNodeIds:created,mutatedNodeIds:[],admissionEligible:false,baselineCalibration:'NOT_RUN',fidelityGate:'NOT_RUN'};
  }catch(error){return {status:'FAIL',platform:'penpot',fileReference:spec.fileReference,pageReference:spec.pageReference,
    componentReference:component?.id,createdNodeIds:created,mutatedNodeIds:[],issues:[{code:'candidate_write_failed',detail:String(error)}],admissionEligible:false};}
}
