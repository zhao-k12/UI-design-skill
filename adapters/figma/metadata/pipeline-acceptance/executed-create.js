// Executed in the Figma Plugin API host. No imports, network or design decisions.
async function executeFigmaAdapter(api, payload) {
  if (api.editorType !== 'figma') throw new Error('unsupported_editor: Design mode required');
  if (api.fileKey && payload.fileReference && api.fileKey !== payload.fileReference) throw new Error('file_reference_mismatch');
  const available = await api.listAvailableFontsAsync();
  const masters = new Map();
  const wantedFonts = new Map();
  function visit(spec, fn) { fn(spec); for (const child of spec.children || []) visit(child, fn); }
  function rememberFont(font) { wantedFonts.set(`${font.family}\0${font.style}\0${JSON.stringify(font.variationSettings || {})}`, font); }
  const specs = [];
  visit(payload.page, spec => specs.push(spec));
  // Full host preflight: no canvas writes before fonts and all native references exist.
  for (const spec of specs) {
    if (spec.type === 'Text') {
      if (!spec.fontName || !available.some(f => f.fontName.family === spec.fontName.family && f.fontName.style === spec.fontName.style)) {
        throw new Error(`missing_font: ${spec.id}`);
      }
      if (spec.fontName.variationSettings) {
        const axes = api.getFontFamilyVariationAxes(spec.fontName.family) || [];
        if (Object.keys(spec.fontName.variationSettings).some(axis => !axes.includes(axis))) throw new Error(`unsupported_font_axis: ${spec.id}`);
      }
      rememberFont(spec.fontName);
    }
    if (spec.componentReference) {
      const master = await api.getNodeByIdAsync(spec.componentReference);
      if (!master || master.type !== 'COMPONENT' || master.removed) throw new Error(`missing_native_component: ${spec.id}`);
      masters.set(spec.componentReference, master);
      for (const text of master.findAllWithCriteria({types: ['TEXT']})) {
        for (const segment of text.getStyledTextSegments(['fontName'])) rememberFont(segment.fontName);
      }
    }
  }
  for (const font of wantedFonts.values()) await api.loadFontAsync(font);
  let page = payload.pageReference ? await api.getNodeByIdAsync(payload.pageReference) : null;
  if (payload.pageReference && (!page || page.type !== 'PAGE')) throw new Error('missing_target_page');
  const pageName = `${payload.documentId}/${payload.page.name}`;
  if (!page) {
    const matches = api.root.children.filter(n => n.name === pageName);
    if (matches.length) throw new Error('existing_page_requires_ledger: provide exact pageReference; do not duplicate');
  } else if (page.children.some(n => n.name === `UI-IR/${payload.documentId}/${payload.page.id}`)) {
    throw new Error('existing_output_requires_review: no duplicate or destructive overwrite');
  }
  const created = [];
  const nodeMap = {};
  const helpers = [];
  // Before text layout, fontWeight can lag behind explicit variable-axis settings.
  const effectiveFontWeight = node => node.fontName.variationSettings?.wght ?? node.fontWeight;
  const record = node => { if (!created.includes(node.id)) created.push(node.id); return node; };
  if (!page) { page = record(api.createPage()); page.name = pageName; }
  await api.setCurrentPageAsync(page);
  function paint(hex) {
    if (!/^#[a-f\d]{6}([a-f\d]{2})?$/i.test(hex)) throw new Error('invalid_resolved_color');
    return {type: 'SOLID', color: {r: parseInt(hex.slice(1,3),16)/255, g: parseInt(hex.slice(3,5),16)/255,
      b: parseInt(hex.slice(5,7),16)/255}, opacity: hex.length === 9 ? parseInt(hex.slice(7,9),16)/255 : 1};
  }
  function applyStyle(node, style, text = false) {
    if (text) { if (style.colorToken || style.fill) node.fills = [paint(style.colorToken || style.fill)]; }
    else if (style.fill) node.fills = [paint(style.fill)];
    if (style.opacity !== undefined) node.opacity = style.opacity;
    if (style.radius !== undefined) node.cornerRadius = style.radius;
    if (style.stroke) { node.strokes = [paint(style.stroke.color)]; node.strokeWeight = style.stroke.width; node.strokeAlign = 'INSIDE'; }
    if (style.shadowToken) node.effects = style.shadowToken.map(shadow => {
      const p = paint(shadow.color);
      return {type: 'DROP_SHADOW', visible: true, blendMode: 'NORMAL', color: {...p.color, a: p.opacity},
        offset: {x: shadow.offsetX, y: shadow.offsetY}, radius: shadow.blur, spread: shadow.spread};
    });
  }
  function resizeAndModes(node, layout, isText = false, parentSpec = null) {
    const width = layout.width, height = layout.height;
    if (isText) node.textAutoResize = width.mode === 'hug' ? 'WIDTH_AND_HEIGHT' : 'HEIGHT';
    if (width.mode === 'fixed' || height.mode === 'fixed') {
      node.resize(width.mode === 'fixed' ? width.value : node.width, height.mode === 'fixed' ? height.value : node.height);
    }
    // resize must precede layoutSizing modes; appendChild has already established context.
    let horizontal = width.mode.toUpperCase(), vertical = height.mode.toUpperCase();
    if (parentSpec?.layout.alignment.cross === 'stretch') {
      if (parentSpec.layout.direction === 'vertical' && horizontal === 'HUG') horizontal = 'FILL';
      if (parentSpec.layout.direction === 'horizontal' && vertical === 'HUG') vertical = 'FILL';
    }
    node.layoutSizingHorizontal = horizontal;
    node.layoutSizingVertical = vertical;
  }
  function configureContainer(node, layout) {
    node.fills = [];
    node.clipsContent = false;
    node.itemSpacing = layout.gap;
    node.paddingTop = layout.padding.top; node.paddingRight = layout.padding.right;
    node.paddingBottom = layout.padding.bottom; node.paddingLeft = layout.padding.left;
    node.primaryAxisAlignItems = {start:'MIN', center:'CENTER', end:'MAX', 'space-between':'SPACE_BETWEEN'}[layout.alignment.main];
    node.counterAxisAlignItems = {start:'MIN', center:'CENTER', end:'MAX', stretch:'MIN'}[layout.alignment.cross];
    if (layout.wrap) { node.layoutWrap = 'WRAP'; node.counterAxisSpacing = layout.gap; }
  }
  async function build(spec, parent, parentSpec = null) {
    let node;
    if (spec.type === 'Text') {
      node = record(api.createText());
      // The host may assign a default font. Load it before switching or parenting text.
      await api.loadFontAsync(node.fontName);
      node.fontName = spec.fontName;
      const typography = spec.style.typographyToken;
      if (effectiveFontWeight(node) !== typography.fontWeight) throw new Error(`font_weight_mismatch: ${spec.id}`);
      node.fontSize = typography.fontSize;
      node.lineHeight = {unit: 'PIXELS', value: typography.lineHeight};
      node.letterSpacing = {unit: 'PIXELS', value: typography.letterSpacing};
      node.characters = spec.text;
    } else if (spec.componentReference) {
      node = record(masters.get(spec.componentReference).createInstance());
      for (const child of node.findAll(() => true)) record(child);
    } else {
      node = record(api.createAutoLayout(spec.type === 'Grid' ? 'VERTICAL' : spec.layout.direction.toUpperCase()));
      configureContainer(node, spec.layout);
    }
    parent.appendChild(node);
    node.name = spec.type === 'Page' ? `UI-IR/${payload.documentId}/${spec.id}` : spec.name;
    nodeMap[spec.id] = node.id;
    resizeAndModes(node, spec.layout, spec.type === 'Text', parentSpec);
    applyStyle(node, spec.style, spec.type === 'Text');
    if (spec.type === 'Grid') {
      const rows = new Map();
      for (const cell of spec.gridCells) {
        let row = rows.get(cell.row);
        if (!row) {
          row = record(api.createAutoLayout('HORIZONTAL'));
          row.name = `${spec.id}/grid-row/${cell.row}`; row.fills = []; row.itemSpacing = spec.layout.gap;
          node.appendChild(row); row.layoutSizingHorizontal = 'FILL'; row.layoutSizingVertical = 'HUG';
          rows.set(cell.row, row); helpers.push(row.id);
        }
        const wrapper = record(api.createAutoLayout('VERTICAL'));
        wrapper.name = `${spec.id}/grid-cell/${cell.id}`; wrapper.fills = [];
        row.appendChild(wrapper); wrapper.resize(cell.width, wrapper.height);
        wrapper.layoutSizingHorizontal = 'FIXED'; wrapper.layoutSizingVertical = 'HUG'; helpers.push(wrapper.id);
        const child = spec.children.find(n => n.id === cell.id);
        await build(child, wrapper, {layout: {direction: 'vertical', alignment: {cross:'start'}}});
      }
    } else {
      for (const child of spec.children || []) await build(child, node, spec);
    }
    return node;
  }
  let root;
  try {
    const right = Math.max(80, ...page.children.map(n => n.x + n.width + 80));
    root = await build(payload.page, page);
    root.x = right; root.y = 80;
  } catch (error) {
    // Do not silently remove partial work; return an exact ledger for targeted recovery.
    return {status:'FAIL', adapterVersion:payload.adapterVersion, issues:[{code:'native_write_failed',detail:String(error)}],
      createdNodeIds:created, mutatedNodeIds:[], pageReference:page.id, nodeMap, helperNodeIds:helpers};
  }
  const evidence = [];
  visit(payload.page, spec => {
    const node = page.findOne(n => n.id === nodeMap[spec.id]);
    if (!node) throw new Error('missing_output_node');
    const entry = {uiIrId:spec.id, nodeId:node.id, type:node.type, name:node.name, width:node.width, height:node.height,
      layoutSizingHorizontal:node.layoutSizingHorizontal, layoutSizingVertical:node.layoutSizingVertical};
    if (node.type === 'FRAME') Object.assign(entry, {layoutMode:node.layoutMode, itemSpacing:node.itemSpacing,
      paddingTop:node.paddingTop,paddingRight:node.paddingRight,paddingBottom:node.paddingBottom,paddingLeft:node.paddingLeft});
    if (node.type === 'INSTANCE') entry.mainComponentReference = node.mainComponent?.id;
    if (node.type === 'TEXT') {entry.characters = node.characters; entry.fontName = node.fontName;
      entry.fontWeight = effectiveFontWeight(node);entry.namedStyleFontWeight = node.fontWeight;}
    evidence.push(entry);
  });
  return {status:'PASS', scope:'figma_native_translation', adapterVersion:payload.adapterVersion,
    uiIrSha256:payload.uiIrSha256, tokensSha256:payload.tokensSha256, componentsSha256:payload.componentsSha256, iconsSha256:payload.iconsSha256,
    pageReference:page.id, rootReference:root.id, createdNodeIds:created, mutatedNodeIds:[], nodeMap, helperNodeIds:helpers, evidence};
}


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


const result=await executeFigmaContentAdapter(figma,{"adapterVersion":"0.1.1-content","documentId":"frozen-user-management-list","uiIrSha256":"b36ce0869f3d44ee6ffb8d2d3819f0f023f22840c86a621361400de74606c05e","tokensSha256":"c45fc025aa3293a675933e377ccdfc90c60204f990ff90402fcb5ebc00178c2f","componentsSha256":"028aa6a9f330e3199fef0fa331111229648ca8299f78d376df70e93a5b0ec369","iconsSha256":"642072b677f35e538592cca05b02b2f37ca5770d08f602fd8953754cd217ebde","fileReference":"0vGWSRoLxBiVPXiZ8xJAX9","page":{"id":"pattern.page","name":"pattern.page","type":"Page","layout":{"width":{"mode":"fixed","value":1440},"height":{"mode":"fixed","value":488},"padding":{"top":24,"right":24,"bottom":24,"left":24},"gap":24,"direction":"vertical","wrap":false,"alignment":{"main":"start","cross":"start"}},"style":{},"children":[{"id":"pattern.header","name":"pattern.header","type":"Section","layout":{"width":{"mode":"fixed","value":1392},"height":{"mode":"fixed","value":28},"padding":{"top":0,"right":0,"bottom":0,"left":0},"gap":16,"direction":"vertical","wrap":false,"alignment":{"main":"start","cross":"start"}},"style":{},"children":[{"id":"layout.item.0.0","name":"layout.item.0.0","type":"Frame","layout":{"width":{"mode":"fixed","value":1392},"height":{"mode":"fixed","value":28},"padding":{"top":0,"right":0,"bottom":0,"left":0},"gap":8,"direction":"horizontal","wrap":false,"alignment":{"main":"space-between","cross":"start"}},"style":{},"children":[{"id":"layout.item.0.0.slot.content","name":"layout.item.0.0.slot.content","type":"Frame","layout":{"width":{"mode":"fixed","value":80},"height":{"mode":"fixed","value":28},"padding":{"top":0,"right":0,"bottom":0,"left":0},"gap":8,"direction":"horizontal","wrap":false,"alignment":{"main":"start","cross":"center"}},"style":{},"children":[{"id":"layout.item.0.0.instance","name":"layout.item.0.0.instance","type":"Text","layout":{"width":{"mode":"fixed","value":80},"height":{"mode":"fixed","value":28},"padding":{"top":0,"right":0,"bottom":0,"left":0},"gap":0,"direction":"vertical","wrap":false,"alignment":{"main":"start","cross":"start"}},"style":{"typographyToken":{"fontFamily":"Noto Sans SC","fontSize":20,"fontWeight":600,"lineHeight":28,"letterSpacing":0},"colorToken":"#20252b"},"text":"用户管理","fontName":{"family":"Noto Sans SC","style":"Regular","variationSettings":{"wght":600}}}]},{"id":"layout.item.0.0.slot.trailing-icon","name":"layout.item.0.0.slot.trailing-icon","type":"Frame","layout":{"width":{"mode":"fixed","value":24},"height":{"mode":"fixed","value":28},"padding":{"top":0,"right":0,"bottom":0,"left":0},"gap":8,"direction":"horizontal","wrap":false,"alignment":{"main":"start","cross":"center"}},"style":{},"children":[{"id":"header-title.icon","name":"header-title.icon","type":"IconInstance","layout":{"width":{"mode":"fixed","value":24},"height":{"mode":"fixed","value":24},"padding":{"top":0,"right":0,"bottom":0,"left":0},"gap":0,"direction":"vertical","wrap":false,"alignment":{"main":"start","cross":"start"}},"style":{},"componentReference":"3:16","svgSha256":"f2e1fd30e6eadb8d5636f5037cf477f38ef81b235757d3ed290b92b2c002fec1"}]}]}]},{"id":"pattern.query","name":"pattern.query","type":"Section","layout":{"width":{"mode":"fixed","value":1392},"height":{"mode":"fixed","value":94},"padding":{"top":16,"right":16,"bottom":16,"left":16},"gap":16,"direction":"vertical","wrap":false,"alignment":{"main":"start","cross":"start"}},"style":{},"children":[{"id":"pattern.query.grid","name":"pattern.query.grid","type":"Grid","layout":{"width":{"mode":"fixed","value":1360},"height":{"mode":"fixed","value":62},"padding":{"top":0,"right":0,"bottom":0,"left":0},"gap":16,"direction":"horizontal","wrap":false,"alignment":{"main":"start","cross":"start"}},"style":{},"gridWidth":1360,"gridCells":[{"id":"layout.item.1.0","row":0,"width":328},{"id":"layout.item.1.1","row":0,"width":328},{"id":"layout.item.1.3","row":0,"width":328},{"id":"layout.item.1.2","row":0,"width":328}],"children":[{"id":"layout.item.1.0","name":"layout.item.1.0","type":"Frame","layout":{"width":{"mode":"fixed","value":328},"height":{"mode":"fixed","value":62},"padding":{"top":0,"right":0,"bottom":0,"left":0},"gap":8,"direction":"vertical","wrap":false,"alignment":{"main":"start","cross":"start"}},"style":{},"children":[{"id":"layout.item.1.0.slot.label","name":"layout.item.1.0.slot.label","type":"Frame","layout":{"width":{"mode":"fixed","value":28},"height":{"mode":"fixed","value":22},"padding":{"top":0,"right":0,"bottom":0,"left":0},"gap":8,"direction":"horizontal","wrap":false,"alignment":{"main":"start","cross":"center"}},"style":{},"children":[{"id":"field-name.label","name":"field-name.label","type":"Text","layout":{"width":{"mode":"fixed","value":28},"height":{"mode":"fixed","value":22},"padding":{"top":0,"right":0,"bottom":0,"left":0},"gap":0,"direction":"vertical","wrap":false,"alignment":{"main":"start","cross":"start"}},"style":{"typographyToken":{"fontFamily":"Noto Sans SC","fontSize":14,"fontWeight":400,"lineHeight":22,"letterSpacing":0},"colorToken":"#20252b"},"text":"姓名","fontName":{"family":"Noto Sans SC","style":"Regular"}}]},{"id":"layout.item.1.0.slot.control","name":"layout.item.1.0.slot.control","type":"Frame","layout":{"width":{"mode":"fixed","value":240},"height":{"mode":"fixed","value":32},"padding":{"top":0,"right":0,"bottom":0,"left":0},"gap":8,"direction":"horizontal","wrap":false,"alignment":{"main":"start","cross":"center"}},"style":{},"children":[{"id":"layout.item.1.0.instance","name":"layout.item.1.0.instance","type":"ComponentInstance","layout":{"width":{"mode":"fixed","value":240},"height":{"mode":"fixed","value":32},"padding":{"top":0,"right":0,"bottom":0,"left":0},"gap":0,"direction":"vertical","wrap":false,"alignment":{"main":"start","cross":"start"}},"style":{},"componentReference":"12:8","fidelityReportSha256":"095db86f0fd809bcd410dc49eb9a3ec9d05cae7162bc27e38fc47cde7decdab3","nativeContent":[{"name":"source/placeholder","originalText":"请输入姓名","text":"请输入姓名","style":{"fontName":{"family":"PingFang SC","style":"Regular"},"fontSize":14,"lineHeight":{"unit":"AUTO"},"letterSpacing":{"unit":"PIXELS","value":0},"textAutoResize":"WIDTH_AND_HEIGHT","textAlignHorizontal":"LEFT","textAlignVertical":"TOP"}}]}]}]},{"id":"layout.item.1.1","name":"layout.item.1.1","type":"Frame","layout":{"width":{"mode":"fixed","value":328},"height":{"mode":"fixed","value":62},"padding":{"top":0,"right":0,"bottom":0,"left":0},"gap":8,"direction":"vertical","wrap":false,"alignment":{"main":"start","cross":"start"}},"style":{},"children":[{"id":"layout.item.1.1.slot.label","name":"layout.item.1.1.slot.label","type":"Frame","layout":{"width":{"mode":"fixed","value":28},"height":{"mode":"fixed","value":22},"padding":{"top":0,"right":0,"bottom":0,"left":0},"gap":8,"direction":"horizontal","wrap":false,"alignment":{"main":"start","cross":"center"}},"style":{},"children":[{"id":"field-status.label","name":"field-status.label","type":"Text","layout":{"width":{"mode":"fixed","value":28},"height":{"mode":"fixed","value":22},"padding":{"top":0,"right":0,"bottom":0,"left":0},"gap":0,"direction":"vertical","wrap":false,"alignment":{"main":"start","cross":"start"}},"style":{"typographyToken":{"fontFamily":"Noto Sans SC","fontSize":14,"fontWeight":400,"lineHeight":22,"letterSpacing":0},"colorToken":"#20252b"},"text":"状态","fontName":{"family":"Noto Sans SC","style":"Regular"}}]},{"id":"layout.item.1.1.slot.control","name":"layout.item.1.1.slot.control","type":"Frame","layout":{"width":{"mode":"fixed","value":240},"height":{"mode":"fixed","value":32},"padding":{"top":0,"right":0,"bottom":0,"left":0},"gap":8,"direction":"horizontal","wrap":false,"alignment":{"main":"start","cross":"center"}},"style":{},"children":[{"id":"layout.item.1.1.instance","name":"layout.item.1.1.instance","type":"ComponentInstance","layout":{"width":{"mode":"fixed","value":240},"height":{"mode":"fixed","value":32},"padding":{"top":0,"right":0,"bottom":0,"left":0},"gap":0,"direction":"vertical","wrap":false,"alignment":{"main":"start","cross":"start"}},"style":{},"componentReference":"12:15","fidelityReportSha256":"24ec8a72a08bb332b4f73734b17ab1772f34f378bc5130da4f7071435c0c4e21","nativeContent":[{"name":"source/selected-value-text","originalText":"启用","text":"启用","style":{"fontName":{"family":"PingFang SC","style":"Regular"},"fontSize":14,"lineHeight":{"unit":"PIXELS","value":30},"letterSpacing":{"unit":"PIXELS","value":0},"textAutoResize":"WIDTH_AND_HEIGHT","textAlignHorizontal":"LEFT","textAlignVertical":"TOP"}}]}]}]},{"id":"layout.item.1.3","name":"layout.item.1.3","type":"Frame","layout":{"width":{"mode":"fixed","value":328},"height":{"mode":"fixed","value":52},"padding":{"top":0,"right":0,"bottom":0,"left":0},"gap":8,"direction":"vertical","wrap":false,"alignment":{"main":"start","cross":"start"}},"style":{},"children":[{"id":"layout.item.1.3.slot.label","name":"layout.item.1.3.slot.label","type":"Frame","layout":{"width":{"mode":"fixed","value":28},"height":{"mode":"fixed","value":22},"padding":{"top":0,"right":0,"bottom":0,"left":0},"gap":8,"direction":"horizontal","wrap":false,"alignment":{"main":"start","cross":"center"}},"style":{},"children":[{"id":"scope-content.label","name":"scope-content.label","type":"Text","layout":{"width":{"mode":"fixed","value":28},"height":{"mode":"fixed","value":22},"padding":{"top":0,"right":0,"bottom":0,"left":0},"gap":0,"direction":"vertical","wrap":false,"alignment":{"main":"start","cross":"start"}},"style":{"typographyToken":{"fontFamily":"Noto Sans SC","fontSize":14,"fontWeight":400,"lineHeight":22,"letterSpacing":0},"colorToken":"#20252b"},"text":"范围","fontName":{"family":"Noto Sans SC","style":"Regular"}}]},{"id":"layout.item.1.3.slot.content","name":"layout.item.1.3.slot.content","type":"Frame","layout":{"width":{"mode":"fixed","value":84},"height":{"mode":"fixed","value":22},"padding":{"top":0,"right":0,"bottom":0,"left":0},"gap":8,"direction":"horizontal","wrap":false,"alignment":{"main":"start","cross":"center"}},"style":{},"children":[{"id":"layout.item.1.3.instance","name":"layout.item.1.3.instance","type":"Text","layout":{"width":{"mode":"fixed","value":84},"height":{"mode":"fixed","value":22},"padding":{"top":0,"right":0,"bottom":0,"left":0},"gap":0,"direction":"vertical","wrap":false,"alignment":{"main":"start","cross":"start"}},"style":{"typographyToken":{"fontFamily":"Noto Sans SC","fontSize":14,"fontWeight":400,"lineHeight":22,"letterSpacing":0},"colorToken":"#20252b"},"text":"查看用户信息","fontName":{"family":"Noto Sans SC","style":"Regular"}}]}]},{"id":"layout.item.1.2","name":"layout.item.1.2","type":"Frame","layout":{"width":{"mode":"fixed","value":328},"height":{"mode":"fixed","value":62},"padding":{"top":0,"right":0,"bottom":0,"left":0},"gap":8,"direction":"vertical","wrap":false,"alignment":{"main":"start","cross":"start"}},"style":{},"children":[{"id":"layout.item.1.2.slot.label","name":"layout.item.1.2.slot.label","type":"Frame","layout":{"width":{"mode":"fixed","value":28},"height":{"mode":"fixed","value":22},"padding":{"top":0,"right":0,"bottom":0,"left":0},"gap":8,"direction":"horizontal","wrap":false,"alignment":{"main":"start","cross":"center"}},"style":{},"children":[{"id":"query-action.label","name":"query-action.label","type":"Text","layout":{"width":{"mode":"fixed","value":28},"height":{"mode":"fixed","value":22},"padding":{"top":0,"right":0,"bottom":0,"left":0},"gap":0,"direction":"vertical","wrap":false,"alignment":{"main":"start","cross":"start"}},"style":{"typographyToken":{"fontFamily":"Noto Sans SC","fontSize":14,"fontWeight":400,"lineHeight":22,"letterSpacing":0},"colorToken":"#20252b"},"text":"操作","fontName":{"family":"Noto Sans SC","style":"Regular"}}]},{"id":"layout.item.1.2.slot.actions","name":"layout.item.1.2.slot.actions","type":"Frame","layout":{"width":{"mode":"fixed","value":60},"height":{"mode":"fixed","value":32},"padding":{"top":0,"right":0,"bottom":0,"left":0},"gap":8,"direction":"horizontal","wrap":false,"alignment":{"main":"start","cross":"center"}},"style":{},"children":[{"id":"layout.item.1.2.instance","name":"layout.item.1.2.instance","type":"ComponentInstance","layout":{"width":{"mode":"fixed","value":60},"height":{"mode":"fixed","value":32},"padding":{"top":0,"right":0,"bottom":0,"left":0},"gap":0,"direction":"vertical","wrap":false,"alignment":{"main":"start","cross":"start"}},"style":{},"componentReference":"18:5","fidelityReportSha256":"f5f768a7041c2302f10efaf2360ebce52f99031898fba81fd6e99827847e6c11","nativeContent":[{"name":"查询","originalText":"查询","text":"查询","style":{"fontName":{"family":"PingFang SC","style":"Regular"},"fontSize":14,"lineHeight":{"unit":"PIXELS","value":21},"letterSpacing":{"unit":"PIXELS","value":0},"textAutoResize":"WIDTH_AND_HEIGHT","textAlignHorizontal":"CENTER","textAlignVertical":"TOP"}}]}]}]}]}]},{"id":"pattern.table","name":"pattern.table","type":"Section","layout":{"width":{"mode":"fixed","value":1392},"height":{"mode":"fixed","value":270},"padding":{"top":0,"right":0,"bottom":0,"left":0},"gap":16,"direction":"vertical","wrap":false,"alignment":{"main":"start","cross":"start"}},"style":{},"children":[{"id":"layout.group.2.content-row.0","name":"layout.group.2.content-row.0","type":"HorizontalStack","layout":{"width":{"mode":"fixed","value":1392},"height":{"mode":"fixed","value":24},"padding":{"top":0,"right":0,"bottom":0,"left":0},"gap":8,"direction":"horizontal","wrap":false,"alignment":{"main":"space-between","cross":"center"}},"style":{},"children":[{"id":"layout.item.2.1","name":"layout.item.2.1","type":"Frame","layout":{"width":{"mode":"fixed","value":56},"height":{"mode":"fixed","value":22},"padding":{"top":0,"right":0,"bottom":0,"left":0},"gap":0,"direction":"vertical","wrap":false,"alignment":{"main":"start","cross":"start"}},"style":{},"children":[{"id":"layout.item.2.1.instance","name":"layout.item.2.1.instance","type":"Text","layout":{"width":{"mode":"fixed","value":56},"height":{"mode":"fixed","value":22},"padding":{"top":0,"right":0,"bottom":0,"left":0},"gap":0,"direction":"vertical","wrap":false,"alignment":{"main":"start","cross":"start"}},"style":{"typographyToken":{"fontFamily":"Noto Sans SC","fontSize":14,"fontWeight":400,"lineHeight":22,"letterSpacing":0},"colorToken":"#20252b"},"text":"用户列表","fontName":{"family":"Noto Sans SC","style":"Regular"}}]},{"id":"layout.item.2.2","name":"layout.item.2.2","type":"Frame","layout":{"width":{"mode":"fixed","value":60},"height":{"mode":"fixed","value":24},"padding":{"top":0,"right":0,"bottom":0,"left":0},"gap":8,"direction":"horizontal","wrap":false,"alignment":{"main":"start","cross":"start"}},"style":{},"children":[{"id":"layout.item.2.2.slot.leading-icon","name":"layout.item.2.2.slot.leading-icon","type":"Frame","layout":{"width":{"mode":"fixed","value":24},"height":{"mode":"fixed","value":24},"padding":{"top":0,"right":0,"bottom":0,"left":0},"gap":8,"direction":"horizontal","wrap":false,"alignment":{"main":"start","cross":"center"}},"style":{},"children":[{"id":"export-action.icon","name":"export-action.icon","type":"IconInstance","layout":{"width":{"mode":"fixed","value":24},"height":{"mode":"fixed","value":24},"padding":{"top":0,"right":0,"bottom":0,"left":0},"gap":0,"direction":"vertical","wrap":false,"alignment":{"main":"start","cross":"start"}},"style":{},"componentReference":"3:13","svgSha256":"ad83ac7dc9d4c6af651a53068e928d82f9402cfd05a924742388549846032f43"}]},{"id":"layout.item.2.2.slot.content","name":"layout.item.2.2.slot.content","type":"Frame","layout":{"width":{"mode":"fixed","value":28},"height":{"mode":"fixed","value":24},"padding":{"top":0,"right":0,"bottom":0,"left":0},"gap":8,"direction":"horizontal","wrap":false,"alignment":{"main":"start","cross":"center"}},"style":{},"children":[{"id":"layout.item.2.2.instance","name":"layout.item.2.2.instance","type":"Text","layout":{"width":{"mode":"fixed","value":28},"height":{"mode":"fixed","value":22},"padding":{"top":0,"right":0,"bottom":0,"left":0},"gap":0,"direction":"vertical","wrap":false,"alignment":{"main":"start","cross":"start"}},"style":{"typographyToken":{"fontFamily":"Noto Sans SC","fontSize":14,"fontWeight":400,"lineHeight":22,"letterSpacing":0},"colorToken":"#20252b"},"text":"导出","fontName":{"family":"Noto Sans SC","style":"Regular"}}]}]}]},{"id":"layout.item.2.0","name":"layout.item.2.0","type":"Frame","layout":{"width":{"mode":"fixed","value":1392},"height":{"mode":"fixed","value":192},"padding":{"top":0,"right":0,"bottom":0,"left":0},"gap":0,"direction":"vertical","wrap":false,"alignment":{"main":"start","cross":"start"}},"style":{},"children":[{"id":"layout.item.2.0.header","name":"layout.item.2.0.header","type":"Row","layout":{"width":{"mode":"fixed","value":1392},"height":{"mode":"fixed","value":48},"padding":{"top":0,"right":0,"bottom":0,"left":0},"gap":0,"direction":"horizontal","wrap":false,"alignment":{"main":"start","cross":"start"}},"style":{},"children":[{"id":"layout.item.2.0.header.column.0","name":"layout.item.2.0.header.column.0","type":"Frame","layout":{"width":{"mode":"fixed","value":464.328125},"height":{"mode":"fixed","value":48},"padding":{"top":0,"right":0,"bottom":0,"left":16},"gap":0,"direction":"horizontal","wrap":false,"alignment":{"main":"start","cross":"center"}},"style":{},"children":[{"id":"layout.item.2.0.header.column.0.text","name":"layout.item.2.0.header.column.0.text","type":"Text","layout":{"width":{"mode":"hug"},"height":{"mode":"hug"},"padding":{"top":0,"right":0,"bottom":0,"left":0},"gap":0,"direction":"vertical","wrap":false,"alignment":{"main":"start","cross":"start"}},"style":{"typographyToken":{"fontFamily":"Noto Sans SC","fontSize":14,"fontWeight":400,"lineHeight":22,"letterSpacing":0},"colorToken":"#20252b"},"text":"姓名","fontName":{"family":"Noto Sans SC","style":"Regular"}}]},{"id":"layout.item.2.0.header.column.1","name":"layout.item.2.0.header.column.1","type":"Frame","layout":{"width":{"mode":"fixed","value":464.328125},"height":{"mode":"fixed","value":48},"padding":{"top":0,"right":0,"bottom":0,"left":16},"gap":0,"direction":"horizontal","wrap":false,"alignment":{"main":"start","cross":"center"}},"style":{},"children":[{"id":"layout.item.2.0.header.column.1.text","name":"layout.item.2.0.header.column.1.text","type":"Text","layout":{"width":{"mode":"hug"},"height":{"mode":"hug"},"padding":{"top":0,"right":0,"bottom":0,"left":0},"gap":0,"direction":"vertical","wrap":false,"alignment":{"main":"start","cross":"start"}},"style":{"typographyToken":{"fontFamily":"Noto Sans SC","fontSize":14,"fontWeight":400,"lineHeight":22,"letterSpacing":0},"colorToken":"#20252b"},"text":"状态","fontName":{"family":"Noto Sans SC","style":"Regular"}}]},{"id":"layout.item.2.0.header.column.2","name":"layout.item.2.0.header.column.2","type":"Frame","layout":{"width":{"mode":"fixed","value":463.34375},"height":{"mode":"fixed","value":48},"padding":{"top":0,"right":0,"bottom":0,"left":16},"gap":0,"direction":"horizontal","wrap":false,"alignment":{"main":"start","cross":"center"}},"style":{},"children":[{"id":"layout.item.2.0.header.column.2.text","name":"layout.item.2.0.header.column.2.text","type":"Text","layout":{"width":{"mode":"hug"},"height":{"mode":"hug"},"padding":{"top":0,"right":0,"bottom":0,"left":0},"gap":0,"direction":"vertical","wrap":false,"alignment":{"main":"start","cross":"start"}},"style":{"typographyToken":{"fontFamily":"Noto Sans SC","fontSize":14,"fontWeight":400,"lineHeight":22,"letterSpacing":0},"colorToken":"#20252b"},"text":"角色","fontName":{"family":"Noto Sans SC","style":"Regular"}}]}]},{"id":"layout.item.2.0.instance","name":"layout.item.2.0.instance","type":"ComponentInstance","layout":{"width":{"mode":"fixed","value":1392},"height":{"mode":"fixed","value":144},"padding":{"top":0,"right":0,"bottom":0,"left":0},"gap":0,"direction":"vertical","wrap":false,"alignment":{"main":"start","cross":"start"}},"style":{},"componentReference":"28:3","fidelityReportSha256":"0984deb3fbaa90614cc8069d47bdfc326850a4ba356902a57a98c53eeee2e49d"}]},{"id":"layout.item.2.3","name":"layout.item.2.3","type":"Frame","layout":{"width":{"mode":"fixed","value":1392},"height":{"mode":"fixed","value":22},"padding":{"top":0,"right":0,"bottom":0,"left":0},"gap":0,"direction":"vertical","wrap":false,"alignment":{"main":"start","cross":"start"}},"style":{},"children":[{"id":"layout.item.2.3.instance","name":"layout.item.2.3.instance","type":"Text","layout":{"width":{"mode":"fixed","value":71},"height":{"mode":"fixed","value":22},"padding":{"top":0,"right":0,"bottom":0,"left":0},"gap":0,"direction":"vertical","wrap":false,"alignment":{"main":"start","cross":"start"}},"style":{"typographyToken":{"fontFamily":"Noto Sans SC","fontSize":14,"fontWeight":400,"lineHeight":22,"letterSpacing":0},"colorToken":"#20252b"},"text":"共 3 位用户","fontName":{"family":"Noto Sans SC","style":"Regular"}}]}]}]},"pageReference":null});if(result.rootReference){const root=await figma.getNodeByIdAsync(result.rootReference);const nodes=await snapshotFigmaContentRoot(root);result.createdNodeIds=[...new Set([...result.createdNodeIds,...nodes.map(n=>n.id)])];result.nativeNodeCount=nodes.length;}return {status:result.status,nativeExecution:result.nativeExecution,fileReference:result.fileReference,pageReference:result.pageReference,rootReference:result.rootReference,uiIrSha256:result.uiIrSha256,createdNodeIds:result.createdNodeIds,mutatedNodeIds:result.mutatedNodeIds,nodeMap:result.nodeMap,issues:result.issues,recoveryRequired:result.recoveryRequired,nativeNodeCount:result.nativeNodeCount,finalAcceptance:'NOT_RUN'};
