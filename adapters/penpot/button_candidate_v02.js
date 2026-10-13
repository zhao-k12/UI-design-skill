// Replay recipe for a fresh Penpot acceptance file. The live TASK-028 receipt
// records the actual native IDs and the line-height/path corrections.
async function createDefaultFontButtonCandidate(penpot, penpotUtils, fileId) {
  if (penpot.currentFile?.id !== fileId) throw new Error('candidate_foreign_file');
  const pageName = 'V0.2 / Default-font Button candidate';
  if (penpotUtils.getPages().some(page => page.name === pageName)) throw new Error('candidate_page_exists');
  const font = penpot.fonts.findById('sourcesanspro');
  const regular = font?.variants.find(variant => variant.fontVariantId === 'regular' && variant.fontWeight === '400');
  if (!regular) throw new Error('native_default_font_unavailable');

  const page = penpot.createPage();
  page.name = pageName;
  await penpot.openPage(page);
  const library = penpot.library.local;
  const blue = library.createColor();
  blue.name = 'V0.2/Button/Primary'; blue.color = '#2D8CF0'; blue.opacity = 1;
  const white = library.createColor();
  white.name = 'V0.2/Button/On Primary'; white.color = '#FFFFFF'; white.opacity = 1;
  const typography = library.createTypography();
  typography.name = 'V0.2/Button/Label';
  typography.setFont(font, regular);
  typography.fontSize = '14'; typography.lineHeight = '1.5'; typography.letterSpacing = '0';

  const main = penpot.createBoard();
  main.name = 'V0.2/Button/Primary/Medium/Default';
  main.x = 800; main.y = 80; main.resize(60, 32);
  main.fills = [blue.asFill()];
  main.strokes = [{...blue.asStroke(), strokeWidth: 1, strokeAlignment: 'inner', strokeStyle: 'solid'}];
  main.borderRadius = 4;
  const flex = main.addFlexLayout();
  flex.dir = 'row'; flex.alignItems = 'center'; flex.justifyContent = 'center';
  flex.leftPadding = 15; flex.rightPadding = 15; flex.topPadding = 0; flex.bottomPadding = 0;
  flex.horizontalSizing = 'fix'; flex.verticalSizing = 'fix';

  const label = penpot.createText('查询');
  if (!label) throw new Error('candidate_text_creation_failed');
  const defaultFont = {fontId: label.fontId, fontFamily: label.fontFamily,
    fontVariantId: label.fontVariantId, fontWeight: label.fontWeight};
  if (defaultFont.fontId !== 'sourcesanspro' || defaultFont.fontVariantId !== 'regular')
    throw new Error('candidate_default_font_changed');
  label.name = 'label'; label.applyTypography(typography);
  // The observed Penpot API kept 1.2 after applyTypography; set the text itself.
  label.lineHeight = '1.5'; label.growType = 'auto-width'; label.fills = [white.asFill()];
  main.appendChild(label);

  const component = library.createComponent([main]);
  if (!component) throw new Error('candidate_component_creation_failed');
  component.path = 'V0.2/Button/Primary/Medium'; component.name = 'Default';
  component.mainInstance().name = 'V0.2/Button/Primary/Medium/Default';
  const review = penpot.createBoard();
  review.name = 'V0.2 Button candidate review';
  review.x = 80; review.y = 80; review.resize(400, 160);
  review.fills = [{fillColor: '#FFFFFF', fillOpacity: 1}];
  const instance = component.instance();
  review.appendChild(instance); penpotUtils.setParentXY(instance, 60, 64);
  if (penpot.currentFile.validate().length) throw new Error('candidate_native_file_invalid');
  return {scope: 'v02-penpot-button-candidate-creation', status: 'CANDIDATE',
    fileId, pageId: page.id, componentId: component.id, mainId: component.mainInstance().id,
    instanceId: instance.id, reviewId: review.id, labelId: label.id, defaultFont,
    nativeAdmission: 'NOT_RUN', releaseReady: false};
}
