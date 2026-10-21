// A retained annotation page. It contains colored geometry and labels only.
async function executeAnnotatedSkeleton(api, payload) {
  if (api.editorType !== 'figma') throw new Error('design_mode_required');
  if (api.fileKey && api.fileKey !== payload.fileReference) throw new Error('file_reference_mismatch');
  const name = `${payload.documentId}/彩色组件骨架/${payload.revision}`;
  if (api.root.children.some(page => page.name === name)) throw new Error('skeleton_revision_already_exists');
  const fonts = await api.listAvailableFontsAsync();
  const regular = fonts.find(font => font.fontName.family === 'Inter' && font.fontName.style === 'Regular');
  if (!regular) throw new Error('Inter Regular is unavailable for skeleton labels');
  await api.loadFontAsync(regular.fontName);
  const page = api.createPage(); page.name = name;
  await api.setCurrentPageAsync(page);
  const root = api.createFrame(); root.name = '彩色组件骨架';
  root.resize(payload.box.width, payload.box.height); root.x = 80; root.y = 80;
  root.fills = [{type:'SOLID',color:{r:1,g:1,b:1}}];
  page.appendChild(root);
  const cells = [];
  const color = hex => ({r:parseInt(hex.slice(1,3),16)/255,
                         g:parseInt(hex.slice(3,5),16)/255,
                         b:parseInt(hex.slice(5,7),16)/255});
  for (const cell of payload.cells) {
    const rect = api.createRectangle();
    rect.name = `${cell.componentType} · ${cell.sourceId}`;
    rect.resize(cell.box.width, cell.box.height);
    rect.fills = [{type:'SOLID',color:color(cell.color)}];
    root.appendChild(rect);
    rect.x = cell.box.x - payload.box.x; rect.y = cell.box.y - payload.box.y;
    const label = api.createText(); label.fontName = regular.fontName;
    label.fontSize = 11; label.characters = `${cell.componentType} · ${cell.label}`;
    label.name = `标注/${cell.cellId}`;
    root.appendChild(label);
    label.x = rect.x + 4; label.y = rect.y + 4;
    cells.push({cellId:cell.cellId,sourceId:cell.sourceId,componentType:cell.componentType,
                color:cell.color,box:cell.box,rectangleId:rect.id,labelId:label.id});
  }
  return {status:'EXECUTED',stage:'annotated-skeleton-page',pageReference:page.id,
          rootReference:root.id,revision:payload.revision,cells};
}
