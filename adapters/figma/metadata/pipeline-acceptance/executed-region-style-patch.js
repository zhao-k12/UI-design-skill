// Declared native text edits on existing genuine instances or UI-IR Text primitives.
async function snapshotFigmaContentRoot(root){
  const nodes=[];
  async function walk(n){
    const box=n.absoluteBoundingBox;
    const item={id:n.id,parent:n.parent?.id,type:n.type,name:n.name,
      x:box?.x,y:box?.y,width:n.width,height:n.height,children:('children' in n?n.children:[]).map(c=>c.id)};
    for(const key of ['visible','opacity','fills','strokes','strokeWeight','strokeAlign','cornerRadius','effects','rotation','blendMode','isMask','clipsContent','layoutMode','layoutSizingHorizontal','layoutSizingVertical','primaryAxisAlignItems','counterAxisAlignItems','itemSpacing','paddingTop','paddingRight','paddingBottom','paddingLeft','layoutPositioning'])
      if(key in n)item[key]=n[key]===figma.mixed?{nativeMixed:true}:JSON.parse(JSON.stringify(n[key]));
    if(n.type==='INSTANCE')item.component=(await n.getMainComponentAsync())?.id;
    if(n.type==='TEXT')for(const key of ['characters','fontName','fontSize','lineHeight','letterSpacing','textAutoResize','textAlignHorizontal','textAlignVertical','textStyleId'])
      item[key]=n[key]===figma.mixed?{nativeMixed:true}:JSON.parse(JSON.stringify(n[key]));
    nodes.push(item);if('children' in n)for(const child of n.children)await walk(child);
  }await walk(root);return nodes;
}

async function captureFigmaSectionContent(api,execution){
  if(api.fileKey!==execution.fileReference||api.currentPage.id!==execution.pageReference)throw new Error('content_capture_context_mismatch');
  const root=await api.getNodeByIdAsync(execution.rootReference);
  if(!root||root.parent.id!==execution.pageReference)throw new Error('content_capture_missing_root');
  const before=await snapshotFigmaContentRoot(root);
  const fonts=new Map();for(const t of root.findAllWithCriteria({types:['TEXT']}))for(const s of t.getStyledTextSegments(['fontName']))fonts.set(JSON.stringify(s.fontName),s.fontName);
  await Promise.all([...fonts.values()].map(f=>api.loadFontAsync(f)));
  const bytes=await root.exportAsync({format:'PNG',constraint:{type:'SCALE',value:1},useAbsoluteBounds:true});
  const nodes=await snapshotFigmaContentRoot(root);
  if(JSON.stringify(before)!==JSON.stringify(nodes))throw new Error('content_capture_state_changed');
  return {status:'CAPTURED',scope:'figma-native-section-content-capture',fileReference:api.fileKey,
    pageReference:api.currentPage.id,rootReference:root.id,nodes,nativePngBase64:api.base64Encode(bytes)};
}

