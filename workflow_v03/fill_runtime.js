// Fill prototype text only after the separate default-component page was read back.
async function fillPrototypeContent(api, payload) {
  if (api.editorType !== 'figma') throw new Error('design_mode_required');
  if (api.fileKey && api.fileKey !== payload.fileReference) throw new Error('file_reference_mismatch');
  const page = await api.getNodeByIdAsync(payload.pageReference);
  if (!page || page.type !== 'PAGE') throw new Error('missing_default_component_page');
  const checked = [];
  for (const target of payload.targets) {
    const id = payload.nodeMap[target.uiIrId];
    if (!id) throw new Error('missing_text_mapping: ' + target.uiIrId);
    const node = await api.getNodeByIdAsync(id);
    let owner = node;
    while (owner && owner !== page) {
      if (owner.type === 'INSTANCE') throw new Error('instance_internals_cannot_be_filled');
      owner = owner.parent;
    }
    if (!node || node.type !== 'TEXT' || node.characters !== target.expectedDefault ||
        owner !== page) throw new Error('default_text_drift: ' + target.uiIrId);
    checked.push({node,target});
  }
  if (new Set(checked.map(row => row.node.id)).size !== checked.length)
    throw new Error('duplicate_text_target');
  const fonts = new Map();
  for (const {node} of checked) fonts.set(JSON.stringify(node.fontName),node.fontName);
  for (const font of fonts.values()) await api.loadFontAsync(font);
  for (const {node,target} of checked) node.characters = target.text;
  return {status:'EXECUTED',stage:'prototype-content-fill',pageReference:page.id,
          mutatedNodeIds:checked.map(row => row.node.id),
          expectedTexts:checked.map(({node,target}) => ({nodeId:node.id,uiIrId:target.uiIrId,text:target.text})),
          finalAcceptance:'NOT_RUN'};
}
