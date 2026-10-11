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
