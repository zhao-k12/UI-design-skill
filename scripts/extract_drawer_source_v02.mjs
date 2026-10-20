import {readFile, writeFile} from 'node:fs/promises';
import {join, resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {ROOT, hash} from '../component-builder/source-reader/source-lock.mjs';
import {extractRuntime} from '../component-builder/runtime-renderer/extract.mjs';

const output = join(ROOT, 'artifacts/task-091/drawer-source');
const fixture = join(ROOT, 'component-builder/runtime-renderer/drawer-cases.json');
const harness = join(ROOT, 'component-builder/runtime-renderer/drawer-harness.js');
const sourceFiles = [
  'node_modules/view-ui-plus/src/components/drawer/drawer.vue',
  'node_modules/view-ui-plus/src/styles/components/drawer.less'
];

export async function run() {
  let observed;
  await extractRuntime(output, {casesPath:fixture,harnessPath:harness,
    observePage: async (page, context) => {
      const metrics = await page.locator('.ivu-drawer').evaluate(root => {
        const outer=root.parentElement.parentElement;
        root.setAttribute('data-runtime-case','overlay.drawer.detail.open');
        const bounds=el=>{const r=el.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height};};
        const style=el=>{const s=getComputedStyle(el);return {color:s.color,backgroundColor:s.backgroundColor,
          border:s.border,borderRadius:s.borderRadius,boxShadow:s.boxShadow,
          fontFamily:s.fontFamily,fontSize:s.fontSize,lineHeight:s.lineHeight,
          padding:s.padding,margin:s.margin};};
        const content=root.querySelector('.ivu-drawer-content');
        const header=root.querySelector('.ivu-drawer-header');
        const body=root.querySelector('.ivu-drawer-body');
        return {classes:[...root.classList],root:bounds(root),rootStyle:style(root),
          content:{bounds:bounds(content),style:style(content)},
          header:header?{text:header.textContent.trim(),bounds:bounds(header),style:style(header)}:null,
          body:body?{text:body.textContent.trim(),bounds:bounds(body),style:style(body)}:null,
          closeCount:root.querySelectorAll('.ivu-drawer-close').length,
          maskCount:outer.querySelectorAll('.ivu-drawer-mask').length};
      });
      observed={scope:'official_drawer_runtime_source',status:'PASS',candidateOnly:true,
        fidelityGate:'NOT_RUN',cases:context.cases,environment:context.environment,
        provenance:context.provenance,metrics,
        sourceFiles:Object.fromEntries(await Promise.all(sourceFiles.map(async file=>
          [file,hash(await readFile(join(ROOT,file)))])))};
    }});
  observed.referenceComponentIrSha256=hash(await readFile(join(output,'component_ir.json')));
  await writeFile(join(output,'drawer-observation.json'),JSON.stringify(observed,null,2)+'\n');
  return {status:observed.status,metrics:observed.metrics};
}

if(process.argv[1]&&import.meta.url===pathToFileURL(resolve(process.argv[1])).href)
  console.log(JSON.stringify(await run(),null,2));
