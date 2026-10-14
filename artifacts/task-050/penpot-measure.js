// Execute with mcp__penpot__execute_code in file 57949053-620f-8001-8008-c804c8d61529.
// Keep this page separate from the accepted component and adapter pages.
const specs = [
  ['title', '用户管理', 20, 28],
  ['label.name', '姓名', 14, 22],
  ['label.status', '状态', 14, 22],
  ['label.summary', '范围', 14, 22],
  ['filter.description', '查看用户信息', 14, 22],
  ['label.action', '操作', 14, 22],
  ['list.title', '用户列表', 14, 22],
  ['list.export.label', '导出', 14, 22],
  ['column.name.label', '姓名', 14, 22],
  ['column.status.label', '状态', 14, 22],
  ['column.role.label', '角色', 14, 22],
  ['list.count', '共 3 位用户', 14, 22],
];
const expectedFileId = '57949053-620f-8001-8008-c804c8d61529';
if (penpot.currentFile?.id !== expectedFileId) throw new Error('wrong_penpot_file');
const font = penpot.fonts.findById('sourcesanspro');
const variant = font?.variants.find(v => v.fontVariantId === 'regular');
if (!font || !variant || Number(variant.fontWeight) !== 400) throw new Error('font_binding_unavailable');
const pageName = 'V0.2 / Default-font text measurements';
let page = penpot.currentFile.pages.find(p => p.name === pageName);
if (!page) {
  page = penpot.createPage();
  page.name = pageName;
}
await penpot.openPage(page);
const rows = [];
for (let i = 0; i < specs.length; i++) {
  const [key, characters, fontSize, lineHeight] = specs[i];
  let n = page.root.children.find(child => child.name === key);
  if (!n) {
    n = penpot.createText(characters);
    n.name = key;
    page.root.appendChild(n);
  }
  font.applyToText(n, variant);
  n.characters = characters;
  n.fontSize = String(fontSize);
  n.lineHeight = String(lineHeight / fontSize);
  n.letterSpacing = '0';
  n.growType = 'auto-width';
  n.x = 100;
  n.y = i * 56;
  rows.push({uiIrId: key, nodeId: n.id, characters: n.characters, width: n.width,
    height: n.height, textBounds: n.textBounds, fontId: n.fontId,
    fontVariantId: n.fontVariantId, fontSize: n.fontSize, lineHeight: n.lineHeight});
}
return {fileId: penpot.currentFile.id, pageId: page.id, pageName, rows};
