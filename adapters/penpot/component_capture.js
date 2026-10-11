// Independent read-only candidate observation; raw native exports remain unmodified.
async function capturePenpotButtonCandidate(api, request) {
  if(api.currentFile?.id!==request.fileReference || api.currentPage?.id!==request.pageReference)throw new Error('candidate_capture_context_mismatch');
  const component=api.library.local.components.find(c=>c.id===request.componentReference);
  const main=component?.mainInstance(),text=api.currentPage.getShapeById(request.textReference);
  if(!main || main.id!==request.mainReference || !main.isComponentMainInstance() || !text || text.type!=='text')throw new Error('candidate_capture_identity_mismatch');
  let ancestor=text;while(ancestor && ancestor.id!==main.id)ancestor=ancestor.parent;
  if(!ancestor)throw new Error('candidate_capture_text_outside_component');
  const texts=request.textReferences?request.textReferences.map(id=>api.currentPage.getShapeById(id)):[text];
  if(request.logicalId==='data.table.default'){
    if(texts.length!==9||new Set(texts.map(n=>n?.id)).size!==9)throw new Error('candidate_capture_text_inventory_mismatch');
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
  const expectedWidth=request.logicalId==='data.table.default'?1392:request.logicalId==='action.button.primary.medium'?60:['form.input.default.medium','form.select.default.medium'].includes(request.logicalId)?240:null;
  const expectedHeight=request.logicalId==='data.table.default'?144:32;
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
  return {status:png&&svg&&textSvg&&(!arrow||arrowSvg)?'CAPTURED':'PARTIAL',platform:'penpot',scope:'production',evidenceKind:'native-platform-export',exporterVersion:'penpot-button-capture-v0.1.0',
    fileReference:request.fileReference,pageReference:api.currentPage.id,fileRevision:revision,componentReference:component.id,
    mainReference:main.id,logicalId:request.logicalId,componentIrSha256:request.componentIrSha256,
    createdNodeIds:[],mutatedNodeIds:[],nodes,nativePngBase64:png?encode(png):null,nativeSvgBase64:svg?encode(svg):null,nativeTextSvgBase64:textSvg?encode(textSvg):null,
    ...(arrow?{arrowReference:arrow.id,nativeArrowSvgBase64:arrowSvg?encode(arrowSvg):null}:{}),nativeSvgMarkup,exportIssues,
    nativeFontFaces,nativePdf,penpotVersion:api.version,
    admissionEligible:false,fidelityGate:'NOT_RUN'};
}

// Convert a separate diagnostic text copy. The editable candidate is never flattened.
async function probePenpotTextOutline(api,request) {
  if(api.currentFile?.id!==request.fileReference || api.currentPage?.id!==request.pageReference)throw new Error('outline_context_mismatch');
  const text=api.currentPage.getShapeById(request.textReference),component=api.library.local.components.find(c=>c.id===request.componentReference);
  if(!text || text.type!=='text' || component?.mainInstance()?.id!==request.mainReference)throw new Error('outline_identity_mismatch');
  const name='diagnostic/button-native-outline-v1';
  if(api.currentPage.root.children.some(n=>n.name===name))throw new Error('outline_probe_requires_recovery');
  const font=api.fonts.findById(text.fontId),variant=font?.variants.find(v=>v.fontVariantId===text.fontVariantId);
  if(!font || !variant)throw new Error('outline_exact_font_missing');
  const original={reference:text.id,parentReference:text.parent?.id,x:text.x,y:text.y,width:text.width,height:text.height,
    characters:text.characters,fontId:text.fontId,fontVariantId:text.fontVariantId,fontSize:text.fontSize,fontWeight:text.fontWeight,
    lineHeight:text.lineHeight,letterSpacing:text.letterSpacing};
  const created=[];
  try {
    const copy=api.createText(text.characters);if(!copy)throw new Error('outline_copy_failed');created.push(copy.id);
    api.currentPage.root.appendChild(copy);copy.name=name;font.applyToText(copy,variant);
    copy.fontSize=text.fontSize;copy.lineHeight=text.lineHeight;copy.letterSpacing=text.letterSpacing;
    copy.growType=text.growType;copy.verticalAlign=text.verticalAlign;copy.align=text.align;copy.fills=text.fills;
    copy.resize(text.width,text.height);copy.x=400;copy.y=80;
    await api.waitForLayoutUpdate();
    const paths=api.flatten([copy]);await api.waitForLayoutUpdate();
    const observations=[];
    for(const path of paths){if(!created.includes(path.id))created.push(path.id);path.name=name;
      observations.push({reference:path.id,type:path.type,x:path.x,y:path.y,width:path.width,height:path.height,d:path.d,commands:path.commands});}
    const unchanged=Object.keys(original).every(k=>k==='reference'?text.id===original[k]:k==='parentReference'?text.parent?.id===original[k]:text[k]===original[k]);
    // A path returned by flatten is not necessarily a glyph outline. Penpot 2.18.3
    // can return only the text frame; never classify that fallback as glyph evidence.
    const frameOnly=observations.length===1 && isTextFrameOutline(observations[0]);
    return {status:frameOnly?'UNSUPPORTED':observations.length&&unchanged?'OBSERVED':'FAIL',
      issues:frameOnly?[{code:'outline_is_text_frame',detail:'Native flatten returned the text bounding rectangle, not glyphs.'}]:[],
      platform:'penpot',fileReference:request.fileReference,
      pageReference:request.pageReference,textReference:text.id,diagnosticOrigin:{x:400,y:80},originalText:original,
      originalEditableTextUnchanged:unchanged,createdNodeIds:created,mutatedNodeIds:[],observations,admissionEligible:false,fidelityGate:'NOT_RUN'};
  }catch(error){return {status:'FAIL',platform:'penpot',fileReference:request.fileReference,createdNodeIds:created,
    mutatedNodeIds:[],issues:[{code:'outline_probe_failed',detail:String(error)}],admissionEligible:false};}
}

function isTextFrameOutline(path) {
  const numbers=String(path.d||'').match(/-?\d+(?:\.\d+)?/g)?.map(Number);
  if(!numbers || /[ACQSTHV]/i.test(path.d) || numbers.length!==10)return false;
  const expected=[path.x,path.y,path.x+path.width,path.y,path.x+path.width,path.y+path.height,
    path.x,path.y+path.height,path.x,path.y];
  return numbers.every((value,i)=>Math.abs(value-expected[i])<1e-8);
}
