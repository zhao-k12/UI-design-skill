// Read-only host discovery. No native writes, network, credentials or user profile.
function discoverPenpotHost(api) {
  if (!api.currentFile || !api.currentPage) throw new Error('open_design_file_required');
  return {platform:'penpot', fileReference:api.currentFile.id, fileRevision:api.currentFile.revn,
    pageReference:api.currentPage.id, pages:api.currentFile.pages.map(p => ({id:p.id,name:p.name})),
    fonts:api.fonts.all.map(f => ({fontId:f.fontId,family:f.fontFamily,
      variants:f.variants.map(v => ({fontVariantId:v.fontVariantId,weight:Number(v.fontWeight),style:v.fontStyle}))})),
    components:api.library.local.components.map(c => {
      const main = c.mainInstance();
      return {componentReference:c.id,name:c.name,mainReference:main?.id,width:main?.width,height:main?.height};
    })};
}

const targetFile = "91396aad-60c8-808b-8008-c0885ca79899";
penpot.ui.open('TASK-010 实际环境检查',"http://127.0.0.1:57831/index.html",{width:440,height:280});
penpot.ui.onMessage(message => {
      if (message?.type !== 'task010-inspect') return;
      try {
        if (penpot.currentFile?.id !== targetFile) throw new Error('target_file_mismatch');
        penpot.ui.sendMessage({type:'task010-result',status:'CAPTURED',result:discoverPenpotHost(penpot)});
      } catch (error) { penpot.ui.sendMessage({type:'task010-result',status:'FAIL',error:String(error)}); }
    });
    
