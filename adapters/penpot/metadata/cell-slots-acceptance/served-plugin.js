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

// Populate explicitly owned empty role frames; never recreate the page or Cell.
async function fillPenpotCellSlots(api, execution, request, beforeCapture) {
  if (execution.status !== 'EXECUTED' || api.currentFile?.id !== execution.fileReference ||
      api.currentPage?.id !== execution.pageReference || beforeCapture.status !== 'CAPTURED' ||
      ['fileReference','pageReference','rootReference'].some(k => beforeCapture[k] !== execution[k]))
    throw new Error('slot_context_mismatch');
  const root = api.currentPage.getShapeById(execution.rootReference);
  if (!root || root.parent?.id !== api.currentPage.root.id ||
      JSON.stringify(snapshotPenpotPatchRoot(root)) !== JSON.stringify(beforeCapture.nodes))
    throw new Error('slot_checkpoint_mismatch');
  const owned = new Set(execution.createdNodeIds), pending = [], names = new Set(), sources = new Map();
  const roles = new Set();
  for (const item of request.items) {
    const parent = api.currentPage.getShapeById(execution.nodeMap[item.roleId]);
    let ancestor = parent; while (ancestor && ancestor.id !== root.id) ancestor = ancestor.parent;
    if (!parent || !ancestor || !owned.has(parent.id) || parent.children.length ||
        roles.has(item.roleId) || parent.width !== item.width || parent.height !== item.height || !item.children.length)
      throw new Error('slot_envelope_mismatch');
    roles.add(item.roleId);
    for (const spec of item.children) {
      if (names.has(spec.id) || execution.nodeMap[spec.id]) throw new Error('slot_duplicate_id');
      names.add(spec.id);
      if (spec.layout.width.mode !== 'fixed' || spec.layout.height.mode !== 'fixed' ||
          spec.layout.height.value > parent.height) throw new Error('slot_child_geometry');
      if (spec.componentReference) {
        const component = api.library.local.components.find(c => c.id === spec.componentReference), main = component?.mainInstance();
        if (!main?.isComponentMainInstance() || !main.isComponentRoot() ||
            main.width !== spec.layout.width.value || main.height !== spec.layout.height.value)
          throw new Error('slot_source_geometry');
        const snapshot = snapshotPenpotPatchRoot(main);
        for (const text of snapshot.filter(n => n.type === 'text')) {
          const font = api.fonts.findById(text.fontId), variant = font?.variants.find(v => v.fontVariantId === text.fontVariantId);
          if (!variant || font.fontFamily !== text.fontFamily || variant.fontWeight !== text.fontWeight || variant.fontStyle !== text.fontStyle)
            throw new Error('slot_master_font');
        }
        sources.set(spec.id,{component, snapshot});
      } else if (spec.type === 'Text') {
        const binding = spec.fontBinding, font = api.fonts.findById(binding.fontId);
        const variant = font?.variants.find(v => v.fontVariantId === binding.fontVariantId);
        if (!variant || font.fontFamily !== binding.family || Number(variant.fontWeight) !== binding.weight || variant.fontStyle !== binding.style)
          throw new Error('slot_source_font');
        sources.set(spec.id,{font,variant});
      } else throw new Error('slot_unsupported_child');
    }
    if (item.children.reduce((w,s) => w+s.layout.width.value,0) > parent.width) throw new Error('slot_width_overflow');
    pending.push({parent,item});
  }
  if (!pending.length) throw new Error('slot_empty_request');
  const created = [], map = {}, before = snapshotPenpotPatchRoot(root);
  function record(node) { created.push(node.id); for (const child of node.children || []) record(child); }
  try {
    for (const {parent,item} of pending) for (const spec of item.children) {
      const source = sources.get(spec.id); let node;
      if (source.component) {
        node = source.component.instance(); record(node);
        if (!node.isComponentCopyInstance() || node.component()?.id !== spec.componentReference) throw new Error('slot_not_genuine_instance');
      } else {
        node = api.createText(spec.text); record(node); source.font.applyToText(node,source.variant);
        const style = spec.style.typographyToken;
        node.fontSize = String(style.fontSize); node.lineHeight = String(style.lineHeight/style.fontSize);
        node.letterSpacing = String(style.letterSpacing); node.growType = 'fixed';
        const color = spec.style.colorToken;
        node.fills = [{fillColor:color.slice(0,7),fillOpacity:color.length === 9 ? parseInt(color.slice(7),16)/255 : 1}];
        node.opacity = 1;
      }
      parent.appendChild(node); node.name = spec.name; map[spec.id] = node.id;
      node.resize(spec.layout.width.value,spec.layout.height.value);
      node.layoutChild.horizontalSizing = 'fix'; node.layoutChild.verticalSizing = 'fix';
    }
    await api.waitForLayoutUpdate();
    const after = snapshotPenpotPatchRoot(root), old = new Map(before.map(n => [n.id,n])), targets = new Set(pending.map(p => p.parent.id));
    if (before.some(n => !after.some(a => a.id === n.id)) ||
        after.some(n => !old.has(n.id) && !created.includes(n.id))) throw new Error('slot_incomplete_node_ledger');
    for (const {parent,item} of pending) for (const spec of item.children) {
      const node = api.currentPage.getShapeById(map[spec.id]);
      if (!node || node.parent?.id !== parent.id || node.width !== spec.layout.width.value || node.height !== spec.layout.height.value ||
          node.x < parent.x || node.y < parent.y || node.x+node.width > parent.x+parent.width || node.y+node.height > parent.y+parent.height)
        throw new Error('slot_native_child_overflow');
    }
    for (const n of after) if (old.has(n.id)) {
      const a = {...old.get(n.id)}, b = {...n};
      if (targets.has(n.id)) { delete a.children; delete b.children; }
      if (JSON.stringify(a) !== JSON.stringify(b)) throw new Error('slot_existing_node_changed');
    }
    for (const source of sources.values()) if (source.component &&
      JSON.stringify(source.snapshot) !== JSON.stringify(snapshotPenpotPatchRoot(source.component.mainInstance())))
      throw new Error('slot_master_changed');
    return {status:'FILLED',fileReference:execution.fileReference,pageReference:execution.pageReference,
      rootReference:root.id,createdNodeIds:created,removedNodeIds:[],mutatedNodeIds:[...targets],nodeMap:map,
      before,after,fullTask015Acceptance:false};
  } catch (error) {
    return {status:'FAIL',nativeExecution:'PARTIAL',recoveryRequired:created.length>0,
      createdNodeIds:created,nodeMap:map,before,after:snapshotPenpotPatchRoot(root),issues:[String(error)]};
  }
}

