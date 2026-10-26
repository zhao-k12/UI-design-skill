import {build} from 'esbuild';
import {chromium} from 'playwright';
import {createHash} from 'node:crypto';
import {readFile,writeFile,mkdir,unlink} from 'node:fs/promises';
import {resolve,join,extname,relative} from 'node:path';
import {pathToFileURL} from 'node:url';
import {staticSnapshot,inspectStaticDelivery} from '../adapters/html/static-snapshot.mjs';

const root=resolve(import.meta.dirname,'..');
const coreDir=resolve(process.argv[2]);
const out=resolve(process.argv[3]);
const inside=relative(join(root,'artifacts'),out);
if(inside.startsWith('..')||resolve(out)===resolve(root))throw Error('artifact_output_required');
await mkdir(out,{recursive:true});
const sha=value=>createHash('sha256').update(value).digest('hex');
const irBytes=await readFile(join(coreDir,'ui_ir.json'));
const ir=JSON.parse(irBytes),core=JSON.parse(await readFile(join(coreDir,'qa_report.json')));
if(ir.schemaVersion!=='html-composition-v1'||core.status!=='PASS'||core.sourceSha256!==ir.sourceSha256||core.uiIrSha256!==sha(irBytes))throw Error('core_gate_failed');
// Registry lookup resolves assets; it never chooses a page structure.
const current=JSON.parse(await readFile(join(root,'registries/icons/current.json')));
const registry=JSON.parse(await readFile(join(root,'registries/icons/snapshots',current.snapshotSha256,'registry.json')));
let icons='';const iconHashes={};
for(const name of ir.requiredIcons){
  const item=registry.icons[`remix.${name}`];
  if(!item||item.status!=='source-ready')throw Error(`missing_icon:${name}`);
  const bytes=await readFile(join(root,'registries/icons/objects',item.svgSha256+'.svg'));
  if(sha(bytes)!==item.svgSha256)throw Error(`icon_hash_mismatch:${name}`);
  iconHashes[name]=item.svgSha256;
  const url=`url("data:image/svg+xml;base64,${bytes.toString('base64')}")`;
  icons+=`.remix-${name}{mask-image:${url};-webkit-mask-image:${url}}`;
}
const bundle=await build({entryPoints:[join(root,'adapters/html/composition.mjs')],bundle:true,write:false,platform:'browser',format:'esm',minify:true,define:{'process.env.NODE_ENV':'"production"'}});
const cssPath=join(root,'node_modules/view-ui-plus/dist/styles/viewuiplus.css');
let css=await readFile(cssPath,'utf8');
for(const [,,asset] of [...css.matchAll(/url\((['"]?)([^)'"\s]+)\1\)/g)]){
  if(/^(data:|https?:|#)/.test(asset))continue;
  const file=resolve(root,'node_modules/view-ui-plus/dist/styles',asset.split(/[?#]/)[0]);
  const mime={'.woff2':'font/woff2','.woff':'font/woff','.ttf':'font/ttf','.svg':'image/svg+xml'}[extname(file)]||'application/octet-stream';
  css=css.replaceAll(asset,`data:${mime};base64,${(await readFile(file)).toString('base64')}`);
}
const base=`html,body{margin:0}#app{min-height:100vh}.remix-custom{display:inline-block;width:1em;height:1em;background:currentColor;mask-size:contain;mask-repeat:no-repeat;-webkit-mask-size:contain;-webkit-mask-repeat:no-repeat}`;
const reviewCss=`.composition-skeleton [data-tree-node]{outline:1px dashed #94a3b8;position:relative;background-color:#dbeafe}.composition-skeleton [data-component="Table"]{background-color:#bbf7d0}.composition-skeleton [data-component="Button"],.composition-skeleton [data-component="Input"],.composition-skeleton [data-component="Select"]{background-color:#fde68a}.composition-skeleton [data-tree-node]::before{content:attr(data-component);position:absolute;top:0;right:0;z-index:10;font-size:10px;line-height:12px;background:#e0e7ff;color:#17233d;pointer-events:none}`;
const title=String(ir.title).replaceAll('&','&amp;').replaceAll('<','&lt;');
const preview=join(out,'stage-preview.html'),final=join(out,'page.html');
await writeFile(preview,`<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${title}</title><style>${css}</style><style>${base}${icons}${reviewCss}</style></head><body><div id="app"></div><script id="design-ir" type="application/json">${irBytes.toString().replaceAll('<','\\u003c')}</script><script type="module">${bundle.outputFiles[0].text.replaceAll('</script','<\\/script')}</script></body></html>`);
const browser=await chromium.launch({headless:true});
const page=await browser.newPage({viewport:{width:Number(process.argv[4])||1440,height:Number(process.argv[5])||1000}});
const errors=[],stages={};let layoutSizing=[];page.on('pageerror',e=>errors.push(String(e)));
try{
  await page.goto(pathToFileURL(preview).href);await page.waitForFunction(()=>window.__ready===true);
  layoutSizing=await page.evaluate(async()=>{await window.__prepareLayout();return window.__sizingReport;});
  for(const stage of ['skeleton','component','delivery']){
    await page.evaluate(v=>window.__setStage(v),stage);
    await page.waitForTimeout(80);
    const shot=await page.screenshot({fullPage:true,animations:'disabled'});
    await writeFile(join(out,stage+'.png'),shot);
    const metrics=await page.evaluate(()=>({nodeIds:[...document.querySelectorAll('[data-tree-node]')].map(n=>n.dataset.treeNode),
      tableColumnCounts:[...document.querySelectorAll('.ivu-table-header thead tr')].map(tr=>tr.children.length),
      tableRows:document.querySelectorAll('.ivu-table-body .ivu-table-row').length,
      menuItems:document.querySelectorAll('.ivu-menu-item').length,arrows:document.querySelectorAll('.ivu-menu-submenu-title-icon').length,
      texts:document.querySelector('#app').innerText,
      overflow:document.documentElement.scrollWidth>innerWidth+1}))
    stages[stage]={status:errors.length||metrics.overflow?'FAIL':'PASS',issues:[...errors,...(metrics.overflow?['viewport_overflow']:[])],...metrics,screenshotSha256:sha(shot)};
  }
  if(Object.values(stages).every(s=>s.status==='PASS')){
    await writeFile(final,await staticSnapshot(page));await page.goto(pathToFileURL(final).href);
    const frozen=await inspectStaticDelivery(page);
    if(!frozen.app||frozen.scripts||frozen.reviewControls||(frozen.buttonPointerEvents&&frozen.buttonPointerEvents!=='none'))throw Error('static_delivery_invalid');
    const shot=await page.screenshot({fullPage:true});await writeFile(join(out,'delivery.png'),shot);
    stages.delivery.screenshotSha256=sha(shot);stages.delivery.static=frozen;
    await unlink(preview);
  }
}finally{await browser.close();}
const qa={status:Object.values(stages).length===3&&Object.values(stages).every(s=>s.status==='PASS')?'PASS':'FAIL',
  sourceSha256:ir.sourceSha256,uiIrSha256:sha(irBytes),officialCssSha256:sha(await readFile(cssPath)),
  adapterSha256:sha(await readFile(join(root,'adapters/html/composition.mjs'))),exporterSha256:sha(await readFile(new URL(import.meta.url))),iconHashes,layoutSizing,stages,
  scope:'Runtime/structure checks only; original-image batched visual review required before delivery.'};
if(qa.status==='PASS')qa.pageSha256=sha(await readFile(final));
await writeFile(join(out,'qa.json'),JSON.stringify(qa,null,2));
console.log(JSON.stringify({status:qa.status,issues:Object.values(stages).flatMap(s=>s.issues)}));
if(qa.status!=='PASS')process.exitCode=1;
