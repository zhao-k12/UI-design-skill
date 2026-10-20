import {readFile, writeFile} from 'node:fs/promises';
import {join, resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {ROOT, hash} from '../component-builder/source-reader/source-lock.mjs';
import {extractRuntime} from '../component-builder/runtime-renderer/extract.mjs';

const output = join(ROOT, 'artifacts/task-094/upload-source');
const fixture = join(ROOT, 'component-builder/runtime-renderer/upload-cases.json');
const harness = join(ROOT, 'component-builder/runtime-renderer/upload-harness.js');
const sourceFiles = [
  'node_modules/view-ui-plus/src/components/upload/upload.vue',
  'node_modules/view-ui-plus/src/styles/components/upload.less'
];

export async function run() {
  let observed;
  await extractRuntime(output, {casesPath:fixture,harnessPath:harness,
    observePage: async (page, context) => {
      const metrics = await page.locator('[data-runtime-case="data.upload.drag.empty"]').evaluate(root => {
        const bounds=el=>{const r=el.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height};};
        const style=el=>{const s=getComputedStyle(el);return {color:s.color,backgroundColor:s.backgroundColor,
          border:s.border,borderRadius:s.borderRadius,boxShadow:s.boxShadow,
          fontFamily:s.fontFamily,fontSize:s.fontSize,lineHeight:s.lineHeight,
          padding:s.padding,margin:s.margin};};
        const drag=root.querySelector('.ivu-upload-drag');
        const input=root.querySelector('input[type="file"]');
        const content=drag.querySelector('div');
        return {classes:[...root.classList],root:bounds(root),rootStyle:style(root),
          drag:{classes:[...drag.classList],bounds:bounds(drag),style:style(drag)},
          content:{text:content.textContent.trim(),bounds:bounds(content),style:style(content)},
          fileInputPresent:!!input,uploadListCount:root.querySelectorAll('.ivu-upload-list').length};
      });
      observed={scope:'official_upload_runtime_source',status:'PASS',candidateOnly:true,
        fidelityGate:'NOT_RUN',cases:context.cases,environment:context.environment,
        provenance:context.provenance,metrics,
        sourceFiles:Object.fromEntries(await Promise.all(sourceFiles.map(async file=>
          [file,hash(await readFile(join(ROOT,file)))])))};
    }});
  observed.referenceComponentIrSha256=hash(await readFile(join(output,'component_ir.json')));
  await writeFile(join(output,'upload-observation.json'),JSON.stringify(observed,null,2)+'\n');
  return {status:observed.status,metrics:observed.metrics};
}

if(process.argv[1]&&import.meta.url===pathToFileURL(resolve(process.argv[1])).href)
  console.log(JSON.stringify(await run(),null,2));