const slotsPayload={"platform": "penpot", "adapterVersion": "0.1.0", "documentId": "task015-six-cell-slots", "uiIrSha256": "a414f564c5d05dab3045ce62bd9e224597b2715885d01ab3b3b1bbec6ccafaaa", "tokensSha256": "c45fc025aa3293a675933e377ccdfc90c60204f990ff90402fcb5ebc00178c2f", "componentsSha256": "028aa6a9f330e3199fef0fa331111229648ca8299f78d376df70e93a5b0ec369", "iconsSha256": "642072b677f35e538592cca05b02b2f37ca5770d08f602fd8953754cd217ebde", "fileReference": "91396aad-60c8-808b-8008-c0885ca79899", "page": {"id": "slot-page", "name": "六类槽位验收", "type": "Page", "layout": {"width": {"mode": "fixed", "value": 1440}, "height": {"mode": "fixed", "value": 80}, "padding": {"top": 24, "right": 24, "bottom": 24, "left": 24}, "gap": 0, "direction": "vertical", "wrap": false, "alignment": {"main": "start", "cross": "start"}}, "style": {"fill": "#f4f5f7"}, "children": [{"id": "slot-cell", "name": "slot-cell", "type": "Frame", "layout": {"width": {"mode": "fixed", "value": 1392}, "height": {"mode": "fixed", "value": 32}, "padding": {"top": 0, "right": 0, "bottom": 0, "left": 0}, "gap": 8, "direction": "horizontal", "wrap": false, "alignment": {"main": "start", "cross": "start"}}, "style": {}, "children": [{"id": "slot-cell.slot.leading-icon", "name": "slot-cell.slot.leading-icon", "type": "Frame", "layout": {"width": {"mode": "fixed", "value": 24}, "height": {"mode": "fixed", "value": 32}, "padding": {"top": 0, "right": 0, "bottom": 0, "left": 0}, "gap": 8, "direction": "horizontal", "wrap": false, "alignment": {"main": "start", "cross": "center"}}, "style": {}, "children": []}, {"id": "slot-cell.slot.label", "name": "slot-cell.slot.label", "type": "Frame", "layout": {"width": {"mode": "fixed", "value": 28}, "height": {"mode": "fixed", "value": 32}, "padding": {"top": 0, "right": 0, "bottom": 0, "left": 0}, "gap": 8, "direction": "horizontal", "wrap": false, "alignment": {"main": "start", "cross": "center"}}, "style": {}, "children": []}, {"id": "slot-cell.slot.control", "name": "slot-cell.slot.control", "type": "Frame", "layout": {"width": {"mode": "fixed", "value": 240}, "height": {"mode": "fixed", "value": 32}, "padding": {"top": 0, "right": 0, "bottom": 0, "left": 0}, "gap": 8, "direction": "horizontal", "wrap": false, "alignment": {"main": "start", "cross": "center"}}, "style": {}, "children": []}, {"id": "slot-cell.slot.trailing-icon", "name": "slot-cell.slot.trailing-icon", "type": "Frame", "layout": {"width": {"mode": "fixed", "value": 24}, "height": {"mode": "fixed", "value": 32}, "padding": {"top": 0, "right": 0, "bottom": 0, "left": 0}, "gap": 8, "direction": "horizontal", "wrap": false, "alignment": {"main": "start", "cross": "center"}}, "style": {}, "children": []}, {"id": "slot-cell.slot.content", "name": "slot-cell.slot.content", "type": "Frame", "layout": {"width": {"mode": "fixed", "value": 56}, "height": {"mode": "fixed", "value": 32}, "padding": {"top": 0, "right": 0, "bottom": 0, "left": 0}, "gap": 8, "direction": "horizontal", "wrap": false, "alignment": {"main": "start", "cross": "center"}}, "style": {}, "children": []}, {"id": "slot-cell.slot.actions", "name": "slot-cell.slot.actions", "type": "Frame", "layout": {"width": {"mode": "fixed", "value": 60}, "height": {"mode": "fixed", "value": 32}, "padding": {"top": 0, "right": 0, "bottom": 0, "left": 0}, "gap": 8, "direction": "horizontal", "wrap": false, "alignment": {"main": "start", "cross": "center"}}, "style": {}, "children": []}]}]}, "pageReference": null};const slotsRequest={"items": [{"roleId": "slot-cell.slot.leading-icon", "width": 24, "height": 32, "children": [{"id": "slot-leading", "name": "slot-leading", "type": "IconInstance", "layout": {"width": {"mode": "fixed", "value": 24}, "height": {"mode": "fixed", "value": 24}, "padding": {"top": 0, "right": 0, "bottom": 0, "left": 0}, "gap": 0, "direction": "vertical", "wrap": false, "alignment": {"main": "start", "cross": "start"}}, "style": {}, "componentReference": "6d6e57fb-4a0a-8065-8008-c0fc685ca781", "svgSha256": "f2e1fd30e6eadb8d5636f5037cf477f38ef81b235757d3ed290b92b2c002fec1"}]}, {"roleId": "slot-cell.slot.label", "width": 28, "height": 32, "children": [{"id": "slot-label", "name": "slot-label", "type": "Text", "layout": {"width": {"mode": "fixed", "value": 28}, "height": {"mode": "fixed", "value": 22}, "padding": {"top": 0, "right": 0, "bottom": 0, "left": 0}, "gap": 0, "direction": "vertical", "wrap": false, "alignment": {"main": "start", "cross": "start"}}, "style": {"typographyToken": {"fontFamily": "Noto Sans SC", "fontSize": 14, "fontWeight": 400, "lineHeight": 22, "letterSpacing": 0}, "colorToken": "#20252b"}, "text": "姓名", "fontBinding": {"fontId": "gfont-noto-sans-sc", "fontVariantId": "regular", "family": "Noto Sans SC", "weight": 400, "style": "normal"}}]}, {"roleId": "slot-cell.slot.control", "width": 240, "height": 32, "children": [{"id": "slot-control", "name": "slot-control", "type": "ComponentInstance", "layout": {"width": {"mode": "fixed", "value": 240}, "height": {"mode": "fixed", "value": 32}, "padding": {"top": 0, "right": 0, "bottom": 0, "left": 0}, "gap": 0, "direction": "vertical", "wrap": false, "alignment": {"main": "start", "cross": "start"}}, "style": {}, "componentReference": "b17404b9-592b-8074-8008-c0cd36551084", "fidelityReportSha256": "095db86f0fd809bcd410dc49eb9a3ec9d05cae7162bc27e38fc47cde7decdab3"}]}, {"roleId": "slot-cell.slot.trailing-icon", "width": 24, "height": 32, "children": [{"id": "slot-trailing", "name": "slot-trailing", "type": "IconInstance", "layout": {"width": {"mode": "fixed", "value": 24}, "height": {"mode": "fixed", "value": 24}, "padding": {"top": 0, "right": 0, "bottom": 0, "left": 0}, "gap": 0, "direction": "vertical", "wrap": false, "alignment": {"main": "start", "cross": "start"}}, "style": {}, "componentReference": "6d6e57fb-4a0a-8065-8008-c0fc6866e456", "svgSha256": "ad83ac7dc9d4c6af651a53068e928d82f9402cfd05a924742388549846032f43"}]}, {"roleId": "slot-cell.slot.content", "width": 56, "height": 32, "children": [{"id": "slot-content", "name": "slot-content", "type": "Text", "layout": {"width": {"mode": "fixed", "value": 56}, "height": {"mode": "fixed", "value": 22}, "padding": {"top": 0, "right": 0, "bottom": 0, "left": 0}, "gap": 0, "direction": "vertical", "wrap": false, "alignment": {"main": "start", "cross": "start"}}, "style": {"typographyToken": {"fontFamily": "Noto Sans SC", "fontSize": 14, "fontWeight": 400, "lineHeight": 22, "letterSpacing": 0}, "colorToken": "#20252b"}, "text": "用户列表", "fontBinding": {"fontId": "gfont-noto-sans-sc", "fontVariantId": "regular", "family": "Noto Sans SC", "weight": 400, "style": "normal"}}]}, {"roleId": "slot-cell.slot.actions", "width": 60, "height": 32, "children": [{"id": "slot-action", "name": "slot-action", "type": "ComponentInstance", "layout": {"width": {"mode": "fixed", "value": 60}, "height": {"mode": "fixed", "value": 32}, "padding": {"top": 0, "right": 0, "bottom": 0, "left": 0}, "gap": 0, "direction": "vertical", "wrap": false, "alignment": {"main": "start", "cross": "start"}}, "style": {}, "componentReference": "10f3de97-3a09-806f-8008-c0aff4ac5af0", "fidelityReportSha256": "f5f768a7041c2302f10efaf2360ebce52f99031898fba81fd6e99827847e6c11"}]}]};let slotsExecution=null,slotsBefore=null,slotsFilled=false;
penpot.ui.onMessage(async message=>{
      if(!['slots-baseline','slots-before','slots-fill','slots-after'].includes(message?.type))return;
      try{let result;
        if(message.type==='slots-baseline'){
          if(slotsExecution)throw new Error('slots_baseline_already_exists');
          result=slotsExecution=await executePenpotAdapter(penpot,slotsPayload);
        }else{
          if(slotsExecution?.status!=='EXECUTED')throw new Error('slots_baseline_required');
          if(message.type==='slots-before')result=slotsBefore=await capturePenpotSectionPatch(penpot,slotsExecution);
          else if(message.type==='slots-fill'){
            if(slotsFilled||!slotsBefore)throw new Error('slots_before_required');slotsFilled=true;
            result=await fillPenpotCellSlots(penpot,slotsExecution,slotsRequest,slotsBefore);
          }else result=await capturePenpotSectionPatch(penpot,slotsExecution);
        }
        penpot.ui.sendMessage({type:'task010-result',status:'CAPTURED',result});
      }catch(error){penpot.ui.sendMessage({type:'task010-result',status:'FAIL',error:String(error)});}
    });