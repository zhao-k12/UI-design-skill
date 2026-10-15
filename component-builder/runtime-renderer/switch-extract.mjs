import {readFile, writeFile, mkdir, readdir} from 'node:fs/promises';
import {join, resolve} from 'node:path';
import {extractRuntime} from './extract.mjs';
import {ROOT, hash} from '../source-reader/source-lock.mjs';

const output = resolve(process.argv[2] ?? join(ROOT, 'artifacts/task-067/switch-source'));
if ((await readdir(output).catch(error => {if (error.code === 'ENOENT') return []; throw error;})).length) {
  throw new Error('switch_source_requires_new_output');
}
await mkdir(output, {recursive: true});
let observation;
await extractRuntime(output, {
  casesPath: join(ROOT, 'component-builder/runtime-renderer/switch-cases.json'),
  harnessPath: join(ROOT, 'component-builder/runtime-renderer/switch-harness.js'),
  observePage: async (page, context) => {
    const metrics = await page.evaluate(() => {
      const root = document.querySelector('[data-runtime-case="form.switch.default.enabled"] > :first-child');
      const inner = root.querySelector('.ivu-switch-inner');
      const input = root.querySelector('input[type="hidden"]');
      const bounds = node => {
        const b = node.getBoundingClientRect();
        return {x: b.x, y: b.y, width: b.width, height: b.height};
      };
      const pick = node => {
        const s = getComputedStyle(node);
        return {display: s.display, width: s.width, height: s.height, color: s.color,
          backgroundColor: s.backgroundColor, border: s.border, borderRadius: s.borderRadius,
          fontFamily: s.fontFamily, fontSize: s.fontSize, lineHeight: s.lineHeight,
          left: s.left, top: s.top};
      };
      const knob = getComputedStyle(root, '::after');
      return {classes: [...root.classList], text: inner.textContent, value: input.value,
        root: bounds(root), inner: bounds(inner), rootStyle: pick(root), innerStyle: pick(inner),
        knobStyle: {content: knob.content, width: knob.width, height: knob.height,
          left: knob.left, top: knob.top, borderRadius: knob.borderRadius,
          backgroundColor: knob.backgroundColor}};
    });
    const cdp = await page.context().newCDPSession(page);
    await cdp.send('DOM.enable');
    await cdp.send('CSS.enable');
    const {root} = await cdp.send('DOM.getDocument');
    const {nodeId} = await cdp.send('DOM.querySelector', {nodeId: root.nodeId,
      selector: '[data-runtime-case="form.switch.default.enabled"] .ivu-switch-inner'});
    const {fonts} = await cdp.send('CSS.getPlatformFontsForNode', {nodeId});
    await cdp.detach();
    observation = {scope: 'official_switch_runtime_source', status: 'PASS',
      candidateOnly: true, fidelityGate: 'NOT_RUN', ...context, metrics, fonts};
  }
});
observation.sourceFiles = Object.fromEntries(await Promise.all([
  'node_modules/view-ui-plus/src/components/switch/switch.vue',
  'node_modules/view-ui-plus/src/styles/components/switch.less'
].map(async path => [path, hash(await readFile(join(ROOT, path)))])));
observation.referenceComponentIrSha256 = hash(await readFile(join(output, 'component_ir.json')));
await writeFile(join(output, 'switch-observation.json'), JSON.stringify(observation, null, 2) + '\n');
console.log(JSON.stringify({status: observation.status, metrics: observation.metrics, fonts: observation.fonts}));
