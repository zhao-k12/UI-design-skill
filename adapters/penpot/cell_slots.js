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
