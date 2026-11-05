import {build} from 'esbuild';
import {chromium} from 'playwright';
import {createHash} from 'node:crypto';
import {readFile,writeFile,mkdir,unlink} from 'node:fs/promises';
import {resolve,join,extname,relative} from 'node:path';
import {pathToFileURL} from 'node:url';
import {staticSnapshot,inspectStaticDelivery} from '../adapters/html/static-snapshot.mjs';
import {measureLayoutRelations} from '../adapters/html/layout-relations.mjs';
import {measureLayoutQuality} from '../adapters/html/layout-quality.mjs';

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
  icons+=`:root{--remix-${name}:${url}}.remix-${name}{mask-image:${url};-webkit-mask-image:${url}}`;
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
const moduleCss=await readFile(join(root,'adapters/html/confirmed-modules.css'),'utf8');
const assets={},assetHashes={};
for(const name of ir.requiredAssets||[]){
  const files={'default-logo':['default-logo.svg','image/svg+xml'],'default-avatar':['default-avatar.png','image/png']};
  if(!files[name])throw Error(`unknown_design_asset:${name}`);
  const [filename,mime]=files[name];const bytes=await readFile(join(root,'assets',filename));
  assetHashes[name]=sha(bytes);
  assets[name]=`data:${mime};base64,${bytes.toString('base64')}`;
}
const base=`html,body{margin:0}#app{min-height:100vh}.remix-custom{display:inline-block;width:1em;height:1em;background:currentColor;mask-size:contain;mask-repeat:no-repeat;-webkit-mask-size:contain;-webkit-mask-repeat:no-repeat}${moduleCss}`;
const reviewCss=`.composition-skeleton [data-tree-node]{outline:1px dashed #94a3b8;background-color:#dbeafe}.composition-skeleton [data-component="Table"]{background-color:#bbf7d0}.composition-skeleton [data-component="Button"],.composition-skeleton [data-component="Input"],.composition-skeleton [data-component="Select"]{background-color:#fde68a}`;
const title=String(ir.title).replaceAll('&','&amp;').replaceAll('<','&lt;');
const preview=join(out,'stage-preview.html'),final=join(out,'page.html');
await writeFile(preview,`<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${title}</title><style>${css}</style><style>${base}${icons}${reviewCss}</style></head><body><div id="app"></div><script>window.__designAssets=${JSON.stringify(assets).replaceAll('<','\\u003c')}</script><script id="design-ir" type="application/json">${irBytes.toString().replaceAll('<','\\u003c')}</script><script type="module">${bundle.outputFiles[0].text.replaceAll('</script','<\\/script')}</script></body></html>`);
const browser=await chromium.launch({headless:true});
const page=await browser.newPage({viewport:{width:Number(process.argv[4])||1440,height:Number(process.argv[5])||1000}});
const errors=[],stages={};let layoutSizing=[],reviewSheetSha256,responsiveQuality;page.on('pageerror',e=>errors.push(String(e)));
try{
  await page.goto(pathToFileURL(preview).href);await page.waitForFunction(()=>window.__ready===true);
  layoutSizing=await page.evaluate(async()=>{await window.__prepareLayout();return window.__sizingReport;});
  for(const stage of ['skeleton','component','delivery']){
    await page.evaluate(v=>window.__setStage(v),stage);
    await page.waitForTimeout(80);
    // Settle finite CSS transitions before both pixels and computed signatures.
    // screenshot(animations:'disabled') alone restores animations afterwards,
    // which otherwise makes an unchanged node acquire different style hashes.
    await page.evaluate(()=>{for(const animation of document.getAnimations()){
      if(Number.isFinite(animation.effect?.getComputedTiming().endTime)){
        try{animation.finish();}catch{/* Unresolved timelines are sampled as-is. */}
      }
    }});
    const shot=await page.screenshot({fullPage:true,animations:'disabled'});
    await writeFile(join(out,stage+'.png'),shot);
    const metrics=await page.evaluate(()=>({nodeIds:[...document.querySelectorAll('[data-tree-node]')].map(n=>n.dataset.treeNode),
      tableColumnCounts:[...document.querySelectorAll('.ivu-table-header thead tr')].map(tr=>tr.children.length),
      tableRows:document.querySelectorAll('.ivu-table-body .ivu-table-row').length,
      menuItems:document.querySelectorAll('.ivu-menu-item').length,arrows:document.querySelectorAll('.ivu-menu-submenu-title-icon').length,
      texts:document.querySelector('#app').innerText,
      overflow:document.documentElement.scrollWidth>innerWidth+1}))
    const signatures=await page.evaluate(async imageUrl=>{
      const nodes=[...document.querySelectorAll('[data-tree-node]')];
      const image=new Image();image.src=imageUrl;await image.decode();
      const canvas=document.createElement('canvas');canvas.width=image.width;canvas.height=image.height;
      const context=canvas.getContext('2d',{willReadFrequently:true});context.drawImage(image,0,0);
      const pixelHash=async n=>{const r=n.getBoundingClientRect(),x=Math.max(0,Math.floor(r.x)),y=Math.max(0,Math.floor(r.y));
        const w=Math.min(canvas.width-x,Math.ceil(r.right)-x),h=Math.min(canvas.height-y,Math.ceil(r.bottom)-y);
        if(w<=0||h<=0)return 'outside';const bytes=context.getImageData(x,y,w,h).data;
        return [...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(b=>b.toString(16).padStart(2,'0')).join('');};
      const rectCache=new WeakMap(),styleCache=new WeakMap();
      const rect=n=>{if(!rectCache.has(n)){const r=n.getBoundingClientRect();rectCache.set(n,[r.x,r.y,r.width,r.height]);}return rectCache.get(n);};
      const style=n=>{if(!styleCache.has(n)){const s=getComputedStyle(n);styleCache.set(n,[...s].map(k=>[k,s.getPropertyValue(k)]));}return styleCache.get(n);};
      const hash=async value=>[...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(JSON.stringify(value))))].map(b=>b.toString(16).padStart(2,'0')).join('');
      const groups={};
      for(const n of nodes){
        const ancestors=[];for(let p=n.parentElement;p;p=p.parentElement)ancestors.push([p.tagName,p.className,rect(p),style(p)]);
        // Official tables generate random internal IDs/classes. Compare semantic
        // DOM, resolved styles and actual pixels instead of those unstable IDs.
        const detail=[n,...n.querySelectorAll('*')].map(e=>[e.tagName,e.textContent,e.getAttribute('role'),rect(e),style(e),e.value,e.checked,e.disabled,...['::before','::after'].map(p=>{const s=getComputedStyle(e,p);return [s.content,s.color,s.backgroundColor,s.width,s.height,s.margin,s.position]})]);
        // Hash inside Chromium: transferring repeated full computed-style trees
        // through Playwright can consume gigabytes on ordinary admin pages.
        (groups[n.dataset.treeNode]??=[]).push(await hash([ancestors,detail,await pixelHash(n)]));
      }
      return {groups,geometry:nodes.map(n=>[n.dataset.treeNode,rect(n)])};
    },`data:image/png;base64,${shot.toString('base64')}`);
    const layoutRelations=await page.evaluate(measureLayoutRelations,ir.layoutRelations||[]);
    const relationIssues=layoutRelations.results.flatMap(r=>r.issues.map(issue=>`${r.id}:${issue}`));
    const layoutQuality=await page.evaluate(measureLayoutQuality);
    const qualityIssues=ir.layoutQualityPolicy?layoutQuality.results.flatMap(r=>r.issues.map(issue=>`${r.id}:${issue}`)):[];
    stages[stage]={status:errors.length||metrics.overflow||relationIssues.length||qualityIssues.length?'FAIL':'PASS',issues:[...errors,...(metrics.overflow?['viewport_overflow']:[]),...relationIssues,...qualityIssues],...metrics,layoutRelations,layoutQuality,screenshotSha256:sha(shot),
      geometrySha256:sha(JSON.stringify(signatures.geometry)),nodeSignatures:Object.fromEntries(Object.entries(signatures.groups).map(([id,value])=>[id,sha(JSON.stringify(value))]))};
  }
  if(Object.values(stages).every(s=>s.status==='PASS')){
    await writeFile(final,await staticSnapshot(page));await page.goto(pathToFileURL(final).href);
    const frozen=await inspectStaticDelivery(page);
    if(!frozen.app||frozen.scripts||frozen.reviewControls||(frozen.buttonPointerEvents&&frozen.buttonPointerEvents!=='none'))throw Error('static_delivery_invalid');
    const shot=await page.screenshot({fullPage:true});await writeFile(join(out,'delivery.png'),shot);
    stages.delivery.screenshotSha256=sha(shot);stages.delivery.static=frozen;
    const finalRelations=await page.evaluate(measureLayoutRelations,ir.layoutRelations||[]);
    stages.delivery.layoutRelations=finalRelations;
    stages.delivery.layoutQuality=await page.evaluate(measureLayoutQuality);
    if(ir.layoutQualityPolicy&&stages.delivery.layoutQuality.status!=='PASS'){
      stages.delivery.status='FAIL';stages.delivery.issues.push(...stages.delivery.layoutQuality.results.flatMap(r=>r.issues.map(issue=>`${r.id}:${issue}`)));
    }
    if(finalRelations.status!=='PASS'){
      stages.delivery.status='FAIL';stages.delivery.issues.push(...finalRelations.results.flatMap(r=>r.issues.map(issue=>`${r.id}:${issue}`)));
    }
    if(ir.layoutQualityPolicy){
      const viewport={width:Math.min(Number(process.argv[4])||1440,1100),height:Math.min(Number(process.argv[5])||1000,700)};
      await page.setViewportSize(viewport);
      await page.evaluate(()=>{window.scrollTo(0,document.documentElement.scrollHeight);for(const e of document.querySelectorAll('[data-tree-node]'))if(['auto','scroll'].includes(getComputedStyle(e).overflowY))e.scrollTop=e.scrollHeight;});
      await page.waitForTimeout(50);
      responsiveQuality={viewport,...await page.evaluate(measureLayoutQuality)};
      const footer=await page.evaluate(()=>{
        const bar=document.querySelector('[data-design-role="page-actions"]');if(!bar)return null;
        const panels=[...document.querySelectorAll('[data-design-role="module-panel"],[data-design-role="summary-panel"],[data-design-role="steps-panel"],[data-design-role="form-section"]')];
        const last=panels.at(-1);if(!last)return null;
        const bottom=last.getBoundingClientRect().bottom,top=bar.getBoundingClientRect().top;
        return {gap:top-bottom,issues:bottom>top+1?['footer_overlaps_last_module']:[]};
      });
      responsiveQuality.footer=footer;
      const issues=[...responsiveQuality.results.flatMap(r=>r.issues.map(issue=>`small:${r.id}:${issue}`)),...(footer?.issues||[])];
      if(issues.length){responsiveQuality.status='FAIL';stages.delivery.status='FAIL';stages.delivery.issues.push(...issues);}
      const smallShot=await page.screenshot({fullPage:true});
      await writeFile(join(out,'small-viewport.png'),smallShot);
      responsiveQuality.screenshotSha256=sha(smallShot);
    }
    await unlink(preview);
  }
  // A contact sheet saves viewer round trips; originals remain available for zoom.
  const panels=await Promise.all(['skeleton','component','delivery'].map(async stage=>`<section><h2>${stage}</h2><img src="data:image/png;base64,${(await readFile(join(out,stage+'.png'))).toString('base64')}" /></section>`));
  await page.setViewportSize({width:1800,height:1000});
  await page.setContent(`<style>body{margin:0;background:#eef1f5;font:16px sans-serif;display:flex;align-items:flex-start;gap:12px;padding:12px}section{width:584px;background:white}h2{margin:12px}img{width:100%;display:block}</style>${panels.join('')}`);
  await page.locator('img').evaluateAll(imgs=>Promise.all(imgs.map(img=>img.decode())));
  const sheet=await page.screenshot({fullPage:true});await writeFile(join(out,'review-sheet.png'),sheet);reviewSheetSha256=sha(sheet);
}finally{await browser.close();}
const qa={status:Object.values(stages).length===3&&Object.values(stages).every(s=>s.status==='PASS')?'PASS':'FAIL',
  sourceSha256:ir.sourceSha256,uiIrSha256:sha(irBytes),officialCssSha256:sha(await readFile(cssPath)),
  officialSourceSha256:sha(JSON.stringify(ir.officialSource)),
  snapshotSha256:sha(await readFile(join(root,'adapters/html/static-snapshot.mjs'))),
  relationCheckerSha256:sha(await readFile(join(root,'adapters/html/layout-relations.mjs'))),
  qualityCheckerSha256:sha(await readFile(join(root,'adapters/html/layout-quality.mjs'))),
  adapterSha256:sha(await readFile(join(root,'adapters/html/composition.mjs'))),exporterSha256:sha(await readFile(new URL(import.meta.url))),moduleCssSha256:sha(moduleCss),assetHashes,iconHashes,layoutSizing,stages,reviewSheetSha256,responsiveQuality,
  scope:'Runtime, declared layout geometry/surfaces and native Card toolbar checks; original-image batched visual review still required.'};
if(qa.status==='PASS')qa.pageSha256=sha(await readFile(final));
await writeFile(join(out,'qa.json'),JSON.stringify(qa,null,2));
console.log(JSON.stringify({status:qa.status,issues:Object.values(stages).flatMap(s=>s.issues)}));
if(qa.status!=='PASS')process.exitCode=1;
