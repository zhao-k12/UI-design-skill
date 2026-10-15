import {readFile, writeFile} from 'node:fs/promises';
import {join, resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {ROOT, hash} from '../component-builder/source-reader/source-lock.mjs';
import {extractRuntime} from '../component-builder/runtime-renderer/extract.mjs';

const output = join(ROOT, 'artifacts/task-076/tabs-source');
const fixture = join(ROOT, 'component-builder/runtime-renderer/tabs-cases.json');
const harness = join(ROOT, 'component-builder/runtime-renderer/tabs-harness.js');
const sourceFiles = [
  'node_modules/view-ui-plus/src/components/tabs/tabs.vue',
  'node_modules/view-ui-plus/src/components/tabs/pane.vue',
  'node_modules/view-ui-plus/src/styles/components/tabs.less'
];

export async function run() {
  let observed;
  await extractRuntime(output, {casesPath: fixture, harnessPath: harness,
    observePage: async (page, context) => {
      const metrics = await page.locator('[data-runtime-case="navigation.tabs.line.overview"] > :first-child').evaluate(root => {
        const bounds = el => {const r=el.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height};};
        const style = el => {const s=getComputedStyle(el);return {color:s.color,backgroundColor:s.backgroundColor,
          border:s.border,borderRadius:s.borderRadius,fontFamily:s.fontFamily,fontSize:s.fontSize,
          lineHeight:s.lineHeight,padding:s.padding,margin:s.margin};};
        const bar=root.querySelector('.ivu-tabs-bar');const ink=root.querySelector('.ivu-tabs-ink-bar');
        return {classes:[...root.classList],root:bounds(root),rootStyle:style(root),
          bar:{bounds:bounds(bar),style:style(bar)},ink:{bounds:bounds(ink),style:style(ink)},
          tabs:[...root.querySelectorAll('.ivu-tabs-tab')].map(n=>({text:n.textContent.trim(),
            classes:[...n.classList],bounds:bounds(n),style:style(n)})),
          panes:[...root.querySelectorAll('.ivu-tabs-tabpane')].map(n=>({text:n.textContent.trim(),
            classes:[...n.classList],bounds:bounds(n),style:style(n)}))};
      });
      observed = {scope:'official_tabs_runtime_source',status:'PASS',candidateOnly:true,
        fidelityGate:'NOT_RUN',cases:context.cases,environment:context.environment,
        provenance:context.provenance,metrics,
        sourceFiles:Object.fromEntries(await Promise.all(sourceFiles.map(async file =>
          [file,hash(await readFile(join(ROOT,file)))])))};
    }});
  observed.referenceComponentIrSha256 = hash(await readFile(join(output,'component_ir.json')));
  await writeFile(join(output,'tabs-observation.json'),JSON.stringify(observed,null,2)+'\n');
  return {status:observed.status,metrics:observed.metrics};
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href)
  console.log(JSON.stringify(await run(),null,2));
