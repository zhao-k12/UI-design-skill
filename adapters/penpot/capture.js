// Separate read-only observation. Requires the caller to open the exact output page.
async function capturePenpotOutput(api, request) {
  if (api.currentFile?.id !== request.fileReference || api.currentPage?.id !== request.pageReference) throw new Error('capture_context_mismatch');
  const revision = api.currentFile.revn;
  const page = api.currentPage, root = page.getShapeById(request.rootReference);
  if (!root || root.parent?.id !== page.root.id) throw new Error('capture_root_mismatch');
  if (![root.width,root.height].every(v => Number.isFinite(v) && v > 0 && v <= 4096) || root.width * root.height > 4000000) throw new Error('capture_geometry_out_of_bounds');
  if (!request.nodeMap || typeof request.nodeMap !== 'object' || Array.isArray(request.nodeMap) ||
      new Set(Object.values(request.nodeMap)).size !== Object.keys(request.nodeMap).length) throw new Error('capture_invalid_node_map');
  const evidence = [], topology = [], seen = new Set();
  function observeTree(n, depth = 0) {
    if (depth > 100 || seen.size >= 20000 || seen.has(n.id)) throw new Error('capture_invalid_tree');
    seen.add(n.id);
    topology.push({nodeId:n.id,parentReference:n.parent?.id,type:n.type,name:n.name,
      childNodeIds:(n.flex ? [...(n.children || [])].reverse() : (n.children || [])).map(child => child.id),
      ...(n.flex ? {nativeStackChildNodeIds:(n.children || []).map(child => child.id),childOrderNormalization:'penpot-stack-to-layout-reverse'} : {}),
      x:n.x,y:n.y,width:n.width,height:n.height});
    for (const child of n.children || []) observeTree(child, depth + 1);
  }
  observeTree(root);
  function editableTextCount(n) { return (n.type === 'text' ? 1 : 0) + (n.children || []).reduce((sum,c) => sum + editableTextCount(c), 0); }
  for (const [uiIrId, nodeId] of Object.entries(request.nodeMap)) {
    const n = page.getShapeById(nodeId);
    if (!n) throw new Error(`capture_missing_node: ${uiIrId}`);
    let ancestor = n;
    while (ancestor && ancestor.id !== root.id) ancestor = ancestor.parent;
    if (!ancestor) throw new Error(`capture_node_outside_root: ${uiIrId}`);
    const f = n.flex, l = n.layoutChild;
    const entry = {uiIrId,nodeId,type:n.type,name:n.name,parentReference:n.parent?.id,
      x:n.x,y:n.y,width:n.width,height:n.height,fills:n.fills,strokes:n.strokes,
      opacity:n.opacity,borderRadius:n.borderRadius,clipContent:n.clipContent,
      rotation:n.rotation,flipX:n.flipX,flipY:n.flipY,hidden:n.hidden,visible:n.visible,blendMode:n.blendMode,shadows:n.shadows,blur:n.blur,
      horizontalSizing:l?.horizontalSizing || f?.horizontalSizing,
      verticalSizing:l?.verticalSizing || f?.verticalSizing};
    if (f) entry.flex = {dir:f.dir,wrap:f.wrap,rowGap:f.rowGap,columnGap:f.columnGap,
      topPadding:f.topPadding,rightPadding:f.rightPadding,bottomPadding:f.bottomPadding,leftPadding:f.leftPadding,
      justifyContent:f.justifyContent,alignItems:f.alignItems};
    if (n.type === 'text') Object.assign(entry,{characters:n.characters,fontId:n.fontId,fontFamily:n.fontFamily,
      fontVariantId:n.fontVariantId,fontWeight:n.fontWeight,fontStyle:n.fontStyle,fontSize:n.fontSize,
      lineHeight:n.lineHeight,letterSpacing:n.letterSpacing,growType:n.growType});
    if (n.isComponentCopyInstance()) Object.assign(entry,{isComponentCopy:true,componentReference:n.component()?.id,
      mainReference:n.component()?.mainInstance()?.id,editableTextCount:editableTextCount(n)});
    evidence.push(entry);
  }
  if (!Number.isInteger(revision) || revision < 0) throw new Error('capture_invalid_revision');
  const renderSnapshot=JSON.stringify(Object.values(request.nodeMap).map(id=>{
    const n=page.getShapeById(id);return {id:n.id,x:n.x,y:n.y,width:n.width,height:n.height,fills:n.fills,strokes:n.strokes,opacity:n.opacity,rotation:n.rotation,flipX:n.flipX,flipY:n.flipY,hidden:n.hidden,visible:n.visible,blendMode:n.blendMode,shadows:n.shadows,blur:n.blur};
  }));
  const png = await root.export({type:'png',scale:1});
  const afterSnapshot=JSON.stringify(Object.values(request.nodeMap).map(id=>{
    const n=page.getShapeById(id);return {id:n.id,x:n.x,y:n.y,width:n.width,height:n.height,fills:n.fills,strokes:n.strokes,opacity:n.opacity,rotation:n.rotation,flipX:n.flipX,flipY:n.flipY,hidden:n.hidden,visible:n.visible,blendMode:n.blendMode,shadows:n.shadows,blur:n.blur};
  }));
  if(renderSnapshot!==afterSnapshot)throw new Error('capture_render_state_changed');
  if (api.currentFile?.id !== request.fileReference || api.currentPage?.id !== request.pageReference ||
      api.currentFile.revn !== revision) throw new Error('capture_document_changed');
  let binary = '';
  for (let i = 0; i < png.length; i += 8192) binary += String.fromCharCode(...png.subarray(i,i+8192));
  return {status:'CAPTURED',platform:'penpot',scope:'production',evidenceKind:'native-platform-export',exporterVersion:'penpot-native-output-v0.1.1',
    finalAcceptance:'NOT_RUN',fileReference:api.currentFile.id,fileRevision:revision,pageReference:page.id,
    rootReference:root.id,createdNodeIds:[],mutatedNodeIds:[],topology,evidence,nativePngBase64:btoa(binary)};
}
