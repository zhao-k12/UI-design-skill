async function createDefaultFontButtonCandidate(figma, fileKey) {
  if (figma.fileKey !== fileKey) throw new Error('candidate_foreign_file');
  const pageName = 'V0.2 / Default-font Button candidate';
  if (figma.root.children.some(p => p.name === pageName)) throw new Error('candidate_page_already_exists');
  const existingCollections = await figma.variables.getLocalVariableCollectionsAsync();
  const collectionName = 'V0.2 / Source Button candidate';
  if (existingCollections.some(c => c.name === collectionName)) throw new Error('candidate_variables_already_exist');
  const available = await figma.listAvailableFontsAsync();
  if (!available.some(f => f.fontName.family === 'Inter' && f.fontName.style === 'Regular')) throw new Error('native_default_font_unavailable');
  await figma.loadFontAsync({family:'Inter',style:'Regular'});
  const collection = figma.variables.createVariableCollection(collectionName);
  const mode = collection.defaultModeId;
  const rgb = (r,g,b) => ({r:r/255,g:g/255,b:b/255});
  const vars = {};
  const add = (key,type,value,scopes) => {
    const v=figma.variables.createVariable(key,collection,type);
    v.scopes=scopes;
    v.setValueForMode(mode,value);
    vars[key]=v;
    return v;
  };
  const blue=add('color/button/primary','COLOR',rgb(45,140,240),['FRAME_FILL','SHAPE_FILL','STROKE_COLOR']);
  const white=add('color/button/on-primary','COLOR',rgb(255,255,255),['TEXT_FILL']);
  const radius=add('radius/button','FLOAT',4,['CORNER_RADIUS']);
  const padding=add('spacing/button/horizontal','FLOAT',15,['GAP']);
  const border=add('stroke/button','FLOAT',1,['STROKE_FLOAT']);
  const height=add('size/button/height','FLOAT',32,['WIDTH_HEIGHT']);
  const family=add('font/button/family','STRING','Inter',['FONT_FAMILY']);
  const style=add('font/button/style','STRING','Regular',['FONT_STYLE']);
  const fontSize=add('font/button/size','FLOAT',14,['FONT_SIZE']);
  const fontWeight=add('font/button/weight','FLOAT',400,['FONT_WEIGHT']);
  const lineHeight=add('font/button/line-height','FLOAT',21,['LINE_HEIGHT']);
  const page=figma.createPage();page.name=pageName;
  await figma.setCurrentPageAsync(page);
  const comp=figma.createComponent();
  comp.name='V0.2/Button/Primary/Medium/Default';
  comp.description='Candidate adapted from locked View UI Plus 1.3.24 primary Button; Inter Regular 14 replaces the historical font. Native fidelity admission pending.';
  comp.x=800;comp.y=80;comp.resize(60,32);
  comp.layoutMode='HORIZONTAL';
  comp.primaryAxisSizingMode='FIXED';comp.counterAxisSizingMode='FIXED';
  comp.primaryAxisAlignItems='CENTER';comp.counterAxisAlignItems='CENTER';
  comp.paddingLeft=15;comp.paddingRight=15;comp.paddingTop=0;comp.paddingBottom=0;
  comp.setBoundVariable('paddingLeft',padding);comp.setBoundVariable('paddingRight',padding);
  comp.setBoundVariable('height',height);
  comp.cornerRadius=4;comp.setBoundVariable('cornerRadius',radius);
  comp.strokeWeight=1;comp.setBoundVariable('strokeWeight',border);
  comp.fills=[figma.variables.setBoundVariableForPaint({type:'SOLID',color:rgb(45,140,240)},'color',blue)];
  comp.strokes=[figma.variables.setBoundVariableForPaint({type:'SOLID',color:rgb(45,140,240)},'color',blue)];
  const label=figma.createText();
  label.name='label';label.fontName={family:'Inter',style:'Regular'};
  label.fontSize=14;label.lineHeight={unit:'PIXELS',value:21};
  label.textAutoResize='WIDTH_AND_HEIGHT';label.characters='查询';
  label.fills=[figma.variables.setBoundVariableForPaint({type:'SOLID',color:rgb(255,255,255)},'color',white)];
  comp.appendChild(label);
  label.setBoundVariable('fontFamily',family);
  label.setBoundVariable('fontStyle',style);
  label.setBoundVariable('fontSize',fontSize);
  label.setBoundVariable('fontWeight',fontWeight);
  label.setBoundVariable('lineHeight',lineHeight);
  const labelKey=comp.addComponentProperty('Label','TEXT','查询');
  label.componentPropertyReferences={characters:labelKey};
  comp.primaryAxisSizingMode='AUTO';
  const review=figma.createFrame();review.name='V0.2 Button candidate review';
  review.x=80;review.y=80;review.resize(400,160);
  review.fills=[{type:'SOLID',color:rgb(255,255,255)}];
  const instance=comp.createInstance();review.appendChild(instance);
  instance.x=60;instance.y=64;
  const first=await review.exportAsync({format:'PNG',constraint:{type:'SCALE',value:2}});
  const second=await review.exportAsync({format:'PNG',constraint:{type:'SCALE',value:2}});
  if (!first.length || !second.length || comp.width<=0 || comp.height<=0 || label.characters!=='查询' || label.fontName.family!=='Inter') throw new Error('candidate_native_creation_invalid');
  return {scope:'v02-button-candidate-creation',platform:'figma',status:'CANDIDATE',fileReference:fileKey,
    pageReference:page.id,pageName,collectionId:collection.id,
    variableIds:Object.fromEntries(Object.entries(vars).map(([k,v])=>[k,v.id])),
    createdNodeIds:[comp.id,label.id,review.id,instance.id],componentId:comp.id,labelId:label.id,
    instanceId:instance.id,reviewFrameId:review.id,labelPropertyKey:labelKey,
    fontName:label.fontName,fontSize:label.fontSize,lineHeight:label.lineHeight,
    componentBounds:{width:comp.width,height:comp.height},textBounds:{width:label.width,height:label.height},
    nativePngBase64:figma.base64Encode(second),nativeAcceptance:'NOT_RUN',releaseReady:false};
}
