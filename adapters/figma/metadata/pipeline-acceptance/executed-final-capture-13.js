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


// Bounded transport of a single deterministic capture, never image processing.
function captureSha256(text,inputBytes){
  const bytes=inputBytes===undefined?Array.from(unescape(encodeURIComponent(text)),c=>c.charCodeAt(0)):Array.from(inputBytes);
  const length=bytes.length;bytes.push(128);while(bytes.length%64!==56)bytes.push(0);
  const bits=length*8;for(let i=7;i>=0;i--)bytes.push(i>=4?0:(bits>>>i*8)&255);
  const constants=[],initial=[];let prime=2;
  while(constants.length<64){let valid=true;for(let d=2;d*d<=prime;d++)if(prime%d===0){valid=false;break;}
    if(valid){if(initial.length<8)initial.push((Math.sqrt(prime)%1*4294967296)|0);constants.push((Math.cbrt(prime)%1*4294967296)|0);}prime++;}
  const rotate=(x,n)=>(x>>>n)|(x<<(32-n));const hash=initial.slice();
  for(let offset=0;offset<bytes.length;offset+=64){const w=[];for(let i=0;i<16;i++)w[i]=(bytes[offset+i*4]<<24)|(bytes[offset+i*4+1]<<16)|(bytes[offset+i*4+2]<<8)|bytes[offset+i*4+3];
    for(let i=16;i<64;i++){const a=w[i-15],b=w[i-2];w[i]=(w[i-16]+(rotate(a,7)^rotate(a,18)^(a>>>3))+w[i-7]+(rotate(b,17)^rotate(b,19)^(b>>>10)))|0;}
    let[a,b,c,d,e,f,g,h]=hash;for(let i=0;i<64;i++){const t1=(h+(rotate(e,6)^rotate(e,11)^rotate(e,25))+((e&f)^(~e&g))+constants[i]+w[i])|0;const t2=((rotate(a,2)^rotate(a,13)^rotate(a,22))+((a&b)^(a&c)^(b&c)))|0;h=g;g=f;f=e;e=(d+t1)|0;d=c;c=b;b=a;a=(t1+t2)|0;}
    [a,b,c,d,e,f,g,h].forEach((value,i)=>hash[i]=(hash[i]+value)|0);
  }
  return hash.map(n=>(n>>>0).toString(16).padStart(8,'0')).join('');
}
function captureTransportPiece(result,index){
  if(result.status!=='PASS')return result;
  const raw=JSON.stringify(result),chunkSize=6500,count=Math.ceil(raw.length/chunkSize);
  if(!Number.isInteger(index)||index<0||index>=count)throw new Error('invalid_capture_transport_piece');
  return{scope:'figma_capture_transport_piece',status:'PASS',index,count,totalCharacters:raw.length,
    captureSha256:captureSha256(raw),chunk:raw.slice(index*chunkSize,(index+1)*chunkSize)};
}


await figma.setCurrentPageAsync(await figma.getNodeByIdAsync('49:2'));
const capture=await captureFigmaSectionContent(figma,{"status":"EXECUTED","nativeExecution":"EXECUTED","fileReference":"0vGWSRoLxBiVPXiZ8xJAX9","pageReference":"49:2","rootReference":"49:3","uiIrSha256":"94d539a316f9ac50af23726b705af8e5c89fd188dba9e99a8a0aee9195394bee","createdNodeIds":["49:2","49:3","49:4","49:5","49:6","49:7","49:8","49:9","I49:9;3:15","49:11","49:12","49:13","49:14","49:15","49:16","49:17","49:18","49:19","I49:19;12:6","I49:19;12:7","49:22","49:23","49:24","49:25","49:26","49:27","I49:27;12:10","I49:27;12:11","I49:27;12:12","I49:27;12:13","I49:27;12:14","49:33","49:34","49:35","49:36","49:37","49:38","49:39","49:40","49:41","49:42","49:43","49:44","I49:44;18:4","I49:44;18:3","49:47","49:48","49:49","49:50","49:51","49:52","49:53","I49:53;3:12","49:55","49:56","49:57","49:58","49:59","49:60","49:61","49:62","49:63","49:64","49:65","I49:65;28:4","I49:65;28:5","I49:65;28:6","I49:65;28:7","I49:65;28:8","I49:65;28:9","I49:65;28:10","I49:65;32:2","I49:65;28:11","I49:65;28:12","I49:65;28:13","I49:65;28:14","I49:65;28:15","I49:65;28:16","I49:65;28:17","I49:65;32:3","I49:65;28:18","I49:65;28:19","I49:65;28:20","I49:65;28:21","I49:65;28:22","I49:65;28:23","I49:65;28:24","I49:65;32:4","I49:65;32:5","49:91","49:92"],"mutatedNodeIds":["I49:19;12:7","I49:27;12:13","I49:44;18:3"],"nodeMap":{"pattern.page":"49:3","pattern.header":"49:4","layout.item.0.0":"49:5","layout.item.0.0.slot.content":"49:6","layout.item.0.0.instance":"49:7","layout.item.0.0.slot.trailing-icon":"49:8","header-title.icon":"49:9","pattern.query":"49:11","pattern.query.grid":"49:12","layout.item.1.0":"49:15","layout.item.1.0.slot.label":"49:16","field-name.label":"49:17","layout.item.1.0.slot.control":"49:18","layout.item.1.0.instance":"49:19","layout.item.1.1":"49:23","layout.item.1.1.slot.label":"49:24","field-status.label":"49:25","layout.item.1.1.slot.control":"49:26","layout.item.1.1.instance":"49:27","layout.item.1.3":"49:34","layout.item.1.3.slot.label":"49:35","scope-content.label":"49:36","layout.item.1.3.slot.content":"49:37","layout.item.1.3.instance":"49:38","layout.item.1.2":"49:40","layout.item.1.2.slot.label":"49:41","query-action.label":"49:42","layout.item.1.2.slot.actions":"49:43","layout.item.1.2.instance":"49:44","pattern.table":"49:47","layout.group.2.content-row.0":"49:48","layout.item.2.1":"49:49","layout.item.2.1.instance":"49:50","layout.item.2.2":"49:51","layout.item.2.2.slot.leading-icon":"49:52","export-action.icon":"49:53","layout.item.2.2.slot.content":"49:55","layout.item.2.2.instance":"49:56","layout.item.2.0":"49:57","layout.item.2.0.header":"49:58","layout.item.2.0.header.column.0":"49:59","layout.item.2.0.header.column.0.text":"49:60","layout.item.2.0.header.column.1":"49:61","layout.item.2.0.header.column.1.text":"49:62","layout.item.2.0.header.column.2":"49:63","layout.item.2.0.header.column.2.text":"49:64","layout.item.2.0.instance":"49:65","layout.item.2.3":"49:91","layout.item.2.3.instance":"49:92"},"nativeNodeCount":90,"finalAcceptance":"NOT_RUN"});
return captureTransportPiece({status:'PASS',capture},13);
