import {readFile, writeFile, mkdir, readdir} from 'node:fs/promises';
import {join, resolve} from 'node:path';
import {extractRuntime} from './extract.mjs';
import {ROOT, hash} from '../source-reader/source-lock.mjs';

const output = resolve(process.argv[2] ?? join(ROOT, 'artifacts/task-063/radio-source'));
if ((await readdir(output).catch(error => {if (error.code === 'ENOENT') return []; throw error;})).length) {
  throw new Error('radio_source_requires_new_output');
}
await mkdir(output, {recursive: true});
let observation;
await extractRuntime(output, {
  casesPath: join(ROOT, 'component-builder/runtime-renderer/radio-cases.json'),
  harnessPath: join(ROOT, 'component-builder/runtime-renderer/radio-harness.js'),
  observePage: async (page, context) => {
    const metrics = await page.evaluate(() => {
      const root = document.querySelector('[data-runtime-case="form.radio.default.enabled"] > :first-child');
      const radio = root.querySelector('.ivu-radio');
      const inner = root.querySelector('.ivu-radio-inner');
      const input = root.querySelector('input[type="radio"]');
      const text = [...root.childNodes].find(node => node.nodeType === Node.TEXT_NODE && node.textContent.includes('启用'));
      if (!text) throw new Error('radio_label_text_missing');
      const range = document.createRange();
      range.selectNodeContents(text);
      const bounds = node => {
        const b = node.getBoundingClientRect();
        return {x: b.x, y: b.y, width: b.width, height: b.height};
      };
      const rect = range.getBoundingClientRect();
      const pick = node => {
        const s = getComputedStyle(node);
        return {display: s.display, width: s.width, height: s.height, color: s.color,
          backgroundColor: s.backgroundColor, border: s.border, borderRadius: s.borderRadius,
          fontFamily: s.fontFamily, fontSize: s.fontSize, lineHeight: s.lineHeight};
      };
      const after = getComputedStyle(inner, '::after');
      return {classes: [...root.classList], text: root.textContent, checked: input.checked,
        disabled: input.disabled, root: bounds(root), radio: bounds(radio), inner: bounds(inner),
        label: {x: rect.x, y: rect.y, width: rect.width, height: rect.height},
        rootStyle: pick(root), innerStyle: pick(inner),
        markStyle: {content: after.content, width: after.width, height: after.height,
          left: after.left, top: after.top, borderRadius: after.borderRadius,
          backgroundColor: after.backgroundColor, opacity: after.opacity, transform: after.transform}};
    });
    const cdp = await page.context().newCDPSession(page);
    await cdp.send('DOM.enable');
    await cdp.send('CSS.enable');
    const {root} = await cdp.send('DOM.getDocument');
    const {nodeId} = await cdp.send('DOM.querySelector', {nodeId: root.nodeId,
      selector: '[data-runtime-case="form.radio.default.enabled"] > .ivu-radio-wrapper'});
    const {fonts} = await cdp.send('CSS.getPlatformFontsForNode', {nodeId});
    await cdp.detach();
    observation = {scope: 'official_radio_runtime_source', status: 'PASS',
      candidateOnly: true, fidelityGate: 'NOT_RUN', ...context, metrics, fonts};
  }
});
observation.sourceFiles = Object.fromEntries(await Promise.all([
  'node_modules/view-ui-plus/src/components/radio/radio.vue',
  'node_modules/view-ui-plus/src/styles/components/radio.less'
].map(async path => [path, hash(await readFile(join(ROOT, path)))])));
observation.referenceComponentIrSha256 = hash(await readFile(join(output, 'component_ir.json')));
await writeFile(join(output, 'radio-observation.json'), JSON.stringify(observation, null, 2) + '\n');
console.log(JSON.stringify({status: observation.status, metrics: observation.metrics, fonts: observation.fonts}));
