// Source-only SVG import, never a visual reconstruction. Native IDs stay in Adapter Metadata.
// Validation adapted from figma-generate-library/scripts/validateCreation.js (async lookups).
async function validateIconCreation(api, checks) {
  const passed = [], failed = [];
  for (const check of checks) {
    const node = await api.getNodeByIdAsync(check.nodeId);
    const reasons = [];
    if (!node) reasons.push('missing native node');
    else {
      if (node.type !== check.expectedType) reasons.push('wrong native type');
      if (node.name !== check.expectedName) reasons.push('wrong native name');
      if (node.width !== 24 || node.height !== 24) reasons.push('wrong official viewBox bounds');
    }
    if (reasons.length) failed.push({nodeId:check.nodeId, reason:reasons.join('; ')});
    else passed.push(check.nodeId);
  }
  return {passed,failed};
}
async function importOfficialIcons(api, payload) {
  const page = await api.getNodeByIdAsync(payload.pageReference);
  if (!page || page.type !== 'PAGE') throw new Error('missing icon library page');
  await api.setCurrentPageAsync(page);
  if (payload.icons.some(icon=>page.findOne(n=>n.name===icon.iconId))) throw new Error('existing_icon_requires_exact_metadata');
  const created = [], masters = [];
  const origin = Math.max(80,...page.children.map(n=>n.x+n.width+80));
  for (const [index,icon] of payload.icons.entries()) {
    const frame = api.createNodeFromSvg(icon.svg);
    const importedIds = [frame.id,...frame.findAll(()=>true).map(n=>n.id)];
    const component = api.createComponentFromNode(frame);
    created.push(...importedIds,component.id);
    component.name = icon.iconId;
    component.description = `Official Remix Icon SVG ${icon.svgSha256}; source ${payload.sourceVersion}`;
    component.x=origin+index*80;component.y=80;
    masters.push({iconId:icon.iconId,componentReference:component.id,svgSha256:icon.svgSha256,
      width:component.width,height:component.height,vectorEvidence:component.findAllWithCriteria({types:['VECTOR']}).map(n=>({
        nodeId:n.id,type:n.type,width:n.width,height:n.height,vectorPaths:n.vectorPaths}))});
  }
  const validation = await validateIconCreation(api,masters.map(m=>({nodeId:m.componentReference,expectedType:'COMPONENT',expectedName:m.iconId})));
  return {scope:'figma_official_svg_components',status:validation.failed.length?'FAIL':'PASS',
    fileReference:payload.fileReference,sourceVersion:payload.sourceVersion,registrySha256:payload.registrySha256,
    pageReference:page.id,createdNodeIds:[...new Set(created)],mutatedNodeIds:[],masters,validation};
}
