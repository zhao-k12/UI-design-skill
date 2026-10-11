// Executed inside the browser. No component dimensions or visual values are inferred.
export function captureComponent(logicalId) {
  const wrapper = [...document.querySelectorAll('[data-runtime-case]')].find(element => element.dataset.runtimeCase === logicalId);
  const root = wrapper?.firstElementChild;
  if (!root) throw new Error('missing_runtime_component: ' + logicalId);
  const origin = root.getBoundingClientRect();
  const properties = ['display', 'position', 'box-sizing', 'width', 'height', 'min-width', 'min-height', 'max-width', 'max-height',
    'padding-top', 'padding-right', 'padding-bottom', 'padding-left', 'margin-top', 'margin-right', 'margin-bottom', 'margin-left',
    'gap', 'row-gap', 'column-gap', 'align-items', 'justify-content', 'vertical-align', 'flex-direction', 'flex-wrap',
    'background-color', 'color', 'opacity', 'visibility', 'border-top-width', 'border-right-width', 'border-bottom-width', 'border-left-width',
    'border-top-style', 'border-right-style', 'border-bottom-style', 'border-left-style', 'border-top-color', 'border-right-color', 'border-bottom-color', 'border-left-color',
    'border-top-left-radius', 'border-top-right-radius', 'border-bottom-left-radius', 'border-bottom-right-radius',
    'font-family', 'font-size', 'font-weight', 'font-style', 'line-height', 'letter-spacing', 'text-align', 'text-transform', 'box-shadow', 'transform', 'content'];
  const rect = box => ({ x: box.x - origin.x, y: box.y - origin.y, width: box.width, height: box.height });
  const style = declaration => Object.fromEntries(properties.map(property => [property, declaration.getPropertyValue(property)]));
  const nodes = [], iconMetrics = [];
  function visit(element, path, parentVisible) {
    const computed = getComputedStyle(element);
    const box = element.getBoundingClientRect();
    const visible = parentVisible && computed.display !== 'none' && computed.visibility !== 'hidden' && Number(computed.opacity) > 0 && box.width > 0 && box.height > 0;
    const pseudoElements = {};
    for (const pseudo of ['::before', '::after', '::placeholder']) {
      const declaration = getComputedStyle(element, pseudo);
      if (pseudo === '::placeholder' && element.tagName !== 'INPUT') continue;
      if (pseudo !== '::placeholder' && ['none', 'normal', ''].includes(declaration.content)) continue;
      pseudoElements[pseudo] = style(declaration);
    }
    const textRuns = [];
    for (const child of element.childNodes) {
      if (child.nodeType === Node.TEXT_NODE && child.textContent.trim()) {
        const range = document.createRange();
        range.selectNodeContents(child);
        textRuns.push({ text: child.textContent, bounds: rect(range.getBoundingClientRect()) });
      }
    }
    nodes.push({ path, parentPath: path === '0' ? null : path.slice(0, path.lastIndexOf('.')), tag: element.tagName.toLowerCase(),
      attributes: Object.fromEntries([...element.attributes].map(attribute => [attribute.name, attribute.value])),
      bounds: rect(box), visible, computedStyle: style(computed), pseudoElements, textRuns,
      value: element instanceof HTMLInputElement ? element.value : null });
    if (element.matches('i.ivu-icon, svg, img')) iconMetrics.push({ path, visible, bounds: rect(box), tag: element.tagName.toLowerCase(), pseudoElements });
    [...element.children].forEach((child, index) => visit(child, `${path}.${index}`, visible));
  }
  visit(root, '0', true);
  return { rootBounds: { width: origin.width, height: origin.height }, nodes, iconMetrics };
}
