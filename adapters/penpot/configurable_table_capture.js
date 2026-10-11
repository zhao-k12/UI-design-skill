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
