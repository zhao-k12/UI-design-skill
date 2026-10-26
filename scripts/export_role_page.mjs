import { build } from 'esbuild';
import { chromium } from 'playwright';
import { createHash } from 'node:crypto';
import { readFile, writeFile, unlink } from 'node:fs/promises';
import { resolve, extname, join } from 'node:path';
import { pathToFileURL } from 'node:url';
import { staticSnapshot, inspectStaticDelivery } from '../adapters/html/static-snapshot.mjs';

const root = resolve(import.meta.dirname, '..');
const dir = resolve(process.argv[2]);
const coreFolder = process.argv[3] || 'core';
if (!dir.startsWith(join(root, 'artifacts') + '\\') && !dir.startsWith(join(root, 'artifacts') + '/')) throw Error('artifact_output_required');
const sha = x => createHash('sha256').update(x).digest('hex');
const json = async name => JSON.parse(await readFile(join(dir, name), 'utf8'));
const irBytes = await readFile(join(dir, coreFolder, 'ui_ir.json'));
const ir = JSON.parse(irBytes), c = ir.content;
const core = await json(coreFolder + '/qa_report.json');
if (core.status !== 'PASS' || ir.sourceSha256 !== sha(await readFile(join(dir, 'prototype.png')))) throw Error('core_source_gate');
const current = JSON.parse(await readFile(join(root, 'registries/icons/current.json')));
const registry = JSON.parse(await readFile(join(root, 'registries/icons/snapshots', current.snapshotSha256, 'registry.json')));
const names = [...new Set([c.brand,c.heading,c.logout,...c.sidebar,...c.headerActions,c.create,c.help,...c.rows.flatMap(row=>row.actions)].map(x=>x.icon).filter(Boolean))];
let iconCss=''; const iconHashes={};
for (const name of names) {
  const descriptor=registry.icons[`remix.${name}`];
  if (!descriptor || descriptor.status !== 'source-ready') throw Error(`missing_icon:${name}`);
  const svg=await readFile(join(root,'registries/icons/objects',descriptor.svgSha256+'.svg'));
  if (sha(svg)!==descriptor.svgSha256) throw Error(`icon_hash_mismatch:${name}`);
  iconHashes[name]=descriptor.svgSha256;
  const url=`url("data:image/svg+xml;base64,${svg.toString('base64')}")`;
  iconCss+=`.remix-${name}{mask-image:${url};-webkit-mask-image:${url}}`;
}
const bundle=await build({entryPoints:[join(root,'adapters/html/role-page-v1.mjs')],bundle:true,write:false,platform:'browser',format:'esm',minify:true,define:{'process.env.NODE_ENV':'"production"'}});
const cssPath=join(root,'node_modules/view-ui-plus/dist/styles/viewuiplus.css');
let css=await readFile(cssPath,'utf8');
for(const [,,asset] of [...css.matchAll(/url\((['"]?)([^)'"\s]+)\1\)/g)]) {
  if(/^(data:|https?:|#)/i.test(asset))continue;
  const path=resolve(root,'node_modules/view-ui-plus/dist/styles',asset.split(/[?#]/)[0]);
  const bytes=await readFile(path);
  const mime={'.woff2':'font/woff2','.woff':'font/woff','.ttf':'font/ttf','.svg':'image/svg+xml'}[extname(path)]||'application/octet-stream';
  css=css.replaceAll(asset,`data:${mime};base64,${bytes.toString('base64')}`);
}
// Only layout relationships and the locked SVG icon adapter. No component visual overrides.
const pad=ir.layout.containerPadding.value;
const local=`html,body{margin:0}#app,.role-layout{min-height:100vh}.role-side{min-height:100vh}.side-flow{display:flex;flex-direction:column;min-height:100vh}.logout-zone{margin-top:auto}.header-actions{display:flex;align-items:center;justify-content:flex-end;height:100%}.role-main{padding:${pad}px;min-width:0}.role-toolbar{display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap;margin-bottom:16px}.toolbar-left{display:flex;align-items:center;gap:8px;flex:0 1 50%}.search-field{flex:1;min-width:0}.toolbar-right{display:flex;align-items:center;gap:8px}.role-row-actions{display:flex;align-items:center;white-space:nowrap}.remix-custom{display:inline-block;width:1em;height:1em;background-color:currentColor;mask-size:contain;mask-repeat:no-repeat;mask-position:center;-webkit-mask-size:contain;-webkit-mask-repeat:no-repeat;-webkit-mask-position:center}.skeleton-cell{padding:16px;border:1px solid #94a3b8;color:#1e293b;box-sizing:border-box}.sk-brand,.sk-header{min-height:60px;background:#ddd6fe}.sk-nav{background:#dbeafe}.side-flow>.sk-nav:nth-child(2){flex:1}.sk-toolbar{background:#fde68a;min-height:72px;margin-bottom:16px}.sk-table{background:#bbf7d0;min-height:740px}`;
if(/\.ivu-[\w-]+/.test(local))throw Error('official_component_style_override');
const brandLayout='.brand-identity{display:inline-flex;align-items:center;gap:8px;height:100%}';
const html=`<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="source-sha256" content="${ir.sourceSha256}"><title>职务权限 · 系统管理中心</title><style data-official-css>${css}</style><style data-layout-only>${local}${brandLayout}${iconCss}</style></head><body><div id="app"></div><script type="application/json" id="design-ir">${irBytes.toString().replaceAll('<','\\u003c')}</script><script type="module">${bundle.outputFiles[0].text.replaceAll('</script','<\\/script')}</script></body></html>`;
const preview=join(dir,'stage-preview.html'), final=join(dir,'page.html');
await writeFile(preview,html);
const browser=await chromium.launch({headless:true});
const page=await browser.newPage({viewport:{width:1912,height:956},deviceScaleFactor:1});
const errors=[],stages={};
page.on('pageerror',error=>errors.push(String(error)));
try {
  await page.goto(pathToFileURL(preview).href);
  await page.waitForFunction(()=>window.__ready===true);
  for(const stage of ['skeleton','component','delivery']) {
    await page.evaluate(value=>window.__setStage(value),stage);
    await page.waitForTimeout(100);
    await writeFile(join(dir,`${stage}.png`),await page.screenshot({fullPage:true,animations:'disabled'}));
    const result=await page.evaluate(({stage,c})=>{
      const all=s=>[...document.querySelectorAll(s)],one=s=>document.querySelector(s);
      const rect=s=>one(s)?.getBoundingClientRect().toJSON();
      const rows=all('.ivu-table-body .ivu-table-row');
      const iconPairs=all('.ivu-btn').filter(b=>b.querySelector(':scope > i')&&b.querySelector(':scope > span'));
      const input=one('[data-region="search"] input');
      return {skeletonBlocks:all('.skeleton-cell').length,menus:all('[data-menu]').length,
        menuIcons:all('[data-menu] > i.remix-custom').length,menuArrows:all('.ivu-menu-submenu-title-icon').length,
        squareBrand:!!one('[data-region="brand"] .ivu-avatar-square .remix-settings-3-line'),
        selected:one('[data-menu].ivu-menu-item-active')?.getAttribute('data-menu'),
        rows:rows.length,rowTexts:rows.map(r=>r.innerText),
        rowActions:all('.role-row-actions button').length,rowIcons:all('.role-row-actions button > i.remix-custom').length,
        linkCells:all('[data-link-cell]').length,
        searchIcon:!!one('[data-region="search"] .ivu-input-search-icon'),placeholder:input?.placeholder,
        pairGaps:iconPairs.map(b=>{const i=b.querySelector(':scope > i'),t=b.querySelector(':scope > span');return t.getBoundingClientRect().left-i.getBoundingClientRect().right}),
        menuGaps:all('[data-menu]').map(b=>getComputedStyle(b.querySelector('i')).marginRight),
        header:rect('[data-region="header"]'),brand:rect('[data-region="brand"]'),
        sidebar:rect('[data-region="sidebar"]'),card:rect('[data-region="card"]'),table:rect('.ivu-table'),
        toolbar:rect('[data-region="toolbar"]'),
        lastActionRight:all('.role-row-actions').map(node=>node.lastElementChild.getBoundingClientRect().right),
        tableRight:one('.ivu-table')?.getBoundingClientRect().right,
        overflow:document.documentElement.scrollWidth>innerWidth+1,
        externalAssets:all('[src],link[href]').map(el=>el.getAttribute('src')||el.getAttribute('href')).filter(v=>/^https?:/.test(v)),
        missing:stage==='delivery'?[c.brand.label,c.heading.label,c.logout.label,...c.sidebar.map(x=>x.label),...c.sortActions.map(x=>x.label),c.create.label,c.help.label,...c.columns.map(x=>x.title)].filter(s=>!document.body.innerText.includes(s)):[]};
    },{stage,c});
    const issues=[...errors];
    if(stage==='skeleton') {
      if(result.skeletonBlocks!==6)issues.push('skeleton_coverage');
      if(result.brand.height!==result.header.height || result.brand.top!==result.header.top)issues.push('skeleton_shell_alignment');
    }
    else {
      if(result.menus!==c.sidebar.length||result.menuIcons!==c.sidebar.length||result.menuArrows!==0||result.selected!==c.activeMenu)issues.push('menu_coverage');
      if(result.rows!==c.rows.length||result.rowActions!==c.rows.length*6||result.rowIcons!==c.rows.length*6||result.linkCells!==c.rows.length*2)issues.push('table_coverage');
      if(!result.searchIcon)issues.push('search_icon_missing');
      if(!result.squareBrand)issues.push('brand_square_missing');
      if(result.brand.height!==result.header.height||result.brand.top!==result.header.top||result.card.left<result.sidebar.right)issues.push('shell_alignment');
      if(result.table.width<result.card.width-40)issues.push('table_not_fill');
      if(result.pairGaps.some(g=>Math.abs(g-4)>1)||result.menuGaps.some(g=>g!=='6px'))issues.push('official_icon_label_spacing');
      if(result.lastActionRight.some(x=>x>result.tableRight))issues.push('actions_overflow');
      if(stage==='delivery') {
        if(result.placeholder!==c.search||result.missing.length)issues.push('delivery_text_missing');
        if(c.rows.some((r,i)=>[r.name,r.memberCount,r.description,r.updatedAt,...r.actions.map(x=>x.label)].some(s=>!result.rowTexts[i]?.includes(s))))issues.push('row_content_missing');
      }
    }
    if(result.overflow||result.externalAssets.length)issues.push('viewport_or_offline_asset');
    stages[stage]={status:issues.length?'FAIL':'PASS',issues,...result};
  }
  if(Object.values(stages).every(x=>x.status==='PASS')) {
    await writeFile(final,await staticSnapshot(page));
    await page.goto(pathToFileURL(final).href);
    const freeze=await inspectStaticDelivery(page);
    if(!freeze.app||freeze.scripts||freeze.reviewControls||freeze.buttonPointerEvents!=='none'||freeze.buttonTabIndex!==-1)throw Error('static_delivery_invalid');
    const before=await page.screenshot({fullPage:true});
    await page.mouse.move(1550,220);
    const after=await page.screenshot({fullPage:true});
    if(sha(before)!==sha(after))throw Error('static_hover_changed');
    await writeFile(join(dir,'delivery.png'),before);
    stages.delivery.static=freeze;
    stages.delivery.hoverInvariant=true;
    await unlink(preview);
  }
}finally{await browser.close();}
const qa={status:Object.values(stages).length===3&&Object.values(stages).every(x=>x.status==='PASS')?'PASS':'FAIL',sourceSha256:ir.sourceSha256,uiIrSha256:sha(irBytes),officialCssSha256:sha(await readFile(cssPath)),adapterSha256:sha(await readFile(join(root,'adapters/html/role-page-v1.mjs'))),exporterSha256:sha(await readFile(new URL(import.meta.url))),iconHashes,stages};
for(const stage of ['skeleton','component','delivery'])qa.stages[stage].screenshotSha256=sha(await readFile(join(dir,stage+'.png')));
if(qa.status==='PASS')qa.pageSha256=sha(await readFile(final));
await writeFile(join(dir,'qa.json'),JSON.stringify(qa,null,2));
console.log(JSON.stringify({status:qa.status,stages:Object.fromEntries(Object.entries(stages).map(([k,v])=>[k,v.status])),issues:Object.values(stages).flatMap(x=>x.issues)}));
if(qa.status!=='PASS')process.exitCode=1;
