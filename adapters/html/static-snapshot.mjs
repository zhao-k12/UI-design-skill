// Preserve the browser-rendered official component DOM while dropping the
// runtime and review controls from the delivered page.
export async function staticSnapshot(page) {
  return page.evaluate(() => {
    const copy = document.documentElement.cloneNode(true);
    for (const node of copy.querySelectorAll('script,.stage-nav,.demo-switch')) node.remove();
    const originalInputs = [...document.querySelectorAll('input,textarea,select')];
    const copiedInputs = [...copy.querySelectorAll('input,textarea,select')];
    originalInputs.forEach((original, index) => {
      const target = copiedInputs[index];
      if (!target) return;
      if (target.tagName === 'TEXTAREA') target.textContent = original.value;
      else if (target.tagName === 'SELECT') {
        [...target.options].forEach((option, optionIndex) => {
          option.selected = original.options[optionIndex]?.selected ?? false;
        });
      } else {
        target.setAttribute('value', original.value);
        if (original.checked) target.setAttribute('checked', '');
        else target.removeAttribute('checked');
      }
    });
    for (const node of copy.querySelectorAll('*')) {
      for (const attribute of [...node.attributes]) {
        if (/^on[a-z]+$/i.test(attribute.name)) node.removeAttribute(attribute.name);
      }
    }
    const app = copy.querySelector('#app');
    if (!app) throw new Error('static_snapshot_app_missing');
    app.setAttribute('data-static-delivery', '');
    // The live component synchronizes its separate header with JavaScript.
    // A static snapshot has no runtime, so put the main header in the same
    // scroll container as its body; official fixed-column overlays stay put.
    const responsiveFixedRules = [];
    const liveTables=[...document.querySelectorAll('#app .ivu-table')];
    for (const [tableIndex,table] of [...app.querySelectorAll('.ivu-table')].entries()) {
      // Content-fit grid tables already use one outer scroll container.
      if (table.closest('[data-shared-table-scroll="true"]')) continue;
      const header=table.querySelector(':scope > .ivu-table-header');
      const body=table.querySelector(':scope > .ivu-table-body');
      if(header && body) {
        const width = parseFloat(header.querySelector('table')?.style.width);
        const headerHeight=liveTables[tableIndex]?.querySelector(':scope > .ivu-table-header')?.getBoundingClientRect().height||0;
        for(const property of ['height','maxHeight']){
          const value=body.style[property];
          if(value?.endsWith('px'))body.style[property]=`${parseFloat(value)+headerHeight}px`;
        }
        body.prepend(header);
        const wrapper = table.parentElement;
        if (wrapper && Number.isFinite(width) && width > 0) {
          const id = responsiveFixedRules.length;
          wrapper.setAttribute('data-static-table-wrapper', String(id));
          const scope = `[data-static-table-wrapper="${id}"]`;
          responsiveFixedRules.push(`${scope}{container:static-table-${id} / inline-size}${scope} .ivu-table-body>.ivu-table-header,${scope} .ivu-table-body>.ivu-table-header>table,${scope} .ivu-table-body>table{width:100%!important;min-width:${width}px}${scope} .ivu-table-body>.ivu-table-header{position:sticky;top:0;z-index:1}@container static-table-${id} (min-width:${width}px){${scope} .ivu-table-fixed-right{display:none!important}${scope} .ivu-table-body .ivu-table-hidden{visibility:visible!important}}`);
        }
      }
    }
    for (const node of app.querySelectorAll('button,input,select,textarea,a,[tabindex]')) {
      node.setAttribute('tabindex', '-1');
      if (node.tagName === 'A') node.removeAttribute('href');
    }
    // Interaction-only property. Official component colors, dimensions,
    // typography, borders and selected appearance remain untouched.
    const frozen = copy.ownerDocument.createElement('style');
    frozen.setAttribute('data-static-interaction-freeze', '');
    // Freeze hover states throughout the static page, while allowing the
    // table scroll container itself to receive wheel and scrollbar events.
    frozen.textContent = '[data-static-delivery],[data-static-delivery] *{pointer-events:none!important}[data-static-delivery] [data-design-role="page-shell"],[data-static-delivery] .ivu-table,[data-static-delivery] .ivu-table-body,[data-static-delivery] [data-design-role="uploaded-value"][data-hover-preview="true"],[data-static-delivery] [data-design-role="uploaded-value"][data-hover-preview="true"] *{pointer-events:auto!important}[data-static-delivery] .ivu-table-body>.ivu-table-header{overflow:visible;width:max-content}' + responsiveFixedRules.join('');
    copy.querySelector('head').append(frozen);
    return '<!doctype html>\n' + copy.outerHTML;
  });
}

export async function inspectStaticDelivery(page) {
  return page.evaluate(() => {
    const app = document.querySelector('[data-static-delivery]');
    const button = app?.querySelector('button');
    return {
      app: Boolean(app), scripts: document.querySelectorAll('script').length,
      reviewControls: document.querySelectorAll('.stage-nav,.demo-switch').length,
      buttonPointerEvents: button && getComputedStyle(button).pointerEvents,
      buttonTabIndex: button?.tabIndex,
      textLength: app?.innerText.length ?? 0,
    };
  });
}
