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
    for (const node of app.querySelectorAll('button,input,select,textarea,a,[tabindex]')) {
      node.setAttribute('tabindex', '-1');
      if (node.tagName === 'A') node.removeAttribute('href');
    }
    // Interaction-only property. Official component colors, dimensions,
    // typography, borders and selected appearance remain untouched.
    const frozen = copy.ownerDocument.createElement('style');
    frozen.setAttribute('data-static-interaction-freeze', '');
    frozen.textContent = '[data-static-delivery],[data-static-delivery] *{pointer-events:none!important}';
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