async function patchFigmaSectionContent(api,execution,request,beforeCapture){
  if(api.fileKey!==execution.fileReference||api.currentPage.id!==execution.pageReference||execution.status!=='EXECUTED')throw new Error('content_patch_context_mismatch');
  const root=await api.getNodeByIdAsync(execution.rootReference);
  if(!root||root.parent.id!==execution.pageReference||beforeCapture?.rootReference!==root.id||
     beforeCapture.fileReference!==api.fileKey||beforeCapture.pageReference!==api.currentPage.id||beforeCapture.status!=='CAPTURED')throw new Error('content_patch_checkpoint_context');
  const before=await snapshotFigmaContentRoot(root);
  if(beforeCapture.nodes?JSON.stringify(before)!==JSON.stringify(beforeCapture.nodes):
     !/^[0-9a-f]{64}$/.test(beforeCapture.nodesSha256||'')||captureSha256(JSON.stringify(before))!==beforeCapture.nodesSha256)
    throw new Error('content_patch_stale_snapshot');
  if(!Array.isArray(request.targets)||!request.targets.length)throw new Error('content_patch_empty_targets');
  const pending=[],seen=new Set(),allowed=new Set();
  for(const target of request.targets){
    if(seen.has(target.textReference))throw new Error('content_patch_duplicate_target');seen.add(target.textReference);
    const owner=await api.getNodeByIdAsync(target.ownerReference),text=await api.getNodeByIdAsync(target.textReference);
    if(!owner||!execution.createdNodeIds.includes(owner.id)||!text||text.type!=='TEXT'||!target.sectionReference)
      throw new Error('content_patch_unknown_target');
    let p=owner,sectionFound=false;while(p&&p.id!==root.id){if(p.id===target.sectionReference)sectionFound=true;p=p.parent;}
    if(!p||!sectionFound)throw new Error('content_patch_outside_section');
    if(target.componentReference){
      if(owner.type!=='INSTANCE'||(await owner.getMainComponentAsync())?.id!==target.componentReference)throw new Error('content_patch_not_linked_instance');
      let ancestor=text;while(ancestor&&ancestor.id!==owner.id)ancestor=ancestor.parent;
      if(!ancestor)throw new Error('content_patch_text_outside_copy');
    }else if(owner.id!==text.id)throw new Error('content_patch_primitive_owner_mismatch');
    if(text.name!==target.name||text.characters!==target.expectedText||typeof target.text!=='string'||!target.text||/[\r\n]/.test(target.text))throw new Error('content_patch_stale_text');
    if(!target.style||Object.entries(target.style).some(([k,v])=>JSON.stringify(text[k])!==JSON.stringify(v)))throw new Error('content_patch_style_mismatch');
    // Property-managed text must use its declared property binding instead.
    if(text.componentPropertyReferences?.characters)throw new Error('unsupported_property_managed_text');
    pending.push({target,text});allowed.add(text.id);
  }
  const fonts=new Map();for(const {text} of pending)for(const s of text.getStyledTextSegments(['fontName']))fonts.set(JSON.stringify(s.fontName),s.fontName);
  await Promise.all([...fonts.values()].map(f=>api.loadFontAsync(f)));
  if(JSON.stringify(before)!==JSON.stringify(await snapshotFigmaContentRoot(root)))throw new Error('content_patch_changed_during_font_load');
  try{
    for(const {text,target} of pending)text.characters=target.text;
    const after=await snapshotFigmaContentRoot(root);
    if(JSON.stringify(before.map(n=>n.id))!==JSON.stringify(after.map(n=>n.id)))throw new Error('content_patch_changed_topology');
    if(JSON.stringify(before.filter(n=>!allowed.has(n.id)))!==JSON.stringify(after.filter(n=>!allowed.has(n.id))))throw new Error('content_patch_changed_unrelated_nodes');
    for(const {text,target} of pending){
      if(text.characters!==target.text||Object.entries(target.style).some(([k,v])=>JSON.stringify(text[k])!==JSON.stringify(v)))throw new Error('content_patch_failed_readback');
      const parent=await api.getNodeByIdAsync(target.ownerReference),a=parent.absoluteBoundingBox,b=text.absoluteBoundingBox;
      if(!a||!b||b.x<a.x-1e-6||b.y<a.y-1e-6||b.x+b.width>a.x+a.width+1e-6||b.y+b.height>a.y+a.height+1e-6)throw new Error('content_patch_text_overflow');
    }
    return {status:'PATCHED',scope:'figma-native-section-content-patch',finalAcceptance:'NOT_RUN',
      fileReference:api.fileKey,pageReference:api.currentPage.id,rootReference:root.id,
      mutatedNodeIds:[...allowed],createdNodeIds:[],removedNodeIds:[],changedSections:[...new Set(pending.map(p=>p.target.sectionReference))],before,after};
  }catch(error){
    for(const {text,target} of pending)text.characters=target.expectedText;
    const restored=await snapshotFigmaContentRoot(root);
    return {status:'FAIL',nativeExecution:'PARTIAL',recoveryRequired:JSON.stringify(restored)!==JSON.stringify(before),
      mutatedNodeIds:[...allowed],createdNodeIds:[],removedNodeIds:[],before,after:restored,issues:[{code:'content_patch_failed',detail:String(error)}]};
  }
}


await figma.setCurrentPageAsync(await figma.getNodeByIdAsync('49:2'));
const root=await figma.getNodeByIdAsync('49:3');const before=await snapshotFigmaContentRoot(root);
const changes=[{"id":"49:3","color":"#f4f5f7"},{"id":"49:4","color":"#ffffff"},{"id":"49:11","color":"#ffffff"},{"id":"49:47","color":"#ffffff"}];
for(const c of changes){const n=await figma.getNodeByIdAsync(c.id);if(!before.some(v=>v.id===n.id)||n.type!=='FRAME')throw Error('unowned_region');n.fills=[{type:'SOLID',color:{r:parseInt(c.color.slice(1,3),16)/255,g:parseInt(c.color.slice(3,5),16)/255,b:parseInt(c.color.slice(5,7),16)/255}}];}
const after=await snapshotFigmaContentRoot(root);const normalize=n=>{const v={...n};if(changes.some(c=>c.id===n.id))delete v.fills;return v};if(JSON.stringify(before.map(normalize))!==JSON.stringify(after.map(normalize)))throw Error('unrelated_mutation');return {status:'PATCHED',createdNodeIds:[],removedNodeIds:[],mutatedNodeIds:changes.map(c=>c.id),baseUiIrSha256:'b36ce0869f3d44ee6ffb8d2d3819f0f023f22840c86a621361400de74606c05e',updatedUiIrSha256:'94d539a316f9ac50af23726b705af8e5c89fd188dba9e99a8a0aee9195394bee',beforeRegions:before.filter(n=>changes.some(c=>c.id===n.id)),afterRegions:after.filter(n=>changes.some(c=>c.id===n.id)),unchangedNodes:before.length-changes.length};