// Penpot Plugin API only. Execution is not fidelity or final page acceptance.
async function executePenpotAdapter(api, payload) {
  if (payload.platform !== 'penpot' || api.currentFile?.id !== payload.fileReference) throw new Error('file_reference_mismatch');
  const specs = [];
  function visit(spec) { specs.push(spec); for (const child of spec.children || []) visit(child); }
  visit(payload.page);
  const masters = new Map(), fonts = new Map();
  for (const spec of specs) {
    if (spec.type === 'Text') {
      const b = spec.fontBinding, font = api.fonts.findById(b.fontId);
      const variant = font?.variants.find(v => v.fontVariantId === b.fontVariantId);
      if (!font || font.fontFamily !== b.family || !variant || Number(variant.fontWeight) !== b.weight || variant.fontStyle !== b.style) {
        throw new Error(`missing_exact_font: ${spec.id}`);
      }
      fonts.set(spec.id, {font, variant});
    }
    if (spec.componentReference) {
      const component = api.library.local.components.find(c => c.id === spec.componentReference);
      const main = component?.mainInstance();
      if (!main || !main.isComponentMainInstance() || !main.isComponentRoot()) throw new Error(`missing_native_component: ${spec.id}`);
      function checkFonts(n) {
        if (n.type === 'text') {
          const font = api.fonts.findById(n.fontId), variant = font?.variants.find(v => v.fontVariantId === n.fontVariantId);
          if (!font || !variant || font.fontFamily !== n.fontFamily || variant.fontWeight !== n.fontWeight || variant.fontStyle !== n.fontStyle) {
            throw new Error(`missing_component_font: ${spec.id}`);
          }
        }
        for (const child of n.children || []) checkFonts(child);
      }
      checkFonts(main);
      // Never stretch a verified component to accommodate a different source geometry.
      if (spec.layout.width.mode !== 'fixed' || spec.layout.height.mode !== 'fixed' ||
          main.width !== spec.layout.width.value || main.height !== spec.layout.height.value) throw new Error(`component_geometry_mismatch: ${spec.id}`);
      masters.set(spec.componentReference, component);
    }
  }
  let page = payload.pageReference ? api.currentFile.pages.find(p => p.id === payload.pageReference) : null;
  if (payload.pageReference && !page) throw new Error('missing_target_page');
  const pageName = `${payload.documentId}/${payload.page.name}`;
  if (!page && api.currentFile.pages.some(p => p.name === pageName)) throw new Error('existing_page_requires_ledger');
  const rootName = `UI-IR/${payload.documentId}/${payload.page.id}`;
  if (page?.root.children.some(n => n.name === rootName)) throw new Error('existing_output_requires_review');
  const created = [], nodeMap = {}, helpers = [];
  const record = n => { if (!created.includes(n.id)) created.push(n.id); return n; };
  function descendants(n) { for (const child of n.children || []) { record(child); descendants(child); } }
  const modes = {fixed: 'fix', fill: 'fill', hug: 'auto'};
  function color(hex) {
    if (!/^#[a-f\d]{6}([a-f\d]{2})?$/i.test(hex)) throw new Error('invalid_resolved_color');
    return {fillColor: hex.slice(0, 7), fillOpacity: hex.length === 9 ? parseInt(hex.slice(7), 16) / 255 : 1};
  }
  function style(n, s, text) {
    if (text ? s.colorToken || s.fill : s.fill) n.fills = [color(text ? s.colorToken || s.fill : s.fill)];
    if (!text && s.opacity === undefined && n.isComponentCopyInstance?.()) return;
    n.opacity = s.opacity === undefined ? 1 : s.opacity;
    if (s.radius !== undefined) n.borderRadius = s.radius;
    if (s.stroke) { const c = color(s.stroke.color); n.strokes = [{strokeColor: c.fillColor, strokeOpacity: c.fillOpacity,
      strokeWidth: s.stroke.width, strokeStyle: 'solid', strokeAlignment: 'inner'}]; }
  }
  function container(n, layout) {
    n.fills = []; n.strokes = []; n.clipContent = false;
    const f = n.addFlexLayout();
    f.dir = layout.direction === 'horizontal' ? 'row' : 'column';
    f.wrap = layout.wrap ? 'wrap' : 'nowrap';
    f.rowGap = layout.gap; f.columnGap = layout.gap;
    f.paddingType = 'multiple';
    for (const side of ['top', 'right', 'bottom', 'left']) f[`${side}Padding`] = layout.padding[side];
    f.justifyContent = layout.alignment.main; f.alignItems = layout.alignment.cross;
    return f;
  }
  function sizing(n, layout, f) {
    const w = layout.width, h = layout.height;
    if (w.mode === 'fixed' || h.mode === 'fixed') n.resize(w.mode === 'fixed' ? w.value : n.width, h.mode === 'fixed' ? h.value : n.height);
    if (f) { f.horizontalSizing = modes[w.mode]; f.verticalSizing = modes[h.mode]; }
    if (n.layoutChild) { n.layoutChild.horizontalSizing = modes[w.mode]; n.layoutChild.verticalSizing = modes[h.mode]; }
  }
  const helperLayout = (direction, width) => ({direction, wrap: false, gap: 0, padding: {top:0,right:0,bottom:0,left:0},
    alignment: {main:'start',cross:'start'}, width, height:{mode:'hug'}});
  async function build(spec, parent, parentSpec = null) {
    let n, flex;
    if (spec.type === 'Text') {
      n = api.createText(spec.text);
      if (!n) throw new Error(`text_creation_failed: ${spec.id}`);
      record(n);
      const {font, variant} = fonts.get(spec.id); font.applyToText(n, variant);
      const t = spec.style.typographyToken;
      n.fontSize = String(t.fontSize);
      // Penpot's internal line-height is a multiplier of font size.
      n.lineHeight = String(t.lineHeight / t.fontSize); n.letterSpacing = String(t.letterSpacing);
      n.growType = spec.layout.width.mode === 'hug' ? 'auto-width' : spec.layout.height.mode === 'fixed' ? 'fixed' : 'auto-height';
    } else if (spec.componentReference) {
      n = record(masters.get(spec.componentReference).instance()); descendants(n);
      if (!n.isComponentCopyInstance() || n.component()?.id !== spec.componentReference) throw new Error(`instance_creation_failed: ${spec.id}`);
    } else {
      n = record(api.createBoard());
      flex = container(n, {...spec.layout, direction: spec.type === 'Grid' ? 'vertical' : spec.layout.direction});
    }
    parent.appendChild(n); n.name = spec.type === 'Page' ? rootName : spec.name; nodeMap[spec.id] = n.id;
    const layout = JSON.parse(JSON.stringify(spec.layout));
    if (parentSpec?.layout.alignment.cross === 'stretch') {
      const axis = parentSpec.layout.direction === 'vertical' ? 'width' : 'height';
      if (layout[axis].mode === 'hug') layout[axis] = {mode:'fill'};
    }
    sizing(n, layout, flex); style(n, spec.style, spec.type === 'Text');
    if (spec.type === 'Grid') {
      const rows = new Map();
      for (const cell of spec.gridCells) {
        let row = rows.get(cell.row);
        if (!row) {
          row = record(api.createBoard()); n.appendChild(row); row.name = `${spec.id}/grid-row/${cell.row}`;
          const l = helperLayout('horizontal', {mode:'fill'}); l.gap = spec.layout.gap;
          sizing(row, l, container(row, l)); rows.set(cell.row, row); helpers.push(row.id);
        }
        const wrapper = record(api.createBoard()); row.appendChild(wrapper); wrapper.name = `${spec.id}/grid-cell/${cell.id}`;
        const l = helperLayout('vertical', {mode:'fixed',value:cell.width});
        sizing(wrapper, l, container(wrapper, l)); helpers.push(wrapper.id);
        await build(spec.children.find(c => c.id === cell.id), wrapper);
      }
    } else for (const child of spec.children || []) await build(child, n, spec);
    return n;
  }
  let root;
  try {
    if (!page) { page = record(api.createPage()); page.name = pageName; }
    await api.openPage(page);
    const right = Math.max(80, ...page.root.children.map(n => n.x + n.width + 80));
    root = await build(payload.page, page.root); root.x = right; root.y = 80;
    if (typeof api.waitForLayoutUpdate === 'function') await api.waitForLayoutUpdate();
  } catch (error) {
    return {status:'FAIL', nativeExecution:'PARTIAL', finalAcceptance:'NOT_RUN', issues:[{code:'native_write_failed',detail:String(error)}],
      scope:'penpot_partial_translation',fileReference:payload.fileReference,adapterVersion:payload.adapterVersion,
      pageReference:page?.id, createdNodeIds:created, mutatedNodeIds:[], nodeMap, helperNodeIds:helpers};
  }
  return {status:'EXECUTED', scope:'penpot_native_translation', finalAcceptance:'NOT_RUN',
    adapterVersion:payload.adapterVersion,
    fileReference:api.currentFile.id, pageReference:page.id, rootReference:root.id, uiIrSha256:payload.uiIrSha256,
    tokensSha256:payload.tokensSha256, componentsSha256:payload.componentsSha256, iconsSha256:payload.iconsSha256,
    createdNodeIds:created, mutatedNodeIds:[], nodeMap, helperNodeIds:helpers};
}

// TASK-015: in-place content patch of exact existing linked copies; no page rebuild.
function snapshotPenpotPatchRoot(root){
  const nodes=[];
  function walk(n){
    const item={id:n.id,parent:n.parent?.id,type:n.type,name:n.name,x:n.x,y:n.y,width:n.width,height:n.height,
      children:(n.children||[]).map(c=>c.id),fills:n.fills,strokes:n.strokes,opacity:n.opacity,
      rotation:n.rotation,hidden:n.hidden,clipContent:n.clipContent,borderRadius:n.borderRadius,
      isCopy:n.isComponentCopyInstance(),isMain:n.isComponentMainInstance()};
    if(item.isCopy||item.isMain)item.component=n.component()?.id;
    if(n.type==='text')for(const key of ['characters','fontId','fontVariantId','fontFamily','fontWeight','fontStyle','fontSize','lineHeight','letterSpacing','growType'])item[key]=n[key];
    nodes.push(item);for(const c of n.children||[])walk(c);
  }
  walk(root);return nodes;
}

async function patchPenpotSectionContent(api,payload,execution,request){
  if(api.currentFile?.id!==execution.fileReference||payload.fileReference!==execution.fileReference||
     api.currentPage?.id!==execution.pageReference||execution.status!=='EXECUTED'||
     request.baseUiIrSha256!==execution.uiIrSha256||request.updatedUiIrSha256!==payload.uiIrSha256)
    throw new Error('section_patch_context_mismatch');
  if(!Number.isInteger(request.expectedRevision)||request.expectedRevision!==api.currentFile.revn)throw new Error('section_patch_stale_revision');
  const page=api.currentPage,root=page.getShapeById(execution.rootReference);
  if(!root||execution.nodeMap[payload.page.id]!==root.id||root.parent?.id!==page.root.id)throw new Error('section_patch_root_mismatch');
  const specs=new Map(),sections=new Map();
  function walk(spec,section=null,parentId=null){
    // Older admitted UI-IR uses top-level Frames for named regions. They must
    // be explicitly declared; arbitrary nested Frames never become Sections.
    if(spec.type==='Section'||(parentId===payload.page.id&&spec.type==='Frame'&&request.sectionIds?.includes(spec.id)))section=spec.id;
    specs.set(spec.id,spec);sections.set(spec.id,section);
    for(const c of spec.children||[])walk(c,section,spec.id);
  }walk(payload.page);
  if(!Array.isArray(request.uiIrIds)||!request.uiIrIds.length||new Set(request.uiIrIds).size!==request.uiIrIds.length)throw new Error('invalid_patch_targets');
  const owned=new Set(execution.createdNodeIds),pending=[],allowed=new Set();
  for(const id of request.uiIrIds){
    const spec=specs.get(id),copy=page.getShapeById(execution.nodeMap[id]);
    let ancestor=copy;while(ancestor&&ancestor.id!==root.id)ancestor=ancestor.parent;
    if(!spec?.nativeContent?.length||!sections.get(id)||!ancestor||!owned.has(copy.id)||!copy.isComponentCopyInstance()||
       copy.isComponentMainInstance()||copy.component()?.id!==spec.componentReference)throw new Error('unsupported_section_patch_target');
    const maps=spec.nativeContent.map(m=>({...m,expectedText:request.expectedCharacters?.[id]?.[m.name]}));
    if(maps.some(m=>typeof m.expectedText!=='string'))throw new Error('missing_patch_content_checkpoint');
    preflightPenpotNativeContent(copy,maps);
    function own(n){allowed.add(n.id);for(const c of n.children||[])own(c);}own(copy);
    pending.push({id,copy,maps});
  }
  const before=snapshotPenpotPatchRoot(root),revision=api.currentFile.revn,applied=[];
  try{
    // No writes before every requested copy is identified; each helper also preflights its text.
    for(const p of pending){await applyPenpotNativeContent(api,p.copy,p.maps);applied.push(p);}
    const after=snapshotPenpotPatchRoot(root);
    if(JSON.stringify(before.filter(n=>!allowed.has(n.id)))!==JSON.stringify(after.filter(n=>!allowed.has(n.id))))throw new Error('section_patch_changed_unrelated_nodes');
    if(JSON.stringify(before.map(n=>n.id))!==JSON.stringify(after.map(n=>n.id)))throw new Error('section_patch_changed_topology');
    return {status:'PATCHED',scope:'penpot-native-section-content-patch',finalAcceptance:'NOT_RUN',fileReference:execution.fileReference,
      pageReference:page.id,rootReference:root.id,beforeRevision:revision,afterRevision:api.currentFile.revn,
      baseUiIrSha256:execution.uiIrSha256,updatedUiIrSha256:payload.uiIrSha256,
      changedSections:[...new Set(pending.map(p=>sections.get(p.id)))],createdNodeIds:[],removedNodeIds:[],
      patchedCopyIds:pending.map(p=>p.copy.id),before,after};
  }catch(error){
    for(const p of applied.reverse()){
      const reverse=p.maps.map(m=>({...m,expectedText:m.text,text:m.expectedText}));
      try{await applyPenpotNativeContent(api,p.copy,reverse);}catch(rollback){throw new Error(`section_patch_recovery_required: ${error}; ${rollback}`);}
    }
    throw error;
  }
}

// Read independently after mutation. Caller must retain/export this separately from execution.
async function capturePenpotSectionPatch(api,execution){
  if(api.currentFile?.id!==execution.fileReference||api.currentPage?.id!==execution.pageReference)throw new Error('patch_capture_context_mismatch');
  const root=api.currentPage.getShapeById(execution.rootReference),revision=api.currentFile.revn;
  if(!root)throw new Error('patch_capture_missing_root');
  const nodes=snapshotPenpotPatchRoot(root),png=await root.export({type:'png',scale:1});
  if(revision!==api.currentFile.revn||JSON.stringify(nodes)!==JSON.stringify(snapshotPenpotPatchRoot(root)))throw new Error('patch_capture_state_changed');
  let binary='';for(let i=0;i<png.length;i+=8192)binary+=String.fromCharCode(...png.subarray(i,i+8192));
  return {status:'CAPTURED',scope:'penpot-native-section-patch-capture',fileReference:execution.fileReference,
    pageReference:execution.pageReference,rootReference:root.id,fileRevision:revision,nodes,nativePngBase64:btoa(binary)};
}

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

const detailsPayload={"platform": "penpot", "adapterVersion": "0.1.0", "documentId": "task015-native-content-details", "uiIrSha256": "486570618570ab6d3bb6b0b3a6bd1b40b7e801e673634ca6e0439382b311de9d", "tokensSha256": "c45fc025aa3293a675933e377ccdfc90c60204f990ff90402fcb5ebc00178c2f", "componentsSha256": "028aa6a9f330e3199fef0fa331111229648ca8299f78d376df70e93a5b0ec369", "iconsSha256": "642072b677f35e538592cca05b02b2f37ca5770d08f602fd8953754cd217ebde", "fileReference": "91396aad-60c8-808b-8008-c0885ca79899", "page": {"id": "acceptance-page", "name": "用户管理列表 · TASK-009 验收", "type": "Page", "layout": {"width": {"mode": "fixed", "value": 1440}, "height": {"mode": "hug"}, "padding": {"top": 24, "right": 24, "bottom": 24, "left": 24}, "gap": 24, "direction": "vertical", "wrap": false, "alignment": {"main": "start", "cross": "start"}}, "style": {"fill": "#f4f5f7"}, "children": [{"id": "header", "name": "header", "type": "Row", "layout": {"width": {"mode": "fill"}, "height": {"mode": "hug"}, "padding": {"top": 0, "right": 0, "bottom": 0, "left": 0}, "gap": 16, "direction": "horizontal", "wrap": false, "alignment": {"main": "start", "cross": "center"}}, "style": {}, "children": [{"id": "title", "name": "title", "type": "Text", "layout": {"width": {"mode": "hug"}, "height": {"mode": "hug"}, "padding": {"top": 0, "right": 0, "bottom": 0, "left": 0}, "gap": 0, "direction": "vertical", "wrap": false, "alignment": {"main": "start", "cross": "start"}}, "style": {"typographyToken": {"fontFamily": "Noto Sans SC", "fontSize": 20, "fontWeight": 600, "lineHeight": 28, "letterSpacing": 0}, "colorToken": "#20252b"}, "text": "用户管理", "fontBinding": {"fontId": "gfont-noto-sans-sc", "fontVariantId": "600", "family": "Noto Sans SC", "weight": 600, "style": "normal"}}, {"id": "header.space", "name": "header.space", "type": "Frame", "layout": {"width": {"mode": "fill"}, "height": {"mode": "fixed", "value": 24}, "padding": {"top": 0, "right": 0, "bottom": 0, "left": 0}, "gap": 0, "direction": "vertical", "wrap": false, "alignment": {"main": "start", "cross": "start"}}, "style": {}, "children": []}, {"id": "header.settings", "name": "header.settings", "type": "IconInstance", "layout": {"width": {"mode": "fixed", "value": 24}, "height": {"mode": "fixed", "value": 24}, "padding": {"top": 0, "right": 0, "bottom": 0, "left": 0}, "gap": 0, "direction": "vertical", "wrap": false, "alignment": {"main": "start", "cross": "start"}}, "style": {}, "componentReference": "6d6e57fb-4a0a-8065-8008-c0fc685ca781", "svgSha256": "f2e1fd30e6eadb8d5636f5037cf477f38ef81b235757d3ed290b92b2c002fec1"}]}, {"id": "query", "name": "query", "type": "Frame", "layout": {"width": {"mode": "fill"}, "height": {"mode": "hug"}, "padding": {"top": 16, "right": 16, "bottom": 16, "left": 16}, "gap": 0, "direction": "vertical", "wrap": false, "alignment": {"main": "start", "cross": "start"}}, "style": {"fill": "#ffffff"}, "children": [{"id": "query.grid", "name": "query.grid", "type": "Grid", "layout": {"width": {"mode": "fill"}, "height": {"mode": "hug"}, "padding": {"top": 0, "right": 0, "bottom": 0, "left": 0}, "gap": 16, "direction": "horizontal", "wrap": false, "alignment": {"main": "start", "cross": "start"}}, "style": {}, "gridWidth": 1360, "gridCells": [{"id": "filter.name", "row": 0, "width": 328.0}, {"id": "filter.status", "row": 0, "width": 328.0}, {"id": "filter.summary", "row": 0, "width": 328.0}, {"id": "filter.action", "row": 0, "width": 328.0}], "children": [{"id": "filter.name", "name": "filter.name", "type": "Frame", "layout": {"width": {"mode": "fill"}, "height": {"mode": "hug"}, "padding": {"top": 0, "right": 0, "bottom": 0, "left": 0}, "gap": 8, "direction": "vertical", "wrap": false, "alignment": {"main": "start", "cross": "start"}}, "style": {}, "children": [{"id": "label.name", "name": "label.name", "type": "Text", "layout": {"width": {"mode": "hug"}, "height": {"mode": "hug"}, "padding": {"top": 0, "right": 0, "bottom": 0, "left": 0}, "gap": 0, "direction": "vertical", "wrap": false, "alignment": {"main": "start", "cross": "start"}}, "style": {"typographyToken": {"fontFamily": "Noto Sans SC", "fontSize": 14, "fontWeight": 400, "lineHeight": 22, "letterSpacing": 0}, "colorToken": "#20252b"}, "text": "姓名", "fontBinding": {"fontId": "gfont-noto-sans-sc", "fontVariantId": "regular", "family": "Noto Sans SC", "weight": 400, "style": "normal"}}, {"id": "input.name", "name": "input.name", "type": "ComponentInstance", "layout": {"width": {"mode": "fixed", "value": 240}, "height": {"mode": "fixed", "value": 32}, "padding": {"top": 0, "right": 0, "bottom": 0, "left": 0}, "gap": 0, "direction": "vertical", "wrap": false, "alignment": {"main": "start", "cross": "start"}}, "style": {}, "componentReference": "b17404b9-592b-8074-8008-c0cd36551084", "fidelityReportSha256": "095db86f0fd809bcd410dc49eb9a3ec9d05cae7162bc27e38fc47cde7decdab3"}]}, {"id": "filter.status", "name": "filter.status", "type": "Frame", "layout": {"width": {"mode": "fill"}, "height": {"mode": "hug"}, "padding": {"top": 0, "right": 0, "bottom": 0, "left": 0}, "gap": 8, "direction": "vertical", "wrap": false, "alignment": {"main": "start", "cross": "start"}}, "style": {}, "children": [{"id": "label.status", "name": "label.status", "type": "Text", "layout": {"width": {"mode": "hug"}, "height": {"mode": "hug"}, "padding": {"top": 0, "right": 0, "bottom": 0, "left": 0}, "gap": 0, "direction": "vertical", "wrap": false, "alignment": {"main": "start", "cross": "start"}}, "style": {"typographyToken": {"fontFamily": "Noto Sans SC", "fontSize": 14, "fontWeight": 400, "lineHeight": 22, "letterSpacing": 0}, "colorToken": "#20252b"}, "text": "状态", "fontBinding": {"fontId": "gfont-noto-sans-sc", "fontVariantId": "regular", "family": "Noto Sans SC", "weight": 400, "style": "normal"}}, {"id": "select.status", "name": "select.status", "type": "ComponentInstance", "layout": {"width": {"mode": "fixed", "value": 240}, "height": {"mode": "fixed", "value": 32}, "padding": {"top": 0, "right": 0, "bottom": 0, "left": 0}, "gap": 0, "direction": "vertical", "wrap": false, "alignment": {"main": "start", "cross": "start"}}, "style": {}, "componentReference": "b17404b9-592b-8074-8008-c0d00dc30929", "fidelityReportSha256": "24ec8a72a08bb332b4f73734b17ab1772f34f378bc5130da4f7071435c0c4e21"}]}, {"id": "filter.summary", "name": "filter.summary", "type": "Frame", "layout": {"width": {"mode": "fill"}, "height": {"mode": "hug"}, "padding": {"top": 0, "right": 0, "bottom": 0, "left": 0}, "gap": 8, "direction": "vertical", "wrap": false, "alignment": {"main": "start", "cross": "start"}}, "style": {}, "children": [{"id": "label.summary", "name": "label.summary", "type": "Text", "layout": {"width": {"mode": "hug"}, "height": {"mode": "hug"}, "padding": {"top": 0, "right": 0, "bottom": 0, "left": 0}, "gap": 0, "direction": "vertical", "wrap": false, "alignment": {"main": "start", "cross": "start"}}, "style": {"typographyToken": {"fontFamily": "Noto Sans SC", "fontSize": 14, "fontWeight": 400, "lineHeight": 22, "letterSpacing": 0}, "colorToken": "#20252b"}, "text": "范围", "fontBinding": {"fontId": "gfont-noto-sans-sc", "fontVariantId": "regular", "family": "Noto Sans SC", "weight": 400, "style": "normal"}}, {"id": "filter.description", "name": "filter.description", "type": "Text", "layout": {"width": {"mode": "hug"}, "height": {"mode": "hug"}, "padding": {"top": 0, "right": 0, "bottom": 0, "left": 0}, "gap": 0, "direction": "vertical", "wrap": false, "alignment": {"main": "start", "cross": "start"}}, "style": {"typographyToken": {"fontFamily": "Noto Sans SC", "fontSize": 14, "fontWeight": 400, "lineHeight": 22, "letterSpacing": 0}, "colorToken": "#20252b"}, "text": "查看用户信息", "fontBinding": {"fontId": "gfont-noto-sans-sc", "fontVariantId": "regular", "family": "Noto Sans SC", "weight": 400, "style": "normal"}}]}, {"id": "filter.action", "name": "filter.action", "type": "Frame", "layout": {"width": {"mode": "fill"}, "height": {"mode": "hug"}, "padding": {"top": 0, "right": 0, "bottom": 0, "left": 0}, "gap": 8, "direction": "vertical", "wrap": false, "alignment": {"main": "start", "cross": "start"}}, "style": {}, "children": [{"id": "label.action", "name": "label.action", "type": "Text", "layout": {"width": {"mode": "hug"}, "height": {"mode": "hug"}, "padding": {"top": 0, "right": 0, "bottom": 0, "left": 0}, "gap": 0, "direction": "vertical", "wrap": false, "alignment": {"main": "start", "cross": "start"}}, "style": {"typographyToken": {"fontFamily": "Noto Sans SC", "fontSize": 14, "fontWeight": 400, "lineHeight": 22, "letterSpacing": 0}, "colorToken": "#20252b"}, "text": "操作", "fontBinding": {"fontId": "gfont-noto-sans-sc", "fontVariantId": "regular", "family": "Noto Sans SC", "weight": 400, "style": "normal"}}, {"id": "button.query", "name": "button.query", "type": "ComponentInstance", "layout": {"width": {"mode": "fixed", "value": 60}, "height": {"mode": "fixed", "value": 32}, "padding": {"top": 0, "right": 0, "bottom": 0, "left": 0}, "gap": 0, "direction": "vertical", "wrap": false, "alignment": {"main": "start", "cross": "start"}}, "style": {}, "componentReference": "10f3de97-3a09-806f-8008-c0aff4ac5af0", "fidelityReportSha256": "f5f768a7041c2302f10efaf2360ebce52f99031898fba81fd6e99827847e6c11"}]}]}]}, {"id": "list", "name": "list", "type": "Frame", "layout": {"width": {"mode": "fill"}, "height": {"mode": "hug"}, "padding": {"top": 0, "right": 0, "bottom": 0, "left": 0}, "gap": 0, "direction": "vertical", "wrap": false, "alignment": {"main": "start", "cross": "start"}}, "style": {"fill": "#ffffff"}, "children": [{"id": "list.toolbar", "name": "list.toolbar", "type": "Row", "layout": {"width": {"mode": "fill"}, "height": {"mode": "fixed", "value": 40}, "padding": {"top": 0, "right": 0, "bottom": 0, "left": 0}, "gap": 8, "direction": "horizontal", "wrap": false, "alignment": {"main": "start", "cross": "center"}}, "style": {}, "children": [{"id": "list.title", "name": "list.title", "type": "Text", "layout": {"width": {"mode": "hug"}, "height": {"mode": "hug"}, "padding": {"top": 0, "right": 0, "bottom": 0, "left": 0}, "gap": 0, "direction": "vertical", "wrap": false, "alignment": {"main": "start", "cross": "start"}}, "style": {"typographyToken": {"fontFamily": "Noto Sans SC", "fontSize": 14, "fontWeight": 400, "lineHeight": 22, "letterSpacing": 0}, "colorToken": "#20252b"}, "text": "用户列表", "fontBinding": {"fontId": "gfont-noto-sans-sc", "fontVariantId": "regular", "family": "Noto Sans SC", "weight": 400, "style": "normal"}}, {"id": "list.space", "name": "list.space", "type": "Frame", "layout": {"width": {"mode": "fill"}, "height": {"mode": "fixed", "value": 24}, "padding": {"top": 0, "right": 0, "bottom": 0, "left": 0}, "gap": 0, "direction": "vertical", "wrap": false, "alignment": {"main": "start", "cross": "start"}}, "style": {}, "children": []}, {"id": "list.export", "name": "list.export", "type": "IconInstance", "layout": {"width": {"mode": "fixed", "value": 24}, "height": {"mode": "fixed", "value": 24}, "padding": {"top": 0, "right": 0, "bottom": 0, "left": 0}, "gap": 0, "direction": "vertical", "wrap": false, "alignment": {"main": "start", "cross": "start"}}, "style": {}, "componentReference": "6d6e57fb-4a0a-8065-8008-c0fc6866e456", "svgSha256": "ad83ac7dc9d4c6af651a53068e928d82f9402cfd05a924742388549846032f43"}, {"id": "list.export.label", "name": "list.export.label", "type": "Text", "layout": {"width": {"mode": "hug"}, "height": {"mode": "hug"}, "padding": {"top": 0, "right": 0, "bottom": 0, "left": 0}, "gap": 0, "direction": "vertical", "wrap": false, "alignment": {"main": "start", "cross": "start"}}, "style": {"typographyToken": {"fontFamily": "Noto Sans SC", "fontSize": 14, "fontWeight": 400, "lineHeight": 22, "letterSpacing": 0}, "colorToken": "#20252b"}, "text": "导出", "fontBinding": {"fontId": "gfont-noto-sans-sc", "fontVariantId": "regular", "family": "Noto Sans SC", "weight": 400, "style": "normal"}}]}, {"id": "list.columns", "name": "list.columns", "type": "Row", "layout": {"width": {"mode": "fill"}, "height": {"mode": "hug"}, "padding": {"top": 0, "right": 0, "bottom": 0, "left": 0}, "gap": 0, "direction": "horizontal", "wrap": false, "alignment": {"main": "start", "cross": "start"}}, "style": {"fill": "#ffffff"}, "children": [{"id": "column.name", "name": "column.name", "type": "Frame", "layout": {"width": {"mode": "fixed", "value": 464.328125}, "height": {"mode": "fixed", "value": 48}, "padding": {"top": 0, "right": 0, "bottom": 0, "left": 16}, "gap": 0, "direction": "horizontal", "wrap": false, "alignment": {"main": "start", "cross": "center"}}, "style": {}, "children": [{"id": "column.name.label", "name": "column.name.label", "type": "Text", "layout": {"width": {"mode": "hug"}, "height": {"mode": "hug"}, "padding": {"top": 0, "right": 0, "bottom": 0, "left": 0}, "gap": 0, "direction": "vertical", "wrap": false, "alignment": {"main": "start", "cross": "start"}}, "style": {"typographyToken": {"fontFamily": "Noto Sans SC", "fontSize": 14, "fontWeight": 400, "lineHeight": 22, "letterSpacing": 0}, "colorToken": "#20252b"}, "text": "姓名", "fontBinding": {"fontId": "gfont-noto-sans-sc", "fontVariantId": "regular", "family": "Noto Sans SC", "weight": 400, "style": "normal"}}]}, {"id": "column.status", "name": "column.status", "type": "Frame", "layout": {"width": {"mode": "fixed", "value": 464.328125}, "height": {"mode": "fixed", "value": 48}, "padding": {"top": 0, "right": 0, "bottom": 0, "left": 16}, "gap": 0, "direction": "horizontal", "wrap": false, "alignment": {"main": "start", "cross": "center"}}, "style": {}, "children": [{"id": "column.status.label", "name": "column.status.label", "type": "Text", "layout": {"width": {"mode": "hug"}, "height": {"mode": "hug"}, "padding": {"top": 0, "right": 0, "bottom": 0, "left": 0}, "gap": 0, "direction": "vertical", "wrap": false, "alignment": {"main": "start", "cross": "start"}}, "style": {"typographyToken": {"fontFamily": "Noto Sans SC", "fontSize": 14, "fontWeight": 400, "lineHeight": 22, "letterSpacing": 0}, "colorToken": "#20252b"}, "text": "状态", "fontBinding": {"fontId": "gfont-noto-sans-sc", "fontVariantId": "regular", "family": "Noto Sans SC", "weight": 400, "style": "normal"}}]}, {"id": "column.role", "name": "column.role", "type": "Frame", "layout": {"width": {"mode": "fixed", "value": 463.34375}, "height": {"mode": "fixed", "value": 48}, "padding": {"top": 0, "right": 0, "bottom": 0, "left": 16}, "gap": 0, "direction": "horizontal", "wrap": false, "alignment": {"main": "start", "cross": "center"}}, "style": {}, "children": [{"id": "column.role.label", "name": "column.role.label", "type": "Text", "layout": {"width": {"mode": "hug"}, "height": {"mode": "hug"}, "padding": {"top": 0, "right": 0, "bottom": 0, "left": 0}, "gap": 0, "direction": "vertical", "wrap": false, "alignment": {"main": "start", "cross": "start"}}, "style": {"typographyToken": {"fontFamily": "Noto Sans SC", "fontSize": 14, "fontWeight": 400, "lineHeight": 22, "letterSpacing": 0}, "colorToken": "#20252b"}, "text": "角色", "fontBinding": {"fontId": "gfont-noto-sans-sc", "fontVariantId": "regular", "family": "Noto Sans SC", "weight": 400, "style": "normal"}}]}]}, {"id": "table.body", "name": "table.body", "type": "ComponentInstance", "layout": {"width": {"mode": "fixed", "value": 1392}, "height": {"mode": "fixed", "value": 144}, "padding": {"top": 0, "right": 0, "bottom": 0, "left": 0}, "gap": 0, "direction": "vertical", "wrap": false, "alignment": {"main": "start", "cross": "start"}}, "style": {}, "componentReference": "6d6e57fb-4a0a-8065-8008-c0f928688eff", "fidelityReportSha256": "0984deb3fbaa90614cc8069d47bdfc326850a4ba356902a57a98c53eeee2e49d"}]}, {"id": "list.count", "name": "list.count", "type": "Text", "layout": {"width": {"mode": "hug"}, "height": {"mode": "hug"}, "padding": {"top": 0, "right": 0, "bottom": 0, "left": 0}, "gap": 0, "direction": "vertical", "wrap": false, "alignment": {"main": "start", "cross": "start"}}, "style": {"typographyToken": {"fontFamily": "Noto Sans SC", "fontSize": 14, "fontWeight": 400, "lineHeight": 22, "letterSpacing": 0}, "colorToken": "#20252b"}, "text": "共 3 位用户", "fontBinding": {"fontId": "gfont-noto-sans-sc", "fontVariantId": "regular", "family": "Noto Sans SC", "weight": 400, "style": "normal"}}]}, "pageReference": null};
let detailsExecution=null;let detailsBefore=null;let detailsRequest=null;let detailsPatched=false;
penpot.ui.onMessage(async message=>{
      if(!['task015-details-baseline','task015-details-before','task015-details-patch','task015-details-after'].includes(message?.type))return;
      try{let result;
        if(penpot.currentFile?.id!==targetFile)throw new Error('details_file_mismatch');
        if(message.type==='task015-details-baseline'){
          if(detailsExecution)throw new Error('details_baseline_already_exists');
          result=detailsExecution=await executePenpotAdapter(penpot,detailsPayload);
        }else{
          if(detailsExecution?.status!=='EXECUTED')throw new Error('details_baseline_required');
          if(message.type==='task015-details-before'){
            result=detailsBefore=await capturePenpotSectionPatch(penpot,detailsExecution);
            const targets=[];
            const recipes=[['input.name','official-source / form.input.default.medium / 0.1::placeholder','姓名','query'],
              ['select.status','official-source / form.select.default.medium / 0.0.1.0','停用','query'],
              ['button.query','official-source / action.button.primary.medium / 0.0','导出','query'],
              ['column.role.label','column.role.label','范围','list'],['filter.description','filter.description','用户列表','query']];
            const nodes=new Map(result.nodes.map(n=>[n.id,n]));
            for(const [uiId,name,text,section] of recipes){
              const owner=nodes.get(detailsExecution.nodeMap[uiId]);
              const found=result.nodes.filter(n=>n.type==='text'&&n.name===name);
              if(!owner||found.length!==1)throw new Error('details_target_ambiguous');
              const n=found[0],style={};for(const k of ['fontId','fontVariantId','fontFamily','fontWeight','fontStyle','fontSize','lineHeight','letterSpacing','growType'])style[k]=n[k];
              targets.push({ownerReference:owner.id,textReference:n.id,name,expectedText:n.characters,text,
                sectionReference:detailsExecution.nodeMap[section],componentReference:owner.isCopy?owner.component:null,style});
            }detailsRequest={targets};result={...result,request:detailsRequest};
          }else if(message.type==='task015-details-after')result=await capturePenpotSectionPatch(penpot,detailsExecution);
          else{
            if(!detailsBefore||detailsPatched)throw new Error('details_requires_independent_before');
            detailsPatched=true;
            result=await patchPenpotPrimitiveContent(penpot,detailsExecution,detailsRequest,detailsBefore);
          }
        }
        penpot.ui.sendMessage({type:'task010-result',status:'CAPTURED',result});
      }catch(error){penpot.ui.sendMessage({type:'task010-result',status:'FAIL',error:String(error)});}
    });