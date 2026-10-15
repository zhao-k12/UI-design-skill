import {readFile, writeFile} from 'node:fs/promises';
import {join} from 'node:path';
import {pathToFileURL} from 'node:url';
import {resolve} from 'node:path';
import {ROOT, hash} from '../component-builder/source-reader/source-lock.mjs';
import {extractRuntime} from '../component-builder/runtime-renderer/extract.mjs';

const output = join(ROOT, 'artifacts/task-070/card-source');
const fixture = join(ROOT, 'component-builder/runtime-renderer/card-cases.json');
const harness = join(ROOT, 'component-builder/runtime-renderer/card-harness.js');
const sourceFiles = [
  'node_modules/view-ui-plus/src/components/card/card.vue',
  'node_modules/view-ui-plus/src/styles/components/card.less'
];

export async function run() {
  let observed;
  await extractRuntime(output, {casesPath: fixture, harnessPath: harness,
    observePage: async (page, context) => {
      const metrics = await page.locator('[data-runtime-case="content.card.default.user-info"] > :first-child').evaluate(root => {
        const head = root.querySelector('.ivu-card-head');
        const body = root.querySelector('.ivu-card-body');
        const bounds = el => {const r = el.getBoundingClientRect(); return {x:r.x,y:r.y,width:r.width,height:r.height};};
        const style = el => {const s = getComputedStyle(el); return {color:s.color,backgroundColor:s.backgroundColor,
          border:s.border,borderRadius:s.borderRadius,fontFamily:s.fontFamily,fontSize:s.fontSize,
          lineHeight:s.lineHeight,padding:s.padding,boxShadow:s.boxShadow};};
        return {classes:[...root.classList],root:bounds(root),head:bounds(head),body:bounds(body),
          rootStyle:style(root),headStyle:style(head),bodyStyle:style(body),
          titleText:head.textContent.trim(),bodyText:body.textContent.trim()};
      });
      observed = {scope:'official_card_runtime_source',status:'PASS',candidateOnly:true,
        fidelityGate:'NOT_RUN',cases:context.cases,environment:context.environment,
        provenance:context.provenance,metrics,
        sourceFiles:Object.fromEntries(await Promise.all(sourceFiles.map(async file =>
          [file,hash(await readFile(join(ROOT,file)))])))};
    }});
  const ir = await readFile(join(output,'component_ir.json'));
  observed.referenceComponentIrSha256 = hash(ir);
  await writeFile(join(output,'card-observation.json'),JSON.stringify(observed,null,2)+'\n');
  return {status:observed.status,metrics:observed.metrics};
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href)
  console.log(JSON.stringify(await run(),null,2));
