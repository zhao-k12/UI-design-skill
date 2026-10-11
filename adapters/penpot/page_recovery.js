// Explicit source defaults on the exact existing output; never edit masters or copies.
async function restorePenpotPageDefaults(api,payload,execution){
  if(api.currentFile?.id!==payload.fileReference||api.currentPage?.id!==execution.pageReference||execution.fileReference!==payload.fileReference||execution.uiIrSha256!==payload.uiIrSha256||execution.status!=='EXECUTED')throw new Error('page_defaults_context_mismatch');
  const page=api.currentPage,root=page.getShapeById(execution.rootReference),pending=[];
  if(!root||root.parent?.id!==page.root.id||execution.nodeMap[payload.page.id]!==root.id)throw new Error('page_defaults_root_mismatch');
  const created=new Set(execution.createdNodeIds),normalize=n=>String(n).split('/').map(x=>x.trim()).join('/');
  function check(id,opacity,name){
    const n=page.getShapeById(id);let ancestor=n;
    while(ancestor&&ancestor.id!==root.id)ancestor=ancestor.parent;
    if(!n||!ancestor||!created.has(id)||n.isComponentCopyInstance()||n.isComponentMainInstance()||normalize(n.name)!==normalize(name)||![1,null].includes(n.opacity)||opacity!==1)throw new Error('page_defaults_identity_mismatch');
    if(n.opacity===null)pending.push(n);
  }
  function walk(spec){
    if(!spec.componentReference)check(execution.nodeMap[spec.id],spec.style.opacity??1,spec.type==='Page'?`UI-IR/${payload.documentId}/${spec.id}`:spec.name);
    for(const child of spec.children||[])walk(child);
  }
  walk(payload.page);
  for(const id of execution.helperNodeIds){
    const n=page.getShapeById(id);
    if(!n||!normalize(n.name).includes('/grid-'))throw new Error('page_defaults_helper_mismatch');
    check(id,1,n.name);
  }
  for(const n of pending)n.opacity=1;
  await api.waitForLayoutUpdate();
  return {status:'SOURCE_DEFAULTS_RESTORED',platform:'penpot',fileReference:payload.fileReference,pageReference:execution.pageReference,rootReference:root.id,createdNodeIds:[],mutatedNodeIds:pending.map(n=>n.id),admissionEligible:false};
}

// Reapply linked source masters using the public reset operation; keep real copies.
async function resetPenpotIconCopies(api,payload,execution){
  if(api.currentFile?.id!==payload.fileReference||api.currentPage?.id!==execution.pageReference||execution.fileReference!==payload.fileReference||execution.status!=='EXECUTED')throw new Error('icon_copies_context_mismatch');
  const specs=[];function walk(s){if(s.type==='IconInstance')specs.push(s);for(const child of s.children||[])walk(child);}walk(payload.page);
  const copies=[];
  for(const spec of specs){
    const copy=api.currentPage.getShapeById(execution.nodeMap[spec.id]);let ancestor=copy;
    while(ancestor&&ancestor.id!==execution.rootReference)ancestor=ancestor.parent;
    if(!ancestor||!copy?.isComponentCopyInstance()||copy.component()?.id!==spec.componentReference||copy.width!==24||copy.height!==24)throw new Error('icon_copies_identity_mismatch');
    copies.push({copy,spec});
  }
  const before=copies.map(({copy})=>({id:copy.id,x:copy.x,y:copy.y,children:copy.children.map(n=>n.id)}));
  for(const {copy,spec} of copies){copy.resetOverrides();copy.name=spec.name;copy.layoutChild.horizontalSizing='fix';copy.layoutChild.verticalSizing='fix';}
  await api.waitForLayoutUpdate();
  if(copies.some(({copy},i)=>copy.x!==before[i].x||copy.y!==before[i].y||!copy.isComponentCopyInstance()||JSON.stringify(copy.children.map(n=>n.id))!==JSON.stringify(before[i].children)))throw new Error('icon_copies_reset_requires_recovery');
  return {status:'LINKED_ICON_COPIES_RESET',platform:'penpot',fileReference:payload.fileReference,pageReference:execution.pageReference,createdNodeIds:[],mutatedNodeIds:copies.map(({copy})=>copy.id),admissionEligible:false};
}
