import {readFile, writeFile, mkdir, readdir} from 'node:fs/promises';
import {join, resolve} from 'node:path';
import {extractRuntime} from './extract.mjs';
import {ROOT, hash} from '../source-reader/source-lock.mjs';

const output = resolve(process.argv[2] ?? join(ROOT, 'artifacts/task-054/tag-source'));
if ((await readdir(output).catch(error => {if (error.code === 'ENOENT') return []; throw error;})).length) {
  throw new Error('tag_source_requires_new_output');
}
await mkdir(output, {recursive: true});
let observation;
await extractRuntime(output, {
  casesPath: join(ROOT, 'component-builder/runtime-renderer/tag-cases.json'),
  harnessPath: join(ROOT, 'component-builder/runtime-renderer/tag-harness.js'),
  observePage: async (page, context) => {
    const metrics = await page.evaluate(() => {
      const root = document.querySelector('[data-runtime-case="data.tag.default.enabled"] > :first-child');
      const label = root.querySelector('.ivu-tag-text');
      const bounds = node => {
        const b = node.getBoundingClientRect();
        return {x: b.x, y: b.y, width: b.width, height: b.height};
      };
      const style = getComputedStyle(root);
      const textStyle = getComputedStyle(label);
      return {
        classes: [...root.classList], text: label.textContent,
        root: bounds(root), label: bounds(label),
        rootStyle: {height: style.height, lineHeight: style.lineHeight, padding: style.padding,
          margin: style.margin, border: style.border, borderRadius: style.borderRadius,
          backgroundColor: style.backgroundColor},
        textStyle: {fontFamily: textStyle.fontFamily, fontSize: textStyle.fontSize,
          fontWeight: textStyle.fontWeight, color: textStyle.color}
      };
    });
    const cdp = await page.context().newCDPSession(page);
    await cdp.send('DOM.enable');
    await cdp.send('CSS.enable');
    const {root} = await cdp.send('DOM.getDocument');
    const {nodeId} = await cdp.send('DOM.querySelector', {nodeId: root.nodeId,
      selector: '[data-runtime-case="data.tag.default.enabled"] .ivu-tag-text'});
    const {fonts} = await cdp.send('CSS.getPlatformFontsForNode', {nodeId});
    await cdp.detach();
    observation = {scope: 'official_tag_runtime_source', status: 'PASS',
      candidateOnly: true, fidelityGate: 'NOT_RUN', ...context, metrics, fonts};
  }
});
observation.sourceFiles = Object.fromEntries(await Promise.all([
  'node_modules/view-ui-plus/src/components/tag/tag.vue',
  'node_modules/view-ui-plus/src/styles/components/tag.less'
].map(async path => [path, hash(await readFile(join(ROOT, path)))])));
observation.referenceComponentIrSha256 = hash(await readFile(join(output, 'component_ir.json')));
await writeFile(join(output, 'tag-observation.json'), JSON.stringify(observation, null, 2) + '\n');
console.log(JSON.stringify({status: observation.status, metrics: observation.metrics, fonts: observation.fonts}));
