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


await figma.setCurrentPageAsync(await figma.getNodeByIdAsync('35:2'));return await fillFigmaCellSlots(figma,{"status":"EXECUTED","scope":"figma_native_translation","adapterVersion":"0.1.0","uiIrSha256":"a414f564c5d05dab3045ce62bd9e224597b2715885d01ab3b3b1bbec6ccafaaa","tokensSha256":"c45fc025aa3293a675933e377ccdfc90c60204f990ff90402fcb5ebc00178c2f","componentsSha256":"028aa6a9f330e3199fef0fa331111229648ca8299f78d376df70e93a5b0ec369","iconsSha256":"642072b677f35e538592cca05b02b2f37ca5770d08f602fd8953754cd217ebde","pageReference":"35:2","rootReference":"46:74","createdNodeIds":["46:74","46:75","46:76","46:77","46:78","46:79","46:80","46:81"],"mutatedNodeIds":[],"nodeMap":{"slot-page":"46:74","slot-cell":"46:75","slot-cell.slot.leading-icon":"46:76","slot-cell.slot.label":"46:77","slot-cell.slot.control":"46:78","slot-cell.slot.trailing-icon":"46:79","slot-cell.slot.content":"46:80","slot-cell.slot.actions":"46:81"},"helperNodeIds":[],"evidence":[{"uiIrId":"slot-page","nodeId":"46:74","type":"FRAME","name":"UI-IR/task015-six-cell-slots/slot-page","width":1440,"height":80,"layoutSizingHorizontal":"FIXED","layoutSizingVertical":"FIXED","layoutMode":"VERTICAL","itemSpacing":0,"paddingTop":24,"paddingRight":24,"paddingBottom":24,"paddingLeft":24},{"uiIrId":"slot-cell","nodeId":"46:75","type":"FRAME","name":"slot-cell","width":1392,"height":32,"layoutSizingHorizontal":"FIXED","layoutSizingVertical":"FIXED","layoutMode":"HORIZONTAL","itemSpacing":8,"paddingTop":0,"paddingRight":0,"paddingBottom":0,"paddingLeft":0},{"uiIrId":"slot-cell.slot.leading-icon","nodeId":"46:76","type":"FRAME","name":"slot-cell.slot.leading-icon","width":24,"height":32,"layoutSizingHorizontal":"FIXED","layoutSizingVertical":"FIXED","layoutMode":"HORIZONTAL","itemSpacing":8,"paddingTop":0,"paddingRight":0,"paddingBottom":0,"paddingLeft":0},{"uiIrId":"slot-cell.slot.label","nodeId":"46:77","type":"FRAME","name":"slot-cell.slot.label","width":28,"height":32,"layoutSizingHorizontal":"FIXED","layoutSizingVertical":"FIXED","layoutMode":"HORIZONTAL","itemSpacing":8,"paddingTop":0,"paddingRight":0,"paddingBottom":0,"paddingLeft":0},{"uiIrId":"slot-cell.slot.control","nodeId":"46:78","type":"FRAME","name":"slot-cell.slot.control","width":240,"height":32,"layoutSizingHorizontal":"FIXED","layoutSizingVertical":"FIXED","layoutMode":"HORIZONTAL","itemSpacing":8,"paddingTop":0,"paddingRight":0,"paddingBottom":0,"paddingLeft":0},{"uiIrId":"slot-cell.slot.trailing-icon","nodeId":"46:79","type":"FRAME","name":"slot-cell.slot.trailing-icon","width":24,"height":32,"layoutSizingHorizontal":"FIXED","layoutSizingVertical":"FIXED","layoutMode":"HORIZONTAL","itemSpacing":8,"paddingTop":0,"paddingRight":0,"paddingBottom":0,"paddingLeft":0},{"uiIrId":"slot-cell.slot.content","nodeId":"46:80","type":"FRAME","name":"slot-cell.slot.content","width":56,"height":32,"layoutSizingHorizontal":"FIXED","layoutSizingVertical":"FIXED","layoutMode":"HORIZONTAL","itemSpacing":8,"paddingTop":0,"paddingRight":0,"paddingBottom":0,"paddingLeft":0},{"uiIrId":"slot-cell.slot.actions","nodeId":"46:81","type":"FRAME","name":"slot-cell.slot.actions","width":60,"height":32,"layoutSizingHorizontal":"FIXED","layoutSizingVertical":"FIXED","layoutMode":"HORIZONTAL","itemSpacing":8,"paddingTop":0,"paddingRight":0,"paddingBottom":0,"paddingLeft":0}],"fileReference":"0vGWSRoLxBiVPXiZ8xJAX9"},{"items":[{"roleId":"slot-cell.slot.leading-icon","width":24,"height":32,"children":[{"id":"slot-leading","name":"slot-leading","type":"IconInstance","layout":{"width":{"mode":"fixed","value":24},"height":{"mode":"fixed","value":24},"padding":{"top":0,"right":0,"bottom":0,"left":0},"gap":0,"direction":"vertical","wrap":false,"alignment":{"main":"start","cross":"start"}},"style":{},"componentReference":"3:16","svgSha256":"f2e1fd30e6eadb8d5636f5037cf477f38ef81b235757d3ed290b92b2c002fec1"}]},{"roleId":"slot-cell.slot.label","width":28,"height":32,"children":[{"id":"slot-label","name":"slot-label","type":"Text","layout":{"width":{"mode":"fixed","value":28},"height":{"mode":"fixed","value":22},"padding":{"top":0,"right":0,"bottom":0,"left":0},"gap":0,"direction":"vertical","wrap":false,"alignment":{"main":"start","cross":"start"}},"style":{"typographyToken":{"fontFamily":"Noto Sans SC","fontSize":14,"fontWeight":400,"lineHeight":22,"letterSpacing":0},"colorToken":"#20252b"},"text":"姓名","fontName":{"family":"Noto Sans SC","style":"Regular"}}]},{"roleId":"slot-cell.slot.control","width":240,"height":32,"children":[{"id":"slot-control","name":"slot-control","type":"ComponentInstance","layout":{"width":{"mode":"fixed","value":240},"height":{"mode":"fixed","value":32},"padding":{"top":0,"right":0,"bottom":0,"left":0},"gap":0,"direction":"vertical","wrap":false,"alignment":{"main":"start","cross":"start"}},"style":{},"componentReference":"12:8","fidelityReportSha256":"095db86f0fd809bcd410dc49eb9a3ec9d05cae7162bc27e38fc47cde7decdab3"}]},{"roleId":"slot-cell.slot.trailing-icon","width":24,"height":32,"children":[{"id":"slot-trailing","name":"slot-trailing","type":"IconInstance","layout":{"width":{"mode":"fixed","value":24},"height":{"mode":"fixed","value":24},"padding":{"top":0,"right":0,"bottom":0,"left":0},"gap":0,"direction":"vertical","wrap":false,"alignment":{"main":"start","cross":"start"}},"style":{},"componentReference":"3:13","svgSha256":"ad83ac7dc9d4c6af651a53068e928d82f9402cfd05a924742388549846032f43"}]},{"roleId":"slot-cell.slot.content","width":56,"height":32,"children":[{"id":"slot-content","name":"slot-content","type":"Text","layout":{"width":{"mode":"fixed","value":56},"height":{"mode":"fixed","value":22},"padding":{"top":0,"right":0,"bottom":0,"left":0},"gap":0,"direction":"vertical","wrap":false,"alignment":{"main":"start","cross":"start"}},"style":{"typographyToken":{"fontFamily":"Noto Sans SC","fontSize":14,"fontWeight":400,"lineHeight":22,"letterSpacing":0},"colorToken":"#20252b"},"text":"用户列表","fontName":{"family":"Noto Sans SC","style":"Regular"}}]},{"roleId":"slot-cell.slot.actions","width":60,"height":32,"children":[{"id":"slot-action","name":"slot-action","type":"ComponentInstance","layout":{"width":{"mode":"fixed","value":60},"height":{"mode":"fixed","value":32},"padding":{"top":0,"right":0,"bottom":0,"left":0},"gap":0,"direction":"vertical","wrap":false,"alignment":{"main":"start","cross":"start"}},"style":{},"componentReference":"18:5","fidelityReportSha256":"f5f768a7041c2302f10efaf2360ebce52f99031898fba81fd6e99827847e6c11"}]}]},"b025cb0482f3b1c70b7410a1b41f4bb20aa01693d8358075e219588ececa3436");
