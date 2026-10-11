// Fill owned empty auto-layout role frames on an existing page and Cell.
async function fillFigmaCellSlots(api,execution,request,beforeSha256){
  if(api.fileKey!==execution.fileReference||api.currentPage.id!==execution.pageReference||execution.status!=='EXECUTED')throw new Error('slot_context_mismatch');
  const root=await api.getNodeByIdAsync(execution.rootReference);
  if(!root||root.parent.id!==execution.pageReference)throw new Error('slot_root_mismatch');
  const before=await snapshotFigmaContentRoot(root);
  if(captureSha256(JSON.stringify(before))!==beforeSha256)throw new Error('slot_checkpoint_mismatch');
  const owned=new Set(execution.createdNodeIds),roles=new Set(),ids=new Set(),pending=[],sources=new Map();
  for(const item of request.items){
    const parent=await api.getNodeByIdAsync(execution.nodeMap[item.roleId]);let ancestor=parent;
    while(ancestor&&ancestor.id!==root.id)ancestor=ancestor.parent;
    if(!parent||!ancestor||parent.type!=='FRAME'||!owned.has(parent.id)||parent.children.length||roles.has(parent.id)||
       parent.width!==item.width||parent.height!==item.height||!item.children.length)throw new Error('slot_envelope_mismatch');
    roles.add(parent.id);
    for(const spec of item.children){
      if(ids.has(spec.id)||execution.nodeMap[spec.id])throw new Error('slot_duplicate_id');ids.add(spec.id);
      if(spec.layout.width.mode!=='fixed'||spec.layout.height.mode!=='fixed'||spec.layout.height.value>parent.height)throw new Error('slot_child_geometry');
      if(spec.componentReference){
        const main=await api.getNodeByIdAsync(spec.componentReference);
        if(main?.type!=='COMPONENT'||main.width!==spec.layout.width.value||main.height!==spec.layout.height.value)throw new Error('slot_source_geometry');
        for(const text of main.findAllWithCriteria({types:['TEXT']}))for(const segment of text.getStyledTextSegments(['fontName']))await api.loadFontAsync(segment.fontName);
        sources.set(spec.id,{main,snapshot:await snapshotFigmaContentRoot(main)});
      }else if(spec.type==='Text'){
        const available=await api.listAvailableFontsAsync();
        if(!available.some(f=>f.fontName.family===spec.fontName.family&&f.fontName.style===spec.fontName.style))throw new Error('slot_missing_font');
        await api.loadFontAsync(spec.fontName);
      }else throw new Error('slot_unsupported_child');
    }
    if(item.children.reduce((w,s)=>w+s.layout.width.value,0)>parent.width)throw new Error('slot_width_overflow');
    pending.push({parent,item});
  }
  if(!pending.length||captureSha256(JSON.stringify(await snapshotFigmaContentRoot(root)))!==beforeSha256)throw new Error('slot_changed_during_preflight');
  const created=[],nodeMap={};
  function record(node){created.push(node.id);for(const child of node.children||[])record(child);}
  try{
    for(const {parent,item} of pending)for(const spec of item.children){
      let node;
      if(spec.componentReference){node=sources.get(spec.id).main.createInstance();record(node);}
      else{
        node=api.createText();record(node);await api.loadFontAsync(node.fontName);node.fontName=spec.fontName;
        const t=spec.style.typographyToken;node.fontSize=t.fontSize;node.lineHeight={unit:'PIXELS',value:t.lineHeight};node.letterSpacing={unit:'PIXELS',value:t.letterSpacing};
        node.characters=spec.text;node.textAutoResize='NONE';
        const color=spec.style.colorToken;node.fills=[{type:'SOLID',color:{r:parseInt(color.slice(1,3),16)/255,g:parseInt(color.slice(3,5),16)/255,b:parseInt(color.slice(5,7),16)/255},opacity:color.length===9?parseInt(color.slice(7),16)/255:1}];
      }
      parent.appendChild(node);node.name=spec.name;node.resize(spec.layout.width.value,spec.layout.height.value);
      node.layoutSizingHorizontal='FIXED';node.layoutSizingVertical='FIXED';nodeMap[spec.id]=node.id;
    }
    const after=await snapshotFigmaContentRoot(root),old=new Map(before.map(n=>[n.id,n]));
    if(before.some(n=>!after.some(a=>a.id===n.id))||after.some(n=>!old.has(n.id)&&!created.includes(n.id)))throw new Error('slot_incomplete_ledger');
    for(const n of after)if(old.has(n.id)){
      const a={...old.get(n.id)},b={...n};if(roles.has(n.id)){delete a.children;delete b.children;}
      if(JSON.stringify(a)!==JSON.stringify(b))throw new Error('slot_existing_node_changed');
    }
    for(const {parent,item} of pending)for(const spec of item.children){
      const node=await api.getNodeByIdAsync(nodeMap[spec.id]),box=node.absoluteBoundingBox,p=parent.absoluteBoundingBox;
      if(node.parent.id!==parent.id||node.width!==spec.layout.width.value||node.height!==spec.layout.height.value||
         box.x<p.x||box.y<p.y||box.x+box.width>p.x+p.width||box.y+box.height>p.y+p.height)throw new Error('slot_native_child_overflow');
    }
    for(const source of sources.values())if(JSON.stringify(source.snapshot)!==JSON.stringify(await snapshotFigmaContentRoot(source.main)))throw new Error('slot_master_changed');
    return {status:'FILLED',fileReference:execution.fileReference,pageReference:execution.pageReference,rootReference:root.id,
      createdNodeIds:created,mutatedNodeIds:[...roles],removedNodeIds:[],nodeMap,beforeSha256,afterSha256:captureSha256(JSON.stringify(after)),fullTask015Acceptance:false};
  }catch(error){return {status:'FAIL',nativeExecution:'PARTIAL',recoveryRequired:created.length>0,createdNodeIds:created,nodeMap,issues:[String(error)]};}
}
