// Read native properties and export PNG without changing the canvas.
async function captureNativeComponent(api, request) {
  const result = {scope:'figma_native_component_capture', status:'FAIL', evidenceKind:'native-platform-export',
    evidenceScope:request.evidenceScope || 'production', captureId:request.captureId,
    exporterVersion:'figma-native-export-v0.1.1', fileReference:api.fileKey,
    logicalId:request.logicalId, componentReference:request.componentReference,
    createdNodeIds:[], mutatedNodeIds:[], admissionEligible:false, fidelityGate:'NOT_RUN', issues:[]};
  try {
    if (api.editorType !== 'figma' || api.fileKey !== request.fileReference) throw new Error('capture_file_mismatch');
    if (!request.captureId || !request.logicalId || !['production','test-fixture'].includes(result.evidenceScope)) throw new Error('invalid_capture_identity');
    const page = await api.getNodeByIdAsync(request.pageReference);
    if (!page || page.type !== 'PAGE') throw new Error('capture_page_missing');
    if (request.pageAlreadySelected) {
      if (api.currentPage?.id !== page.id) throw new Error('capture_current_page_mismatch');
    } else {
      await api.setCurrentPageAsync(page);
    }
    const root = await api.getNodeByIdAsync(request.componentReference);
    if (!root || root.type !== 'COMPONENT' || root.parent?.id !== page.id) throw new Error('capture_component_missing');
    // Load the existing text's actual font segments before inspecting/exporting it.
    const fonts = new Map();
    for (const node of root.findAllWithCriteria({types:['TEXT']})) {
      for (const segment of node.getStyledTextSegments(['fontName'])) {
        fonts.set(JSON.stringify(segment.fontName),segment.fontName);
      }
    }
    for (const font of fonts.values()) await api.loadFontAsync(font);
    const nodes=[];
    function copy(value) {
      if (value === api.mixed) return {nativeMixed:true};
      return JSON.parse(JSON.stringify(value));
    }
    function visit(node,parentReference) {
      const item={reference:node.id,parentReference,type:node.type,name:node.name,
        localBounds:{x:node.x,y:node.y,width:node.width,height:node.height},
        absoluteBounds:copy(node.absoluteBoundingBox),properties:{}};
      for (const key of ['visible','opacity','fills','strokes','strokeWeight','strokeAlign','cornerRadius',
          'effects','rotation','blendMode','isMask','clipsContent','layoutMode','layoutSizingHorizontal','layoutSizingVertical',
          'primaryAxisAlignItems','counterAxisAlignItems','itemSpacing','strokesIncludedInLayout',
          'paddingTop','paddingRight','paddingBottom','paddingLeft','layoutPositioning']) {
        if (key in node) item.properties[key]=copy(node[key]);
      }
      for(const key of ['strokeTopWeight','strokeRightWeight','strokeBottomWeight','strokeLeftWeight'])if(key in node)item.properties[key]=copy(node[key]);
      if (node.type === 'TEXT') {
        for (const key of ['characters','fontName','fontWeight','fontSize','lineHeight',
            'letterSpacing','textAutoResize','textAlignHorizontal','textAlignVertical']) item.properties[key]=copy(node[key]);
        for (const key of ['textCase','textDecoration','paragraphIndent','paragraphSpacing']) {
          if (key in node) item.properties[key]=copy(node[key]);
        }
      }
      nodes.push(item);
      if ('children' in node) for (const child of node.children) visit(child,node.id);
    }
    visit(root,null);
    if (!root.absoluteBoundingBox || root.width<=0 || root.height<=0) throw new Error('capture_empty_component');
    const bytes=await root.exportAsync({format:'PNG',constraint:{type:'SCALE',value:1},useAbsoluteBounds:true});
    result.nativeEvidence={pageReference:page.id,nodes,rootReference:root.id};
    result.raster={format:'PNG',scale:1,background:'native-transparent',bytes:Array.from(bytes)};
    result.limitations=['No per-glyph bounds or CSS-normalized measurements are inferred.',
      'Host result and hashes alone do not authenticate platform provenance.'];
    result.status='PASS';
  } catch(error) { result.issues.push({code:String(error.message)}); }
  return result;
}

async function finishCandidateCapture(api, built, request) {
  if (built.status !== 'PASS') return built;
  const componentReference=built.nativeObservation.componentReference;
  const capture=await captureNativeComponent(api,{...request,componentReference,
    captureId:request.captureId || `${request.fileReference}/${request.logicalId}/${componentReference}`,
    pageAlreadySelected:true});
  return {...built,status:capture.status,nativeCapture:capture,
    issues:[...(built.issues || []),...capture.issues]};
}
