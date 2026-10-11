// Source-driven candidate, never a production registry entry or fidelity claim.
async function buildButtonCandidate(api, payload) {
  const createdNodeIds = [];
  const result = { scope: 'figma_button_candidate', status: 'FAIL', admissionEligible: false,
    fidelityGate: 'NOT_RUN', createdNodeIds, mutatedNodeIds: [], issues: [] };
  try {
    if (api.editorType !== 'figma' || api.fileKey !== payload.fileReference) throw new Error('target_file_mismatch');
    const spec = payload.spec;
    const calibration = spec.sourceSpan;
    if (calibration) {
      const b=calibration.bounds;
      if(!b || typeof calibration.verifiedNativeSvg!=='string' || !calibration.verifiedNativeSvg.startsWith('<svg') || calibration.verifiedNativeSvg.length>1000000 || ![b.x,b.y,b.width,b.height,calibration.textOffsetY,calibration.nativeSvgBaseline,calibration.sourceBaselineComponentY].every(Number.isFinite) || b.width<=0 || b.height<=0 || Math.abs(calibration.textOffsetY)>b.height ||
          b.y+calibration.textOffsetY+calibration.nativeSvgBaseline!==calibration.sourceBaselineComponentY ||
          Object.keys(calibration.evidenceHashes||{}).length!==4 || Object.values(calibration.evidenceHashes).some(value=>!/^[0-9a-f]{64}$/.test(value))) throw new Error('invalid_button_baseline_calibration');
    }
    const fonts = await api.listAvailableFontsAsync();
    if (!fonts.some(item => item.fontName.family === spec.fontName.family && item.fontName.style === spec.fontName.style)) throw new Error('missing_official_font');
    await api.loadFontAsync(spec.fontName);
    const page = await api.getNodeByIdAsync(payload.pageReference);
    if (!page || page.type !== 'PAGE') throw new Error('missing_candidate_page');
    await api.setCurrentPageAsync(page);
    if (page.children.some(node => node.name === spec.name)) throw new Error('candidate_exists_requires_ledger');
    const right = Math.max(0, ...page.children.map(node => node.x + node.width));
    const frame = api.createAutoLayout('HORIZONTAL');
    createdNodeIds.push(frame.id);
    page.appendChild(frame);
    frame.name = spec.name;
    frame.x = right + 80; frame.y = 80;
    frame.resize(spec.width, spec.height);
    frame.layoutSizingHorizontal = 'FIXED'; frame.layoutSizingVertical = 'FIXED';
    frame.primaryAxisAlignItems = 'CENTER'; frame.counterAxisAlignItems = 'CENTER';
    frame.itemSpacing = 0;
    frame.fills = [spec.fill]; frame.strokes = [spec.stroke];
    frame.strokeWeight = spec.strokeWidth; frame.strokeAlign = 'INSIDE';
    frame.strokesIncludedInLayout = true; frame.cornerRadius = spec.radius;
    frame.paddingTop = spec.padding.top; frame.paddingRight = spec.padding.right;
    frame.paddingBottom = spec.padding.bottom; frame.paddingLeft = spec.padding.left;
    const text = api.createText(); createdNodeIds.push(text.id);
    await api.loadFontAsync(text.fontName);
    text.fontName = spec.fontName;
    text.fontSize = spec.fontSize; text.lineHeight = {unit:'PIXELS', value:spec.lineHeight};
    text.letterSpacing = {unit:'PIXELS', value:0}; text.fills = [spec.textFill];
    text.characters = spec.text; text.textAlignHorizontal = 'CENTER';
    text.textAutoResize = 'WIDTH_AND_HEIGHT'; frame.appendChild(text);
    text.layoutSizingHorizontal = 'HUG'; text.layoutSizingVertical = 'HUG';
    if (text.fontWeight !== spec.fontWeight) throw new Error('source_font_weight_mismatch');
    let span;
    if (calibration) {
      const b=calibration.bounds;
      if(text.width!==b.width || text.height!==b.height) throw new Error('button_baseline_native_text_dimensions_changed');
      const svg=await text.exportAsync({format:'SVG_STRING',svgOutlineText:true,useAbsoluteBounds:true});
      if(svg!==calibration.verifiedNativeSvg)throw new Error('button_baseline_native_outline_changed');
      span=api.createAutoLayout('HORIZONTAL');createdNodeIds.push(span.id);
      frame.appendChild(span);span.name='source/0.0';span.resize(b.width,b.height);
      span.layoutSizingHorizontal='FIXED';span.layoutSizingVertical='FIXED';
      span.paddingTop=0;span.paddingRight=0;span.paddingBottom=0;span.paddingLeft=0;
      span.itemSpacing=0;span.fills=[];span.strokes=[];span.effects=[];span.clipsContent=false;
      span.primaryAxisAlignItems='MIN';span.counterAxisAlignItems='MIN';
      span.appendChild(text);text.layoutPositioning='ABSOLUTE';text.x=0;text.y=calibration.textOffsetY;
      if(span.x!==b.x || span.y!==b.y || span.width!==b.width || span.height!==b.height || text.y!==calibration.textOffsetY) throw new Error('button_baseline_native_geometry_changed');
    }
    const component = api.createComponentFromNode(frame);
    createdNodeIds.push(component.id);
    component.description = `Unadmitted official runtime candidate: ${spec.logicalId}; ${spec.sourceVersion}`;
    // Read only from created native nodes. Never copy source bounds into capture output.
    result.nativeObservation = { componentReference: component.id, textReference: text.id,
      ...(span ? {spanReference:span.id,spanBounds:{x:span.x,y:span.y,width:span.width,height:span.height},
        textOffsetY:text.y,calibrationEvidenceHashes:calibration.evidenceHashes} : {}),
      component: {type:component.type, width:component.width, height:component.height,
        fills:component.fills, strokes:component.strokes, strokeWeight:component.strokeWeight,
        strokeAlign:component.strokeAlign, cornerRadius:component.cornerRadius,
        paddingTop:component.paddingTop, paddingRight:component.paddingRight,
        paddingBottom:component.paddingBottom, paddingLeft:component.paddingLeft},
      text: {type:text.type, characters:text.characters, width:text.width, height:text.height,
        x:text.x, y:text.y, fontName:text.fontName, fontWeight:text.fontWeight,
        fontSize:text.fontSize, lineHeight:text.lineHeight, fills:text.fills} };
    result.status = 'PASS';
  } catch (error) { result.issues.push({code:String(error.message)}); }
  return result;
}
