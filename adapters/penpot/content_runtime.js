// Declared text overrides on genuine linked copies only; never edit a source master.
function preflightPenpotNativeContent(copy, mappings) {
  if (!copy.isComponentCopyInstance() || copy.isComponentMainInstance()) throw new Error('content_requires_linked_copy');
  if(![copy.x,copy.y,copy.width,copy.height].every(Number.isFinite)||copy.width<=0||copy.height<=0)throw new Error('invalid_content_geometry');
  const texts=[];function walk(n){if(n.type==='text')texts.push(n);for(const c of n.children||[])walk(c);}walk(copy);
  const pending=[], names=new Set();
  for(const mapping of mappings){
    if(names.has(mapping.name))throw new Error('duplicate_content_target');names.add(mapping.name);
    const found=texts.filter(n=>n.name===mapping.name);
    if(found.length!==1||typeof mapping.text!=='string'||!mapping.text||/[\r\n]/.test(mapping.text))throw new Error('invalid_content_target');
    const n=found[0];
    if(![n.x,n.y,n.width,n.height].every(Number.isFinite)||n.width<=0||n.height<=0)throw new Error('invalid_text_geometry');
    if(n.characters!==(mapping.expectedText??mapping.originalText))throw new Error('stale_content_target');
    if(Object.entries(mapping.style).some(([key,value])=>n[key]!==value))throw new Error('content_style_changed');
    pending.push({n,before:n.characters,mapping});
  }
  return pending;
}

async function applyPenpotNativeContent(api, copy, mappings) {
  const pending=preflightPenpotNativeContent(copy,mappings);
  const box={x:copy.x,y:copy.y,width:copy.width,height:copy.height},component=copy.component()?.id;
  try{
    for(const {n,mapping} of pending)n.characters=mapping.text;
    await api.waitForLayoutUpdate();
    if(!copy.isComponentCopyInstance()||copy.component()?.id!==component||Object.entries(box).some(([k,v])=>!Number.isFinite(copy[k])||Math.abs(copy[k]-v)>1e-6))throw new Error('content_changed_instance_geometry');
    for(const {n,mapping} of pending){
      if(n.characters!==mapping.text||Object.entries(mapping.style).some(([k,v])=>n[k]!==v))throw new Error('content_readback_mismatch');
      if(n.x<copy.x-1e-6||n.y<copy.y-1e-6||n.x+n.width>copy.x+copy.width+1e-6||n.y+n.height>copy.y+copy.height+1e-6)throw new Error('content_text_overflow');
    }
  }catch(error){
    for(const {n,before} of pending)n.characters=before;
    await api.waitForLayoutUpdate();
    throw error;
  }
  return {copyReference:copy.id,componentReference:component,mutatedTextIds:pending.map(p=>p.n.id),createdNodeIds:[]};
}

async function executePenpotContentAdapter(api,payload){
  if(payload.platform!=='penpot'||api.currentFile?.id!==payload.fileReference)throw new Error('file_reference_mismatch');
  const specs=[];function walk(n){if(n.nativeContent?.length)specs.push(n);for(const c of n.children||[])walk(c);}walk(payload.page);
  // Validate every source text against its master before any new page is created.
  for(const spec of specs){
    const main=api.library.local.components.find(c=>c.id===spec.componentReference)?.mainInstance();
    if(!main?.isComponentMainInstance())throw new Error('missing_content_master');
    const texts=[];function scan(n){if(n.type==='text')texts.push(n);for(const c of n.children||[])scan(c);}scan(main);
    for(const m of spec.nativeContent){
      const found=texts.filter(n=>n.name===m.name);
      if(found.length!==1||found[0].characters!==m.originalText||Object.entries(m.style).some(([k,v])=>found[0][k]!==v))throw new Error('content_master_changed');
    }
  }
  const execution=await executePenpotAdapter(api,payload);
  if(execution.status!=='EXECUTED')return execution;
  try{
    for(const spec of specs)await applyPenpotNativeContent(api,api.currentPage.getShapeById(execution.nodeMap[spec.id]),spec.nativeContent);
    return {...execution,contentInjectedUiIrIds:specs.map(s=>s.id),finalAcceptance:'NOT_RUN'};
  }catch(error){return {...execution,status:'FAIL',nativeExecution:'PARTIAL',finalAcceptance:'NOT_RUN',issues:[{code:'native_content_injection_failed',detail:String(error)}]};}
}
