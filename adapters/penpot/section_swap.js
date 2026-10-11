// Public SDK component swap. Independent of the frozen native-content executor.
async function swapPenpotSectionComponent(api,payload,execution,request,beforeCapture){
  if(api.currentFile?.id!==execution.fileReference||payload.fileReference!==execution.fileReference||
     api.currentPage?.id!==execution.pageReference||execution.status!=='EXECUTED'||
     request.baseUiIrSha256!==execution.uiIrSha256||request.updatedUiIrSha256!==payload.uiIrSha256)
    throw new Error('section_swap_context_mismatch');
  if(beforeCapture?.status!=='CAPTURED'||beforeCapture.fileReference!==execution.fileReference||
     beforeCapture.pageReference!==execution.pageReference||beforeCapture.rootReference!==execution.rootReference||
     beforeCapture.fileRevision!==api.currentFile.revn)throw new Error('section_swap_stale_capture');
  const page=api.currentPage,root=page.getShapeById(execution.rootReference);
  if(!root||root.parent?.id!==page.root.id||execution.nodeMap[payload.page.id]!==root.id)throw new Error('section_swap_root_mismatch');
  const before=snapshotPenpotPatchRoot(root);
  if(JSON.stringify(before)!==JSON.stringify(beforeCapture.nodes))throw new Error('section_swap_changed_checkpoint');
  let target,section;
  function walk(spec,region=null,parent=null){
    if(spec.type==='Section'||(parent===payload.page.id&&spec.type==='Frame'&&request.sectionIds?.includes(spec.id)))region=spec.id;
    if(spec.id===request.uiIrId){if(target)throw new Error('section_swap_duplicate_target');target=spec;section=region;}
    for(const child of spec.children||[])walk(child,region,spec.id);
  }walk(payload.page);
  const copy=page.getShapeById(execution.nodeMap[request.uiIrId]);
  let ancestor=copy;while(ancestor&&ancestor.id!==root.id)ancestor=ancestor.parent;
  if(!target||target.type!=='ComponentInstance'||!section||!ancestor||!copy||
     !execution.createdNodeIds.includes(copy.id)||!copy.isComponentCopyInstance()||copy.isComponentMainInstance()||
     copy.component()?.id!==request.expectedComponentReference||target.componentReference===request.expectedComponentReference)
    throw new Error('section_swap_invalid_target');
  if(typeof copy.swapComponent!=='function')throw new Error('unsupported_component_swap');
  // Content overrides need a separate declared binding after swapping; reject for now.
  if(target.nativeContent?.length)throw new Error('unsupported_swap_content');
  const component=api.library.local.components.find(c=>c.id===target.componentReference),main=component?.mainInstance();
  if(!main?.isComponentMainInstance()||main.component()?.id!==component.id)throw new Error('section_swap_missing_master');
  const box={x:copy.x,y:copy.y,width:copy.width,height:copy.height},identity={id:copy.id,parent:copy.parent.id,name:copy.name};
  if(!Object.values(box).every(Number.isFinite)||box.width<=0||box.height<=0||
     main.width!==box.width||main.height!==box.height||target.layout?.width?.mode!=='fixed'||
     target.layout?.height?.mode!=='fixed'||target.layout.width.value!==box.width||target.layout.height.value!==box.height)
    throw new Error('section_swap_source_size_mismatch');
  const oldIds=new Set();function collect(n,set){set.add(n.id);for(const child of n.children||[])collect(child,set);}collect(copy,oldIds);
  const masterBefore=snapshotPenpotPatchRoot(main);
  let after;
  try{
    copy.swapComponent(component);
    // The native SDK replaces the copy name with the source master's name.
    // Restore this existing logical identity without touching source visuals.
    copy.name=identity.name;
    await api.waitForLayoutUpdate();
    const current=page.getShapeById(identity.id);
    if(!current||!current.isComponentCopyInstance()||current.isComponentMainInstance()||current.component()?.id!==component.id)
      throw new Error('section_swap_link_mismatch');
    if(current.parent?.id!==identity.parent||current.name!==identity.name||Object.entries(box).some(([k,v])=>current[k]!==v))
      throw new Error('section_swap_identity_or_geometry_changed');
    const newIds=new Set();collect(current,newIds);after=snapshotPenpotPatchRoot(root);
    if(JSON.stringify(masterBefore)!==JSON.stringify(snapshotPenpotPatchRoot(main)))throw new Error('section_swap_changed_source_master');
    if(JSON.stringify(before.filter(n=>!oldIds.has(n.id)))!==JSON.stringify(after.filter(n=>!newIds.has(n.id))))
      throw new Error('section_swap_changed_unrelated_nodes');
    return {status:'SWAPPED',scope:'penpot-native-section-component-swap',finalAcceptance:'NOT_RUN',
      fileReference:execution.fileReference,pageReference:page.id,rootReference:root.id,
      baseUiIrSha256:execution.uiIrSha256,updatedUiIrSha256:payload.uiIrSha256,
      beforeRevision:beforeCapture.fileRevision,afterRevision:api.currentFile.revn,changedSections:[section],
      swappedCopyId:identity.id,previousComponentReference:request.expectedComponentReference,componentReference:component.id,
      createdNodeIds:[...newIds].filter(id=>!oldIds.has(id)),removedNodeIds:[...oldIds].filter(id=>!newIds.has(id)),before,after,
      sourceMasterBefore:masterBefore,sourceMasterAfter:snapshotPenpotPatchRoot(main)};
  }catch(error){
    // Swapping back can generate different descendant IDs; never claim exact rollback.
    after=snapshotPenpotPatchRoot(root);
    return {status:'FAIL',nativeExecution:'PARTIAL',recoveryRequired:true,finalAcceptance:'NOT_RUN',
      fileReference:execution.fileReference,pageReference:page.id,rootReference:root.id,
      swappedCopyId:identity.id,before,after,issues:[{code:'section_swap_failed',detail:String(error)}]};
  }
}
