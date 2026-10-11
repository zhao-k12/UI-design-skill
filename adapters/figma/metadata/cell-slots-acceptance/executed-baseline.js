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


return await executeFigmaAdapter(figma,{"adapterVersion":"0.1.0","documentId":"task015-six-cell-slots","uiIrSha256":"a414f564c5d05dab3045ce62bd9e224597b2715885d01ab3b3b1bbec6ccafaaa","tokensSha256":"c45fc025aa3293a675933e377ccdfc90c60204f990ff90402fcb5ebc00178c2f","componentsSha256":"028aa6a9f330e3199fef0fa331111229648ca8299f78d376df70e93a5b0ec369","iconsSha256":"642072b677f35e538592cca05b02b2f37ca5770d08f602fd8953754cd217ebde","fileReference":"0vGWSRoLxBiVPXiZ8xJAX9","page":{"id":"slot-page","name":"六类槽位验收","type":"Page","layout":{"width":{"mode":"fixed","value":1440},"height":{"mode":"fixed","value":80},"padding":{"top":24,"right":24,"bottom":24,"left":24},"gap":0,"direction":"vertical","wrap":false,"alignment":{"main":"start","cross":"start"}},"style":{"fill":"#f4f5f7"},"children":[{"id":"slot-cell","name":"slot-cell","type":"Frame","layout":{"width":{"mode":"fixed","value":1392},"height":{"mode":"fixed","value":32},"padding":{"top":0,"right":0,"bottom":0,"left":0},"gap":8,"direction":"horizontal","wrap":false,"alignment":{"main":"start","cross":"start"}},"style":{},"children":[{"id":"slot-cell.slot.leading-icon","name":"slot-cell.slot.leading-icon","type":"Frame","layout":{"width":{"mode":"fixed","value":24},"height":{"mode":"fixed","value":32},"padding":{"top":0,"right":0,"bottom":0,"left":0},"gap":8,"direction":"horizontal","wrap":false,"alignment":{"main":"start","cross":"center"}},"style":{},"children":[]},{"id":"slot-cell.slot.label","name":"slot-cell.slot.label","type":"Frame","layout":{"width":{"mode":"fixed","value":28},"height":{"mode":"fixed","value":32},"padding":{"top":0,"right":0,"bottom":0,"left":0},"gap":8,"direction":"horizontal","wrap":false,"alignment":{"main":"start","cross":"center"}},"style":{},"children":[]},{"id":"slot-cell.slot.control","name":"slot-cell.slot.control","type":"Frame","layout":{"width":{"mode":"fixed","value":240},"height":{"mode":"fixed","value":32},"padding":{"top":0,"right":0,"bottom":0,"left":0},"gap":8,"direction":"horizontal","wrap":false,"alignment":{"main":"start","cross":"center"}},"style":{},"children":[]},{"id":"slot-cell.slot.trailing-icon","name":"slot-cell.slot.trailing-icon","type":"Frame","layout":{"width":{"mode":"fixed","value":24},"height":{"mode":"fixed","value":32},"padding":{"top":0,"right":0,"bottom":0,"left":0},"gap":8,"direction":"horizontal","wrap":false,"alignment":{"main":"start","cross":"center"}},"style":{},"children":[]},{"id":"slot-cell.slot.content","name":"slot-cell.slot.content","type":"Frame","layout":{"width":{"mode":"fixed","value":56},"height":{"mode":"fixed","value":32},"padding":{"top":0,"right":0,"bottom":0,"left":0},"gap":8,"direction":"horizontal","wrap":false,"alignment":{"main":"start","cross":"center"}},"style":{},"children":[]},{"id":"slot-cell.slot.actions","name":"slot-cell.slot.actions","type":"Frame","layout":{"width":{"mode":"fixed","value":60},"height":{"mode":"fixed","value":32},"padding":{"top":0,"right":0,"bottom":0,"left":0},"gap":8,"direction":"horizontal","wrap":false,"alignment":{"main":"start","cross":"center"}},"style":{},"children":[]}]}]},"pageReference":"35:2"});
