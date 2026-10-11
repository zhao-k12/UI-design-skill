// Existing native text primitives and declared linked-copy content only.
async function patchPenpotPrimitiveContent(api,execution,request,beforeCapture){
  if(api.currentFile?.id!==execution.fileReference||api.currentPage?.id!==execution.pageReference||execution.status!=='EXECUTED')throw new Error('primitive_content_context_mismatch');
  const page=api.currentPage,root=page.getShapeById(execution.rootReference);
  if(!root||root.parent?.id!==page.root.id||beforeCapture?.status!=='CAPTURED'||
     ['fileReference','pageReference','rootReference'].some(k=>beforeCapture[k]!==execution[k]))throw new Error('primitive_content_capture_context');
  const before=snapshotPenpotPatchRoot(root);
  if(beforeCapture.fileRevision!==api.currentFile.revn||JSON.stringify(before)!==JSON.stringify(beforeCapture.nodes))throw new Error('primitive_content_stale_snapshot');
  if(!Array.isArray(request.targets)||!request.targets.length)throw new Error('primitive_content_empty_request');
  const owned=new Set(execution.createdNodeIds),seen=new Set(),pending=[];
  for(const target of request.targets){
    const owner=page.getShapeById(target.ownerReference),text=page.getShapeById(target.textReference);
    if(!owner||!owned.has(owner.id)||!text||text.type!=='text'||seen.has(text.id))throw new Error('primitive_content_unknown_target');seen.add(text.id);
    let parent=owner,region=false;while(parent&&parent.id!==root.id){if(parent.id===target.sectionReference)region=true;parent=parent.parent;}
    if(!parent||!region)throw new Error('primitive_content_outside_section');
    if(target.componentReference){
      if(!owner.isComponentCopyInstance()||owner.isComponentMainInstance()||owner.component()?.id!==target.componentReference)throw new Error('primitive_content_requires_linked_copy');
      let ancestor=text;while(ancestor&&ancestor.id!==owner.id)ancestor=ancestor.parent;
      if(!ancestor)throw new Error('primitive_content_outside_copy');
    }else if(owner.id!==text.id||!owned.has(text.id))throw new Error('primitive_content_owner_mismatch');
    if(text.name!==target.name||text.characters!==target.expectedText||typeof target.text!=='string'||!target.text||/[\r\n]/.test(target.text)||
       !target.style||Object.entries(target.style).some(([k,v])=>text[k]!==v))throw new Error('primitive_content_stale_text_or_style');
    pending.push({owner,text,target});
  }
  try{
    for(const {text,target} of pending)text.characters=target.text;
    await api.waitForLayoutUpdate();
    const after=snapshotPenpotPatchRoot(root);
    if(JSON.stringify(before.map(n=>n.id))!==JSON.stringify(after.map(n=>n.id)))throw new Error('primitive_content_changed_topology');
    if(JSON.stringify(before.filter(n=>!seen.has(n.id)))!==JSON.stringify(after.filter(n=>!seen.has(n.id))))throw new Error('primitive_content_changed_unrelated_nodes');
    for(const {owner,text,target} of pending){
      if(text.characters!==target.text||Object.entries(target.style).some(([k,v])=>text[k]!==v))throw new Error('primitive_content_readback_mismatch');
      const region=target.componentReference?owner:text.parent;
      if(![text.x,text.y,text.width,text.height].every(Number.isFinite)||text.width<=0||text.height<=0||
         text.x<region.x-1e-6||text.y<region.y-1e-6||text.x+text.width>region.x+region.width+1e-6||text.y+text.height>region.y+region.height+1e-6)
        throw new Error('primitive_content_text_overflow');
    }
    return {status:'PATCHED',scope:'penpot-native-primitive-content-patch',fileReference:execution.fileReference,
      pageReference:execution.pageReference,rootReference:root.id,beforeRevision:beforeCapture.fileRevision,afterRevision:api.currentFile.revn,
      mutatedNodeIds:[...seen],createdNodeIds:[],removedNodeIds:[],changedSections:[...new Set(pending.map(p=>p.target.sectionReference))],
      before,after,finalAcceptance:'NOT_RUN'};
  }catch(error){
    for(const {text,target} of pending)text.characters=target.expectedText;
    await api.waitForLayoutUpdate();const restored=snapshotPenpotPatchRoot(root);
    return {status:'FAIL',nativeExecution:'PARTIAL',recoveryRequired:JSON.stringify(restored)!==JSON.stringify(before),
      fileReference:execution.fileReference,pageReference:execution.pageReference,rootReference:root.id,
      before,after:restored,mutatedNodeIds:[...seen],createdNodeIds:[],removedNodeIds:[],
      issues:[{code:'primitive_content_failed',detail:String(error)}],finalAcceptance:'NOT_RUN'};
  }
}
