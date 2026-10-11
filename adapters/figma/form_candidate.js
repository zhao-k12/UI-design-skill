// Translate supported official static Input/Select samples, not admitted UI assets.
async function buildFormCandidate(api, payload) {
  const createdNodeIds = [];
  const result = {scope:'figma_form_candidate', status:'FAIL', admissionEligible:false,
    fidelityGate:'NOT_RUN', createdNodeIds, mutatedNodeIds:[], issues:[]};
  try {
    if (api.editorType !== 'figma' || api.fileKey !== payload.fileReference) throw new Error('target_file_mismatch');
    const spec = payload.spec;
    if (!['Input','Select'].includes(spec.componentType)) throw new Error('unsupported_form_type');
    const available = await api.listAvailableFontsAsync();
    const wanted = [spec.label, ...(spec.arrow ? [spec.arrow] : [])];
    // Discover every source font before creating any canvas node.
    for (const text of wanted) {
      if (!available.some(item => item.fontName.family === text.fontName.family && item.fontName.style === text.fontName.style)) throw new Error('missing_official_font: ' + text.fontName.family);
    }
    for (const text of wanted) await api.loadFontAsync(text.fontName);
    const page = await api.getNodeByIdAsync(payload.pageReference);
    if (!page || page.type !== 'PAGE') throw new Error('missing_candidate_page');
    await api.setCurrentPageAsync(page);
    if (page.children.some(node => node.name === spec.name)) throw new Error('candidate_exists_requires_ledger');
    const right = Math.max(0, ...page.children.map(node => node.x + node.width));
    function frame(parent, name, width, height) {
      const node = api.createAutoLayout('HORIZONTAL'); createdNodeIds.push(node.id);
      parent.appendChild(node); node.name = name; node.resize(width,height);
      node.layoutSizingHorizontal = 'FIXED'; node.layoutSizingVertical = 'FIXED';
      node.itemSpacing = 0; node.paddingTop=0; node.paddingRight=0; node.paddingBottom=0; node.paddingLeft=0;
      node.fills=[]; node.strokes=[]; node.effects=[];
      node.primaryAxisAlignItems='MIN'; node.counterAxisAlignItems='CENTER';
      return node;
    }
    async function text(parent, name, source) {
      const node = api.createText(); createdNodeIds.push(node.id);
      await api.loadFontAsync(node.fontName);
      node.fontName = source.fontName; node.fontSize = source.fontSize;
      node.lineHeight=source.lineHeight; node.letterSpacing={unit:'PIXELS',value:0};
      node.fills=[source.fill]; node.characters=source.characters;
      node.textAlignHorizontal='LEFT'; node.textAutoResize='WIDTH_AND_HEIGHT';
      parent.appendChild(node); node.name=name;
      node.layoutSizingHorizontal='HUG'; node.layoutSizingVertical='HUG';
      if (node.fontWeight !== source.fontWeight) throw new Error('source_font_weight_mismatch: ' + source.sourcePath);
      return node;
    }
    const root = frame(page,spec.name,spec.rootBounds.width,spec.rootBounds.height);
    root.x=right+80; root.y=80;
    const field = frame(root,'source/'+spec.surface.sourcePath,spec.surface.bounds.width,spec.surface.bounds.height);
    field.fills=[spec.surface.fill]; field.strokes=[spec.surface.stroke];
    field.strokeWeight=spec.surface.strokeWidth; field.strokeAlign='INSIDE';
    field.strokesIncludedInLayout=true; field.cornerRadius=spec.surface.radius;
    field.paddingTop=spec.surface.padding.top; field.paddingRight=spec.surface.padding.right;
    field.paddingBottom=spec.surface.padding.bottom; field.paddingLeft=spec.surface.padding.left;
    let label, arrow=null, content=null, labelSlot=null;
    if (spec.componentType === 'Input') {
      label = await text(field,'source/placeholder',spec.label);
    } else {
      content = frame(field,'source/'+spec.content.sourcePath,spec.content.bounds.width,spec.content.bounds.height);
      labelSlot = frame(content,'source/selected-value',spec.content.bounds.width,spec.content.bounds.height);
      labelSlot.paddingTop=spec.label.padding.top; labelSlot.paddingRight=spec.label.padding.right;
      labelSlot.paddingBottom=spec.label.padding.bottom; labelSlot.paddingLeft=spec.label.padding.left;
      label = await text(labelSlot,'source/selected-value-text',spec.label);
      arrow = await text(content,'source/ionicons-arrow',spec.arrow);
      // The source arrow is absolute. Captured DOM bounds already include its transform.
      arrow.layoutPositioning='ABSOLUTE';
      arrow.textAutoResize='NONE'; arrow.resize(spec.arrow.bounds.width,spec.arrow.bounds.height);
      arrow.layoutSizingHorizontal='FIXED'; arrow.layoutSizingVertical='FIXED';
      arrow.x=spec.arrow.bounds.x-spec.content.bounds.x;
      arrow.y=spec.arrow.bounds.y-spec.content.bounds.y;
    }
    const component=api.createComponentFromNode(root); createdNodeIds.push(component.id);
    component.description=`Unadmitted ${spec.componentType} runtime candidate: ${spec.logicalId}; ${spec.sourceVersion}`;
    function bounds(node) { return {x:node.x,y:node.y,width:node.width,height:node.height}; }
    function textObservation(node) { return {reference:node.id,type:node.type,bounds:bounds(node),
      characters:node.characters,fontName:node.fontName,fontWeight:node.fontWeight,
      fontSize:node.fontSize,lineHeight:node.lineHeight,fills:node.fills,
      layoutPositioning:node.layoutPositioning,textAutoResize:node.textAutoResize}; }
    result.nativeObservation={componentReference:component.id,componentType:spec.componentType,
      root:{type:component.type,bounds:bounds(component),fills:component.fills,strokes:component.strokes},
      field:{reference:field.id,bounds:bounds(field),fills:field.fills,strokes:field.strokes,
        strokeWeight:field.strokeWeight,strokeAlign:field.strokeAlign,cornerRadius:field.cornerRadius,
        paddingTop:field.paddingTop,paddingRight:field.paddingRight,paddingBottom:field.paddingBottom,paddingLeft:field.paddingLeft},
      label:textObservation(label),arrow:arrow?textObservation(arrow):null,
      content:content?{reference:content.id,bounds:bounds(content)}:null,
      labelSlot:labelSlot?{reference:labelSlot.id,bounds:bounds(labelSlot)}:null};
    result.status='PASS';
  } catch(error) { result.issues.push({code:String(error.message)}); }
  return result;
}
