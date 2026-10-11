// TASK-015: in-place content patch of exact existing linked copies; no page rebuild.
function snapshotPenpotPatchRoot(root){
  const nodes=[];
  function walk(n){
    const item={id:n.id,parent:n.parent?.id,type:n.type,name:n.name,x:n.x,y:n.y,width:n.width,height:n.height,
      children:(n.children||[]).map(c=>c.id),fills:n.fills,strokes:n.strokes,opacity:n.opacity,
      rotation:n.rotation,hidden:n.hidden,clipContent:n.clipContent,borderRadius:n.borderRadius,
      isCopy:n.isComponentCopyInstance(),isMain:n.isComponentMainInstance()};
    if(item.isCopy||item.isMain)item.component=n.component()?.id;
    if(n.type==='text')for(const key of ['characters','fontId','fontVariantId','fontFamily','fontWeight','fontStyle','fontSize','lineHeight','letterSpacing','growType'])item[key]=n[key];
    nodes.push(item);for(const c of n.children||[])walk(c);
  }
  walk(root);return nodes;
}

async function patchPenpotSectionContent(api,payload,execution,request){
  if(api.currentFile?.id!==execution.fileReference||payload.fileReference!==execution.fileReference||
     api.currentPage?.id!==execution.pageReference||execution.status!=='EXECUTED'||
     request.baseUiIrSha256!==execution.uiIrSha256||request.updatedUiIrSha256!==payload.uiIrSha256)
    throw new Error('section_patch_context_mismatch');
  if(!Number.isInteger(request.expectedRevision)||request.expectedRevision!==api.currentFile.revn)throw new Error('section_patch_stale_revision');
  const page=api.currentPage,root=page.getShapeById(execution.rootReference);
  if(!root||execution.nodeMap[payload.page.id]!==root.id||root.parent?.id!==page.root.id)throw new Error('section_patch_root_mismatch');
  const specs=new Map(),sections=new Map();
  function walk(spec,section=null,parentId=null){
    // Older admitted UI-IR uses top-level Frames for named regions. They must
    // be explicitly declared; arbitrary nested Frames never become Sections.
    if(spec.type==='Section'||(parentId===payload.page.id&&spec.type==='Frame'&&request.sectionIds?.includes(spec.id)))section=spec.id;
    specs.set(spec.id,spec);sections.set(spec.id,section);
    for(const c of spec.children||[])walk(c,section,spec.id);
  }walk(payload.page);
  if(!Array.isArray(request.uiIrIds)||!request.uiIrIds.length||new Set(request.uiIrIds).size!==request.uiIrIds.length)throw new Error('invalid_patch_targets');
  const owned=new Set(execution.createdNodeIds),pending=[],allowed=new Set();
  for(const id of request.uiIrIds){
    const spec=specs.get(id),copy=page.getShapeById(execution.nodeMap[id]);
    let ancestor=copy;while(ancestor&&ancestor.id!==root.id)ancestor=ancestor.parent;
    if(!spec?.nativeContent?.length||!sections.get(id)||!ancestor||!owned.has(copy.id)||!copy.isComponentCopyInstance()||
       copy.isComponentMainInstance()||copy.component()?.id!==spec.componentReference)throw new Error('unsupported_section_patch_target');
    const maps=spec.nativeContent.map(m=>({...m,expectedText:request.expectedCharacters?.[id]?.[m.name]}));
    if(maps.some(m=>typeof m.expectedText!=='string'))throw new Error('missing_patch_content_checkpoint');
    preflightPenpotNativeContent(copy,maps);
    function own(n){allowed.add(n.id);for(const c of n.children||[])own(c);}own(copy);
    pending.push({id,copy,maps});
  }
  const before=snapshotPenpotPatchRoot(root),revision=api.currentFile.revn,applied=[];
  try{
    // No writes before every requested copy is identified; each helper also preflights its text.
    for(const p of pending){await applyPenpotNativeContent(api,p.copy,p.maps);applied.push(p);}
    const after=snapshotPenpotPatchRoot(root);
    if(JSON.stringify(before.filter(n=>!allowed.has(n.id)))!==JSON.stringify(after.filter(n=>!allowed.has(n.id))))throw new Error('section_patch_changed_unrelated_nodes');
    if(JSON.stringify(before.map(n=>n.id))!==JSON.stringify(after.map(n=>n.id)))throw new Error('section_patch_changed_topology');
    return {status:'PATCHED',scope:'penpot-native-section-content-patch',finalAcceptance:'NOT_RUN',fileReference:execution.fileReference,
      pageReference:page.id,rootReference:root.id,beforeRevision:revision,afterRevision:api.currentFile.revn,
      baseUiIrSha256:execution.uiIrSha256,updatedUiIrSha256:payload.uiIrSha256,
      changedSections:[...new Set(pending.map(p=>sections.get(p.id)))],createdNodeIds:[],removedNodeIds:[],
      patchedCopyIds:pending.map(p=>p.copy.id),before,after};
  }catch(error){
    for(const p of applied.reverse()){
      const reverse=p.maps.map(m=>({...m,expectedText:m.text,text:m.expectedText}));
      try{await applyPenpotNativeContent(api,p.copy,reverse);}catch(rollback){throw new Error(`section_patch_recovery_required: ${error}; ${rollback}`);}
    }
    throw error;
  }
}

// Read independently after mutation. Caller must retain/export this separately from execution.
async function capturePenpotSectionPatch(api,execution){
  if(api.currentFile?.id!==execution.fileReference||api.currentPage?.id!==execution.pageReference)throw new Error('patch_capture_context_mismatch');
  const root=api.currentPage.getShapeById(execution.rootReference),revision=api.currentFile.revn;
  if(!root)throw new Error('patch_capture_missing_root');
  const nodes=snapshotPenpotPatchRoot(root),png=await root.export({type:'png',scale:1});
  if(revision!==api.currentFile.revn||JSON.stringify(nodes)!==JSON.stringify(snapshotPenpotPatchRoot(root)))throw new Error('patch_capture_state_changed');
  let binary='';for(let i=0;i<png.length;i+=8192)binary+=String.fromCharCode(...png.subarray(i,i+8192));
  return {status:'CAPTURED',scope:'penpot-native-section-patch-capture',fileReference:execution.fileReference,
    pageReference:execution.pageReference,rootReference:root.id,fileRevision:revision,nodes,nativePngBase64:btoa(binary)};
}
