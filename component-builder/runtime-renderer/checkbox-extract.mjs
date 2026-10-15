import {readFile, writeFile, mkdir, readdir} from 'node:fs/promises';
import {join, resolve} from 'node:path';
import {extractRuntime} from './extract.mjs';
import {ROOT, hash} from '../source-reader/source-lock.mjs';

const output = resolve(process.argv[2] ?? join(ROOT, 'artifacts/task-058/checkbox-source'));
if ((await readdir(output).catch(error => {if (error.code === 'ENOENT') return []; throw error;})).length) {
  throw new Error('checkbox_source_requires_new_output');
}
await mkdir(output, {recursive: true});
let observation;
await extractRuntime(output, {
  casesPath: join(ROOT, 'component-builder/runtime-renderer/checkbox-cases.json'),
  harnessPath: join(ROOT, 'component-builder/runtime-renderer/checkbox-harness.js'),
  observePage: async (page, context) => {
    const metrics = await page.evaluate(() => {
      const root = document.querySelector('[data-runtime-case="form.checkbox.default.enabled"] > :first-child');
      const box = root.querySelector('.ivu-checkbox');
      const inner = root.querySelector('.ivu-checkbox-inner');
      const label = root.querySelector('.ivu-checkbox-label-text');
      const input = root.querySelector('input[type="checkbox"]');
      const bounds = node => {
        const b = node.getBoundingClientRect();
        return {x: b.x, y: b.y, width: b.width, height: b.height};
      };
      const pick = node => {
        const s = getComputedStyle(node);
        return {display: s.display, width: s.width, height: s.height, color: s.color,
          backgroundColor: s.backgroundColor, border: s.border, borderRadius: s.borderRadius,
          fontFamily: s.fontFamily, fontSize: s.fontSize, lineHeight: s.lineHeight};
      };
      return {classes: [...root.classList], text: label.textContent, checked: input.checked,
        disabled: input.disabled, root: bounds(root), box: bounds(box), inner: bounds(inner),
        label: bounds(label), rootStyle: pick(root), innerStyle: pick(inner), labelStyle: pick(label),
        checkmarkStyle: {content: getComputedStyle(inner, '::after').content,
          border: getComputedStyle(inner, '::after').border,
          transform: getComputedStyle(inner, '::after').transform}};
    });
    const cdp = await page.context().newCDPSession(page);
    await cdp.send('DOM.enable');
    await cdp.send('CSS.enable');
    const {root} = await cdp.send('DOM.getDocument');
    const {nodeId} = await cdp.send('DOM.querySelector', {nodeId: root.nodeId,
      selector: '[data-runtime-case="form.checkbox.default.enabled"] .ivu-checkbox-label-text'});
    const {fonts} = await cdp.send('CSS.getPlatformFontsForNode', {nodeId});
    await cdp.detach();
    observation = {scope: 'official_checkbox_runtime_source', status: 'PASS',
      candidateOnly: true, fidelityGate: 'NOT_RUN', ...context, metrics, fonts};
  }
});
observation.sourceFiles = Object.fromEntries(await Promise.all([
  'node_modules/view-ui-plus/src/components/checkbox/checkbox.vue',
  'node_modules/view-ui-plus/src/styles/components/checkbox.less',
  'node_modules/view-ui-plus/src/styles/mixins/checkbox.less'
].map(async path => [path, hash(await readFile(join(ROOT, path)))])));
observation.referenceComponentIrSha256 = hash(await readFile(join(output, 'component_ir.json')));
await writeFile(join(output, 'checkbox-observation.json'), JSON.stringify(observation, null, 2) + '\n');
console.log(JSON.stringify({status: observation.status, metrics: observation.metrics, fonts: observation.fonts}));
