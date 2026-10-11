// Content extension; the historical TASK-009 runtime stays byte-identical.
async function executeFigmaContentAdapter(api,payload){
  if(api.fileKey!==payload.fileReference)throw new Error('content_file_reference_mismatch');
  const specs=[];
  function scan(n,region=null,parent=null){
    if(n.type==='Section'||(parent===payload.page.id&&n.type==='Frame'))region=n.id;
    if(n.nativeContent?.length)specs.push({spec:n,region});
    for(const child of n.children||[])scan(child,region,n.id);
  }scan(payload.page);
  for(const {spec,region} of specs){
    if(!region)throw new Error('content_requires_declared_region');
    const main=await api.getNodeByIdAsync(spec.componentReference);
    if(main?.type!=='COMPONENT')throw new Error('missing_content_master');
    for(const mapping of spec.nativeContent){
      const found=main.findAllWithCriteria({types:['TEXT']}).filter(n=>n.name===mapping.name);
      if(found.length!==1||found[0].characters!==mapping.originalText||Object.entries(mapping.style).some(([k,v])=>JSON.stringify(found[0][k])!==JSON.stringify(v)))throw new Error('content_source_master_changed');
    }
  }
  const built=await executeFigmaAdapter(api,payload);
  if(built.status!=='PASS')return built;
  const execution={...built,status:'EXECUTED',fileReference:api.fileKey},targets=[];
  try{
    for(const {spec,region} of specs){
      const owner=await api.getNodeByIdAsync(built.nodeMap[spec.id]);
      for(const mapping of spec.nativeContent){
        const found=owner.findAllWithCriteria({types:['TEXT']}).filter(n=>n.name===mapping.name);
        if(found.length!==1)throw new Error('created_content_target_ambiguous');
        targets.push({ownerReference:owner.id,textReference:found[0].id,name:mapping.name,
          componentReference:spec.componentReference,sectionReference:built.nodeMap[region],
          expectedText:mapping.originalText,text:mapping.text,style:mapping.style});
      }
    }
    if(!targets.length)return {...execution,finalAcceptance:'NOT_RUN'};
    const root=await api.getNodeByIdAsync(built.rootReference);
    const before={status:'CAPTURED',fileReference:api.fileKey,pageReference:api.currentPage.id,rootReference:root.id,nodes:await snapshotFigmaContentRoot(root)};
    const patch=await patchFigmaSectionContent(api,execution,{targets},before);
    return {...execution,status:patch.status==='PATCHED'?'EXECUTED':'FAIL',nativeExecution:patch.status==='PATCHED'?'EXECUTED':'PARTIAL',
      mutatedNodeIds:patch.mutatedNodeIds,contentPatch:patch,finalAcceptance:'NOT_RUN'};
  }catch(error){return {...execution,status:'FAIL',nativeExecution:'PARTIAL',recoveryRequired:true,
    finalAcceptance:'NOT_RUN',issues:[{code:'native_content_injection_failed',detail:String(error)}]};}
}
